"""Package the store's data as one zip (like HackerTube's download), with readable field names.
Usage: python3 pipeline/export_data.py  -> export/hackerzon-data.zip"""
import json, os, zipfile, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE, OUT = f"{ROOT}/site/data", f"{ROOT}/export"
os.makedirs(OUT, exist_ok=True)
prods = json.load(open(f"{SITE}/products.json"))
stats = json.load(open(f"{SITE}/stats.json"))
STANCE = {"rec": "recommends", "cite": "cites", "neg": "criticizes", "joke": "joke", "self": "self_promotion", "other": "other", None: None}
def product_row(p):
    return {"id": p["a"], "rank": p["rk"], "title": p["t"], "by": p["by"], "kind": p["k"], "department": p["d"], "category": p["sub"],
            "summary": p["s"], "why_hn_recommends": p["w"], "about": p["ab"], "quote": p["q"], "tags": p["tg"],
            "aged": p["aged"], "hidden_gem": p["gem"], "hns_choice": p.get("hc", False),
            "score": p["sc"], "positive_share": p["r"], "n_recommenders": p["na"], "n_months": p["nm"], "n_comments": p["n"],
            "first_month": p["f"], "last_month": p["l"], "comments_per_year": p["y"],
            "asin": p.get("amz"), "other_editions": p.get("ed", []), "amazon_url": f"https://www.amazon.com/dp/{p['amz']}" if p.get("amz") else None,
            "store_links": p.get("lk", {}), "found_via": p.get("src", []), "openlibrary_cover_id": p.get("oc"),
            "also_recommended": p.get("rel", [])}
zp = f"{OUT}/hackerzon-data.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    z.writestr("products.jsonl", "".join(json.dumps(product_row(p), ensure_ascii=False) + "\n" for p in prods))
    lines = []
    for p in prods:
        for m in json.load(open(f"{SITE}/m/{p['a']}.json")):
            lines.append(json.dumps({"product_id": p["a"], "comment_id": m["id"], "author": m["u"], "month": m["mo"],
                "story_id": m.get("sid"), "story_title": m.get("stt"), "stance": STANCE.get(m.get("s")), "found_via": m.get("v", "amazon"),
                "hn_url": f"https://news.ycombinator.com/item?id={m['id']}", "text": m["x"]}, ensure_ascii=False) + "\n")
    z.writestr("mentions.jsonl", "".join(lines))
    z.writestr("stats.json", json.dumps(stats, indent=1))
    z.write(f"{ROOT}/DATA.md", "DATA.md")
    for f in ["TASK.md", "EXTRACT.md"]:
        z.write(f"{ROOT}/pipeline/{f}", f"prompts/{f}")
print(zp, round(os.path.getsize(zp) / 1e6, 1), "MB;", len(prods), "products,", len(lines), "mentions")
