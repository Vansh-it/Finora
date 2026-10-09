"""Endpoint tests for the research chat: pipeline, streaming, quota, usage API.

Covers spec PART 35 items: follow-up mode pass-through, company context,
LLM failure, streaming frames, citation/source payloads, quota rejection
(no unnecessary LLM/web calls), and 300-word enforcement end-to-end.
"""

from __future__ import annotations

import json
import sys
import os

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app
import lib.chat_usage as cu
from lib.research_agent import count_words
from lib.response_guard import MAX_RESPONSE_WORDS

USER_ID = "test_user_123"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
    # keep global quota state clean for other test modules
    cu._quota.pop(USER_ID, None)


def _mock_auth():
    from lib.auth_service import User
    mock_user = User(user_id=USER_ID, email="test@example.com", name="Test")
    return patch("app.get_user_from_token", return_value=mock_user)


def _auth_headers():
    return {"Authorization": "Bearer fake_test_token"}


def _mock_generate(return_value: str = "Hello! I'm Finora."):
    mock_manager = MagicMock()
    mock_manager.generate_chat.return_value = return_value
    mock_manager.get_status.return_value = {"active_provider": "test_model",
                                            "providers": []}
    return patch("app.get_manager", return_value=mock_manager)


def _fake_web_research():
    """Canned research result shaped exactly like run_web_research output."""
    return {
        "evidence": [{
            "source_type": "news",
            "title": "Tesla cuts prices amid demand concerns",
            "url": "https://www.reuters.com/business/auto/tesla-prices",
            "publisher": "www.reuters.com",
            "published_at": "2026-10-06",
            "retrieved_at": "2026-10-07T00:00:00Z",
            "relevance_score": 3.2,
            "credibility_score": 0.75,
            "content": "Tesla reduced prices on several models this week.",
            "tier": 2,
        }],
        "sources": [{
            "title": "Tesla cuts prices amid demand concerns",
            "url": "https://www.reuters.com/business/auto/tesla-prices",
            "publisher": "www.reuters.com",
            "published_at": "2026-10-06",
            "tier": "news",
        }],
        "queries": ["Tesla margin trend"],
        "errors": [],
        "degraded": False,
        "partially_degraded": False,
        "timings": {"search_ms": 120, "fetch_ms": 80, "total_ms": 200},
        "counts": {"queries": 1, "results": 5, "sources_used": 1},
    }


def _parse_frames(raw: str) -> list[dict]:
    frames = []
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            frames.append(json.loads(line[len("data: "):]))
    return frames


# ═════════════════════════════════════════════════════════════════════════════
# Streaming (spec PART 18, 40)
# ═════════════════════════════════════════════════════════════════════════════

class TestStreaming:
    def test_stream_emits_real_stages_then_answer(self, client):
        with _mock_auth(), _mock_generate("EV/EBITDA is enterprise value over EBITDA."):
            resp = client.post(
                "/api/chat/stream",
                json={"message": "What is EV/EBITDA?", "history": []},
                headers=_auth_headers(), content_type="application/json",
            )
            # consume inside the patch: the SSE generator runs lazily
            raw = resp.get_data(as_text=True)
        assert resp.status_code == 200
        assert resp.mimetype == "text/event-stream"
        frames = _parse_frames(raw)
        events = [f["event"] for f in frames]
        stages = [f.get("stage") for f in frames if f["event"] == "status"]
        assert events[0] == "status"
        assert "synthesizing" in stages
        # definition question → no web research stage, no fake progress
        assert "searching" not in stages
        assert events[-1] == "answer"
        answer = frames[-1]
        assert answer["response"]
        assert answer["status"] == "success"
        assert count_words(answer["response"]) <= MAX_RESPONSE_WORDS
        assert "usage" in answer
        assert answer["usage"]["messages_used"] >= 1

    def test_stream_research_stages_for_web_question(self, client):
        mock_manager = MagicMock()
        mock_manager.generate_chat.return_value = "Margins fell on pricing pressure. [S1]"
        mock_manager.get_status.return_value = {"active_provider": "test_model",
                                                "providers": []}
        with (_mock_auth(),
              patch("app.get_manager", return_value=mock_manager),
              patch("app.run_web_research", return_value=_fake_web_research()),
              patch("app._build_session_context",
                    return_value=("Company: Tesla (TSLA)\nrevenue: $22.5B", "Tesla"))):
            resp = client.post(
                "/api/chat/stream",
                json={"message": "Why did Tesla's margins fall?",
                      "history": [], "session_id": "some_session"},
                headers=_auth_headers(), content_type="application/json",
            )
            raw = resp.get_data(as_text=True)
        frames = _parse_frames(raw)
        events = [f["event"] for f in frames]
        stages = [f.get("stage") for f in frames if f["event"] == "status"]
        assert "internal" in stages
        assert "searching" in stages
        assert "comparing" in stages
        answer = frames[-1]
        assert answer["event"] == "answer"
        assert answer["sources"], "source cards must be returned"
        assert answer["research"]["performed"] is True
        assert answer["research"]["mode"] == "INTERNAL_DATA_PLUS_WEB_RESEARCH"
        assert answer["research"]["num_queries"] >= 1
        # internal context + external evidence must reach the LLM prompt
        system_msg = mock_manager.generate_chat.call_args[0][0][0]["content"]
        assert "RESEARCH DATA" in system_msg
        assert "Tesla" in system_msg
        assert "EXTERNAL RESEARCH" in system_msg
        assert "reuters.com" in system_msg
        assert "HARD LIMIT" in system_msg

    def test_stream_llm_failure_emits_error_event(self, client):
        mock_manager = MagicMock()
        mock_manager.generate_chat.side_effect = RuntimeError("All providers exhausted")
        with _mock_auth(), patch("app.get_manager", return_value=mock_manager):
            resp = client.post(
                "/api/chat/stream",
                json={"message": "Hello there friend", "history": []},
                headers=_auth_headers(), content_type="application/json",
            )
            raw = resp.get_data(as_text=True)
        frames = _parse_frames(raw)
        assert frames[-1]["event"] == "error"
        assert "temporarily unable" in frames[-1]["error"].lower()
        assert "traceback" not in json.dumps(frames).lower()

    def test_stream_research_failure_still_answers(self, client):
        with (_mock_auth(),
              _mock_generate("Answering from internal knowledge."),
              patch("app.run_web_research",
                    side_effect=RuntimeError("provider down"))):
            resp = client.post(
                "/api/chat/stream",
                json={"message": "Why are chip stocks falling?", "history": []},
                headers=_auth_headers(), content_type="application/json",
            )
            raw = resp.get_data(as_text=True)
        frames = _parse_frames(raw)
        assert frames[-1]["event"] == "answer"
        assert frames[-1]["research"]["degraded"] is True


# ═════════════════════════════════════════════════════════════════════════════
# JSON endpoints (spec PARTS 16, 44, 59)
# ═════════════════════════════════════════════════════════════════════════════

class TestAnswerContract:
    def test_answer_never_exceeds_300_words(self, client):
        long_text = ("Tesla revenue grew to $22.5 billion, up three percent "
                     "year over year, driven by energy storage. ") * 30
        with _mock_auth(), _mock_generate(long_text):
            resp = client.post(
                "/api/chat",
                json={"message": "Summarize Tesla"},
                headers=_auth_headers(), content_type="application/json",
            )
        data = resp.get_json()
        assert resp.status_code == 200
        assert count_words(data["response"]) <= MAX_RESPONSE_WORDS
        assert data["response_compressed"] is True
        assert data["word_count"] <= MAX_RESPONSE_WORDS

    def test_web_research_answer_includes_sources_and_metrics(self, client):
        with (_mock_auth(),
              _mock_generate("Margins fell on pricing pressure. [S1]"),
              patch("app.run_web_research", return_value=_fake_web_research())):
            resp = client.post(
                "/api/chat",
                json={"message": "Why did Tesla's margins fall?"},
                headers=_auth_headers(), content_type="application/json",
            )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["sources"][0]["url"].startswith("https://")
        research = data["research"]
        assert research["performed"] is True
        for key in ("mode", "num_queries", "num_sources_used", "search_ms",
                    "fetch_ms", "context_build_ms", "llm_ms", "total_ms",
                    "degraded"):
            assert key in research, f"missing metric {key}"
        assert data["usage"]["messages_limit"] == 25
        assert data["usage"]["words_limit"] == 7500

    def test_internal_only_skips_web_research(self, client):
        with (_mock_auth(), _mock_generate("Revenue was $22.5B."),
              patch("app.run_web_research") as research_mock):
            resp = client.post(
                "/api/chat",
                json={"message": "What was revenue?"},
                headers=_auth_headers(), content_type="application/json",
            )
        data = resp.get_json()
        assert resp.status_code == 200
        # definition/metric question without recency → no web research
        research_mock.assert_not_called()
        assert data["research"]["performed"] is False


# ═════════════════════════════════════════════════════════════════════════════
# Quota API + enforcement (spec PARTS 49-58)
# ═════════════════════════════════════════════════════════════════════════════

class TestQuotaEnforcement:
    def test_usage_endpoint_shape(self, client):
        with _mock_auth():
            resp = client.get("/api/chat/usage", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.get_json()
        for key in ("messages_used", "messages_limit", "words_used",
                    "words_limit", "messages_remaining", "words_remaining",
                    "reset_at"):
            assert key in data, f"missing {key}"
        assert data["messages_limit"] == 25
        assert data["words_limit"] == 7500

    def test_usage_endpoint_requires_auth(self, client):
        resp = client.get("/api/chat/usage")
        assert resp.status_code == 401

    def test_message_limit_rejected_server_side(self, client):
        for _ in range(25):
            cu.reserve_message(USER_ID, "x")
        with _mock_auth(), _mock_generate("should not run") as mgr:
            resp = client.post(
                "/api/chat",
                json={"message": "one more"},
                headers=_auth_headers(), content_type="application/json",
            )
        assert resp.status_code == 429
        data = resp.get_json()
        assert data["rate_limited"] is True
        assert data["reason"] == "message_limit"
        mgr.return_value.generate_chat.assert_not_called()

    def test_word_limit_rejected_server_side(self, client):
        cu.reserve_message(USER_ID, " ".join(["w"] * 7500))
        with _mock_auth(), _mock_generate("should not run") as mgr:
            resp = client.post(
                "/api/chat",
                json={"message": "hi"},
                headers=_auth_headers(), content_type="application/json",
            )
        assert resp.status_code == 429
        data = resp.get_json()
        assert data["reason"] == "word_limit"
        mgr.return_value.generate_chat.assert_not_called()

    def test_quota_survives_refresh_style_new_sessions(self, client):
        """Server state is authoritative — a fresh client session still 429s."""
        for _ in range(25):
            cu.reserve_message(USER_ID, "x")
        with _mock_auth(), _mock_generate("nope"):
            resp = client.post(
                "/api/chat/stream",
                json={"message": "hello"},
                headers=_auth_headers(), content_type="application/json",
            )
        assert resp.status_code == 429

    def test_rejection_payload_does_not_leak_internals(self, client):
        for _ in range(25):
            cu.reserve_message(USER_ID, "x")
        with _mock_auth(), _mock_generate("nope"):
            resp = client.post(
                "/api/chat",
                json={"message": "hello"},
                headers=_auth_headers(), content_type="application/json",
            )
        raw = resp.get_data(as_text=True).lower()
        assert "traceback" not in raw
        assert "api_key" not in raw
        assert "tavily" not in raw
