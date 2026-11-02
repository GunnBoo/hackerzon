"""Products still without a picture: search Wikimedia Commons files directly.
A file counts only if its name contains every distinctive word of the product name, and its license is free."""
import json, os, re, sys, urllib.parse, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_images as F
GENERIC = {"wireless","professional","mechanical","keyboard","mouse","ergonomic","headphones","noise","cancelling","canceling","chair","office",
           "tablet","paper","laptop","edition","series","usb","the","with","and","for","set","kit","smart","portable","adapter","maker","coffee"}
todo = [a for a in json.load(open(os.path.join(os.path.dirname(F.CRED), "noimg.json"))) if a in F.P and a not in F.credits and F.P[a]["k"] == "product"]
def toks(s): return [w for w in re.findall(r"[a-z0-9]+", (s or "").lower())]
def run(a):
    p = F.P[a]
    name = re.sub(r"\(.*?\)", "", p["t"]).strip()
    need = [w for w in toks(name) if w not in GENERIC] or toks(name)
    if not need: return a, None
    q = " ".join(need[:5])
    d = F.get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "list": "search", "srnamespace": 6, "srsearch": q, "srlimit": 15, "format": "json"}), tries=2)
    for hit in (d or {}).get("query", {}).get("search", []):
        title = hit["title"]
        if not title.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) or "logo" in title.lower(): continue
        ft = set(toks(title))
        if not all(w in ft for w in need): continue
        info = F.get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 400, "format": "json"}), tries=2)
        fp = next(iter((info or {}).get("query", {}).get("pages", {}).values()), {})
        if "imageinfo" not in fp: continue
        ii = fp["imageinfo"][0]; md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        if not F.FREE.search(lic): continue
        b = F.get(ii.get("thumburl") or ii["url"], as_json=False, tries=2)
        if b and F.save(a, b):
            artist = re.sub(r"<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()[:80]
            return a, {"src": "Wikimedia Commons", "url": ii.get("descriptionurl", ""), "license": lic, "artist": artist, "article": title}
    return a, None
n = 0
with cf.ThreadPoolExecutor(3) as ex:
    for a, c in ex.map(run, todo):
        if c: F.credits[a] = c; n += 1; print(f"  {F.P[a]['t'][:50]:50} <- {c['article'][:60]}")
json.dump(F.credits, open(F.CRED, "w"), indent=1)
print(f"found {n} / {len(todo)}")
