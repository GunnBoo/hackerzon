"""Find Open Library cover IDs for books that have no Amazon ID/ISBN (found via Ask HN or Goodreads etc.).
Writes data/olcovers.json: item id -> cover id."""
import json, glob, os, urllib.request, urllib.parse, concurrent.futures as cf
D = "data"
ents = json.load(open(f"{D}/entities.json"))
labels = {}
for fn in glob.glob(f"{D}/labels/*.jsonl") + glob.glob(f"{D}/labels2/*.jsonl"):
    for l in open(fn):
        if l.strip():
            o = json.loads(l); labels[o["a"]] = o
out = json.load(open(f"{D}/olcovers.json")) if os.path.exists(f"{D}/olcovers.json") else {}
todo = [(i, o) for i, o in labels.items() if o.get("keep") and o.get("kind") == "book" and i in ents and not ents[i].get("asin") and i not in out]
def look(item):
    i, o = item
    q = {"title": o["t"].split(":")[0], "limit": 1, "fields": "cover_i"}
    if o.get("by"): q["author"] = o["by"].split(",")[0].replace(" et al.", "")
    try:
        with urllib.request.urlopen("https://openlibrary.org/search.json?" + urllib.parse.urlencode(q), timeout=30) as r:
            d = json.load(r)
        c = (d.get("docs") or [{}])[0].get("cover_i")
        return i, c
    except Exception:
        return i, None
with cf.ThreadPoolExecutor(6) as ex:
    for i, c in ex.map(look, todo):
        if c: out[i] = c
json.dump(out, open(f"{D}/olcovers.json", "w"))
print("looked up", len(todo), "covers known", len(out))
