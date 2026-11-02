# Labeling task: Hacker News product recommendations

You are labeling products for a store that only sells things Hacker News commenters
have repeatedly recommended (an Amazon-style site with no ads, no sponsored results,
no upsells). Each input line is one Amazon product (by ASIN) plus a sample of the HN
comments that linked to it. `known` is either Open Library book data (trust it for
title/authors) or the slug from the Amazon URL (may be missing — then identify the
product from the comments; if you truly cannot tell what it is, set keep=false).

For EVERY input line write exactly ONE output line of JSON (JSONL, same order), with these keys:

- "a": the ASIN, copied exactly.
- "keep": true if HN people are genuinely recommending this as something worth buying/reading.
  false if: you can't identify the product; it is mostly self-promotion (one person pushing
  their own book/product — look at top_author_share and the text); the links are mostly
  criticism, mockery, jokes, or citing it as an example of something bad; or it's spam.
  Being cited as a respected source (e.g. a classic book quoted as evidence) counts as keep.
- "drop": short reason if keep=false, else "".
- "t": clean product title as a store would show it (books: main title, add a short subtitle
  only if it is the familiar form, e.g. "Code: The Hidden Language of Computer Hardware and Software").
  No edition junk like "2nd Edition" unless it matters (e.g. "The C Programming Language, 2nd Edition" is fine).
- "by": book author(s) (max 2 names, then "et al.") or the brand/maker for products.
- "dept": exactly one of the department names listed below.
- "sub": a short sub-category, preferring the suggestions listed under that department.
- "kind": "book" | "product" | "media" (films, music, games, video courses).
- "s": one-sentence plain description of what it is (max 30 words). Factual, no hype.
- "w": why HN recommends it, specific to what the comments say (1–2 sentences, max 45 words).
  Write it like a knowledgeable friend, not marketing copy.
- "about": 3 short bullets (each max 16 words) a shopper would want: who it's for, what
  you get, caveats HN raised (e.g. "dated examples", "dense math", "loud fan").
- "q": {"id": comment id, "t": an exact verbatim excerpt (5–25 words) from that comment
  that best captures why people like it}. Must be copied exactly from the text, no edits.
  Use the most enthusiastic genuine recommendation. If none fits, use null.
- "tags": 2–5 lowercase topic tags (e.g. "compilers", "sleep", "mechanical keyboards").
- "gem": true if this is a lesser-known item that most people outside HN wouldn't have
  heard of (a niche gem), false for famous/mainstream items (SICP, Kindle, Clean Code, Atomic Habits).
- "aged": one of "timeless" | "still useful" | "dated" | "historical" — how well it holds up today
  (Nov 2026), based on your knowledge and the comments.
- "st": object mapping EVERY given comment id to its stance:
  "rec" (recommends it), "cite" (cites/references it neutrally), "neg" (criticizes/warns against),
  "joke" (joke/sarcasm), "self" (author promoting own work), "other".

## Departments (use these exact strings for "dept")

Books (kind=book) — split by subject:
- "Programming" — sub: Software Engineering, Languages, Systems & Low-level, Web, Data & Databases, Security, Career & Craft, Algorithms
- "Computer Science & Math" — sub: Theory, Math, Statistics & ML, AI, Logic
- "Science & Engineering" — sub: Physics, Biology, Chemistry, Electronics, Engineering, Space, Popular Science
- "Business & Startups" — sub: Startups, Management, Sales & Marketing, Strategy, Productivity, Negotiation
- "Economics & Finance" — sub: Economics, Investing, Personal Finance
- "History & Biography" — sub: History of Computing, History, Biography & Memoir, War
- "Psychology & Self-Help" — sub: Psychology, Self-Improvement, Health & Mind, Habits
- "Philosophy & Society" — sub: Philosophy, Politics, Law, Sociology, Religion
- "Fiction & Sci-Fi" — sub: Science Fiction, Fantasy, Literary Fiction, Thriller, Kids & YA
- "Design, Writing & Art" — sub: Design, Writing, Typography, Architecture, Art & Photography, Music Theory
- "Food, Health & Home" — sub: Cooking, Fitness, Medicine, Parenting, DIY

Products & media:
- "Computers & Accessories" — sub: Keyboards & Mice, Monitors, Laptops & PCs, Storage, Networking, Cables & Adapters, Peripherals
- "Electronics & Gadgets" — sub: Audio, Phones & Tablets, E-readers, Cameras, Smart Home, Power & Batteries, Wearables
- "Maker & Tools" — sub: Electronics Hobby, Single-board Computers, 3D Printing, Hand Tools, Test Equipment, Soldering
- "Home & Kitchen" — sub: Kitchen, Coffee & Tea, Air & Climate, Lighting, Cleaning, Furniture & Desk, Bedding & Sleep
- "Health & Personal Care" — sub: Sleep, Ergonomics, Fitness, Personal Care, Supplements
- "Outdoors & Travel" — sub: Bags, Travel Gear, Outdoor, Bikes
- "Office & School" — sub: Pens & Paper, Whiteboards, Desk Accessories
- "Toys, Games & Kids" — sub: Board Games, Puzzles, STEM Toys, Kids
- "Movies, Music & Games" — sub: Movies & TV, Music, Video Games, Courses

## Rules
- Output ONLY valid JSONL to the output file: one JSON object per line, no markdown, no commentary.
- Same number of lines as the input, same order.
- Write the file with the Write tool (you may write it in two halves: write the first half,
  then use Bash `cat >>` with a quoted heredoc to append the rest, or rewrite the whole file).
- Then run: python3 pipeline/validate.py <input> <output>
  and fix every problem it reports until it prints OK.

## Items found without an Amazon link (batch files named c*.jsonl)
- Some items came from other stores' links (Manning, O'Reilly, MIT Press, ...) or were only named in
  "Ask HN" answers. Their `known` may be just {"name_hint", "maker_or_author_hint", "kind_hint"}
  taken from the comments; correct the title/author if the comments or your knowledge say otherwise.
- Ask HN answers often list many items. Judge the stance toward THIS item only.
- Keep=false also when the name is too generic to be one product a store could sell
  (e.g. "MacBook" with no model is fine as a product line; "a good chair" is not), or when it is
  software/an app/a service rather than something you buy.
