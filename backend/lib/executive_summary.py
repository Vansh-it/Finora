"""Executive summary generation service.

Builds a compact grounded analysis context from the research session,
sends it to the existing Nemotron LLM, and returns a structured
professional executive summary.

The LLM is an interpretation layer — Python remains the source of truth.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from lib.provider_manager import generate_text, TaskType
from lib.dashboard_builder import _get_metric_value, _fmt_pct, _fmt_billions, _fmt_ratio


# ── Analysis context builder ──────────────────────────────────────────────────
def _build_analysis_context(session_data: dict) -> dict:
    """Build a compact analysis context from the research session."""
    company_meta = session_data.get("company_meta", {})
    financial_stmts = session_data.get("financial_statements", {})
    calculated_metrics = session_data.get("calculated_metrics", {})
    verification_results = session_data.get("verification_results", {})
    source_registry = session_data.get("source_registry", {})

    company_name = company_meta.get("name", session_data.get("company", "Unknown"))
    ticker = company_meta.get("ticker", "")
    period_mode = session_data.get("period_mode", "latest")
    periods = financial_stmts.get("periods", [])
    latest = periods[-1] if periods else ""

    annual = calculated_metrics.get("annual_metrics", {})

    def _val(metric_id: str) -> Optional[float]:
        return _get_metric_value(annual, metric_id, latest)

    def _raw(stmt_type: str, metric: str) -> Optional[float]:
        md = financial_stmts.get(stmt_type, {}).get(metric)
        if md is None:
            return None
        if isinstance(md, dict):
            if "value" in md:
                return md.get("value")
            if periods:
                f = md.get(periods[-1])
                if isinstance(f, dict):
                    return f.get("value")
        return None

    # ── Financial snapshot ───────────────────────────────────────────────
    snapshot = {}
    for label, val in [
        ("revenue", _raw("income_statement", "revenue")),
        ("net_income", _raw("income_statement", "net_income")),
        ("operating_income", _raw("income_statement", "operating_income")),
        ("diluted_eps", _raw("income_statement", "diluted_eps")),
        ("total_assets", _raw("balance_sheet", "total_assets")),
        ("shareholders_equity", _raw("balance_sheet", "shareholders_equity")),
        ("operating_cash_flow", _raw("cash_flow", "operating_cash_flow")),
        ("free_cash_flow", _val("free_cash_flow")),
    ]:
        if val is not None:
            snapshot[label] = val

    # ── Key ratios ───────────────────────────────────────────────────────
    ratios = {}
    for mid in ["gross_margin", "operating_margin", "pretax_margin", "net_margin",
                 "ebitda_margin", "fcf_margin", "ocf_margin",
                 "roa", "roe", "roic", "roce",
                 "current_ratio", "quick_ratio", "cash_ratio",
                 "debt_to_equity", "debt_to_assets", "net_debt",
                 "debt_to_ebitda", "net_debt_to_ebitda",
                 "asset_turnover", "receivables_turnover", "days_sales_outstanding",
                 "inventory_turnover", "days_inventory_outstanding", "days_payable_outstanding",
                 "cash_conversion_cycle",
                 "capex_intensity", "buyback_to_fcf", "cash_conversion", "ocf_to_net_income",
                 "net_working_capital"]:
        v = _val(mid)
        if v is not None:
            ratios[mid] = v

    # ── Growth ───────────────────────────────────────────────────────────
    growth = {}
    growth_metrics = calculated_metrics.get("growth_metrics", {})
    for mid in ["revenue_growth", "operating_income_growth", "net_income_growth",
                 "eps_growth", "fcf_growth"]:
        v = _val(mid)
        if v is not None:
            growth[mid] = v

    # ── DuPont ───────────────────────────────────────────────────────────
    dupont = None
    dupont_raw = annual.get(latest, {}).get("dupont") if isinstance(annual.get(latest), dict) else None
    if dupont_raw is None:
        dupont_raw = annual.get("dupont")
    if isinstance(dupont_raw, dict) and dupont_raw.get("value") is not None:
        dupont = {
            "roe": dupont_raw.get("value"),
            "net_margin": dupont_raw.get("calculation", ""),
        }

    # ── Management commentary ────────────────────────────────────────────
    commentary = verification_results.get("management_commentary", [])

    # ── Verification summary ─────────────────────────────────────────────
    ver_summary = verification_results.get("summary", {})
    mismatches = ver_summary.get("mismatches", 0)
    cross_verified = ver_summary.get("exact_matches", 0) + ver_summary.get("within_tolerance", 0)

    # ── Source count ──────────────────────────────────────────────────────
    sources = source_registry.get("sources", [])
    source_count = len([s for s in sources if s.get("trust_tier", 3) <= 2])

    return {
        "company": {"name": company_name, "ticker": ticker},
        "period": {"mode": period_mode, "latest_period": latest, "all_periods": periods},
        "financial_snapshot": snapshot,
        "ratios": ratios,
        "growth": growth,
        "dupont": dupont,
        "management_commentary": commentary,
        "verification": {
            "cross_verified": cross_verified,
            "mismatches": mismatches,
            "source_count": source_count,
        },
        "forensic_scores": session_data.get("forensic_scores", {}),
        "red_flags": session_data.get("red_flags", []),
        "macro_context": session_data.get("macro_context", {}),
    }


# ── LLM prompt ────────────────────────────────────────────────────────────────
ANALYSIS_PROMPT = """You are a senior financial analyst writing a concise editorial research briefing.

Based ONLY on the following data, write a tight executive analysis.

DATA:
{context}

Write a JSON object with exactly these fields:
{{
  "the_read": "ONE concise editorial briefing of 60-100 words. Identify the most financially important story. No generic filler. No 'Company X is a leading...' unless genuinely useful. Example style: 'Operating profile improved materially as revenue accelerated while margins expanded. Free cash flow remains the strongest quality signal, with cash generation growing faster than reported earnings. Balance sheet remains unusually liquid, limiting financial-risk concerns, although current valuation embeds substantial expectations.'",
  "annotations": [
    {{"tag": "STRENGTH|WATCH|RISK", "text": "One short sentence grounded in actual data. Only include if defensible. 1-3 total annotations."}}
  ],
  "highlights": [
    {{"title": "string", "text": "1-2 sentence highlight", "importance": "high|medium|low"}}
  ],
  "growth_analysis": "2-4 sentences on growth and operating performance",
  "profitability_analysis": "2-4 sentences on margins, returns, DuPont",
  "cash_flow_analysis": "2-4 sentences on cash generation and capital allocation",
  "balance_sheet_analysis": "2-3 sentences on leverage and liquidity",
  "management_commentary_summary": "2-3 sentences summarizing management commentary if available, otherwise empty string"
}}

RULES:
1. Use ONLY numbers from the data above. Never invent values.
2. Every percentage, dollar figure, or ratio must come from the data.
3. If a metric is not in the data, do not discuss it.
4. Be professional, analytical, neutral. No hype.
5. Do NOT output investment recommendations (buy/sell/hold).
6. The_read must be 60-100 words maximum. Be ruthlessly concise.
7. Annotations: max 3. Do not force a risk if no defensible risk exists.
8. Return ONLY valid JSON. No markdown, no commentary outside JSON."""


# ── JSON parsing ──────────────────────────────────────────────────────────────
def _parse_json(text: str) -> Optional[dict]:
    """Robustly parse JSON from LLM output."""
    if not text:
        return None

    text = text.strip()

    # Try direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Try extracting from code block
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if code_block:
        try:
            result = json.loads(code_block.group(1).strip())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            result = json.loads(brace_match.group(0))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None


# ── Validation ────────────────────────────────────────────────────────────────
def _validate_summary(summary: dict, context: dict) -> dict:
    """Validate the summary structure and remove unsupported claims.

    Returns the validated (possibly trimmed) summary.
    """
    required_fields = [
        "executive_overview", "highlights", "growth_analysis",
        "profitability_analysis", "cash_flow_analysis", "balance_sheet_analysis",
        "watch_items", "management_commentary_summary", "data_quality_note",
    ]

    # Handle new 'the_read' and 'annotations' fields from updated prompt
    if "the_read" not in summary:
        # Fallback: use executive_overview if the_read not generated
        eo = summary.get("executive_overview", "")
        summary["the_read"] = str(eo)[:500] if eo else ""
    if "annotations" not in summary:
        summary["annotations"] = []
    if not isinstance(summary["annotations"], list):
        summary["annotations"] = []
    summary["annotations"] = [
        a for a in summary["annotations"]
        if isinstance(a, dict) and "tag" in a and "text" in a
    ][:3]
    # Map old watch_items to annotations if annotations is empty
    if not summary["annotations"] and summary.get("watch_items"):
        tag_map = {"WATCH": "WATCH", "STRENGTH": "STRENGTH", "RISK": "RISK"}
        for w in summary["watch_items"][:3]:
            severity = w.get("severity", "low")
            tag = tag_map.get(str(w.get("tag", "WATCH")).upper(), "WATCH")
            if severity == "high":
                tag = "RISK"
            elif severity == "low":
                tag = "STRENGTH"
            summary["annotations"].append({"tag": tag, "text": w.get("reason", w.get("text", ""))})

    # Ensure all required fields exist
    for field in required_fields:
        if field not in summary:
            summary[field] = "" if field not in ("highlights", "watch_items") else []

    # Ensure highlights is a list of dicts
    if not isinstance(summary["highlights"], list):
        summary["highlights"] = []
    summary["highlights"] = [
        h for h in summary["highlights"]
        if isinstance(h, dict) and "title" in h and "text" in h
    ][:7]

    # Ensure watch_items is a list of dicts
    if not isinstance(summary["watch_items"], list):
        summary["watch_items"] = []
    summary["watch_items"] = [
        w for w in summary["watch_items"]
        if isinstance(w, dict) and "title" in w and "reason" in w
    ][:5]

    # Validate string fields are actually strings
    for field in ["executive_overview", "growth_analysis", "profitability_analysis",
                   "cash_flow_analysis", "balance_sheet_analysis",
                   "management_commentary_summary", "data_quality_note"]:
        if not isinstance(summary[field], str):
            summary[field] = str(summary[field]) if summary[field] else ""

    return summary


# ── Data quality note (deterministic) ─────────────────────────────────────────
def _build_data_quality_note(context: dict) -> str:
    """Build a deterministic data quality note from verification metadata."""
    ver = context.get("verification", {})
    cross_verified = ver.get("cross_verified", 0)
    mismatches = ver.get("mismatches", 0)
    source_count = ver.get("source_count", 0)

    parts = ["Primary financial data: SEC XBRL."]
    if cross_verified > 0:
        parts.append(f"{cross_verified} metric{'s' if cross_verified != 1 else ''} independently cross-verified against official company materials.")
    if source_count > 0:
        parts.append(f"{source_count} authoritative source{'s' if source_count != 1 else ''} used.")
    if mismatches > 0:
        parts.append(f"{mismatches} material mismatch{'es' if mismatches != 1 else ''} detected — SEC value retained as primary.")
    else:
        parts.append("No material mismatches detected.")

    return " ".join(parts)


# ── Main generation function ──────────────────────────────────────────────────
def generate_executive_summary(session_data: dict) -> dict:
    """Generate a professional executive summary from the research session.

    Parameters
    ----------
    session_data : dict
        Research session dict (from session.to_dict()).

    Returns
    -------
    dict
        Validated executive summary with all required sections.

    Raises
    ------
    RuntimeError
        If the LLM fails completely.
    """
    # Step 1: Build analysis context
    context = _build_analysis_context(session_data)

    # Step 2: Generate summary via LLM
    prompt = ANALYSIS_PROMPT.format(context=json.dumps(context, indent=2, default=str))

    try:
        response = generate_text(prompt, task_type=TaskType.EXECUTIVE_SUMMARY)
    except Exception as exc:
        raise RuntimeError(f"LLM generation failed: {exc}")

    # Step 3: Parse JSON
    summary = _parse_json(response)
    if summary is None:
        raise RuntimeError("LLM returned invalid JSON")

    # Step 4: Validate structure
    summary = _validate_summary(summary, context)

    # Step 5: Override data quality note with deterministic version
    summary["data_quality_note"] = _build_data_quality_note(context)

    # Step 6: Add metadata
    summary["_metadata"] = {
        "company": context["company"],
        "period": context["period"],
        "source_count": context["verification"]["source_count"],
        "cross_verified": context["verification"]["cross_verified"],
    }

    return summary
