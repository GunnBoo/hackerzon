"""Fetch every HN comment containing an Amazon link from the Algolia HN API.
Algolia caps a query at 1000 hits, so we walk the archive in time windows
and split any window that has more than 1000 hits."""
import json, sys, time, urllib.request, urllib.parse, datetime, os

OUT = sys.argv[1]
QUERIES = sys.argv[2].split(",") if len(sys.argv) > 2 else ["amazon.com", "amzn.to", "amzn.com", "amazon.co.uk"]
START = int(datetime.datetime(2007, 1, 1).timestamp())
END = int(time.time())

def get(q, a, b):
    params = {"query": q, "tags": "comment", "hitsPerPage": 1000,
              "numericFilters": f"created_at_i>={a},created_at_i<{b}"}
    url = "https://hn.algolia.com/api/v1/search_by_date?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            time.sleep(2 + attempt * 3)
    raise RuntimeError(url)

seen = set()
n = 0
with open(OUT, "w") as f:
    def walk(q, a, b):
        global n
        d = get(q, a, b)
        if d["nbHits"] > 1000 and b - a > 3600:
            mid = (a + b) // 2
            walk(q, a, mid); walk(q, mid, b)
            return
        for h in d["hits"]:
            if h["objectID"] in seen:
                continue
            seen.add(h["objectID"])
            f.write(json.dumps({k: h.get(k) for k in
                ["objectID", "author", "created_at_i", "comment_text", "story_id",
                 "story_title", "parent_id"]}) + "\n")
            n += 1
    for q in QUERIES:
        # yearly windows, auto-split when dense
        a = START
        while a < END:
            b = min(a + 365 * 86400, END)
            walk(q, a, b)
            a = b
        print(q, "total so far", n, flush=True)
print("done", n)
