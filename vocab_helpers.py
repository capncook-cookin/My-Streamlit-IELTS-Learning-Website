"""
Groq-powered vocabulary lookup for the CtrlLang writing studio.

Added in v3 so the vocabulary helper is fast (Groq 8b-instant, ~1s typical
latency) and returns TWO meanings per term:
  - `plain_meaning`        the everyday dictionary definition
  - `context_meaning`      how the word/phrase is being used in the essay
                           (only when a context sentence is supplied)

The original /api/dictionary route in main.py still uses Ollama; this file
is additive and lives in a separate module so the main.py file stays
byte-identical except for the two include_router lines.

Cache: 5-minute in-memory TTL keyed on (term, first 200 chars of context).
Cache hits are exposed via /api/vocab/cache-stats.
"""

from dotenv import load_dotenv
import json
import os
import time
import requests

load_dotenv()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Groq's 8B instant tier (llama-3.1-8b-instant) was decommissioned late 2025;
# gpt-oss-20b is the current fast/cheap open model on Groq's free tier.
GROQ_VOCAB_MODEL = "openai/gpt-oss-20b"

# Server-side key (the chat widget uses the same env var).
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Cache: { "term|context_prefix" -> (expires_at_epoch, result_dict) }
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 300
_CACHE_HITS = 0


def _cache_key(term: str, context: str) -> str:
    return f"{term.strip().lower()}|{context.strip().lower()[:200]}"


def _from_cache(term: str, context: str) -> dict | None:
    """Return a cached result if present and not expired, else None."""
    global _CACHE_HITS
    key = _cache_key(term, context)
    entry = _CACHE.get(key)
    if entry is None:
        return None
    expires_at, payload = entry
    if expires_at < time.time():
        _CACHE.pop(key, None)
        return None
    _CACHE_HITS += 1
    return payload


def _to_cache(term: str, context: str, payload: dict) -> None:
    key = _cache_key(term, context)
    _CACHE[key] = (time.time() + _CACHE_TTL_SECONDS, payload)


def cache_stats() -> dict:
    """Snapshot of the in-memory cache — used by GET /api/vocab/cache-stats."""
    now = time.time()
    live = sum(1 for exp, _ in _CACHE.values() if exp >= now)
    return {
        "size": live,
        "hits": _CACHE_HITS,
        "ttl_seconds": _CACHE_TTL_SECONDS,
    }


def groq_define(term: str, context: str = "") -> dict:
    """
    Look up a word/phrase via Groq and return plain + context meanings.

    Returns one of:
      {"term", "plain_meaning", "context_meaning", "part_of_speech",
       "example", "synonyms": [...]}
      or
      {"error": "<human-readable error message>"}  (always safe to surface)
    """
    if not GROQ_API_KEY:
        return {"error": "⚠️ GROQ_API_KEY is not set in the backend's .env file."}

    cached = _from_cache(term, context)
    if cached is not None:
        return cached

    system_prompt = (
        "You are a dictionary for IELTS Writing students. Given a word or "
        "phrase, respond ONLY in raw JSON, no markdown fences, no preamble, "
        "in this exact shape: "
        '{"term": "<echo back the input term>", '
        '"plain_meaning": "<one clear sentence a learner can understand>", '
        '"context_meaning": "<one sentence explaining how the word is used '
        'in the provided essay context — empty string if no context was given>", '
        '"part_of_speech": "<e.g. noun, verb, adjective, phrase>", '
        '"example": "<one natural example sentence using the word>", '
        '"synonyms": ["<synonym 1>", "<synonym 2>", "<synonym 3>"], '
        '"collocations": ['
        '{"phrase": "<common collocation 1>", "example": "<example sentence using it>"}, '
        '{"phrase": "<common collocation 2>", "example": "<example sentence using it>"}, '
        '{"phrase": "<common collocation 3>", "example": "<example sentence using it>"}'
        ']}'
    )
    user_prompt = f"Word or phrase: {term.strip()}"
    if context.strip():
        user_prompt += f"\nUsed in this essay context: {context.strip()}"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_VOCAB_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 400,
        "temperature": 0.3,
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        # Some models wrap JSON in code fences despite instructions — strip them.
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(raw)
        # Normalize synonyms so the frontend can always .map() it.
        if not isinstance(parsed.get("synonyms"), list):
            parsed["synonyms"] = []
        # Normalize collocations to [{"phrase","example"}, ...] so the UI
        # never has to defensive-check every item. Drop malformed entries
        # rather than crashing on a bad model output.
        raw_coll = parsed.get("collocations")
        clean_coll = []
        if isinstance(raw_coll, list):
            for item in raw_coll:
                if isinstance(item, dict) and item.get("phrase"):
                    clean_coll.append({
                        "phrase": str(item.get("phrase", "")).strip(),
                        "example": str(item.get("example", "")).strip(),
                    })
        parsed["collocations"] = clean_coll
        # Always echo back the term in case the model reformatted it.
        parsed.setdefault("term", term.strip())
        _to_cache(term, context, parsed)
        return parsed
    except requests.exceptions.Timeout:
        return {"error": "⚠️ Groq took too long to respond (>15s). Try again."}
    except requests.exceptions.HTTPError as e:
        code = response.status_code
        if code == 401:
            return {"error": "⚠️ Invalid GROQ_API_KEY. Double-check the value in .env."}
        if code == 429:
            return {"error": "⚠️ Groq rate limit hit — wait a moment and try again."}
        return {"error": f"⚠️ Groq API error: HTTP {code}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"⚠️ Network error talking to Groq: {e}"}
    except (json.JSONDecodeError, KeyError) as e:
        return {"error": f"⚠️ Groq response wasn't valid JSON: {e}"}
