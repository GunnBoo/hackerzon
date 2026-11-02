import json, sys
DEPTS = {"Programming","Computer Science & Math","Science & Engineering","Business & Startups","Economics & Finance",
 "History & Biography","Psychology & Self-Help","Philosophy & Society","Fiction & Sci-Fi","Design, Writing & Art",
 "Food, Health & Home","Computers & Accessories","Electronics & Gadgets","Maker & Tools","Home & Kitchen",
 "Health & Personal Care","Outdoors & Travel","Office & School","Toys, Games & Kids","Movies, Music & Games"}
inp = [json.loads(l) for l in open(sys.argv[1])]
errs = []
try:
    out = [json.loads(l) for l in open(sys.argv[2]) if l.strip()]
except Exception as e:
    print("INVALID JSON:", e); sys.exit(1)
if len(out) != len(inp): errs.append(f"line count {len(out)} != {len(inp)}")
byid = {o.get("a"): o for o in out}
for r in inp:
    o = byid.get(r["asin"])
    if not o: errs.append(f"{r['asin']}: missing"); continue
    if not isinstance(o.get("keep"), bool): errs.append(f"{r['asin']}: keep not bool")
    if o.get("keep"):
        for k in ["t","by","dept","sub","kind","s","w","about","tags","gem","aged","st"]:
            if k not in o: errs.append(f"{r['asin']}: missing {k}")
        if o.get("dept") not in DEPTS: errs.append(f"{r['asin']}: bad dept {o.get('dept')!r}")
        if o.get("kind") not in ("book","product","media"): errs.append(f"{r['asin']}: bad kind")
        if o.get("aged") not in ("timeless","still useful","dated","historical"): errs.append(f"{r['asin']}: bad aged")
        q = o.get("q")
        if q:
            src = {c["id"]: c["text"] for c in r["comments"]}
            if q.get("id") not in src: errs.append(f"{r['asin']}: quote id not in comments")
            elif q.get("t","") not in src[q["id"]]: errs.append(f"{r['asin']}: quote is not verbatim from comment {q['id']}")
    st = o.get("st") or {}
    missing = [c["id"] for c in r["comments"] if c["id"] not in st]
    if missing: errs.append(f"{r['asin']}: st missing ids {missing}")
    bad = [v for v in st.values() if v not in ("rec","cite","neg","joke","self","other")]
    if bad: errs.append(f"{r['asin']}: bad stance values {bad}")
print("\n".join(errs[:60]) if errs else "OK")
sys.exit(1 if errs else 0)
