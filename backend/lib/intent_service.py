"""Intent classification engine.

Classifies every user prompt into exactly one of two intents:
  - ``chat``  — casual conversation, greetings, small talk
  - ``research`` — requests for financial/company research

Uses a fast deterministic local classifier for obvious cases.
Only falls back to Nemotron LLM for genuinely ambiguous prompts.
Never waits longer than 5 seconds for classification.
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass
from typing import Any, Optional

# ── Known company names and tickers ──────────────────────────────────────────
# A broad set of well-known public companies for deterministic matching.
_KNOWN_COMPANIES: dict[str, str] = {
    # Tech
    "microsoft": "Microsoft", "msft": "Microsoft",
    "apple": "Apple", "aapl": "Apple",
    "google": "Alphabet", "alphabet": "Alphabet", "googl": "Alphabet", "goog": "Alphabet",
    "amazon": "Amazon", "amzn": "Amazon",
    "nvidia": "NVIDIA", "nvda": "NVIDIA",
    "meta": "Meta", "facebook": "Meta", "meta platforms": "Meta",
    "tesla": "Tesla", "tsla": "Tesla",
    "netflix": "Netflix", "nflx": "Netflix",
    "adobe": "Adobe", "adbe": "Adobe",
    "salesforce": "Salesforce", "crm": "Salesforce",
    "oracle": "Oracle", "orcl": "Oracle",
    "ibm": "IBM",
    "intel": "Intel", "intc": "Intel",
    "amd": "AMD",
    "broadcom": "Broadcom", "avgo": "Broadcom",
    "qualcomm": "Qualcomm", "qcom": "Qualcomm",
    "cisco": "Cisco", "csco": "Cisco",
    "palantir": "Palantir", "pltr": "Palantir",
    "snowflake": "Snowflake", "snow": "Snowflake",
    "databricks": "Databricks",
    "uber": "Uber", "uber technologies": "Uber",
    "lyft": "Lyft",
    "shopify": "Shopify", "shop": "Shopify",
    "spotify": "Spotify", "spot": "Spotify",
    "snap": "Snap", "snapchat": "Snap",
    "pinterest": "Pinterest", "pins": "Pinterest",
    "crowdstrike": "CrowdStrike", "crwd": "CrowdStrike",
    "palo alto": "Palo Alto Networks", "panw": "Palo Alto Networks",
    "servicenow": "ServiceNow", "now": "ServiceNow",
    "intuit": "Intuit", "intu": "Intuit",
    "paypal": "PayPal", "pypl": "PayPal",
    "block": "Block", "square": "Block", "sq": "Block",
    "twilio": "Twilio", "twlo": "Twilio",
    "cloudflare": "Cloudflare", "net": "Cloudflare",
    "zoom": "Zoom", "zm": "Zoom",
    "dell": "Dell", "dell technologies": "Dell",
    "hp": "HP", "hewlett packard": "HP",
    # Finance
    "jpmorgan": "JPMorgan Chase", "jpmorgan chase": "JPMorgan Chase", "jpm": "JPMorgan Chase",
    "goldman": "Goldman Sachs", "goldman sachs": "Goldman Sachs", "gs": "Goldman Sachs",
    "morgan stanley": "Morgan Stanley", "ms": "Morgan Stanley",
    "bank of america": "Bank of America", "boa": "Bank of America", "bac": "Bank of America",
    "citigroup": "Citigroup", "citi": "Citigroup", "c": "Citigroup",
    "wells fargo": "Wells Fargo", "wfc": "Wells Fargo",
    "visa": "Visa", "v": "Visa",
    "mastercard": "Mastercard", "ma": "Mastercard",
    "berkshire": "Berkshire Hathaway", "berkshire hathaway": "Berkshire Hathaway", "brk": "Berkshire Hathaway",
    "blackrock": "BlackRock", "blk": "BlackRock",
    "charles schwab": "Charles Schwab", "schwab": "Charles Schwab", "schw": "Charles Schwab",
    "fidelity": "Fidelity",
    "td bank": "TD Bank",
    "ubs": "UBS",
    "barclays": "Barclays",
    "hsbc": "HSBC",
    "deutsche bank": "Deutsche Bank",
    # Healthcare
    "johnson": "Johnson & Johnson", "johnson & johnson": "Johnson & Johnson", "jj": "Johnson & Johnson",
    "unitedhealth": "UnitedHealth Group", "unitedhealth group": "UnitedHealth Group", "unh": "UnitedHealth Group",
    "pfizer": "Pfizer", "pfe": "Pfizer",
    "moderna": "Moderna", "mrna": "Moderna",
    "abbvie": "AbbVie", "abbv": "AbbVie",
    "merck": "Merck", "mrk": "Merck",
    "amgen": "Amgen", "amgn": "Amgen",
    "gilead": "Gilead Sciences", "gilead sciences": "Gilead Sciences", "gild": "Gilead Sciences",
    "eli lilly": "Eli Lilly", "lilly": "Eli Lilly", "lly": "Eli Lilly",
    "abbott": "Abbott Laboratories", "abt": "Abbott Laboratories",
    "bristol-myers": "Bristol-Myers Squibb", "bristol myers": "Bristol-Myers Squibb", "bmy": "Bristol-Myers Squibb",
    "amgen": "Amgen",
    # Consumer
    "coca-cola": "Coca-Cola", "coca cola": "Coca-Cola", "ko": "Coca-Cola",
    "pepsi": "PepsiCo", "pepsico": "PepsiCo", "pep": "PepsiCo",
    "procter": "Procter & Gamble", "procter & gamble": "Procter & Gamble", "pg": "Procter & Gamble",
    "walmart": "Walmart", "wmt": "Walmart",
    "costco": "Costco", "cost": "Costco",
    "mcdonald": "McDonald's", "mcdonalds": "McDonald's", "mcd": "McDonald's",
    "starbucks": "Starbucks", "sbux": "Starbucks",
    "nike": "Nike", "nke": "Nike",
    "disney": "Disney", "waltes disney": "Disney", "dis": "Disney",
    "comcast": "Comcast", "cmcsa": "Comcast",
    # Energy
    "exxon": "ExxonMobil", "exxonmobil": "ExxonMobil", "xom": "ExxonMobil",
    "chevron": "Chevron", "cvx": "Chevron",
    "shell": "Shell", "shel": "Shell",
    "bp": "BP",
    # Industrial
    "boeing": "Boeing", "ba": "Boeing",
    "lockheed": "Lockheed Martin", "lockheed martin": "Lockheed Martin", "lmt": "Lockheed Martin",
    "caterpillar": "Caterpillar", "cat": "Caterpillar",
    "ge": "GE Aerospace", "ge aerospace": "GE Aerospace",
    # Telecom
    "at&t": "AT&T", "att": "AT&T", "t": "AT&T",
    "verizon": "Verizon", "vz": "Verizon",
    "t-mobile": "T-Mobile", "tmus": "T-Mobile",
    # Other
    "taiwan semiconductor": "TSMC", "tsmc": "TSMC", "tsm": "TSMC",
    "samsung": "Samsung",
    "byd": "BYD",
    "toyota": "Toyota", "tm": "Toyota",
    "honda": "Honda",
    "sony": "Sony",
    "spotify": "Spotify",
    "airbnb": "Airbnb", "abnb": "Airbnb",
    "doordash": "DoorDash", "dash": "DoorDash",
    "robinhood": "Robinhood", "hood": "Robinhood",
    "coinbase": "Coinbase", "coin": "Coinbase",
    "palantir": "Palantir",
    "arm": "ARM Holdings", "arm holdings": "ARM Holdings",
    "sofi": "SoFi Technologies", "sofi technologies": "SoFi Technologies",
    "rivian": "Rivian", "rivn": "Rivian",
    "lucid": "Lucid", "lcid": "Lucid",
    "nio": "NIO",
}

# ── Chat signals ─────────────────────────────────────────────────────────────
# Patterns that strongly indicate a casual chat, not research.
_CHAT_EXACT = {
    "hi", "hello", "hey", "howdy", "sup", "yo", "hola", "thanks", "thank you",
    "thx", "ty", "please", "ok", "okay", "yes", "no", "sure", "cool", "nice",
    "bye", "goodbye", "see you", "good morning", "good afternoon", "good evening",
    "what's up", "how are you", "how are you doing", "help",
}

_CHAT_STARTS = [
    "what is ", "what's ", "what are ", "what does ", "how do ", "how does ",
    "how to ", "can you ", "could you ", "tell me about ", "explain ",
    "define ", "what do you ", "do you ", "is it ", "are you ",
    "what happened ", "why do ", "why is ", "what's the difference ",
    "what's a ", "what is a ", "what are the ", "how much ",
    "who are ", "how are ", "who is ", "tell me ", "say ", "give me ",
]

# ── Research signals ─────────────────────────────────────────────────────────
_RESEARCH_VERBS = [
    "research", "analyze", "analyse", "investigate", "examine", "study",
    "evaluate", "assess", "review", "get", "build", "show", "display",
    "create", "generate", "find", "look up", "pull up", "fetch",
    "prepare", "compile", "summarize", "summarise", "compare",
]

_RESEARCH_NOUNS = [
    "financial", "financials", "revenue", "earnings", "income", "profit",
    "loss", "balance sheet", "cash flow", "metrics", "ratio", "ratios",
    "valuation", "market cap", "stock", "share price", "dividend",
    "filing", "10-k", "10-q", "sec", "edgar", "fiscal",
    "annual report", "quarterly", "dashboard", "report",
]


# ── Data classes ─────────────────────────────────────────────────────────────
@dataclass
class ChatResult:
    intent: str = "chat"
    confidence: float = 1.0
    model_used: str = "local"

    def to_dict(self) -> dict[str, Any]:
        return {"intent": self.intent, "confidence": self.confidence}


@dataclass
class ResearchResult:
    intent: str = "research"
    company: str = ""
    period_mode: str = "latest"
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    objective: str = ""
    confidence: float = 0.0
    model_used: str = "local"

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "company": self.company,
            "period_mode": self.period_mode,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "objective": self.objective,
            "confidence": self.confidence,
        }


IntentResult = ChatResult | ResearchResult


# ── Year extraction ──────────────────────────────────────────────────────────
_YEAR_RANGE_RE = re.compile(
    r"(?:fy|fiscal\s+year\s+)?(\d{4})\s*[-–—to]+\s*(?:fy|fiscal\s+year\s+)?(\d{4})",
    re.IGNORECASE,
)
_SINGLE_YEAR_RE = re.compile(
    r"(?:fy|fiscal\s+year\s+)?(\d{4})",
    re.IGNORECASE,
)


def _extract_years(text: str) -> tuple[Optional[int], Optional[int], str]:
    """Extract start/end years and determine period_mode."""
    # Try range first
    m = _YEAR_RANGE_RE.search(text)
    if m:
        y1, y2 = int(m.group(1)), int(m.group(2))
        if 2000 <= y1 <= 2099 and 2000 <= y2 <= 2099:
            return y1, y2, "specified"

    # Try single year
    m = _SINGLE_YEAR_RE.search(text)
    if m:
        y = int(m.group(1))
        if 2000 <= y <= 2099:
            return y, y, "specified"

    return None, None, "latest"


# ── Company extraction ───────────────────────────────────────────────────────
def _extract_company(text: str, known_only: bool = False) -> tuple[str, str]:
    """Extract company name from text. Returns (canonical_name, raw_match).

    If known_only is True, only return matches against the known company list.
    Falls back to None if no known company is found.
    """
    lower = text.lower().strip()

    # Remove common prefixes/suffixes
    for prefix in ["research ", "analyze ", "analyse ", "investigate ", "examine ",
                    "study ", "evaluate ", "assess ", "review ", "get ", "build ",
                    "show ", "display ", "create ", "generate ", "find ",
                    "look up ", "pull up ", "fetch ", "prepare ", "compile ",
                    "summarize ", "summarise ", "compare ", "company ", "stock ",
                    "financials for ", "financials of ", "report on ", "report for ",
                    "dashboard for ", "dashboard of "]:
        if lower.startswith(prefix):
            lower = lower[len(prefix):]
            break

    # Remove year patterns
    lower = _YEAR_RANGE_RE.sub("", lower).strip()
    lower = _SINGLE_YEAR_RE.sub("", lower).strip()

    # Remove trailing research words
    for suffix in [" financials", " financial", " research", " analysis",
                    " latest", " report", " dashboard", " earnings",
                    " stock", " income", " revenue", " fiscal",
                    " s financials", "'s financials", "s financials"]:
        if lower.endswith(suffix):
            lower = lower[:-len(suffix)].strip()
            break

    # Remove possessive
    lower = re.sub(r"'s\b", "", lower).strip()
    lower = re.sub(r"s\b$", "", lower).strip() if lower.endswith("s") and len(lower) > 3 else lower

    # Clean up
    lower = re.sub(r"\s+", " ", lower).strip()
    lower = lower.strip(",.!?;:")

    if not lower:
        return "", ""

    # Direct match against known companies
    if lower in _KNOWN_COMPANIES:
        return _KNOWN_COMPANIES[lower], lower

    # Try partial match (company name is a substring of input)
    # Use word boundaries for short tickers to avoid false matches
    best_match = ""
    best_name = ""
    for key, name in _KNOWN_COMPANIES.items():
        if len(key) <= 2:
            # Short tickers must match as whole words
            if re.search(rf"\b{re.escape(key)}\b", lower):
                if len(key) > len(best_match):
                    best_match = key
                    best_name = name
        else:
            if key in lower and len(key) > len(best_match):
                best_match = key
                best_name = name

    if best_match:
        return best_name, best_match

    # If it looks like a proper name (capitalized, not a common word), treat as company
    # But only if not in known_only mode (used by local classifier to avoid false positives)
    if not known_only:
        words = text.strip().split()
        if words:
            # Check if first word after removing research verbs is likely a company
            cleaned = text.lower()
            for verb in _RESEARCH_VERBS:
                cleaned = re.sub(rf"\b{re.escape(verb)}\b", "", cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            if cleaned:
                # Return the first meaningful word(s)
                company_words = []
                for w in cleaned.split():
                    wl = w.lower().strip(",.!?;:")
                    if wl in ("the", "a", "an", "for", "of", "on", "about", "latest", "fy",
                               "fiscal", "year", "years"):
                        continue
                    if re.match(r"^\d{4}$", wl):
                        break
                    company_words.append(wl)
                if company_words:
                    guessed = " ".join(company_words)
                    if guessed in _KNOWN_COMPANIES:
                        return _KNOWN_COMPANIES[guessed], guessed
                    # Capitalize for display
                    return guessed.title(), guessed

    return "", ""


# ── Deterministic local classifier ───────────────────────────────────────────
def _local_classify(prompt: str) -> Optional[IntentResult]:
    """Try to classify deterministically without an LLM.

    Returns IntentResult if confident, None if ambiguous.
    """
    if not prompt or not prompt.strip():
        return ChatResult(confidence=1.0, model_used="local")

    text = prompt.strip()
    lower = text.lower().strip()
    # Strip trailing punctuation for matching
    lower_clean = lower.rstrip(".!?;:")

    # 1. Exact chat matches (try with and without trailing punctuation)
    if lower_clean in _CHAT_EXACT or lower in _CHAT_EXACT:
        return ChatResult(confidence=0.99, model_used="local")

    # 2. Check for explicit research verbs + company
    has_research_verb = False
    for verb in _RESEARCH_VERBS:
        if re.search(rf"\b{re.escape(verb)}\b", lower):
            has_research_verb = True
            break

    company_name, _ = _extract_company(text, known_only=True)
    has_company = bool(company_name)

    # 3. Check for explicit period mentions
    _, _, period_mode = _extract_years(text)

    # 4. Strong research signals: research verb + company
    if has_research_verb and has_company:
        sy, ey, pm = _extract_years(text)
        return ResearchResult(
            company=company_name,
            period_mode=pm,
            start_year=sy,
            end_year=ey,
            objective=_extract_objective(text),
            confidence=0.95,
            model_used="local",
        )

    # 5. Company + research noun (even without explicit verb)
    has_research_noun = False
    for noun in _RESEARCH_NOUNS:
        if noun in lower:
            has_research_noun = True
            break

    if has_company and has_research_noun:
        sy, ey, pm = _extract_years(text)
        return ResearchResult(
            company=company_name,
            period_mode=pm,
            start_year=sy,
            end_year=ey,
            objective=_extract_objective(text),
            confidence=0.90,
            model_used="local",
        )

    # 6. Just a ticker symbol (1-5 uppercase letters, common tickers)
    if re.match(r"^[A-Z]{1,5}$", text.strip()):
        ticker_lower = text.strip().lower()
        if ticker_lower in _KNOWN_COMPANIES:
            return ResearchResult(
                company=_KNOWN_COMPANIES[ticker_lower],
                period_mode="latest",
                confidence=0.90,
                model_used="local",
            )

    # 7. Pure chat patterns: starts with common chat starters (check with and without punctuation)
    for starter in _CHAT_STARTS:
        if (lower.startswith(starter) or lower_clean.startswith(starter)) and not has_company:
            return ChatResult(confidence=0.85, model_used="local")

    # 8. Very short prompts without research signals are chat
    if len(lower.split()) <= 2 and not has_company:
        return ChatResult(confidence=0.80, model_used="local")

    # 9. Company name alone (no verb, no noun) — could be research
    if has_company and not has_research_verb and period_mode == "latest":
        # "Microsoft" alone — treat as research with medium confidence
        return ResearchResult(
            company=company_name,
            period_mode="latest",
            confidence=0.75,
            model_used="local",
        )

    # Ambiguous — needs LLM
    return None


def _extract_objective(text: str) -> str:
    """Extract a short objective description from the prompt."""
    lower = text.lower().strip()

    # Remove research verbs and company
    for verb in _RESEARCH_VERBS:
        lower = re.sub(rf"\b{re.escape(verb)}\b", "", lower, flags=re.IGNORECASE)

    # Remove company name patterns
    lower = re.sub(r"\s+", " ", lower).strip()
    lower = lower.strip(",.!?;:")

    # Remove year patterns
    lower = _YEAR_RANGE_RE.sub("", lower)
    lower = _SINGLE_YEAR_RE.sub("", lower)
    lower = re.sub(r"\s+", " ", lower).strip()

    if len(lower) > 5:
        return lower[:100]

    return "Financial research"


# ── LLM-based classifier (with timeout) ─────────────────────────────────────
_CLASSIFY_PROMPT = """\
You are an intent classifier.  Given the user's message, classify it into one \
of exactly two intents: "chat" or "research".

Rules:
- "chat" = greetings, small talk, thank you, jokes, generic conversation.
- "research" = any request about a specific company, financial data, \
metrics, analysis, or business intelligence.
- NEVER produce markdown.  NEVER explain your reasoning.
- NEVER answer the user's question — only classify it.

Output ONLY valid JSON with no trailing text.

For "research" intents, extract:
  "company"        — the company name (string)
  "period_mode"    — "specified" if the user mentions specific years, \
                     "latest" if no years are mentioned
  "start_year"     — the start year if mentioned, otherwise null
  "end_year"       — the end year if mentioned, otherwise null
  "objective"      — a short description of what they want to research
  "confidence"     — a float 0–1 indicating your certainty

For "chat" intents:
  "confidence"     — a float 0–1

Examples:

User: Hello
{"intent":"chat","confidence":0.99}

User: Research Microsoft between 2024 and 2025 and calculate important financial metrics.
{"intent":"research","company":"Microsoft","period_mode":"specified","start_year":2024,"end_year":2025,"objective":"financial research","confidence":0.99}

User: Tell me about Apple's revenue last year
{"intent":"research","company":"Apple","period_mode":"latest","start_year":null,"end_year":null,"objective":"revenue analysis","confidence":0.95}

User: Analyze NVIDIA
{"intent":"research","company":"NVIDIA","period_mode":"latest","start_year":null,"end_year":null,"objective":"financial analysis","confidence":0.95}

User: What's the weather like?
{"intent":"chat","confidence":0.95}
"""


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json … ``` wrappers the LLM might emit."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] which invalid JSON."""
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def _extract_json(text: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from LLM output."""
    text = _strip_markdown_fences(text)
    text = _strip_trailing_commas(text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if match:
        candidate = _strip_trailing_commas(match.group(0))
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM output: {text!r}")


def _llm_classify(prompt: str, timeout: float = 8.0) -> Optional[IntentResult]:
    """Classify using LLM with a strict timeout.

    Returns IntentResult on success, None on timeout/error/malformed output.
    """
    try:
        from lib.provider_manager import generate_text
    except ImportError:
        return None

    result_holder: list[Optional[IntentResult]] = [None]
    error_holder: list[Optional[Exception]] = [None]

    def _do_llm():
        try:
            full_prompt = f"{_CLASSIFY_PROMPT}\n\nUser: {prompt.strip()}"
            raw = generate_text(full_prompt)
            parsed = _extract_json(raw)
            result_holder[0] = _build_llm_result(parsed)
        except Exception as exc:
            error_holder[0] = exc

    thread = threading.Thread(target=_do_llm, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        # Timeout — LLM too slow
        return None

    if error_holder[0] is not None:
        return None

    return result_holder[0]


def _build_llm_result(parsed: dict[str, Any]) -> IntentResult:
    """Build a typed result from a parsed JSON dict from the LLM."""
    intent = parsed.get("intent", "chat")

    if intent == "research":
        company = parsed.get("company", "")
        if not isinstance(company, str) or not company.strip():
            return ChatResult(confidence=0.5, model_used="nemotron")
        company = company.strip()

        period_mode = parsed.get("period_mode", "latest")
        if period_mode not in ("specified", "latest"):
            period_mode = "latest"

        start_year = parsed.get("start_year")
        end_year = parsed.get("end_year")
        if start_year is not None:
            start_year = int(start_year)
        if end_year is not None:
            end_year = int(end_year)

        objective = str(parsed.get("objective", "")).strip()
        confidence = float(parsed.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        return ResearchResult(
            company=company,
            period_mode=period_mode,
            start_year=start_year,
            end_year=end_year,
            objective=objective,
            confidence=confidence,
            model_used="nemotron",
        )

    confidence = float(parsed.get("confidence", 1.0))
    confidence = max(0.0, min(1.0, confidence))
    return ChatResult(confidence=confidence, model_used="nemotron")


# ── Main classification function ─────────────────────────────────────────────
def classify_intent(user_prompt: str) -> IntentResult:
    """Classify a user prompt using local rules first, LLM fallback.

    Returns a ``ChatResult`` or ``ResearchResult`` with validated fields.
    Never blocks for more than ~8 seconds.
    """
    if not user_prompt or not user_prompt.strip():
        return ChatResult(confidence=1.0, model_used="local")

    # Step 1: Try deterministic local classification
    local_result = _local_classify(user_prompt)
    if local_result is not None:
        return local_result

    # Step 2: Ambiguous — try LLM with timeout
    llm_result = _llm_classify(user_prompt, timeout=8.0)
    if llm_result is not None:
        return llm_result

    # Step 3: LLM failed/timed out — fall back to local best-effort
    # If we can at least extract a company name, treat as research
    company_name, _ = _extract_company(user_prompt)
    if company_name:
        sy, ey, pm = _extract_years(user_prompt)
        return ResearchResult(
            company=company_name,
            period_mode=pm,
            start_year=sy,
            end_year=ey,
            objective=_extract_objective(user_prompt),
            confidence=0.60,
            model_used="local_fallback",
        )

    # Truly ambiguous and no company found — default to chat
    return ChatResult(confidence=0.50, model_used="local_fallback")
