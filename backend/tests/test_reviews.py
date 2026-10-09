"""Unit tests for the Google Sheets-backed review service and its API.

Covers:
  - submission validation (lengths, rating bounds, HTML stripping)
  - per-IP submission rate limiting
  - sheet parsing (header detection, sorting, limit)
  - graceful degradation when credentials are missing
  - header auto-creation on an empty sheet
  - GET/POST /api/reviews behaviour incl. honeypot and error statuses
"""

from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lib.reviews as reviews
from lib.reviews import (
    HEADERS,
    add_review,
    check_review_rate_limit,
    get_reviews,
    validate_review,
)
from app import app


class FakeWorksheet:
    """In-memory stand-in for a gspread worksheet."""

    def __init__(self, rows=None):
        self.rows = [list(r) for r in (rows or [])]

    def get_all_values(self):
        return [list(r) for r in self.rows]

    def append_row(self, values, value_input_option=None):
        self.rows.append(list(values))


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Reset all module-level review state before/after each test."""
    reviews._attempts.clear()
    reviews._cache = []
    reviews._cache_at = 0.0
    reviews._ws = None
    reviews._init_error = ""
    reviews._init_failed_at = 0.0
    yield
    reviews._attempts.clear()
    reviews._cache = []
    reviews._cache_at = 0.0
    reviews._ws = None
    reviews._init_error = ""
    reviews._init_failed_at = 0.0


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Validation ───────────────────────────────────────────────────────────────

def test_valid_submission_passes():
    review, err = validate_review({
        "name": "Vansh Chaurasia",
        "company": "Finora Labs",
        "rating": "5",
        "review": "Institutional-grade research with sources I can actually verify.",
    })
    assert err is None
    assert review == {
        "name": "Vansh Chaurasia",
        "company": "Finora Labs",
        "rating": 5,
        "review": "Institutional-grade research with sources I can actually verify.",
    }


def test_name_required():
    review, err = validate_review({"name": " ", "rating": 5, "review": "A perfectly fine review here."})
    assert review is None
    assert "name" in err.lower()


def test_short_review_rejected():
    review, err = validate_review({"name": "Ana", "rating": 4, "review": "too short"})
    assert review is None
    assert "10 characters" in err


def test_review_max_length_enforced():
    review, err = validate_review({"name": "Ana", "rating": 4, "review": "x" * 2001})
    assert review is None
    assert "2000" in err


@pytest.mark.parametrize("rating", ["0", "6", "-1", "abc", None])
def test_bad_rating_rejected(rating):
    review, err = validate_review({"name": "Ana", "rating": rating, "review": "A perfectly fine review here."})
    assert review is None
    assert "rating" in err.lower()


def test_company_optional_but_bounded():
    review, err = validate_review({"name": "Ana", "company": "c" * 81, "rating": 3, "review": "A perfectly fine review here."})
    assert review is None
    assert "Company" in err
    review, err = validate_review({"name": "Ana", "rating": 3, "review": "A perfectly fine review here."})
    assert err is None
    assert review["company"] == ""


def test_html_and_control_chars_stripped():
    review, err = validate_review({
        "name": "<b>Vansh</b>",
        "rating": 5,
        "review": "Great   work\x00 Finora <script>alert(1)</script>really nails it.",
    })
    assert err is None
    assert review["name"] == "Vansh"
    assert "<" not in review["review"]
    assert "alert(1)" not in review["review"]
    assert "\x00" not in review["review"]


# ── Rate limiting ────────────────────────────────────────────────────────────

def test_rate_limit_allows_five_then_blocks():
    for i in range(5):
        allowed, retry = check_review_rate_limit("1.2.3.4")
        assert allowed and retry == 0
    allowed, retry = check_review_rate_limit("1.2.3.4")
    assert not allowed
    assert retry > 0


def test_rate_limit_is_per_ip():
    for _ in range(5):
        check_review_rate_limit("1.2.3.4")
    allowed, _ = check_review_rate_limit("5.6.7.8")
    assert allowed


def test_rate_limit_window_prunes_old_entries(monkeypatch):
    import time as _time
    base = _time.time()
    reviews._attempts["9.9.9.9"] = [base - 4000, base - 3900, base - 3800, base - 3700, base - 3600]
    allowed, _ = check_review_rate_limit("9.9.9.9")
    assert allowed


# ── Sheet parsing / storage ──────────────────────────────────────────────────

def test_get_reviews_reads_and_sorts(monkeypatch):
    fake = FakeWorksheet([
        HEADERS,
        ["2026-01-01T00:00:00+00:00", "Older", "A", 4, "Older review body here."],
        ["2026-03-01T00:00:00+00:00", "Newer", "B", 5, "Newer review body here."],
        ["2026-02-01T00:00:00+00:00", "Middle", "C", 3, "Middle review body here."],
    ])
    monkeypatch.setattr(reviews, "_open_worksheet", lambda: fake)
    res = get_reviews(2)
    assert res["configured"] is True
    assert res["error"] is None
    assert [r["name"] for r in res["reviews"]] == ["Newer", "Middle"]


def test_get_reviews_unconfigured_returns_empty(monkeypatch):
    monkeypatch.setenv("GOOGLE_CREDENTIALS_FILE", "definitely_missing_key.json")
    res = get_reviews(5)
    assert res == {"reviews": [], "configured": False, "error": reviews._init_error}
    assert res["error"]


def test_add_review_creates_header_on_empty_sheet(monkeypatch):
    fake = FakeWorksheet()
    monkeypatch.setattr(reviews, "_open_worksheet", lambda: fake)
    saved, err = add_review({"name": "Ana", "company": "Acme", "rating": 5, "review": "A perfectly fine review here."})
    assert err is None
    assert fake.rows[0] == HEADERS
    assert fake.rows[1][1:4] == ["Ana", "Acme", "5"]
    assert saved["timestamp"]


def test_add_review_invalidates_cache(monkeypatch):
    fake = FakeWorksheet([HEADERS])
    monkeypatch.setattr(reviews, "_open_worksheet", lambda: fake)
    reviews._cache = []
    reviews._cache_at = 10**12  # fresh-looking cache
    add_review({"name": "Ana", "company": "", "rating": 4, "review": "A perfectly fine review here."})
    assert reviews._cache_at == 0.0


# ── API ──────────────────────────────────────────────────────────────────────

def test_get_api_returns_reviews(client, monkeypatch):
    fake = FakeWorksheet([HEADERS, ["2026-05-01T00:00:00+00:00", "Ana", "Acme", 5, "Finora is genuinely excellent."]])
    monkeypatch.setattr(reviews, "_open_worksheet", lambda: fake)
    res = client.get("/api/reviews?limit=10")
    assert res.status_code == 200
    data = res.get_json()
    assert data["configured"] is True
    assert len(data["reviews"]) == 1
    assert data["reviews"][0]["name"] == "Ana"


def test_post_api_success(client, monkeypatch):
    fake = FakeWorksheet([HEADERS])
    monkeypatch.setattr(reviews, "_open_worksheet", lambda: fake)
    res = client.post("/api/reviews", json={
        "name": "Ana",
        "company": "Acme",
        "rating": 5,
        "review": "Finora is genuinely excellent research tooling.",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    assert data["review"]["rating"] == 5
    assert len(fake.rows) == 2  # header + saved row


def test_post_api_validation_error(client):
    res = client.post("/api/reviews", json={"name": "A", "rating": 9, "review": "short"})
    assert res.status_code == 400
    assert res.get_json()["status"] == "error"


def test_post_api_honeypot_fakes_success_without_storing(client, monkeypatch):
    fake = FakeWorksheet([HEADERS])
    monkeypatch.setattr(reviews, "_open_worksheet", lambda: fake)
    res = client.post("/api/reviews", json={
        "name": "Bot", "rating": 5, "review": "totally a human review here", "website": "spam.example",
    })
    assert res.status_code == 201
    assert len(fake.rows) == 1  # nothing appended


def test_post_api_rate_limited(client, monkeypatch):
    monkeypatch.setattr(reviews, "_open_worksheet", lambda: FakeWorksheet([HEADERS]))
    payload = {"name": "Ana", "rating": 4, "review": "Finora is genuinely excellent research tooling."}
    res = None
    for _ in range(6):
        res = client.post("/api/reviews", json=payload)
    assert res.status_code == 429
    assert "try again" in res.get_json()["error"].lower()


def test_post_api_sheet_failure_returns_503(client, monkeypatch):
    def boom():
        raise reviews.ReviewsNotConfigured("sheet unreachable")
    monkeypatch.setattr(reviews, "_open_worksheet", boom)
    res = client.post("/api/reviews", json={
        "name": "Ana", "rating": 4, "review": "Finora is genuinely excellent research tooling.",
    })
    assert res.status_code == 503
    assert res.get_json()["status"] == "error"
