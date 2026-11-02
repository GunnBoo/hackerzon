import json, sys
ids = {o["id"] for o in (json.loads(l) for l in open(sys.argv[1]) if l.strip()) if "id" in o}
errs = []; n = 0; items = 0
try:
    for i, l in enumerate(open(sys.argv[2])):
        if not l.strip(): continue
        o = json.loads(l); n += 1
        if o.get("id") not in ids: errs.append(f"line {i+1}: id {o.get('id')!r} not in input")
        its = o.get("items")
        if not isinstance(its, list) or not its: errs.append(f"line {i+1}: items must be a non-empty list"); continue
        for it in its:
            items += 1
            if not isinstance(it.get("n"), str) or not it["n"].strip(): errs.append(f"line {i+1}: empty name")
            if it.get("k") not in ("book", "product", "media"): errs.append(f"line {i+1}: bad k {it.get('k')!r}")
            if it.get("s") not in ("rec", "neg", "other"): errs.append(f"line {i+1}: bad s {it.get('s')!r}")
            if not isinstance(it.get("by", ""), str): errs.append(f"line {i+1}: by must be a string")
except Exception as e:
    print("INVALID JSON:", e); sys.exit(1)
if n == 0: errs.append("no output lines")
print("\n".join(errs[:50]) if errs else f"OK ({n} comments, {items} items)")
sys.exit(1 if errs else 0)
