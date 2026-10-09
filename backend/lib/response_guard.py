"""Final-response validation + controlled compression for Finora chat.

HARD RULE: every user-visible assistant response must be <= MAX_RESPONSE_WORDS
(default 300) words. The limit applies to the final answer only — research
context may be far larger internally.

Compression is NOT truncation:
- blocks are prioritised (direct answer -> evidence-bearing blocks -> rest),
- filler (greetings, generic disclaimers, repetition) is dropped first,
- the Sources section is preserved (trimmed from the end if needed),
- remaining over-long blocks are cut at sentence boundaries,
- markdown is repaired so no response ends mid-structure.
"""

from __future__ import annotations

import re
from typing import Optional

from lib.research_agent import count_words  # deterministic server-side counter

MAX_RESPONSE_WORDS = 300

# Blocks matching these are dropped first when compressing.
_FILLER_PATTERNS = (
    r"^\s*(certainly|sure|of course|great question|hope (?:this|that) helps)\b",
    r"^\s*(based on (?:the|the provided|the information)|as an ai|i hope)\b",
    r"^\s*(finora is a research tool, not investment advice)",
    r"^\s*(note that this|disclaimer|always do your own research)",
    r"^\s*(in summary,?)\s*$",
    r"^\s*as requested\b",
)


def _is_filler(text: str) -> bool:
    t = text.strip()
    return any(re.search(p, t, re.IGNORECASE) for p in _FILLER_PATTERNS)


def _split_blocks(text: str) -> list[str]:
    """Split markdown into atomic blocks: headings, table rows, list items, paragraphs."""
    lines = text.split("\n")
    blocks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            block = "\n".join(current).strip()
            if block:
                blocks.append(block)
            current.clear()

    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            current.append(line)
            if in_fence:
                flush()
            in_fence = not in_fence
            continue
        if in_fence:
            current.append(line)
            continue
        if not stripped:
            flush()
            continue
        if stripped.startswith("#"):
            flush()
            blocks.append(stripped)
            continue
        if stripped.startswith("|"):
            flush()
            blocks.append(stripped)
            continue
        if re.match(r"^([-*+]|\d+\.)\s+", stripped):
            flush()
            blocks.append(stripped)
            continue
        current.append(line)
    flush()
    return blocks


def _block_words(block: str) -> int:
    # Table rows: count only the cell contents, not pipes.
    if block.lstrip().startswith("|"):
        return count_words(re.sub(r"[|#*-]", " ", block))
    return count_words(block)


def _score_block(block: str, first: bool) -> float:
    """Higher = keep first when compressing."""
    if first:
        return 100.0
    if block.lstrip().startswith("#"):
        return 60.0
    if _is_filler(block):
        return -100.0
    score = 10.0
    # Evidence-bearing blocks (financial figures, citations) matter most.
    if re.search(r"\$|\d+%|\b\d+(?:\.\d+)?[BM]\b|\[\^?\d+\]|\[S\d+\]", block):
        score += 25.0
    if re.search(r"\b(risk|driver|cause|decline|growth|margin|revenue|outlook)\b",
                 block, re.IGNORECASE):
        score += 8.0
    if len(block.split()) > 60:
        score -= 5.0  # wall-of-text blocks are less dense
    return score


def _truncate_at_sentence(text: str, max_words: int) -> str:
    """Cut at a sentence boundary so the text still ends naturally."""
    words = text.split()
    if len(words) <= max_words:
        return text
    clipped = " ".join(words[:max_words])
    # Prefer the last complete sentence inside the clip.
    m = None
    for m in re.finditer(r"[.!?][\"'\)\]]?(?=\s|$)", clipped):
        pass
    if m:
        clipped = clipped[: m.end()]
    else:
        # No sentence end — cut at last comma/semicolon if reasonably late.
        alt = max(clipped.rfind(", "), clipped.rfind("; "))
        if alt > max_words * 0.5:
            clipped = clipped[: alt + 1]
        else:
            clipped = clipped.rstrip(",;: ")
    return clipped.strip()


def _repair_markdown(text: str) -> str:
    """Never leave unfinished markdown structures."""
    text = text.strip()
    # Unfinished citation/label at the very end.
    text = re.sub(r"\[[^\]]*$", "", text)
    # Dangling partial inline tokens (backticks excluded — fences below).
    text = re.sub(r"\s*[\[*_#>|\\]+$", "", text)
    text = re.sub(r"(?<!\S)[-]+\s*$", "", text)
    # Trailing heading marker with no content.
    text = re.sub(r"\n#+\s*$", "", text)
    # Dangling partial table row.
    lines = text.split("\n")
    if lines and lines[-1].strip().startswith("|") and lines[-1].count("|") < 2:
        lines.pop()
        text = "\n".join(lines)
    # Balance code fences and bold AFTER stripping so repairs survive.
    if text.count("```") % 2 == 1:
        text = text + "\n```"
    if text.count("**") % 2 == 1:
        text = text[:-2].rstrip() if text.endswith("**") else text + "**"
    return text.strip()


def compress_to_limit(text: str, max_words: int = MAX_RESPONSE_WORDS) -> str:
    """Controlled compression: prioritise blocks, drop filler, then trim."""
    if count_words(text) <= max_words:
        return text

    blocks = _split_blocks(text)
    if not blocks:
        return text

    # Locate the Sources section (heading + following blocks).
    sources_start: Optional[int] = None
    for i, b in enumerate(blocks):
        if re.match(r"^#+\s*sources?\b", b.strip(), re.IGNORECASE) or \
           b.strip().lower() in ("sources", "source:"):
            sources_start = i
            break

    body = blocks if sources_start is None else blocks[:sources_start]
    sources = [] if sources_start is None else blocks[sources_start:]

    # Select body blocks by priority, reassembling in original order.
    first_content = next(
        (i for i in range(len(body)) if not body[i].lstrip().startswith("#")),
        0,
    )
    order = sorted(
        range(len(body)),
        key=lambda i: -_score_block(body[i], first=(i == first_content)),
    )
    selected: set[int] = set()
    # Reserve room for the sources section (trimmed to fit later).
    reserved = min(sum(_block_words(b) for b in sources), max_words // 3)
    budget = max_words - reserved
    answer_slot = False

    for idx in order:
        w = _block_words(body[idx])
        if _score_block(body[idx], first=(idx == first_content)) <= -50:
            continue  # filler: never selected
        if idx == first_content:
            # The direct answer must always survive — trim it if too big.
            if w > budget:
                body[idx] = _truncate_at_sentence(body[idx], max(20, budget - 5))
            selected.add(idx)
            answer_slot = True
            continue
        if used_total(selected, body) + w <= budget:
            selected.add(idx)

    # Drop headings whose content did not survive, and ensure the answer
    # block (or its heading) is never dropped along with them.
    to_remove: set[int] = set()
    for idx in sorted(selected):
        if body[idx].lstrip().startswith("#"):
            has_content = any(
                j in selected and not body[j].lstrip().startswith("#")
                for j in range(idx + 1, len(body))
                if j < len(body) and _is_heading_before_next(body, idx, j)
            )
            if not has_content:
                to_remove.add(idx)
    if answer_slot and first_content in selected:
        to_remove -= {i for i in to_remove if i <= first_content}
    selected -= to_remove

    kept = [body[i] for i in sorted(selected)]

    def _join(blocks: list[str]) -> str:
        """Consecutive list items / table rows stay in one markdown block."""
        out = ""
        for b in blocks:
            if not out:
                out = b
                continue
            prev_item = re.match(r"^([-*+]|\d+\.)\s+", out.split("\n")[-1].strip()) or out.split("\n")[-1].strip().startswith("|")
            cur_item = re.match(r"^([-*+]|\d+\.)\s+", b.strip()) or b.strip().startswith("|")
            out += ("\n" if (prev_item and cur_item) else "\n\n") + b
        return out

    # Sources: keep heading + as many entries as fit.
    if sources:
        out_words = sum(_block_words(b) for b in kept)
        remaining = max_words - out_words
        src_kept: list[str] = []
        for b in sources:
            w = _block_words(b)
            if w <= remaining:
                src_kept.append(b)
                remaining -= w
            elif not src_kept:
                src_kept.append(_truncate_at_sentence(b, max(10, remaining)))
                remaining = 0
                break
            else:
                break
        if src_kept:
            # If only entries survived without the heading, re-add heading.
            if not re.match(r"^#+\s*sources?\b", src_kept[0].strip(), re.IGNORECASE):
                if sources[0].strip().lower() in ("sources", "source:") or \
                   re.match(r"^#+\s*sources?\b", sources[0].strip(), re.IGNORECASE):
                    src_kept = [sources[0]] + src_kept
            kept.extend(src_kept)

    result = _join(kept)

    # Final safety: if still over (pathological layouts), cut at block level
    # from the least important end — never mid-citation if avoidable.
    if count_words(result) > max_words:
        lines = result.split("\n\n")
        while lines and count_words("\n\n".join(lines)) > max_words and len(lines) > 1:
            # drop the lowest-value line-group that is not the first or Sources
            drop_idx = None
            for i in range(len(lines) - 1, 0, -1):
                if re.match(r"^#+\s*sources?\b", lines[i].strip(), re.IGNORECASE):
                    continue
                drop_idx = i
                break
            if drop_idx is None:
                break
            lines.pop(drop_idx)
        result = "\n\n".join(lines)
    if count_words(result) > max_words:
        head = _truncate_at_sentence(result, max_words)
        # Preserve a trailing Sources block if it existed and fits.
        if sources and re.match(r"^#+\s*sources?\b", sources[0].strip(), re.IGNORECASE):
            src_text = "\n\n".join(sources)
            avail = max_words - count_words(head)
            if avail > 5:
                head = head + "\n\n" + _truncate_at_sentence(src_text, avail)
        result = head

    return _repair_markdown(result)


def used_total(selected: set[int], body: list[str]) -> int:
    return sum(_block_words(body[i]) for i in selected)


def _is_heading_before_next(body: list[str], heading_idx: int, candidate: int) -> bool:
    """True when candidate is in the same section as body[heading_idx]."""
    if candidate <= heading_idx:
        return False
    for j in range(heading_idx + 1, candidate + 1):
        if body[j].lstrip().startswith("#") and j != heading_idx:
            return False
    return True


_LEAK_PATTERNS = (
    (re.compile(r"nvapi-|sk-[A-Za-z0-9]{10,}|tvly-[A-Za-z0-9]{10,}", re.I), "api_key"),
    (re.compile(r"\btraceback \(most recent call last\)", re.I), "traceback"),
    (re.compile(r"---\s*EXTERNAL RESEARCH|---\s*END EXTERNAL RESEARCH", re.I), "raw_context"),
    (re.compile(r"---\s*RESEARCH DATA\s*---", re.I), "raw_context"),
    (re.compile(r"\brole\s*:\s*(system|assistant)\b"), "raw_prompt"),
)


def validate_response(
    text: str,
    max_words: int = MAX_RESPONSE_WORDS,
) -> dict:
    """Deterministic final-response validation.

    Returns {"ok": bool, "word_count": int, "issues": [str, ...]}.
    """
    issues: list[str] = []
    words = count_words(text or "")
    if words > max_words:
        issues.append(f"over_word_limit:{words}>{max_words}")
    if not text or not text.strip():
        issues.append("empty")
    if text and text.count("```") % 2 == 1:
        issues.append("unbalanced_code_fence")
    if text and text.count("**") % 2 == 1:
        issues.append("unbalanced_bold")
    if text:
        for pattern, name in _LEAK_PATTERNS:
            if pattern.search(text):
                issues.append(f"leak:{name}")
        tail = text.rstrip()
        if tail.endswith(("|", "-", "*", "#")) and not tail.endswith(".*"):
            issues.append("unfinished_markdown")
    return {"ok": not issues, "word_count": words, "issues": issues}


def enforce_response_limit(
    text: str,
    max_words: int = MAX_RESPONSE_WORDS,
) -> dict:
    """Validate and, if needed, compress. Never truncates mid-sentence.

    Returns {"text", "word_count", "compressed", "issues"}.
    """
    words = count_words(text or "")
    compressed = False
    out = text or ""
    if words > max_words:
        out = compress_to_limit(out, max_words)
        compressed = True
    # Repair pass regardless.
    out = _repair_markdown(out)
    final_words = count_words(out)
    if final_words > max_words:
        # Absolute last resort — still sentence-bounded.
        out = _truncate_at_sentence(out, max_words)
        out = _repair_markdown(out)
        final_words = count_words(out)
    result = validate_response(out, max_words)
    return {
        "text": out,
        "word_count": final_words,
        "compressed": compressed,
        "issues": result["issues"],
    }
