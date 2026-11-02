"""Retry pass for items still without a picture: slower, simpler queries."""
import json, os, re, sys, urllib.parse, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_images as F
todo = [a for a in json.load(open(os.path.join(os.path.dirname(F.CRED), "noimg.json"))) if a in F.P and a not in F.credits]
def book(p):
    title = re.split(r"[:(]|,? \d+(st|nd|rd|th) Edition|, Third Edition|, Second Edition", p["t"])[0].strip()
    title = re.sub(r"^The (.*) (Series|Saga|Chronicle)$", r"\1", title)
    for q in ({"title": title, "author": F.last(p["by"])}, {"q": f"{title} {F.last(p['by'])}".strip()}, {"title": title}):
        d = F.get("https://openlibrary.org/search.json?" + urllib.parse.urlencode({**q, "limit": 5, "fields": "cover_i,isbn,key"}), tries=2)
        for doc in (d or {}).get("docs", []):
            if doc.get("cover_i"):
                b = F.get(f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg?default=false", as_json=False, tries=2)
                if b and F.save(p["a"], b): return {"src": "Open Library", "url": f"https://openlibrary.org{doc.get('key','')}"}
            for i in [i for i in doc.get("isbn", []) if re.fullmatch(r"\d{9}[\dX]", i)][:5]:
                b = F.get(f"https://m.media-amazon.com/images/P/{i}.01._SCLZZZZZZZ_.jpg", as_json=False, tries=1)
                if b and len(b) > 1000 and F.save(p["a"], b): return {"src": "Amazon", "url": f"https://www.amazon.com/dp/{i}", "isbn": i}
    return None
def product(p):
    base = re.sub(r"\(.*?\)", "", p["t"]).strip()
    short = " ".join(base.split()[:3])
    for name in (base, short):
        q = dict(p); q["t"] = name; q["by"] = ""
        c = F.product(q)
        if c: return c
    return None
def run(a):
    p = F.P[a]
    try: return a, (book(p) if p["k"] == "book" else product(p))
    except Exception: return a, None
n = 0; got = []
with cf.ThreadPoolExecutor(2) as ex:
    for a, c in ex.map(run, todo):
        if c: F.credits[a] = c; n += 1; got.append((F.P[a]["t"][:45], c.get("article") or c["src"]))
json.dump(F.credits, open(F.CRED, "w"), indent=1)
print(f"found {n} / {len(todo)}")
for g in got:
    if g[1] not in ("Open Library", "Amazon"): print("  ", g)
