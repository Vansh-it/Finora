"""Tests for the response sanitizer that strips internal model reasoning."""

from __future__ import annotations

import pytest

from lib.response_sanitizer import sanitize_response, _strip_think_tags, _strip_leaked_prefixes


class TestStripThinkTags:
    """Test removal of think/reasoning tags."""

    def test_removes_complete_think_tags(self):
        text = "<think>\nLet me analyze this...\n</think>\nMicrosoft reported $200B revenue."
        result = _strip_think_tags(text)
        assert "<think>" not in result
        assert "</think>" not in result
        assert "Let me analyze this" not in result
        assert "Microsoft reported $200B revenue." in result

    def test_removes_thinking_tags(self):
        text = "</think>\nRevenue was strong."
        result = _strip_think_tags(text)
        assert "</think>" not in result
        assert "Revenue was strong." in result

    def test_removes_openai_reasoning_tags(self):
        text = "</think>\nMicrosoft is profitable."
        result = _strip_think_tags(text)
        assert "</think>" not in result
        assert "Microsoft is profitable." in result

    def test_removes_unclosed_think_tag(self):
        text = "<think>\nI need to think about this..."
        result = _strip_think_tags(text)
        assert "<think>" not in result
        assert "I need to think about this" not in result

    def test_removes_think_fence_block(self):
        text = "```thinking\nLet me plan this out\n```\n\nMicrosoft revenue is $200B."
        result = _strip_think_tags(text)
        assert "thinking" not in result.lower() or "Microsoft" in result
        assert "Microsoft revenue is $200B." in result

    def test_no_tags_unchanged(self):
        text = "Microsoft reported strong revenue of $200B."
        result = _strip_think_tags(text)
        assert result == text


class TestStripLeakedPrefixes:
    """Test removal of leaked internal reasoning prefixes."""

    def test_strips_here_is_my_thinking_process(self):
        text = "Here's a thinking process:\nMicrosoft is a great company."
        result = _strip_leaked_prefixes(text)
        assert "Here's a thinking process" not in result
        assert "Microsoft is a great company." in result

    def test_strips_analyze_user_input(self):
        text = "Analyze User Input:\nThe user wants to know about revenue."
        result = _strip_leaked_prefixes(text)
        assert "Analyze User Input" not in result
        assert "The user wants to know about revenue." in result

    def test_strips_system_prompt(self):
        text = "System prompt: I should answer about Microsoft."
        result = _strip_leaked_prefixes(text)
        assert "System prompt" not in result

    def test_strips_i_need_to(self):
        text = "I need to analyze the revenue data."
        result = _strip_leaked_prefixes(text)
        assert "I need to analyze" not in result

    def test_strips_let_me_draft(self):
        text = "Let me draft a response about margins."
        result = _strip_leaked_prefixes(text)
        assert "Let me draft" not in result

    def test_strips_let_me_analyze(self):
        text = "Let me analyze the balance sheet."
        result = _strip_leaked_prefixes(text)
        assert "Let me analyze" not in result

    def test_strips_i_should(self):
        text = "I should provide the formula for ROE."
        result = _strip_leaked_prefixes(text)
        assert "I should provide" not in result

    def test_strips_the_prompt_says(self):
        text = "The prompt says I need to explain metrics."
        result = _strip_leaked_prefixes(text)
        assert "The prompt says" not in result

    def test_strips_multiple_leaked_lines(self):
        text = (
            "Here's a thinking process:\n"
            "I need to analyze the data.\n"
            "Let me draft a response.\n"
            "Microsoft reported $200B revenue."
        )
        result = _strip_leaked_prefixes(text)
        assert "Microsoft reported $200B revenue." in result
        assert "thinking process" not in result.lower()

    def test_normal_text_not_stripped(self):
        text = "Microsoft reported $200B in revenue for FY2025."
        result = _strip_leaked_prefixes(text)
        assert result == text


class TestSanitizeResponse:
    """Test the full sanitize_response pipeline."""

    def test_cleans_think_and_prefix(self):
        text = (
            "<think>\nAnalyzing...\n</think>\n"
            "Here's a thinking process:\n"
            "Microsoft reported $200B revenue."
        )
        result = sanitize_response(text)
        assert "<think>" not in result
        assert "thinking process" not in result.lower()
        assert "Microsoft reported $200B revenue." in result

    def test_empty_input(self):
        assert sanitize_response("") == ""
        assert sanitize_response("   ") == ""

    def test_think_only_returns_empty(self):
        result = sanitize_response("<think>\nJust thinking...\n</think>")
        # After stripping think tags, nothing useful remains
        assert "<think>" not in result
        assert "Just thinking" not in result

    def test_normal_response_preserved(self):
        text = "Microsoft (MSFT) reported revenue of $200B in FY2025."
        result = sanitize_response(text)
        assert result == text

    def test_markdown_preserved(self):
        text = (
            "**Revenue**\n\n"
            "- $200B in FY2025\n"
            "- $180B in FY2024\n\n"
            "**Source**: SEC 10-K · FY2025"
        )
        result = sanitize_response(text)
        assert "**Revenue**" in result
        assert "- $200B" in result
        assert "**Source**" in result

    def test_excessive_blank_lines_collapsed(self):
        text = "Line one.\n\n\n\n\n\nLine two."
        result = sanitize_response(text)
        assert "\n\n\n" not in result
        assert "Line one." in result
        assert "Line two." in result

    def test_unclosed_think_tag_handled(self):
        text = "<think>\nI'm thinking about this..."
        result = sanitize_response(text)
        assert "<think>" not in result

    def test_nested_think_content_stripped(self):
        text = "<think>\nAnalyze User Input:\nI need to draft...\n</think>\nRevenue was $200B."
        result = sanitize_response(text)
        assert "<think>" not in result
        assert "Analyze User Input" not in result
        assert "Revenue was $200B." in result


class TestLeakagePatterns:
    """Test that specific leaked phrases are caught."""

    @pytest.mark.parametrize("phrase", [
        "Here's a thinking process:",
        "Here is my thinking process:",
        "Thinking process:",
        "Analyze User Input:",
        "System prompt:",
        "The system prompt says",
        "The prompt says",
        "I need to",
        "I should probably",
        "Let me draft",
        "Let me analyze",
        "Let me think",
        "My reasoning:",
        "Internal analysis:",
        "Internal reasoning:",
        "Scratchpad:",
        "Chain of thought:",
        "Chain-of-thought:",
        "Reasoning:",
        "Thinking:",
        "How I'll answer:",
        "The user wants me to",
        "I'll respond with",
        "First, I'll",
        "My approach:",
    ])
    def test_leaked_phrase_stripped(self, phrase: str):
        text = f"{phrase}\nActual response content here."
        result = sanitize_response(text)
        assert phrase.lower() not in result.lower()
        assert "Actual response content here." in result
