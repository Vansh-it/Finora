"""Financial calculation engine.

Takes normalized SEC/XBRL financial statement data and computes
analyst-grade metrics.  All arithmetic is deterministic Python —
LLMs are never used for calculations.

Every calculated metric includes full traceability:
  - metric ID, professional name, classification
  - raw value, display value, unit, period, period_type
  - formula, calculation string, raw inputs, source evidence
  - methodology reference
  - previous-period value and trend (where available)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

from lib.metric_methodology import METODOLOGY, get_beginner_explanation
from lib.xbrl_mapper import INCOME_STATEMENT_CONCEPTS, BALANCE_SHEET_CONCEPTS, CASH_FLOW_CONCEPTS, ADDITIONAL_CONCEPTS


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _val(fact: Optional[dict]) -> Optional[float]:
    """Extract the numeric value from a financial fact dict."""
    if fact is None:
        return None
    v = fact.get("value")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _get_fact(stmts: dict, statement_type: str, metric: str, period: str) -> Optional[dict]:
    """Get a fact dict from the extracted statements."""
    statement = stmts.get(statement_type, {})
    metric_data = statement.get(metric)
    if metric_data is None:
        return None
    if "period" in metric_data:
        return metric_data if metric_data.get("period") == period else None
    return metric_data.get(period)


def _available(*vals: Any) -> bool:
    """Check that none of the values are None."""
    return all(v is not None for v in vals)


def _safe_divide(numerator: float, denominator: float) -> Optional[float]:
    """Safe division that returns None for divide-by-zero."""
    if denominator == 0 or math.isinf(denominator) or math.isnan(denominator):
        return None
    result = numerator / denominator
    if math.isinf(result) or math.isnan(result):
        return None
    return result


def _safe_cagr(start_val: float, end_val: float, n_years: int) -> Optional[float]:
    """Safe CAGR calculation."""
    if n_years <= 0:
        return None
    if start_val <= 0 or end_val <= 0:
        return None
    return ((end_val / start_val) ** (1.0 / n_years) - 1.0) * 100.0


def _previous_period(period: str) -> Optional[str]:
    """Get the previous fiscal year label."""
    try:
        year = int(period.replace("FY", ""))
        return f"FY{year - 1}"
    except (ValueError, TypeError):
        return None


# ══════════════════════════════════════════════════════════════════════════
# METRIC RESULT
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class CalculatedMetric:
    """A single calculated metric with full traceability."""
    metric_id: str = ""
    name: str = ""
    value: Optional[float] = None
    display_value: str = "N/A"
    unit: str = ""
    period: str = ""
    period_type: str = "annual"  # annual | quarterly
    status: str = "calculated"  # calculated | unavailable
    classification: str = "calculated"  # reported | calculated | derived
    formula: str = ""
    inputs: list = field(default_factory=list)
    calculation: str = ""
    methodology: str = ""
    reason: str = ""
    # Trend metadata
    previous_value: Optional[float] = None
    change_pp: Optional[float] = None
    direction: str = "flat"  # up | down | flat

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "metric_id": self.metric_id,
            "name": self.name,
            "unit": self.unit,
            "period": self.period,
            "period_type": self.period_type,
            "status": self.status,
            "classification": self.classification,
            "formula": self.formula,
            "methodology": self.methodology,
        }
        if self.status == "calculated":
            result["value"] = self.value
            result["display_value"] = self.display_value
            result["inputs"] = self.inputs
            result["calculation"] = self.calculation
            if self.previous_value is not None:
                result["previous_value"] = self.previous_value
                result["change_pp"] = self.change_pp
                result["direction"] = self.direction
        else:
            if self.value is not None:
                result["value"] = self.value
            result["reason"] = self.reason
        return result


def _unavailable(metric_id: str, period: str, reason: str) -> dict:
    """Create an unavailable metric result."""
    meta = METODOLOGY.get(metric_id, {})
    return CalculatedMetric(
        metric_id=metric_id,
        name=meta.get("name", metric_id),
        unit=meta.get("unit", ""),
        period=period,
        status="unavailable",
        classification=meta.get("classification", "calculated"),
        formula=meta.get("formula", ""),
        methodology=meta.get("notes", ""),
        reason=reason,
    ).to_dict()


def _make_inputs(*pairs: tuple[str, Optional[dict]]) -> list[dict]:
    """Build the inputs list from (label, fact_dict) pairs."""
    result = []
    for label, fact in pairs:
        entry: dict[str, Any] = {"name": label}
        if fact and "value" in fact:
            entry["value"] = fact["value"]
            entry["source_evidence"] = {
                "xbrl_concept": fact.get("xbrl_concept", ""),
                "form": fact.get("form", ""),
                "filing_date": fact.get("filing_date", ""),
                "accession_number": fact.get("accession_number", ""),
                "period": fact.get("period", ""),
                "source": fact.get("source", ""),
                "source_url": fact.get("source_url", ""),
            }
        else:
            entry["value"] = None
        result.append(entry)
    return result


def _trend_info(stmts: dict, statement_type: str, metric: str,
                current_period: str, current_val: float) -> dict:
    """Get previous value and trend for a metric."""
    prev = _previous_period(current_period)
    if prev is None:
        return {}
    prev_fact = _get_fact(stmts, statement_type, metric, prev)
    prev_val = _val(prev_fact)
    if prev_val is None or prev_val == 0:
        return {}
    change = current_val - prev_val
    # For percentages, change is in percentage points
    if current_val < 100 and prev_val < 100:
        change_pp = round(change, 2)
    else:
        change_pp = round(change, 2)
    direction = "up" if change > 0 else ("down" if change < 0 else "flat")
    return {"previous_value": prev_val, "change_pp": change_pp, "direction": direction}


# ══════════════════════════════════════════════════════════════════════════
# BUILD A METRIC DICT QUICKLY
# ══════════════════════════════════════════════════════════════════════════

def _build_metric(
    metric_id: str,
    value: float,
    display: str,
    period: str,
    classification: str,
    formula: str,
    inputs: list,
    calculation: str,
    trend: Optional[dict] = None,
) -> dict:
    """Build a calculated metric dict."""
    meta = METODOLOGY.get(metric_id, {})
    m = CalculatedMetric(
        metric_id=metric_id,
        name=meta.get("name", metric_id),
        value=value,
        display_value=display,
        unit=meta.get("unit", ""),
        period=period,
        period_type="annual",
        status="calculated",
        classification=classification,
        formula=formula,
        inputs=inputs,
        calculation=calculation,
        methodology=meta.get("notes", ""),
    )
    if trend:
        m.previous_value = trend.get("previous_value")
        m.change_pp = trend.get("change_pp")
        m.direction = trend.get("direction", "flat")
    return m.to_dict()


# ══════════════════════════════════════════════════════════════════════════
# GROWTH CALCULATIONS
# ══════════════════════════════════════════════════════════════════════════

def _yoy_growth(stmts, statement_type, metric, current_period, previous_period, metric_id):
    meta = METODOLOGY.get(metric_id, {})
    current_fact = _get_fact(stmts, statement_type, metric, current_period)
    previous_fact = _get_fact(stmts, statement_type, metric, previous_period)
    current_val = _val(current_fact)
    previous_val = _val(previous_fact)
    if not _available(current_val, previous_val):
        reasons = []
        if current_val is None:
            reasons.append(f"no {current_period} data")
        if previous_val is None:
            reasons.append(f"no {previous_period} data")
        return _unavailable(metric_id, f"{current_period} vs {previous_period}", "; ".join(reasons))
    growth = _safe_divide(current_val - previous_val, abs(previous_val))
    if growth is None:
        return _unavailable(metric_id, f"{current_period} vs {previous_period}", "Cannot compute growth")
    value = round(growth * 100, 2)
    inputs = _make_inputs(
        (f"{current_period} {meta.get('name', metric)}", current_fact),
        (f"{previous_period} {meta.get('name', metric)}", previous_fact),
    )
    return CalculatedMetric(
        metric_id=metric_id, name=meta.get("name", metric_id),
        value=value, display_value=f"{'+' if value >= 0 else ''}{value:.1f}%",
        unit="%", period=f"{current_period} vs {previous_period}",
        status="calculated", classification="calculated",
        formula=meta.get("formula", ""), inputs=inputs,
        calculation=f"({current_val:,.0f} - {previous_val:,.0f}) / {abs(previous_val):,.0f} * 100 = {value:.2f}%",
        methodology=meta.get("notes", ""),
    ).to_dict()


def _cagr(stmts, statement_type, metric, start_period, end_period, n_years, metric_id):
    meta = METODOLOGY.get(metric_id, {})
    start_fact = _get_fact(stmts, statement_type, metric, start_period)
    end_fact = _get_fact(stmts, statement_type, metric, end_period)
    start_val = _val(start_fact)
    end_val = _val(end_fact)
    if not _available(start_val, end_val):
        return _unavailable(metric_id, f"{start_period} to {end_period}", "Insufficient data for CAGR")
    if n_years <= 0:
        return _unavailable(metric_id, f"{start_period} to {end_period}", "Cannot compute CAGR with 0 years")
    cagr_val = _safe_cagr(start_val, end_val, n_years)
    if cagr_val is None:
        return _unavailable(metric_id, f"{start_period} to {end_period}", "Cannot compute CAGR (negative values)")
    inputs = _make_inputs((f"{start_period} {metric}", start_fact), (f"{end_period} {metric}", end_fact))
    return CalculatedMetric(
        metric_id=metric_id, name=meta.get("name", metric_id),
        value=round(cagr_val, 2), display_value=f"{'+' if cagr_val >= 0 else ''}{cagr_val:.1f}%",
        unit="%", period=f"{start_period} to {end_period}",
        status="calculated", classification="calculated",
        formula=meta.get("formula", ""), inputs=inputs,
        calculation=f"({end_val:,.0f} / {start_val:,.0f})^(1/{n_years}) - 1 = {cagr_val:.2f}%",
        methodology=meta.get("notes", ""),
    ).to_dict()


# ══════════════════════════════════════════════════════════════════════════
# PERIOD METRICS
# ══════════════════════════════════════════════════════════════════════════

def _compute_period_metrics(stmts: dict, period: str) -> dict[str, dict]:
    """Compute all single-period metrics."""
    pm: dict[str, dict] = {}

    # Pre-fetch common facts
    rev_fact = _get_fact(stmts, "income_statement", "revenue", period)
    rev_val = _val(rev_fact)
    ta_fact = _get_fact(stmts, "balance_sheet", "total_assets", period)
    ta_val = _val(ta_fact)

    # ── Margins ──
    for mid, (num_type, num_metric, den_type, den_metric, formula, cls) in {
        "gross_margin": ("income_statement", "gross_profit", "income_statement", "revenue",
                        "Gross Profit / Revenue * 100", "calculated"),
        "operating_margin": ("income_statement", "operating_income", "income_statement", "revenue",
                            "Operating Income / Revenue * 100", "calculated"),
        "pretax_margin": ("income_statement", "pretax_income", "income_statement", "revenue",
                         "Pretax Income / Revenue * 100", "calculated"),
        "net_margin": ("income_statement", "net_income", "income_statement", "revenue",
                      "Net Income / Revenue * 100", "calculated"),
    }.items():
        meta = METODOLOGY.get(mid, {})
        num_fact = _get_fact(stmts, num_type, num_metric, period)
        den_fact = _get_fact(stmts, den_type, den_metric, period)
        num_val = _val(num_fact)
        den_val = _val(den_fact)
        if not _available(num_val, den_val):
            pm[mid] = _unavailable(mid, period, "Insufficient data")
            continue
        m = _safe_divide(num_val, den_val)
        if m is None:
            pm[mid] = _unavailable(mid, period, "Cannot compute margin")
            continue
        value = round(m * 100, 2)
        trend = _trend_info(stmts, num_type, num_metric, period, num_val)
        inputs = _make_inputs((meta.get("name", mid), num_fact), ("Revenue", den_fact))
        pm[mid] = _build_metric(mid, value, f"{value:.1f}%", period, cls, formula, inputs,
                                f"({num_val:,.0f} / {den_val:,.0f}) * 100 = {value:.2f}%", trend)

    # ── EBITDA Margin ──
    ebitda_result = _derive_ebitda(stmts, period)
    ebitda_val = _val(ebitda_result)
    if _available(ebitda_val, rev_val) and rev_val != 0:
        em = round((ebitda_val / rev_val) * 100, 2)
        pm["ebitda_margin"] = _build_metric("ebitda_margin", em, f"{em:.1f}%", period, "calculated",
            "EBITDA / Revenue * 100",
            _make_inputs(("EBITDA", ebitda_result), ("Revenue", rev_fact)),
            f"({ebitda_val:,.0f} / {rev_val:,.0f}) * 100 = {em:.2f}%")
    else:
        pm["ebitda_margin"] = _unavailable("ebitda_margin", period, "Missing EBITDA or revenue")

    # ── OCF Margin ──
    ocf_fact = _get_fact(stmts, "cash_flow", "operating_cash_flow", period)
    rev_fact = _get_fact(stmts, "income_statement", "revenue", period)
    ocf_val = _val(ocf_fact)
    rev_val = _val(rev_fact)
    if _available(ocf_val, rev_val) and rev_val != 0:
        m = round((ocf_val / rev_val) * 100, 2)
        pm["ocf_margin"] = _build_metric("ocf_margin", m, f"{m:.1f}%", period, "calculated",
            "Operating Cash Flow / Revenue * 100",
            _make_inputs(("OCF", ocf_fact), ("Revenue", rev_fact)),
            f"({ocf_val:,.0f} / {rev_val:,.0f}) * 100 = {m:.2f}%")
    else:
        pm["ocf_margin"] = _unavailable("ocf_margin", period, "Missing OCF or revenue")

    # ── Free Cash Flow ──
    capex_fact = _get_fact(stmts, "cash_flow", "capital_expenditures", period)
    capex_val = _val(capex_fact)
    if _available(ocf_val, capex_val):
        fcf = ocf_val - abs(capex_val)
        pm["free_cash_flow"] = _build_metric("free_cash_flow", round(fcf, 0),
            f"${fcf / 1e9:.1f}B" if abs(fcf) >= 1e9 else f"${fcf:,.0f}", period, "calculated",
            "Operating Cash Flow - Capital Expenditures",
            _make_inputs(("Operating Cash Flow", ocf_fact), ("Capital Expenditures", capex_fact)),
            f"{ocf_val:,.0f} - {abs(capex_val):,.0f} = {fcf:,.0f}")
    else:
        pm["free_cash_flow"] = _unavailable("free_cash_flow", period, "Missing OCF or CapEx")
        fcf = None

    # ── FCF Margin ──
    if fcf is not None and rev_val is not None and rev_val != 0:
        fcf_m = round((fcf / rev_val) * 100, 2)
        pm["fcf_margin"] = _build_metric("fcf_margin", fcf_m, f"{fcf_m:.1f}%", period, "calculated",
            "Free Cash Flow / Revenue * 100",
            _make_inputs(("FCF", ocf_fact), ("Revenue", rev_fact)),
            f"({fcf:,.0f} / {rev_val:,.0f}) * 100 = {fcf_m:.2f}%")
    else:
        pm["fcf_margin"] = _unavailable("fcf_margin", period, "Missing FCF or revenue")

    # ── Cash Conversion ──
    ni_fact = _get_fact(stmts, "income_statement", "net_income", period)
    ni_val = _val(ni_fact)
    if _available(fcf, ni_val) and ni_val != 0:
        cc = round((fcf / ni_val) * 100, 2)
        pm["cash_conversion"] = _build_metric("cash_conversion", cc, f"{cc:.1f}%", period, "calculated",
            "Free Cash Flow / Net Income * 100",
            _make_inputs(("FCF", ocf_fact), ("Net Income", ni_fact)),
            f"({fcf:,.0f} / {ni_val:,.0f}) * 100 = {cc:.2f}%")
    else:
        pm["cash_conversion"] = _unavailable("cash_conversion", period, "Missing FCF or net income")

    # ── OCF / Net Income ──
    if _available(ocf_val, ni_val) and ni_val != 0:
        ratio = round((ocf_val / ni_val) * 100, 2)
        pm["ocf_to_net_income"] = _build_metric("ocf_to_net_income", ratio, f"{ratio:.1f}%", period, "calculated",
            "Operating Cash Flow / Net Income * 100",
            _make_inputs(("OCF", ocf_fact), ("Net Income", ni_fact)),
            f"({ocf_val:,.0f} / {ni_val:,.0f}) * 100 = {ratio:.2f}%")
    else:
        pm["ocf_to_net_income"] = _unavailable("ocf_to_net_income", period, "Missing OCF or net income")

    # ── CapEx Intensity ──
    if _available(capex_val, rev_val) and rev_val != 0:
        ci = round((abs(capex_val) / rev_val) * 100, 2)
        pm["capex_intensity"] = _build_metric("capex_intensity", ci, f"{ci:.1f}%", period, "calculated",
            "Capital Expenditures / Revenue * 100",
            _make_inputs(("CapEx", capex_fact), ("Revenue", rev_fact)),
            f"{abs(capex_val):,.0f} / {rev_val:,.0f} * 100 = {ci:.2f}%")
    else:
        pm["capex_intensity"] = _unavailable("capex_intensity", period, "Missing CapEx or revenue")

    # ── CapEx / OCF ──
    if _available(capex_val, ocf_val) and ocf_val != 0:
        co = round((abs(capex_val) / ocf_val) * 100, 2)
        pm["capex_to_ocf"] = _build_metric("capex_to_ocf", co, f"{co:.1f}%", period, "calculated",
            "Capital Expenditures / Operating Cash Flow * 100",
            _make_inputs(("CapEx", capex_fact), ("OCF", ocf_fact)),
            f"{abs(capex_val):,.0f} / {ocf_val:,.0f} * 100 = {co:.2f}%")
    else:
        pm["capex_to_ocf"] = _unavailable("capex_to_ocf", period, "Missing CapEx or OCF")

    # ── Liquidity ──
    pm["current_ratio"] = _ratio(stmts, "balance_sheet", "current_assets",
                                  "balance_sheet", "current_liabilities", period, "current_ratio")
    pm["quick_ratio"] = _quick_ratio(stmts, period)
    pm["cash_ratio"] = _cash_ratio(stmts, period)

    # ── Net Working Capital ──
    ca_fact = _get_fact(stmts, "balance_sheet", "current_assets", period)
    cl_fact = _get_fact(stmts, "balance_sheet", "current_liabilities", period)
    ca_val = _val(ca_fact)
    cl_val = _val(cl_fact)
    if _available(ca_val, cl_val):
        nwc = ca_val - cl_val
        trend = _trend_info(stmts, "balance_sheet", "current_assets", period, ca_val)
        pm["net_working_capital"] = _build_metric("net_working_capital", round(nwc, 0),
            f"${nwc / 1e9:.1f}B" if abs(nwc) >= 1e9 else f"${nwc:,.0f}",
            period, "calculated", "Current Assets - Current Liabilities",
            _make_inputs(("Current Assets", ca_fact), ("Current Liabilities", cl_fact)),
            f"{ca_val:,.0f} - {cl_val:,.0f} = {nwc:,.0f}", trend)
    else:
        pm["net_working_capital"] = _unavailable("net_working_capital", period, "Missing data")

    # ── Net Working Capital / Revenue ──
    if _available(ca_val, cl_val, rev_val) and rev_val != 0:
        nwc_rev = round(((ca_val - cl_val) / rev_val) * 100, 2)
        pm["nwc_to_revenue"] = _build_metric("nwc_to_revenue", nwc_rev, f"{nwc_rev:.1f}%", period, "calculated",
            "Net Working Capital / Revenue * 100",
            _make_inputs(("NWC", ca_fact), ("Revenue", rev_fact)),
            f"{ca_val - cl_val:,.0f} / {rev_val:,.0f} * 100 = {nwc_rev:.2f}%")
    else:
        pm["nwc_to_revenue"] = _unavailable("nwc_to_revenue", period, "Missing data")

    # ── Leverage ──
    pm["debt_to_equity"] = _ratio(stmts, "balance_sheet", "total_liabilities",
                                   "balance_sheet", "shareholders_equity", period, "debt_to_equity")
    pm["debt_to_assets"] = _ratio(stmts, "balance_sheet", "total_liabilities",
                                   "balance_sheet", "total_assets", period, "debt_to_assets")
    pm["net_debt"] = _net_debt(stmts, period)

    # ── Debt / Capital ──
    total_debt = _total_debt(stmts, period)
    equity_fact = _get_fact(stmts, "balance_sheet", "shareholders_equity", period)
    equity_val = _val(equity_fact)
    if total_debt is not None and equity_val is not None:
        capital = total_debt + equity_val
        if capital > 0:
            dc = round((total_debt / capital) * 100, 2)
            pm["debt_to_capital"] = _build_metric("debt_to_capital", dc, f"{dc:.1f}%", period, "calculated",
                "Total Debt / (Total Debt + Equity) * 100",
                _make_inputs(("Total Debt", equity_fact), ("Equity", equity_fact)),
                f"{total_debt:,.0f} / {capital:,.0f} * 100 = {dc:.2f}%")
        else:
            pm["debt_to_capital"] = _unavailable("debt_to_capital", period, "Capital is zero")
    else:
        pm["debt_to_capital"] = _unavailable("debt_to_capital", period, "Missing debt or equity")

    # ── EBITDA ──
    pm["ebitda"] = _derive_ebitda(stmts, period)
    ebitda_val = _val(pm.get("ebitda"))

    # ── Debt / EBITDA ──
    if total_debt is not None and ebitda_val is not None and ebitda_val > 0:
        de = round(total_debt / ebitda_val, 2)
        pm["debt_to_ebitda"] = _build_metric("debt_to_ebitda", de, f"{de:.2f}x", period, "calculated",
            "Total Debt / EBITDA",
            _make_inputs(("Total Debt", equity_fact), ("EBITDA", _get_fact(stmts, "income_statement", "operating_income", period))),
            f"{total_debt:,.0f} / {ebitda_val:,.0f} = {de:.2f}")
    else:
        pm["debt_to_ebitda"] = _unavailable("debt_to_ebitda", period, "Missing debt or EBITDA")

    # ── Net Debt / EBITDA ──
    pm["net_debt_to_ebitda"] = _net_debt_to_ebitda(stmts, period, ebitda_val)

    # ── Interest Coverage ──
    op_fact = _get_fact(stmts, "income_statement", "operating_income", period)
    int_fact = _get_fact(stmts, "cash_flow", "interest_expense", period)
    op_val = _val(op_fact)
    int_val = _val(int_fact)
    if _available(op_val, int_val) and int_val != 0:
        ic = round(_safe_divide(op_val, abs(int_val)) or 0, 2)
        pm["interest_coverage"] = _build_metric("interest_coverage", ic, f"{ic:.2f}x", period, "calculated",
            "Operating Income / Interest Expense",
            _make_inputs(("Operating Income", op_fact), ("Interest Expense", int_fact)),
            f"{op_val:,.0f} / {abs(int_val):,.0f} = {ic:.2f}")
    else:
        pm["interest_coverage"] = _unavailable("interest_coverage", period, "Missing operating income or interest expense")

    # ── Cash Flow to Debt ──
    if _available(ocf_val, total_debt) and total_debt > 0:
        cf_debt = round((ocf_val / total_debt) * 100, 2)
        pm["cash_flow_to_debt"] = _build_metric("cash_flow_to_debt", cf_debt, f"{cf_debt:.1f}%", period, "calculated",
            "Operating Cash Flow / Total Debt * 100",
            _make_inputs(("OCF", ocf_fact), ("Total Debt", equity_fact)),
            f"{ocf_val:,.0f} / {total_debt:,.0f} * 100 = {cf_debt:.2f}%")
    else:
        pm["cash_flow_to_debt"] = _unavailable("cash_flow_to_debt", period, "Missing OCF or debt")

    # ── Returns ──
    pm["roa"] = _return_on(stmts, "income_statement", "net_income",
                           "balance_sheet", "total_assets", period, "roa")
    pm["roe"] = _return_on(stmts, "income_statement", "net_income",
                           "balance_sheet", "shareholders_equity", period, "roe")
    pm["roic"] = _roic(stmts, period)

    # ── DuPont Analysis ──
    pm["dupont"] = _dupont(stmts, period)

    # ── ROCE ──
    pm["roce"] = _roce(stmts, period)

    # ── Efficiency ──
    if _available(rev_val, ta_val) and ta_val != 0:
        turnover = round(rev_val / ta_val, 2)
        pm["asset_turnover"] = _build_metric("asset_turnover", turnover, f"{turnover:.2f}x", period, "calculated",
            "Revenue / Total Assets",
            _make_inputs(("Revenue", rev_fact), ("Total Assets", _get_fact(stmts, "balance_sheet", "total_assets", period))),
            f"{rev_val:,.0f} / {ta_val:,.0f} = {turnover:.2f}")
    else:
        pm["asset_turnover"] = _unavailable("asset_turnover", period, "Missing revenue or assets")

    ar_fact = _get_fact(stmts, "balance_sheet", "accounts_receivable", period)
    ar_val = _val(ar_fact)
    if _available(rev_val, ar_val) and ar_val != 0:
        rec_turnover = round(rev_val / ar_val, 2)
        pm["receivables_turnover"] = _build_metric("receivables_turnover", rec_turnover, f"{rec_turnover:.2f}x", period, "calculated",
            "Revenue / Accounts Receivable",
            _make_inputs(("Revenue", rev_fact), ("Accounts Receivable", ar_fact)),
            f"{rev_val:,.0f} / {ar_val:,.0f} = {rec_turnover:.2f}")
        pm["days_sales_outstanding"] = _dso(period, rec_turnover)
    else:
        pm["receivables_turnover"] = _unavailable("receivables_turnover", period, "Missing data")
        pm["days_sales_outstanding"] = _unavailable("days_sales_outstanding", period, "Missing data")

    inv_fact = _get_fact(stmts, "balance_sheet", "inventory", period)
    inv_val = _val(inv_fact)
    cor_fact = _get_fact(stmts, "income_statement", "cost_of_revenue", period)
    cor_val = _val(cor_fact)
    if _available(cor_val, inv_val) and inv_val != 0:
        inv_turnover = round(cor_val / inv_val, 2)
        pm["inventory_turnover"] = _build_metric("inventory_turnover", inv_turnover, f"{inv_turnover:.2f}x", period, "calculated",
            "Cost of Revenue / Inventory",
            _make_inputs(("Cost of Revenue", cor_fact), ("Inventory", inv_fact)),
            f"{cor_val:,.0f} / {inv_val:,.0f} = {inv_turnover:.2f}")
        pm["days_inventory_outstanding"] = _dio(period, inv_turnover)
    else:
        pm["inventory_turnover"] = _unavailable("inventory_turnover", period, "Missing data")
        pm["days_inventory_outstanding"] = _unavailable("days_inventory_outstanding", period, "Missing data")

    ap_fact = _get_fact(stmts, "balance_sheet", "accounts_payable", period)
    ap_val = _val(ap_fact)
    if _available(cor_val, ap_val) and ap_val != 0:
        pay_turnover = round(cor_val / ap_val, 2)
        pm["days_payable_outstanding"] = _dpo(period, pay_turnover)
    else:
        pm["days_payable_outstanding"] = _unavailable("days_payable_outstanding", period, "Missing data")

    # Cash Conversion Cycle
    dso_val = _val(pm.get("days_sales_outstanding"))
    dio_val = _val(pm.get("days_inventory_outstanding"))
    dpo_val = _val(pm.get("days_payable_outstanding"))
    if _available(dso_val, dio_val, dpo_val):
        ccc = dso_val + dio_val - dpo_val
        pm["cash_conversion_cycle"] = _build_metric("cash_conversion_cycle", round(ccc, 1),
            f"{ccc:.0f} days", period, "calculated",
            "DSO + DIO - DPO",
            [{"name": "DSO", "value": dso_val}, {"name": "DIO", "value": dio_val}, {"name": "DPO", "value": dpo_val}],
            f"{dso_val:.0f} + {dio_val:.0f} - {dpo_val:.0f} = {ccc:.0f}")
    else:
        pm["cash_conversion_cycle"] = _unavailable("cash_conversion_cycle", period, "Missing DSO/DIO/DPO")

    # ── Per Share ──
    shares_fact = _get_fact(stmts, "additional", "diluted_shares", period)
    shares_val = _val(shares_fact)
    if _available(ni_val, shares_val) and shares_val != 0:
        # Already have EPS from extraction, but compute if not
        pass  # EPS comes from XBRL directly

    if _available(rev_val, shares_val) and shares_val != 0:
        rps = round(rev_val / shares_val, 2)
        pm["revenue_per_share"] = _build_metric("revenue_per_share", rps, f"${rps:.2f}", period, "calculated",
            "Revenue / Diluted Shares Outstanding",
            _make_inputs(("Revenue", rev_fact), ("Shares", shares_fact)),
            f"{rev_val:,.0f} / {shares_val:,.0f} = {rps:.2f}")

    if _available(fcf, shares_val) and shares_val != 0:
        fcps = round(fcf / shares_val, 2)
        pm["fcf_per_share"] = _build_metric("fcf_per_share", fcps, f"${fcps:.2f}", period, "calculated",
            "Free Cash Flow / Diluted Shares Outstanding",
            _make_inputs(("FCF", ocf_fact), ("Shares", shares_fact)),
            f"{fcf:,.0f} / {shares_val:,.0f} = {fcps:.2f}")

    equity_fact = _get_fact(stmts, "balance_sheet", "shareholders_equity", period)
    if _available(equity_val, shares_val) and shares_val != 0:
        bvps = round(equity_val / shares_val, 2)
        pm["book_value_per_share"] = _build_metric("book_value_per_share", bvps, f"${bvps:.2f}", period, "calculated",
            "Shareholders' Equity / Diluted Shares Outstanding",
            _make_inputs(("Equity", equity_fact), ("Shares", shares_fact)),
            f"{equity_val:,.0f} / {shares_val:,.0f} = {bvps:.2f}")

    # ── Effective Tax Rate ──
    tax_fact = _get_fact(stmts, "income_statement", "income_tax_expense", period)
    tax_val = _val(tax_fact)
    pretax_fact = _get_fact(stmts, "income_statement", "pretax_income", period)
    pretax_val = _val(pretax_fact)
    if _available(tax_val, pretax_val) and pretax_val > 0:
        etr = round((abs(tax_val) / pretax_val) * 100, 2)
        pm["effective_tax_rate"] = _build_metric("effective_tax_rate", etr, f"{etr:.1f}%", period, "derived",
            "Income Tax Expense / Pretax Income * 100",
            _make_inputs(("Tax Expense", tax_fact), ("Pretax Income", pretax_fact)),
            f"{abs(tax_val):,.0f} / {pretax_val:,.0f} * 100 = {etr:.2f}%")
    else:
        pm["effective_tax_rate"] = _unavailable("effective_tax_rate", period, "Missing tax or pretax income")

    # ── Dividend Payout Ratio ──
    div_fact = _get_fact(stmts, "cash_flow", "dividends_paid", period)
    div_val = _val(div_fact)
    if _available(div_val, ni_val) and ni_val > 0:
        dpr = round((abs(div_val) / ni_val) * 100, 2)
        pm["dividend_payout_ratio"] = _build_metric("dividend_payout_ratio", dpr, f"{dpr:.1f}%", period, "calculated",
            "Dividends Paid / Net Income * 100",
            _make_inputs(("Dividends", div_fact), ("Net Income", ni_fact)),
            f"{abs(div_val):,.0f} / {ni_val:,.0f} * 100 = {dpr:.2f}%")
    else:
        pm["dividend_payout_ratio"] = _unavailable("dividend_payout_ratio", period, "Missing dividends or net income")

    # ── Share Repurchase / FCF ──
    buyback_fact = _get_fact(stmts, "cash_flow", "share_repurchases", period)
    buyback_val = _val(buyback_fact)
    if _available(buyback_val, fcf) and fcf > 0:
        bcr = round((abs(buyback_val) / fcf) * 100, 2)
        pm["buyback_to_fcf"] = _build_metric("buyback_to_fcf", bcr, f"{bcr:.1f}%", period, "calculated",
            "Share Repurchases / Free Cash Flow * 100",
            _make_inputs(("Buybacks", buyback_fact), ("FCF", ocf_fact)),
            f"{abs(buyback_val):,.0f} / {fcf:,.0f} * 100 = {bcr:.2f}%")
    else:
        pm["buyback_to_fcf"] = _unavailable("buyback_to_fcf", period, "Missing buybacks or FCF")

    return pm


# ══════════════════════════════════════════════════════════════════════════
# SPECIALIZED CALCULATIONS
# ══════════════════════════════════════════════════════════════════════════

def _ratio(stmts, num_type, num_metric, den_type, den_metric, period, metric_id):
    meta = METODOLOGY.get(metric_id, {})
    num_fact = _get_fact(stmts, num_type, num_metric, period)
    den_fact = _get_fact(stmts, den_type, den_metric, period)
    num_val = _val(num_fact)
    den_val = _val(den_fact)
    if not _available(num_val, den_val):
        return _unavailable(metric_id, period, "Insufficient data")
    r = _safe_divide(num_val, den_val)
    if r is None:
        return _unavailable(metric_id, period, "Cannot compute ratio")
    trend = _trend_info(stmts, num_type, num_metric, period, num_val)
    inputs = _make_inputs((metric_id.replace("_", " "), num_fact), (den_metric.replace("_", " "), den_fact))
    return _build_metric(metric_id, round(r, 2), f"{r:.2f}x", period, "calculated",
                         meta.get("formula", ""), inputs,
                         f"{num_val:,.0f} / {den_val:,.0f} = {r:.2f}", trend)


def _quick_ratio(stmts, period):
    meta = METODOLOGY.get("quick_ratio", {})
    cash_fact = _get_fact(stmts, "balance_sheet", "cash_and_equivalents", period)
    st_inv_fact = _get_fact(stmts, "balance_sheet", "short_term_investments", period)
    ar_fact = _get_fact(stmts, "balance_sheet", "accounts_receivable", period)
    cl_fact = _get_fact(stmts, "balance_sheet", "current_liabilities", period)
    cash_val = _val(cash_fact) or 0
    st_inv_val = _val(st_inv_fact) or 0
    ar_val = _val(ar_fact) or 0
    cl_val = _val(cl_fact)
    if cl_val is None or cl_val == 0:
        return _unavailable("quick_ratio", period, "Missing current liabilities")
    liquid = cash_val + st_inv_val + ar_val
    qr = _safe_divide(liquid, cl_val)
    if qr is None:
        return _unavailable("quick_ratio", period, "Cannot compute quick ratio")
    inputs = _make_inputs(("Cash", cash_fact), ("ST Inv", st_inv_fact), ("AR", ar_fact), ("CL", cl_fact))
    return _build_metric("quick_ratio", round(qr, 2), f"{qr:.2f}x", period, "calculated",
                         meta.get("formula", ""), inputs,
                         f"({cash_val:,.0f} + {st_inv_val:,.0f} + {ar_val:,.0f}) / {cl_val:,.0f} = {qr:.2f}")


def _cash_ratio(stmts, period):
    meta = METODOLOGY.get("cash_ratio", {})
    cash_fact = _get_fact(stmts, "balance_sheet", "cash_and_equivalents", period)
    st_inv_fact = _get_fact(stmts, "balance_sheet", "short_term_investments", period)
    cl_fact = _get_fact(stmts, "balance_sheet", "current_liabilities", period)
    cash_val = _val(cash_fact) or 0
    st_inv_val = _val(st_inv_fact) or 0
    cl_val = _val(cl_fact)
    if cl_val is None or cl_val == 0:
        return _unavailable("cash_ratio", period, "Missing current liabilities")
    liquid = cash_val + st_inv_val
    cr = _safe_divide(liquid, cl_val)
    if cr is None:
        return _unavailable("cash_ratio", period, "Cannot compute cash ratio")
    inputs = _make_inputs(("Cash", cash_fact), ("ST Inv", st_inv_fact), ("CL", cl_fact))
    return _build_metric("cash_ratio", round(cr, 2), f"{cr:.2f}x", period, "calculated",
                         meta.get("formula", ""), inputs,
                         f"({cash_val:,.0f} + {st_inv_val:,.0f}) / {cl_val:,.0f} = {cr:.2f}")


def _total_debt(stmts, period):
    st_fact = _get_fact(stmts, "balance_sheet", "short_term_debt", period)
    lt_fact = _get_fact(stmts, "balance_sheet", "long_term_debt", period)
    st_val = _val(st_fact) or 0
    lt_val = _val(lt_fact) or 0
    if st_val == 0 and lt_val == 0:
        return None
    return st_val + lt_val


def _net_debt(stmts, period):
    meta = METODOLOGY.get("net_debt", {})
    st_debt_fact = _get_fact(stmts, "balance_sheet", "short_term_debt", period)
    lt_debt_fact = _get_fact(stmts, "balance_sheet", "long_term_debt", period)
    cash_fact = _get_fact(stmts, "balance_sheet", "cash_and_equivalents", period)
    st_inv_fact = _get_fact(stmts, "balance_sheet", "short_term_investments", period)
    st_val = _val(st_debt_fact) or 0
    lt_val = _val(lt_debt_fact) or 0
    cash_val = _val(cash_fact)
    st_inv_val = _val(st_inv_fact) or 0
    if cash_val is None:
        return _unavailable("net_debt", period, "Missing cash")
    td = st_val + lt_val
    if td == 0:
        return _unavailable("net_debt", period, "Missing debt")
    nd = td - cash_val - st_inv_val
    trend = _trend_info(stmts, "balance_sheet", "cash_and_equivalents", period, cash_val)
    inputs = _make_inputs(("Total Debt", lt_debt_fact), ("Cash", cash_fact), ("ST Inv", st_inv_fact))
    return _build_metric("net_debt", round(nd, 0),
                         f"${nd / 1e9:.1f}B" if abs(nd) >= 1e9 else f"${nd:,.0f}",
                         period, "calculated", meta.get("formula", ""), inputs,
                         f"{td:,.0f} - {cash_val:,.0f} - {st_inv_val:,.0f} = {nd:,.0f}", trend)


def _derive_ebitda(stmts, period):
    meta = METODOLOGY.get("ebitda", {})
    op_fact = _get_fact(stmts, "income_statement", "operating_income", period)
    op_val = _val(op_fact)
    da_fact = _get_fact(stmts, "cash_flow", "depreciation_amortization", period)
    if da_fact is None:
        da_fact = _get_fact(stmts, "additional", "depreciation_amortization", period)
    da_val = _val(da_fact)
    if not _available(op_val, da_val):
        return _unavailable("ebitda", period, "Missing operating income or D&A")
    ebitda = op_val + da_val
    inputs = _make_inputs(("Operating Income", op_fact), ("D&A", da_fact))
    return _build_metric("ebitda", round(ebitda, 0),
                         f"${ebitda / 1e9:.1f}B" if abs(ebitda) >= 1e9 else f"${ebitda:,.0f}",
                         period, "derived", meta.get("formula", ""), inputs,
                         f"{op_val:,.0f} + {da_val:,.0f} = {ebitda:,.0f}")


def _net_debt_to_ebitda(stmts, period, ebitda_val):
    meta = METODOLOGY.get("net_debt_to_ebitda", {})
    if ebitda_val is None:
        return _unavailable("net_debt_to_ebitda", period, "EBITDA not available")
    nd_result = _net_debt(stmts, period)
    nd_val = _val(nd_result)
    if nd_val is None:
        return _unavailable("net_debt_to_ebitda", period, "Net debt not available")
    if ebitda_val == 0:
        return _unavailable("net_debt_to_ebitda", period, "EBITDA is zero")
    ratio = nd_val / ebitda_val
    return _build_metric("net_debt_to_ebitda", round(ratio, 2), f"{ratio:.2f}x", period, "calculated",
                         meta.get("formula", ""),
                         [{"name": "Net Debt", "value": nd_val}, {"name": "EBITDA", "value": ebitda_val}],
                         f"{nd_val:,.0f} / {ebitda_val:,.0f} = {ratio:.2f}")


def _return_on(stmts, num_type, num_metric, asset_type, asset_metric, period, metric_id,
               use_average=True, fallback_to_ending=True):
    meta = METODOLOGY.get(metric_id, {})
    ni_fact = _get_fact(stmts, num_type, num_metric, period)
    ni_val = _val(ni_fact)
    current_fact = _get_fact(stmts, asset_type, asset_metric, period)
    current_val = _val(current_fact)
    prev_fact = None
    prev_val = None
    if use_average:
        prev = _previous_period(period)
        if prev:
            prev_fact = _get_fact(stmts, asset_type, asset_metric, prev)
            prev_val = _val(prev_fact)
    if ni_val is None:
        return _unavailable(metric_id, period, "No net income available")
    if current_val is None:
        return _unavailable(metric_id, period, f"No {asset_metric} available")
    if use_average and prev_val is not None:
        avg = (current_val + prev_val) / 2.0
        label = "Average"
        inputs = _make_inputs(("Net Income", ni_fact),
                              (f"{asset_metric} (current)", current_fact),
                              (f"{asset_metric} (prev)", prev_fact))
    elif fallback_to_ending:
        avg = current_val
        label = "Ending"
        inputs = _make_inputs(("Net Income", ni_fact), (f"{asset_metric} (ending)", current_fact))
    else:
        return _unavailable(metric_id, period, f"No prior {asset_metric}")
    r = _safe_divide(ni_val, avg)
    if r is None:
        return _unavailable(metric_id, period, "Cannot compute return")
    value = round(r * 100, 2)
    return _build_metric(metric_id, value, f"{value:.1f}%", period, "calculated",
                         meta.get("formula", ""), inputs,
                         f"{ni_val:,.0f} / {avg:,.0f} ({label}) * 100 = {value:.2f}%")


def _roic(stmts, period):
    meta = METODOLOGY.get("roic", {})
    op_fact = _get_fact(stmts, "income_statement", "operating_income", period)
    equity_fact = _get_fact(stmts, "balance_sheet", "shareholders_equity", period)
    cash_fact = _get_fact(stmts, "balance_sheet", "cash_and_equivalents", period)
    lt_fact = _get_fact(stmts, "balance_sheet", "long_term_debt", period)
    st_fact = _get_fact(stmts, "balance_sheet", "short_term_debt", period)
    op_val = _val(op_fact)
    equity_val = _val(equity_fact)
    cash_val = _val(cash_fact)
    st_val = _val(st_fact) or 0
    lt_val = _val(lt_fact) or 0
    if not _available(op_val, equity_val, cash_val):
        return _unavailable("roic", period, "Missing inputs")
    td = st_val + lt_val
    ic = td + equity_val - cash_val
    if ic <= 0:
        return _unavailable("roic", period, "Invested capital <= 0")
    # Use effective tax rate if available
    tax_fact = _get_fact(stmts, "income_statement", "income_tax_expense", period)
    pretax_fact = _get_fact(stmts, "income_statement", "pretax_income", period)
    tax_val = _val(tax_fact)
    pretax_val = _val(pretax_fact)
    if _available(tax_val, pretax_val) and pretax_val > 0:
        effective_tax = abs(tax_val) / pretax_val
    else:
        effective_tax = 0.21  # US corporate default
    nopat = op_val * (1 - effective_tax)
    roic_val = _safe_divide(nopat, ic)
    if roic_val is None:
        return _unavailable("roic", period, "Cannot compute ROIC")
    value = round(roic_val * 100, 2)
    inputs = _make_inputs(("Operating Income", op_fact), ("Equity", equity_fact),
                          ("Cash", cash_fact), ("Total Debt", lt_fact))
    return _build_metric("roic", value, f"{value:.1f}%", period, "calculated",
                         meta.get("formula", ""), inputs,
                         f"NOPAT = {op_val:,.0f} * (1-{effective_tax:.2f}) = {nopat:,.0f}; IC = {ic:,.0f}; ROIC = {value:.2f}%")


def _roce(stmts, period):
    """Return on Capital Employed = NOPAT / Capital Employed."""
    meta = METODOLOGY.get("roce", {})
    op_fact = _get_fact(stmts, "income_statement", "operating_income", period)
    op_val = _val(op_fact)
    ta_fact = _get_fact(stmts, "balance_sheet", "total_assets", period)
    cl_fact = _get_fact(stmts, "balance_sheet", "current_liabilities", period)
    ta_val = _val(ta_fact)
    cl_val = _val(cl_fact)
    if not _available(op_val, ta_val, cl_val):
        return _unavailable("roce", period, "Missing inputs")
    capital_employed = ta_val - cl_val
    if capital_employed <= 0:
        return _unavailable("roce", period, "Capital employed <= 0")
    # Use effective tax rate
    tax_fact = _get_fact(stmts, "income_statement", "income_tax_expense", period)
    pretax_fact = _get_fact(stmts, "income_statement", "pretax_income", period)
    tax_val = _val(tax_fact)
    pretax_val = _val(pretax_fact)
    if _available(tax_val, pretax_val) and pretax_val > 0:
        etr = abs(tax_val) / pretax_val
    else:
        etr = 0.21
    nopat = op_val * (1 - etr)
    roce_val = _safe_divide(nopat, capital_employed)
    if roce_val is None:
        return _unavailable("roce", period, "Cannot compute ROCE")
    value = round(roce_val * 100, 2)
    inputs = _make_inputs(("Operating Income", op_fact), ("Total Assets", ta_fact), ("Current Liab", cl_fact))
    return _build_metric("roce", value, f"{value:.1f}%", period, "calculated",
                         meta.get("formula", ""), inputs,
                         f"NOPAT = {nopat:,.0f}; Capital = {capital_employed:,.0f}; ROCE = {value:.2f}%")


def _dupont(stmts, period):
    """DuPont decomposition: ROE = Net Margin x Asset Turnover x Equity Multiplier."""
    meta = METODOLOGY.get("dupont", {})
    ni_fact = _get_fact(stmts, "income_statement", "net_income", period)
    rev_fact = _get_fact(stmts, "income_statement", "revenue", period)
    ta_fact = _get_fact(stmts, "balance_sheet", "total_assets", period)
    eq_fact = _get_fact(stmts, "balance_sheet", "shareholders_equity", period)
    ni_val = _val(ni_fact)
    rev_val = _val(rev_fact)
    ta_val = _val(ta_fact)
    eq_val = _val(eq_fact)
    if not _available(ni_val, rev_val, ta_val, eq_val):
        return _unavailable("dupont", period, "Missing inputs")
    if rev_val == 0 or ta_val == 0 or eq_val == 0:
        return _unavailable("dupont", period, "Zero denominator")
    net_margin = ni_val / rev_val
    asset_turnover = rev_val / ta_val
    equity_multiplier = ta_val / eq_val
    roe = net_margin * asset_turnover * equity_multiplier * 100
    inputs = _make_inputs(("Net Income", ni_fact), ("Revenue", rev_fact),
                          ("Total Assets", ta_fact), ("Equity", eq_fact))
    return _build_metric("dupont", round(roe, 2), f"{roe:.1f}%", period, "calculated",
                         meta.get("formula", ""), inputs,
                         f"Margin={net_margin:.4f} x Turnover={asset_turnover:.4f} x Multiplier={equity_multiplier:.4f} = {roe:.2f}%",
                         {"previous_value": None, "change_pp": None, "direction": "flat"})


def _dso(period, rec_turnover):
    meta = METODOLOGY.get("days_sales_outstanding", {})
    if rec_turnover is None or rec_turnover == 0:
        return _unavailable("days_sales_outstanding", period, "No receivables turnover")
    dso = 365.0 / rec_turnover
    return _build_metric("days_sales_outstanding", round(dso, 1), f"{dso:.0f} days", period, "calculated",
                         meta.get("formula", ""),
                         [{"name": "Receivables Turnover", "value": rec_turnover}],
                         f"365 / {rec_turnover:.2f} = {dso:.1f}")


def _dio(period, inv_turnover):
    meta = METODOLOGY.get("days_inventory_outstanding", {})
    if inv_turnover is None or inv_turnover == 0:
        return _unavailable("days_inventory_outstanding", period, "No inventory turnover")
    dio = 365.0 / inv_turnover
    return _build_metric("days_inventory_outstanding", round(dio, 1), f"{dio:.0f} days", period, "calculated",
                         meta.get("formula", ""),
                         [{"name": "Inventory Turnover", "value": inv_turnover}],
                         f"365 / {inv_turnover:.2f} = {dio:.1f}")


def _dpo(period, pay_turnover):
    meta = METODOLOGY.get("days_payable_outstanding", {})
    if pay_turnover is None or pay_turnover == 0:
        return _unavailable("days_payable_outstanding", period, "No payables turnover")
    dpo = 365.0 / pay_turnover
    return _build_metric("days_payable_outstanding", round(dpo, 1), f"{dpo:.0f} days", period, "calculated",
                         meta.get("formula", ""),
                         [{"name": "Payables Turnover", "value": pay_turnover}],
                         f"365 / {pay_turnover:.2f} = {dpo:.1f}")


# ══════════════════════════════════════════════════════════════════════════
# MAIN CALCULATION FUNCTION
# ══════════════════════════════════════════════════════════════════════════

def calculate_metrics(statements: dict) -> dict[str, Any]:
    """Calculate all financial metrics from extracted financial statements."""
    company = statements.get("company", {})
    periods = statements.get("periods", [])

    annual_metrics: dict[str, dict[str, dict]] = {}
    growth_metrics: dict[str, dict[str, dict]] = {}
    cagr_metrics: dict[str, dict[str, dict]] = {}

    for period in periods:
        annual_metrics[period] = _compute_period_metrics(stmts=statements, period=period)

    # ── Growth ──
    sorted_periods = sorted([p for p in periods if p.startswith("FY")],
                            key=lambda p: int(p.replace("FY", "")))
    if len(sorted_periods) >= 2:
        current = sorted_periods[-1]
        previous = sorted_periods[-2]
        label = f"{current} vs {previous}"
        g: dict[str, dict] = {}
        for mid, stype, smetric in [
            ("revenue_growth", "income_statement", "revenue"),
            ("gross_profit_growth", "income_statement", "gross_profit"),
            ("operating_income_growth", "income_statement", "operating_income"),
            ("net_income_growth", "income_statement", "net_income"),
            ("eps_growth", "income_statement", "diluted_eps"),
            ("ocf_growth", "cash_flow", "operating_cash_flow"),
            ("fcf_growth", "cash_flow", "operating_cash_flow"),
        ]:
            g[mid] = _yoy_growth(statements, stype, smetric, current, previous, mid)
        growth_metrics[label] = g

    # ── CAGR ──
    if len(sorted_periods) >= 2:
        start = sorted_periods[0]
        end = sorted_periods[-1]
        try:
            start_yr = int(start.replace("FY", ""))
            end_yr = int(end.replace("FY", ""))
            n_years = end_yr - start_yr
            if n_years > 0:
                cagr_label = f"{start} to {end}"
                c: dict[str, dict] = {}
                for mid, stype, smetric in [
                    ("revenue_cagr", "income_statement", "revenue"),
                    ("net_income_cagr", "income_statement", "net_income"),
                    ("eps_cagr", "income_statement", "diluted_eps"),
                ]:
                    c[mid] = _cagr(statements, stype, smetric, start, end, n_years, mid)
                cagr_metrics[cagr_label] = c
        except (ValueError, TypeError):
            pass

    # ── Category map ──
    categories = {
        "growth": ["revenue_growth", "gross_profit_growth", "operating_income_growth",
                    "net_income_growth", "eps_growth", "ocf_growth", "fcf_growth"],
        "cagr": ["revenue_cagr", "net_income_cagr", "eps_cagr"],
        "profitability": ["gross_margin", "operating_margin", "pretax_margin", "net_margin",
                          "ebitda_margin", "fcf_margin", "ocf_margin"],
        "returns": ["roa", "roe", "roic", "roce"],
        "cash_flow": ["free_cash_flow", "cash_conversion", "ocf_to_net_income",
                      "capex_intensity", "capex_to_ocf", "cash_flow_to_debt"],
        "liquidity": ["current_ratio", "quick_ratio", "cash_ratio",
                      "net_working_capital", "nwc_to_revenue"],
        "leverage": ["debt_to_equity", "debt_to_assets", "debt_to_capital",
                     "net_debt", "debt_to_ebitda", "net_debt_to_ebitda", "interest_coverage"],
        "efficiency": ["asset_turnover", "receivables_turnover", "inventory_turnover",
                       "days_sales_outstanding", "days_inventory_outstanding",
                       "days_payable_outstanding", "cash_conversion_cycle"],
        "per_share": ["revenue_per_share", "fcf_per_share", "book_value_per_share"],
        "capital_allocation": ["dividend_payout_ratio", "buyback_to_fcf", "effective_tax_rate"],
        "dupont": ["dupont"],
        "valuation": [],  # Future: needs market data
    }

    # ── Metadata ──
    # Count unique metric types, not per-period duplicates
    latest_period = sorted_periods[-1] if sorted_periods else (periods[-1] if periods else "")
    unique_metric_ids: set[str] = set()
    calculated_count = 0
    unavailable_count = 0
    unavailable_details: list[dict] = []

    if latest_period and latest_period in annual_metrics:
        for mid, m in annual_metrics[latest_period].items():
            unique_metric_ids.add(mid)
            if m.get("status") == "calculated":
                calculated_count += 1
            else:
                unavailable_count += 1
                unavailable_details.append({
                    "metric_id": mid,
                    "status": "unavailable",
                    "reason": m.get("reason", "Required input unavailable"),
                })

    # Also count growth/cagr metrics
    for gm_group in growth_metrics.values():
        for mid, m in gm_group.items():
            unique_metric_ids.add(mid)
            if m.get("status") == "calculated":
                calculated_count += 1
            else:
                unavailable_count += 1
                unavailable_details.append({
                    "metric_id": mid,
                    "status": "unavailable",
                    "reason": m.get("reason", "Required input unavailable"),
                })

    for cm_group in cagr_metrics.values():
        for mid, m in cm_group.items():
            unique_metric_ids.add(mid)
            if m.get("status") == "calculated":
                calculated_count += 1
            else:
                unavailable_count += 1
                unavailable_details.append({
                    "metric_id": mid,
                    "status": "unavailable",
                    "reason": m.get("reason", "Required input unavailable"),
                })

    total_metrics = calculated_count + unavailable_count
    extraction_meta = statements.get("metadata", {})

    return {
        "company": company,
        "periods": periods,
        "annual_metrics": annual_metrics,
        "growth_metrics": growth_metrics,
        "cagr_metrics": cagr_metrics,
        "categories": categories,
        "metadata": {
            "calculation_engine": "Finora Financial Calculator v2.0",
            "total_metrics_attempted": total_metrics,
            "metrics_calculated": calculated_count,
            "metrics_unavailable": unavailable_count,
            "completeness": {
                "required_inputs": len(INCOME_STATEMENT_CONCEPTS) + len(BALANCE_SHEET_CONCEPTS) + len(CASH_FLOW_CONCEPTS) + len(ADDITIONAL_CONCEPTS),
                "found_primary": extraction_meta.get("metrics_extracted", 0),
                "found_fallback": 0,
                "unavailable": unavailable_count,
            },
            "unavailable_details": unavailable_details,
            "methodology": "Finora standard methodology — see metric_methodology.py",
        },
    }
