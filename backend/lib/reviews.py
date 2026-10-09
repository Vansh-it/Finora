"""Google Sheets-backed review storage for Finora.

Reads/writes a shared Google Sheet through a service account.
Credentials come from the GOOGLE_SERVICE_ACCOUNT_JSON env var (raw or base64
JSON, for hosting) or from backend/credentials.json (local dev).

Everything degrades gracefully: when credentials or the sheet are missing or
unreachable, reads return an empty configured=False payload and writes return a
friendly error — the site never crashes because of reviews.
"""

from __future__ import annotations

import base64
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Shared sheet: "Automated Finora Review"
SPREADSHEET_ID = "1hxdo-pnbswpBV91qgNFyt--_CzgVAMlIYcs5sEhCW9A"
SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)
HEADERS = ["Timestamp", "Name", "Company", "Rating", "Review"]

NAME_MIN, NAME_MAX = 2, 80
COMPANY_MAX = 80
REVIEW_MIN, REVIEW_MAX = 10, 2000
RATING_MIN, RATING_MAX = 1, 5

_RATE_WINDOW = 3600  # 1 hour
_RATE_MAX = 5        # submissions per window per IP
_CACHE_TTL = 60      # seconds a fresh read is served from memory
_INIT_RETRY = 15     # seconds before retrying after a failed sheet open

_lock = threading.Lock()          # guards cache/rate/init state
_sheet_lock = threading.Lock()    # serializes network writes

_attempts: dict[str, list[float]] = {}
_cache: list[dict[str, Any]] = []
_cache_at = 0.0
_ws: Any = None
_init_error = ""
_init_failed_at = 0.0


class ReviewsNotConfigured(Exception):
    """Raised when credentials or the target sheet are unavailable."""


def _credentials_info() -> dict[str, Any] | None:
    """Load service-account JSON from env var, env file path, or default file."""
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            try:
                return json.loads(base64.b64decode(raw).decode("utf-8"))
            except Exception:
                return None
    default = Path(__file__).resolve().parent.parent / "credentials.json"
    path = os.environ.get("GOOGLE_CREDENTIALS_FILE", "").strip() or str(default)
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None
    return None


def _open_worksheet():
    """Return the cached worksheet, opening the sheet on first use."""
    global _ws
    if _ws is not None:
        return _ws
    info = _credentials_info()
    if not info:
        raise ReviewsNotConfigured("Google service-account credentials not found.")
    try:
        import gspread
    except ImportError as exc:  # pragma: no cover - dependency should exist
        raise ReviewsNotConfigured("gspread is not installed on the server.") from exc
    try:
        client = gspread.service_account_from_dict(info, scopes=list(SCOPES))
        sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip() or SPREADSHEET_ID
        spreadsheet = client.open_by_key(sheet_id)
        tab = os.environ.get("GOOGLE_WORKSHEET", "").strip()
        ws = spreadsheet.worksheet(tab) if tab else spreadsheet.get_worksheet(0)
    except ReviewsNotConfigured:
        raise
    except Exception as exc:
        raise ReviewsNotConfigured(_describe_open_failure(exc)) from exc
    _ws = ws
    return ws


def _describe_open_failure(exc: Exception) -> str:
    text = str(exc).lower()
    if "permission" in text or "403" in text:
        return (
            "The reviews sheet is not shared with the service account "
            "(share it as Editor and try again)."
        )
    if "not found" in text or "404" in text:
        return "The reviews sheet could not be found (check GOOGLE_SHEET_ID)."
    return "The reviews sheet is currently unreachable — please try again later."


def _clean(value: Any) -> str:
    """Coerce to a single-line safe string: strip HTML, control chars, padding."""
    s = "" if value is None else str(value)
    s = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]*>", "", s)
    s = re.sub(r"[\x00-\x1f\x7f]", " ", s)
    return " ".join(s.split())


def validate_review(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Validate a submission. Returns (clean_review, None) or (None, error)."""
    name = _clean(payload.get("name"))
    company = _clean(payload.get("company"))
    review = _clean(payload.get("review"))
    if len(name) < NAME_MIN:
        return None, "Please enter your name (at least 2 characters)."
    if len(name) > NAME_MAX:
        return None, f"Name is too long (max {NAME_MAX} characters)."
    if len(company) > COMPANY_MAX:
        return None, f"Company is too long (max {COMPANY_MAX} characters)."
    try:
        rating = int(float(payload.get("rating")))
    except (TypeError, ValueError):
        return None, "Please choose a star rating from 1 to 5."
    if not RATING_MIN <= rating <= RATING_MAX:
        return None, "Rating must be between 1 and 5."
    if len(review) < REVIEW_MIN:
        return None, f"Please write at least {REVIEW_MIN} characters."
    if len(review) > REVIEW_MAX:
        return None, f"Review is too long (max {REVIEW_MAX} characters)."
    return {"name": name, "company": company, "rating": rating, "review": review}, None


def check_review_rate_limit(client_ip: str) -> tuple[bool, int]:
    """Per-IP submission limiter. Returns (allowed, seconds_until_retry)."""
    now = time.time()
    with _lock:
        stamps = [t for t in _attempts.get(client_ip, []) if now - t < _RATE_WINDOW]
        if len(stamps) >= _RATE_MAX:
            _attempts[client_ip] = stamps
            return False, max(1, int(stamps[0] + _RATE_WINDOW - now))
        stamps.append(now)
        _attempts[client_ip] = stamps
    return True, 0


def _parse_values(values: list[list[str]]) -> list[dict[str, Any]]:
    if not values:
        return []
    start = 1 if [_c.strip() for _c in values[0][: len(HEADERS)]] == HEADERS else 0
    reviews: list[dict[str, Any]] = []
    for row in values[start:]:
        cells = [str(c).strip() for c in row] + [""] * max(0, len(HEADERS) - len(row))
        timestamp, name, company, rating_raw, review = cells[: len(HEADERS)]
        if not name and not review:
            continue
        try:
            rating = int(float(rating_raw))
        except ValueError:
            rating = 0
        reviews.append({
            "timestamp": timestamp,
            "name": name,
            "company": company,
            "rating": rating,
            "review": review,
        })
    reviews.sort(key=lambda r: r["timestamp"], reverse=True)
    return reviews


def get_reviews(limit: int = 12) -> dict[str, Any]:
    """Return recent reviews. Always safe to call (never raises)."""
    global _cache, _cache_at, _init_error, _init_failed_at
    now = time.time()
    with _lock:
        if now - _cache_at < _CACHE_TTL and _cache_at > 0:
            return {"reviews": _cache[:limit], "configured": True, "error": None}
        if _init_error and now - _init_failed_at < _INIT_RETRY:
            return {"reviews": [], "configured": False, "error": _init_error}
    try:
        ws = _open_worksheet()
        values = ws.get_all_values()
    except Exception as exc:
        message = str(exc)
        with _lock:
            _init_error = message
            _init_failed_at = time.time()
        _drop_cache()
        return {"reviews": [], "configured": False, "error": message}
    reviews = _parse_values(values)
    with _lock:
        _cache = reviews
        _cache_at = time.time()
        _init_error = ""
    return {"reviews": reviews[:limit], "configured": True, "error": None}


def _drop_cache() -> None:
    global _cache_at
    with _lock:
        _cache_at = 0.0


def add_review(review: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Append a validated review to the sheet. Returns (saved_review, error)."""
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    row = [
        timestamp,
        review["name"],
        review.get("company", ""),
        str(review["rating"]),
        review["review"],
    ]
    try:
        ws = _open_worksheet()
        with _sheet_lock:
            existing = ws.get_all_values()
            if not existing:
                ws.append_row(HEADERS, value_input_option="RAW")
            ws.append_row(row, value_input_option="RAW")
    except Exception as exc:
        return None, str(exc)
    _drop_cache()
    return {**review, "timestamp": timestamp}, None
