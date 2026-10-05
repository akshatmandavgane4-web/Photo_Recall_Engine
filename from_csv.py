"""Manual-export fallback, e.g. for Google Photos community threads (no API).
CSV columns: url, date, text  (optional: author, thread_id).
Usage: python -m collectors.from_csv community path/to/file.csv"""
import csv, hashlib, sys
from .common import record, save


def main(source, path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    save(source, [record(source, hashlib.sha256((r["url"] + r["text"]).encode()).hexdigest()[:10],
                         r["url"], r.get("date"), r.get("author"), r["text"],
                         thread_id=r.get("thread_id") or r["url"]) for r in rows])


if __name__ == "__main__":
    main(*sys.argv[1:3])
