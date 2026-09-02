"""Server-side sanitizer that strips internal model reasoning from LLM output.

This is a DEFENSIVE layer — the primary fixes are:
  1. System prompt instructing model not to output reasoning
  2. Provider field filtering (never return reasoning_content)
  3. Provider-specific parameters to minimize reasoning output

This module handles residual leakage from models like Nemotron that embed
chain-of-thought reasoning inside the content field:
  - Numbered reasoning steps (Nemotron-style)
  - <think>...</think> and similar blocks
  - Leaked internal prefixes/suffixes
  - Common reasoning scratchpad patterns
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger("finora.sanitizer")

# ── Think/reasoning tag patterns ─────────────────────────────────────────────

_THINK_TAG_RE = re.compile(
    r"<think(?:ing)?>(?:(?!</think(?:ing)?>).)*(?:</think(?:ing)?>)?",
    re.IGNORECASE | re.DOTALL,
)

_REASONING_TAG_RE = re.compile(
    r"<reason(?:ing)?(?:_content)?>(?:(?!</reason(?:ing)?(?:_content)?>).)*"
    r"(?:</reason(?:ing)?(?:_content)?>)?",
    re.IGNORECASE | re.DOTALL,
)

_ANALYSIS_TAG_RE = re.compile(
    r"<analysis>(?:(?!</analysis>).)*(?:</analysis>)?",
    re.IGNORECASE | re.DOTALL,
)

_THINK_FENCE_RE = re.compile(
    r"```(?:think(?:ing)?|reason(?:ing)?)[\s\S]*?(?:```|$)",
    re.IGNORECASE,
)

# ── Numbered step reasoning (Nemotron-style) ─────────────────────────────────
# Nemotron produces responses like:
#   1. **Analyze User Input:** The user said...
#   2. **Check Provided Research Data:** ...
#   3. **Draft Response:** ...
#   4. **Output:** The final answer here.

_NUMBERED_STEP_RE = re.compile(
    r"^\s*\d+\.\s+\*\*[^*]+:\*\*",
    re.MULTILINE,
)

# Match the "output/response/answer/final" section that contains the real answer
_OUTPUT_SECTION_RE = re.compile(
    r"\d+\.\s+\*\*(?:Output|Response|Answer|Final|Drafted?\s*Response|Visible\s*Response|Final\s*Answer)[^*]*\*\*\s*[:\s]*",
    re.IGNORECASE,
)

# ── Leaked prefix/suffix patterns ────────────────────────────────────────────
_LEAKED_PREFIXES: list[str] = [
    "here's a thinking process",
    "here is my thinking process",
    "thinking process:",
    "analyze user input:",
    "analysis:",
    "system prompt:",
    "the system prompt says",
    "the prompt says",
    "i need to",
    "i should",
    "i should probably",
    "let me draft",
    "let me analyze",
    "let me think",
    "let me consider",
    "my reasoning:",
    "my analysis:",
    "internal analysis:",
    "internal reasoning:",
    "scratchpad:",
    "draft:",
    "plan:",
    "step-by-step:",
    "chain of thought:",
    "chain-of-thought:",
    "reasoning:",
    "thinking:",
    "meta-commentary:",
    "how i'll answer:",
    "how i will answer:",
    "the user wants me to",
    "the user is asking",
    "i'll respond with",
    "i will respond with",
    "i should respond",
    "first, i'll",
    "first i'll",
    "my approach:",
    "approach:",
    "need to be concise",
    "user asks:",
    "user question:",
    "user wants",
    "given the context",
    "based on the research data",
    "let's craft",
    "let me re-read",
    "let me re-read the",
    "wait...",
    "wait,",
    "check provided research data:",
]

_LEAKED_PREFIX_RE = re.compile(
    r"^(?:" + "|".join(re.escape(p) for p in _LEAKED_PREFIXES) + r")[^\n]*\n?",
    re.IGNORECASE,
)


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> and similar reasoning blocks."""
    text = _THINK_TAG_RE.sub("", text)
    text = _REASONING_TAG_RE.sub("", text)
    text = _ANALYSIS_TAG_RE.sub("", text)
    text = _THINK_FENCE_RE.sub("", text)
    # Also strip standalone closing tags
    text = re.sub(r"</think(?:ing)?>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</reason(?:ing)?(?:_content)?>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</analysis>", "", text, flags=re.IGNORECASE)
    return text


def _strip_leaked_prefixes(text: str) -> str:
    """Remove lines that start with known internal-reasoning prefixes."""
    text = text.lstrip()
    for _ in range(10):
        new_text = _LEAKED_PREFIX_RE.sub("", text, count=1)
        if new_text == text:
            break
        text = new_text
    return text


def _strip_numbered_reasoning(text: str) -> str:
    """Strip numbered-step chain-of-thought that models like Nemotron leak.

    Strategy:
    1. Count how many numbered steps exist (1. **Step:** ...)
    2. If ≥3 steps, treat the response as primarily reasoning
    3. Extract the section after "Output/Response/Answer" header
    4. If no output section, extract everything after the last numbered step
    5. If nothing clean found, return original (sanitized by other passes)
    """
    matches = list(_NUMBERED_STEP_RE.finditer(text))
    if len(matches) < 3:
        return text  # Not enough numbered steps to be reasoning leakage

    # Check fraction of lines that are numbered reasoning steps
    lines = text.split("\n")
    reasoning_lines = sum(1 for line in lines if _NUMBERED_STEP_RE.match(line))
    total_lines = max(len([l for l in lines if l.strip()]), 1)
    reasoning_ratio = reasoning_lines / total_lines

    # If not predominantly reasoning, don't strip
    if reasoning_ratio < 0.3:
        return text

    # Try to find the output/response section
    output_match = _OUTPUT_SECTION_RE.search(text)
    if output_match:
        after_header = text[output_match.end():]
        # Strip leading colon, dash, etc.
        after_header = re.sub(r"^\s*[:\u2014\u2013\-]*\s*", "", after_header)
        # Find end of this section (next numbered step or end of text)
        next_step = _NUMBERED_STEP_RE.search(after_header)
        if next_step:
            answer = after_header[:next_step.start()].strip()
        else:
            answer = after_header.strip()
        if answer and len(answer) > 10:
            logger.info(f"Sanitizer: extracted {len(answer)} chars from output section")
            return answer

    # No output section — try to find content after all reasoning steps
    # Look for the last numbered step and take everything after it
    last_match = matches[-1]
    after_last = text[last_match.end():]
    # Strip the step content that might be on the same line
    # (e.g., "4. **Output:** some text")
    step_end = re.search(r"\n", after_last)
    if step_end:
        answer = after_last[step_end.end():].strip()
    else:
        answer = after_last.strip()

    if answer and len(answer) > 10:
        logger.info(f"Sanitizer: extracted {len(answer)} chars after last reasoning step")
        return answer

    # Last resort: try to find any non-reasoning content
    # Remove all numbered step lines and see what's left
    cleaned_lines = []
    for line in lines:
        if not _NUMBERED_STEP_RE.match(line):
            cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    if cleaned and len(cleaned) > 20:
        logger.info(f"Sanitizer: extracted {len(cleaned)} chars by removing numbered lines")
        return cleaned

    return text


def _detect_reasoning_heavy(text: str) -> bool:
    """Detect if the entire response is primarily internal reasoning."""
    indicators = [
        "thinking process",
        "internal analysis",
        "internal reasoning",
        "chain-of-thought",
        "chain of thought",
        "scratchpad",
        "let me analyze",
        "let me draft",
        "let me think",
        "let me consider",
        "let me reason",
        "here's my thinking",
        "here is my thinking",
        "how i'll answer",
        "how i will answer",
        "my approach:",
        "user asks:",
        "user wants:",
        "user question:",
        "the user wants me to",
        "the user is asking",
        "check provided research data",
        "analyze user input",
    ]
    lower = text.lower()
    hits = sum(1 for ind in indicators if ind in lower)
    return hits >= 3


def _clean_whitespace(text: str) -> str:
    """Collapse excessive blank lines and strip."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def sanitize_response(raw: str) -> str:
    """Sanitize LLM output to remove internal reasoning before user display.

    This is a DEFENSIVE backup layer. The primary fixes are:
    1. System prompt instructing model not to output reasoning
    2. Provider field filtering (never return reasoning_content)
    3. Provider-specific parameters to minimize reasoning output

    Args:
        raw: The raw text from the LLM provider.

    Returns:
        Cleaned text safe for user display.
    """
    if not raw or not raw.strip():
        return ""

    text = raw

    # Step 1: Strip think/reasoning tags
    text = _strip_think_tags(text)

    # Step 2: Strip leaked prefix lines
    text = _strip_leaked_prefixes(text)

    # Step 3: Strip numbered-step chain-of-thought leakage (Nemotron-style)
    text = _strip_numbered_reasoning(text)

    # Step 4: Clean up whitespace
    text = _clean_whitespace(text)

    # Step 5: Final sanity check — if what's left still looks like reasoning
    if _detect_reasoning_heavy(text):
        logger.warning(
            f"Sanitizer: response still contains reasoning indicators after all passes "
            f"(first 200 chars: {text[:200]!r})"
        )
        # Last resort: try one more aggressive pass
        text = _strip_leaked_prefixes(text)
        text = _clean_whitespace(text)

    if not text:
        return ""

    return text
