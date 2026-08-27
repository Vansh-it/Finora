"""Simple JSON-file persistence for production durability.

Stores users, auth sessions, research sessions, and chat usage to disk.
Designed for the zero-cost MVP — no database dependency.

All writes are atomic (write to temp file then rename).
Reads are bounded and validated.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_LOCK = threading.Lock()

# File paths
_USERS_FILE = _DATA_DIR / "users.json"
_SESSIONS_FILE = _DATA_DIR / "auth_sessions.json"
_RESEARCH_FILE = _DATA_DIR / "research_sessions.json"
_CHAT_FILE = _DATA_DIR / "chat_usage.json"

# Maximum sizes to prevent unbounded growth
MAX_RESEARCH_SESSIONS = 10000
MAX_CHAT_ENTRIES = 50000


def _ensure_data_dir() -> None:
    """Create data directory if it doesn't exist."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write(path: Path, data: dict) -> None:
    """Write data to a file atomically using temp file + rename."""
    _ensure_data_dir()
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(_DATA_DIR), suffix=".tmp", prefix=path.stem
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        shutil.move(tmp_path, str(path))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _read_json(path: Path) -> dict:
    """Read a JSON file, returning empty dict on missing/corrupt."""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except (json.JSONDecodeError, OSError):
        return {}


# ── Users ─────────────────────────────────────────────────────────────────────

def save_users(users: dict[str, Any]) -> None:
    """Save all users to disk."""
    with _LOCK:
        _atomic_write(_USERS_FILE, users)


def load_users() -> dict[str, Any]:
    """Load all users from disk."""
    return _read_json(_USERS_FILE)


def save_user(user: Any) -> None:
    """Save a single user to disk (merges with existing)."""
    with _LOCK:
        users = _read_json(_USERS_FILE)
        user_id = getattr(user, "user_id", None) or user.get("user_id", "")
        if user_id:
            if hasattr(user, "to_dict"):
                users[user_id] = user.to_dict()
            else:
                users[user_id] = user
        _atomic_write(_USERS_FILE, users)


def save_email_index(index: dict[str, str]) -> None:
    """Save the email→user_id index."""
    with _LOCK:
        _atomic_write(_DATA_DIR / "email_index.json", index)


def load_email_index() -> dict[str, str]:
    """Load the email→user_id index."""
    data = _read_json(_DATA_DIR / "email_index.json")
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}


# ── Auth Sessions ─────────────────────────────────────────────────────────────

def save_auth_sessions(sessions: dict[str, Any]) -> None:
    """Save all auth sessions to disk."""
    with _LOCK:
        _atomic_write(_SESSIONS_FILE, sessions)


def load_auth_sessions() -> dict[str, Any]:
    """Load all auth sessions from disk."""
    return _read_json(_SESSIONS_FILE)


# ── Research Sessions ────────────────────────────────────────────────────────

def save_research_sessions(sessions: dict[str, Any]) -> None:
    """Save all research sessions to disk."""
    with _LOCK:
        # Prune if too large (keep most recent)
        if len(sessions) > MAX_RESEARCH_SESSIONS:
            sorted_items = sorted(
                sessions.items(),
                key=lambda x: x[1].get("created_at", "") if isinstance(x[1], dict) else "",
                reverse=True,
            )
            sessions = dict(sorted_items[:MAX_RESEARCH_SESSIONS])
        _atomic_write(_RESEARCH_FILE, sessions)


def load_research_sessions() -> dict[str, Any]:
    """Load all research sessions from disk."""
    return _read_json(_RESEARCH_FILE)


# ── Chat Usage ───────────────────────────────────────────────────────────────

def save_chat_usage(usage: dict[str, Any]) -> None:
    """Save chat usage to disk."""
    with _LOCK:
        # Prune old entries
        cutoff = time.time() - 86400  # 24 hours
        pruned = {}
        for uid, timestamps in usage.items():
            if isinstance(timestamps, list):
                recent = [ts for ts in timestamps if ts > cutoff]
                if recent:
                    pruned[uid] = recent
        if len(pruned) > MAX_CHAT_ENTRIES:
            # Keep only users with most messages
            sorted_users = sorted(pruned.items(), key=lambda x: len(x[1]), reverse=True)
            pruned = dict(sorted_users[:MAX_CHAT_ENTRIES])
        _atomic_write(_CHAT_FILE, pruned)


def load_chat_usage() -> dict[str, Any]:
    """Load chat usage from disk."""
    data = _read_json(_CHAT_FILE)
    # Validate structure: user_id → list of floats
    result = {}
    cutoff = time.time() - 86400
    for uid, timestamps in data.items():
        if isinstance(timestamps, list):
            valid = [ts for ts in timestamps if isinstance(ts, (int, float)) and ts > cutoff]
            if valid:
                result[uid] = valid
    return result


# ── Cleanup ───────────────────────────────────────────────────────────────────

def clear_all_persistence() -> None:
    """Remove all persisted data files."""
    with _LOCK:
        for f in [_USERS_FILE, _SESSIONS_FILE, _RESEARCH_FILE, _CHAT_FILE,
                   _DATA_DIR / "email_index.json"]:
            if f.exists():
                f.unlink()


def get_data_dir() -> str:
    """Return the data directory path."""
    _ensure_data_dir()
    return str(_DATA_DIR)
