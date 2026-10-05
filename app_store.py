"""App Store reviews (Apple's public RSS feed; no key; max 500 recent per country).
Usage: python -m collectors.app_store"""
import time
import requests
from .common import record, save

APP_ID = "962194608"  # Google Photos on iOS
COUNTRIES = ["in", "us", "gb", "ca", "au"]


def main():
    recs = []
    for country in COUNTRIES:
        n = 0
        for page in range(1, 11):
            r = requests.get(f"https://itunes.apple.com/{country}/rss/customerreviews/"
                             f"page={page}/id={APP_ID}/sortby=mostrecent/json", timeout=20)
            if r.status_code != 200:
                break
            entries = r.json().get("feed", {}).get("entry", [])
            if isinstance(entries, dict):
                entries = [entries]
            entries = [e for e in entries if "im:rating" in e]
            if not entries:
                break
            for e in entries:
                rid = e["id"]["label"]
                recs.append(record(
                    "app_store", f"{country}_{rid}",
                    f"https://apps.apple.com/{country}/app/id{APP_ID}?see-all=reviews",
                    e["updated"]["label"][:10], e["author"]["name"]["label"],
                    e["content"]["label"], rating=int(e["im:rating"]["label"]),
                    title=e["title"]["label"]))
            n += len(entries)
            time.sleep(0.5)
        print(f"app_store {country}: {n}")
    save("app_store", recs)


if __name__ == "__main__":
    main()
