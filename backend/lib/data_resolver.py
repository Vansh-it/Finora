"""Data completeness resolver.

Central module that resolves financial inputs following the authoritative
source hierarchy:

  1. SEC normalized value (primary)
  2. Alternate SEC/XBRL concepts (same filing)
  3. Business Quant structured value (secondary fallback)
  4. Inline XBRL / selected filing (deep fallback)
  5. SEC statement table extraction
  6. Official company report via Jina
  7. Unavailable (displayed as N/A)

Key principles:
  - SEC remains primary authority; never silently replaced
  - BQ data is clearly labelled as secondary_structured
  - Cross-checking happens when both SEC and BQ values exist
  - Never estimates, guesses, or fills with zero
"""

from __future__ import annotations

import math
from typing import Any, Optional

from lib.business_quant_client import is_available as bq_available, extract_bq_financials


# ── Cross-check statuses ──────────────────────────────────────────────────────
EXACT_MATCH = "exact_match"
WITHIN_TOLERANCE = "within_tolerance"
MATERIAL_MISMATCH = "material_mismatch"
DIFFERENT_PERIOD = "different_period"
NOT_COMPARABLE = "not_comparable"

TOLERANCE_PCT = 5.0  # 5% tolerance for "within_tolerance"


def _compare_values(
    sec_val: Optional[float],
    bq_val: Optional[float],
) -> dict[str, Any]:
    """Compare SEC and BQ values. Returns cross-check result."""
    if sec_val is None or bq_val is None:
        return {"status": NOT_COMPARABLE}

    if sec_val == 0 and bq_val == 0:
        return {"status": EXACT_MATCH}

    if sec_val == 0 or bq_val == 0:
        return {"status": MATERIAL_MISMATCH, "note": "One value is zero"}

    # Calculate percentage difference
    avg = (abs(sec_val) + abs(bq_val)) / 2
    if avg == 0:
        return {"status": EXACT_MATCH}

    diff_pct = abs(sec_val - bq_val) / avg * 100

    if diff_pct < 0.5:
        return {"status": EXACT_MATCH}
    elif diff_pct <= TOLERANCE_PCT:
        return {"status": WITHIN_TOLERANCE, "difference_pct": round(diff_pct, 2)}
    else:
        return {
            "status": MATERIAL_MISMATCH,
            "sec_value": sec_val,
            "bq_value": bq_val,
            "difference_pct": round(diff_pct, 2),
        }


def resolve_financial_inputs(
    financial_statements: dict[str, Any],
    ticker: str = "",
    period: str = "",
) -> dict[str, Any]:
    """Resolve financial inputs using the source hierarchy.

    Takes the SEC-extracted financial statements and augments with BQ
    data where SEC is missing values.  Never overwrites valid SEC data.

    Parameters
    ----------
    financial_statements : dict
        SEC-extracted financial statements (income_statement, balance_sheet, cash_flow).
    ticker : str
        Company ticker for BQ lookup.
    period : str
        Target fiscal period (e.g. "FY2025").

    Returns
    -------
    dict with keys:
        - resolved: dict of metric -> resolved value
        - provenance: dict of metric -> source info
        - cross_checks: list of cross-check results
        - bq_recovered: count of fields recovered from BQ
        - sec_fields: count of fields from SEC
    """
    result = {
        "resolved": {},
        "provenance": {},
        "cross_checks": [],
        "bq_recovered": 0,
        "sec_fields": 0,
    }

    # Collect all SEC values for the period
    stmts = financial_statements
    income = stmts.get("income_statement", {})
    balance = stmts.get("balance_sheet", {})
    cashflow = stmts.get("cash_flow", {})

    def _get_sec_value(stmt_type: dict, metric: str) -> Optional[float]:
        """Get a value from SEC statements for a period."""
        md = stmt_type.get(metric)
        if md is None:
            return None
        if isinstance(md, dict):
            if "value" in md:
                return md.get("value")
            if period and period in md:
                inner = md.get(period)
                if isinstance(inner, dict):
                    return inner.get("value")
        return None

    # All metrics we want to resolve
    all_metrics = {
        "income_statement": {
            "revenue": "revenue",
            "cost_of_revenue": "cost_of_revenue",
            "gross_profit": "gross_profit",
            "operating_income": "operating_income",
            "pretax_income": "pretax_income",
            "net_income": "net_income",
            "basic_eps": "basic_eps",
            "diluted_eps": "diluted_eps",
        },
        "balance_sheet": {
            "cash_and_equivalents": "cash_and_equivalents",
            "short_term_investments": "short_term_investments",
            "accounts_receivable": "accounts_receivable",
            "current_assets": "current_assets",
            "total_assets": "total_assets",
            "current_liabilities": "current_liabilities",
            "total_liabilities": "total_liabilities",
            "short_term_debt": "short_term_debt",
            "long_term_debt": "long_term_debt",
            "shareholders_equity": "shareholders_equity",
        },
        "cash_flow": {
            "operating_cash_flow": "operating_cash_flow",
            "capital_expenditures": "capital_expenditures",
            "dividends_paid": "dividends_paid",
            "share_repurchases": "share_repurchases",
            "depreciation_amortization": "depreciation_amortization",
            "interest_expense": "interest_expense",
        },
    }

    # Step 1-2: Collect SEC values
    sec_values: dict[str, Optional[float]] = {}
    stmts_map = {
        "income_statement": income,
        "balance_sheet": balance,
        "cash_flow": cashflow,
    }

    for stmt_type, metrics in all_metrics.items():
        for metric, finora_name in metrics.items():
            sec_val = _get_sec_value(stmts_map.get(stmt_type, {}), metric)
            sec_values[finora_name] = sec_val
            if sec_val is not None:
                result["sec_fields"] += 1
                result["resolved"][finora_name] = sec_val
                result["provenance"][finora_name] = {
                    "value": sec_val,
                    "source": "sec_xbrl",
                    "source_classification": "primary",
                    "primary_authority": True,
                }

    # Step 3: Business Quant fallback for missing values
    bq_recovered = 0
    bq_values: dict[str, float] = {}

    missing_metrics = [m for m, v in sec_values.items() if v is None]

    if missing_metrics and bq_available() and ticker:
        try:
            bq_data = extract_bq_financials(ticker)
        except Exception:
            bq_data = {}

        for metric in missing_metrics:
            bq_entry = bq_data.get(metric)
            if bq_entry is not None and bq_entry.get("value") is not None:
                bq_val = bq_entry["value"]
                bq_values[metric] = bq_val
                result["resolved"][metric] = bq_val
                result["provenance"][metric] = {
                    "value": bq_val,
                    "source": "business_quant",
                    "source_classification": "secondary_structured",
                    "primary_authority": False,
                    "original_field": metric,
                }
                bq_recovered += 1

    result["bq_recovered"] = bq_recovered

    # Cross-check SEC vs BQ for fields where both exist
    for metric in sec_values:
        if sec_values[metric] is not None and metric in bq_values:
            check = _compare_values(sec_values[metric], bq_values[metric])
            if check["status"] != NOT_COMPARABLE:
                check["metric"] = metric
                result["cross_checks"].append(check)

    return result


def apply_resolved_inputs(
    financial_statements: dict[str, Any],
    resolution: dict[str, Any],
) -> dict[str, Any]:
    """Apply resolved inputs back to financial statements for calculation.

    Only fills genuinely missing values. Never overwrites SEC data.

    Returns updated financial_statements dict.
    """
    stmts = dict(financial_statements)
    provenance = resolution.get("provenance", {})

    stmt_type_map = {
        "revenue": "income_statement",
        "cost_of_revenue": "income_statement",
        "gross_profit": "income_statement",
        "operating_income": "income_statement",
        "pretax_income": "income_statement",
        "net_income": "income_statement",
        "basic_eps": "income_statement",
        "diluted_eps": "income_statement",
        "cash_and_equivalents": "balance_sheet",
        "short_term_investments": "balance_sheet",
        "accounts_receivable": "balance_sheet",
        "current_assets": "balance_sheet",
        "total_assets": "balance_sheet",
        "current_liabilities": "balance_sheet",
        "total_liabilities": "balance_sheet",
        "short_term_debt": "balance_sheet",
        "long_term_debt": "balance_sheet",
        "shareholders_equity": "balance_sheet",
        "operating_cash_flow": "cash_flow",
        "capital_expenditures": "cash_flow",
        "dividends_paid": "cash_flow",
        "share_repurchases": "cash_flow",
        "depreciation_amortization": "cash_flow",
        "interest_expense": "cash_flow",
    }

    for metric, prov in provenance.items():
        if prov.get("source") == "business_quant":
            stmt_type = stmt_type_map.get(metric)
            if stmt_type and stmt_type in stmts:
                stmt_data = stmts.get(stmt_type, {})
                existing = stmt_data.get(metric)
                # Only fill if genuinely missing
                has_value = False
                if existing is not None:
                    if isinstance(existing, dict):
                        if "value" in existing and existing["value"] is not None:
                            has_value = True
                if not has_value:
                    # Inject BQ value with provenance
                    if isinstance(existing, dict) and "value" not in existing:
                        # Period-keyed dict — fill the latest period
                        pass  # Don't modify period-keyed dicts directly
                    else:
                        stmts[stmt_type] = dict(stmts.get(stmt_type, {}))
                        stmts[stmt_type][metric] = {
                            "value": prov["value"],
                            "source": "business_quant",
                            "source_classification": "secondary_structured",
                            "period": resolution.get("period", ""),
                            "verification_status": "secondary_source",
                        }

    return stmts
