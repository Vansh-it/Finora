"""Cross-source verification engine.

Compares external financial facts (from Jina/LLM extraction) against
Finora's authoritative SEC/XBRL facts. Determines whether each source:
  - confirms the SEC value
  - differs from the SEC value
  - is not comparable
  - does not contain the metric

SEC XBRL remains the primary numeric authority unless stronger logic
explicitly determines otherwise.
"""

from __future__ import annotations

import re
from typing import Any, Optional


# ── Tolerance thresholds ──────────────────────────────────────────────────────
# For values that may be presented differently (billions vs full dollars)
RELATIVE_TOLERANCE = 0.02  # 2% tolerance for rounding differences
ABSOLUTE_TOLERANCE_USD = 5_000_000  # $5M absolute tolerance for large values
ABSOLUTE_TOLERANCE_EPS = 0.10  # $0.10 tolerance for per-share values

# ── Verification statuses ─────────────────────────────────────────────────────
EXACT_MATCH = "exact_match"
WITHIN_TOLERANCE = "within_tolerance"
MISMATCH = "mismatch"
NOT_COMPARABLE = "not_comparable"
MISSING_EXTERNAL = "missing_external"
MISSING_SEC = "missing_sec"


# ── Unit normalization ────────────────────────────────────────────────────────
def _normalize_to_raw(value: float, unit_hint: str = "", context: str = "") -> Optional[float]:
    """Normalize a value that might be in billions/millions to raw dollars.

    Uses heuristics based on magnitude and context.
    """
    if value is None:
        return None

    abs_val = abs(value)

    # If the value looks like raw dollars (billions scale for large companies)
    # e.g., 331_839_000_000
    if abs_val > 1_000_000_000:
        return value

    # If the value looks like it's in billions (e.g., 331.8)
    if abs_val < 10_000 and "revenue" in (context + unit_hint).lower():
        return value * 1_000_000_000

    # If the value looks like it's in millions (e.g., 331839)
    if abs_val > 100_000 and abs_val < 10_000_000:
        # Could be millions — check if context suggests it
        if any(kw in (context + unit_hint).lower() for kw in ["revenue", "income", "assets", "cash", "debt"]):
            return value * 1_000_000

    # Return as-is if we can't determine
    return value


def _normalize_external_value(
    ext_value: float,
    sec_value: float,
    metric_id: str,
) -> float:
    """Normalize an external value to match SEC scale for comparison.

    If SEC is in raw dollars and external looks like billions,
    scale external to raw dollars.
    """
    if ext_value is None or sec_value is None:
        return ext_value

    abs_ext = abs(ext_value)
    abs_sec = abs(sec_value)

    # If both are already similar magnitude, no normalization needed
    if abs_sec > 0 and 0.1 < abs_ext / abs_sec < 10:
        return ext_value

    # If SEC is in billions scale and external is raw
    if abs_sec > 1_000_000_000 and abs_ext < 1_000_000_000:
        # External might be in millions
        if abs_ext > 100_000:
            return ext_value * 1_000_000
        # External might be in billions
        if abs_ext > 10:
            return ext_value * 1_000_000_000

    # If SEC is small (like EPS) and external is similar
    if abs_sec < 1000 and abs_ext < 1000:
        return ext_value

    return ext_value


# ── Comparison logic ──────────────────────────────────────────────────────────
def _compare_values(
    sec_value: Optional[float],
    ext_value: Optional[float],
    metric_id: str,
) -> dict:
    """Compare a SEC value against an external value.

    Returns a verification result dict.
    """
    if sec_value is None and ext_value is None:
        return {"verification_status": NOT_COMPARABLE, "reason": "Both values missing"}

    if sec_value is None:
        return {"verification_status": MISSING_SEC, "reason": "No SEC/XBRL value available"}

    if ext_value is None:
        return {"verification_status": MISSING_EXTERNAL, "reason": "External source does not contain this metric"}

    # Normalize external value to SEC scale
    ext_normalized = _normalize_external_value(ext_value, sec_value, metric_id)

    # Calculate difference
    diff = abs(ext_normalized - sec_value)
    diff_pct = (diff / abs(sec_value) * 100) if sec_value != 0 else 0

    # Determine tolerance based on metric type
    is_eps = "eps" in metric_id.lower()
    if is_eps:
        absolute_tol = ABSOLUTE_TOLERANCE_EPS
    else:
        absolute_tol = ABSOLUTE_TOLERANCE_USD

    # Check exact match (within floating point)
    if diff == 0:
        return {
            "verification_status": EXACT_MATCH,
            "difference": 0,
            "difference_pct": 0,
        }

    # Check tolerance
    within_relative = diff_pct <= RELATIVE_TOLERANCE
    within_absolute = diff <= absolute_tol

    if within_relative or within_absolute:
        return {
            "verification_status": WITHIN_TOLERANCE,
            "difference": diff,
            "difference_pct": round(diff_pct, 2),
            "reason": "Within rounding tolerance",
        }

    # Material mismatch
    return {
        "verification_status": MISMATCH,
        "difference": diff,
        "difference_pct": round(diff_pct, 2),
        "reason": f"Material difference: {diff_pct:.1f}%",
    }


# ── Main verification function ────────────────────────────────────────────────
def verify_sources(
    sec_statements: dict,
    external_facts: list[dict],
    commentary: list[dict],
    company_name: str = "",
    ticker: str = "",
) -> dict:
    """Cross-verify external facts against SEC/XBRL financial statements.

    Parameters
    ----------
    sec_statements : dict
        Finora's extracted SEC financial statements (from financial_extractor).
    external_facts : list[dict]
        Facts extracted from external sources (via Jina + LLM).
    commentary : list[dict]
        Management commentary extracted from external sources.
    company_name, ticker : str
        Company identifiers.

    Returns
    -------
    dict
        Verification results with comparisons, mismatches, and evidence.
    """
    verifications: list[dict] = []
    matches = 0
    mismatches = 0
    not_comparable = 0

    # Build a lookup of SEC values by metric_id
    sec_lookup = _build_sec_lookup(sec_statements)

    # Process each external fact
    for ext_fact in external_facts:
        metric_id = ext_fact.get("metric_id", "")
        ext_value = ext_fact.get("value")
        period = ext_fact.get("period", "")

        if not metric_id:
            continue

        # Find corresponding SEC value
        sec_entry = sec_lookup.get(metric_id, {}).get(period)

        sec_value = None
        sec_period_type = ""
        if sec_entry:
            sec_value = sec_entry.get("value")
            sec_period_type = sec_entry.get("period_type", "annual")

        ext_period_type = ext_fact.get("period_type", "annual")

        # Check period comparability
        if sec_period_type and ext_period_type and sec_period_type != ext_period_type:
            verifications.append({
                "metric_id": metric_id,
                "period": period,
                "sec_value": sec_value,
                "external_value": ext_value,
                "verification_status": NOT_COMPARABLE,
                "reason": f"Period type mismatch: SEC={sec_period_type}, external={ext_period_type}",
                "primary_source": "SEC XBRL",
                "supporting_source": ext_fact.get("source_provider", ""),
                "external_evidence": ext_fact.get("evidence", ""),
            })
            not_comparable += 1
            continue

        # Compare values
        comparison = _compare_values(sec_value, ext_value, metric_id)

        result = {
            "metric_id": metric_id,
            "period": period,
            "sec_value": sec_value,
            "external_value": ext_value,
            "verification_status": comparison["verification_status"],
            "difference": comparison.get("difference"),
            "difference_pct": comparison.get("difference_pct"),
            "reason": comparison.get("reason", ""),
            "primary_source": "SEC XBRL",
            "supporting_source": ext_fact.get("source_provider", ""),
            "external_confidence": ext_fact.get("confidence", 0),
            "external_evidence": ext_fact.get("evidence", ""),
            "classification": ext_fact.get("classification", "reported"),
        }
        verifications.append(result)

        status = comparison["verification_status"]
        if status == EXACT_MATCH or status == WITHIN_TOLERANCE:
            matches += 1
        elif status == MISMATCH:
            mismatches += 1
        elif status == NOT_COMPARABLE:
            not_comparable += 1

    return {
        "verifications": verifications,
        "summary": {
            "total_compared": len(verifications),
            "exact_matches": matches,
            "within_tolerance": sum(1 for v in verifications if v["verification_status"] == WITHIN_TOLERANCE),
            "mismatches": mismatches,
            "not_comparable": not_comparable,
            "missing_external": sum(1 for v in verifications if v["verification_status"] == MISSING_EXTERNAL),
            "missing_sec": sum(1 for v in verifications if v["verification_status"] == MISSING_SEC),
        },
        "management_commentary": commentary,
        "primary_source": "SEC XBRL",
    }


# ── Helpers ──────────────────────────────────────────────────────────────────
def _build_sec_lookup(sec_statements: dict) -> dict[str, dict[str, dict]]:
    """Build a lookup of SEC values: {metric_id: {period: {value, period_type}}}."""
    lookup: dict[str, dict[str, dict]] = {}

    statements_map = {
        "income_statement": sec_statements.get("income_statement", {}),
        "balance_sheet": sec_statements.get("balance_sheet", {}),
        "cash_flow": sec_statements.get("cash_flow", {}),
    }

    for stmt_type, stmt_data in statements_map.items():
        for metric_id, metric_data in stmt_data.items():
            if metric_data is None:
                continue

            if isinstance(metric_data, dict):
                # Check if single fact (latest) or period-keyed (specified)
                if "period" in metric_data:
                    # Single fact
                    period = metric_data["period"]
                    if metric_id not in lookup:
                        lookup[metric_id] = {}
                    lookup[metric_id][period] = {
                        "value": metric_data.get("value"),
                        "period_type": _infer_period_type(metric_data),
                    }
                else:
                    # Period-keyed
                    for period_key, fact in metric_data.items():
                        if fact is not None and isinstance(fact, dict):
                            if metric_id not in lookup:
                                lookup[metric_id] = {}
                            lookup[metric_id][period_key] = {
                                "value": fact.get("value"),
                                "period_type": _infer_period_type(fact),
                            }

    return lookup


def _infer_period_type(fact: dict) -> str:
    """Infer whether a fact is annual or quarterly."""
    period = fact.get("period", "")
    if period.startswith("Q"):
        return "quarterly"
    if period.startswith("FY"):
        return "annual"
    # Check period_start/period_end
    start = fact.get("period_start", "")
    end = fact.get("period_end", "")
    if start and end:
        try:
            from datetime import datetime
            dt_start = datetime.strptime(start, "%Y-%m-%d")
            dt_end = datetime.strptime(end, "%Y-%m-%d")
            days = (dt_end - dt_start).days
            return "quarterly" if 80 <= days <= 100 else "annual"
        except (ValueError, TypeError):
            pass
    return "annual"
