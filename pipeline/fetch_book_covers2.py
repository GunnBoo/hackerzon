"""Second pass for books still without a cover: get ISBNs from Open Library search, then try Amazon's cover for each ISBN-10."""
import json, os, re, urllib.parse, concurrent.futures as cf, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_images import P, credits, CRED, get, save, last
todo = [a for a in json.load(open(os.path.join(os.path.dirname(CRED), "noimg.json"))) if a in P and a not in credits and P[a]["k"] == "book"]
def run(a):
    p = P[a]; title = re.split(r"[:(]", p["t"])[0].strip()
    d = get("https://openlibrary.org/search.json?" + urllib.parse.urlencode({"title": title, "author": last(p["by"]), "limit": 3, "fields": "isbn,key,title"}))
    for doc in (d or {}).get("docs", []):
        isbns = [i for i in doc.get("isbn", []) if re.fullmatch(r"\d{9}[\dX]", i)][:8]
        for i in isbns:
            b = get(f"https://m.media-amazon.com/images/P/{i}.01._SCLZZZZZZZ_.jpg", as_json=False, tries=1)
            if b and len(b) > 1000:
                try:
                    if save(a, b): return a, {"src": "Amazon", "url": f"https://www.amazon.com/dp/{i}", "isbn": i}
                except Exception: pass
    return a, None
n = 0
with cf.ThreadPoolExecutor(6) as ex:
    for a, c in ex.map(run, todo):
        if c: credits[a] = c; n += 1
json.dump(credits, open(CRED, "w"), indent=1)
print(f"book covers found {n} / {len(todo)}")
