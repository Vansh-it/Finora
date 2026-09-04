"""FMP (Financial Modeling Prep) API client.

Provides structured financial data enrichment as a secondary source.
SEC remains authoritative — FMP enriches, never overwrites valid SEC data.

Key features:
  - Secure API key loading (never exposed to frontend)
  - HTTP connection reuse via urllib
  - Explicit connect/read timeouts
  - Bounded retry with exponential backoff + jitter
  - 429 / quota / 403 detection
  - Malformed response handling
  - In-memory response cache
  - Request instrumentation
  - Normalized errors
  - Never crashes core SEC research on failure
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from lib.cache import BoundedTTLCache
from lib.netutil import apply_ipv4_first as _net_fix
_net_fix()

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path, override=True)

logger = logging.getLogger("finora.fmp")

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_URL = "https://financialmodelingprep.com/stable"
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 20
MAX_RETRIES = 2
RETRY_BASE_BACKOFF = 1.0  # seconds
RETRY_MAX_WAIT = 8.0  # seconds
JITTER_MAX = 0.5

# ── Cache ─────────────────────────────────────────────────────────────────────
_fmp_cache = BoundedTTLCache(maxsize=2000, ttl=3600.0, name="fmp")

# ── Instrumentation ───────────────────────────────────────────────────────────
_instrumentation = {
    "requests_this_research": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "total_requests": 0,
    "total_errors": 0,
}


def get_instrumentation() -> dict:
    """Return a copy of current FMP instrumentation counters."""
    return dict(_instrumentation)


def reset_instrumentation() -> None:
    """Reset instrumentation counters (used between research sessions)."""
    _instrumentation["requests_this_research"] = 0
    _instrumentation["cache_hits"] = 0
    _instrumentation["cache_misses"] = 0


def clear_cache() -> None:
    """Drop all cached FMP responses (tests only)."""
    _fmp_cache.clear()


def _get_api_key() -> str:
    """Load FMP API key from environment. Returns empty string if missing."""
    return os.environ.get("FMP_API_KEY", "").strip()


def is_available() -> bool:
    """Check if FMP is configured with a valid API key."""
    key = _get_api_key()
    return bool(key) and len(key) > 5


def _cache_get(url: str) -> Optional[dict]:
    """Check cache for a response."""
    cached = _fmp_cache.get(url)
    if cached is not None:
        _instrumentation["cache_hits"] += 1
        return cached
    _instrumentation["cache_misses"] += 1
    return None


def _cache_set(url: str, data: Any) -> None:
    """Store response in cache."""
    _fmp_cache.set(url, data)


def _fmp_get(
    endpoint: str,
    params: Optional[dict] = None,
    cache_ttl: float = 3600.0,
) -> Optional[Any]:
    """GET an FMP endpoint with retries, caching, and instrumentation.

    Returns parsed JSON on success, None on failure (never raises).
    """
    api_key = _get_api_key()
    if not api_key or len(api_key) <= 5:
        logger.debug("[fmp] API key not configured — skipping")
        return None

    # Build URL
    url = f"{BASE_URL}/{endpoint}"
    query_parts = [f"apikey={api_key}"]
    if params:
        for k, v in params.items():
            if v is not None:
                query_parts.append(f"{k}={v}")
    url += "?" + "&".join(query_parts)

    # Check cache (use a key without the API key)
    cache_key = f"fmp:{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
    if cache_ttl > 0:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    _instrumentation["requests_this_research"] += 1
    _instrumentation["total_requests"] += 1

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Finora/2.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=READ_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")

            # Handle empty response
            if not raw or raw.strip() == "":
                logger.warning(f"[fmp] Empty response for {endpoint}")
                _instrumentation["total_errors"] += 1
                return None

            # Handle non-JSON
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning(f"[fmp] Malformed JSON for {endpoint}: {exc}")
                _instrumentation["total_errors"] += 1
                return None

            # Handle FMP error responses
            if isinstance(data, dict):
                if "Error Message" in data:
                    error_msg = data["Error Message"]
                    if "Invalid API KEY" in error_msg or "limit" in error_msg.lower():
                        logger.warning(f"[fmp] Quota/auth error: {error_msg}")
                    else:
                        logger.warning(f"[fmp] Error for {endpoint}: {error_msg}")
                    _instrumentation["total_errors"] += 1
                    return None

            # Handle empty array (valid FMP response for no data)
            if isinstance(data, list) and len(data) == 0:
                _cache_set(cache_key, data)
                return data

            # Success
            if cache_ttl > 0:
                _cache_set(cache_key, data)
            return data

        except urllib.error.HTTPError as exc:
            last_error = exc
            code = exc.code
            if code == 429:
                wait = min(RETRY_BASE_BACKOFF * (2 ** attempt) + random.uniform(0, JITTER_MAX), RETRY_MAX_WAIT)
                logger.warning(f"[fmp] Rate limited (429), waiting {wait:.1f}s")
                time.sleep(wait)
            elif code == 403:
                logger.warning(f"[fmp] Plan restriction (403) for {endpoint}")
                _instrumentation["total_errors"] += 1
                return None
            elif code >= 500:
                wait = RETRY_BASE_BACKOFF * (2 ** attempt) + random.uniform(0, JITTER_MAX)
                time.sleep(wait)
            else:
                logger.warning(f"[fmp] HTTP {code} for {endpoint}")
                _instrumentation["total_errors"] += 1
                return None

        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            wait = RETRY_BASE_BACKOFF * (2 ** attempt) + random.uniform(0, JITTER_MAX)
            logger.warning(f"[fmp] Network error for {endpoint}: {exc}, retrying in {wait:.1f}s")
            time.sleep(wait)

        except Exception as exc:
            last_error = exc
            logger.warning(f"[fmp] Unexpected error for {endpoint}: {exc}")
            _instrumentation["total_errors"] += 1
            return None

    logger.warning(f"[fmp] Failed after {MAX_RETRIES + 1} attempts for {endpoint}: {last_error}")
    _instrumentation["total_errors"] += 1
    return None


# ── Public API — High-value endpoints ─────────────────────────────────────────

def get_company_profile(ticker: str) -> Optional[dict]:
    """Fetch company profile (name, sector, industry, market cap, etc.)."""
    data = _fmp_get("profile", {"symbol": ticker.upper()}, cache_ttl=86400.0)
    if isinstance(data, list) and data:
        return data[0]
    return None


def get_income_statement(ticker: str, period: str = "annual", limit: int = 5) -> Optional[list]:
    """Fetch income statement history."""
    return _fmp_get("income-statement", {"symbol": ticker.upper(), "period": period, "limit": limit}, cache_ttl=86400.0)


def get_balance_sheet(ticker: str, period: str = "annual", limit: int = 5) -> Optional[list]:
    """Fetch balance sheet history."""
    return _fmp_get("balance-sheet-statement", {"symbol": ticker.upper(), "period": period, "limit": limit}, cache_ttl=86400.0)


def get_cash_flow(ticker: str, period: str = "annual", limit: int = 5) -> Optional[list]:
    """Fetch cash flow statement history."""
    return _fmp_get("cash-flow-statement", {"symbol": ticker.upper(), "period": period, "limit": limit}, cache_ttl=86400.0)


def get_key_metrics(ticker: str, period: str = "annual", limit: int = 5) -> Optional[list]:
    """Fetch key financial metrics."""
    return _fmp_get("key-metrics", {"symbol": ticker.upper(), "period": period, "limit": limit}, cache_ttl=86400.0)


def get_financial_ratios(ticker: str, period: str = "annual", limit: int = 5) -> Optional[list]:
    """Fetch financial ratios."""
    return _fmp_get("ratios", {"symbol": ticker.upper(), "period": period, "limit": limit}, cache_ttl=86400.0)


def get_enterprise_value(ticker: str, period: str = "annual", limit: int = 5) -> Optional[list]:
    """Fetch enterprise value history."""
    return _fmp_get("enterprise-values", {"symbol": ticker.upper(), "period": period, "limit": limit}, cache_ttl=86400.0)


def get_market_cap(ticker: str) -> Optional[float]:
    """Fetch current market capitalization."""
    profile = get_company_profile(ticker)
    if profile:
        # New API uses 'marketCap', legacy used 'mktCap'
        for key in ("marketCap", "mktCap"):
            if key in profile and profile[key] is not None:
                try:
                    return float(profile[key])
                except (TypeError, ValueError):
                    pass
    return None


def get_quote(ticker: str) -> Optional[dict]:
    """Fetch current quote (price, change, volume)."""
    data = _fmp_get("quote", {"symbol": ticker.upper()}, cache_ttl=300.0)
    if isinstance(data, list) and data:
        return data[0]
    return None


def get_historical_price(
    ticker: str,
    from_date: str,
    to_date: Optional[str] = None,
) -> Optional[list]:
    """Fetch historical daily prices.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol.
    from_date : str
        Start date in YYYY-MM-DD format.
    to_date : str, optional
        End date (defaults to today).
    """
    params = {"symbol": ticker.upper(), "from": from_date}
    if to_date:
        params["to"] = to_date
    data = _fmp_get(
        "historical-price-eod/full",
        params,
        cache_ttl=2592000.0,  # 30 days — historical prices don't change
    )
    if isinstance(data, dict):
        return data.get("historical", [])
    # The new API returns a list directly
    if isinstance(data, list):
        return data
    return None


def get_shares_outstanding(ticker: str) -> Optional[float]:
    """Fetch shares outstanding from the most recent profile."""
    profile = get_company_profile(ticker)
    if profile:
        # New API may not include sharesOutstanding in profile
        for key in ("sharesOutstanding",):
            if key in profile and profile[key] is not None:
                try:
                    return float(profile[key])
                except (TypeError, ValueError):
                    pass
        # Fallback: derive from market cap / price
        cap = profile.get("marketCap") or profile.get("mktCap")
        price = profile.get("price")
        if cap and price and price > 0:
            try:
                return float(cap) / float(price)
            except (TypeError, ValueError, ZeroDivisionError):
                pass
    return None


def get_ebitda(ticker: str, period: str = "annual") -> Optional[float]:
    """Fetch EBITDA from income statement or key metrics."""
    # Try income statement first (has direct ebitda field)
    data = get_income_statement(ticker, period=period, limit=1)
    if isinstance(data, list) and data:
        ebitda = data[0].get("ebitda")
        if ebitda:
            try:
                return float(ebitda)
            except (TypeError, ValueError):
                pass
    # Fallback: derive from key metrics (EV/EBITDA ratio)
    data = get_key_metrics(ticker, period=period, limit=1)
    if isinstance(data, list) and data:
        ev = data[0].get("enterpriseValue")
        ev_ebitda = data[0].get("evToEBITDA") or data[0].get("enterpriseValueOverEBITDA")
        if ev and ev_ebitda and ev_ebitda != 0:
            try:
                return float(ev) / float(ev_ebitda)
            except (TypeError, ValueError, ZeroDivisionError):
                pass
    return None
