"""Conflict resolution engine.

Compares financial values from multiple sources (SEC, FMP, BQ)
after normalization. Determines consensus status for each metric.

Statuses:
  EXACT_MATCH: Sources agree within 0.5%
  WITHIN_TOLERANCE: Sources agree within 5%
  MATERIAL_MISMATCH: Sources disagree beyond tolerance
  PERIOD_MISMATCH: Different fiscal periods being compared
  UNIT_MISMATCH: Different units or scales
  NOT_COMPARABLE: Insufficient data for comparison
"""

from __future__ import annotations

import math
from typing import Any, Optional


EXACT_MATCH = "EXACT_MATCH"
WITHIN_TOLERANCE = "WITHIN_TOLERANCE"
MATERIAL_MISMATCH = "MATERIAL_MISMATCH"
PERIOD_MISMATCH = "PERIOD_MISMATCH"
UNIT_MISMATCH = "UNIT_MISMATCH"
NOT_COMPARABLE = "NOT_COMPARABLE"

TOLERANCE_PCT = 5.0  # 5% for within_tolerance
EXACT_TOLERANCE_PCT = 0.5  # 0.5% for exact_match


def compare_values(
    primary_val: Optional[float],
    secondary_val: Optional[float],
    primary_source: str = "SEC",
    secondary_source: str = "FMP",
) -> dict:
    """Compare two numeric values from different sources.

    Returns a dict with status, difference info, and normalized comparison.
    """
    if primary_val is None or secondary_val is None:
        return {
            "status": NOT_COMPARABLE,
            "primary_source": primary_source,
            "secondary_source": secondary_source,
            "reason": "One or both values unavailable",
        }

    if primary_val == 0 and secondary_val == 0:
        return {
            "status": EXACT_MATCH,
            "primary_source": primary_source,
            "secondary_source": secondary_source,
            "difference_pct": 0.0,
        }

    if primary_val == 0 or secondary_val == 0:
        return {
            "status": MATERIAL_MISMATCH,
            "primary_source": primary_source,
            "secondary_source": secondary_source,
            "reason": "One value is zero while the other is non-zero",
            "difference_pct": 100.0,
        }

    # Calculate percentage difference using average as denominator
    avg = (abs(primary_val) + abs(secondary_val)) / 2.0
    if avg == 0:
        return {
            "status": EXACT_MATCH,
            "primary_source": primary_source,
            "secondary_source": secondary_source,
            "difference_pct": 0.0,
        }

    diff_pct = abs(primary_val - secondary_val) / avg * 100.0

    if diff_pct < EXACT_TOLERANCE_PCT:
        status = EXACT_MATCH
    elif diff_pct <= TOLERANCE_PCT:
        status = WITHIN_TOLERANCE
    else:
        status = MATERIAL_MISMATCH

    return {
        "status": status,
        "primary_source": primary_source,
        "secondary_source": secondary_source,
        "primary_value": primary_val,
        "secondary_value": secondary_val,
        "difference_pct": round(diff_pct, 2),
        "difference_abs": abs(primary_val - secondary_val),
    }


def resolve_metric(
    sec_val: Optional[float],
    fmp_val: Optional[float],
    bq_val: Optional[float] = None,
    metric_name: str = "",
) -> dict:
    """Resolve the canonical value for a metric from multiple sources.

    Follows the source hierarchy: SEC > FMP > BQ.
    Returns the resolved value, source, and cross-check information.
    """
    result = {
        "metric": metric_name,
        "resolved_value": None,
        "source": None,
        "classification": "reported",
        "cross_check": None,
    }

    # SEC wins if available
    if sec_val is not None:
        result["resolved_value"] = sec_val
        result["source"] = "SEC"
        result["classification"] = "reported"

        # Cross-check against FMP
        if fmp_val is not None:
            result["cross_check"] = compare_values(sec_val, fmp_val, "SEC", "FMP")
        elif bq_val is not None:
            result["cross_check"] = compare_values(sec_val, bq_val, "SEC", "BQ")

    # FMP enrichment if SEC unavailable
    elif fmp_val is not None:
        result["resolved_value"] = fmp_val
        result["source"] = "FMP"
        result["classification"] = "normalized_external"

        if bq_val is not None:
            result["cross_check"] = compare_values(fmp_val, bq_val, "FMP", "BQ")

    # BQ fallback
    elif bq_val is not None:
        result["resolved_value"] = bq_val
        result["source"] = "BQ"
        result["classification"] = "secondary_structured"

    return result


def build_cross_check_report(
    metrics: dict[str, dict],
) -> dict:
    """Build a summary report of all cross-checks.

    Parameters
    ----------
    metrics : dict
        Mapping of metric_name -> resolve_metric result.

    Returns
    -------
    dict with summary statistics.
    """
    total = len(metrics)
    exact = 0
    within_tolerance = 0
    mismatches = 0
    sec_only = 0
    details = []

    for name, result in metrics.items():
        cc = result.get("cross_check")
        source = result.get("source", "")

        if cc is None:
            sec_only += 1
            status = "no_cross_check"
        else:
            status = cc.get("status", NOT_COMPARABLE)
            if status == EXACT_MATCH:
                exact += 1
            elif status == WITHIN_TOLERANCE:
                within_tolerance += 1
            elif status == MATERIAL_MISMATCH:
                mismatches += 1

        details.append({
            "metric": name,
            "source": source,
            "cross_check_status": status,
            "difference_pct": cc.get("difference_pct") if cc else None,
        })

    return {
        "total_metrics": total,
        "sec_primary": total - sec_only,
        "sec_only": sec_only,
        "exact_matches": exact,
        "within_tolerance": within_tolerance,
        "material_mismatches": mismatches,
        "details": details,
    }
