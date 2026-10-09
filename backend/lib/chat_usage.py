"""Chat usage quota — server-authoritative daily limits.

Hard limits (both enforced together):
  - DAILY_MESSAGE_LIMIT (25) user messages per user per UTC day
  - DAILY_WORD_LIMIT   (7500) user-input words per user per UTC day

Whichever limit is reached first blocks further chat requests until the
UTC-day rollover. The server is authoritative: browser state, refreshes,
extra tabs, and client-side JS cannot bypass it.

Race safety: check + increment + persist happen under one process-wide lock,
so simultaneous requests cannot both pass a boundary check.

Storage: JSON file via lib.persistence, one record per user:
    {user_id: {"day": "YYYY-MM-DD", "messages": int, "words": int}}
Legacy records (list of timestamps from the old rolling-window scheme) are
migrated on load: timestamps falling on the current UTC day are counted as
messages for that day, everything else is dropped (daily policy).
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from lib.research_agent import count_words  # deterministic server-side counter
from lib.persistence import save_chat_usage, load_chat_usage

DAILY_MESSAGE_LIMIT = 25
DAILY_WORD_LIMIT = 7500
CHAT_LIMIT = DAILY_MESSAGE_LIMIT      # backwards-compatible alias
CHAT_WORD_LIMIT = DAILY_WORD_LIMIT    # backwards-compatible alias

# user_id → {"day": str, "messages": int, "words": int}
_quota: dict[str, dict[str, Any]] = {}
_loaded = False
_lock = threading.Lock()


def _utc_day(ts: float | None = None) -> str:
    dt = datetime.fromtimestamp(ts or time.time(), tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def _reset_at_epoch() -> float:
    """Next UTC midnight as epoch seconds."""
    now = datetime.now(tz=timezone.utc)
    nxt = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    # advance one day
    from datetime import timedelta
    nxt = nxt + timedelta(days=1)
    return nxt.timestamp()


def _migrate_legacy(user_id: str, value: Any) -> dict[str, Any] | None:
    """Convert old rolling-window records into a daily record."""
    today = _utc_day()
    if isinstance(value, list):
        messages = sum(1 for ts in value if _utc_day(float(ts)) == today)
        return {"day": today, "messages": min(messages, DAILY_MESSAGE_LIMIT), "words": 0}
    if isinstance(value, dict) and isinstance(value.get("day"), str):
        try:
            return {
                "day": value["day"],
                "messages": int(value.get("messages", 0)),
                "words": int(value.get("words", 0)),
            }
        except (TypeError, ValueError):
            return None
    return None


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    for user_id, value in (load_chat_usage() or {}).items():
        record = _migrate_legacy(user_id, value)
        if record:
            _quota[user_id] = record


def _today_record(user_id: str) -> dict[str, Any]:
    """Get today's record for a user, resetting automatically on day change."""
    today = _utc_day()
    rec = _quota.get(user_id)
    if rec is not None and not isinstance(rec, dict):
        # Legacy (or externally loaded) value — migrate into a daily record.
        rec = _migrate_legacy(user_id, rec)
        if rec is None:
            _quota.pop(user_id, None)
        else:
            _quota[user_id] = rec
    if rec is None or not isinstance(rec, dict) or rec.get("day") != today:
        rec = {"day": today, "messages": 0, "words": 0}
        _quota[user_id] = rec
    return rec


def _usage_dict(rec: dict[str, Any]) -> dict[str, Any]:
    messages_used = int(rec.get("messages", 0))
    words_used = int(rec.get("words", 0))
    reset_at_ts = _reset_at_epoch()
    reset_in = max(0, int(reset_at_ts - time.time()))
    return {
        # legacy keys (kept for existing callers/tests)
        "used": messages_used,
        "limit": DAILY_MESSAGE_LIMIT,
        "remaining": max(0, DAILY_MESSAGE_LIMIT - messages_used),
        "reset_in_seconds": reset_in,
        # new keys
        "messages_used": messages_used,
        "messages_limit": DAILY_MESSAGE_LIMIT,
        "messages_remaining": max(0, DAILY_MESSAGE_LIMIT - messages_used),
        "words_used": words_used,
        "words_limit": DAILY_WORD_LIMIT,
        "words_remaining": max(0, DAILY_WORD_LIMIT - words_used),
        "reset_at": datetime.fromtimestamp(reset_at_ts, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }


def _reject_reason(rec: dict[str, Any], words: int) -> str:
    if int(rec.get("messages", 0)) >= DAILY_MESSAGE_LIMIT:
        return "message_limit"
    if int(rec.get("words", 0)) + words > DAILY_WORD_LIMIT:
        return "word_limit"
    return ""


def can_send_message(user_id: str, text: str = "") -> bool:
    """True when the user is under BOTH daily limits."""
    with _lock:
        _ensure_loaded()
        rec = _today_record(user_id)
        return _reject_reason(rec, count_words(text)) == ""


def reserve_message(user_id: str, text: str) -> dict[str, Any]:
    """Atomically check and record one user message.

    Returns the usage dict plus:
        allowed: bool
        reason: "" | "message_limit" | "word_limit"
    Rejected messages are NOT recorded.
    """
    words = count_words(text)
    with _lock:
        _ensure_loaded()
        rec = _today_record(user_id)
        reason = _reject_reason(rec, words)
        if reason:
            usage = _usage_dict(rec)
            usage.update({"allowed": False, "reason": reason})
            return usage
        rec["messages"] = int(rec.get("messages", 0)) + 1
        rec["words"] = int(rec.get("words", 0)) + words
        save_chat_usage(dict(_quota))
        usage = _usage_dict(rec)
        usage.update({"allowed": True, "reason": ""})
        return usage


def record_message(user_id: str, text: str = "") -> dict[str, Any]:
    """Backwards-compatible wrapper around reserve_message."""
    return reserve_message(user_id, text)


def get_usage(user_id: str) -> dict[str, Any]:
    """Current usage without recording a message."""
    with _lock:
        _ensure_loaded()
        rec = _today_record(user_id)
        usage = _usage_dict(rec)
        usage.update({"allowed": _reject_reason(rec, 0) == "", "reason": ""})
        return usage


def clear_all() -> None:
    """Drop all usage data — useful for tests."""
    global _loaded
    with _lock:
        _quota.clear()
        _loaded = False
    from lib.persistence import clear_all_persistence
    clear_all_persistence()
