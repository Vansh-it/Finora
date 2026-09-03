"""SEC EDGAR HTTP client.

Single place responsible for all communication with SEC endpoints.
Handles User-Agent headers, retries, caching, and rate-limiting.

SEC requires a valid User-Agent header and expects fair access
(no more than 10 requests per second).
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
from urllib.parse import quote

from dotenv import load_dotenv
from lib.netutil import apply_ipv4_first as _net_fix
_net_fix()
from lib.cache import BoundedTTLCache, single_flight

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path, override=True)

# ── Configuration ─────────────────────────────────────────────────────────────
SEC_BASE = "https://data.sec.gov"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
REQUEST_TIMEOUT = 15  # seconds (was 20 — tightened for pipeline SLA)
MAX_RETRIES = 2  # was 3 — cap worst-case at ~15+30=45s
RETRY_BACKOFF = 1.5  # seconds, doubles each retry
MIN_REQUEST_INTERVAL = 0.12  # seconds between requests (~8 req/s, under SEC limit)


def _get_user_agent() -> str:
    """Read User-Agent from environment. Raises if not configured."""
    ua = os.getenv("FINORA_SEC_USER_AGENT", "").strip()
    if not ua:
        raise RuntimeError(
            "FINORA_SEC_USER_AGENT not set. Add it to your .env file. "
            "SEC EDGAR requires a valid User-Agent header."
        )
    return ua


# -- Bounded TTL+LRU cache ---
_sec_cache = BoundedTTLCache(maxsize=2000, ttl=3600.0, name="sec")
_last_request_time: float = 0.0


def _get_cached(url: str, ttl_seconds: float = 3600.0) -> Optional[Any]:
    """Return cached response if still valid."""
    return _sec_cache.get(url)


def _set_cache(url: str, data: Any) -> None:
    """Store response in cache."""
    _sec_cache.set(url, data)


def clear_cache() -> None:
    """Drop all cached SEC responses -- useful for tests."""
    _sec_cache.clear()

# ── Rate limiting ─────────────────────────────────────────────────────────────
def _respect_rate_limit() -> None:
    """Ensure minimum interval between requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


# ── HTTP layer ────────────────────────────────────────────────────────────────
def sec_get(url: str, *, timeout: int = REQUEST_TIMEOUT, cache_ttl: float = 3600.0) -> dict | list:
    """GET a SEC endpoint with User-Agent, retries, and caching.

    Parameters
    ----------
    url : str
        Full SEC URL to fetch.
    timeout : int
        Request timeout in seconds.
    cache_ttl : float
        Cache time-to-live in seconds. Set to 0 to skip cache.

    Returns
    -------
    dict | list
        Parsed JSON response.

    Raises
    ------
    RuntimeError
        If the request fails after all retries or SEC is unavailable.
    ValueError
        If the response is not valid JSON.
    """
    # Check cache first
    if cache_ttl > 0:
        cached = _get_cached(url, cache_ttl)
        if cached is not None:
            return cached

    _respect_rate_limit()

    user_agent = _get_user_agent()
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, headers=headers, method="GET")
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                if cache_ttl > 0:
                    _set_cache(url, data)
                return data
        except HTTPError as exc:
            last_error = exc
            code = exc.code
            if code == 429:
                # Rate limited — back off
                wait = RETRY_BACKOFF * (2 ** attempt)
                time.sleep(wait)
            elif code == 404:
                raise ValueError(f"SEC resource not found: {url}")
            elif code >= 500:
                # Server error — retry
                wait = RETRY_BACKOFF * (2 ** attempt)
                time.sleep(wait)
            else:
                raise RuntimeError(f"SEC HTTP {code}: {exc.reason}")
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            wait = RETRY_BACKOFF * (2 ** attempt)
            time.sleep(wait)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON from SEC: {exc}")

    raise RuntimeError(
        f"SEC request failed after {MAX_RETRIES} attempts: {last_error}"
    )


def get_company_submissions(cik: str, *, cache_ttl: float = 86400.0) -> dict:
    """Fetch all filing submissions for a company by CIK.

    Parameters
    ----------
    cik : str
        10-digit CIK (e.g. "0000789019").
    cache_ttl : float
        Cache TTL in seconds. Defaults to 24 hours.

    Returns
    -------
    dict
        SEC submissions JSON with filings array.
    """
    cik_clean = cik.lstrip("0").zfill(10)
    url = f"{SEC_BASE}/submissions/CIK{cik_clean}.json"
    return sec_get(url, cache_ttl=cache_ttl)


def get_company_facts(cik: str, *, cache_ttl: float = 86400.0) -> dict:
    """Fetch XBRL company facts for a company by CIK."""
    cik_clean = cik.lstrip("0").zfill(10)
    url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{cik_clean}.json"
    return sec_get(url, cache_ttl=cache_ttl)


def get_ticker_mapping(*, cache_ttl: float = 86400.0) -> dict:
    """Fetch the official SEC ticker-to-CIK mapping.

    Returns
    -------
    dict
        Mapping of ticker symbols to company info dicts.
    """
    cached = _get_cached("ticker_mapping", cache_ttl)
    if cached is not None:
        return cached

    data = sec_get(SEC_TICKERS_URL, cache_ttl=cache_ttl)
    _set_cache("ticker_mapping", data)
    return data
