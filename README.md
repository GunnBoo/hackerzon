# Hackerzon

An Amazon-style store that only carries products Hacker News commenters have recommended to each other again and again over 20 years. No sponsored results, ads, upsells, Subscribe & Save or affiliate tags.

It answers [this reply](https://x.com/tylerpalmer/status/2116960851634893052) to Karpathy's [HackerTube post](https://x.com/karpathy/status/2116957135661945283): "now do Amazon and remove sponsored posts, ads, upsells, and subscribe and save for everything".

**Live:** https://gunnboo.github.io/hackerzon/

**Data:** [hackerzon-data.zip](https://github.com/GunnBoo/hackerzon/releases/latest/download/hackerzon-data.zip) (every product and HN comment, with a [DATA.md](DATA.md) written for agents)

## Run it

```bash
python3 -m http.server 8765 --directory site
```

Then open http://localhost:8765. It's a static site (plain HTML/CSS/JS, no build step), so any static host works.

## How the data was made

Same recipe as HackerTube, from three sources:

1. **Amazon links.** `pipeline/fetch.py` pulls every HN comment with an Amazon link from the public Algolia HN API (61k comments, 2007–2026). `pipeline/extract.py` regexes out product IDs (ASINs); `pipeline/openlibrary.py` merges editions of the same book.
2. **Other store links.** `pipeline/fetch.py data/raw/stores.jsonl "goodreads.com,oreilly.com,..."` pulls comments linking Goodreads, O'Reilly, MIT Press, Manning, Pragmatic Bookshelf, No Starch, Bookshop.org and others; `pipeline/extract_stores.py` pulls their IDs. Books with an ISBN map straight to the Amazon item.
3. **Products named without a link.** `pipeline/fetch_threads.py` downloads ~1,200 "Ask HN" recommendation threads (best purchases, books that changed you, desk setups). Claude Haiku agents (instructions in `pipeline/EXTRACT.md`, checked by `pipeline/validate_extract.py`) list every book/product each top-level answer names, with its stance.

Then:

4. `pipeline/merge_all.py` joins the three sources (by ASIN/ISBN, then title + author) and applies the cut: at least 3 different people in at least 3 different months. Items found only by name need at least 4 people actually recommending them.
5. Claude Sonnet agents (`pipeline/TASK.md`, checked by `pipeline/validate.py`) read sample comments per item, label each comment's stance, drop self-promotion/jokes/non-products, and write the title, category, summary and "why HN recommends it".
6. `pipeline/covers.py` finds Open Library covers for books without an ISBN; `pipeline/build.py` ranks items by roughly how many different months they were recommended in (each person counts for at most 2 months) and writes `site/data/`.
7. `pipeline/bundle.py` packages `dist/` for publishing as a claude.ai artifact (covers inlined, files sharded); `pipeline/export_data.py` writes the data zip.

The public site is `site/`, deployed to GitHub Pages by `.github/workflows/pages.yml` on every push to `main`. The working data (`data/`, ~330 MB) isn't in the repo; the release zip has the finished dataset. [hackerzon-pipeline-work.zip](https://github.com/GunnBoo/hackerzon/releases/download/data-2026-11/hackerzon-pipeline-work.zip) holds the agents' raw outputs (label batches, Ask HN extractions, image credits), so the store can be rebuilt without re-running them; the raw HN comments can be re-fetched with `pipeline/fetch.py` and `pipeline/fetch_threads.py`.

To rebuild after changing labels:

```bash
python3 pipeline/merge_all.py z && python3 pipeline/covers.py && python3 pipeline/build.py data site/data && python3 pipeline/bundle.py
```

## Notes

- Images load from Amazon by product ID, falling back to Open Library covers and then a drawn cover.
- Items with no Amazon listing link to a plain Amazon search (no affiliate tag), plus the store HN linked (Manning, O'Reilly, ...).
- No accounts: your list, likes and history live in the browser's localStorage.
- Not affiliated with Amazon, Hacker News or Y Combinator.
