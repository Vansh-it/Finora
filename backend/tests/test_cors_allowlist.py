"""Regression tests for production CORS configuration.

Context / bug being locked down
-------------------------------
The deployed mobile frontend (https://finora-2-0.vercel.app) showed
"Could not reach Finora. Check your connection and try again." Searching worked
from the web frontend but not mobile. Root cause: the backend CORS allowlist
(`CORS_ORIGINS`) contained the web origin but not the mobile origin, so the
browser blocked the cross-origin response and `fetch` rejected.

`app.py` resolves the allowlist at import time (see lines ~101-113). These tests
load a fresh app instance with a controlled `CORS_ORIGINS` value and assert the
allowlist behaviour, including the exact value/format the production environment
must use so BOTH frontends keep working.

Expected `CORS_ORIGINS` value (comma-separated, exact scheme+host, no trailing
slash, surrounding whitespace trimmed):

    https://finora-gamma-two.vercel.app,https://finora-2-0.vercel.app
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_PATH = BACKEND_DIR / "app.py"

# app.py imports from the top-level ``lib`` package; make it importable the same
# way the other backend tests do.
sys.path.insert(0, str(BACKEND_DIR))

# Production frontends that must be allowed.
WEB_ORIGIN = "https://finora-gamma-two.vercel.app"
MOBILE_ORIGIN = "https://finora-2-0.vercel.app"
REQUIRED_PROD_ORIGINS = (WEB_ORIGIN, MOBILE_ORIGIN)

# The exact production value operators must set on the backend host.
REQUIRED_PROD_CORS = f"{WEB_ORIGIN},{MOBILE_ORIGIN}"

# Anything not in the allowlist must NOT receive CORS headers (no wildcard).
UNTRUSTED_ORIGIN = "https://evil.example.com"

_load_counter = 0


def load_app(cors_origins: str | None):
    """Import backend/app.py with a controlled CORS_ORIGINS value.

    app.py computes the allowlist at import time, so a fresh module instance is
    loaded instead of mutating the already-imported global ``app`` object.
    ``CORS_ORIGINS`` is always restored afterwards.
    """
    global _load_counter
    original = os.environ.get("CORS_ORIGINS")
    if cors_origins is None:
        os.environ.pop("CORS_ORIGINS", None)
    else:
        os.environ["CORS_ORIGINS"] = cors_origins
    try:
        _load_counter += 1
        spec = importlib.util.spec_from_file_location(f"app_cors_under_test_{_load_counter}", APP_PATH)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        # Several lib/*_client.py modules call load_dotenv(..., override=True),
        # which would clobber CORS_ORIGINS from a developer's local .env during
        # import. Neutralise dotenv so the controlled value is what app.py reads.
        with patch("dotenv.load_dotenv", lambda *a, **k: None):
            spec.loader.exec_module(module)
        return module
    finally:
        if original is None:
            os.environ.pop("CORS_ORIGINS", None)
        else:
            os.environ["CORS_ORIGINS"] = original


def _acao(response) -> str | None:
    return response.headers.get("Access-Control-Allow-Origin")


# ── Format & parsing ─────────────────────────────────────────────────────────


def test_cors_origins_is_comma_separated_and_trimmed():
    """Whitespace around entries is trimmed and empty entries are dropped."""
    module = load_app(f"  {WEB_ORIGIN} ,, {MOBILE_ORIGIN}  , ")
    assert module._allowed_origins == [WEB_ORIGIN, MOBILE_ORIGIN]


def test_empty_cors_origins_falls_back_to_dev_defaults():
    """With no CORS_ORIGINS configured the app only trusts local dev origins."""
    module = load_app(None)
    assert module._allowed_origins == [
        "http://localhost:4321",
        "http://localhost:3000",
        "http://127.0.0.1:4321",
        "http://127.0.0.1:3000",
    ]
    # Production origins must NOT be implicitly trusted without configuration.
    assert MOBILE_ORIGIN not in module._allowed_origins
    assert WEB_ORIGIN not in module._allowed_origins


# ── The actual regression: mobile origin must be allowed when configured ─────


def test_required_production_config_allows_both_frontends():
    """The documented production value allows the web AND mobile origins."""
    module = load_app(REQUIRED_PROD_CORS)
    client = module.app.test_client()
    for origin in REQUIRED_PROD_ORIGINS:
        res = client.get("/api/health", headers={"Origin": origin})
        assert res.status_code == 200
        assert _acao(res) == origin, f"{origin} was not granted CORS access"


def test_health_check_sets_mobile_cors_header():
    """GET /api/health reflects the mobile origin (the exact failing case)."""
    module = load_app(REQUIRED_PROD_CORS)
    client = module.app.test_client()
    res = client.get("/api/health", headers={"Origin": MOBILE_ORIGIN})
    assert res.status_code == 200
    assert _acao(res) == MOBILE_ORIGIN
    assert res.headers.get("Access-Control-Allow-Credentials") == "true"


def test_preflight_allows_mobile_origin_for_research_run():
    """OPTIONS preflight for the search endpoint succeeds for the mobile origin."""
    module = load_app(REQUIRED_PROD_CORS)
    client = module.app.test_client()
    res = client.options(
        "/api/research/run",
        headers={
            "Origin": MOBILE_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert _acao(res) == MOBILE_ORIGIN


def test_mobile_origin_denied_when_missing_from_allowlist():
    """Reproduces the original bug: mobile origin absent => no CORS header."""
    module = load_app(WEB_ORIGIN)  # web only, exactly the pre-fix production state
    client = module.app.test_client()
    res = client.get("/api/health", headers={"Origin": MOBILE_ORIGIN})
    assert res.status_code == 200
    assert _acao(res) is None


# ── Security: allowlist stays exact, no wildcard ─────────────────────────────


def test_untrusted_origin_is_not_granted():
    module = load_app(REQUIRED_PROD_CORS)
    client = module.app.test_client()
    res = client.get("/api/health", headers={"Origin": UNTRUSTED_ORIGIN})
    assert _acao(res) is None
