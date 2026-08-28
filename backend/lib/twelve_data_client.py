"""Twelve Data API client.

Fetches market data (price, shares outstanding, market cap) for tickers.
Uses caching and retry to protect free-tier quota.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

# ── Cache ────────────────────────────────────────────────────────────────────
_cache: dict[str, dict] = {}
_cache_ttl = 3600  # 1 hour
_historical_cache_ttl = 86400 * 30  # 30 days for historical (prices don't change)


def _get_api_key() -> str:
    key = os.environ.get("TWELVE_DATA_API_KEY", "")
    if not key:
        raise RuntimeError("TWELVE_DATA_API_KEY not configured")
    return key


def _cache_get(url: str) -> Optional[dict]:
    entry = _cache.get(url)
    if entry:
        # Use longer TTL for historical data
        ttl = _historical_cache_ttl if "historical:" in url else _cache_ttl
        if (time.time() - entry["ts"]) < ttl:
            return entry["data"]
    return None


def _cache_set(url: str, data: dict) -> None:
    _cache[url] = {"data": data, "ts": time.time()}


def clear_cache() -> None:
    """Clear all cached responses (for tests)."""
    _cache.clear()


# ── API calls ────────────────────────────────────────────────────────────────

def fetch_quote(ticker: str, retries: int = 1, timeout: int = 8) -> dict:
    """Fetch real-time quote for a ticker."""
    cached = _cache_get(f"quote:{ticker}")
    if cached:
        return cached

    api_key = _get_api_key()
    url = (
        f"https://api.twelvedata.com/quote?"
        f"symbol={ticker}&apikey={api_key}"
    )

    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Finora/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())

            if isinstance(data, dict) and "code" in data and "message" in data:
                raise ValueError(f"Twelve Data error: {data['message']}")

            _cache_set(f"quote:{ticker}", data)
            return data

        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code == 429:
                time.sleep(min(2 ** attempt, 4))
            elif exc.code >= 500:
                time.sleep(1)
            else:
                raise ValueError(f"Twelve Data HTTP {exc.code}")
        except urllib.error.URLError as exc:
            last_err = exc
            time.sleep(1)
        except json.JSONDecodeError as exc:
            last_err = exc
            break

    raise RuntimeError(f"Twelve Data request failed after {retries + 1} attempts: {last_err}")


def fetch_time_series(
    ticker: str,
    interval: str = "1day",
    outputsize: int = 30,
    retries: int = 1,
    timeout: int = 8,
) -> dict:
    """Fetch time series data for a ticker.

    Returns dict with 'values' list of {datetime, open, high, low, close, volume}.
    """
    cached = _cache_get(f"ts:{ticker}:{interval}:{outputsize}")
    if cached:
        return cached

    api_key = _get_api_key()
    url = (
        f"https://api.twelvedata.com/time_series?"
        f"symbol={ticker}&interval={interval}"
        f"&outputsize={outputsize}&apikey={api_key}"
    )

    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Finora/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())

            if isinstance(data, dict) and "code" in data and "message" in data:
                raise ValueError(f"Twelve Data error: {data['message']}")

            _cache_set(f"ts:{ticker}:{interval}:{outputsize}", data)
            return data

        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code == 429:
                time.sleep(min(2 ** attempt, 4))
            elif exc.code >= 500:
                time.sleep(1)
            else:
                raise ValueError(f"Twelve Data HTTP {exc.code}")
        except urllib.error.URLError as exc:
            last_err = exc
            time.sleep(1)
        except json.JSONDecodeError as exc:
            last_err = exc
            break

    raise RuntimeError(f"Twelve Data request failed after {retries + 1} attempts: {last_err}")


def fetch_historical_price(
    ticker: str,
    target_date: str,
    retries: int = 1,
    timeout: int = 8,
) -> Optional[dict]:
    """Fetch the closing price at or immediately before a target date.

    Uses Twelve Data time_series endpoint with date range.
    target_date should be YYYY-MM-DD format.

    Returns:
        {"close": 123.45, "date": "2023-06-30", "source": "Twelve Data"}
        or None if unavailable.
    """
    cache_key = f"historical:{ticker}:{target_date}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    api_key = _get_api_key()

    # Request a window around the target date to handle non-trading days
    # Go back up to 10 calendar days to cover weekends + holidays
    try:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        return None

    start_dt = target_dt - timedelta(days=10)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = target_dt.strftime("%Y-%m-%d")

    url = (
        f"https://api.twelvedata.com/time_series?"
        f"symbol={ticker}&interval=1day"
        f"&start_date={start_str}&end_date={end_str}"
        f"&apikey={api_key}"
    )

    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Finora/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())

            if isinstance(data, dict) and "code" in data and "message" in data:
                raise ValueError(f"Twelve Data error: {data['message']}")

            values = data.get("values", [])
            if not values:
                result = None
                _cache_set(cache_key, result or {"_empty": True})
                return None

            # Find the closest date on or before target_date
            # Values are typically sorted newest-first from Twelve Data
            best = None
            best_date = None
            for v in values:
                dt_str = v.get("datetime", "")
                if dt_str <= end_str and dt_str >= start_str:
                    if best is None or dt_str > best_date:
                        best = v
                        best_date = dt_str

            if best is None:
                _cache_set(cache_key, {"_empty": True})
                return None

            close_val = None
            if "close" in best:
                try:
                    close_val = float(best["close"])
                except (TypeError, ValueError):
                    pass

            if close_val is None:
                _cache_set(cache_key, {"_empty": True})
                return None

            result = {
                "close": close_val,
                "date": best_date,
                "source": "Twelve Data",
            }
            _cache_set(cache_key, result)
            return result

        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code == 429:
                time.sleep(min(2 ** attempt, 4))
            elif exc.code >= 500:
                time.sleep(1)
            else:
                raise ValueError(f"Twelve Data HTTP {exc.code}")
        except urllib.error.URLError as exc:
            last_err = exc
            time.sleep(1)
        except (json.JSONDecodeError, ValueError) as exc:
            last_err = exc
            break

    raise RuntimeError(f"Twelve Data historical request failed: {last_err}")


def get_market_snapshot(ticker: str) -> dict:
    """Get a normalized market snapshot for a ticker."""
    try:
        quote = fetch_quote(ticker)
    except Exception as exc:
        return {
            "ticker": ticker,
            "name": "",
            "exchange": "",
            "currency": "USD",
            "price": None,
            "price_date": "",
            "previous_close": None,
            "percent_change": None,
            "shares_outstanding": None,
            "market_cap": None,
            "source": "Twelve Data",
            "error": str(exc),
        }

    close_val = None
    if "close" in quote:
        try:
            close_val = float(quote["close"])
        except (TypeError, ValueError):
            pass

    prev_close = None
    if "previous_close" in quote:
        try:
            prev_close = float(quote["previous_close"])
        except (TypeError, ValueError):
            pass

    pct_change = None
    if "percent_change" in quote:
        try:
            pct_change = float(quote["percent_change"])
        except (TypeError, ValueError):
            pass

    ts = quote.get("timestamp")
    price_date = ""
    if ts:
        try:
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            price_date = dt.strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError):
            pass

    shares = None
    for field in ["shares_outstanding", "shares Outstanding"]:
        if field in quote:
            try:
                shares = float(quote[field])
            except (TypeError, ValueError):
                pass

    market_cap = None
    for field in ["market_capitalization", "market_cap"]:
        if field in quote:
            try:
                market_cap = float(quote[field])
            except (TypeError, ValueError):
                pass

    return {
        "ticker": quote.get("symbol", ticker),
        "name": quote.get("name", ""),
        "exchange": quote.get("exchange", ""),
        "currency": quote.get("currency", "USD"),
        "price": close_val,
        "price_date": price_date,
        "previous_close": prev_close,
        "percent_change": pct_change,
        "shares_outstanding": shares,
        "market_cap": market_cap,
        "source": "Twelve Data",
        "timestamp": ts,
    }
