"""Reddit collector (official API, app-only OAuth). Usage: python -m collectors.reddit
Needs REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET in .env. Collects posts and their top comments."""
import os, time
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from .common import record, save

load_dotenv()
UA = {"User-Agent": os.getenv("REDDIT_USER_AGENT", "photo-recall-research/0.1")}
SUBREDDITS = ["googlephotos", "GooglePixel", "Android", "DataHoarder", "photography"]
QUERIES = [
    "can't find photo", "find old photo", "search not working", "search doesn't find",
    "looking for a photo", "lost photo remember", "scrolling to find", "search by description",
    "find screenshot", "find document photo", "ask photos",
]
POSTS_PER_QUERY = 50
COMMENTS_PER_POST = 8
MIN_COMMENTS_TO_FETCH = 3


def token():
    r = requests.post("https://www.reddit.com/api/v1/access_token",
                      auth=(os.environ["REDDIT_CLIENT_ID"], os.environ["REDDIT_CLIENT_SECRET"]),
                      data={"grant_type": "client_credentials"}, headers=UA, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def get(path, tok, **params):
    for attempt in range(3):
        r = requests.get(f"https://oauth.reddit.com{path}", params=params,
                         headers={**UA, "Authorization": f"bearer {tok}"}, timeout=20)
        if r.status_code == 429:
            time.sleep(10 * (attempt + 1)); continue
        r.raise_for_status()
        time.sleep(1.1)  # stay well under the rate limit
        return r.json()
    return None


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def main():
    tok, posts = token(), {}
    for sub in SUBREDDITS:
        for q in QUERIES:
            # outside the main sub, the query must mention the product
            query = q if sub == "googlephotos" else f'"google photos" {q}'
            data = get(f"/r/{sub}/search", tok, q=query, restrict_sr=1, sort="relevance",
                       t="all", limit=POSTS_PER_QUERY)
            for c in (data or {}).get("data", {}).get("children", []):
                posts[c["data"]["id"]] = c["data"]
        print(f"r/{sub}: {len(posts)} unique posts so far")

    recs = []
    for pid, p in posts.items():
        url = "https://www.reddit.com" + p["permalink"]
        recs.append(record("reddit", pid, url, iso(p["created_utc"]), p.get("author"),
                           p.get("selftext", ""), thread_id=pid, title=p.get("title")))
        if p.get("num_comments", 0) < MIN_COMMENTS_TO_FETCH:
            continue
        thread = get(f"/comments/{pid}", tok, limit=COMMENTS_PER_POST, depth=1, sort="top")
        for c in (thread[1]["data"]["children"] if thread else []):
            d = c.get("data", {})
            if c.get("kind") != "t1" or d.get("body") in (None, "[deleted]", "[removed]"):
                continue
            recs.append(record("reddit", f"{pid}_{d['id']}", url + d["id"], iso(d["created_utc"]),
                               d.get("author"), d["body"], thread_id=pid))
    save("reddit", recs)


if __name__ == "__main__":
    main()
