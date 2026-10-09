"""Unit tests for the research agent: classification, planning, search,
dedup, tiering, freshness, evidence, and the 300-word response guard.

Covers spec PART 35 items: internal-only questions, web-research questions,
mixed questions, current/latest questions, search failure, partial failure,
duplicate sources, low-quality sources, stale information, empty results,
malformed URLs, SSRF attempts, and response compression/validation.
"""

from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lib.research_agent as ra
from lib.research_agent import (
    INTERNAL_DATA_ONLY,
    INTERNAL_PLUS_WEB,
    WEB_PRIMARY,
    GENERAL_FINANCE,
    classify_research_mode,
    needs_web_research,
    plan_queries,
    run_web_research,
    normalize_url,
    source_tier,
    is_time_sensitive,
    build_evidence_block,
    count_words,
    MAX_EVIDENCE_CHARS,
)
from lib.response_guard import (
    enforce_response_limit,
    validate_response,
    MAX_RESPONSE_WORDS,
)


# ═════════════════════════════════════════════════════════════════════════════
# Classification (spec PART 4)
# ═════════════════════════════════════════════════════════════════════════════

class TestClassification:
    def test_internal_only_metric_question(self):
        q = "What was Tesla's revenue last quarter?"
        assert classify_research_mode(q, has_internal_data=True) == INTERNAL_DATA_ONLY
        assert needs_web_research(INTERNAL_DATA_ONLY, q) is False

    def test_internal_only_eps_question(self):
        assert classify_research_mode(
            "What was diluted EPS?", has_internal_data=True
        ) == INTERNAL_DATA_ONLY

    def test_why_question_uses_internal_plus_web(self):
        q = "Why did Tesla's margins decline?"
        mode = classify_research_mode(q, has_internal_data=True)
        assert mode == INTERNAL_PLUS_WEB
        assert needs_web_research(mode, q) is True

    def test_latest_developments_needs_web(self):
        q = "What are the latest developments around Tesla?"
        mode = classify_research_mode(q, has_internal_data=True)
        assert mode == INTERNAL_PLUS_WEB
        assert needs_web_research(mode, q) is True

    def test_analyst_question_needs_web(self):
        q = "What are analysts currently saying about Tesla?"
        mode = classify_research_mode(q, has_internal_data=True)
        assert mode == INTERNAL_PLUS_WEB
        assert needs_web_research(mode, q) is True

    def test_risk_question_needs_web(self):
        q = "What are the main risks facing Tesla?"
        mode = classify_research_mode(q, has_internal_data=True)
        assert mode == INTERNAL_PLUS_WEB

    def test_general_finance_without_company(self):
        q = "Explain the current interest-rate environment."
        assert classify_research_mode(q, has_internal_data=False) == GENERAL_FINANCE
        assert needs_web_research(GENERAL_FINANCE, q) is True

    def test_general_concept_definition_skips_web(self):
        q = "What is EV/EBITDA?"
        mode = classify_research_mode(q, has_internal_data=False)
        assert mode == GENERAL_FINANCE
        assert needs_web_research(mode, q) is False

    def test_chit_chat_skips_web(self):
        assert needs_web_research(GENERAL_FINANCE, "Hi") is False

    def test_followup_inherits_previous_mode(self):
        assert classify_research_mode(
            "Why?", has_internal_data=True, previous_mode=INTERNAL_DATA_ONLY
        ) == INTERNAL_PLUS_WEB

    def test_followup_keeps_web_mode(self):
        assert classify_research_mode(
            "What about margins?", has_internal_data=True,
            previous_mode=INTERNAL_PLUS_WEB,
        ) == INTERNAL_PLUS_WEB

    def test_historical_question_not_time_sensitive(self):
        assert is_time_sensitive("What was revenue in FY2019?") is False

    def test_freshness_keywords_detected(self):
        for q in ("What is the latest news?", "What happened today?",
                  "current outlook", "recent developments"):
            assert is_time_sensitive(q) is True, q


# ═════════════════════════════════════════════════════════════════════════════
# Query decomposition (spec PART 5)
# ═════════════════════════════════════════════════════════════════════════════

class TestQueryPlanning:
    def test_internal_only_yields_zero_queries(self):
        assert plan_queries("What was revenue?", company="Tesla",
                            mode=INTERNAL_DATA_ONLY) == []

    def test_company_queries_include_company(self):
        queries = plan_queries(
            "Why did Tesla's margins fall and what are analysts saying about it?",
            company="Tesla", mode=INTERNAL_PLUS_WEB,
        )
        assert queries
        assert all("Tesla" in q for q in queries)
        assert len(queries) <= 4
        assert any("analyst" in q for q in queries)

    def test_simple_question_gets_few_queries(self):
        queries = plan_queries("Why did revenue fall?", company="Tesla",
                               mode=INTERNAL_PLUS_WEB)
        assert 1 <= len(queries) <= 2

    def test_queries_are_deduplicated(self):
        queries = plan_queries("latest news", company="Tesla", mode=WEB_PRIMARY)
        lowered = [q.lower().strip() for q in queries]
        assert len(lowered) == len(set(lowered))

    def test_general_research_query(self):
        queries = plan_queries("Why are semiconductor stocks falling?", mode=GENERAL_FINANCE)
        assert len(queries) >= 1
        assert "semiconductor" in queries[0]


# ═════════════════════════════════════════════════════════════════════════════
# URLs, tiers, dedup (spec PARTS 8-9)
# ═════════════════════════════════════════════════════════════════════════════

class TestSourceQuality:
    def test_normalize_url_strips_tracking(self):
        a = normalize_url("https://www.reuters.com/a?utm_source=x&utm_campaign=y&fbclid=zz")
        b = normalize_url("https://reuters.com/a")
        assert a == b

    def test_tier1_sec(self):
        assert source_tier("https://www.sec.gov/Archives/xyz") == 1

    def test_tier1_gov(self):
        assert source_tier("https://www.federalreserve.gov/foo") == 1

    def test_tier1_ir_subdomain(self):
        assert source_tier("https://ir.tesla.com/news") == 1

    def test_tier2_major_press(self):
        assert source_tier("https://www.reuters.com/business") == 2
        assert source_tier("https://www.cnbc.com/x") == 2

    def test_tier3_default(self):
        assert source_tier("https://random-blog.example/post") == 3

    def test_content_farm_not_promoted(self):
        assert source_tier("https://www.pinterest.com/pin/1") == 3


def _fake_results():
    return [
        {"query": "q", "title": "Tesla cuts prices", "url":
         "https://www.reuters.com/auto/a?utm_source=feed", "snippet": "Tesla cut prices",
         "published_at": "2026-10-01", "score": 0.9},
        {"query": "q2", "title": "Tesla cuts prices", "url":
         "https://www.reuters.com/auto/a", "snippet": "duplicate story",
         "published_at": "2026-10-01", "score": 0.8},
        {"query": "q3", "title": "Tesla trims vehicle prices", "url":
         "https://www.reuters.com/auto/a/", "snippet": "syndicated",
         "published_at": "", "score": 0.7},
        {"query": "q4", "title": "TESLA PRICE CUTS!!", "url":
         "https://spam.example.io/tesla", "snippet": "seo spam",
         "published_at": "", "score": 0.99},
        {"query": "q5", "title": "Tesla Form 10-Q", "url":
         "https://www.sec.gov/Archives/tesla-10q", "snippet": "filing",
         "published_at": "2026-08-01", "score": 0.5},
    ]


class TestDedupAndRanking:
    @pytest.fixture(autouse=True)
    def _patch_search(self, monkeypatch):
        results = _fake_results()

        def fake_search(query, max_results=5):
            return {"results": results}

        monkeypatch.setattr(ra, "_run_search", fake_search)
        monkeypatch.setattr(
            ra, "_fetch_content",
            lambda url: {"status": "error", "content": ""},
        )

    def test_duplicates_and_syndication_removed(self):
        out = run_web_research("Why did Tesla cut prices?",
                               company="Tesla", queries=["Tesla prices"])
        urls = [s["url"] for s in out["sources"]]
        # utm variant, trailing slash, www variant all collapse
        assert len([u for u in urls if "reuters.com/auto/a" in u]) == 1

    def test_official_source_ranks_first(self):
        out = run_web_research("Tesla filing facts", company="Tesla",
                               queries=["Tesla filing"])
        assert out["sources"], "expected sources"
        assert out["sources"][0]["tier"] == "official"

    def test_partial_failure_still_returns_evidence(self, monkeypatch):
        calls = {"n": 0}

        def flaky(query, max_results=5):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("Tavily HTTP 429")
            return {"results": _fake_results()}

        monkeypatch.setattr(ra, "_run_search", flaky)
        out = run_web_research("Why did Tesla cut prices?", company="Tesla",
                               queries=["one", "two"])
        assert out["degraded"] is False
        assert out["partially_degraded"] is True
        assert out["sources"]
        assert out["errors"]

    def test_total_search_failure_degrades_gracefully(self, monkeypatch):
        def boom(query, max_results=5):
            raise RuntimeError("Tavily request failed")

        monkeypatch.setattr(ra, "_run_search", boom)
        out = run_web_research("latest Tesla news", company="Tesla",
                               queries=["one", "two"])
        assert out["degraded"] is True
        assert out["evidence"] == []
        assert out["errors"]

    def test_empty_results_not_degraded(self, monkeypatch):
        monkeypatch.setattr(ra, "_run_search",
                            lambda q, max_results=5: {"results": []})
        out = run_web_research("latest Tesla news", company="Tesla",
                               queries=["nothing"])
        assert out["degraded"] is False
        assert out["sources"] == []
        assert out["counts"]["results"] == 0


class TestMalformedUrls:
    def test_bad_urls_dropped(self):
        resp = {"results": [
            {"title": "no url", "url": "", "content": "x"},
            {"title": "ftp", "url": "ftp://example.com/f", "content": "x"},
            {"title": "javascript", "url": "javascript:alert(1)", "content": "x"},
            {"title": "ok", "url": "https://example.com/a", "content": "x"},
        ]}
        flat = ra._flatten_results("q", resp)
        assert len(flat) == 1
        assert flat[0]["url"].startswith("https://")


class TestSsrfGuard:
    def test_private_ip_fetch_blocked(self):
        res = ra._fetch_content("http://127.0.0.1/admin")
        assert res["status"] == "blocked"

    def test_metadata_ip_fetch_blocked(self):
        res = ra._fetch_content("http://169.254.169.254/latest/meta-data")
        assert res["status"] == "blocked"


# ═════════════════════════════════════════════════════════════════════════════
# Freshness (spec PART 11)
# ═════════════════════════════════════════════════════════════════════════════

class TestFreshness:
    def test_fresh_sources_beat_stale_for_recent_queries(self, monkeypatch):
        results = [
            {"query": "q", "title": "Old story", "url": "https://reuters.com/old",
             "snippet": "old", "published_at": "2024-01-01", "score": 0.9},
            {"query": "q", "title": "Fresh story", "url": "https://reuters.com/new",
             "snippet": "new", "published_at": "2026-10-06", "score": 0.5},
        ]
        monkeypatch.setattr(ra, "_run_search",
                            lambda q, max_results=5: {"results": results})
        monkeypatch.setattr(ra, "_fetch_content",
                            lambda url: {"status": "error", "content": ""})
        out = run_web_research("What is the latest Tesla news?",
                               company="Tesla", queries=["Tesla news"],
                               time_sensitive=True)
        assert out["sources"][0]["url"].endswith("/new")

    def test_unknown_date_penalised_for_fresh_queries(self):
        now = 1_700_000_000.0
        a = {"url": "https://x.com/a", "title": "a", "snippet": "", "published_at": ""}
        b = {"url": "https://x.com/b", "title": "b", "snippet": "",
             "published_at": "2026-10-01"}
        ranked = ra._rank([dict(a), dict(b)], "latest news", True)
        assert ranked[0]["url"].endswith("/b")


# ═════════════════════════════════════════════════════════════════════════════
# Evidence (spec PART 14)
# ═════════════════════════════════════════════════════════════════════════════

class TestEvidence:
    def test_evidence_shape(self, monkeypatch):
        monkeypatch.setattr(ra, "_run_search", lambda q, max_results=5: {
            "results": [{"query": "q", "title": "T", "url": "https://www.sec.gov/x",
                         "snippet": "content here", "published_at": "2026-10-01"}]
        })
        monkeypatch.setattr(ra, "_fetch_content",
                            lambda url: {"status": "error", "content": ""})
        out = run_web_research("Tesla filing facts", queries=["q"])
        ev = out["evidence"][0]
        for key in ("source_type", "title", "url", "publisher", "published_at",
                    "retrieved_at", "relevance_score", "credibility_score", "content"):
            assert key in ev, f"missing {key}"
        assert ev["source_type"] in ("sec", "company", "news", "web", "finora_internal")

    def test_evidence_block_size_capped(self):
        evidence = [
            {"source_type": "web", "title": f"T{i}", "url": f"https://e.com/{i}",
             "publisher": "e.com", "published_at": "", "content": "word " * 3000}
            for i in range(10)
        ]
        block = build_evidence_block(evidence)
        assert len(block) < MAX_EVIDENCE_CHARS + 500
        assert "untrusted" in block.lower()

    def test_empty_evidence_block(self):
        assert build_evidence_block([]) == ""


# ═════════════════════════════════════════════════════════════════════════════
# Response guard (spec PARTS 44-46, 59-61)
# ═════════════════════════════════════════════════════════════════════════════

LONG_ANSWER = (
    "## Bottom line\n\n"
    "Tesla's gross margin fell 240bps to 17.4% as pricing pressure and mix shift "
    "weighed on automotive gross margin. [S1]\n\n"
    + "The company faced pricing pressure across markets and mix shift toward "
      "cheaper models affecting blended margins. " * 30
    + "\n## What matters\n\n- Pricing pressure\n- Mix shift\n- Cost reductions\n"
    "\n## Sources\n\n• Reuters — Tesla demand outlook\n• Tesla IR — Quarterly results\n"
    "• SEC — 10-Q filing"
)


class TestResponseGuard:
    def test_short_answer_untouched(self):
        out = enforce_response_limit("Revenue was $22.5B, up 3% YoY.")
        assert out["text"] == "Revenue was $22.5B, up 3% YoY."
        assert out["compressed"] is False

    def test_long_answer_compressed_to_limit(self):
        out = enforce_response_limit(LONG_ANSWER)
        assert out["compressed"] is True
        assert out["word_count"] <= MAX_RESPONSE_WORDS
        assert out["issues"] == []

    def test_compression_is_not_truncation(self):
        out = enforce_response_limit(LONG_ANSWER)
        text = out["text"]
        # ends with a real sentence / list entry, not a mid-word cut
        assert text.rstrip()[-1] not in "-–|*#"
        # key structures survive
        assert "##" in text
        assert "Sources" in text
        # no unfinished bold
        assert text.count("**") % 2 == 0

    def test_sources_preserved_when_compressed(self):
        out = enforce_response_limit(LONG_ANSWER)
        assert "Reuters" in out["text"]

    def test_validate_ok_for_normal_answer(self):
        res = validate_response("Tesla revenue grew 3% to $22.5B. [S1]")
        assert res["ok"] is True

    def test_validate_detects_api_key_leak(self):
        res = validate_response("key is nvapi-abc123xyz789")
        assert res["ok"] is False
        assert any(i.startswith("leak:") for i in res["issues"])

    def test_validate_detects_traceback(self):
        res = validate_response("Traceback (most recent call last): boom")
        assert res["ok"] is False

    def test_validate_detects_raw_context(self):
        res = validate_response("--- EXTERNAL RESEARCH ---\nstuff")
        assert res["ok"] is False

    def test_validate_detects_over_limit(self):
        res = validate_response("word " * 400)
        assert res["ok"] is False
        assert any("over_word_limit" in i for i in res["issues"])

    def test_unbalanced_fence_repaired(self):
        out = enforce_response_limit("```python\nprint(1)")
        assert out["text"].count("```") % 2 == 0

    def test_word_count_deterministic(self):
        assert count_words("a b  c") == 3
        assert count_words("") == 0
