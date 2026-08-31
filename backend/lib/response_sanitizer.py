"""Server-side sanitizer that strips internal model reasoning from LLM output.

This is a DEFENSIVE layer — the primary fix is the system prompt and
provider field filtering.  This module handles residual leakage:
  - <think>...</think> blocks (and unclosed variants)
  - <think>...</think> blocks (OpenAI-style)
  - Common leaked internal prefixes/patterns
  - Leading/trailing reasoning artifacts
"""

from __future__ import annotations

import re

# ── Think/reasoning tag patterns ─────────────────────────────────────────────
# These regexes match <think>...</think> and <think>...</think> blocks,
# including unclosed variants (model ran out of tokens mid-thought).

_THINK_TAG_RE = re.compile(
    r"<think(?:ing)?>(?:(?!</think(?:ing)?>).)*(?:</think(?:ing)?>)?",
    re.IGNORECASE | re.DOTALL,
)

_REASONING_TAG_RE = re.compile(
    r"<reason(?:ing)?(?:_content)?>(?:(?!</reason(?:ing)?(?:_content)?>).)*"
    r"(?:</reason(?:ing)?(?:_content)?>)?",
    re.IGNORECASE | re.DOTALL,
)

# Also handle ```thinking ... ``` fenced blocks some models use
_THINK_FENCE_RE = re.compile(
    r"```(?:think(?:ing)?|reason(?:ing)?)[\s\S]*?(?:```|$)",
    re.IGNORECASE,
)

# ── Leaked prefix/suffix patterns ────────────────────────────────────────────
# Lines that start with these are almost certainly internal reasoning.
_LEAKED_PREFIXES: list[str] = [
    "here's a thinking process",
    "here is my thinking process",
    "thinking process:",
    "analyze user input:",
    "an:",
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
]

# Regex that matches any of the leaked prefixes at the start of the text
_LEAKED_PREFIX_RE = re.compile(
    r"^(?:" + "|".join(re.escape(p) for p in _LEAKED_PREFIXES) + r")[^\n]*\n?",
    re.IGNORECASE,
)

# ── Full-response leak detection ─────────────────────────────────────────────
# If the entire response looks like it's just internal reasoning with no
# real answer, we may want to return a fallback.

_REASONING_HEAVY_RE = re.compile(
    r"(?:thinking process|internal (?:analysis|reasoning)|chain[ -]of[ -]thought|"
    r"let me (?:analyze|draft|think|consider|reason)|"
    r"here(?:'s| is) my (?:thinking|reasoning|analysis))",
    re.IGNORECASE,
)


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> and similar reasoning blocks."""
    text = _THINK_TAG_RE.sub("", text)
    text = _REASONING_TAG_RE.sub("", text)
    text = _THINK_FENCE_RE.sub("", text)
    # Also strip standalone closing tags (model emitted close without open)
    text = re.sub(r"</think(?:ing)?>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</reason(?:ing)?(?:_content)?>", "", text, flags=re.IGNORECASE)
    return text


def _strip_leaked_prefixes(text: str) -> str:
    """Remove lines that start with known internal-reasoning prefixes."""
    # Strip leading whitespace so ^ anchor can match
    text = text.lstrip()
    # Apply repeatedly in case multiple leaked lines are stacked
    for _ in range(5):
        new_text = _LEAKED_PREFIX_RE.sub("", text, count=1)
        if new_text == text:
            break
        text = new_text
    return text


def _clean_whitespace(text: str) -> str:
    """Collapse excessive blank lines and strip."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def sanitize_response(raw: str) -> str:
    """Sanitize LLM output to remove internal reasoning before user display.

    This is a DEFENSIVE backup layer.  The primary fixes are:
    1. System prompt instructing model not to output reasoning
    2. Provider field filtering (never return reasoning_content)

    Args:
        raw: The raw text from the LLM provider.

    Returns:
        Cleaned text safe for user display.  Never empty — returns a
        fallback message if everything was stripped.
    """
    if not raw or not raw.strip():
        return ""

    text = raw

    # Step 1: Strip think/reasoning tags
    text = _strip_think_tags(text)

    # Step 2: Strip leaked prefix lines
    text = _strip_leaked_prefixes(text)

    # Step 3: Clean up whitespace (also ensures ^ anchor works for prefixes)
    text = _clean_whitespace(text)

    # Step 4: Sanity check — if nothing useful is left, return empty
    # (the caller can decide what to do with an empty string)
    if not text:
        return ""

    return text
