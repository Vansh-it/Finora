"""Source fact extractor.

Takes clean Markdown/text from Jina Reader and extracts structured
financial facts using the LLM (Nemotron). Facts are normalized to
match Finora's existing metric schema for cross-source verification.

LLM extraction must NEVER override SEC/XBRL numeric data.
This module only produces supporting evidence, not primary values.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from lib.provider_manager import generate_text


# ── Extraction prompt template ────────────────────────────────────────────────
EXTRACTION_PROMPT = """You are a financial data extraction engine. Extract ALL numeric financial facts from the text below.

Company: {company_name}
Ticker: {ticker}
Requested period: {period}

Return a JSON array of facts. Each fact must have:
- metric_id: one of: revenue, gross_profit, operating_income, pretax_income, net_income, diluted_eps, basic_eps, operating_cash_flow, capital_expenditures, free_cash_flow, cash_and_equivalents, total_assets, total_liabilities, shareholders_equity, total_debt, long_term_debt, short_term_debt, interest_expense, depreciation_amortization
- value: the numeric value (as a plain number, not formatted)
- unit: "USD" or "USD/shares" for EPS
- period: fiscal period label (e.g. "FY2025", "Q3-FY2025")
- period_type: "annual" or "quarterly"
- classification: "reported" if explicitly stated in the text
- confidence: 0.0 to 1.0
- evidence: a short quote or section reference from the text (max 150 chars)

Rules:
1. Only extract values that are EXPLICITLY stated in the text.
2. Do NOT calculate or infer values not present.
3. If a value is in billions (e.g. "$331.8 billion"), convert to raw dollars.
4. If a value is in millions (e.g. "$133,749 million"), convert to raw dollars.
5. Preserve the original unit if given (e.g. "USD/shares" for EPS).
6. Return an empty array if no financial facts are found.
7. Only return valid JSON — no commentary.

Text:
{text}

Return ONLY the JSON array:"""

COMMENTARY_PROMPT = """You are a financial analyst. Extract important management commentary from this earnings/investor material.

Company: {company_name}
Ticker: {ticker}

Return a JSON array of commentary items. Each item must have:
- topic: one of: revenue_drivers, margin_commentary, segment_performance, guidance, outlook, risks, strategic_investment, cost_structure, market_conditions
- summary: a concise 1-2 sentence summary
- sentiment: "positive", "negative", or "neutral"
- importance: "high", "medium", or "low"

Rules:
1. Only extract commentary that is EXPLICITLY stated.
2. Focus on the most important 5-8 items.
3. Return an empty array if no commentary is found.
4. Only return valid JSON — no commentary.

Text:
{text}

Return ONLY the JSON array:"""


# ── Public API ────────────────────────────────────────────────────────────────
def extract_facts_from_source(
    content: str,
    company_name: str,
    ticker: str,
    period: str = "latest",
    source_id: str = "",
    source_url: str = "",
    source_provider: str = "",
    source_type: str = "",
) -> dict:
    """Extract structured financial facts from source content using LLM.

    Parameters
    ----------
    content : str
        Clean Markdown/text from Jina Reader.
    company_name : str
        Company name.
    ticker : str
        Stock ticker.
    period : str
        Requested period label.
    source_id, source_url, source_provider, source_type : str
        Source metadata for evidence traceability.

    Returns
    -------
    dict
        {"facts": [...], "commentary": [...], "metadata": {...}}
    """
    if not content or len(content.strip()) < 50:
        return {
            "facts": [],
            "commentary": [],
            "metadata": {
                "source_id": source_id,
                "content_length": len(content) if content else 0,
                "extraction_status": "insufficient_content",
            },
        }

    # Truncate content for LLM context window (keep first 8000 chars)
    truncated = content[:8000]

    # ── Extract financial facts ──────────────────────────────────────────
    facts: list[dict] = []
    try:
        prompt = EXTRACTION_PROMPT.format(
            company_name=company_name,
            ticker=ticker,
            period=period,
            text=truncated,
        )
        response = generate_text(prompt)
        facts = _parse_json_array(response)
    except Exception:
        facts = []

    # ── Extract management commentary ────────────────────────────────────
    commentary: list[dict] = []
    try:
        prompt = COMMENTARY_PROMPT.format(
            company_name=company_name,
            ticker=ticker,
            text=truncated,
        )
        response = generate_text(prompt)
        commentary = _parse_json_array(response)
    except Exception:
        commentary = []

    # ── Enrich facts with source metadata ────────────────────────────────
    for fact in facts:
        fact["source_id"] = source_id
        fact["source_url"] = source_url
        fact["source_provider"] = source_provider
        fact["source_type"] = source_type

    return {
        "facts": facts,
        "commentary": commentary,
        "metadata": {
            "source_id": source_id,
            "source_url": source_url,
            "content_length": len(content),
            "facts_extracted": len(facts),
            "commentary_extracted": len(commentary),
            "extraction_status": "success" if facts else "no_facts_found",
        },
    }


# ── JSON parsing helper ──────────────────────────────────────────────────────
def _parse_json_array(text: str) -> list[dict]:
    """Robustly parse a JSON array from LLM output.

    Handles cases where LLM wraps in markdown code blocks or adds commentary.
    """
    if not text:
        return []

    text = text.strip()

    # Try direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
    except json.JSONDecodeError:
        pass

    # Try extracting from code block
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if code_block:
        try:
            result = json.loads(code_block.group(1).strip())
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return [result]
        except json.JSONDecodeError:
            pass

    # Try finding array in text
    array_match = re.search(r"\[.*\]", text, re.DOTALL)
    if array_match:
        try:
            result = json.loads(array_match.group(0))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    return []
