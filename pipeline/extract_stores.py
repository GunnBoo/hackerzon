"""Pull product identifiers out of HN comments that link other stores/publishers.
Books with an ISBN are keyed by ISBN-10 (= Amazon ASIN), so they merge with Amazon items.
Usage: python3 extract_stores.py raw/stores.jsonl out.jsonl"""
import json, re, sys, html, datetime, collections
src, out = sys.argv[1], sys.argv[2]
TAG = re.compile(r"<[^>]+>")

def isbn10(s):
    s = s.replace("-", "").upper()
    if re.fullmatch(r"\d{9}[\dX]", s):
        tot = sum((10 - i) * (10 if ch == "X" else int(ch)) for i, ch in enumerate(s))
        return s if tot % 11 == 0 and not s.startswith("0636920") else None
    if re.fullmatch(r"978\d{10}", s):
        core = s[3:12]
        tot = sum((10 - i) * int(d) for i, d in enumerate(core))
        c = (11 - tot % 11) % 11
        return core + ("X" if c == 10 else str(c))
    return None

def slug(s): return re.sub(r"[-_+]+", " ", s or "").strip() or None
GENERIC = {"catalog", "about", "books", "search", "store", "faq", "contact", "blog", "categories", "subjects", "cart", "account", "help", "free", "meap", "index", "titles", "category", "ebooks", "sale", "book", "books", "product", "catalog"}
PATTERNS = [
    (r"goodreads\.com/(?:en/)?book/show/(\d+)(?:[.-]([A-Za-z0-9_\-]+))?", lambda m: ("gr:" + m[1], None, slug(m[2]), "book")),
    (r"oreilly\.com/library/view/([a-z0-9-]+)/((?:97[89])?\d{9}[\dX])", lambda m: ("isbn", isbn10(m[2]), slug(m[1]), "book")),
    (r"oreilly\.com/(?:catalog|product)/((?:97[89])?\d{9}[\dX])", lambda m: ("isbn", isbn10(m[1]), None, "book")),
    (r"oreilly\.com/(?:catalog|library/view)/([a-z0-9-]+)", lambda m: ("or:" + m[1], None, slug(m[1]), "book")),
    (r"pragprog\.com/(?:titles|book)/([a-z0-9]+)(?:/([a-z0-9-]+))?", lambda m: ("pp:" + m[1], None, slug(m[2]), "book")),
    (r"manning\.com/(?:books/)?([a-z0-9][a-z0-9-]{3,})", lambda m: ("mn:" + m[1], None, slug(m[1]), "book")),
    (r"nostarch\.com/([a-z0-9][a-z0-9-]{3,})", lambda m: ("ns:" + m[1], None, slug(m[1]), "book")),
    (r"mitpress\.mit\.edu/(?:books/|\d{13}/)([a-z0-9-]{4,})", lambda m: ("mit:" + m[1], None, slug(m[1]), "book")),
    (r"mitpress\.mit\.edu/(97[89]\d{10})", lambda m: ("isbn", isbn10(m[1]), None, "book")),
    (r"bookshop\.org/[^\s\"<>]*?(97[89]\d{10})", lambda m: ("isbn", isbn10(m[1]), None, "book")),
    (r"press\.princeton\.edu/books/[a-z]+/(97[89]\d{10})(?:/([a-z0-9-]+))?", lambda m: ("isbn", isbn10(m[1]), slug(m[2]), "book")),
    (r"cambridge\.org/core/books/([a-z0-9-]{6,})", lambda m: ("cam:" + m[1], None, slug(m[1]), "book")),
    (r"springer\.com/(?:gp/)?book/(97[89][\d-]{10,14})", lambda m: ("isbn", isbn10(m[1]), None, "book")),
    (r"abebooks\.[a-z.]+/[^\s\"<>]*?(?:isbn=|/)(97[89]\d{10}|\d{9}[\dX])", lambda m: ("isbn", isbn10(m[1]), None, "book")),
    (r"bhphotovideo\.com/c/product/(\d+)-[A-Z]+/([a-z0-9_-]+)", lambda m: ("bh:" + m[1], None, slug(m[2]), "product")),
    (r"etsy\.com/(?:[a-z]{2}/)?listing/(\d+)(?:/([a-z0-9-]+))?", lambda m: ("etsy:" + m[1], None, slug(m[2]), "product")),
]
PATTERNS = [(re.compile(p, re.I), f) for p, f in PATTERNS]
items = collections.defaultdict(lambda: {"mentions": {}, "slugs": collections.Counter(), "kind": None, "src": collections.Counter()})
for line in open(src):
    c = json.loads(line)
    # match only full link targets; HN truncates long URLs in the visible text
    raw = " ".join(html.unescape(h) for h in re.findall(r'href="([^"]+)"', c.get("comment_text") or ""))
    found = {}
    for rx, f in PATTERNS:
        for m in rx.finditer(raw):
            key, isbn, title, kind = f(m)
            if key == "isbn":
                if not isbn: continue
                key = isbn
            elif key.split(":", 1)[1].lower() in GENERIC: continue
            found.setdefault(key, (title, kind, rx.pattern.split("\\.")[0].split("(")[-1]))
    if not found: continue
    text = html.unescape(TAG.sub("", c["comment_text"].replace("<p>", "\n\n"))).strip()
    mo = datetime.datetime.utcfromtimestamp(c["created_at_i"]).strftime("%Y-%m")
    for key, (title, kind, site) in found.items():
        it = items[key]
        if title: it["slugs"][title] += 1
        it["kind"] = kind; it["src"][site] += 1
        it["mentions"][c["objectID"]] = {"id": c["objectID"], "author": c["author"], "month": mo, "story_id": c.get("story_id"),
            "story_title": c.get("story_title"), "n_links": len(found), "text": text[:2500], "via": site}
with open(out, "w") as f:
    for k, it in items.items():
        ms = sorted(it["mentions"].values(), key=lambda m: m["month"])
        f.write(json.dumps({"key": k, "slug_title": it["slugs"].most_common(1)[0][0] if it["slugs"] else None, "kind": it["kind"],
            "src": dict(it["src"]), "n_authors": len({m["author"] for m in ms}), "n_months": len({m["month"] for m in ms}), "mentions": ms}) + "\n")
print("items", len(items), "isbn-keyed", sum(1 for k in items if ":" not in k))
