"""Shared record shape, hashing, keyword pre-filter and JSONL output for all collectors."""
import hashlib, json, re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# Cheap first pass (architecture.md 3.3 step 2). The LLM relevance classifier runs after this.
KEYWORDS = re.compile(
    r"can'?t find|cannot find|couldn'?t find|unable to find|looking for|trying to find|"
    r"search(ing|ed)?\b|find (a|an|the|my|that|old)|old photo|scroll|lost (a |my )?(photo|picture|pic)|"
    r"where is|remember", re.I)


def author_hash(name):
    return hashlib.sha256((name or "").encode()).hexdigest()[:12]


def record(source, native_id, url, date, author, text, rating=None, thread_id=None, title=None):
    text = " ".join(((title + ". ") if title else "") .split() + (text or "").split())
    return {
        "id": f"{source}_{native_id}", "source": source, "url": url, "date": date,
        "author_hash": author_hash(author), "rating": rating,
        "thread_id": thread_id, "text": text,
        "text_hash": hashlib.sha256(text.lower().encode()).hexdigest()[:16],
        "keyword_hit": bool(KEYWORDS.search(text)),
    }


def save(source, records, min_chars=40):
    """Dedupe by id and text hash, drop very short texts, write data/raw/<source>.jsonl."""
    seen, out = set(), []
    for r in records:
        if len(r["text"]) < min_chars or r["id"] in seen or r["text_hash"] in seen:
            continue
        seen.update((r["id"], r["text_hash"]))
        out.append(r)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{source}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    hits = sum(r["keyword_hit"] for r in out)
    print(f"{source}: {len(out)} records ({hits} pass keyword filter) -> {path}")
    return out
