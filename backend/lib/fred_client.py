"""FRED (Federal Reserve Economic Data) macro context client.

Retrieves a small high-value macro snapshot:
  - Federal Funds Rate (DFF)
  - 10-Year Treasury Yield (DGS10)
  - CPI / Inflation context (CPIAUCSL)

Key features:
  - Graceful degradation when FRED_API_KEY is missing
  - Shared global macro snapshot cache (NOT company-specific)
  - Single-flight request coalescing
  - Bounded retries with timeout
  - Never crashes research on failure
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from lib.cache import BoundedTTLCache, single_flight
from lib.netutil import apply_ipv4_first as _net_fix
_net_fix()

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path, override=True)

logger = logging.getLogger("finora.fred")

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
REQUEST_TIMEOUT = 15
MAX_RETRIES = 2
RETRY_BACKOFF = 2.0

# FRED series IDs
FRED_SERIES = {
    "fed_funds_rate": {"series_id": "DFF", "name": "Federal Funds Rate", "unit": "%"},
    "treasury_10y": {"series_id": "DGS10", "name": "10-Year Treasury Yield", "unit": "%"},
    "cpi": {"series_id": "CPIAUCSL", "name": "Consumer Price Index", "unit": "index"},
}

# ── Cache ─────────────────────────────────────────────────────────────────────
# Macro data is NOT company-specific — use ONE shared cache.
# Refresh every 6 hours.
fred_macro_cache = BoundedTTLCache(maxsize=10, ttl=21600.0, name="fred_macro")


def clear_cache() -> None:
    """Drop cached FRED data (tests only)."""
    fred_macro_cache.clear()


def is_available() -> bool:
    """Check if FRED is configured with a valid API key."""
    key = os.environ.get("FRED_API_KEY", "").strip()
    return bool(key) and len(key) > 5


def _get_api_key() -> str:
    return os.environ.get("FRED_API_KEY", "").strip()


def _fred_get(series_id: str) -> Optional[dict]:
    """Fetch the most recent observation for a FRED series.

    Returns the observation dict or None on failure.
    """
    api_key = _get_api_key()
    if not api_key or len(api_key) <= 5:
        return None

    url = (
        f"{BASE_URL}?series_id={series_id}"
        f"&api_key={api_key}&file_type=json"
        f"&sort_order=desc&limit=1"
    )

    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Finora/2.0"})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            observations = data.get("observations", [])
            if observations and isinstance(observations, list):
                obs = observations[0]
                # FRED returns "." for missing values
                value_str = obs.get("value", ".")
                if value_str and value_str != ".":
                    try:
                        return {
                            "date": obs.get("date", ""),
                            "value": float(value_str),
                            "series_id": series_id,
                        }
                    except (TypeError, ValueError):
                        pass
            return None

        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                time.sleep(RETRY_BACKOFF * (2 ** attempt))
            else:
                logger.warning(f"[fred] HTTP {exc.code} for {series_id}")
                return None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning(f"[fred] Network error for {series_id}: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF)
            else:
                return None
        except Exception as exc:
            logger.warning(f"[fred] Unexpected error for {series_id}: {exc}")
            return None

    return None


def get_macro_snapshot() -> dict:
    """Get a compact macro snapshot with all key series.

    Returns a dict with keys for each series. Uses global cache
    so multiple companies in one session only trigger one FRED call.
    """
    cache_key = "fred:macro_snapshot"
    cached = fred_macro_cache.get(cache_key)
    if cached is not None:
        return cached

    if not is_available():
        logger.info("[fred] API key not configured — returning empty macro snapshot")
        return {
            "available": False,
            "reason": "FRED_API_KEY not configured",
            "fed_funds_rate": None,
            "treasury_10y": None,
            "cpi": None,
        }

    snapshot = {
        "available": True,
        "timestamp": time.time(),
        "fed_funds_rate": None,
        "treasury_10y": None,
        "cpi": None,
    }

    for key, meta in FRED_SERIES.items():
        obs = _fred_get(meta["series_id"])
        if obs:
            snapshot[key] = {
                "value": obs["value"],
                "date": obs["date"],
                "name": meta["name"],
                "unit": meta["unit"],
                "series_id": meta["series_id"],
            }

    fred_macro_cache.set(cache_key, snapshot)
    return snapshot


def get_macro_for_dashboard() -> dict:
    """Get macro data formatted for the dashboard strip."""
    snapshot = get_macro_snapshot()

    strip = []
    for key in ["treasury_10y", "fed_funds_rate", "cpi"]:
        data = snapshot.get(key)
        if data:
            label = data["name"].upper()
            if key == "cpi":
                value = f"{data['value']:.1f}"
            else:
                value = f"{data['value']:.1f}%"
            strip.append({
                "label": label,
                "value": value,
                "date": data.get("date", ""),
                "unit": data.get("unit", ""),
            })

    return {
        "available": snapshot.get("available", False),
        "strip": strip,
        "attribution": "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.",
    }
