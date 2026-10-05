"""Play Store reviews (google-play-scraper library; no key). Usage: python -m collectors.play_store"""
from google_play_scraper import Sort, reviews
from .common import record, save

APP = "com.google.android.apps.photos"
COUNTRIES = ["in", "us", "gb"]
PER_PULL = 3000  # per country and sort order; most are filtered out as irrelevant later


def main():
    recs = []
    for country in COUNTRIES:
        for sort in (Sort.NEWEST, Sort.MOST_RELEVANT):
            got, tok = [], None
            while len(got) < PER_PULL:
                batch, tok = reviews(APP, lang="en", country=country, sort=sort,
                                     count=200, continuation_token=tok)
                if not batch:
                    break
                got += batch
            print(f"play_store {country}/{sort.name}: {len(got)}")
            for r in got:
                recs.append(record(
                    "play_store", r["reviewId"],
                    f"https://play.google.com/store/apps/details?id={APP}&reviewId={r['reviewId']}",
                    r["at"].strftime("%Y-%m-%d"), r.get("userName"), r.get("content"),
                    rating=r.get("score")))
    save("play_store", recs)


if __name__ == "__main__":
    main()
