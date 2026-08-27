"""Unit tests for the authentication service.

Covers: sign up, sign in, sign out, session persistence,
duplicate emails, weak passwords, and token validation.
"""

from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.auth_service import (
    sign_up,
    sign_in,
    sign_out,
    get_user_from_token,
    get_user,
    clear_all,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Clear all users/sessions before each test."""
    clear_all()
    yield
    clear_all()


# ═════════════════════════════════════════════════════════════════════════════
# Sign Up (tests 1-5)
# ═════════════════════════════════════════════════════════════════════════════


class TestSignUp:
    def test_01_valid_signup(self):
        """Valid sign up returns user dict + token."""
        result = sign_up("user@test.com", "password123", "Test User")
        assert "user" in result
        assert "token" in result
        assert result["user"]["email"] == "user@test.com"
        assert result["user"]["name"] == "Test User"
        assert result["user"]["research_runs_used"] == 0
        assert result["user"]["research_runs_limit"] == 5

    def test_02_duplicate_email_rejected(self):
        """Signing up twice with same email raises ValueError."""
        sign_up("dup@test.com", "password123")
        with pytest.raises(ValueError, match="already exists"):
            sign_up("dup@test.com", "password456")

    def test_03_empty_email_rejected(self):
        """Empty email raises ValueError."""
        with pytest.raises(ValueError, match="required"):
            sign_up("", "password123")

    def test_04_short_password_rejected(self):
        """Password under 8 chars raises ValueError."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            sign_up("short@test.com", "abc")

    def test_05_email_case_insensitive(self):
        """Emails are normalised to lowercase."""
        r1 = sign_up("User@TEST.com", "password123")
        assert r1["user"]["email"] == "user@test.com"
        # Duplicate with different case should be rejected
        with pytest.raises(ValueError, match="already exists"):
            sign_up("user@test.com", "password456")


# ═════════════════════════════════════════════════════════════════════════════
# Sign In (tests 6-9)
# ═════════════════════════════════════════════════════════════════════════════


class TestSignIn:
    def test_06_valid_signin(self):
        """Sign in with correct credentials returns user + token."""
        sign_up("login@test.com", "password123")
        result = sign_in("login@test.com", "password123")
        assert "user" in result
        assert "token" in result
        assert result["user"]["email"] == "login@test.com"

    def test_07_wrong_password(self):
        """Sign in with wrong password raises ValueError."""
        sign_up("login@test.com", "password123")
        with pytest.raises(ValueError, match="Incorrect password"):
            sign_in("login@test.com", "wrongpassword")

    def test_08_unknown_email(self):
        """Sign in with unknown email raises ValueError."""
        with pytest.raises(ValueError, match="No account found"):
            sign_in("nobody@test.com", "password123")

    def test_09_session_persists_user_id(self):
        """Signed-in user can be looked up by token."""
        sign_up("persist@test.com", "password123")
        result = sign_in("persist@test.com", "password123")
        user = get_user_from_token(result["token"])
        assert user is not None
        assert user.email == "persist@test.com"


# ═════════════════════════════════════════════════════════════════════════════
# Sign Out (tests 10-12)
# ═════════════════════════════════════════════════════════════════════════════


class TestSignOut:
    def test_10_sign_out_invalidates_token(self):
        """After sign out, token is no longer valid."""
        result = sign_up("out@test.com", "password123")
        token = result["token"]
        assert get_user_from_token(token) is not None
        sign_out(token)
        assert get_user_from_token(token) is None

    def test_11_sign_out_returns_true(self):
        """Sign out of a valid token returns True."""
        result = sign_up("out@test.com", "password123")
        assert sign_out(result["token"]) is True

    def test_12_sign_out_invalid_token(self):
        """Sign out of a nonexistent token returns False."""
        assert sign_out("nonexistent-token") is False


# ═════════════════════════════════════════════════════════════════════════════
# Token Validation (tests 13-15)
# ═════════════════════════════════════════════════════════════════════════════


class TestTokenValidation:
    def test_13_invalid_token_returns_none(self):
        """Random token returns None."""
        assert get_user_from_token("totally-fake-token") is None

    def test_14_user_lookup_by_id(self):
        """get_user() returns the user by ID."""
        result = sign_up("lookup@test.com", "password123")
        user = get_user(result["user"]["user_id"])
        assert user is not None
        assert user.email == "lookup@test.com"

    def test_15_user_lookup_nonexistent(self):
        """get_user() with fake ID returns None."""
        assert get_user("fake-id") is None
