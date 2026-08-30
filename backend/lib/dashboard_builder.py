"""Dashboard data builder.

Transforms raw research session data (SEC statements, calculated metrics,
source registry, verification results) into a single clean universal
dashboard payload consumed by the frontend.

One payload regardless of company.
"""

from __future__ import annotations

from typing import Any, Optional


# ── Formatting helpers ────────────────────────────────────────────────────────
def _fmt_billions(value: Optional[float]) -> str:
    """Format a raw dollar value as $XX.XB."""
    if value is None:
        return "\u2014"
    b = value / 1_000_000_000
    if abs(b) >= 100:
        return f"${b:,.0f}B"
    return f"${b:,.1f}B"


def _fmt_millions(value: Optional[float]) -> str:
    """Format a raw dollar value as $XX.XM."""
    if value is None:
        return "\u2014"
    m = value / 1_000_000
    if abs(m) >= 1000:
        return f"${m/1000:,.1f}B"
    return f"${m:,.0f}M"


def _fmt_pct(value: Optional[float]) -> str:
    """Format a percentage value."""
    if value is None:
        return "\u2014"
    return f"{value:.1f}%"


def _fmt_ratio(value: Optional[float]) -> str:
    """Format a ratio value."""
    if value is None:
        return "\u2014"
    return f"{value:.2f}x"


def _fmt_eps(value: Optional[float]) -> str:
    """Format EPS."""
    if value is None:
        return "\u2014"
    return f"${value:.2f}"


def _fmt_dollar(value: Optional[float]) -> str:
    """Format raw dollar."""
    if value is None:
        return "\u2014"
    if abs(value) >= 1_000_000_000:
        return _fmt_billions(value)
    if abs(value) >= 1_000_000:
        return _fmt_millions(value)
    return f"${value:,.0f}"


def _extract_value(fact: Any) -> Optional[float]:
    """Extract numeric value from a fact dict or FinancialFact-like object."""
    if fact is None:
        return None
    if isinstance(fact, dict):
        return fact.get("value")
    if hasattr(fact, "value"):
        return fact.value
    return None


def _extract_period(fact: Any) -> str:
    """Extract period from a fact."""
    if fact is None:
        return ""
    if isinstance(fact, dict):
        return fact.get("period", "")
    if hasattr(fact, "period"):
        return fact.period
    return ""


def _raw(stmts: dict, statement_type: str, metric: str, period: str) -> Optional[float]:
    """Get raw value from extracted financial statements."""
    stmt = stmts.get(statement_type, {})
    md = stmt.get(metric)
    if md is None:
        return None
    if isinstance(md, dict):
        if "value" in md:
            return md.get("value")
        inner = md.get(period)
        if isinstance(inner, dict):
            return inner.get("value")
    return None


def _get_metric_value(annual: dict, metric_id: str, period: str) -> Optional[float]:
    """Get a metric value from the period-first annual_metrics layout."""
    if period in annual and metric_id in annual[period]:
        v = annual[period][metric_id]
        if isinstance(v, dict):
            return v.get("value")
    return None


def _get_metric_full(annual: dict, metric_id: str, period: str) -> Optional[dict]:
    """Get the full metric dict from the period-first annual_metrics layout."""
    if period in annual and metric_id in annual[period]:
        v = annual[period][metric_id]
        if isinstance(v, dict):
            return v
    return None


def _verification_for_metric(metric_id: str, calc_metrics: dict, stmts: dict, verification: dict) -> dict:
    """Build verification info for a metric."""
    ver_summary = verification.get("summary", {})
    cross_verified = ver_summary.get("exact_matches", 0) + ver_summary.get("within_tolerance", 0)
    mismatches = ver_summary.get("mismatches", 0)
    return {
        "formula": "",
        "values": [],
        "source": {"doc": "SEC XBRL", "page": ""},
        "explanation": f"Primary source: SEC XBRL. {cross_verified} metrics cross-verified.",
        "verification_status": "verified" if cross_verified > 0 and mismatches == 0 else "sec_primary_only",
    }


def _build_kpi(metric_id: str, label: str, value: Optional[float], formatter, change=None, verification=None) -> dict:
    """Build a KPI card dict."""
    if value is None:
        disp = "\u2014"
    else:
        disp = formatter(value)

    return {
        "id": metric_id,
        "label": label,
        "value": disp,
        "change": change or {"value": "\u2014", "direction": "flat"},
        "spark": [value] if value else [0],
        "verification": verification or {},
    }


# ── Main builder ──────────────────────────────────────────────────────────────
def build_dashboard_payload(session_data: dict) -> dict:
    """Build the universal dashboard payload from a research session dict."""

    company_meta = session_data.get("company_meta", {})
    financial_stmts = session_data.get("financial_statements", {})
    calculated_metrics = session_data.get("calculated_metrics", {})
    verification_results = session_data.get("verification_results", {})
    source_registry = session_data.get("source_registry", {})

    company_name = company_meta.get("name", session_data.get("company", "Unknown"))
    ticker = company_meta.get("ticker", "")
    exchange = company_meta.get("exchange", "")
    cik = company_meta.get("cik", "")
    periods = financial_stmts.get("periods", [])
    period_mode = session_data.get("period_mode", "latest")
    latest = periods[-1] if periods else ""

    annual = calculated_metrics.get("annual_metrics", {})
    growth_metrics = calculated_metrics.get("growth_metrics", {})

    # ── Company header ───────────────────────────────────────────────────
    period_label = "Latest available" if period_mode == "latest" else f"FY{session_data.get('start_year', '')}–FY{session_data.get('end_year', '')}"
    company_header = {
        "name": company_name,
        "ticker": ticker,
        "exchange": exchange,
        "period": period_label,
        "period_mode": period_mode,
        "currency": "USD",
        "cik": cik,
        "logoInitials": "".join(w[0] for w in company_name.split()[:2]).upper() if company_name else "?",
    }

    # ── KPIs ─────────────────────────────────────────────────────────────
    kpis = []

    # Revenue
    rev_val = _raw(financial_stmts, "income_statement", "revenue", latest)
    rev_prev = _raw(financial_stmts, "income_statement", "revenue", f"FY{int(latest.replace('FY',''))-1}") if latest.startswith("FY") else None
    rev_change = None
    if rev_val is not None and rev_prev is not None and rev_prev != 0:
        pct = ((rev_val - rev_prev) / abs(rev_prev)) * 100
        rev_change = {"value": f"{'+' if pct >= 0 else ''}{pct:.1f}%", "direction": "up" if pct > 0 else "down" if pct < 0 else "flat"}
    kpis.append(_build_kpi("revenue", "Revenue", rev_val, _fmt_billions, rev_change, _verification_for_metric("revenue", calculated_metrics, financial_stmts, verification_results)))

    # Net Income
    ni_val = _raw(financial_stmts, "income_statement", "net_income", latest)
    ni_prev = _raw(financial_stmts, "income_statement", "net_income", f"FY{int(latest.replace('FY',''))-1}") if latest.startswith("FY") else None
    ni_change = None
    if ni_val is not None and ni_prev is not None and ni_prev != 0:
        pct = ((ni_val - ni_prev) / abs(ni_prev)) * 100
        ni_change = {"value": f"{'+' if pct >= 0 else ''}{pct:.1f}%", "direction": "up" if pct > 0 else "down" if pct < 0 else "flat"}
    kpis.append(_build_kpi("net-income", "Net Income", ni_val, _fmt_billions, ni_change, _verification_for_metric("net_income", calculated_metrics, financial_stmts, verification_results)))

    # Operating Income
    oi_val = _raw(financial_stmts, "income_statement", "operating_income", latest)
    oi_prev = _raw(financial_stmts, "income_statement", "operating_income", f"FY{int(latest.replace('FY',''))-1}") if latest.startswith("FY") else None
    oi_change = None
    if oi_val is not None and oi_prev is not None and oi_prev != 0:
        pct = ((oi_val - oi_prev) / abs(oi_prev)) * 100
        oi_change = {"value": f"{'+' if pct >= 0 else ''}{pct:.1f}%", "direction": "up" if pct > 0 else "down" if pct < 0 else "flat"}
    kpis.append(_build_kpi("op-income", "Operating Income", oi_val, _fmt_billions, oi_change, _verification_for_metric("operating_income", calculated_metrics, financial_stmts, verification_results)))

    # EPS
    eps_val = _raw(financial_stmts, "income_statement", "diluted_eps", latest)
    kpis.append(_build_kpi("eps", "EPS (Diluted)", eps_val, _fmt_eps, verification=_verification_for_metric("diluted_eps", calculated_metrics, financial_stmts, verification_results)))

    # FCF
    fcf_val = _get_metric_value(annual, "free_cash_flow", latest)
    kpis.append(_build_kpi("fcf", "Free Cash Flow", fcf_val, _fmt_billions, verification=_verification_for_metric("free_cash_flow", calculated_metrics, financial_stmts, verification_results)))

    # Gross Margin
    gm_val = _get_metric_value(annual, "gross_margin", latest)
    gm_change = None
    if latest.startswith("FY"):
        prev_p = f"FY{int(latest.replace('FY',''))-1}"
        gm_prev = _get_metric_value(annual, "gross_margin", prev_p)
        if gm_val is not None and gm_prev is not None:
            pp = gm_val - gm_prev
            gm_change = {"value": f"{'+' if pp >= 0 else ''}{pp:.1f}pp", "direction": "up" if pp > 0 else "down" if pp < 0 else "flat"}
    kpis.append(_build_kpi("gross-margin", "Gross Margin", gm_val, _fmt_pct, gm_change, _verification_for_metric("gross_margin", calculated_metrics, financial_stmts, verification_results)))

    # ── Income Statement rows ────────────────────────────────────────────
    income_metrics = [
        ("revenue", "Revenue"),
        ("cost_of_revenue", "Cost of Revenue"),
        ("gross_profit", "Gross Profit"),
        ("operating_income", "Operating Income"),
        ("pretax_income", "Pretax Income"),
        ("net_income", "Net Income"),
        ("basic_eps", "Basic EPS"),
        ("diluted_eps", "Diluted EPS"),
    ]
    income_rows = []
    for mid, label in income_metrics:
        strong = mid in ("revenue", "gross_profit", "operating_income", "net_income")
        vals = []
        for p in periods:
            v = _raw(financial_stmts, "income_statement", mid, p)
            if v is not None:
                if "eps" in mid:
                    vals.append(_fmt_eps(v))
                else:
                    vals.append(_fmt_billions(v))
            else:
                vals.append("\u2014")
        income_rows.append({"label": label, "values": vals, "strong": strong})

    # ── Balance Sheet rows ───────────────────────────────────────────────
    bs_metrics = [
        ("cash_and_equivalents", "Cash & Equivalents"),
        ("short_term_investments", "Short-term Investments"),
        ("accounts_receivable", "Accounts Receivable"),
        ("current_assets", "Current Assets"),
        ("total_assets", "Total Assets"),
        ("current_liabilities", "Current Liabilities"),
        ("total_liabilities", "Total Liabilities"),
        ("long_term_debt", "Long-term Debt"),
        ("short_term_debt", "Short-term Debt"),
        ("shareholders_equity", "Shareholders' Equity"),
    ]
    balance_rows = []
    for mid, label in bs_metrics:
        strong = mid in ("total_assets", "total_liabilities", "shareholders_equity")
        vals = []
        for p in periods:
            v = _raw(financial_stmts, "balance_sheet", mid, p)
            vals.append(_fmt_billions(v) if v is not None else "\u2014")
        balance_rows.append({"label": label, "values": vals, "strong": strong})

    # ── Cash Flow rows ───────────────────────────────────────────────────
    cf_metrics = [
        ("operating_cash_flow", "Operating Cash Flow"),
        ("capital_expenditures", "Capital Expenditures"),
        ("investing_cash_flow", "Investing Cash Flow"),
        ("financing_cash_flow", "Financing Cash Flow"),
    ]
    cashflow_rows = []
    for mid, label in cf_metrics:
        strong = mid == "operating_cash_flow"
        vals = []
        for p in periods:
            v = _raw(financial_stmts, "cash_flow", mid, p)
            vals.append(_fmt_billions(v) if v is not None else "\u2014")
        cashflow_rows.append({"label": label, "values": vals, "strong": strong})

    # ── Growth rows ──────────────────────────────────────────────────────
    growth_list = [
        ("revenue_growth", "Revenue Growth"),
        ("operating_income_growth", "Operating Income Growth"),
        ("net_income_growth", "Net Income Growth"),
        ("eps_growth", "EPS Growth"),
    ]
    growth_rows = []
    for mid, label in growth_list:
        vals = []
        for p_label in growth_metrics:
            g = growth_metrics[p_label].get(mid, {})
            v = g.get("value")
            vals.append(f"{'+' if v is not None and v >= 0 else ''}{v:.1f}%" if v is not None else "\u2014")
        growth_rows.append({"label": label, "values": vals, "strong": mid == "revenue_growth"})

    # ── Profitability metrics ────────────────────────────────────────────
    profitability = []
    for mid in ["gross_margin", "operating_margin", "pretax_margin", "net_margin",
                "ebitda_margin", "fcf_margin", "ocf_margin",
                "roa", "roe", "roic", "roce"]:
        v = _get_metric_value(annual, mid, latest)
        disp = _fmt_pct(v)
        profitability.append({"metric": mid.replace("_", " ").title(), "value": disp, "note": ""})

    # ── Liquidity ────────────────────────────────────────────────────────
    liquidity = []
    for mid in ["current_ratio", "quick_ratio", "cash_ratio", "net_working_capital", "nwc_to_revenue"]:
        v = _get_metric_value(annual, mid, latest)
        if mid in ("net_working_capital",):
            disp = _fmt_dollar(v)
        elif mid in ("nwc_to_revenue",):
            disp = _fmt_pct(v)
        else:
            disp = _fmt_ratio(v)
        liquidity.append({"metric": mid.replace("_", " ").title(), "value": disp, "note": ""})

    # ── Leverage ─────────────────────────────────────────────────────────
    leverage = []
    for mid in ["debt_to_equity", "debt_to_assets", "debt_to_capital",
                "net_debt", "debt_to_ebitda", "net_debt_to_ebitda", "cash_flow_to_debt", "interest_coverage"]:
        v = _get_metric_value(annual, mid, latest)
        if mid in ("net_debt",):
            disp = _fmt_dollar(v)
        elif mid in ("debt_to_equity", "debt_to_assets", "debt_to_capital", "cash_flow_to_debt", "interest_coverage"):
            disp = _fmt_pct(v) if v is not None and "coverage" not in mid else _fmt_ratio(v)
            if "coverage" in mid:
                disp = _fmt_ratio(v)
        else:
            disp = _fmt_ratio(v)
        leverage.append({"metric": mid.replace("_", " ").title(), "value": disp, "note": ""})

    # ── Efficiency ───────────────────────────────────────────────────────
    efficiency = []
    for mid in ["asset_turnover", "receivables_turnover", "days_sales_outstanding",
                "inventory_turnover", "days_inventory_outstanding", "days_payable_outstanding",
                "cash_conversion_cycle"]:
        v = _get_metric_value(annual, mid, latest)
        if "days" in mid or "cycle" in mid:
            disp = f"{v:.0f} days" if v is not None else "\u2014"
        else:
            disp = _fmt_ratio(v)
        efficiency.append({"metric": mid.replace("_", " ").title(), "value": disp, "note": ""})

    # ── Capital Allocation ───────────────────────────────────────────────
    capital_alloc = []
    for mid in ["capex_intensity", "buyback_to_fcf", "cash_conversion", "ocf_to_net_income"]:
        v = _get_metric_value(annual, mid, latest)
        disp = _fmt_pct(v)
        capital_alloc.append({"metric": mid.replace("_", " ").title(), "value": disp, "note": ""})

    # ── DuPont ───────────────────────────────────────────────────────────
    dupont_data = None
    dupont_full = _get_metric_full(annual, "dupont", latest)
    if dupont_full and dupont_full.get("status") == "calculated":
        calc_str = dupont_full.get("calculation", "")
        # Parse components from calculation string
        dupont_data = {
            "roe": dupont_full.get("display_value", "\u2014"),
            "net_margin": "",
            "asset_turnover": "",
            "equity_multiplier": "",
            "calculation": calc_str,
            "methodology": dupont_full.get("methodology", "Finora DuPont Analysis"),
        }
        # Try to extract values from calculation
        if "Margin=" in calc_str and "Turnover=" in calc_str and "Multiplier=" in calc_str:
            try:
                parts = calc_str.split("x")
                for part in parts:
                    if "Margin=" in part:
                        val = float(part.split("=")[1].strip())
                        dupont_data["net_margin"] = f"{val*100:.1f}%"
                    elif "Turnover=" in part:
                        val = float(part.split("=")[1].strip())
                        dupont_data["asset_turnover"] = f"{val:.2f}x"
                    elif "Multiplier=" in part:
                        val = float(part.split("=")[1].split("=")[0].strip())
                        dupont_data["equity_multiplier"] = f"{val:.2f}x"
            except (ValueError, IndexError):
                pass

    # ── Charts ───────────────────────────────────────────────────────────
    def _chart_data(metric: str) -> list:
        result = []
        for p in periods:
            v = _raw(financial_stmts, "income_statement" if metric in ("revenue", "operating_income", "net_income") else "cash_flow", metric, p)
            if v is not None:
                result.append({"label": p, "value": v / 1e9})
        return result

    revenue_chart = _chart_data("revenue")
    op_income_chart = _chart_data("operating_income")
    net_income_chart = _chart_data("net_income")
    fcf_chart = []
    for p in periods:
        v = _get_metric_value(annual, "free_cash_flow", p)
        if v is not None:
            fcf_chart.append({"label": p, "value": v / 1e9})

    # ── Sources ──────────────────────────────────────────────────────────
    sources = []
    for s in source_registry.get("sources", []):
        sources.append({
            "id": s.get("source_id", "unknown"),
            "name": s.get("title") or s.get("provider", "Unknown"),
            "meta": f"{s.get('source_type', '')} · {s.get('authority', '')} · Tier {s.get('trust_tier', '?')}",
            "pages": s.get("url", ""),
            "status": s.get("status", "verified"),
            "url": s.get("url", ""),
            "trust_tier": s.get("trust_tier", 3),
            "period": s.get("period", ""),
        })

    # ── Management Commentary ────────────────────────────────────────────
    commentary = verification_results.get("management_commentary", [])

    # ── Data quality ─────────────────────────────────────────────────────
    ver_summary = verification_results.get("summary", {})

    data_quality = {
        "primary_source": "SEC XBRL",
        "metrics_calculated": (
            len([mid for mid, m in annual.get(latest, {}).items()
                 if isinstance(m, dict) and m.get("status") == "calculated"]) +
            len([mid for gm in growth_metrics.values() for mid, m in gm.items()
                 if isinstance(m, dict) and m.get("status") == "calculated"])
        ),
        "cross_verified": ver_summary.get("exact_matches", 0) + ver_summary.get("within_tolerance", 0),
        "mismatches": ver_summary.get("mismatches", 0),
        "sources_count": len(sources),
    }

    # ── Valuation ────────────────────────────────────────────────────────
    valuation = session_data.get("valuation_metrics") or {}
    valuation_metrics = valuation.get("valuation_metrics", {}) if isinstance(valuation, dict) else {}
    period_alignment = valuation.get("period_alignment", {}) if isinstance(valuation, dict) else {}
    market_data = session_data.get("market_data") or {}
    is_financial = valuation.get("is_financial_institution", False) if isinstance(valuation, dict) else False

    # Build valuation section
    is_historical = market_data.get("historical", False)
    valuation_section = {
        "market_data": {
            "price": market_data.get("price"),
            "price_date": market_data.get("price_date", ""),
            "previous_close": market_data.get("previous_close"),
            "percent_change": market_data.get("percent_change"),
            "exchange": market_data.get("exchange", ""),
            "currency": market_data.get("currency", "USD"),
            "source": market_data.get("source", ""),
            "is_historical": is_historical,
            "alignment_status": market_data.get("alignment_status", "current"),
            "target_date": market_data.get("target_date", ""),
        },
        "metrics": [],
        "period_alignment": period_alignment,
        "is_financial_institution": is_financial,
        "is_historical": is_historical,
    }

    # Order of display
    val_display_order = [
        ("share_price", "Share Price"),
        ("market_cap", "Market Cap"),
        ("enterprise_value", "Enterprise Value"),
        ("pe_ratio", "P/E Ratio"),
        ("ev_to_revenue", "EV / Revenue"),
        ("ev_to_ebitda", "EV / EBITDA"),
        ("price_to_sales", "Price / Sales"),
        ("price_to_book", "Price / Book"),
        ("ev_to_ebit", "EV / EBIT"),
        ("ev_to_fcf", "EV / FCF"),
        ("earnings_yield", "Earnings Yield"),
        ("fcf_yield", "FCF Yield"),
        ("net_debt_to_ev", "Net Debt / EV"),
    ]
    for mid, label in val_display_order:
        m = valuation_metrics.get(mid)
        if m:
            valuation_section["metrics"].append({
                "metric_id": mid,
                "name": label,
                "display_value": m.get("display_value", "\u2014"),
                "value": m.get("value"),
                "status": m.get("status", "unavailable"),
                "applicability": m.get("applicability", "applicable"),
                "formula": m.get("formula", ""),
                "inputs": m.get("inputs", []),
                "calculation": m.get("calculation", ""),
                "market_data_date": m.get("market_data_date", ""),
                "price_type": m.get("price_type", "current"),
                "reason": m.get("reason", ""),
            })

    return {
        "company": company_header,
        "periods": periods,
        "kpis": kpis,
        "income_statement": {"columns": ["Line item"] + periods, "rows": income_rows},
        "balance_sheet": {"columns": ["Line item"] + periods, "rows": balance_rows},
        "cash_flow": {"columns": ["Line item"] + periods, "rows": cashflow_rows},
        "growth": {"columns": ["Metric"] + periods, "rows": growth_rows},
        "profitability": profitability,
        "liquidity": liquidity,
        "leverage": leverage,
        "efficiency": efficiency,
        "capital_allocation": capital_alloc,
        "dupont": dupont_data,
        "charts": {
            "revenue": revenue_chart,
            "operating_income": op_income_chart,
            "net_income": net_income_chart,
            "free_cash_flow": fcf_chart,
        },
        "sources": sources,
        "management_commentary": commentary,
        "data_quality": data_quality,
        "executive_summary": session_data.get("executive_summary"),
        "valuation": valuation_section,
    }
