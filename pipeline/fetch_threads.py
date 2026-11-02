"""Fetch full comment trees for Ask HN recommendation threads (Algolia items API).
Keeps top-level answers plus direct replies that themselves recommend (depth<=2)."""
import json, sys, time, html, re, urllib.request, concurrent.futures as cf
threads = json.load(open(sys.argv[1])); OUT = sys.argv[2]
TAG = re.compile(r"<[^>]+>")
def clean(t): return html.unescape(TAG.sub("", (t or "").replace("<p>", "\n\n"))).strip()
def get(i):
    for a in range(4):
        try:
            with urllib.request.urlopen(f"https://hn.algolia.com/api/v1/items/{i}", timeout=90) as r: return json.load(r)
        except Exception: time.sleep(3 + 4 * a)
    return None
def walk(t):
    d = get(t["id"])
    out = []
    if not d: return out
    for c in d.get("children", []):
        if c.get("author") and c.get("text"):
            out.append({"id": str(c["id"]), "author": c["author"], "created_at_i": c["created_at_i"], "depth": 1,
                        "story_id": t["id"], "story_title": t["title"], "text": clean(c["text"])})
        for r in c.get("children", []):
            if r.get("author") and r.get("text"):
                out.append({"id": str(r["id"]), "author": r["author"], "created_at_i": r["created_at_i"], "depth": 2,
                            "story_id": t["id"], "story_title": t["title"], "text": clean(r["text"])})
    return out
n = 0
with open(OUT, "w") as f, cf.ThreadPoolExecutor(6) as ex:
    for i, rows in enumerate(ex.map(walk, threads)):
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n"); n += 1
        if i % 100 == 0: print(i, n, flush=True)
print("done", n)
