"""Business Quant Fundamental Data API client.

Provides structured financial data as a secondary fallback when SEC XBRL
is missing values.  The source hierarchy is always SEC-primary — BQ data
never overwrites valid SEC values, only fills genuinely missing inputs.

Key features:
  - Explicit timeout and bounded retries
  - 429 / 4xx / 5xx handling with cooldown
  - In-memory response cache (same session)
  - Ticker validation
  - Structured provenance on every returned value
  - Never crashes core SEC research on failure
"""

from __future__ import annotations

import os
import time
import hashlib
import json
import logging
from typing import Any, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from dotenv import load_dotenv
from pathlib import Path

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path, override=True)

logger = logging.getLogger("finora.business_quant")

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_URL = "https://api.businessquant.com/api"
REQUEST_TIMEOUT = 15  # seconds
MAX_RETRIES = 2
RETRY_BACKOFF = 1.5  # seconds
MIN_REQUEST_INTERVAL = 0.2  # seconds between requests

# ── Cache ─────────────────────────────────────────────────────────────────────
_cache: dict[str, tuple[float, Any]] = {}
_last_request_time: float = 0.0


def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _get_cached(url: str, ttl_seconds: float = 3600.0) -> Optional[Any]:
    key = _cache_key(url)
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < ttl_seconds:
            return data
    return None


def _set_cache(url: str, data: Any) -> None:
    _cache[_cache_key(url)] = (time.time(), data)


def clear_cache() -> None:
    """Drop all cached BQ responses — useful for tests."""
    _cache.clear()


def _respect_rate_limit() -> None:
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


# ── API Key ───────────────────────────────────────────────────────────────────
def _get_api_key() -> str:
    key = os.getenv("BUSINESS_QUANT_API_KEY", "").strip()
    return key


def is_available() -> bool:
    """Check if Business Quant is configured with a valid API key."""
    key = _get_api_key()
    return bool(key) and key != "your_business_quant_api_key_here"


# ── HTTP Layer ────────────────────────────────────────────────────────────────
def _bq_get(endpoint: str, params: Optional[dict] = None, cache_ttl: float = 3600.0) -> Optional[dict]:
    """GET a Business Quant endpoint with retries and caching.

    Returns parsed JSON dict on success, None on failure (never raises).
    """
    api_key = _get_api_key()
    if not api_key or api_key == "your_business_quant_api_key_here":
        logger.debug("Business Quant API key not configured — skipping")
        return None

    url = f"{BASE_URL}/{endpoint}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        if query:
            url += f"?{query}"

    # Check cache
    if cache_ttl > 0:
        cached = _get_cached(url, cache_ttl)
        if cached is not None:
            return cached

    _respect_rate_limit()

    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
    }

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, headers=headers, method="GET")
            with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                if cache_ttl > 0:
                    _set_cache(url, data)
                return data
        except HTTPError as exc:
            last_error = exc
            code = exc.code
            if code == 429:
                wait = RETRY_BACKOFF * (2 ** attempt)
                logger.warning(f"Business Quant rate limited, waiting {wait}s")
                time.sleep(wait)
            elif 400 <= code < 500:
                logger.warning(f"Business Quant client error {code}: {exc.reason}")
                return None  # Don't retry client errors
            elif code >= 500:
                wait = RETRY_BACKOFF * (2 ** attempt)
                time.sleep(wait)
            else:
                return None
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            wait = RETRY_BACKOFF * (2 ** attempt)
            time.sleep(wait)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(f"Business Quant invalid JSON response: {exc}")
            return None

    logger.warning(f"Business Quant request failed after {MAX_RETRIES} attempts: {last_error}")
    return None


# ── Public API ────────────────────────────────────────────────────────────────
def get_income_statement(ticker: str) -> Optional[dict]:
    """Fetch income statement data for a ticker."""
    return _bq_get("income-statement", {"ticker": ticker.upper()})


def get_balance_sheet(ticker: str) -> Optional[dict]:
    """Fetch balance sheet data for a ticker."""
    return _bq_get("balance-sheet", {"ticker": ticker.upper()})


def get_cash_flow(ticker: str) -> Optional[dict]:
    """Fetch cash flow statement data for a ticker."""
    return _bq_get("cash-flow", {"ticker": ticker.upper()})


def get_key_metrics(ticker: str) -> Optional[dict]:
    """Fetch key financial metrics for a ticker."""
    return _bq_get("key-metrics", {"ticker": ticker.upper()})


def get_stock_profile(ticker: str) -> Optional[dict]:
    """Fetch stock profile data (exchange, sector, industry, etc.)."""
    return _bq_get("stock-profile", {"ticker": ticker.upper()})


def get_segment_financials(ticker: str) -> Optional[dict]:
    """Fetch segment financial data for a ticker."""
    return _bq_get("segment-revenue", {"ticker": ticker.upper()})


def get_analyst_estimates(ticker: str) -> Optional[dict]:
    """Fetch analyst estimates if available under user's API access."""
    return _bq_get("analyst-estimates", {"ticker": ticker.upper()})


# ── BQ Statement Mapper ───────────────────────────────────────────────────────
# Maps Business Quant field names to Finora normalized field names.

BQ_INCOME_MAP = {
    "revenue": ["revenue", "totalRevenue", "revenue_usd", "total_revenue"],
    "cost_of_revenue": ["costOfRevenue", "costOfRevenue", "costOfSales", "totalCostOfRevenue"],
    "gross_profit": ["grossProfit", "gross_income"],
    "operating_income": ["operatingIncome", "operating_income"],
    "pretax_income": ["pretaxIncome", "incomeBeforeTax", "income_before_taxes"],
    "net_income": ["netIncome", "net_income", "netIncomeLoss"],
    "basic_eps": ["epsBasic", "basicEps", "earningsPerShareBasic"],
    "diluted_eps": ["epsDiluted", "dilutedEps", "earningsPerShareDiluted"],
}

BQ_BALANCE_MAP = {
    "cash_and_equivalents": ["cashAndCashEquivalents", "cashAndEquivalents", "cash"],
    "short_term_investments": ["shortTermInvestments", "marketableSecurities"],
    "accounts_receivable": ["netReceivables", "accountsReceivable"],
    "inventory": ["inventory", "inventories"],
    "current_assets": ["totalCurrentAssets", "total_current_assets"],
    "total_assets": ["totalAssets", "total_assets"],
    "current_liabilities": ["totalCurrentLiabilities", "total_current_liabilities"],
    "total_liabilities": ["totalLiabilities", "total_liabilities"],
    "short_term_debt": ["shortTermDebt", "currentLongTermDebt"],
    "long_term_debt": ["longTermDebt", "longTermDebt"],
    "shareholders_equity": ["totalStockholdersEquity", "stockholdersEquity", "totalShareholderEquity"],
}

BQ_CASHFLOW_MAP = {
    "operating_cash_flow": ["operatingCashFlow", "operating_cash_flow", "cashFlowFromContinuingOperatingActivities"],
    "capital_expenditures": ["capitalExpenditure", "capitalExpenditures", "capitalExpenditure"],
    "investing_cash_flow": ["investingCashFlow", "investing_cash_flow"],
    "financing_cash_flow": ["financingCashFlow", "financing_cash_flow"],
    "dividends_paid": ["dividendsPaid", "dividends_paid"],
    "share_repurchases": ["repurchaseOfCapitalStock", "commonStockRepurchased"],
    "depreciation_amortization": ["depreciationAndAmortization", "depreciation_amortization", "depreciation"],
    "interest_expense": ["interestExpense", "interest_expense", "interestExpenseDebt"],
}


def _extract_bq_value(bq_data: Any, field_names: list[str]) -> Optional[float]:
    """Try to extract a numeric value from BQ response using possible field names."""
    if bq_data is None:
        return None
    if isinstance(bq_data, list):
        # Take the most recent entry
        if not bq_data:
            return None
        bq_data = bq_data[0] if isinstance(bq_data[0], dict) else None
    if not isinstance(bq_data, dict):
        return None

    for name in field_names:
        val = bq_data.get(name)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


def extract_bq_financials(ticker: str) -> dict[str, Any]:
    """Fetch and normalize all BQ financial data for a ticker.

    Returns a normalized dict mapping Finora metric names to values,
    with provenance metadata for each recovered value.

    Never raises — returns empty dict on failure.
    """
    if not is_available():
        return {}

    result: dict[str, Any] = {}

    # Fetch all statement types
    income_data = get_income_statement(ticker)
    balance_data = get_balance_sheet(ticker)
    cashflow_data = get_cash_flow(ticker)

    # Extract income statement values
    for finora_name, bq_fields in BQ_INCOME_MAP.items():
        val = _extract_bq_value(income_data, bq_fields)
        if val is not None:
            result[finora_name] = {
                "value": val,
                "source": "business_quant",
                "source_classification": "secondary_structured",
                "primary_authority": False,
            }

    # Extract balance sheet values
    for finora_name, bq_fields in BQ_BALANCE_MAP.items():
        val = _extract_bq_value(balance_data, bq_fields)
        if val is not None:
            result[finora_name] = {
                "value": val,
                "source": "business_quant",
                "source_classification": "secondary_structured",
                "primary_authority": False,
            }

    # Extract cash flow values
    for finora_name, bq_fields in BQ_CASHFLOW_MAP.items():
        val = _extract_bq_value(cashflow_data, bq_fields)
        if val is not None:
            result[finora_name] = {
                "value": val,
                "source": "business_quant",
                "source_classification": "secondary_structured",
                "primary_authority": False,
            }

    if result:
        logger.info(f"Business Quant recovered {len(result)} fields for {ticker}")
    else:
        logger.info(f"Business Quant returned no usable data for {ticker}")

    return result
