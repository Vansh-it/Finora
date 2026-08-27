"""Unit tests for chat usage limit service.

Covers: 15-message limit, rolling window, pruning old messages,
usage reporting, and edge cases.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.chat_usage import (
    CHAT_LIMIT,
    ROLLING_WINDOW_SECONDS,
    can_send_message,
    record_message,
    get_usage,
    clear_all,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Clear all message logs before each test."""
    clear_all()
    yield
    clear_all()


# ═════════════════════════════════════════════════════════════════════════════
# Basic Usage (tests 1-5)
# ═════════════════════════════════════════════════════════════════════════════


class TestBasicUsage:
    def test_01_first_message_allowed(self):
        """First message is always allowed."""
        usage = record_message("user1")
        assert usage["allowed"] is True
        assert usage["used"] == 1
        assert usage["remaining"] == CHAT_LIMIT - 1

    def test_02_can_send_before_limit(self):
        """can_send_message returns True when under limit."""
        for i in range(CHAT_LIMIT - 1):
            record_message("user2")
        assert can_send_message("user2") is True

    def test_03_usage_tracking(self):
        """get_usage returns correct counts without recording."""
        record_message("user3")
        record_message("user3")
        usage = get_usage("user3")
        assert usage["used"] == 2
        assert usage["remaining"] == CHAT_LIMIT - 2

    def test_04_fresh_user_has_zero_usage(self):
        """New user has 0 messages used."""
        usage = get_usage("new_user")
        assert usage["used"] == 0
        assert usage["remaining"] == CHAT_LIMIT

    def test_05_independent_users(self):
        """Different users have independent limits."""
        record_message("user_a")
        record_message("user_a")
        record_message("user_b")
        assert get_usage("user_a")["used"] == 2
        assert get_usage("user_b")["used"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# Limit Enforcement (tests 6-9)
# ═════════════════════════════════════════════════════════════════════════════


class TestLimitEnforcement:
    def test_06_15th_message_allowed(self):
        """Message 15 (the last allowed) should be accepted."""
        for i in range(CHAT_LIMIT - 1):
            record_message("user_limit")
        usage = record_message("user_limit")
        assert usage["allowed"] is True
        assert usage["used"] == CHAT_LIMIT
        assert usage["remaining"] == 0

    def test_07_16th_message_rejected(self):
        """Message 16 should be rejected."""
        for i in range(CHAT_LIMIT):
            record_message("user_over")
        usage = record_message("user_over")
        assert usage["allowed"] is False
        assert usage["used"] == CHAT_LIMIT
        assert usage["remaining"] == 0

    def test_08_can_send_returns_false_at_limit(self):
        """can_send_message returns False at exactly the limit."""
        for i in range(CHAT_LIMIT):
            record_message("user_full")
        assert can_send_message("user_full") is False

    def test_09_rejected_message_not_recorded(self):
        """A rejected message should NOT be added to the log."""
        for i in range(CHAT_LIMIT):
            record_message("user_count")
        record_message("user_count")  # rejected
        usage = get_usage("user_count")
        assert usage["used"] == CHAT_LIMIT  # still 15, not 16


# ═════════════════════════════════════════════════════════════════════════════
# Rolling Window (tests 10-13)
# ═════════════════════════════════════════════════════════════════════════════


class TestRollingWindow:
    def test_10_old_messages_pruned(self):
        """Messages older than 24h are no longer counted."""
        # Manually inject an old timestamp
        from lib.chat_usage import _message_log
        old_time = time.time() - ROLLING_WINDOW_SECONDS - 100
        _message_log["old_user"] = [old_time] * 15

        # Should now be allowed since all messages are expired
        assert can_send_message("old_user") is True
        assert get_usage("old_user")["used"] == 0

    def test_11_partial_expiry(self):
        """Only some messages expire, user stays at limit."""
        from lib.chat_usage import _message_log
        now = time.time()
        old_time = now - ROLLING_WINDOW_SECONDS - 100
        # 14 old (expired) + 1 recent (not expired) = 1 remaining in window
        _message_log["partial_user"] = [old_time] * 14 + [now]

        usage = get_usage("partial_user")
        assert usage["used"] == 1
        assert usage["remaining"] == CHAT_LIMIT - 1

    def test_12_reset_in_seconds_positive(self):
        """reset_in_seconds is positive for messages within window."""
        record_message("reset_user")
        usage = get_usage("reset_user")
        assert usage["reset_in_seconds"] > 0

    def test_13_reset_in_seconds_zero_when_empty(self):
        """reset_in_seconds is 0 when no messages exist."""
        usage = get_usage("empty_user")
        assert usage["reset_in_seconds"] == 0
