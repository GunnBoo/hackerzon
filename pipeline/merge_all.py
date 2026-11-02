"""Merge the three sources into one set of store items:
  1. Amazon links (data/products_all.jsonl, editions merged via Open Library)
  2. Other store/publisher links (data/stores_items.jsonl; ISBN-keyed ones attach to the Amazon item)
  3. Products named in Ask HN answers (data/askhn/out/*.jsonl), matched by title (+ author)
Writes data/entities.json and labeling batches (data/batches2/) for new items that pass the cut."""
import json, re, glob, os, collections, datetime, unicodedata
D = "data"
ol = json.load(open(f"{D}/openlibrary.json"))
labels = {}
for fn in glob.glob(f"{D}/labels/*.jsonl") + glob.glob(f"{D}/labels2/*.jsonl"):
    for l in open(fn):
        if l.strip(): o = json.loads(l); labels[o["a"]] = o
cands = json.load(open(f"{D}/candidates.json"))          # Amazon items that already passed (editions merged)
rows = {json.loads(l)["asin"]: json.loads(l) for l in open(f"{D}/products_all.jsonl")}

def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    t = re.split(r"[:(\[]| - | – ", t)[0]
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"^(the|a|an) ", "", t.strip())
    t = re.sub(r"\b(\d+(st|nd|rd|th) edition|edition|paperback|hardcover|kindle|vol(ume)? \d+|volumes? \d+ \d+)\b", "", t)
    return re.sub(r"\s+", " ", t).strip()
def last(by):
    w = re.sub(r"[^a-z ]", " ", unicodedata.normalize("NFKD", (by or "").split(",")[0].split(" and ")[0]).encode("ascii", "ignore").decode().lower()).split()
    w = [x for x in w if x not in ("jr", "sr", "ii", "iii", "phd", "md", "et", "al")]
    return w[-1] if w else ""
def pnorm(name, by):
    """products: drop the brand prefix so 'Herman Miller Aeron' == 'Aeron'"""
    t, b = norm(name), norm(by)
    if b and t.startswith(b + " "): t = t[len(b) + 1:]
    return t

E = {}          # id -> entity
alias = {}      # asin -> entity id
# 1. Amazon entities: every candidate (editions merged) + every other ASIN
for a, c in cands.items():
    lab = labels.get(a, {})
    meta = ol.get(a, {})
    E[a] = {"id": a, "asin": a, "editions": c["editions"], "title": lab.get("t") or meta.get("title") or c.get("slug_title"),
            "by": lab.get("by") or ", ".join(meta.get("authors", [])[:2]), "kind": lab.get("kind"), "mentions": {m["id"]: dict(m, via="amazon") for m in c["mentions"]},
            "links": {}, "src": {"amazon": len(c["mentions"])}, "st": dict(lab.get("st", {}))}
    for e in c["editions"]: alias[e] = a
for a, r in rows.items():
    if a in alias: continue
    E[a] = {"id": a, "asin": a, "editions": [a], "title": (ol.get(a) or {}).get("title") or r.get("slug_title"), "by": "", "kind": None,
            "mentions": {m["id"]: dict(m, via="amazon") for m in r["mentions"]}, "links": {}, "src": {"amazon": len(r["mentions"])}, "st": {}}
    alias[a] = a

STORE_URL = {"pp": "https://pragprog.com/titles/{}/", "mn": "https://www.manning.com/books/{}", "ns": "https://nostarch.com/{}",
             "or": "https://www.oreilly.com/library/view/{}/", "gr": "https://www.goodreads.com/book/show/{}", "mit": "https://mitpress.mit.edu/books/{}",
             "cam": "https://www.cambridge.org/core/books/{}", "bh": "https://www.bhphotovideo.com/c/product/{}-REG/", "etsy": "https://www.etsy.com/listing/{}"}
STORE_NAME = {"pp": "Pragmatic Bookshelf", "mn": "Manning", "ns": "No Starch Press", "or": "O'Reilly", "gr": "Goodreads", "mit": "MIT Press",
              "cam": "Cambridge University Press", "bh": "B&H Photo", "etsy": "Etsy"}
# 2. store items
for l in open(f"{D}/stores_items.jsonl"):
    s = json.loads(l); k = s["key"]
    ms = {m["id"]: m for m in s["mentions"]}
    if ":" not in k:                       # ISBN-10 == ASIN
        eid = alias.get(k)
        if not eid:
            E[k] = {"id": k, "asin": k, "editions": [k], "title": s.get("slug_title"), "by": "", "kind": "book", "mentions": {}, "links": {}, "src": {}, "st": {}}
            eid = alias[k] = k
    else:
        p, v = k.split(":", 1)
        eid = "s-" + re.sub(r"[^a-z0-9]+", "-", k.lower())
        if eid not in E:
            E[eid] = {"id": eid, "asin": None, "editions": [], "title": s.get("slug_title"), "by": "", "kind": s.get("kind"), "mentions": {},
                      "links": {STORE_NAME[p]: STORE_URL[p].format(v)}, "src": {}, "st": {}}
    e = E[eid]
    for mid, m in ms.items(): e["mentions"].setdefault(mid, m)
    for site, n in s["src"].items(): e["src"][site] = e["src"].get(site, 0) + n

# fold store-only items (Goodreads, Manning, ...) into an existing item with the same title
base = collections.defaultdict(list)
for e in E.values():
    if not e["id"].startswith("s-") and e["title"] and (e["id"] in labels or e["id"] in ol):
        base[norm(e["title"])].append(e["id"])
folded = 0
for sid in [i for i in E if i.startswith("s-")]:
    s = E[sid]; t = norm(s["title"])
    if len(t) < 4 or t not in base: continue
    tgt = E[max(base[t], key=lambda i: (i in labels and labels[i].get("keep"), len(E[i]["mentions"])))]
    for mid, m in s["mentions"].items(): tgt["mentions"].setdefault(mid, m)
    tgt["links"].update(s["links"])
    for site, n in s["src"].items(): tgt["src"][site] = tgt["src"].get(site, 0) + n
    del E[sid]; folded += 1
print("store items folded into existing items:", folded)

# title index over entities with a usable title (labeled / Open Library / store slugs)
def index():
    idx = collections.defaultdict(list)
    for e in E.values():
        if e["title"]:
            idx[norm(e["title"])].append(e["id"])
    return idx
idx = index()
by_author = collections.defaultdict(list)
for e in E.values():
    if e["title"] and e["by"] and (e["id"] in labels or e["id"] in ol): by_author[last(e["by"])].append((norm(e["title"]), e["id"]))
def prefix_match(t, ln):
    """same author, and one title is the short form of the other ('Art of Computer Programming' vs '... Volume 1')"""
    if not ln or len(t.split()) < 2: return None
    best = [i for nt, i in by_author.get(ln, []) if nt.startswith(t + " ") or t.startswith(nt + " ")]
    return max(best, key=lambda i: len(E[i]["mentions"])) if best else None

# 3. Ask HN extractions
src = {}
for l in open(f"{D}/askhn/comments.jsonl"):
    r = json.loads(l)
    if r["depth"] == 1: src[r["id"]] = r
new_groups = collections.defaultdict(lambda: {"names": collections.Counter(), "by": collections.Counter(), "kind": collections.Counter(), "hits": []})
n_items = matched = 0
for fn in sorted(glob.glob(f"{D}/askhn/out/*.jsonl")):
    for l in open(fn):
        if not l.strip(): continue
        try: o = json.loads(l)
        except Exception: continue
        r = src.get(str(o.get("id")))
        if not r: continue
        for it in o.get("items", []):
            n_items += 1
            t = norm(it.get("n"))
            if len(t) < 2: continue
            ln = last(it.get("by"))
            ids = idx.get(t, []) or ([pm] if it.get("k") == "book" and (pm := prefix_match(t, ln)) else [])
            if it.get("k") != "book": t = pnorm(it.get("n"), it.get("by"))
            # same title; prefer the entity whose author/brand matches, then the most-mentioned
            ids = sorted(ids, key=lambda i: (last(E[i]["by"]) == ln and ln != "", len(E[i]["mentions"])), reverse=True)
            if ids and (not ln or not E[ids[0]]["by"] or last(E[ids[0]]["by"]) == ln or it.get("k") != "book"):
                matched += 1
                hit_e = E[ids[0]]
                key = None
            else:
                key = ("n", t, ln if it.get("k") == "book" else "")
                hit_e = None
            m = {"id": r["id"], "author": r["author"], "month": datetime.datetime.utcfromtimestamp(r["created_at_i"]).strftime("%Y-%m"),
                 "story_id": r["story_id"], "story_title": r["story_title"], "n_links": len(o["items"]), "text": r["text"][:2500], "via": "askhn"}
            if hit_e:
                hit_e["mentions"].setdefault(m["id"], m); hit_e["st"].setdefault(m["id"], it["s"])
                hit_e["src"]["askhn"] = hit_e["src"].get("askhn", 0) + 1
            else:
                g = new_groups[key]; g["names"][it["n"].strip()] += 1; g["by"][(it.get("by") or "").strip()] += 1; g["kind"][it["k"]] += 1
                g["hits"].append((m, it["s"]))
for key, g in new_groups.items():
    eid = "n-" + re.sub(r"[^a-z0-9]+", "-", (key[1] + " " + key[2]).strip())[:60]
    by = next((b for b, _ in g["by"].most_common() if b), "")
    E[eid] = {"id": eid, "asin": None, "editions": [], "title": g["names"].most_common(1)[0][0], "by": by, "kind": g["kind"].most_common(1)[0][0],
              "mentions": {}, "links": {}, "src": {"askhn": len(g["hits"])}, "st": {}}
    for m, s in g["hits"]:
        E[eid]["mentions"].setdefault(m["id"], m); E[eid]["st"].setdefault(m["id"], s)
print(f"Ask HN items {n_items}, matched to existing {matched}, new name groups {len(new_groups)}")

def stats(e):
    ms = sorted(e["mentions"].values(), key=lambda m: m["month"])
    e["mentions"] = ms
    e["n_authors"] = len({m["author"] for m in ms}); e["n_months"] = len({m["month"] for m in ms})
    au = collections.Counter(m["author"] for m in ms)
    e["top_author_share"] = round(au.most_common(1)[0][1] / len(ms), 2) if ms else 1
    # an Ask HN-only item needs its recommenders to say they like it
    return e
for e in E.values(): stats(e)
def passes(e):
    if e["n_authors"] < 3 or e["n_months"] < 3: return False
    if set(e["src"]) <= {"askhn", "goodreads"}:   # found by name (Goodreads is a catalog, not a store): need 4 people recommending it, in 3+ months
        rec = [m for m in e["mentions"] if e["st"].get(m["id"]) == "rec" or m.get("via") == "goodreads"]
        return len({m["author"] for m in rec}) >= 4 and len({m["month"] for m in rec}) >= 3
    return True
passing = {i: e for i, e in E.items() if passes(e)}
already = {i for i in passing if i in labels}
import sys as _s
_tag = _s.argv[1] if len(_s.argv) > 1 else "c"
queued = {json.loads(l)["asin"] for f in glob.glob(f"{D}/batches2/*.jsonl") if not os.path.basename(f).startswith(_tag) for l in open(f) if l.strip()}
need = [e for i, e in passing.items() if i not in labels and i not in queued]
need.sort(key=lambda e: (-e["n_months"], -e["n_authors"]))
print(f"entities {len(E)}, passing cut {len(passing)}, already labeled {len(already)}, new to label {len(need)}")
print("new by source:", collections.Counter(tuple(sorted(e['src'])) for e in need).most_common(8))
json.dump(passing, open(f"{D}/entities.json", "w"))

# batches for card writing (same format/TASK as before)
def snippet(m, e):
    t = m["text"]
    keys = [k for k in [*(e["editions"] or []), (e["title"] or "")[:25]] if k]
    pos = next((t.upper().find(k.upper()) for k in keys if t.upper().find(k.upper()) >= 0), -1)
    if pos < 0: return t[:420]
    s = max(0, pos - 260); en = min(len(t), pos + 160)
    return ("…" if s else "") + t[s:en] + ("…" if en < len(t) else "")
def pick(ms, k=8):
    seen, out = set(), []
    step = max(1, len(ms) // k)
    for m in ms[::step] + ms:
        if m["author"] in seen: continue
        seen.add(m["author"]); out.append(m)
        if len(out) >= k: break
    return sorted(out, key=lambda m: m["month"])
os.makedirs(f"{D}/batches2", exist_ok=True); os.makedirs(f"{D}/labels2", exist_ok=True)
import sys
TAG = sys.argv[1] if len(sys.argv) > 1 else "c"
for f in glob.glob(f"{D}/batches2/{TAG}*.jsonl"): os.remove(f)
B = 70
for bi in range(0, len(need), B):
    with open(f"{D}/batches2/{TAG}{bi//B:02d}.jsonl", "w") as f:
        for e in need[bi:bi+B]:
            meta = ol.get(e["asin"] or "")
            known = ({"title": meta["title"], "authors": meta["authors"][:3], "year": meta["year"]} if meta else
                     {"name_hint": e["title"], "maker_or_author_hint": e["by"], "kind_hint": e["kind"]})
            f.write(json.dumps({"asin": e["id"], "known": known,
                "stats": {k: e[k] for k in ["n_authors", "n_months", "top_author_share"]} | {"first": e["mentions"][0]["month"], "last": e["mentions"][-1]["month"]},
                "comments": [{"id": m["id"], "by": m["author"], "mo": m["month"], "story": (m.get("story_title") or "")[:90], "text": snippet(m, e)} for m in pick(e["mentions"])]},
                ensure_ascii=False) + "\n")
print("label batches:", len(glob.glob(f"{D}/batches2/{TAG}*.jsonl")))
