"""Chat usage limit service.

Enforces 15 user messages per user per rolling 24-hour period.
Stores message timestamps with JSON-file persistence.
"""

from __future__ import annotations

import time
from typing import Any

from lib.persistence import save_chat_usage, load_chat_usage

CHAT_LIMIT = 15
ROLLING_WINDOW_SECONDS = 24 * 3600  # 24 hours

# user_id → list of message timestamps (synced to disk)
_message_log: dict[str, list[float]] = {}
_loaded = False


def _ensure_loaded() -> None:
    """Load persisted chat data into memory on first access."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    _message_log.update(load_chat_usage())


def _persist() -> None:
    """Save chat usage to disk."""
    save_chat_usage(dict(_message_log))


def _prune_old(user_id: str) -> None:
    """Remove messages older than the rolling window."""
    cutoff = time.time() - ROLLING_WINDOW_SECONDS
    if user_id in _message_log:
        _message_log[user_id] = [
            ts for ts in _message_log[user_id] if ts > cutoff
        ]


def can_send_message(user_id: str) -> bool:
    """Check if the user has remaining messages in the rolling window."""
    _ensure_loaded()
    _prune_old(user_id)
    return len(_message_log.get(user_id, [])) < CHAT_LIMIT


def record_message(user_id: str) -> dict[str, Any]:
    """Record a user message and return the updated usage info.

    Returns dict with:
        - allowed: bool
        - used: int
        - limit: int
        - remaining: int
        - reset_in_seconds: int (approximate time until oldest message expires)
    """
    _ensure_loaded()
    _prune_old(user_id)
    messages = _message_log.get(user_id, [])
    used = len(messages)
    remaining = max(0, CHAT_LIMIT - used)

    if used >= CHAT_LIMIT:
        reset_in = int(messages[0] + ROLLING_WINDOW_SECONDS - time.time())
        return {
            "allowed": False,
            "used": used,
            "limit": CHAT_LIMIT,
            "remaining": 0,
            "reset_in_seconds": max(0, reset_in),
        }

    # Record this message
    if user_id not in _message_log:
        _message_log[user_id] = []
    _message_log[user_id].append(time.time())

    used = len(_message_log[user_id])
    remaining = max(0, CHAT_LIMIT - used)
    reset_in = 0
    if _message_log[user_id]:
        reset_in = int(_message_log[user_id][0] + ROLLING_WINDOW_SECONDS - time.time())

    # Persist to disk
    _persist()

    return {
        "allowed": True,
        "used": used,
        "limit": CHAT_LIMIT,
        "remaining": remaining,
        "reset_in_seconds": max(0, reset_in),
    }


def get_usage(user_id: str) -> dict[str, Any]:
    """Get current usage without recording a message."""
    _ensure_loaded()
    _prune_old(user_id)
    messages = _message_log.get(user_id, [])
    used = len(messages)
    remaining = max(0, CHAT_LIMIT - used)
    reset_in = 0
    if messages:
        reset_in = int(messages[0] + ROLLING_WINDOW_SECONDS - time.time())
    return {
        "used": used,
        "limit": CHAT_LIMIT,
        "remaining": remaining,
        "reset_in_seconds": max(0, reset_in),
    }


def clear_all() -> None:
    """Drop all message logs — useful for tests."""
    global _loaded
    _message_log.clear()
    _loaded = False
    from lib.persistence import clear_all_persistence
    clear_all_persistence()
