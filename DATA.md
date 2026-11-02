# Hackerzon data

The products Hacker News commenters kept recommending to each other, 2007–2026, as plain JSON lines.
This is the data behind https://gunnboo.github.io/hackerzon/. Give the zip to your agent and ask for your own version:
a different store, a weekly email of picks in your topics, a terminal browser, an analysis.

## Files

| File | What it is |
|---|---|
| `products.jsonl` | One line per store item (2,861). Title, author/brand, category, Claude-written summary and "why HN recommends it", stats, links. |
| `mentions.jsonl` | One line per HN comment that recommended, cited or named an item (~38k), with the comment text and a link back to HN. |
| `stats.json` | Totals: comments scanned per source, threads read, date range. |
| `prompts/TASK.md` | The instructions Claude Sonnet followed to label comments and write product cards. |
| `prompts/EXTRACT.md` | The instructions Claude Haiku followed to pull product names out of Ask HN answers. |

`mentions.jsonl` joins to `products.jsonl` on `product_id` = `id`.

## How it was made

1. **Amazon links.** Every HN comment containing an Amazon link (61k, via the public Algolia HN API). Product IDs (ASINs) pulled out with regexes; book editions merged via Open Library.
2. **Other store links.** Comments linking Goodreads, O'Reilly, MIT Press, Manning, Pragmatic Bookshelf, No Starch, Bookshop.org, Princeton/Cambridge UP, Springer and AbeBooks (19k). Books with an ISBN are matched to their Amazon listing (ISBN-10 = ASIN).
3. **Named without a link.** 53k top-level answers in 1,208 "Ask HN" recommendation threads ("What sub-$200 product improved your life?", "Books that changed how you think"). Claude Haiku listed every book or product each answer names and whether it recommends it.
4. **Merge and cut.** Sources joined by ASIN/ISBN, then by title + author (or brand). An item makes the cut if at least 3 different people mentioned it in at least 3 different months. Items found only by name (Ask HN, Goodreads) need at least 4 different people *recommending* it.
5. **Read and label.** Claude Sonnet read up to 8 comments per item, labeled each comment's stance, dropped self-promotion, jokes, unidentifiable items and software, and wrote the card text.
6. **Rank.** `score` ≈ number of different months someone recommended the item, with each person counting for at most 2 months, times the share of positive comments.

## products.jsonl fields

| Field | Meaning |
|---|---|
| `id` | Item ID. An ASIN (`0735611319`), `n-…` for items found only by name, `s-…` for items found via another store. |
| `rank` | Position by `score`, 1 = most recommended. |
| `title`, `by` | Display title; author(s) for books, brand for products. |
| `kind` | `book`, `product` or `media`. |
| `department`, `category` | Store department and sub-category (fixed list, see `prompts/TASK.md`). |
| `summary` | One factual sentence on what it is (Claude-written). |
| `why_hn_recommends` | What the comments say about why it's good (Claude-written). |
| `about` | 3 short bullets: who it's for, what you get, caveats HN raised. |
| `quote` | `{id, t}`: a verbatim excerpt from comment `id`. |
| `tags` | 2–5 topic tags. |
| `aged` | `timeless`, `still useful`, `dated` or `historical` (Claude's judgment, Nov 2026). |
| `hidden_gem` | Claude judged it niche, and HN's comments are mostly positive. |
| `hns_choice` | Top item in its category. |
| `score`, `positive_share` | See "Rank" above. `positive_share` = recommends + ½·cites over labeled comments. |
| `n_recommenders`, `n_months`, `n_comments` | Distinct HN users, distinct months, total comments. |
| `first_month`, `last_month`, `comments_per_year` | When HN talked about it. |
| `asin`, `amazon_url`, `other_editions` | Amazon product ID if known (null for name-only items). |
| `store_links` | Other stores HN linked, e.g. `{"Manning": "https://…"}`. |
| `found_via` | Sources, most common first: `amazon`, `askhn`, `goodreads`, `oreilly`, `mitpress`, … |
| `openlibrary_cover_id` | For books without an ISBN: `https://covers.openlibrary.org/b/id/<id>-L.jpg`. |
| `also_recommended` | Up to 12 item IDs recommended by the same people or in the same comments. |

## mentions.jsonl fields

| Field | Meaning |
|---|---|
| `product_id` | Joins to `products.jsonl` `id`. |
| `comment_id`, `hn_url` | The HN comment. |
| `author`, `month` | HN username and `YYYY-MM`. |
| `story_id`, `story_title` | The thread it was posted in. |
| `stance` | `recommends`, `cites`, `criticizes`, `joke`, `self_promotion`, `other`, or null if no model read it. |
| `found_via` | Which source matched this comment to the item. |
| `text` | Comment text (HTML stripped, up to 3,000 characters). |

## Gotchas

- Labels and card text are an AI model's reading of a sample of comments. They can be wrong; the comments are the ground truth.
- Name matching is imperfect: a few items are split across editions or model years, and a generic name ("MacBook Pro") absorbs mentions of several generations.
- An Ask HN answer that lists ten books counts as a mention for each of them.
- No prices or Amazon descriptions are included. Amazon's metadata isn't ours to redistribute; every Amazon item has its ASIN so you can look it up.

## Example

```python
import json
P = [json.loads(l) for l in open("products.jsonl")]
M = [json.loads(l) for l in open("mentions.jsonl")]
keyboards = [p for p in P if "keyboard" in p["title"].lower()]
for p in sorted(keyboards, key=lambda p: -p["score"])[:5]:
    recs = [m for m in M if m["product_id"] == p["id"] and m["stance"] == "recommends"]
    print(p["title"], p["n_recommenders"], recs[0]["hn_url"] if recs else "")
```

## License and credit

Released under ODC-By 1.0, like HackerTube and the Hacker News archive it comes from: use it for anything, just credit Hackerzon. Comments belong to their authors and link back to Hacker News. Not affiliated with Amazon, Hacker News or Y Combinator.
