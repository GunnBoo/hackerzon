"""Pull Amazon product IDs (ASINs) out of HN comments and group them.
Usage: python3 extract.py comments.jsonl out_dir"""
import json, re, sys, html, collections, datetime, os

src, out = sys.argv[1], sys.argv[2]
ASIN_RE = re.compile(
    r'(?:amazon\.(?:com|co\.uk|ca|de|fr|in|com\.au|co\.jp)|amzn\.com)'
    r'(/[^\s"<>]*?)?/(?:dp|gp/product|gp/aw/d|exec/obidos/ASIN|exec/obidos/tg/detail/-|o/ASIN|d|product-reviews)/([A-Z0-9]{10})(?![A-Z0-9])', re.I)
SHORT_RE = re.compile(r'amzn\.com/([A-Z0-9]{10})(?![A-Z0-9])', re.I)
TAG_RE = re.compile(r'<[^>]+>')

def clean(t):
    t = t.replace('<p>', '\n\n')
    t = TAG_RE.sub('', t)
    return html.unescape(t).strip()

def slug_title(path):
    if not path: return None
    parts = [p for p in path.split('/') if p]
    for p in parts:
        if '-' in p and not p.startswith(('ref', 's?', 'gp')) and len(p) > 6:
            return p.replace('-', ' ')
    return None

prods = collections.defaultdict(lambda: {"mentions": [], "slugs": collections.Counter()})
for line in open(src):
    c = json.loads(line)
    raw = html.unescape(c.get("comment_text") or "")
    found = {}
    for m in ASIN_RE.finditer(raw):
        asin = m.group(2).upper()
        found.setdefault(asin, slug_title(m.group(1)))
    for m in SHORT_RE.finditer(raw):
        found.setdefault(m.group(1).upper(), None)
    if not found: continue
    text = clean(c["comment_text"])
    month = datetime.datetime.utcfromtimestamp(c["created_at_i"]).strftime("%Y-%m")
    for asin, slug in found.items():
        p = prods[asin]
        if slug: p["slugs"][slug] += 1
        p["mentions"].append({"id": c["objectID"], "author": c["author"], "month": month,
            "story_id": c.get("story_id"), "story_title": c.get("story_title"),
            "n_links": len(found), "text": text[:2500]})

rows = []
for asin, p in prods.items():
    ms = p["mentions"]
    authors = {m["author"] for m in ms}
    months = {m["month"] for m in ms}
    rows.append({"asin": asin, "slug_title": p["slugs"].most_common(1)[0][0] if p["slugs"] else None,
                 "n_mentions": len(ms), "n_authors": len(authors), "n_months": len(months),
                 "first": min(months), "last": max(months), "mentions": sorted(ms, key=lambda m: m["month"])})
rows.sort(key=lambda r: (-r["n_months"], -r["n_authors"]))
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, "products_all.jsonl"), "w") as f:
    for r in rows: f.write(json.dumps(r) + "\n")
print("distinct ASINs", len(rows))
for a, mo in [(2,2),(3,2),(3,3),(4,3),(5,4)]:
    print(f">= {a} authors & >= {mo} months:", sum(1 for r in rows if r["n_authors"]>=a and r["n_months"]>=mo))
for r in rows[:25]: print(r["n_months"], r["n_authors"], r["asin"], r["slug_title"])
