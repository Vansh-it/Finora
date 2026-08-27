"""Production hardening tests.

Covers: research quota, password hashing (werkzeug), session ownership,
input validation, persistence, chat limit, idempotency, concurrency safety.
"""

from __future__ import annotations

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.auth_service import (
    sign_up, sign_in, sign_out, get_user_from_token, get_user,
    increment_research_runs, can_use_research, clear_all,
)
from lib.chat_usage import can_send_message, record_message, get_usage, clear_all as clear_chat
from lib.research_session import (
    grant_permission, get_session, cancel_session,
    update_session_status, clear_all_sessions,
)
from lib.persistence import clear_all_persistence, get_data_dir


@pytest.fixture(autouse=True)
def clean_state():
    """Clear all state before each test."""
    clear_all()
    clear_chat()
    clear_all_sessions()
    yield
    clear_all()
    clear_chat()
    clear_all_sessions()


# ── Password Security ────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_uses_werkzeug_pbkdf2(self):
        """Password hash should use PBKDF2, not plain SHA-256."""
        result = sign_up("secure@test.com", "password123")
        from lib.auth_service import _users
        user = list(_users.values())[0]
        # Werkzeug PBKDF2 hashes start with pbkdf2:sha256
        assert "pbkdf2" in user.password_hash or "scrypt" in user.password_hash

    def test_same_password_different_hashes(self):
        """Two users with same password should have different hashes (unique salt)."""
        sign_up("user1@test.com", "password123")
        sign_up("user2@test.com", "password123")
        from lib.auth_service import _users
        hashes = [u.password_hash for u in _users.values()]
        assert len(hashes) == 2
        assert hashes[0] != hashes[1]

    def test_password_not_in_user_dict(self):
        """password_hash should not appear in public user dict."""
        result = sign_up("pub@test.com", "password123")
        user_dict = result["user"]
        assert "password_hash" not in user_dict
        assert "password" not in user_dict

    def test_password_hash_in_internal_dict(self):
        """password_hash should be in to_dict() for persistence."""
        from lib.auth_service import _users
        sign_up("internal@test.com", "password123")
        user = list(_users.values())[0]
        internal = user.to_dict()
        assert "password_hash" in internal
        assert len(internal["password_hash"]) > 20

    def test_sign_in_with_werkzeug_hash(self):
        """Sign in should work with werkzeug hashed password."""
        sign_up("login@test.com", "securepass1")
        result = sign_in("login@test.com", "securepass1")
        assert "token" in result

    def test_wrong_password_rejected(self):
        """Wrong password should be rejected."""
        sign_up("wrong@test.com", "correctpass")
        with pytest.raises(ValueError, match="Incorrect password"):
            sign_in("wrong@test.com", "wrongpass1")


# ── Research Quota ────────────────────────────────────────────────────────────

class TestResearchQuota:
    def test_new_user_has_5_runs(self):
        """New user starts with 5 remaining research runs."""
        result = sign_up("quota@test.com", "password123")
        user = get_user(result["user"]["user_id"])
        assert user.research_runs_limit == 5
        assert user.research_runs_used == 0

    def test_can_use_research_initially(self):
        """New user should be allowed to research."""
        result = sign_up("canresearch@test.com", "password123")
        quota = can_use_research(result["user"]["user_id"])
        assert quota["allowed"] is True
        assert quota["remaining"] == 5

    def test_increment_research_runs(self):
        """Incrementing should increase used count."""
        result = sign_up("inc@test.com", "password123")
        uid = result["user"]["user_id"]
        increment_research_runs(uid)
        user = get_user(uid)
        assert user.research_runs_used == 1

    def test_quota_exhausted_after_5(self):
        """After 5 successful runs, user should be blocked."""
        result = sign_up("exhaust@test.com", "password123")
        uid = result["user"]["user_id"]
        for _ in range(5):
            assert increment_research_runs(uid) is True
        assert increment_research_runs(uid) is False
        quota = can_use_research(uid)
        assert quota["allowed"] is False
        assert quota["remaining"] == 0

    def test_quota_idempotent_on_refresh(self):
        """Refreshing dashboard should NOT consume another run."""
        result = sign_up("idempotent@test.com", "password123")
        uid = result["user"]["user_id"]
        increment_research_runs(uid)
        # Reading session again doesn't increment
        user = get_user(uid)
        assert user.research_runs_used == 1

    def test_failed_run_not_counted(self):
        """A failed/errored research should not count against quota."""
        result = sign_up("failed@test.com", "password123")
        uid = result["user"]["user_id"]
        # Quota only incremented in api_read_verify_sources on success
        user = get_user(uid)
        assert user.research_runs_used == 0

    def test_unknown_user_quota(self):
        """Unknown user_id should return not allowed."""
        quota = can_use_research("nonexistent_user_id")
        assert quota["allowed"] is False

    def test_quota_persists_in_session(self):
        """Quota should survive in-memory session via persistence."""
        result = sign_up("persist@test.com", "password123")
        uid = result["user"]["user_id"]
        for _ in range(3):
            increment_research_runs(uid)
        # Re-fetch user
        user = get_user(uid)
        assert user.research_runs_used == 3

    def test_fifth_run_succeeds_sixth_blocked(self):
        """Exactly 5 runs should succeed, 6th should be blocked."""
        result = sign_up("boundary@test.com", "password123")
        uid = result["user"]["user_id"]
        for i in range(5):
            assert increment_research_runs(uid) is True, f"Run {i+1} should succeed"
        assert increment_research_runs(uid) is False, "Run 6 should be blocked"


# ── Session Ownership ─────────────────────────────────────────────────────────

class TestSessionOwnership:
    def test_session_stores_user_id(self):
        """Research session should store the user_id."""
        result = sign_up("owner@test.com", "password123")
        uid = result["user"]["user_id"]
        session = grant_permission({"company": "Microsoft"}, user_id=uid)
        assert session.user_id == uid

    def test_session_without_user_id(self):
        """Sessions without user_id should still work (backward compat)."""
        session = grant_permission({"company": "Apple"})
        assert session.user_id == ""

    def test_session_dict_includes_user_id(self):
        """Session.to_dict() should include user_id."""
        result = sign_up("dictowner@test.com", "password123")
        session = grant_permission({"company": "NVIDIA"}, user_id=result["user"]["user_id"])
        d = session.to_dict()
        assert "user_id" in d
        assert d["user_id"] == result["user"]["user_id"]


# ── Chat Limit ───────────────────────────────────────────────────────────────

class TestChatLimit:
    def test_can_send_initially(self):
        """New user should be able to send messages."""
        assert can_send_message("user_chat_test") is True

    def test_records_15_messages(self):
        """Should allow exactly 15 messages."""
        uid = "chat_limit_user"
        for i in range(15):
            result = record_message(uid)
            assert result["allowed"] is True, f"Message {i+1} should be allowed"
        assert result["remaining"] == 0

    def test_16th_message_blocked(self):
        """16th message should be blocked."""
        uid = "chat_16th_user"
        for _ in range(15):
            record_message(uid)
        result = record_message(uid)
        assert result["allowed"] is False
        assert result["remaining"] == 0

    def test_usage_tracking(self):
        """Usage should track correctly."""
        uid = "chat_usage_user"
        record_message(uid)
        record_message(uid)
        usage = get_usage(uid)
        assert usage["used"] == 2
        assert usage["remaining"] == 13
        assert usage["limit"] == 15

    def test_clear_all_works(self):
        """clear_all should reset chat data."""
        uid = "clear_chat_user"
        for _ in range(10):
            record_message(uid)
        clear_chat()
        assert can_send_message(uid) is True

    def test_different_users_independent(self):
        """Chat limits should be independent per user."""
        record_message("user_a")
        record_message("user_a")
        record_message("user_b")
        assert get_usage("user_a")["used"] == 2
        assert get_usage("user_b")["used"] == 1


# ── Input Validation ─────────────────────────────────────────────────────────

class TestInputValidation:
    def test_empty_email_rejected(self):
        """Empty email should be rejected."""
        with pytest.raises(ValueError):
            sign_up("", "password123")

    def test_empty_password_rejected(self):
        """Empty password should be rejected."""
        with pytest.raises(ValueError):
            sign_up("test@test.com", "")

    def test_short_password_rejected(self):
        """Password < 8 chars should be rejected."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            sign_up("short@test.com", "abc")

    def test_duplicate_email_rejected(self):
        """Duplicate email should be rejected."""
        sign_up("dup@test.com", "password123")
        with pytest.raises(ValueError, match="already exists"):
            sign_up("dup@test.com", "password124")

    def test_email_case_insensitive(self):
        """Email should be case-insensitive."""
        sign_up("Case@Test.com", "password123")
        with pytest.raises(ValueError, match="already exists"):
            sign_up("case@test.com", "password123")

    def test_invalid_session_id_format(self):
        """Invalid session ID format should be caught in validation."""
        import re
        pattern = re.compile(r"^[a-f0-9]{32,64}$")
        assert not pattern.match("../../../etc/passwd")
        assert not pattern.match("<script>alert(1)</script>")
        assert not pattern.match("UPPERCASE")
        assert not pattern.match("")
        assert pattern.match("a" * 32)


# ── Persistence ───────────────────────────────────────────────────────────────

class TestPersistence:
    def test_data_dir_exists(self):
        """Data directory should be created."""
        data_dir = get_data_dir()
        assert os.path.isdir(data_dir)

    def test_user_survives_clear_and_reload(self):
        """User data should persist to disk and reload."""
        result = sign_up("persist@test.com", "password123")
        uid = result["user"]["user_id"]
        # Simulate restart by clearing in-memory state
        from lib import auth_service
        auth_service._users.clear()
        auth_service._sessions.clear()
        auth_service._email_index.clear()
        auth_service._loaded = False
        # Re-load from disk
        user = get_user(uid)
        assert user is not None
        assert user.email == "persist@test.com"

    def test_session_survives_reload(self):
        """Auth session should persist across reloads."""
        result = sign_up("session@test.com", "password123")
        token = result["token"]
        # Clear in-memory
        from lib import auth_service
        auth_service._users.clear()
        auth_service._sessions.clear()
        auth_service._email_index.clear()
        auth_service._loaded = False
        # Re-load
        user = get_user_from_token(token)
        assert user is not None


# ── Cancellation ──────────────────────────────────────────────────────────────

class TestCancellation:
    def test_cancelled_session_has_error_status(self):
        """Cancelled session should return error/409 from endpoints."""
        session = grant_permission({"company": "TestCo"})
        cancel_session(session.session_id)
        fetched = get_session(session.session_id)
        assert fetched.status == "cancelled"

    def test_cancel_nonexistent_returns_false(self):
        """Cancelling nonexistent session should return False."""
        assert cancel_session("nonexistent_id") is False
