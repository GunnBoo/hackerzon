"""Package the site for publishing as a claude.ai artifact.
The artifact sandbox blocks images from other hosts and caps the file count, so:
- covers are downloaded once, shrunk, and shipped as data: URIs in ~17 shard files
- per-product comment files are packed into the same ~17 shards
- CSS and JS are inlined into one page
Usage: python3 bundle.py   (reads site/, writes dist/)"""
import json, os, io, base64, re, shutil, urllib.request, concurrent.futures as cf
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE, DIST, CACHE = f"{ROOT}/site", f"{ROOT}/dist", f"{ROOT}/data/imgcache"
SHARD = 100
os.makedirs(CACHE, exist_ok=True)
prods = json.load(open(f"{SITE}/data/products.json"))

def sources(p):
    out = [f"https://m.media-amazon.com/images/P/{a}.01._SCLZZZZZZZ_.jpg" for a in [p["amz"], *p.get("ed", [])][:3]] if p.get("amz") else []
    if p.get("isbn"): out.append(f"https://covers.openlibrary.org/b/isbn/{p['amz']}-L.jpg?default=false")
    if p.get("oc"): out.append(f"https://covers.openlibrary.org/b/id/{p['oc']}-L.jpg?default=false")
    return out

def fetch(p):
    path = f"{CACHE}/{p['a']}.jpg"
    miss = path + ".none"
    if os.path.exists(path) or os.path.exists(miss): return
    for url in sources(p):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                b = r.read()
            if len(b) < 1000: continue  # Amazon's 1x1 "no image" gif
            Image.open(io.BytesIO(b)).verify()
            open(path, "wb").write(b); return
        except Exception:
            continue
    open(miss, "w").close()

with cf.ThreadPoolExecutor(16) as ex:
    list(ex.map(fetch, prods))
have = sum(os.path.exists(f"{CACHE}/{p['a']}.jpg") for p in prods)
print(f"covers: {have}/{len(prods)}")

def thumb(a):
    path = f"{CACHE}/{a}.jpg"
    if not os.path.exists(path): return None
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((240, 240))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=62, optimize=True, progressive=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None

if os.path.exists(DIST): shutil.rmtree(DIST)
os.makedirs(f"{DIST}/data/ms"); os.makedirs(f"{DIST}/data/img")
shards = {}
for p in prods:
    p["sh"] = (p["rk"] - 1) // SHARD
    shards.setdefault(p["sh"], []).append(p["a"])
for k, asins in shards.items():
    ms = {a: json.load(open(f"{SITE}/data/m/{a}.json")) for a in asins}
    json.dump(ms, open(f"{DIST}/data/ms/{k}.json", "w"), ensure_ascii=False, separators=(",", ":"))
    imgs = {a: t for a in asins if (t := thumb(a))}
    json.dump(imgs, open(f"{DIST}/data/img/{k}.json", "w"), separators=(",", ":"))
json.dump(prods, open(f"{DIST}/data/products.json", "w"), ensure_ascii=False, separators=(",", ":"))
shutil.copy(f"{SITE}/data/stats.json", f"{DIST}/data/stats.json")

# one page: inline CSS + JS, no html/head/body wrapper (the artifact host adds it)
html = open(f"{SITE}/index.html").read()
css = open(f"{SITE}/style.css").read()
js = open(f"{SITE}/app.js").read()
body = re.search(r"<body>(.*)</body>", html, re.S).group(1)
body = re.sub(r'<script src="app\.js[^"]*"></script>', "", body)
icon = re.search(r'<link rel="icon"[^>]*>', html).group(0)
page = (f"<title>Hackerzon</title>\n<style>\n{css}\n</style>\n{body.strip()}\n"
        f"<script>window.HZ_BUNDLE = true;</script>\n<script>\n{js}\n</script>\n")
open(f"{DIST}/index.html", "w").write(page)
sizes = sorted((os.path.getsize(os.path.join(dp, f)), os.path.join(dp, f)[len(DIST)+1:]) for dp, _, fs in os.walk(DIST) for f in fs)
print("files:", len(sizes), "total MB:", round(sum(s for s, _ in sizes) / 1e6, 1), "largest:", sizes[-3:])
