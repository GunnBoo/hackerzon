"""Merge book editions (same Open Library work), apply the HN cut (>=3 people, >=3 months),
and write compact batch files for the Claude labeling pass."""
import json, sys, os, re, collections
D = sys.argv[1]; BATCH = int(sys.argv[2]) if len(sys.argv) > 2 else 70
rows = {json.loads(l)["asin"]: json.loads(l) for l in open(f"{D}/products_all.jsonl")}
ol = json.load(open(f"{D}/openlibrary.json"))

# group candidate ASINs by work key
groups = collections.defaultdict(list)
for a, r in rows.items():
    if a in ol and ol[a].get("work"):
        groups[ol[a]["work"]].append(a)
merged = {}
used = set()
for w, asins in groups.items():
    if len(asins) == 1: continue
    asins.sort(key=lambda a: -rows[a]["n_mentions"])
    main = asins[0]
    ms = {}
    for a in asins:
        for m in rows[a]["mentions"]: ms[m["id"]] = m
        used.add(a)
    merged[main] = dict(rows[main], mentions=sorted(ms.values(), key=lambda m: m["month"]), editions=asins)
for a, r in rows.items():
    if a not in used: merged[a] = dict(r, editions=[a])

def stats(r):
    ms = r["mentions"]
    au = collections.Counter(m["author"] for m in ms)
    r["n_mentions"] = len(ms); r["n_authors"] = len(au); r["n_months"] = len({m["month"] for m in ms})
    r["first"] = ms[0]["month"]; r["last"] = ms[-1]["month"]
    r["top_author_share"] = round(au.most_common(1)[0][1] / len(ms), 2)
    return r
cands = [stats(r) for r in merged.values()]
cands = [r for r in cands if r["n_authors"] >= 3 and r["n_months"] >= 3]
cands.sort(key=lambda r: (-r["n_months"], -r["n_authors"]))
print("candidates after edition merge:", len(cands))

def snippet(m, asins):
    t = m["text"]
    pos = -1
    for a in asins:
        pos = t.upper().find(a)
        if pos >= 0: break
    if pos < 0: return t[:380]
    s = max(0, pos - 260); e = min(len(t), pos + 140)
    return ("…" if s else "") + t[s:e] + ("…" if e < len(t) else "")

def pick(ms, k=8):
    # spread across time, one per author first
    seen, out = set(), []
    step = max(1, len(ms) // k)
    for m in ms[::step] + ms:
        if m["author"] in seen: continue
        seen.add(m["author"]); out.append(m)
        if len(out) >= k: break
    return sorted(out, key=lambda m: m["month"])

os.makedirs(f"{D}/batches", exist_ok=True)
os.makedirs(f"{D}/labels", exist_ok=True)
json.dump({r["asin"]: r for r in cands}, open(f"{D}/candidates.json", "w"))
for bi in range(0, len(cands), BATCH):
    with open(f"{D}/batches/b{bi//BATCH:02d}.jsonl", "w") as f:
        for r in cands[bi:bi+BATCH]:
            meta = ol.get(r["asin"])
            hint = ({"title": meta["title"] + (": " + meta["subtitle"] if meta.get("subtitle") else ""),
                     "authors": meta["authors"][:3], "year": meta["year"], "subjects": meta["subjects"][:5]}
                    if meta else {"url_slug": r.get("slug_title")})
            f.write(json.dumps({"asin": r["asin"], "known": hint,
                "stats": {k: r[k] for k in ["n_authors", "n_months", "first", "last", "top_author_share"]},
                "comments": [{"id": m["id"], "by": m["author"], "mo": m["month"],
                              "story": (m["story_title"] or "")[:90], "text": snippet(m, r["editions"])}
                             for m in pick(r["mentions"])]}, ensure_ascii=False) + "\n")
print("batches:", len(os.listdir(f"{D}/batches")))
