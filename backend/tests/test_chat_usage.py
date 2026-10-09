"""Unit tests for the daily chat usage quota service.

Covers the production limits:
  - 25 user messages per user per UTC day
  - 7,500 user-input words per user per UTC day
  - both enforced together (whichever hits first blocks)
  - automatic UTC-day reset
  - atomic check+increment (race safety)
  - rejected messages are not recorded
"""

from __future__ import annotations

import threading

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.chat_usage import (
    DAILY_MESSAGE_LIMIT,
    DAILY_WORD_LIMIT,
    can_send_message,
    reserve_message,
    record_message,
    get_usage,
    clear_all,
)
from lib.research_agent import count_words


@pytest.fixture(autouse=True)
def clean_state():
    """Clear all quota data before/after each test."""
    clear_all()
    yield
    clear_all()


# ═════════════════════════════════════════════════════════════════════════════
# Constants (spec: PART 49)
# ═════════════════════════════════════════════════════════════════════════════

class TestLimits:
    def test_message_limit_is_25(self):
        assert DAILY_MESSAGE_LIMIT == 25

    def test_word_limit_is_7500(self):
        assert DAILY_WORD_LIMIT == 7500


# ═════════════════════════════════════════════════════════════════════════════
# Word counting (spec: PART 51 — deterministic, server-side)
# ═════════════════════════════════════════════════════════════════════════════

class TestWordCount:
    def test_basic_count(self):
        assert count_words("what happened to tesla") == 4

    def test_whitespace_variants(self):
        assert count_words("  a   b\t c \n") == 3

    def test_empty_and_none(self):
        assert count_words("") == 0
        assert count_words("   ") == 0
        assert count_words(None) == 0

    def test_matches_split_semantics(self):
        text = "Why did Tesla's margins fall? [S1]"
        assert count_words(text) == len(text.split())


# ═════════════════════════════════════════════════════════════════════════════
# Message limit (spec: PART 49/50)
# ═════════════════════════════════════════════════════════════════════════════

class TestMessageLimit:
    def test_first_message_allowed(self):
        usage = reserve_message("user1", "hello")
        assert usage["allowed"] is True
        assert usage["messages_used"] == 1
        assert usage["messages_remaining"] == DAILY_MESSAGE_LIMIT - 1

    def test_25th_allowed_26th_blocked(self):
        uid = "user_msg_limit"
        for i in range(DAILY_MESSAGE_LIMIT):
            usage = reserve_message(uid, f"message number {i}")
            assert usage["allowed"] is True, f"message {i+1} must be allowed"
        usage = reserve_message(uid, "one too many")
        assert usage["allowed"] is False
        assert usage["reason"] == "message_limit"
        assert usage["messages_used"] == DAILY_MESSAGE_LIMIT
        assert usage["messages_remaining"] == 0

    def test_rejected_message_not_recorded(self):
        uid = "user_rejected"
        for _ in range(DAILY_MESSAGE_LIMIT):
            reserve_message(uid, "x")
        reserve_message(uid, "should not count")
        assert get_usage(uid)["messages_used"] == DAILY_MESSAGE_LIMIT
        assert get_usage(uid)["words_used"] == sum(
            count_words("x") for _ in range(DAILY_MESSAGE_LIMIT)
        )

    def test_can_send_message_reflects_limit(self):
        uid = "user_can_send"
        assert can_send_message(uid) is True
        for _ in range(DAILY_MESSAGE_LIMIT):
            reserve_message(uid, "x")
        assert can_send_message(uid) is False

    def test_independent_users(self):
        reserve_message("user_a", "one")
        reserve_message("user_a", "two")
        reserve_message("user_b", "one")
        assert get_usage("user_a")["messages_used"] == 2
        assert get_usage("user_b")["messages_used"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# Word limit (spec: PART 49/51)
# ═════════════════════════════════════════════════════════════════════════════

class TestWordLimit:
    def test_words_accumulate(self):
        usage = reserve_message("user_words", "one two three four five")
        assert usage["words_used"] == 5
        assert usage["words_limit"] == DAILY_WORD_LIMIT
        assert usage["words_remaining"] == DAILY_WORD_LIMIT - 5

    def test_word_limit_blocks_before_message_limit(self):
        """PART 68 #16: word limit can trigger before the message limit."""
        uid = "user_word_limit"
        filler = " ".join(["word"] * 500)  # 500 words per message
        consumed = 0
        # 14 messages × 500 = 7,000 words (still under 25 messages)
        for i in range(14):
            usage = reserve_message(uid, filler)
            assert usage["allowed"] is True, f"message {i+1} should pass"
            consumed += 500
        assert consumed == 7000
        # Message 15 lands exactly on 7,500 words → allowed
        usage = reserve_message(uid, filler)
        assert usage["allowed"] is True
        assert usage["words_used"] == DAILY_WORD_LIMIT
        # Message 16 would exceed 7,500 → blocked (message count still < 25)
        usage = reserve_message(uid, filler)
        assert usage["allowed"] is False
        assert usage["reason"] == "word_limit"
        assert usage["messages_used"] == 15  # rejected message not recorded
        assert usage["words_used"] == 7500

    def test_exact_boundary_allowed(self):
        """Exactly 7,500 words is allowed; the next word is not."""
        uid = "user_boundary"
        usage = reserve_message(uid, " ".join(["w"] * 7490))
        assert usage["allowed"] is True
        assert usage["words_used"] == 7490
        # 10 words remaining — a 10-word message fits exactly
        usage = reserve_message(uid, " ".join(["w"] * 10))
        assert usage["allowed"] is True
        assert usage["words_used"] == DAILY_WORD_LIMIT
        # now nothing fits
        usage = reserve_message(uid, "any")
        assert usage["allowed"] is False
        assert usage["reason"] in ("word_limit", "message_limit")

    def test_empty_word_message_still_counted_as_message(self):
        uid = "user_empty_words"
        usage = reserve_message(uid, "hi")
        assert usage["allowed"] is True
        assert usage["messages_used"] == 1
        assert usage["words_used"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# Daily reset (spec: PART 52)
# ═════════════════════════════════════════════════════════════════════════════

class TestDailyReset:
    def test_old_day_record_resets(self):
        import lib.chat_usage as cu
        uid = "user_reset"
        cu._ensure_loaded()
        cu._quota[uid] = {"day": "2000-01-01", "messages": 25, "words": 7400}
        usage = get_usage(uid)
        assert usage["messages_used"] == 0
        assert usage["words_used"] == 0
        assert can_send_message(uid, "hello") is True

    def test_reset_at_is_next_utc_midnight(self):
        usage = get_usage("user_reset_at")
        reset_at = usage["reset_at"]
        assert reset_at.endswith("Z")
        # must be in the future and less than 24h away
        from datetime import datetime, timezone
        dt = datetime.strptime(reset_at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        now = datetime.now(timezone.utc)
        assert dt > now
        assert (dt - now).total_seconds() <= 86400

    def test_legacy_timestamp_list_migrates(self):
        """Old rolling-window records (list of timestamps) are migrated."""
        import lib.chat_usage as cu
        uid = "user_legacy"
        cu._ensure_loaded()
        import time as _time
        now = _time.time()
        cu._quota[uid] = [now, now, now]  # legacy format: 3 messages today
        usage = get_usage(uid)
        assert usage["messages_used"] == 3
        assert usage["words_used"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# Race safety (spec: PART 54)
# ═════════════════════════════════════════════════════════════════════════════

class TestRaceSafety:
    def test_simultaneous_requests_cannot_bypass_limit(self):
        """40 simultaneous requests on a 24/25 user: only 1 may pass."""
        uid = "user_race"
        for _ in range(DAILY_MESSAGE_LIMIT - 1):
            reserve_message(uid, "x")

        results = []
        lock = threading.Lock()
        barrier = threading.Barrier(10)

        def worker():
            barrier.wait()
            usage = reserve_message(uid, "race message here")
            with lock:
                results.append(usage["allowed"])

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        allowed = sum(1 for r in results if r)
        assert allowed == 1  # exactly one may fill slot 25
        assert get_usage(uid)["messages_used"] == DAILY_MESSAGE_LIMIT

    def test_concurrent_first_messages(self):
        """40 concurrent messages for a fresh user: exactly 25 allowed."""
        uid = "user_race_fresh"
        results = []
        lock = threading.Lock()
        barrier = threading.Barrier(40)

        def worker():
            barrier.wait()
            usage = reserve_message(uid, "hello world")
            with lock:
                results.append(usage["allowed"])

        threads = [threading.Thread(target=worker) for _ in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sum(1 for r in results if r) == DAILY_MESSAGE_LIMIT
        assert get_usage(uid)["messages_used"] == DAILY_MESSAGE_LIMIT


# ═════════════════════════════════════════════════════════════════════════════
# Usage reporting (spec: PART 58)
# ═════════════════════════════════════════════════════════════════════════════

class TestUsageReporting:
    def test_usage_shape(self):
        reserve_message("user_shape", "one two three")
        usage = get_usage("user_shape")
        for key in ("messages_used", "messages_limit", "messages_remaining",
                    "words_used", "words_limit", "words_remaining", "reset_at"):
            assert key in usage, f"missing {key}"
        assert usage["messages_used"] == 1
        assert usage["words_used"] == 3
        # legacy keys still present for old callers
        for key in ("used", "limit", "remaining", "reset_in_seconds"):
            assert key in usage

    def test_get_usage_does_not_record(self):
        uid = "user_no_record"
        get_usage(uid)
        get_usage(uid)
        assert get_usage(uid)["messages_used"] == 0
