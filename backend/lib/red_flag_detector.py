"""Deterministic red flag detection engine.

Scans SEC financial statements for quantitative warning signals.
NO LLM detection. All flags are grounded in actual metric comparisons.

Every flag includes: id, category, severity, headline, description,
metric evidence, period, and source.
"""

from __future__ import annotations

import math
from typing import Any, Optional


def _val(fact: Any) -> Optional[float]:
    if fact is None:
        return None
    if isinstance(fact, dict):
        v = fact.get("value")
    else:
        v = fact
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _get_fact(stmts: dict, stmt_type: str, metric: str, period: str) -> Optional[dict]:
    stmt = stmts.get(stmt_type, {})
    md = stmt.get(metric)
    if md is None:
        return None
    if isinstance(md, dict):
        if "value" in md and md.get("period") == period:
            return md
        inner = md.get(period)
        if isinstance(inner, dict):
            return inner
    return None


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    r = a / b
    if math.isinf(r) or math.isnan(r):
        return None
    return r


def _growth_rate(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / abs(previous)


def detect_red_flags(stmts: dict, period: str, forensic_scores: Optional[dict] = None) -> list[dict]:
    """Scan for red flags in financial statements.

    Returns a list of flag dicts, each with:
        id, category, severity, headline, description, evidence, period
    """
    prev = f"FY{int(period.replace('FY', '')) - 1}" if period.startswith("FY") else ""
    flags = []

    def _get(stmt_type, metric, p):
        return _val(_get_fact(stmts, stmt_type, metric, p))

    # Current period values
    rev = _get("income_statement", "revenue", period)
    rev_p = _get("income_statement", "revenue", prev) if prev else None
    gp = _get("income_statement", "gross_profit", period)
    gp_p = _get("income_statement", "gross_profit", prev) if prev else None
    oi = _get("income_statement", "operating_income", period)
    oi_p = _get("income_statement", "operating_income", prev) if prev else None
    ni = _get("income_statement", "net_income", period)
    ni_p = _get("income_statement", "net_income", prev) if prev else None
    ar = _get("balance_sheet", "accounts_receivable", period)
    ar_p = _get("balance_sheet", "accounts_receivable", prev) if prev else None
    inv = _get("balance_sheet", "inventory", period)
    inv_p = _get("balance_sheet", "inventory", prev) if prev else None
    ocf = _get("cash_flow", "operating_cash_flow", period)
    ocf_p = _get("cash_flow", "operating_cash_flow", prev) if prev else None
    cfo = ocf  # alias
    lt_debt = _get("balance_sheet", "long_term_debt", period)
    lt_debt_p = _get("balance_sheet", "long_term_debt", prev) if prev else None
    st_debt = _get("balance_sheet", "short_term_debt", period)
    st_debt_p = _get("balance_sheet", "short_term_debt", prev) if prev else None
    shares = _get("additional", "diluted_shares", period)
    shares_p = _get("additional", "diluted_shares", prev) if prev else None
    ca = _get("balance_sheet", "current_assets", period)
    cl = _get("balance_sheet", "current_liabilities", period)
    ta = _get("balance_sheet", "total_assets", period)
    capex = _get("cash_flow", "capital_expenditures", period)

    # 1. Receivables growing faster than revenue
    if rev is not None and ar is not None and rev_p is not None and ar_p is not None:
        rev_g = _growth_rate(rev, rev_p)
        ar_g = _growth_rate(ar, ar_p)
        if rev_g is not None and ar_g is not None and ar_g > rev_g + 0.10:
            flags.append({
                "id": "receivables_growth_exceeds_revenue",
                "category": "RECEIVABLES",
                "severity": "high" if ar_g > rev_g + 0.25 else "medium",
                "headline": "Receivables grew materially faster than revenue",
                "description": f"Accounts receivable grew {ar_g*100:.1f}% while revenue grew {rev_g*100:.1f}%.",
                "evidence": {
                    "receivables_growth": round(ar_g * 100, 1),
                    "revenue_growth": round(rev_g * 100, 1),
                },
                "period": period,
            })

    # 2. Inventory growing faster than revenue
    if rev is not None and inv is not None and rev_p is not None and inv_p is not None:
        rev_g = _growth_rate(rev, rev_p)
        inv_g = _growth_rate(inv, inv_p)
        if rev_g is not None and inv_g is not None and inv_g > rev_g + 0.10:
            flags.append({
                "id": "inventory_growth_exceeds_revenue",
                "category": "INVENTORY",
                "severity": "high" if inv_g > rev_g + 0.25 else "medium",
                "headline": "Inventory grew materially faster than revenue",
                "description": f"Inventory grew {inv_g*100:.1f}% while revenue grew {rev_g*100:.1f}%.",
                "evidence": {
                    "inventory_growth": round(inv_g * 100, 1),
                    "revenue_growth": round(rev_g * 100, 1),
                },
                "period": period,
            })

    # 3. Gross margin deterioration
    if gp is not None and rev is not None and gp_p is not None and rev_p is not None:
        gm = _safe_div(gp, rev)
        gm_p = _safe_div(gp_p, rev_p)
        if gm is not None and gm_p is not None:
            gm_change = gm - gm_p
            if gm_change < -0.03:  # >3pp decline
                flags.append({
                    "id": "gross_margin_deterioration",
                    "category": "MARGINS",
                    "severity": "high" if gm_change < -0.05 else "medium",
                    "headline": "Gross margin deteriorated materially",
                    "description": f"Gross margin declined from {gm_p*100:.1f}% to {gm*100:.1f}% ({gm_change*100:.1f}pp).",
                    "evidence": {
                        "current_margin": round(gm * 100, 1),
                        "prior_margin": round(gm_p * 100, 1),
                        "change_pp": round(gm_change * 100, 1),
                    },
                    "period": period,
                })

    # 4. Operating margin deterioration
    if oi is not None and rev is not None and oi_p is not None and rev_p is not None:
        om = _safe_div(oi, rev)
        om_p = _safe_div(oi_p, rev_p)
        if om is not None and om_p is not None:
            om_change = om - om_p
            if om_change < -0.03:
                flags.append({
                    "id": "operating_margin_deterioration",
                    "category": "MARGINS",
                    "severity": "high" if om_change < -0.05 else "medium",
                    "headline": "Operating margin deteriorated materially",
                    "description": f"Operating margin declined from {om_p*100:.1f}% to {om*100:.1f}% ({om_change*100:.1f}pp).",
                    "evidence": {
                        "current_margin": round(om * 100, 1),
                        "prior_margin": round(om_p * 100, 1),
                        "change_pp": round(om_change * 100, 1),
                    },
                    "period": period,
                })

    # 5. Negative FCF trend (FCF declining for 2 consecutive periods)
    fcf = None
    if ocf is not None and capex is not None:
        fcf = ocf - abs(capex)
    fcf_p = None
    if ocf_p is not None:
        capex_p = _get("cash_flow", "capital_expenditures", prev) if prev else None
        if capex_p is not None:
            fcf_p = ocf_p - abs(capex_p)
    if fcf is not None and fcf_p is not None and fcf < fcf_p and fcf < 0:
        flags.append({
            "id": "negative_fcf_trend",
            "category": "CASH FLOW",
            "severity": "high",
            "headline": "Free cash flow is negative and declining",
            "description": f"FCF declined from ${fcf_p/1e9:.1f}B to ${fcf/1e9:.1f}B.",
            "evidence": {"current_fcf": fcf, "prior_fcf": fcf_p},
            "period": period,
        })

    # 6. Net income rising while OCF falls
    if ni is not None and ni_p is not None and ocf is not None and ocf_p is not None:
        ni_up = ni > ni_p
        ocf_down = ocf < ocf_p
        if ni_up and ocf_down and ni > 0:
            flags.append({
                "id": "earnings_cashflow_divergence",
                "category": "CASH FLOW",
                "severity": "high",
                "headline": "Net income rising while operating cash flow falls",
                "description": f"Net income increased from ${ni_p/1e9:.1f}B to ${ni/1e9:.1f}B while OCF fell from ${ocf_p/1e9:.1f}B to ${ocf/1e9:.1f}B.",
                "evidence": {
                    "net_income": ni, "prior_net_income": ni_p,
                    "ocf": ocf, "prior_ocf": ocf_p,
                },
                "period": period,
            })

    # 7. Material leverage increase
    if lt_debt is not None and lt_debt_p is not None and ta is not None and ta > 0:
        debt_ratio = lt_debt / ta
        if ta and ta > 0:
            debt_ratio_p = lt_debt_p / ta if lt_debt_p is not None else 0
        else:
            debt_ratio_p = None
        if debt_ratio_p is not None and debt_ratio > debt_ratio_p + 0.05:
            flags.append({
                "id": "leverage_increase",
                "category": "LEVERAGE",
                "severity": "high" if debt_ratio > debt_ratio_p + 0.10 else "medium",
                "headline": "Long-term debt increased materially relative to assets",
                "description": f"LTD/Total Assets increased from {debt_ratio_p*100:.1f}% to {debt_ratio*100:.1f}%.",
                "evidence": {
                    "current_ratio": round(debt_ratio * 100, 1),
                    "prior_ratio": round(debt_ratio_p * 100, 1),
                },
                "period": period,
            })

    # 8. Share dilution
    if shares is not None and shares_p is not None:
        dilution = _growth_rate(shares, shares_p)
        if dilution is not None and dilution > 0.03:
            flags.append({
                "id": "share_dilution",
                "category": "DILUTION",
                "severity": "high" if dilution > 0.10 else "medium",
                "headline": "Shares outstanding increased materially",
                "description": f"Shares outstanding grew {dilution*100:.1f}%, indicating potential dilution.",
                "evidence": {
                    "current_shares": shares,
                    "prior_shares": shares_p,
                    "dilution_pct": round(dilution * 100, 1),
                },
                "period": period,
            })

    # 9. Liquidity deterioration
    if ca is not None and cl is not None and cl > 0:
        cr = ca / cl
        if prev:
            ca_p = _get("balance_sheet", "current_assets", prev)
            cl_p = _get("balance_sheet", "current_liabilities", prev)
            if ca_p is not None and cl_p is not None and cl_p > 0:
                cr_p = ca_p / cl_p
                if cr < cr_p - 0.3:
                    flags.append({
                        "id": "liquidity_deterioration",
                        "category": "LIQUIDITY",
                        "severity": "high" if cr < 1.0 else "medium",
                        "headline": "Current ratio declined materially",
                        "description": f"Current ratio fell from {cr_p:.2f}x to {cr:.2f}x.",
                        "evidence": {"current": round(cr, 2), "prior": round(cr_p, 2)},
                        "period": period,
                    })

    # 10. Unusual CapEx movement
    if capex is not None:
        capex_p = _get("cash_flow", "capital_expenditures", prev) if prev else None
        if capex_p is not None and capex_p != 0:
            capex_change = _growth_rate(abs(capex), abs(capex_p))
            if capex_change is not None and abs(capex_change) > 0.5:
                flags.append({
                    "id": "unusual_capex_movement",
                    "category": "CAPEX",
                    "severity": "medium",
                    "headline": "Capital expenditures changed significantly",
                    "description": f"CapEx changed {capex_change*100:.1f}% from prior period.",
                    "evidence": {
                        "current": capex,
                        "prior": capex_p,
                        "change_pct": round(capex_change * 100, 1),
                    },
                    "period": period,
                })

    # 11. Weak Piotroski score (if available)
    if forensic_scores:
        piotroski = forensic_scores.get("piotroski")
        if piotroski and isinstance(piotroski, dict):
            score = piotroski.get("score")
            if score is not None and score <= 3:
                flags.append({
                    "id": "weak_piotroski",
                    "category": "FORENSIC",
                    "severity": "high",
                    "headline": f"Weak Piotroski F-Score ({score}/9)",
                    "description": "Multiple financial health signals indicate weakness.",
                    "evidence": {"piotroski_score": score},
                    "period": period,
                })

    # 12. Altman distress signal
    if forensic_scores:
        altman = forensic_scores.get("altman")
        if altman and isinstance(altman, dict):
            score = altman.get("score")
            if score is not None and score < 1.81:
                flags.append({
                    "id": "altman_distress_signal",
                    "category": "FORENSIC",
                    "severity": "high",
                    "headline": f"Altman Z-Score in distress zone ({score:.2f})",
                    "description": "Altman Z-Score below 1.81 indicates elevated financial distress probability.",
                    "evidence": {"altman_z_score": round(score, 2)},
                    "period": period,
                })

    # 13. Elevated Beneish M-Score
    if forensic_scores:
        beneish = forensic_scores.get("beneish")
        if beneish and isinstance(beneish, dict):
            score = beneish.get("score")
            if score is not None and score > -1.78:
                flags.append({
                    "id": "elevated_beneish",
                    "category": "FORENSIC",
                    "severity": "medium",
                    "headline": f"Elevated Beneish M-Score ({score:.2f})",
                    "description": "Beneish M-Score above -1.78 suggests elevated manipulation-risk screening signal.",
                    "evidence": {"beneish_m_score": round(score, 2)},
                    "period": period,
                    "note": "Statistical screening indicator, not proof of accounting misconduct.",
                })

    return flags
