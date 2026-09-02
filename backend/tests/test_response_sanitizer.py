"""Tests for response sanitizer — leak detection regression tests.

These tests verify that internal model reasoning is NEVER exposed to users.
Both Nemotron and Kimi adapter outputs are tested.
"""

from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.response_sanitizer import sanitize_response


# ═════════════════════════════════════════════════════════════════════════════
# Nemotron-style numbered reasoning leakage
# ═════════════════════════════════════════════════════════════════════════════


class TestNemotronNumberedReasoning:
    """Test stripping of Nemotron-style numbered reasoning steps."""

    def test_full_numbered_reasoning_with_output_section(self):
        """Nemotron produces numbered steps with an Output section."""
        raw = (
            "1. **Analyze User Input:**\n"
            "The user is asking about the company's business model.\n\n"
            "2. **Check Provided Research Data:**\n"
            "The research context contains revenue, income, and metric data.\n\n"
            "3. **Determine Response Strategy:**\n"
            "I should explain the company's business in simple terms.\n\n"
            "4. **Draft Response:**\n"
            "Let me structure a clear answer.\n\n"
            "5. **Output:**\n"
            "Texas Instruments is a semiconductor company that designs and "
            "manufactures analog chips and embedded processors.\n\n"
            "**Financial picture**\n"
            "- Revenue: $17.7B\n"
            "- Net income: $5.0B"
        )
        result = sanitize_response(raw)
        assert "Texas Instruments is a semiconductor company" in result
        assert "Analyze User Input" not in result
        assert "Check Provided Research Data" not in result
        assert "Determine Response Strategy" not in result
        assert "Draft Response" not in result
        assert "Output:" not in result

    def test_numbered_reasoning_without_explicit_output(self):
        """Nemotron produces numbered steps without explicit Output section."""
        raw = (
            "1. **Analyze User Input:**\n"
            "The user wants to understand what this form does.\n\n"
            "2. **Check Provided Research Data:**\n"
            "The research context has financial data.\n\n"
            "3. **Wait...**\n"
            "I should clarify what the user means by 'form'.\n\n"
            "4. **I need to answer:**\n"
            "Let me re-read the question.\n\n"
            "5. **So I need to answer:**\n"
            "This dashboard form displays financial research data.\n\n"
            "Texas Instruments makes chips for electronics."
        )
        result = sanitize_response(raw)
        assert "Analyze User Input" not in result
        assert "Check Provided Research Data" not in result
        assert "Wait..." not in result
        assert "I need to answer" not in result
        assert "Let me re-read" not in result
        # The actual answer should survive
        assert "Texas Instruments makes chips" in result

    def test_two_steps_not_stripped(self):
        """Only 2 numbered steps should not trigger stripping."""
        raw = (
            "1. **Overview:**\n"
            "This is a semiconductor company.\n\n"
            "2. **Key metrics:**\n"
            "Revenue: $17.7B, Net income: $5.0B."
        )
        result = sanitize_response(raw)
        # Should keep the content since it's not predominantly reasoning
        assert "semiconductor company" in result
        assert "Revenue" in result

    def test_mixed_reasoning_and_answer(self):
        """Reasoning mixed with actual answer content."""
        raw = (
            "1. **Analyze User Input:** The user wants revenue data.\n"
            "2. **Check Research Data:** Revenue is available.\n"
            "3. **Response:** Texas Instruments reported $17.7B in revenue for FY2025.\n"
        )
        result = sanitize_response(raw)
        assert "17.7B" in result
        assert "Analyze User Input" not in result


# ═════════════════════════════════════════════════════════════════════════════
# Think/reasoning tags
# ═════════════════════════════════════════════════════════════════════════════


class TestThinkTags:
    """Test stripping of think/reasoning XML tags."""

    def test_think_tags(self):
        """<think>...</think> blocks should be removed."""
        raw = (
            "<think>\nThe user is asking about Texas Instruments. Let me look up the data.\n</think>\n"
            "Texas Instruments is a semiconductor company."
        )
        result = sanitize_response(raw)
        assert "<think>" not in result
        assert "let me look up" not in result.lower()
        assert "Texas Instruments is a semiconductor company" in result

    def test_unclosed_think_tag(self):
        """Unclosed <think> tag should be stripped."""
        raw = (
            "<think>\nThinking about the user's question...\n"
            "Texas Instruments makes chips."
        )
        result = sanitize_response(raw)
        assert "<think>" not in result
        assert "Thinking about" not in result

    def test_thinking_tags(self):
        """<think>...</think> tags should be removed."""
        raw = (
            "<think>\nLet me analyze this...\n</think>\n"
            "The answer is 42."
        )
        result = sanitize_response(raw)
        assert "<think>" not in result
        assert "The answer is 42" in result

    def test_reasoning_tags(self):
        """<reasoning>...</reasoning> tags should be removed."""
        raw = (
            "<reasoning>\nUser wants to know about revenue.\n</reasoning>\n"
            "Revenue was $17.7B."
        )
        result = sanitize_response(raw)
        assert "<reasoning>" not in result
        assert "Revenue was $17.7B" in result

    def test_reasoning_content_tags(self):
        """<reasoning_content>...</reasoning_content> tags should be removed."""
        raw = (
            "<reasoning_content>\nAnalyzing the question...\n</reasoning_content>\n"
            "The company reported strong earnings."
        )
        result = sanitize_response(raw)
        assert "reasoning_content" not in result
        assert "strong earnings" in result

    def test_analysis_tags(self):
        """<analysis>...</analysis> tags should be removed."""
        raw = (
            "<analysis>\nLet me think step by step...\n</analysis>\n"
            "Texas Instruments designs chips."
        )
        result = sanitize_response(raw)
        assert "<analysis>" not in result
        assert "Texas Instruments designs chips" in result

    def test_think_fence_blocks(self):
        """```thinking ... ``` blocks should be removed."""
        raw = (
            "```thinking\nLet me analyze this...\n```\n"
            "The answer is clear."
        )
        result = sanitize_response(raw)
        assert "```thinking" not in result
        assert "Let me analyze" not in result
        assert "The answer is clear" in result


# ═════════════════════════════════════════════════════════════════════════════
# Leaked prefix patterns
# ═════════════════════════════════════════════════════════════════════════════


class TestLeakedPrefixes:
    """Test stripping of leaked internal reasoning prefixes."""

    def test_analyze_user_input(self):
        """'Analyze User Input:' prefix should be stripped."""
        raw = "Analyze User Input:\nThe user wants to know about revenue.\n\nRevenue was $17.7B."
        result = sanitize_response(raw)
        assert "Analyze User Input" not in result
        assert "Revenue was $17.7B" in result

    def test_check_provided_research_data(self):
        """'Check Provided Research Data:' prefix should be stripped."""
        raw = "Check Provided Research Data:\nThe data shows strong growth.\n\nThe company grew 15%."
        result = sanitize_response(raw)
        assert "Check Provided Research Data" not in result
        assert "company grew 15%" in result

    def test_let_me_re_read(self):
        """'Let me re-read' prefix should be stripped."""
        raw = "Let me re-read the question...\nThe user wants a simple explanation.\n\nTI makes chips."
        result = sanitize_response(raw)
        assert "Let me re-read" not in result
        assert "TI makes chips" in result

    def test_i_need_to(self):
        """'I need to' prefix should be stripped."""
        raw = "I need to explain this clearly.\nTI is a semiconductor company."
        result = sanitize_response(raw)
        assert "I need to explain" not in result
        assert "TI is a semiconductor company" in result

    def test_i_should(self):
        """'I should' prefix should be stripped."""
        raw = "I should focus on the key metrics.\nRevenue: $17.7B."
        result = sanitize_response(raw)
        assert "I should focus" not in result
        assert "Revenue: $17.7B" in result

    def test_lets_craft(self):
        """'Let's craft' prefix should be stripped."""
        raw = "Let's craft a response...\nTexas Instruments designs analog chips."
        result = sanitize_response(raw)
        assert "Let's craft" not in result
        assert "Texas Instruments designs analog chips" in result

    def test_system_prompt_says(self):
        """'The system prompt says' prefix should be stripped."""
        raw = "The system prompt says I should be concise.\nTI makes chips for electronics."
        result = sanitize_response(raw)
        assert "system prompt" not in result.lower()
        assert "TI makes chips" in result

    def test_thinking_process(self):
        """'Thinking process:' prefix should be stripped."""
        raw = "Thinking process:\nI need to analyze the data.\n\nThe company is profitable."
        result = sanitize_response(raw)
        assert "Thinking process" not in result
        assert "company is profitable" in result

    def test_wait_prefix(self):
        """'Wait...' prefix should be stripped."""
        raw = "Wait...\nI should clarify.\n\nTI makes chips."
        result = sanitize_response(raw)
        assert "Wait..." not in result
        assert "TI makes chips" in result

    def test_user_asks_prefix(self):
        """'User asks:' prefix should be stripped."""
        raw = "User asks: What does TI do?\n\nTI designs analog chips."
        result = sanitize_response(raw)
        assert "User asks:" not in result
        assert "TI designs analog chips" in result


# ═════════════════════════════════════════════════════════════════════════════
# Clean responses (should NOT be modified)
# ═════════════════════════════════════════════════════════════════════════════


class TestCleanResponses:
    """Test that clean responses are not corrupted."""

    def test_normal_financial_answer(self):
        """A normal financial answer should pass through unchanged."""
        raw = (
            "**Texas Instruments in simple terms**\n\n"
            "Texas Instruments is a semiconductor company. It designs and "
            "manufactures chips used inside electronic systems.\n\n"
            "**Financial picture**\n\n"
            "- Revenue: $17.7B\n"
            "- Operating income: $6.0B\n"
            "- Net income: $5.0B\n\n"
            "**Source**\nFinora research · SEC XBRL · FY2025"
        )
        result = sanitize_response(raw)
        assert result == raw

    def test_metric_explanation(self):
        """A metric explanation should pass through unchanged."""
        raw = (
            "**ROIC**\n15.2%\n\n"
            "**Formula**\nNOPAT / Invested Capital\n\n"
            "**Calculation**\n$2.5B / $16.4B = 15.2%\n\n"
            "**Source**\nSEC 10-K · FY2025"
        )
        result = sanitize_response(raw)
        assert result == raw

    def test_empty_input(self):
        """Empty input should return empty."""
        assert sanitize_response("") == ""
        assert sanitize_response("   ") == ""
        assert sanitize_response(None) == ""

    def test_plain_text(self):
        """Plain text without any reasoning should pass through."""
        raw = "TI makes analog chips and embedded processors for electronics."
        result = sanitize_response(raw)
        assert result == raw


# ═════════════════════════════════════════════════════════════════════════════
# Edge cases
# ═════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Test edge cases and defensive handling."""

    def test_only_reasoning_no_answer(self):
        """If the entire response is reasoning with no real answer."""
        raw = (
            "1. **Analyze User Input:** The user asks about revenue.\n"
            "2. **Check Data:** Revenue is $17.7B.\n"
            "3. **Draft:** I should explain this.\n"
        )
        result = sanitize_response(raw)
        # Should still return something (not crash)
        assert result is not None

    def test_deeply_nested_think_tags(self):
        """Nested think tags should be handled."""
        raw = "<think><think><think>\nThinking...\n</think></think></think>\nReal answer here."
        result = sanitize_response(raw)
        assert "<think>" not in result
        assert "Real answer here" in result

    def test_mixed_tags_and_prefixes(self):
        """Multiple types of leakage in one response."""
        raw = (
            "<think>\nLet me think...\n</think>\n"
            "Analyze User Input:\nThe user wants revenue data.\n\n"
            "Revenue was $17.7B for FY2025."
        )
        result = sanitize_response(raw)
        assert "<think>" not in result
        assert "Analyze User Input" not in result
        assert "Revenue was $17.7B" in result

    def test_very_long_reasoning_with_short_answer(self):
        """Long reasoning with a short actual answer."""
        reasoning = "\n".join(
            f"{i}. **Step {i}:** Analyzing component {i}..."
            for i in range(1, 20)
        )
        raw = f"{reasoning}\n\nThe answer is $17.7B."
        result = sanitize_response(raw)
        assert "Step" not in result or "$17.7B" in result
