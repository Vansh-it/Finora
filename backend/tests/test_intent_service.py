"""Unit tests for the intent classification service.

Tests cover:
- Deterministic local classification (no LLM needed)
- LLM fallback for ambiguous prompts (mocked)
- Timeout/failure handling
- Edge cases and JSON parsing
- Period mode extraction
- Confidence bounds

All LLM calls are mocked — tests run offline with zero API cost.
"""

from __future__ import annotations

import json
import time
from unittest.mock import patch

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.intent_service import (
    ChatResult,
    ResearchResult,
    _extract_json,
    _local_classify,
    _llm_classify,
    _extract_company,
    _extract_years,
    classify_intent,
)


# ═════════════════════════════════════════════════════════════════════════════
# Group 1: Local classification — Chat (no LLM needed)
# ═════════════════════════════════════════════════════════════════════════════

class TestLocalChatClassification:
    """Tests for prompts that classify deterministically as chat."""

    def test_hello(self):
        result = classify_intent("Hello")
        assert isinstance(result, ChatResult)
        assert result.intent == "chat"
        assert result.model_used == "local"

    def test_hi(self):
        result = classify_intent("hi")
        assert isinstance(result, ChatResult)
        assert result.intent == "chat"
        assert result.model_used == "local"

    def test_hey(self):
        result = classify_intent("hey")
        assert isinstance(result, ChatResult)
        assert result.model_used == "local"

    def test_thanks(self):
        result = classify_intent("Thanks!")
        assert isinstance(result, ChatResult)

    def test_good_morning(self):
        result = classify_intent("Good morning")
        assert isinstance(result, ChatResult)

    def test_how_are_you(self):
        result = classify_intent("How are you?")
        assert isinstance(result, ChatResult)

    def test_whats_up(self):
        result = classify_intent("What's up?")
        assert isinstance(result, ChatResult)

    def test_empty_prompt(self):
        result = classify_intent("")
        assert isinstance(result, ChatResult)
        assert result.confidence == 1.0

    def test_weather_question(self):
        """Weather question without a company should be chat."""
        result = classify_intent("What's the weather like?")
        assert isinstance(result, ChatResult)

    def test_who_are_you(self):
        result = classify_intent("Who are you?")
        assert isinstance(result, ChatResult)

    def test_explain_roic(self):
        """'what is ROIC?' without a company context should be chat."""
        result = classify_intent("what is ROIC")
        assert isinstance(result, ChatResult)
        assert result.model_used == "local"

    def test_explain_ebitda(self):
        result = classify_intent("explain EBITDA")
        assert isinstance(result, ChatResult)

    def test_short_unknown_words(self):
        """Very short unknown text is likely chat."""
        result = classify_intent("cool stuff")
        assert isinstance(result, ChatResult)

    def test_joke_request(self):
        result = classify_intent("Tell me a joke")
        assert isinstance(result, ChatResult)


# ═════════════════════════════════════════════════════════════════════════════
# Group 2: Local classification — Research (no LLM needed)
# ═════════════════════════════════════════════════════════════════════════════

class TestLocalResearchClassification:
    """Tests for prompts that classify deterministically as research."""

    def test_research_microsoft(self):
        result = classify_intent("Research Microsoft")
        assert isinstance(result, ResearchResult)
        assert result.company == "Microsoft"
        assert result.period_mode == "latest"
        assert result.model_used == "local"

    def test_research_apple_fy2024(self):
        result = classify_intent("Research Apple FY2024")
        assert isinstance(result, ResearchResult)
        assert result.company == "Apple"
        assert result.period_mode == "specified"
        assert result.start_year == 2024
        assert result.end_year == 2024

    def test_analyze_nvidia(self):
        result = classify_intent("Analyze NVIDIA")
        assert isinstance(result, ResearchResult)
        assert result.company == "NVIDIA"

    def test_msft_financials(self):
        result = classify_intent("MSFT financials")
        assert isinstance(result, ResearchResult)
        assert result.company == "Microsoft"

    def test_build_dashboard_amazon(self):
        result = classify_intent("Build a dashboard for Amazon")
        assert isinstance(result, ResearchResult)
        assert result.company == "Amazon"

    def test_research_jpmorgan_latest(self):
        result = classify_intent("Research JPMorgan latest")
        assert isinstance(result, ResearchResult)
        assert result.company == "JPMorgan Chase"

    def test_get_apple_financials(self):
        result = classify_intent("Get Apple financials")
        assert isinstance(result, ResearchResult)
        assert result.company == "Apple"

    def test_research_microsoft_range(self):
        result = classify_intent("Research Microsoft FY2023-FY2025")
        assert isinstance(result, ResearchResult)
        assert result.company == "Microsoft"
        assert result.period_mode == "specified"
        assert result.start_year == 2023
        assert result.end_year == 2025

    def test_ticker_only(self):
        """A ticker symbol alone should be classified as research."""
        result = classify_intent("AAPL")
        assert isinstance(result, ResearchResult)
        assert result.company == "Apple"

    def test_company_name_only(self):
        """A company name alone should be classified as research."""
        result = classify_intent("Tesla")
        assert isinstance(result, ResearchResult)
        assert result.company == "Tesla"

    def test_show_google_revenue(self):
        result = classify_intent("Show Google revenue")
        assert isinstance(result, ResearchResult)
        assert result.company == "Alphabet"

    def test_evaluate_salesforce(self):
        result = classify_intent("Evaluate Salesforce")
        assert isinstance(result, ResearchResult)
        assert result.company == "Salesforce"


# ═════════════════════════════════════════════════════════════════════════════
# Group 3: Period extraction
# ═════════════════════════════════════════════════════════════════════════════

class TestPeriodExtraction:

    def test_single_year_fy(self):
        sy, ey, mode = _extract_years("FY2023")
        assert sy == 2023
        assert ey == 2023
        assert mode == "specified"

    def test_year_range(self):
        sy, ey, mode = _extract_years("2022-2024")
        assert sy == 2022
        assert ey == 2024
        assert mode == "specified"

    def test_en_dash_range(self):
        sy, ey, mode = _extract_years("FY2020\u2013FY2023")
        assert sy == 2020
        assert ey == 2023

    def test_no_years(self):
        sy, ey, mode = _extract_years("Research Microsoft")
        assert sy is None
        assert ey is None
        assert mode == "latest"


# ═════════════════════════════════════════════════════════════════════════════
# Group 4: Company extraction
# ═════════════════════════════════════════════════════════════════════════════

class TestCompanyExtraction:

    def test_known_ticker(self):
        name, _ = _extract_company("NVDA")
        assert name == "NVIDIA"

    def test_known_name(self):
        name, _ = _extract_company("research Microsoft")
        assert name == "Microsoft"

    def test_unknown_company_fallback(self):
        name, raw = _extract_company("Research Acme Corp")
        # Should extract "acme corp" as company
        assert "acme" in name.lower() or "acme" in raw.lower()

    def test_case_insensitive(self):
        name, _ = _extract_company("research apple")
        assert name == "Apple"


# ═════════════════════════════════════════════════════════════════════════════
# Group 5: LLM fallback (mocked)
# ═════════════════════════════════════════════════════════════════════════════

class TestLLMFallback:
    """Tests for prompts that need the LLM, with mocked LLM calls."""

    def test_ambiguous_prompt_uses_llm(self):
        """An ambiguous prompt should call the LLM when local fails."""
        mock_response = json.dumps({"intent": "chat", "confidence": 0.85})
        with patch("lib.provider_manager.generate_text", return_value=mock_response):
            with patch("lib.intent_service._local_classify", return_value=None):
                result = classify_intent("totally ambiguous prompt xyz123")
                assert isinstance(result, ChatResult)
                assert result.model_used == "nemotron"

    def test_llm_returns_research(self):
        mock_response = json.dumps({
            "intent": "research", "company": "Meta",
            "period_mode": "latest", "start_year": None, "end_year": None,
            "objective": "analysis", "confidence": 0.90,
        })
        with patch("lib.provider_manager.generate_text", return_value=mock_response):
            with patch("lib.intent_service._local_classify", return_value=None):
                result = classify_intent("do something with Meta platforms")
                assert isinstance(result, ResearchResult)
                assert result.company == "Meta"

    def test_llm_malformed_returns_fallback(self):
        """Malformed LLM output should fall back to local classification."""
        with patch("lib.provider_manager.generate_text", return_value="not valid json at all"):
            result = classify_intent("Research Apple")
            # Should still get local classification (Apple is known)
            assert isinstance(result, ResearchResult)
            assert result.company == "Apple"


# ═════════════════════════════════════════════════════════════════════════════
# Group 6: Timeout handling
# ═════════════════════════════════════════════════════════════════════════════

class TestTimeoutHandling:

    def test_llm_timeout_returns_none(self):
        """LLM timeout should return None, not hang."""
        def slow_generate(prompt):
            time.sleep(10)
            return '{"intent":"chat"}'

        with patch("lib.provider_manager.generate_text", side_effect=slow_generate):
            start = time.time()
            result = _llm_classify("totally ambiguous text here", timeout=0.5)
            elapsed = time.time() - start
            assert result is None
            assert elapsed < 2.0

    def test_llm_429_returns_none(self):
        """Rate-limited LLM should return None gracefully."""
        with patch("lib.provider_manager.generate_text", side_effect=RuntimeError("429 rate limit")):
            result = _llm_classify("ambiguous", timeout=5)
            assert result is None

    def test_llm_timeout_falls_back_to_local(self):
        """Full classify_intent should still work after LLM timeout."""
        def slow_generate(prompt):
            time.sleep(10)
            return '{"intent":"chat"}'

        with patch("lib.provider_manager.generate_text", side_effect=slow_generate):
            start = time.time()
            result = classify_intent("Research Tesla")
            elapsed = time.time() - start
            assert isinstance(result, ResearchResult)
            assert result.company == "Tesla"
            assert elapsed < 2.0

    def test_classification_never_waits_indefinitely(self):
        """Even with a very slow LLM, local classification should be instant."""
        def infinite_wait(prompt):
            time.sleep(3600)
            return '{"intent":"chat"}'

        with patch("lib.provider_manager.generate_text", side_effect=infinite_wait):
            start = time.time()
            result = classify_intent("hello")
            elapsed = time.time() - start
            assert isinstance(result, ChatResult)
            assert elapsed < 0.5


# ═════════════════════════════════════════════════════════════════════════════
# Group 7: JSON parsing edge cases
# ═════════════════════════════════════════════════════════════════════════════

class TestJsonParsing:

    def test_markdown_fences(self):
        raw = '```json\n{"intent":"chat","confidence":0.99}\n```'
        parsed = _extract_json(raw)
        assert parsed["intent"] == "chat"

    def test_trailing_comma(self):
        raw = '{"intent":"research","company":"Apple",}'
        parsed = _extract_json(raw)
        assert parsed["company"] == "Apple"

    def test_surrounding_text(self):
        raw = 'Classification: {"intent":"chat","confidence":0.90} — done.'
        parsed = _extract_json(raw)
        assert parsed["intent"] == "chat"

    def test_completely_invalid(self):
        with pytest.raises(ValueError):
            _extract_json("this is not json at all")


# ═════════════════════════════════════════════════════════════════════════════
# Group 8: Result serialization & bounds
# ═════════════════════════════════════════════════════════════════════════════

class TestResultSerialization:

    def test_chat_result_to_dict(self):
        r = ChatResult(confidence=0.85)
        d = r.to_dict()
        assert d["intent"] == "chat"
        assert d["confidence"] == 0.85

    def test_research_result_to_dict(self):
        r = ResearchResult(
            company="Microsoft",
            period_mode="specified",
            start_year=2024,
            end_year=2025,
            objective="financial research",
            confidence=0.95,
        )
        d = r.to_dict()
        assert d["intent"] == "research"
        assert d["company"] == "Microsoft"
        assert d["period_mode"] == "specified"
        assert d["start_year"] == 2024
        assert d["end_year"] == 2025

    def test_research_result_with_none_years(self):
        r = ResearchResult(company="NVIDIA", period_mode="latest")
        d = r.to_dict()
        assert d["start_year"] is None
        assert d["end_year"] is None


# ═════════════════════════════════════════════════════════════════════════════
# Group 9: Specific requirements from the task
# ═════════════════════════════════════════════════════════════════════════════

class TestSpecificRequirements:
    """Tests matching the exact requirements from the task prompt."""

    def test_research_microsoft_no_llm(self):
        """Research Microsoft -> research without LLM."""
        result = classify_intent("Research Microsoft")
        assert isinstance(result, ResearchResult)
        assert result.company == "Microsoft"
        assert result.model_used == "local"

    def test_msft_financial_research_no_llm(self):
        """MSFT financial research -> research without LLM."""
        result = classify_intent("MSFT financial research")
        assert isinstance(result, ResearchResult)
        assert result.company == "Microsoft"

    def test_analyze_apple_fy2024_no_llm(self):
        """Analyze Apple FY2024 -> research without LLM."""
        result = classify_intent("Analyze Apple FY2024")
        assert isinstance(result, ResearchResult)
        assert result.company == "Apple"
        assert result.period_mode == "specified"
        assert result.start_year == 2024

    def test_hi_no_llm(self):
        """hi -> chat without LLM."""
        result = classify_intent("hi")
        assert isinstance(result, ChatResult)
        assert result.model_used == "local"

    def test_what_is_roic_no_llm(self):
        """what is ROIC? -> chat without LLM."""
        result = classify_intent("what is ROIC?")
        assert isinstance(result, ChatResult)

    def test_classification_speed(self):
        """Classification of obvious prompts should be well under 1 second."""
        prompts = [
            "Research Microsoft",
            "hi",
            "Analyze Apple FY2024",
            "what is ROIC?",
            "MSFT",
            "Research JPMorgan latest",
        ]
        start = time.time()
        for _ in range(100):
            for p in prompts:
                classify_intent(p)
        elapsed = time.time() - start
        # 600 classifications should take well under 1 second
        assert elapsed < 1.0, f"600 classifications took {elapsed:.2f}s"

    def test_nemotron_timeout_fallback(self):
        """When Nemotron times out, deterministic fallback should work."""
        def slow(prompt):
            time.sleep(10)
            return '{"intent":"chat"}'

        with patch("lib.provider_manager.generate_text", side_effect=slow):
            result = classify_intent("Research NVIDIA")
            assert isinstance(result, ResearchResult)
            assert result.company == "NVIDIA"

    def test_nemotron_429_fallback(self):
        """When Nemotron returns 429, should fall back gracefully."""
        with patch("lib.provider_manager.generate_text", side_effect=RuntimeError("429")):
            result = classify_intent("Research Apple")
            assert isinstance(result, ResearchResult)
            assert result.company == "Apple"

    def test_malformed_llm_response_fallback(self):
        """When LLM returns garbage, should fall back gracefully."""
        with patch("lib.provider_manager.generate_text", return_value="I'm not a JSON engine"):
            result = classify_intent("Research Microsoft")
            assert isinstance(result, ResearchResult)
            assert result.company == "Microsoft"

    def test_classification_never_waits_indefinitely_final(self):
        """Classification must never hang — must complete in < 2s even with broken LLM."""
        def infinite(prompt):
            time.sleep(3600)
            return '{"intent":"chat"}'

        with patch("lib.provider_manager.generate_text", side_effect=infinite):
            start = time.time()
            result = classify_intent("hello")
            elapsed = time.time() - start
            assert isinstance(result, ChatResult)
            assert elapsed < 2.0
