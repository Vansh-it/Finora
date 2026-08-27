"""Valuation engine.

Takes SEC/XBRL fundamentals + Twelve Data market data and computes
analyst-grade valuation multiples.  All arithmetic is deterministic Python —
LLMs are never used for calculations.

Every valuation metric includes full traceability:
  - formula, inputs, source evidence, period alignment, applicability
"""

from __future__ import annotations

import math
from typing import Any, Optional

from lib.financial_calculator import _val, _get_fact, CalculatedMetric


# ── Financial institution SIC codes ──────────────────────────────────────────
_FINANCIAL_SIC_RANGES = [(6000, 6999)]

_FINANCIAL_TICKERS = {
    "JPM", "GS", "MS", "BAC", "C", "WFC", "USB", "PNC", "TFC", "COF",
    "AXP", "DFS", "SYF", "BRK-A", "BRK-B", "AIG", "MET", "PRU", "TRV",
    "ALL", "CB", "MMC", "AON", "ICE", "CME", "SPGI", "MCO", "MSCI",
    "CBOE", "NDAQ", "V", "MA", "FIS", "FISV", "ADP", "PAYX",
}


def _is_financial_institution(session_data: dict) -> bool:
    meta = session_data.get("company_meta", {})
    ticker = meta.get("ticker", "").replace(".", "").replace("-", "")
    if ticker in _FINANCIAL_TICKERS:
        return True
    sic = meta.get("sic") or meta.get("sic_code")
    if sic:
        try:
            sic_int = int(sic)
            for low, high in _FINANCIAL_SIC_RANGES:
                if low <= sic_int <= high:
                    return True
        except (TypeError, ValueError):
            pass
    return False


# ── Helpers ──────────────────────────────────────────────────────────────────

def _nm_result(metric_id, period, reason, name=""):
    return {
        "metric_id": metric_id, "name": name or metric_id.replace("_", " ").title(),
        "value": None, "display_value": "NM", "unit": "", "period": period,
        "period_type": "annual", "status": "calculated", "classification": "calculated",
        "formula": "", "inputs": [], "calculation": "", "methodology": "",
        "applicability": "not_meaningful", "reason": reason,
    }


def _unavail(metric_id, period, reason, name=""):
    return {
        "metric_id": metric_id, "name": name or metric_id.replace("_", " ").title(),
        "value": None, "display_value": "N/A", "unit": "", "period": period,
        "period_type": "annual", "status": "unavailable", "classification": "calculated",
        "formula": "", "inputs": [], "calculation": "", "methodology": "",
        "applicability": "unavailable", "reason": reason,
    }


def _valuation_metric(metric_id, value, display, period, formula, inputs, calculation,
                      market_date="", is_financial=False, name="", price_type="current"):
    return {
        "metric_id": metric_id, "name": name or metric_id.replace("_", " ").title(),
        "value": value, "display_value": display, "unit": "", "period": period,
        "period_type": "annual", "status": "calculated", "classification": "calculated",
        "formula": formula, "inputs": inputs, "calculation": calculation,
        "methodology": "Finora Valuation Engine",
        "market_data_date": market_date,
        "price_type": price_type,
        "applicability": "suppressed_for_financial" if is_financial else "applicable",
    }


# ── Period-end resolution from SEC XBRL data ─────────────────────────────────
def resolve_financial_period_end(
    financial_stmts: dict,
    target_period: str,
) -> dict:
    """Resolve the authoritative fiscal period-end date from SEC XBRL data.

    Scans extracted financial facts for the target period (e.g. 'FY2023')
    and returns the actual period_end date from the SEC filing.

    Returns:
        {
            "financial_period": "FY2023",
            "period_end": "2023-06-30",
            "source": "SEC_XBRL",
            "status": "resolved"
        }
        or with status="unavailable" if no authoritative date found.
    """
    # Scan income statement facts for period_end dates
    for stmt_key in ["income_statement", "balance_sheet", "cash_flow"]:
        stmt = financial_stmts.get(stmt_key, {})
        for metric, data in stmt.items():
            if data is None:
                continue
            if isinstance(data, dict):
                # Single fact (latest mode)
                if data.get("period") == target_period and data.get("period_end"):
                    return {
                        "financial_period": target_period,
                        "period_end": data["period_end"],
                        "source": "SEC_XBRL",
                        "status": "resolved",
                    }
                # Period-keyed dict (specified mode)
                fact = data.get(target_period)
                if fact and isinstance(fact, dict) and fact.get("period_end"):
                    return {
                        "financial_period": target_period,
                        "period_end": fact["period_end"],
                        "source": "SEC_XBRL",
                        "status": "resolved",
                    }

    # Also check additional facts
    additional = financial_stmts.get("additional", {})
    for metric, data in additional.items():
        if data is None:
            continue
        if isinstance(data, dict):
            if data.get("period") == target_period and data.get("period_end"):
                return {
                    "financial_period": target_period,
                    "period_end": data["period_end"],
                    "source": "SEC_XBRL",
                    "status": "resolved",
                }
            fact = data.get(target_period)
            if fact and isinstance(fact, dict) and fact.get("period_end"):
                return {
                    "financial_period": target_period,
                    "period_end": fact["period_end"],
                    "source": "SEC_XBRL",
                    "status": "resolved",
                }

    return {
        "financial_period": target_period,
        "period_end": None,
        "source": None,
        "status": "unavailable",
        "reason": "Authoritative fiscal period-end date could not be determined from SEC XBRL data.",
    }


def _get_fiscal_period_end_from_statements(
    financial_stmts: dict,
    target_period: str,
) -> Optional[str]:
    """Extract the period_end date string from SEC XBRL financial statements.

    Returns YYYY-MM-DD string or None if not found.
    """
    result = resolve_financial_period_end(financial_stmts, target_period)
    return result.get("period_end")


def _fiscal_year_label(period: str) -> Optional[int]:
    """Extract fiscal year integer from period label like 'FY2023'."""
    try:
        return int(period.replace("FY", ""))
    except (ValueError, TypeError):
        return None


# ── Main calculation ─────────────────────────────────────────────────────────

def calculate_valuation(session_data: dict) -> dict:
    """Calculate all valuation metrics from market data + SEC fundamentals.

    For latest mode: uses current market data.
    For specified mode: uses historical market data aligned to fiscal period end.
    """
    financial_stmts = session_data.get("financial_statements", {})
    calculated_metrics = session_data.get("calculated_metrics", {})
    market_data = session_data.get("market_data", {})
    period_mode = session_data.get("period_mode", "latest")
    start_year = session_data.get("start_year")
    end_year = session_data.get("end_year")
    meta = session_data.get("company_meta", {})
    ticker = meta.get("ticker", "")

    periods = financial_stmts.get("periods", [])
    latest = periods[-1] if periods else ""

    # Determine the target valuation period
    if period_mode == "specified" and end_year:
        target_period = f"FY{end_year}"
    elif periods:
        target_period = latest
    else:
        target_period = ""

    # Use target period for fundamental data
    annual = calculated_metrics.get("annual_metrics", {})

    def _m(metric_id):
        if target_period in annual and metric_id in annual[target_period]:
            v = annual[target_period][metric_id]
            if isinstance(v, dict):
                return v.get("value")
        return None

    def _raw(stmt, metric):
        fact = _get_fact(financial_stmts, stmt, metric, target_period)
        return _val(fact)

    def _raw_fact(stmt, metric):
        return _get_fact(financial_stmts, stmt, metric, target_period)

    # ── Determine price and alignment ────────────────────────────────────
    is_historical = period_mode == "specified"
    price = market_data.get("price")
    market_date = market_data.get("price_date", "")
    price_type = "current"
    alignment_status = "current"

    if is_historical and end_year:
        # Historical: use price from market_data (already fetched by endpoint)
        # The endpoint should have fetched historical price for this period
        price_type = "historical_period_end"
        alignment_status = "exact_period_end"

        # Check if the market_data already has historical alignment
        if market_data.get("historical"):
            price = market_data.get("price")
            market_date = market_data.get("price_date", "")
            alignment_status = market_data.get("alignment_status", "exact_period_end")
        else:
            # Fallback: use whatever price we have (endpoint should have set it)
            price = market_data.get("price")
            market_date = market_data.get("price_date", "")
            if market_date:
                target_date = _get_fiscal_period_end(ticker, end_year)
                if market_date != target_date:
                    alignment_status = "previous_trading_day"
    else:
        price_type = "current"
        alignment_status = "current"

    shares_twelve = market_data.get("shares_outstanding")
    is_financial = _is_financial_institution(session_data)

    # ── Get shares outstanding ───────────────────────────────────────────
    shares = shares_twelve
    shares_source = "Twelve Data"
    if not shares:
        shares_fact = _get_fact(financial_stmts, "additional", "diluted_shares", target_period)
        shares = _val(shares_fact)
        shares_source = "SEC XBRL"

    # ── Compute Market Cap ───────────────────────────────────────────────
    market_cap = market_data.get("market_cap")
    mc_inputs = []

    if market_cap is None and price and shares:
        market_cap = price * shares
        mc_inputs = [
            {"name": "Share Price", "value": price, "source": market_data.get("source", "Twelve Data")},
            {"name": "Shares Outstanding", "value": shares, "source": shares_source},
        ]
    elif market_cap:
        mc_inputs = [{"name": "Market Cap", "value": market_cap, "source": market_data.get("source", "Twelve Data")}]

    # ── Compute Enterprise Value ─────────────────────────────────────────
    lt_debt = _val(_raw_fact("balance_sheet", "long_term_debt")) or 0
    st_debt = _val(_raw_fact("balance_sheet", "short_term_debt")) or 0
    cash = _val(_raw_fact("balance_sheet", "cash_and_equivalents")) or 0
    st_inv = _val(_raw_fact("balance_sheet", "short_term_investments")) or 0
    total_debt = lt_debt + st_debt
    total_cash = cash + st_inv

    enterprise_value = None
    ev_inputs = []
    if market_cap is not None and market_cap > 0:
        enterprise_value = market_cap + total_debt - total_cash
        ev_inputs = [
            {"name": "Market Cap", "value": market_cap, "source": market_data.get("source", "Twelve Data")},
            {"name": "Total Debt", "value": total_debt, "source": "SEC XBRL"},
            {"name": "Cash & ST Investments", "value": total_cash, "source": "SEC XBRL"},
        ]

    # ── Fundamental values ───────────────────────────────────────────────
    net_income = _raw("income_statement", "net_income")
    revenue = _raw("income_statement", "revenue")
    operating_income = _raw("income_statement", "operating_income")
    equity = _raw("balance_sheet", "shareholders_equity")
    ebitda = _m("ebitda")
    fcf = _m("free_cash_flow")

    # ── Build valuation metrics ──────────────────────────────────────────
    valuation = {}

    # ── Price per Share ──────────────────────────────────────────────────
    if price:
        valuation["share_price"] = {
            "metric_id": "share_price", "name": "Share Price",
            "value": price, "display_value": f"${price:,.2f}", "unit": "USD",
            "period": target_period, "status": "reported", "classification": "reported",
            "formula": "", "inputs": [{"name": "Price", "value": price, "source": market_data.get("source", "Twelve Data"), "date": market_date}],
            "calculation": "", "methodology": "Twelve Data" + (" historical" if is_historical else " real-time quote"),
            "market_data_date": market_date, "price_type": price_type,
            "source": market_data.get("source", "Twelve Data"),
        }
    else:
        valuation["share_price"] = _unavail("share_price", target_period, "No market price available")

    # ── Market Cap ───────────────────────────────────────────────────────
    if market_cap is not None and market_cap > 0:
        valuation["market_cap"] = _valuation_metric(
            "market_cap", market_cap,
            f"${market_cap / 1e9:,.1f}B" if market_cap >= 1e9 else f"${market_cap:,.0f}",
            target_period, "Share Price * Shares Outstanding", mc_inputs,
            f"${price:,.2f} * {shares:,.0f} = ${market_cap:,.0f}" if shares and price else f"Market Cap = ${market_cap:,.0f}",
            market_date=market_date, price_type=price_type,
        )
    else:
        valuation["market_cap"] = _unavail("market_cap", target_period, "Cannot determine market cap")

    # ── Enterprise Value ─────────────────────────────────────────────────
    if enterprise_value is not None:
        valuation["enterprise_value"] = _valuation_metric(
            "enterprise_value", enterprise_value,
            f"${enterprise_value / 1e9:,.1f}B" if enterprise_value >= 1e9 else f"${enterprise_value:,.0f}",
            target_period, "Market Cap + Total Debt - Cash & ST Investments", ev_inputs,
            f"{market_cap:,.0f} + {total_debt:,.0f} - {total_cash:,.0f} = {enterprise_value:,.0f}",
            market_date=market_date, price_type=price_type,
        )
    else:
        valuation["enterprise_value"] = _unavail("enterprise_value", target_period, "Cannot determine enterprise value")

    # ── P/E Ratio ────────────────────────────────────────────────────────
    if market_cap and net_income:
        if net_income <= 0:
            valuation["pe_ratio"] = _nm_result("pe_ratio", target_period, "Net income is negative", "P/E Ratio")
        else:
            pe = market_cap / net_income
            valuation["pe_ratio"] = _valuation_metric(
                "pe_ratio", round(pe, 2), f"{pe:.1f}x", target_period,
                "Market Cap / Net Income",
                [{"name": "Market Cap", "value": market_cap, "source": market_data.get("source", "Twelve Data")},
                 {"name": "Net Income", "value": net_income, "source": "SEC XBRL"}],
                f"{market_cap:,.0f} / {net_income:,.0f} = {pe:.2f}",
                market_date=market_date, price_type=price_type,
            )
    else:
        valuation["pe_ratio"] = _unavail("pe_ratio", target_period, "Missing market cap or net income")

    # ── Price / Sales ────────────────────────────────────────────────────
    if market_cap and revenue:
        ps = market_cap / revenue
        valuation["price_to_sales"] = _valuation_metric(
            "price_to_sales", round(ps, 2), f"{ps:.1f}x", target_period,
            "Market Cap / Revenue",
            [{"name": "Market Cap", "value": market_cap, "source": market_data.get("source", "Twelve Data")},
             {"name": "Revenue", "value": revenue, "source": "SEC XBRL"}],
            f"{market_cap:,.0f} / {revenue:,.0f} = {ps:.2f}",
            market_date=market_date, price_type=price_type,
        )
    else:
        valuation["price_to_sales"] = _unavail("price_to_sales", target_period, "Missing market cap or revenue")

    # ── Price / Book ─────────────────────────────────────────────────────
    if market_cap and equity:
        if equity <= 0:
            valuation["price_to_book"] = _nm_result("price_to_book", target_period, "Equity is negative", "Price / Book")
        else:
            pb = market_cap / equity
            valuation["price_to_book"] = _valuation_metric(
                "price_to_book", round(pb, 2), f"{pb:.1f}x", target_period,
                "Market Cap / Shareholders Equity",
                [{"name": "Market Cap", "value": market_cap, "source": market_data.get("source", "Twelve Data")},
                 {"name": "Equity", "value": equity, "source": "SEC XBRL"}],
                f"{market_cap:,.0f} / {equity:,.0f} = {pb:.2f}",
                market_date=market_date, price_type=price_type,
            )
    else:
        valuation["price_to_book"] = _unavail("price_to_book", target_period, "Missing market cap or equity")

    # ── Earnings Yield ───────────────────────────────────────────────────
    if market_cap and net_income:
        if net_income <= 0:
            valuation["earnings_yield"] = _nm_result("earnings_yield", target_period, "Net income is negative", "Earnings Yield")
        else:
            ey = (net_income / market_cap) * 100
            valuation["earnings_yield"] = _valuation_metric(
                "earnings_yield", round(ey, 2), f"{ey:.1f}%", target_period,
                "Net Income / Market Cap * 100",
                [{"name": "Net Income", "value": net_income, "source": "SEC XBRL"},
                 {"name": "Market Cap", "value": market_cap, "source": market_data.get("source", "Twelve Data")}],
                f"{net_income:,.0f} / {market_cap:,.0f} * 100 = {ey:.2f}%",
                market_date=market_date, price_type=price_type,
            )
    else:
        valuation["earnings_yield"] = _unavail("earnings_yield", target_period, "Missing inputs")

    # ── FCF Yield ────────────────────────────────────────────────────────
    if market_cap and fcf is not None:
        if fcf <= 0:
            valuation["fcf_yield"] = _nm_result("fcf_yield", target_period, "FCF is negative", "FCF Yield")
        else:
            fy = (fcf / market_cap) * 100
            valuation["fcf_yield"] = _valuation_metric(
                "fcf_yield", round(fy, 2), f"{fy:.1f}%", target_period,
                "Free Cash Flow / Market Cap * 100",
                [{"name": "FCF", "value": fcf, "source": "SEC XBRL (calculated)"},
                 {"name": "Market Cap", "value": market_cap, "source": market_data.get("source", "Twelve Data")}],
                f"{fcf:,.0f} / {market_cap:,.0f} * 100 = {fy:.2f}%",
                market_date=market_date, price_type=price_type,
            )
    else:
        valuation["fcf_yield"] = _unavail("fcf_yield", target_period, "Missing market cap or FCF")

    # ── EV / Revenue ─────────────────────────────────────────────────────
    if enterprise_value is not None and revenue and revenue > 0:
        ev_rev = enterprise_value / revenue
        valuation["ev_to_revenue"] = _valuation_metric(
            "ev_to_revenue", round(ev_rev, 2), f"{ev_rev:.1f}x", target_period,
            "Enterprise Value / Revenue",
            [{"name": "Enterprise Value", "value": enterprise_value, "source": "Calculated"},
             {"name": "Revenue", "value": revenue, "source": "SEC XBRL"}],
            f"{enterprise_value:,.0f} / {revenue:,.0f} = {ev_rev:.2f}",
            market_date=market_date, price_type=price_type, is_financial=is_financial,
        )
    else:
        valuation["ev_to_revenue"] = _unavail("ev_to_revenue", target_period, "Missing enterprise value or revenue")

    # ── EV / EBITDA ──────────────────────────────────────────────────────
    if enterprise_value is not None and ebitda:
        if ebitda <= 0:
            valuation["ev_to_ebitda"] = _nm_result("ev_to_ebitda", target_period, "EBITDA is negative", "EV / EBITDA")
        else:
            ev_ebitda = enterprise_value / ebitda
            valuation["ev_to_ebitda"] = _valuation_metric(
                "ev_to_ebitda", round(ev_ebitda, 2), f"{ev_ebitda:.1f}x", target_period,
                "Enterprise Value / EBITDA",
                [{"name": "Enterprise Value", "value": enterprise_value, "source": "Calculated"},
                 {"name": "EBITDA", "value": ebitda, "source": "SEC XBRL (derived)"}],
                f"{enterprise_value:,.0f} / {ebitda:,.0f} = {ev_ebitda:.2f}",
                market_date=market_date, price_type=price_type, is_financial=is_financial,
            )
    else:
        valuation["ev_to_ebitda"] = _unavail("ev_to_ebitda", target_period, "Missing enterprise value or EBITDA")

    # ── EV / EBIT ────────────────────────────────────────────────────────
    if enterprise_value is not None and operating_income and operating_income > 0:
        ev_ebit = enterprise_value / operating_income
        valuation["ev_to_ebit"] = _valuation_metric(
            "ev_to_ebit", round(ev_ebit, 2), f"{ev_ebit:.1f}x", target_period,
            "Enterprise Value / Operating Income",
            [{"name": "Enterprise Value", "value": enterprise_value, "source": "Calculated"},
             {"name": "Operating Income", "value": operating_income, "source": "SEC XBRL"}],
            f"{enterprise_value:,.0f} / {operating_income:,.0f} = {ev_ebit:.2f}",
            market_date=market_date, price_type=price_type, is_financial=is_financial,
        )
    elif enterprise_value is not None and operating_income and operating_income <= 0:
        valuation["ev_to_ebit"] = _nm_result("ev_to_ebit", target_period, "Operating income is negative", "EV / EBIT")
    else:
        valuation["ev_to_ebit"] = _unavail("ev_to_ebit", target_period, "Missing enterprise value or operating income")

    # ── EV / FCF ─────────────────────────────────────────────────────────
    if enterprise_value is not None and fcf and fcf > 0:
        ev_fcf = enterprise_value / fcf
        valuation["ev_to_fcf"] = _valuation_metric(
            "ev_to_fcf", round(ev_fcf, 2), f"{ev_fcf:.1f}x", target_period,
            "Enterprise Value / Free Cash Flow",
            [{"name": "Enterprise Value", "value": enterprise_value, "source": "Calculated"},
             {"name": "FCF", "value": fcf, "source": "SEC XBRL (calculated)"}],
            f"{enterprise_value:,.0f} / {fcf:,.0f} = {ev_fcf:.2f}",
            market_date=market_date, price_type=price_type, is_financial=is_financial,
        )
    elif enterprise_value is not None and fcf and fcf <= 0:
        valuation["ev_to_fcf"] = _nm_result("ev_to_fcf", target_period, "FCF is negative", "EV / FCF")
    else:
        valuation["ev_to_fcf"] = _unavail("ev_to_fcf", target_period, "Missing enterprise value or FCF")

    # ── Net Debt / Enterprise Value ──────────────────────────────────────
    net_debt_val = _m("net_debt")
    if net_debt_val is not None and enterprise_value and enterprise_value > 0:
        nd_ev = (net_debt_val / enterprise_value) * 100
        valuation["net_debt_to_ev"] = _valuation_metric(
            "net_debt_to_ev", round(nd_ev, 2), f"{nd_ev:.1f}%", target_period,
            "Net Debt / Enterprise Value * 100",
            [{"name": "Net Debt", "value": net_debt_val, "source": "SEC XBRL (calculated)"},
             {"name": "Enterprise Value", "value": enterprise_value, "source": "Calculated"}],
            f"{net_debt_val:,.0f} / {enterprise_value:,.0f} * 100 = {nd_ev:.2f}%",
            market_date=market_date, price_type=price_type,
        )
    else:
        valuation["net_debt_to_ev"] = _unavail("net_debt_to_ev", target_period, "Missing net debt or enterprise value")

    # ── Period alignment metadata ────────────────────────────────────────
    period_alignment = {
        "financial_period": target_period,
        "market_data_date": market_date,
        "price_type": price_type,
        "alignment_status": alignment_status,
        "is_current_valuation": not is_historical,
    }

    if is_historical and end_year:
        # Resolve authoritative period end from SEC XBRL data
        resolved = resolve_financial_period_end(financial_stmts, target_period)
        fiscal_end = resolved.get("period_end")
        if fiscal_end:
            period_alignment["financial_period_end"] = fiscal_end
            period_alignment["period_end_source"] = resolved.get("source", "")
            if market_date and market_date != fiscal_end:
                period_alignment["alignment_status"] = "previous_trading_day"
                period_alignment["note"] = f"Historical valuation: {target_period} financials with closing price from {market_date} (nearest trading day to fiscal year-end {fiscal_end})"
            else:
                period_alignment["alignment_status"] = "exact_period_end"
                period_alignment["note"] = f"Historical valuation: {target_period} financials with closing price from {market_date}"
        else:
            # Could not resolve period end — historical valuation unavailable
            period_alignment["alignment_status"] = "unavailable"
            period_alignment["note"] = f"Historical valuation unavailable: Finora could not determine an authoritative fiscal period-end date for {target_period}."
            # Mark all valuation metrics as unavailable
            for key in valuation:
                if isinstance(valuation[key], dict) and valuation[key].get("status") == "calculated":
                    valuation[key] = _unavail(key, target_period, "Historical valuation unavailable: fiscal period-end date could not be determined")
    else:
        period_alignment["note"] = f"Current valuation: {target_period} financials with current market price from {market_date}" if market_date else f"Current valuation: {target_period} financials"

    return {
        "market_data": market_data,
        "valuation_metrics": valuation,
        "period_alignment": period_alignment,
        "is_financial_institution": is_financial,
    }
