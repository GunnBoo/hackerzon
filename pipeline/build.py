"""Combine HN mentions + Claude labels into the site's data files.
Usage: python3 build.py data site/data"""
import json, sys, os, glob, re, math, collections, shutil
D, OUT = sys.argv[1], sys.argv[2]
# all sources merged by merge_all.py (Amazon links, other store links, Ask HN answers)
cands = json.load(open(f"{D}/entities.json"))
for e in cands.values(): e["n_mentions"] = len(e["mentions"])
ol = json.load(open(f"{D}/openlibrary.json"))
olc = json.load(open(f"{D}/olcovers.json")) if os.path.exists(f"{D}/olcovers.json") else {}
imgc = json.load(open(f"{D}/imgcredits.json")) if os.path.exists(f"{D}/imgcredits.json") else {}
def own_img(a):
    f = re.sub(r"[^A-Za-z0-9._-]", "_", a) + ".jpg"
    return f"img/{f}" if a in imgc and os.path.exists(f"{OUT}/../img/{f}") else None
labels = {}
for fn in sorted(glob.glob(f"{D}/labels/*.jsonl")) + sorted(glob.glob(f"{D}/labels2/*.jsonl")):
    for line in open(fn):
        line = line.strip()
        if not line: continue
        try: o = json.loads(line)
        except Exception: continue
        if o.get("a") in cands: labels[o["a"]] = o
kept = {a: o for a, o in labels.items() if o.get("keep")}
for a, o in kept.items():  # stances from Ask HN extraction fill in comments the labeler didn't see
    o["st"] = {**cands[a].get("st", {}), **o.get("st", {})}
print("labeled", len(labels), "kept", len(kept))

# merge duplicates (e.g. Kindle + print edition) by normalized title + first author
def norm(o):
    t = re.sub(r"[^a-z0-9 ]", "", o["t"].lower().split(":")[0]).strip()
    t = re.sub(r"^(the|a|an) ", "", t)
    first = (o.get("by") or "").lower().split(",")[0].split(" and ")[0].split()
    last = re.sub(r"[^a-z]", "", first[-1]) if first else ""
    return t + "|" + last
groups = collections.defaultdict(list)
for a, o in kept.items(): groups[norm(o)].append(a)
for key, asins in groups.items():
    if len(asins) < 2: continue
    asins.sort(key=lambda a: -cands[a]["n_mentions"])
    main = asins[0]
    ms = {m["id"]: m for a in asins for m in cands[a]["mentions"]}
    cands[main]["mentions"] = sorted(ms.values(), key=lambda m: m["month"])
    cands[main]["editions"] = sum((cands[a]["editions"] for a in asins), [])
    for a in asins[1:]:
        cands[main]["links"] = {**cands[a].get("links", {}), **cands[main].get("links", {})}
        cands[main]["asin"] = cands[main].get("asin") or cands[a].get("asin")
        for k, v in cands[a].get("src", {}).items(): cands[main]["src"][k] = cands[main]["src"].get(k, 0) + v
        kept[main]["st"] = {**kept[a].get("st", {}), **kept[main].get("st", {})}
        del kept[a]
# products: a name-only item ("AeroPress Coffee Maker", from Ask HN) folds into the one Amazon-linked
# product whose name contains all its words ("AeroPress Coffee and Espresso Maker"). Only unique matches.
STOP = {"the", "a", "an", "and", "of", "for", "with", "by", "in"}
def ptoks(o):
    return {w for w in re.findall(r"[a-z0-9]+", (o["t"] + " " + (o.get("by") or "")).lower()) if w not in STOP}
amz_prods = [a for a, o in kept.items() if o.get("kind") == "product" and cands[a].get("asin")]
merges = []
for a in [a for a, o in list(kept.items()) if o.get("kind") == "product" and not cands[a].get("asin")]:
    T = ptoks(kept[a])
    if len(T) < 2: continue
    hits = [b for b in amz_prods if b in kept and T <= ptoks(kept[b])]
    if len(hits) != 1: continue
    main = hits[0]
    ms = {m["id"]: m for x in (main, a) for m in cands[x]["mentions"]}
    cands[main]["mentions"] = sorted(ms.values(), key=lambda m: m["month"])
    for k2, v in cands[a].get("src", {}).items(): cands[main]["src"][k2] = cands[main]["src"].get(k2, 0) + v
    kept[main]["st"] = {**kept[a].get("st", {}), **kept[main].get("st", {})}
    merges.append((kept[a]["t"], "->", kept[main]["t"]))
    del kept[a]
print("product merges:", len(merges))
for m in merges[:60]: print("  ", *m)
print("after duplicate merge", len(kept))

def score(a, o):
    ms = cands[a]["mentions"]
    st = o.get("st", {})
    lab = [st[m["id"]] for m in ms if m["id"] in st]
    pos = sum(1 for s in lab if s == "rec") + 0.5 * sum(1 for s in lab if s == "cite")
    ratio = pos / len(lab) if lab else 0.5
    months = len({m["month"] for m in ms})
    authors = len({m["author"] for m in ms})
    # Months with an (estimated) recommendation, like HackerTube's ranking.
    # Each person counts for at most 2 months, so one enthusiast can't carry an item.
    per_author = collections.defaultdict(list)
    for m in ms:
        if m["month"] not in per_author[m["author"]]:
            per_author[m["author"]].append(m["month"])
    capped = {mo for mos in per_author.values() for mo in mos[:2]}
    sc = len(capped) * ratio
    return round(sc, 1), round(ratio, 2), months, authors

prods = []
for a, o in kept.items():
    c = cands[a]
    sc, ratio, months, authors = score(a, o)
    if sc < 1.5: continue
    ms = c["mentions"]
    years = sorted({m["month"][:4] for m in ms})
    hist = collections.Counter(m["month"][:4] for m in ms)
    meta = ol.get(a) or {}
    prods.append({
        "a": a, "t": o["t"], "by": o.get("by", ""), "d": o["dept"], "sub": o.get("sub", ""), "k": o["kind"],
        "s": o.get("s", ""), "w": o.get("w", ""), "ab": o.get("about", [])[:4], "q": o.get("q"),
        "tg": o.get("tags", [])[:5], "aged": o.get("aged", ""),
        # hidden gem: Claude judged it niche, and HN's comments are mostly positive
        "gem": bool(o.get("gem")) and ratio >= 0.6 and sc >= 3 and authors <= 20,
        "sc": sc, "r": ratio, "nm": months, "na": authors, "n": len(ms),
        "f": ms[0]["month"], "l": ms[-1]["month"],
        "y": {y: hist[y] for y in years},
        "ed": [e for e in c["editions"] if e != a][:4],
        "amz": c.get("asin"), "lk": c.get("links", {}),
        "src": sorted(c.get("src", {}), key=lambda k: -c["src"][k]),
        "isbn": bool(c.get("asin") and re.fullmatch(r"\d{9}[\dX]", c["asin"])),
        "oc": olc.get(a),
        "im": own_img(a), "ic": {k: v for k, v in imgc.get(a, {}).items() if k in ("src", "url", "license", "artist")} if own_img(a) else None,
        "pub": meta.get("year"), "pg": meta.get("pages"),
    })
prods.sort(key=lambda p: (-p["sc"], -p["na"]))
for i, p in enumerate(prods): p["rk"] = i + 1
print("products in store", len(prods))

# HN's Choice: best in each sub-category
best = {}
for p in prods:
    k = (p["d"], p["sub"])
    if k not in best and p["sc"] >= 6: best[k] = p["a"]
for p in prods: p["hc"] = best.get((p["d"], p["sub"])) == p["a"]

# "HNers who recommended this also recommended": shared recommenders + same-comment co-mentions
idx = {p["a"]: p for p in prods}
by_author = collections.defaultdict(set)
by_comment = collections.defaultdict(set)
for p in prods:
    for m in cands[p["a"]]["mentions"]:
        by_author[m["author"]].add(p["a"]); by_comment[m["id"]].add(p["a"])
co = collections.defaultdict(collections.Counter)
for au, s in by_author.items():
    if len(s) < 2 or len(s) > 60: continue
    w = 1 / math.log(2 + len(s))
    for x in s:
        for y in s:
            if x != y: co[x][y] += w
for cid, s in by_comment.items():
    if len(s) < 2 or len(s) > 25: continue
    for x in s:
        for y in s:
            if x != y: co[x][y] += 0.5
for p in prods:
    p["rel"] = [b for b, _ in co[p["a"]].most_common(12)]

# write
if os.path.exists(f"{OUT}/m"): shutil.rmtree(f"{OUT}/m")
os.makedirs(f"{OUT}/m", exist_ok=True)
st_all = {a: o.get("st", {}) for a, o in labels.items()}
total_mentions = 0
for p in prods:
    st = kept[p["a"]].get("st", {})
    ms = [{"id": m["id"], "u": m["author"], "mo": m["month"], "sid": m.get("story_id"),
           "stt": m.get("story_title") or "", "x": m["text"][:3000], "s": st.get(m["id"]), "v": m.get("via", "amazon")}
          for m in cands[p["a"]]["mentions"]]
    total_mentions += len(ms)
    json.dump(ms, open(f"{OUT}/m/{p['a']}.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(prods, open(f"{OUT}/products.json", "w"), ensure_ascii=False, separators=(",", ":"))
allm = sorted({m["month"] for p in prods for m in cands[p["a"]]["mentions"]})
json.dump({"products": len(prods), "mentions": total_mentions,
           "people": len({m["author"] for p in prods for m in cands[p["a"]]["mentions"]}),
           "scanned": sum(1 for _ in open(f"{D}/raw/comments.jsonl")),
           "scanned_stores": sum(1 for _ in open(f"{D}/raw/stores.jsonl")),
           "askhn_threads": len(json.load(open(f"{D}/askhn/threads.json"))),
           "askhn_answers": sum(1 for l in open(f"{D}/askhn/comments.jsonl") if '"depth": 1' in l),
           "by_source": dict(collections.Counter(s for p in prods for s in p["src"])),
           "asins": sum(1 for _ in open(f"{D}/products_all.jsonl")),
           "from": allm[0], "to": allm[-1]}, open(f"{OUT}/stats.json", "w"))
print("wrote", OUT, "mentions", total_mentions)
