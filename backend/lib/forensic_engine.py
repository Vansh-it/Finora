"""Forensic accounting engine.

Deterministic Python implementations of:
  - Piotroski F-Score (0–9)
  - Altman Z-Score (with applicability logic)
  - Beneish M-Score (8-component screening)

NO API calls. NO LLM calculations. All arithmetic is deterministic.
Every score includes full evidence with individual component results.
"""

from __future__ import annotations

import math
from typing import Any, Optional


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════

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
    result = a / b
    if math.isinf(result) or math.isnan(result):
        return None
    return result


# ══════════════════════════════════════════════════════════════════════════
# PIOTROSKI F-SCORE
# ══════════════════════════════════════════════════════════════════════════

def calculate_piotroski(stmts: dict, period: str) -> dict:
    """Calculate Piotroski F-Score (0–9) from SEC financial statements.

    Returns a dict with score, status, individual signals, and evidence.
    """
    prev = f"FY{int(period.replace('FY', '')) - 1}" if period.startswith("FY") else ""

    # Fetch facts
    ni = _val(_get_fact(stmts, "income_statement", "net_income", period))
    ocf = _val(_get_fact(stmts, "cash_flow", "operating_cash_flow", period))
    ta = _val(_get_fact(stmts, "balance_sheet", "total_assets", period))
    ta_prev = _val(_get_fact(stmts, "balance_sheet", "total_assets", prev)) if prev else None
    cl = _val(_get_fact(stmts, "balance_sheet", "current_liabilities", period))
    cl_prev = _val(_get_fact(stmts, "balance_sheet", "current_liabilities", prev)) if prev else None
    rev = _val(_get_fact(stmts, "income_statement", "revenue", period))
    rev_prev = _val(_get_fact(stmts, "income_statement", "revenue", prev)) if prev else None
    cogs = _val(_get_fact(stmts, "income_statement", "cost_of_revenue", period))
    cogs_prev = _val(_get_fact(stmts, "income_statement", "cost_of_revenue", prev)) if prev else None
    ar = _val(_get_fact(stmts, "balance_sheet", "accounts_receivable", period))
    ar_prev = _val(_get_fact(stmts, "balance_sheet", "accounts_receivable", prev)) if prev else None
    lt_debt = _val(_get_fact(stmts, "balance_sheet", "long_term_debt", period))
    lt_debt_prev = _val(_get_fact(stmts, "balance_sheet", "long_term_debt", prev)) if prev else None
    shares = _val(_get_fact(stmts, "additional", "diluted_shares", period))
    shares_prev = _val(_get_fact(stmts, "additional", "diluted_shares", prev)) if prev else None
    gm = _val(_get_fact(stmts, "income_statement", "gross_profit", period))
    gm_prev = _val(_get_fact(stmts, "income_statement", "gross_profit", prev)) if prev else None

    signals = []
    score = 0

    # 1. Positive ROA
    roa = _safe_div(ni, ta) if ni is not None and ta is not None else None
    s1 = 1 if roa is not None and roa > 0 else 0
    score += s1
    signals.append({
        "id": "positive_roa",
        "name": "Positive ROA",
        "result": s1,
        "value": round(roa * 100, 2) if roa is not None else None,
        "description": "Net Income / Total Assets > 0",
    })

    # 2. Positive Operating Cash Flow
    s2 = 1 if ocf is not None and ocf > 0 else 0
    score += s2
    signals.append({
        "id": "positive_ocf",
        "name": "Positive Operating Cash Flow",
        "result": s2,
        "value": ocf,
        "description": "Operating Cash Flow > 0",
    })

    # 3. ROA improved (current ROA > prior ROA)
    roa_prev = _safe_div(_val(_get_fact(stmts, "income_statement", "net_income", prev)) if prev else None, ta_prev) if prev and ta_prev else None
    s3 = 1 if roa is not None and roa_prev is not None and roa > roa_prev else 0
    score += s3
    signals.append({
        "id": "roa_improved",
        "name": "ROA Improved",
        "result": s3,
        "description": f"Current ROA ({roa*100:.1f}%)" + (f" > Prior ROA ({roa_prev*100:.1f}%)" if roa_prev else "") if roa else "ROA unavailable",
    })

    # 4. Accrual Quality (OCF > NI — cash earnings exceed accrual earnings)
    s4 = 1 if ocf is not None and ni is not None and ocf > ni else 0
    score += s4
    signals.append({
        "id": "accrual_quality",
        "name": "Accrual Quality",
        "result": s4,
        "description": "Operating Cash Flow > Net Income",
    })

    # 5. Leverage improved (long-term debt ratio decreased)
    ltd_ratio = _safe_div(lt_debt, ta) if lt_debt is not None and ta is not None else None
    ltd_ratio_prev = _safe_div(lt_debt_prev, ta_prev) if lt_debt_prev is not None and ta_prev is not None else None
    s5 = 1 if ltd_ratio is not None and ltd_ratio_prev is not None and ltd_ratio < ltd_ratio_prev else 0
    if ltd_ratio is None and ltd_ratio_prev is None:
        s5 = 1  # Both zero debt is favorable
    score += s5
    signals.append({
        "id": "leverage_improved",
        "name": "Leverage Improved",
        "result": s5,
        "description": f"LTD/TA ratio decreased" if s5 else "LTD/TA ratio not improved",
    })

    # 6. Liquidity improved (current ratio increased)
    cr = _safe_div(_val(_get_fact(stmts, "balance_sheet", "current_assets", period)), cl)
    cr_prev = _safe_div(_val(_get_fact(stmts, "balance_sheet", "current_assets", prev)), cl_prev) if prev and cl_prev else None
    s6 = 1 if cr is not None and cr_prev is not None and cr > cr_prev else 0
    score += s6
    signals.append({
        "id": "liquidity_improved",
        "name": "Liquidity Improved",
        "result": s6,
        "description": f"Current ratio increased" if s6 else "Current ratio not improved",
    })

    # 7. No dilution (shares did not increase)
    s7 = 1 if shares is not None and shares_prev is not None and shares <= shares_prev else 0
    if shares is None and shares_prev is None:
        s7 = 0
    score += s7
    signals.append({
        "id": "no_dilution",
        "name": "No Dilution",
        "result": s7,
        "description": f"Shares outstanding did not increase" if s7 else "Shares outstanding increased or unavailable",
    })

    # 8. Gross margin improved
    gm_val = _safe_div(gm, rev) if gm is not None and rev is not None else None
    gm_val_prev = _safe_div(gm_prev, rev_prev) if gm_prev is not None and rev_prev is not None else None
    s8 = 1 if gm_val is not None and gm_val_prev is not None and gm_val > gm_val_prev else 0
    score += s8
    signals.append({
        "id": "gross_margin_improved",
        "name": "Gross Margin Improved",
        "result": s8,
        "description": f"Gross margin improved" if s8 else "Gross margin not improved or unavailable",
    })

    # 9. Asset turnover improved
    at = _safe_div(rev, ta) if rev is not None and ta is not None else None
    at_prev = _safe_div(rev_prev, ta_prev) if rev_prev is not None and ta_prev is not None else None
    s9 = 1 if at is not None and at_prev is not None and at > at_prev else 0
    score += s9
    signals.append({
        "id": "asset_turnover_improved",
        "name": "Asset Turnover Improved",
        "result": s9,
        "description": f"Asset turnover improved" if s9 else "Asset turnover not improved or unavailable",
    })

    # Status interpretation
    if score >= 7:
        status = "STRONG"
    elif score >= 4:
        status = "MIXED"
    else:
        status = "WEAK"

    return {
        "metric_id": "piotroski_f_score",
        "name": "Piotroski F-Score",
        "score": score,
        "max_score": 9,
        "status": status,
        "signals": signals,
        "formula": "9 binary signals: profitability (3) + leverage/liquidity (3) + operating efficiency (3)",
        "methodology": "Piotroski (2000) — Financial Statement Analysis",
        "classification": "Financial Health Signal",
        "period": period,
        "note": "This is a financial health signal, not a buy/sell recommendation.",
    }


# ══════════════════════════════════════════════════════════════════════════
# ALTMAN Z-SCORE
# ══════════════════════════════════════════════════════════════════════════

# Financial institution tickers where Altman Z is not applicable
_FINANCIAL_TICKERS = {
    "JPM", "GS", "MS", "BAC", "C", "WFC", "USB", "PNC", "TFC", "COF",
    "AXP", "DFS", "SYF", "BRK-A", "BRK-B", "AIG", "MET", "PRU", "TRV",
    "ALL", "CB", "MMC", "AON", "ICE", "CME", "SPGI", "MCO", "MSCI",
    "CBOE", "NDAQ", "V", "MA", "FIS", "FISV", "ADP", "PAYX",
}

# GICS financial sector codes
_FINANCIAL_SECTORS = {
    "Financial Services", "Banking", "Insurance", "Capital Markets",
    "Diversified Financial Services", "Thrifts & Mortgage Finance",
}


def calculate_altman_z(
    stmts: dict,
    period: str,
    ticker: str = "",
    sector: str = "",
) -> dict:
    """Calculate Altman Z-Score with applicability logic.

    Parameters
    ----------
    stmts : dict
        SEC-extracted financial statements.
    period : str
        Fiscal period label (e.g. "FY2023").
    ticker : str
        Stock ticker for financial institution check.
    sector : str
        Company sector for applicability.

    Returns
    -------
    dict with score, status, applicability, components, and evidence.
    """
    # Applicability check
    ticker_clean = ticker.replace(".", "").replace("-", "").upper()
    if ticker_clean in _FINANCIAL_TICKERS or sector in _FINANCIAL_SECTORS:
        return {
            "metric_id": "altman_z_score",
            "name": "Altman Z-Score",
            "score": None,
            "status": "NOT APPLICABLE",
            "applicability": "not_applicable",
            "reason": f"Altman Z-Score is designed for industrial/manufacturing companies. {ticker or 'This company'} operates in the financial services sector where this model is not meaningful.",
            "components": [],
            "formula": "Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5",
            "methodology": "Altman (1968) — Industrial distress prediction model",
            "period": period,
            "note": "The original Altman Z-Score was developed for manufacturing companies and may produce misleading results for financial institutions.",
        }

    # Fetch facts
    ta = _val(_get_fact(stmts, "balance_sheet", "total_assets", period))
    cl = _val(_get_fact(stmts, "balance_sheet", "current_liabilities", period))
    ca = _val(_get_fact(stmts, "balance_sheet", "current_assets", period))
    tl = _val(_get_fact(stmts, "balance_sheet", "total_liabilities", period))
    equity = _val(_get_fact(stmts, "balance_sheet", "shareholders_equity", period))
    rev = _val(_get_fact(stmts, "income_statement", "revenue", period))
    ebit = _val(_get_fact(stmts, "income_statement", "operating_income", period))
    ni = _val(_get_fact(stmts, "income_statement", "net_income", period))

    # Check required inputs
    required = {"Total Assets": ta, "Current Liabilities": cl, "Retained Earnings (approx via Equity)": equity, "Revenue": rev, "EBIT": ebit}
    missing = [k for k, v in required.items() if v is None]

    if missing:
        return {
            "metric_id": "altman_z_score",
            "name": "Altman Z-Score",
            "score": None,
            "status": "UNAVAILABLE",
            "applicability": "unavailable",
            "reason": f"Missing required inputs: {', '.join(missing)}",
            "components": [],
            "formula": "Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5",
            "methodology": "Altman (1968) — Industrial distress prediction model",
            "period": period,
        }

    # Compute components (using equity as proxy for retained earnings)
    # X1 = Working Capital / Total Assets
    wc = (ca or 0) - (cl or 0)
    x1 = _safe_div(wc, ta)

    # X2 = Retained Earnings / Total Assets (use equity as proxy)
    x2 = _safe_div(equity, ta)

    # X3 = EBIT / Total Assets
    x3 = _safe_div(ebit, ta)

    # X4 = Market Cap / Total Liabilities
    # Market cap not available in pure SEC data — use book value of equity
    x4 = _safe_div(equity, tl) if tl and tl > 0 else None

    # X5 = Revenue / Total Assets
    x5 = _safe_div(rev, ta)

    # Compute Z-Score
    z_score = None
    if all(v is not None for v in [x1, x2, x3, x4, x5]):
        z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

    # Interpretation
    if z_score is not None:
        if z_score > 2.99:
            status = "SAFE ZONE"
            interpretation = "Low probability of financial distress"
        elif z_score > 1.81:
            status = "GREY ZONE"
            interpretation = "Moderate risk — requires monitoring"
        else:
            status = "DISTRESS ZONE"
            interpretation = "High probability of financial distress"
    else:
        status = "UNAVAILABLE"
        interpretation = "Could not compute Z-Score"

    components = [
        {"id": "x1", "name": "Working Capital / Total Assets", "value": round(x1, 4) if x1 is not None else None, "coefficient": 1.2, "contribution": round(1.2 * x1, 4) if x1 is not None else None},
        {"id": "x2", "name": "Retained Earnings (Equity) / Total Assets", "value": round(x2, 4) if x2 is not None else None, "coefficient": 1.4, "contribution": round(1.4 * x2, 4) if x2 is not None else None},
        {"id": "x3", "name": "EBIT / Total Assets", "value": round(x3, 4) if x3 is not None else None, "coefficient": 3.3, "contribution": round(3.3 * x3, 4) if x3 is not None else None},
        {"id": "x4", "name": "Equity / Total Liabilities", "value": round(x4, 4) if x4 is not None else None, "coefficient": 0.6, "contribution": round(0.6 * x4, 4) if x4 is not None else None},
        {"id": "x5", "name": "Revenue / Total Assets", "value": round(x5, 4) if x5 is not None else None, "coefficient": 1.0, "contribution": round(1.0 * x5, 4) if x5 is not None else None},
    ]

    return {
        "metric_id": "altman_z_score",
        "name": "Altman Z-Score",
        "score": round(z_score, 4) if z_score is not None else None,
        "display_value": f"{z_score:.2f}" if z_score is not None else "N/A",
        "status": status,
        "interpretation": interpretation,
        "applicability": "applicable",
        "components": components,
        "formula": "Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5",
        "methodology": "Altman (1968) — Industrial distress prediction model",
        "period": period,
        "note": "Z > 2.99 = Safe Zone; 1.81 < Z < 2.99 = Grey Zone; Z < 1.81 = Distress Zone. Equity used as proxy for retained earnings. Market cap not used (SEC-only data).",
    }


# ══════════════════════════════════════════════════════════════════════════
# BENEISH M-SCORE
# ══════════════════════════════════════════════════════════════════════════

def calculate_beneish(stmts: dict, period: str) -> dict:
    """Calculate Beneish M-Score for earnings manipulation screening.

    Requires two comparable periods of data.
    Returns components, classification, and disclaimer.

    M-Score > -1.78 indicates potential earnings manipulation risk.
    """
    prev = f"FY{int(period.replace('FY', '')) - 1}" if period.startswith("FY") else ""

    if not prev:
        return {
            "metric_id": "beneish_m_score",
            "name": "Beneish M-Score",
            "score": None,
            "status": "UNAVAILABLE",
            "reason": f"Requires two comparable periods. Current period: {period}. Prior period data not available.",
            "components": [],
            "formula": "M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI",
            "methodology": "Beneish (1999) — Earnings manipulation screening",
            "period": period,
            "note": "Statistical screening indicator. Elevated scores suggest higher probability of earnings manipulation but do not constitute proof of accounting misconduct.",
        }

    # Fetch all required values for both periods
    def _get(stmt_type, metric, p):
        return _val(_get_fact(stmts, stmt_type, metric, p))

    # Current period
    rev = _get("income_statement", "revenue", period)
    cogs = _get("income_statement", "cost_of_revenue", period)
    ni = _get("income_statement", "net_income", period)
    oi = _get("income_statement", "operating_income", period)
    da = _get("cash_flow", "depreciation_amortization", period)
    if da is None:
        da = _get("additional", "depreciation_amortization", period)
    sga = _get("income_statement", "selling_general_admin", period)
    cfo = _get("cash_flow", "operating_cash_flow", period)
    ppe_net = _get("balance_sheet", "property_plant_equipment", period)
    if ppe_net is None:
        ppe_net = _get("balance_sheet", "net_ppe", period)
    current_assets = _get("balance_sheet", "current_assets", period)
    current_liabilities = _get("balance_sheet", "current_liabilities", period)
    lt_debt = _get("balance_sheet", "long_term_debt", period)
    total_assets = _get("balance_sheet", "total_assets", period)
    receivables = _get("balance_sheet", "accounts_receivable", period)

    # Prior period
    rev_p = _get("income_statement", "revenue", prev)
    cogs_p = _get("income_statement", "cost_of_revenue", prev)
    ni_p = _get("income_statement", "net_income", prev)
    da_p = _get("cash_flow", "depreciation_amortization", prev)
    if da_p is None:
        da_p = _get("additional", "depreciation_amortization", prev)
    sga_p = _get("income_statement", "selling_general_admin", prev)
    ppe_net_p = _get("balance_sheet", "property_plant_equipment", prev)
    if ppe_net_p is None:
        ppe_net_p = _get("balance_sheet", "net_ppe", prev)
    current_assets_p = _get("balance_sheet", "current_assets", prev)
    current_liabilities_p = _get("balance_sheet", "current_liabilities", prev)
    lt_debt_p = _get("balance_sheet", "long_term_debt", prev)
    total_assets_p = _get("balance_sheet", "total_assets", prev)
    receivables_p = _get("balance_sheet", "accounts_receivable", prev)

    # Check required values
    required_current = {"Revenue": rev, "COGS": cogs, "Total Assets": total_assets, "Receivables": receivables}
    required_prior = {"Revenue (prior)": rev_p, "COGS (prior)": cogs_p, "Total Assets (prior)": total_assets_p, "Receivables (prior)": receivables_p}
    missing = [k for k, v in {**required_current, **required_prior}.items() if v is None]

    if missing:
        return {
            "metric_id": "beneish_m_score",
            "name": "Beneish M-Score",
            "score": None,
            "status": "UNAVAILABLE",
            "reason": f"Missing required inputs for two-period comparison: {', '.join(missing)}",
            "components": [],
            "formula": "M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI",
            "methodology": "Beneish (1999) — Earnings manipulation screening",
            "period": period,
            "note": "Statistical screening indicator. Elevated scores suggest higher probability of earnings manipulation but do not constitute proof of accounting misconduct.",
        }

    eps = 1e-9  # tiny epsilon to avoid division by zero

    # DSRI: Days Sales in Receivables Index
    dsri_num = (receivables / max(rev, eps)) if rev else None
    dsri_den = (receivables_p / max(rev_p, eps)) if rev_p else None
    dsri = _safe_div(dsri_num, dsri_den)

    # GMI: Gross Margin Index
    gm = ((rev - cogs) / max(rev, eps)) if rev and cogs is not None else None
    gm_p = ((rev_p - cogs_p) / max(rev_p, eps)) if rev_p and cogs_p is not None else None
    gmi = _safe_div(gm_p, gm) if gm is not None and gm_p is not None else None

    # AQI: Asset Quality Index
    def _non_ppe_assets(ta, ppe):
        if ta is None or ppe is None:
            return None
        return ta - ppe

    npe = _non_ppe_assets(total_assets, ppe_net)
    npe_p = _non_ppe_assets(total_assets_p, ppe_net_p)
    aqi_num = _safe_div(npe, total_assets)
    aqi_den = _safe_div(npe_p, total_assets_p)
    aqi = _safe_div(aqi_num, aqi_den)

    # SGI: Sales Growth Index
    sgi = _safe_div(rev, rev_p) if rev_p else None

    # DEPI: Depreciation Index
    dep_rate = _safe_div(da, max((da or 0) + (ppe_net or 0), eps)) if da is not None and ppe_net is not None else None
    dep_rate_p = _safe_div(da_p, max((da_p or 0) + (ppe_net_p or 0), eps)) if da_p is not None and ppe_net_p is not None else None
    depi = _safe_div(dep_rate_p, dep_rate) if dep_rate is not None and dep_rate_p is not None else None

    # SGAI: SGA Expense Index
    sga_ratio = _safe_div(sga, rev) if sga is not None and rev else None
    sga_ratio_p = _safe_div(sga_p, rev_p) if sga_p is not None and rev_p else None
    sgai = _safe_div(sga_ratio, sga_ratio_p) if sga_ratio is not None and sga_ratio_p is not None else None

    # LVGI: Leverage Index
    lev = _safe_div(lt_debt, current_assets) if lt_debt is not None and current_assets else None
    lev_p = _safe_div(lt_debt_p, current_assets_p) if lt_debt_p is not None and current_assets_p else None
    lvgi = _safe_div(lev, lev_p) if lev is not None and lev_p is not None else None

    # TATA: Total Accruals to Total Assets
    if cfo is not None and ni is not None and total_assets:
        tata = (cfo - ni) / total_assets
    else:
        tata = None

    # Compute M-Score
    components = []
    vals = [dsri, gmi, aqi, sgi, depi, sgai, tata, lvgi]
    coeffs = [0.92, 0.528, 0.404, 0.892, 0.115, -0.172, 4.679, -0.327]
    names = ["DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "TATA", "LVGI"]
    full_names = [
        "Days Sales in Receivables Index",
        "Gross Margin Index",
        "Asset Quality Index",
        "Sales Growth Index",
        "Depreciation Index",
        "SGA Expense Index",
        "Total Accruals to Total Assets",
        "Leverage Index",
    ]

    m_score = -4.84
    all_available = True
    for val, coeff, name, full_name in zip(vals, coeffs, names, full_names):
        if val is not None:
            contribution = coeff * val
            m_score += contribution
            components.append({
                "id": name,
                "name": full_name,
                "value": round(val, 4),
                "coefficient": coeff,
                "contribution": round(contribution, 4),
            })
        else:
            all_available = False
            components.append({
                "id": name,
                "name": full_name,
                "value": None,
                "coefficient": coeff,
                "contribution": None,
            })

    if not all_available:
        return {
            "metric_id": "beneish_m_score",
            "name": "Beneish M-Score",
            "score": None,
            "status": "UNAVAILABLE",
            "reason": "One or more components could not be computed due to missing data",
            "components": components,
            "formula": "M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI",
            "methodology": "Beneish (1999) — Earnings manipulation screening",
            "period": f"{prev} to {period}",
            "note": "Statistical screening indicator. Elevated scores suggest higher probability of earnings manipulation but do not constitute proof of accounting misconduct.",
        }

    # Classification
    if m_score > -1.78:
        status = "ELEVATED"
        interpretation = "M-Score > -1.78 suggests elevated manipulation-risk screening signal"
    else:
        status = "LOW RISK"
        interpretation = "M-Score ≤ -1.78 suggests lower manipulation-risk screening signal"

    return {
        "metric_id": "beneish_m_score",
        "name": "Beneish M-Score",
        "score": round(m_score, 4),
        "display_value": f"{m_score:.2f}",
        "status": status,
        "interpretation": interpretation,
        "components": components,
        "formula": "M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI",
        "methodology": "Beneish (1999) — Earnings manipulation screening",
        "period": f"{prev} to {period}",
        "note": "This is a statistical screening indicator, not proof of accounting misconduct. M-Score > -1.78 indicates elevated risk.",
    }
