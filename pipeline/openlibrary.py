"""Look up ISBN-10 ASINs on Open Library: title, authors, work key (to merge editions), subjects, cover."""
import json, sys, re, urllib.request, time, concurrent.futures as cf
src, out = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(src)]
cand = [r["asin"] for r in rows if r["n_authors"] >= 3 and r["n_months"] >= 3 and re.fullmatch(r"\d{9}[\dX]", r["asin"])]
print("isbn candidates", len(cand))
def fetch(chunk):
    keys = ",".join("ISBN:" + a for a in chunk)
    url = f"https://openlibrary.org/api/books?bibkeys={keys}&format=json&jscmd=data"
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r: return json.load(r)
        except Exception: time.sleep(3 + i * 4)
    return {}
def fetch_works(chunk):
    keys = ",".join("ISBN:" + a for a in chunk)
    url = f"https://openlibrary.org/api/books?bibkeys={keys}&format=json&jscmd=details"
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r: return json.load(r)
        except Exception: time.sleep(3 + i * 4)
    return {}
chunks = [cand[i:i+40] for i in range(0, len(cand), 40)]
res = {}
with cf.ThreadPoolExecutor(4) as ex:
    for d, w in zip(ex.map(fetch, chunks), ex.map(fetch_works, chunks)):
        for k, v in d.items():
            a = k.split(":")[1]
            det = (w.get(k) or {}).get("details", {})
            works = det.get("works") or []
            res[a] = {"title": v.get("title"), "subtitle": v.get("subtitle"),
                      "authors": [x["name"] for x in v.get("authors", [])],
                      "year": v.get("publish_date"), "pages": v.get("number_of_pages"),
                      "subjects": [s["name"] for s in v.get("subjects", [])][:8],
                      "cover": bool(v.get("cover")),
                      "work": works[0]["key"] if works else None}
json.dump(res, open(out, "w"))
print("found", len(res), "with work key", sum(1 for v in res.values() if v["work"]))
