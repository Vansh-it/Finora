"""Stooq free historical price fallback client.

Stooq provides NO-KEY, FREE historical market data via CSV.
Used as a resilience fallback when Twelve Data or other paid providers
are rate-limited or unavailable.

Key features:
  - No API key required
  - Server-side construction of request URLs (no SSRF risk)
  - Deterministic symbol normalization (AAPL -> aapl.us)
  - CSV parsing with validation
  - Aggressive caching (historical prices don't change)
  - Never crashes research on failure
"""

from __future__ import annotations

import csv
import io
import logging
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Any, Optional

from lib.cache import BoundedTTLCache
from lib.ssrf_guard import validate_url
from lib.netutil import apply_ipv4_first as _net_fix
_net_fix()

logger = logging.getLogger("finora.stooq")

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_URL = "https://stooq.com/q/l/"
REQUEST_TIMEOUT = 15
MAX_RETRIES = 2
RETRY_BACKOFF = 1.5

# ── Cache ─────────────────────────────────────────────────────────────────────
# Historical prices don't meaningfully change — cache aggressively.
stooq_cache = BoundedTTLCache(maxsize=4000, ttl=2592000.0, name="stooq")


def clear_cache() -> None:
    """Drop all cached Stooq responses (tests only)."""
    stooq_cache.clear()


# ── Symbol normalization ──────────────────────────────────────────────────────

def normalize_symbol(ticker: str) -> Optional[str]:
    """Convert a US-market ticker to Stooq format.

    Examples:
        AAPL -> aapl.us
        MSFT -> msft.us
        WMT  -> wmt.us
        BRK-B -> brk-b.us

    Returns None if ticker is invalid.
    """
    if not ticker or not isinstance(ticker, str):
        return None
    t = ticker.strip().upper()
    if not t or not t.replace("-", "").replace(".", "").isalnum():
        return None
    # Strip existing exchange suffixes (e.g. AAPL.US -> AAPL)
    for suffix in [".US", ".us"]:
        if t.endswith(suffix):
            t = t[:-len(suffix)]
            break
    # Stooq uses .us suffix for US-listed stocks
    return f"{t.lower()}.us"


def _build_url(symbol: str) -> str:
    """Build a Stooq CSV request URL server-side."""
    return f"{BASE_URL}?s={symbol}&f=sd2t2ohlcv&h&e=csv"


# ── CSV Parser ────────────────────────────────────────────────────────────────

def _parse_csv(raw_csv: str, symbol: str) -> list[dict]:
    """Safely parse Stooq CSV response into price records.

    Returns a list of dicts with keys: date, open, high, low, close, volume.
    Only includes records with valid numeric prices.
    """
    if not raw_csv or not raw_csv.strip():
        return []

    records = []
    try:
        reader = csv.DictReader(io.StringIO(raw_csv))
        for row in reader:
            try:
                date_str = row.get("Date", "").strip()
                close_str = row.get("Close", "").strip()
                open_str = row.get("Open", "").strip()
                high_str = row.get("High", "").strip()
                low_str = row.get("Low", "").strip()
                vol_str = row.get("Volume", "").strip()

                # Skip rows with N/D or empty critical fields
                if not date_str or date_str == "N/D":
                    continue
                if not close_str or close_str == "N/D":
                    continue

                close = float(close_str)
                if close <= 0:
                    continue

                record = {
                    "date": date_str,
                    "close": close,
                    "symbol": symbol,
                }

                if open_str and open_str != "N/D":
                    try:
                        record["open"] = float(open_str)
                    except (TypeError, ValueError):
                        pass
                if high_str and high_str != "N/D":
                    try:
                        record["high"] = float(high_str)
                    except (TypeError, ValueError):
                        pass
                if low_str and low_str != "N/D":
                    try:
                        record["low"] = float(low_str)
                    except (TypeError, ValueError):
                        pass
                if vol_str and vol_str != "N/D":
                    try:
                        record["volume"] = int(float(vol_str))
                    except (TypeError, ValueError):
                        pass

                records.append(record)
            except (TypeError, ValueError, KeyError):
                continue
    except Exception as exc:
        logger.warning(f"[stooq] CSV parse error: {exc}")
        return []

    return records


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_historical_price(
    ticker: str,
    target_date: str,
    tolerance_days: int = 5,
) -> Optional[dict]:
    """Fetch the historical closing price nearest to target_date.

    Parameters
    ----------
    ticker : str
        Stock ticker (e.g. "AAPL").
    target_date : str
        Target date in YYYY-MM-DD format.
    tolerance_days : int
        How many days before target_date to search (finds nearest previous trading day).

    Returns
    -------
    dict with keys: date, close, symbol, source ("stooq"), or None on failure.
    """
    symbol = normalize_symbol(ticker)
    if not symbol:
        logger.warning(f"[stooq] Invalid ticker: {ticker}")
        return None

    cache_key = f"stooq:{symbol}:{target_date}"
    cached = stooq_cache.get(cache_key)
    if cached is not None:
        return cached

    # Build date range: from (target_date - tolerance) to target_date
    try:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        logger.warning(f"[stooq] Invalid date format: {target_date}")
        return None

    from_dt = target_dt - timedelta(days=tolerance_days + 3)  # extra buffer for weekends
    from_date = from_dt.strftime("%Y-%m-%d")

    url = _build_url(symbol)
    url += f"&d1={from_date}&d2={target_date}"

    # Validate URL safety
    ok, reason = validate_url(url)
    if not ok:
        logger.warning(f"[stooq] URL validation failed: {reason}")
        return None

    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Finora/2.0"})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                raw_csv = resp.read().decode("utf-8")

            # Detect bot protection / HTML challenge pages
            if raw_csv.strip().startswith("<!DOCTYPE") or raw_csv.strip().startswith("<html") or "noscript" in raw_csv[:500].lower():
                logger.warning(f"[stooq] Bot protection detected for {symbol} — Stooq is unavailable as server-side fallback")
                stooq_cache.set(cache_key, None)
                return None

            records = _parse_csv(raw_csv, symbol)

            if not records:
                logger.info(f"[stooq] No data returned for {symbol} near {target_date}")
                stooq_cache.set(cache_key, None)
                return None

            # Find the record closest to but not after target_date
            best = None
            for rec in records:
                try:
                    rec_dt = datetime.strptime(rec["date"], "%Y-%m-%d")
                    if rec_dt <= target_dt:
                        if best is None or rec_dt > datetime.strptime(best["date"], "%Y-%m-%d"):
                            best = rec
                except (ValueError, KeyError):
                    continue

            if best is None:
                # Take the earliest record as fallback
                if records:
                    best = min(records, key=lambda r: r.get("date", ""))

            if best:
                best["source"] = "stooq"
                best["type"] = "historical_fallback"
                stooq_cache.set(cache_key, best)
                logger.info(f"[stooq] Got price for {symbol} on {best['date']}: ${best['close']}")
                return best

            stooq_cache.set(cache_key, None)
            return None

        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                time.sleep(RETRY_BACKOFF * (2 ** attempt))
            else:
                logger.warning(f"[stooq] HTTP {exc.code} for {symbol}")
                return None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning(f"[stooq] Network error for {symbol}: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF)
            else:
                return None
        except Exception as exc:
            logger.warning(f"[stooq] Unexpected error for {symbol}: {exc}")
            return None

    return None


def fetch_historical_series(
    ticker: str,
    from_date: str,
    to_date: Optional[str] = None,
) -> list[dict]:
    """Fetch a series of historical daily prices.

    Returns a list of price records sorted by date (oldest first).
    Used for charting when Twelve Data is unavailable.
    """
    symbol = normalize_symbol(ticker)
    if not symbol:
        return []

    to_date = to_date or datetime.now().strftime("%Y-%m-%d")

    cache_key = f"stooq:series:{symbol}:{from_date}:{to_date}"
    cached = stooq_cache.get(cache_key)
    if cached is not None:
        return cached

    url = _build_url(symbol)
    url += f"&d1={from_date}&d2={to_date}"

    ok, reason = validate_url(url)
    if not ok:
        return []

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Finora/2.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw_csv = resp.read().decode("utf-8")

        # Detect bot protection / HTML challenge pages
        if raw_csv.strip().startswith("<!DOCTYPE") or raw_csv.strip().startswith("<html") or "noscript" in raw_csv[:500].lower():
            logger.warning(f"[stooq] Bot protection detected for {symbol} — Stooq unavailable")
            stooq_cache.set(cache_key, [])
            return []

        records = _parse_csv(raw_csv, symbol)
        # Sort oldest first
        records.sort(key=lambda r: r.get("date", ""))

        for rec in records:
            rec["source"] = "stooq"
            rec["type"] = "historical_fallback"

        stooq_cache.set(cache_key, records)
        return records

    except Exception as exc:
        logger.warning(f"[stooq] Series fetch failed for {symbol}: {exc}")
        return []
