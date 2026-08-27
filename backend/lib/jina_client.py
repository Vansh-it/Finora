"""Jina Reader API client.

Single place responsible for all Jina Reader communication.
Transforms URLs into clean readable Markdown/text for downstream
financial fact extraction.

Only trusted, filtered sources should be sent to Jina.
"""

from __future__ import annotations

import json
import os
import time
import hashlib
from pathlib import Path
from typing import Any, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path, override=True)

# ── Configuration ─────────────────────────────────────────────────────────────
JINA_READER_URL = "https://r.jina.ai"
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 2
RETRY_BACKOFF = 2.0  # seconds
MIN_REQUEST_INTERVAL = 1.0  # seconds between requests
MAX_CONTENT_LENGTH = 100_000  # characters — trim huge pages


def _get_api_key() -> str:
    """Read Jina API key from environment. Raises if not configured."""
    key = os.getenv("JINA_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "JINA_API_KEY not set. Add it to your .env file. "
            "Get a free key at https://jina.ai"
        )
    return key


# ── In-memory cache ──────────────────────────────────────────────────────────
_cache: dict[str, tuple[float, dict]] = {}
_last_request_time: float = 0.0
_read_count: int = 0


def _cache_key(url: str) -> str:
    return hashlib.md5(url.strip().lower().encode()).hexdigest()


def _get_cached(url: str, ttl_seconds: float = 7200.0) -> Optional[dict]:
    """Return cached read result if still valid."""
    key = _cache_key(url)
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < ttl_seconds:
            return data
    return None


def _set_cache(url: str, data: dict) -> None:
    """Store read result in cache."""
    _cache[_cache_key(url)] = (time.time(), data)


def clear_cache() -> None:
    """Drop all cached Jina reads — useful for tests."""
    _cache.clear()


def get_read_count() -> int:
    """Return number of Jina reads performed since import/reset."""
    return _read_count


def reset_read_count() -> None:
    """Reset the read counter."""
    global _read_count
    _read_count = 0


# ── Rate limiting ─────────────────────────────────────────────────────────────
def _respect_rate_limit() -> None:
    """Ensure minimum interval between requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


# ── HTTP layer ────────────────────────────────────────────────────────────────
def read_url(
    url: str,
    *,
    timeout: int = REQUEST_TIMEOUT,
    cache_ttl: float = 7200.0,
) -> dict:
    """Read a URL using Jina Reader and return clean Markdown content.

    Parameters
    ----------
    url : str
        The URL to read.
    timeout : int
        Request timeout in seconds.
    cache_ttl : float
        Cache time-to-live in seconds. Set to 0 to skip cache.

    Returns
    -------
    dict
        {"url": ..., "status": "success"|"error", "content": "...",
         "content_length": int, "title": "..."}

    Raises
    ------
    RuntimeError
        If the request fails after all retries.
    ValueError
        If the response is invalid.
    """
    global _read_count

    # Check cache first
    if cache_ttl > 0:
        cached = _get_cached(url, cache_ttl)
        if cached is not None:
            return cached

    _respect_rate_limit()
    _read_count += 1

    api_key = _get_api_key()
    jina_url = f"{JINA_READER_URL}/{url}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "X-Return-Format": "markdown",
    }

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            req = Request(jina_url, headers=headers, method="GET")
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)

                # Extract content
                content = ""
                title = ""

                # Jina returns data as array of objects or single object
                if isinstance(data, dict):
                    if "data" in data:
                        inner = data["data"]
                        if isinstance(inner, list) and len(inner) > 0:
                            content = inner[0].get("content", "")
                            title = inner[0].get("title", "")
                        elif isinstance(inner, dict):
                            content = inner.get("content", "")
                            title = inner.get("title", "")
                    elif "content" in data:
                        content = data["content"]
                        title = data.get("title", "")
                elif isinstance(data, list) and len(data) > 0:
                    content = data[0].get("content", "")
                    title = data[0].get("title", "")

                # Trim excessive content
                if len(content) > MAX_CONTENT_LENGTH:
                    content = content[:MAX_CONTENT_LENGTH] + "\n\n[Content truncated]"

                result = {
                    "url": url,
                    "status": "success" if content else "empty",
                    "content": content,
                    "content_length": len(content),
                    "title": title,
                }

                if cache_ttl > 0:
                    _set_cache(url, result)
                return result

        except HTTPError as exc:
            last_error = exc
            code = exc.code
            if code == 429:
                wait = RETRY_BACKOFF * (2 ** attempt)
                time.sleep(wait)
            elif code == 404:
                return {
                    "url": url,
                    "status": "not_found",
                    "content": "",
                    "content_length": 0,
                    "title": "",
                }
            elif code >= 400 and code < 500:
                return {
                    "url": url,
                    "status": "error",
                    "content": "",
                    "content_length": 0,
                    "title": "",
                    "error": f"HTTP {code}: {exc.reason}",
                }
            else:
                wait = RETRY_BACKOFF * (2 ** attempt)
                time.sleep(wait)
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            wait = RETRY_BACKOFF * (2 ** attempt)
            time.sleep(wait)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON from Jina Reader: {exc}")

    # All retries exhausted — graceful failure, don't crash
    return {
        "url": url,
        "status": "error",
        "content": "",
        "content_length": 0,
        "title": "",
        "error": f"Failed after {MAX_RETRIES} attempts: {last_error}",
    }
