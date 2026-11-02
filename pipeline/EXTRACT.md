# Extraction task: products recommended by name in Ask HN threads

You're helping build an Amazon-style store of things Hacker News commenters recommend.
The input file has a {"thread": "<title>"} line before each thread's comments; every other line is
one HN comment ({"id", "text"}) from that "Ask HN" recommendation thread (e.g. "What sub $200
product improved your life?", "What books changed how you think?"). Many name products or books
in plain text, without links. Your job: list every buyable item each comment names.

## What counts (include)
- Books (any genre), including textbooks.
- Physical products: gadgets, tools, kitchen gear, furniture, clothing, toys, board games,
  musical instruments, outdoor gear, etc.
- Media you buy: films/TV box sets, albums, video games, paid video courses.

## What doesn't count (skip)
- Software, apps, websites, SaaS, browser extensions, programming languages, libraries.
- Subscriptions and services (Netflix, a gym, a newsletter).
- Generic categories with no specific item ("a standing desk", "noise-cancelling headphones",
  "anything by Feynman"). A brand + product line is fine ("Uniqlo Airism shirts", "Sony WH-1000XM4").
- Things mentioned only as the topic of the thread title, or quoted from someone else.

## Output
For each input comment that names at least one item, write ONE JSON line:
{"id": "<comment id>", "items": [{"n": "...", "by": "...", "k": "book|product|media", "s": "rec|neg|other"}]}
Skip comments that name no items (don't write a line for them).

- "n": canonical name a store would use. Books: the main title only, no subtitle, no
  edition ("Gödel, Escher, Bach", "The Design of Everyday Things"). Products: "Brand Model" in its
  common form ("AeroPress", "Kindle Paperwhite", "Logitech MX Master 3", "Casio F-91W").
  Fix obvious misspellings. Use the same spelling every time you see the same item.
- "by": book author's full name (first author only), or the brand/maker for products. "" if unknown.
- "k": "book", "product" or "media".
- "s": "rec" if the commenter recommends/praises it or says it improved their life, "neg" if they warn
  against it, "other" for neutral mentions.

## Rules
- Output ONLY JSONL to the output file, no markdown or commentary.
- Read every comment yourself and judge it; don't write a script that pattern-matches names.
  (You may use a small script only to write out the JSON you produced.)
- Then run: python3 pipeline/validate_extract.py <input> <output>
  and fix everything it reports until it prints OK.
