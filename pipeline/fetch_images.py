"""Find pictures for items that have none, and host them with the site (site/img/).
Books: Google Books cover, then Open Library title search.
Products/media: the lead photo of the matching Wikipedia article, only if it is a freely
licensed file on Wikimedia Commons (no logos/SVGs, no fair-use files). Credits go to data/imgcredits.json."""
import json, os, re, io, time, urllib.request, urllib.parse, concurrent.futures as cf
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = {p["a"]: p for p in json.load(open(f"{ROOT}/site/data/products.json"))}
todo = [] if __name__ != "__main__" else [a for a in json.load(open(f"{ROOT}/data/noimg.json")) if a in P]
OUT = f"{ROOT}/site/img"; os.makedirs(OUT, exist_ok=True)
CRED = f"{ROOT}/data/imgcredits.json"
credits = json.load(open(CRED)) if os.path.exists(CRED) else {}
UA = {"User-Agent": "Hackerzon/1.0 (https://github.com/Boo-Geonhyeok/hackerzon; image lookup)"}
FREE = re.compile(r"^(cc[ -]?by|cc[ -]?zero|cc0|public domain|pd|gfdl|attribution|no restrictions)", re.I)

def get(url, as_json=True, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                b = r.read()
            return json.loads(b) if as_json else b
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None
def fname(a): return re.sub(r"[^A-Za-z0-9._-]", "_", a) + ".jpg"
def save(a, b):
    im = Image.open(io.BytesIO(b)).convert("RGB")
    if min(im.size) < 60: return False
    im.thumbnail((360, 360))
    im.save(f"{OUT}/{fname(a)}", "JPEG", quality=78, optimize=True, progressive=True)
    return True
def words(s): return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 1}
def last(by): w = re.findall(r"[A-Za-z]+", (by or "").split(",")[0].split(" and ")[0]); return w[-1] if w else ""

def book(p):
    title = re.split(r"[:(]", p["t"])[0].strip()
    q = f'intitle:"{title}"' + (f' inauthor:"{last(p["by"])}"' if last(p["by"]) else "")
    d = get("https://www.googleapis.com/books/v1/volumes?" + urllib.parse.urlencode({"q": q, "maxResults": 5, "printType": "books"}))
    for it in (d or {}).get("items", []):
        il = it.get("volumeInfo", {}).get("imageLinks", {})
        u = il.get("thumbnail") or il.get("smallThumbnail")
        if not u: continue
        u = u.replace("http://", "https://").replace("&edge=curl", "")
        b = get(u, as_json=False)
        if b and len(b) > 3000 and save(p["a"], b):
            return {"src": "Google Books", "url": it.get("volumeInfo", {}).get("infoLink", "")}
    d = get("https://openlibrary.org/search.json?" + urllib.parse.urlencode({"title": title, "author": last(p["by"]), "limit": 3, "fields": "cover_i,key"}))
    for doc in (d or {}).get("docs", []):
        if doc.get("cover_i"):
            b = get(f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg?default=false", as_json=False)
            if b and save(p["a"], b):
                return {"src": "Open Library", "url": f"https://openlibrary.org{doc.get('key','')}"}
    return None

def product(p):
    name = re.sub(r"\(.*?\)", "", p["t"]).strip()
    q = name if (p["by"] or "").split()[0:1] and name.lower().startswith((p["by"] or "").lower()) else f"{p['by']} {name}".strip()
    d = get("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "generator": "search", "gsrsearch": q, "gsrlimit": 4,
            "prop": "pageimages", "piprop": "name", "format": "json"}))
    pages = sorted((d or {}).get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 9))
    key = words(name) - words(p["by"]) or words(name)
    for pg in pages:
        img = pg.get("pageimage")
        if not img or img.lower().endswith((".svg", ".gif")) or "logo" in img.lower(): continue
        if not (key & words(pg["title"])): continue          # article must be about this product
        info = get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "titles": f"File:{img}", "prop": "imageinfo",
                   "iiprop": "url|extmetadata", "iiurlwidth": 400, "format": "json"}))
        fp = next(iter((info or {}).get("query", {}).get("pages", {}).values()), {})
        if "imageinfo" not in fp: continue                    # not on Commons -> likely non-free
        ii = fp["imageinfo"][0]; md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        if not FREE.search(lic): continue
        b = get(ii.get("thumburl") or ii["url"], as_json=False)
        if b and save(p["a"], b):
            artist = re.sub(r"<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()[:80]
            return {"src": "Wikimedia Commons", "url": ii.get("descriptionurl", ""), "license": lic, "artist": artist, "article": pg["title"]}
    return None

def run(a):
    if a in credits: return a, credits[a]
    p = P[a]
    try:
        c = book(p) if p["k"] == "book" else product(p)
        if not c and p["k"] != "book": c = None
        if not c and p["k"] == "media": c = book(p) if False else None
    except Exception as e:
        c = None
    return a, c
found = 0
if __name__ == "__main__":
  with cf.ThreadPoolExecutor(6) as ex:
      for a, c in ex.map(run, todo):
          if c: credits[a] = c; found += 1
  json.dump(credits, open(CRED, "w"), indent=1)
  print(f"pictures found {found} / {len(todo)}")
