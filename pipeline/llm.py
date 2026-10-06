"""Thin Groq client (OpenAI-compatible endpoint): JSON mode, temperature 0, retry on rate limits."""
import json, os, time
import requests
from dotenv import load_dotenv

load_dotenv()
BASE = "https://api.groq.com/openai/v1"
PREFERRED = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "moonshotai/kimi-k2-instruct",
             "meta-llama/llama-4-scout-17b-16e-instruct", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]
_models, _exhausted = None, set()


def _headers():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise SystemExit("GROQ_API_KEY is missing from .env")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _candidates():
    """Models this key can use, best first. GROQ_MODEL from .env, if set, goes to the front."""
    global _models
    if _models is None:
        r = requests.get(f"{BASE}/models", headers=_headers(), timeout=20)
        r.raise_for_status()
        ids = {m["id"] for m in r.json()["data"]}
        first = [os.getenv("GROQ_MODEL")] if os.getenv("GROQ_MODEL") else []
        _models = [m for m in dict.fromkeys(first + PREFERRED) if m in ids]
        if not _models:
            raise SystemExit("No usable model. Set GROQ_MODEL in .env to one of: " + ", ".join(sorted(ids)))
    return _models


def model():
    """The model in use now: the best one whose daily quota is not used up."""
    left = [m for m in _candidates() if m not in _exhausted]
    if not left:
        raise RuntimeError("Daily quota used up on every model: " + ", ".join(_candidates()))
    return left[0]


def chat_json(system, user, max_tokens=1500):
    """One call, parsed JSON back. Raises ValueError on unparseable output, RuntimeError if the daily quota is gone."""
    body = {"temperature": 0, "max_tokens": max_tokens, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    for attempt in range(12):
        body["model"] = model()
        r = requests.post(f"{BASE}/chat/completions", headers=_headers(), json=body, timeout=60)
        if r.status_code == 429:
            wait = float(r.headers.get("retry-after", 5))
            if wait > 45 or "per day" in r.text or "TPD" in r.text or "RPD" in r.text:
                _exhausted.add(body["model"])       # daily quota gone: move to the next model
                print(f"  daily limit reached on {body['model']}; switching model", flush=True)
                continue
            time.sleep(wait + 0.5); continue
        if r.status_code in (400, 404) and "model" in r.text.lower() and "json" not in r.text.lower():
            _exhausted.add(body["model"]); continue  # model retired or unsupported
        if r.status_code >= 500:
            time.sleep(3 * (attempt + 1)); continue
        if r.status_code == 400 and "json" in r.text.lower():
            raise ValueError("model returned invalid JSON")
        r.raise_for_status()
        try:
            return json.loads(r.json()["choices"][0]["message"]["content"])
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"unparseable response: {e}")
    raise RuntimeError("Groq kept failing after 12 attempts.")
