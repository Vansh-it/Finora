"""Tests for source fact extractor."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.source_fact_extractor import extract_facts_from_source, _parse_json_array


class TestJsonParsing:
    def test_parse_valid_array(self):
        text = '[{"metric_id": "revenue", "value": 100}]'
        result = _parse_json_array(text)
        assert len(result) == 1
        assert result[0]["metric_id"] == "revenue"

    def test_parse_code_block(self):
        text = '```json\n[{"metric_id": "revenue", "value": 100}]\n```'
        result = _parse_json_array(text)
        assert len(result) == 1

    def test_parse_array_in_text(self):
        text = 'Here are the facts:\n[{"metric_id": "revenue", "value": 100}]\nDone.'
        result = _parse_json_array(text)
        assert len(result) == 1

    def test_parse_empty(self):
        assert _parse_json_array("") == []
        assert _parse_json_array("no json here") == []
        assert _parse_json_array("[]") == []

    def test_parse_single_dict(self):
        text = '{"metric_id": "revenue", "value": 100}'
        result = _parse_json_array(text)
        assert len(result) == 1


class TestExtractFacts:
    @patch("lib.source_fact_extractor.generate_text")
    def test_successful_extraction(self, mock_llm):
        mock_llm.return_value = json.dumps([
            {
                "metric_id": "revenue",
                "value": 331839000000,
                "unit": "USD",
                "period": "FY2026",
                "period_type": "annual",
                "classification": "reported",
                "confidence": 0.95,
                "evidence": "Revenue was $331.8 billion",
            }
        ])

        result = extract_facts_from_source(
            content="Microsoft reported revenue of $331.8 billion for FY2026.",
            company_name="Microsoft Corporation",
            ticker="MSFT",
            source_id="ir_001",
            source_url="https://investor.microsoft.com",
            source_provider="Microsoft Investor Relations",
        )

        assert len(result["facts"]) == 1
        assert result["facts"][0]["metric_id"] == "revenue"
        assert result["facts"][0]["source_id"] == "ir_001"
        assert result["facts"][0]["source_provider"] == "Microsoft Investor Relations"
        assert result["metadata"]["extraction_status"] == "success"

    @patch("lib.source_fact_extractor.generate_text")
    def test_commentary_extraction(self, mock_llm):
        # First call: facts, Second call: commentary
        mock_llm.side_effect = [
            "[]",
            json.dumps([
                {
                    "topic": "revenue_drivers",
                    "summary": "Cloud revenue grew 22% YoY.",
                    "sentiment": "positive",
                    "importance": "high",
                }
            ]),
        ]

        result = extract_facts_from_source(
            content="Microsoft cloud revenue grew 22% year over year driven by Azure.",
            company_name="Microsoft Corporation",
            ticker="MSFT",
        )

        assert len(result["commentary"]) == 1
        assert result["commentary"][0]["topic"] == "revenue_drivers"

    def test_insufficient_content(self):
        result = extract_facts_from_source(
            content="Too short",
            company_name="Test",
            ticker="TST",
        )
        assert result["metadata"]["extraction_status"] == "insufficient_content"
        assert result["facts"] == []

    def test_empty_content(self):
        result = extract_facts_from_source(
            content="",
            company_name="Test",
            ticker="TST",
        )
        assert result["metadata"]["extraction_status"] == "insufficient_content"

    @patch("lib.source_fact_extractor.generate_text")
    def test_llm_failure_graceful(self, mock_llm):
        mock_llm.side_effect = RuntimeError("LLM error")

        result = extract_facts_from_source(
            content="Some content that is long enough to pass the minimum check and trigger extraction.",
            company_name="Test",
            ticker="TST",
        )

        assert result["facts"] == []
        assert result["commentary"] == []

    @patch("lib.source_fact_extractor.generate_text")
    def test_source_metadata_propagation(self, mock_llm):
        mock_llm.return_value = "[]"

        result = extract_facts_from_source(
            content="Some content that is long enough to pass the minimum check for extraction.",
            company_name="Apple Inc.",
            ticker="AAPL",
            source_id="tavily_001",
            source_url="https://investor.apple.com",
            source_provider="Apple Investor Relations",
            source_type="earnings_release",
        )

        assert result["metadata"]["source_id"] == "tavily_001"
        assert result["metadata"]["source_url"] == "https://investor.apple.com"
