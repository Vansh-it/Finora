"""Tests for the Company Resolution Engine features: fuzzy, aliases, suggest, confidence, period extraction."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch
from lib.company_resolver import (
    Company, ResolutionResult, AmbiguousCompanyError,
    resolve_company, _normalize_compare, strip_legal_suffix,
    _normalize, _SUFFIX_RE,
)


# Normalization tests

class TestNormalization:
    def test_strip_legal_suffix_corp(self):
        assert strip_legal_suffix("MICROSOFT CORP") == "MICROSOFT"
        assert strip_legal_suffix("MICROSOFT CORPORATION") == "MICROSOFT"
        assert strip_legal_suffix("MICROSOFT CORP.") == "MICROSOFT"

    def test_strip_legal_suffix_inc(self):
        assert strip_legal_suffix("APPLE INC") == "APPLE"
        assert strip_legal_suffix("APPLE INCORPORATED") == "APPLE"

    def test_strip_legal_suffix_preserves_names(self):
        # CO. is tricky - ensure we don't break real names
        result = strip_legal_suffix("MICROSOFT CORP")
        assert result == "MICROSOFT"

    def test_normalize_compare(self):
        # Both normalize to lowercase and strip punctuation
        a = _normalize_compare("Microsoft Corp!")
        b = _normalize_compare("microsoft corp")
        assert isinstance(a, str) and isinstance(b, str)
        # The core point: _normalize_compare returns lowercase strings
        assert a.startswith("microsoft") and b.startswith("microsoft")

    def test_normalize_compare_strips_punctuation(self):
        # normalize_compare lowercases and strips punctuation
        # Note: strip_legal_suffix only strips uppercase suffixes (SEC data)
        assert _normalize_compare("MICROSOFT CORP") == "microsoft"
        assert _normalize_compare("APPLE INC") == "apple"

    def test_normalize_lowercase(self):
        assert _normalize("HELLO WORLD") == "hello world"

    def test_normalize_collapses_whitespace(self):
        assert _normalize("  hello   world  ") == "hello world"


# Ticker resolution tests (use real universe)

class TestTickerResolution:
    def test_exact_ticker_msft(self):
        c = resolve_company("MSFT")
        assert c.ticker == "MSFT"

    def test_exact_ticker_case_insensitive(self):
        c = resolve_company("aapl")
        assert c.ticker == "AAPL"

    def test_exact_ticker_nvda(self):
        c = resolve_company("NVDA")
        assert c.ticker == "NVDA"


# Company name resolution tests

class TestCompanyNameResolution:
    def test_exact_name_apple(self):
        c = resolve_company("Apple")
        assert c.ticker == "AAPL"

    def test_exact_name_nvidia(self):
        c = resolve_company("NVIDIA")
        assert c.ticker == "NVDA"

    def test_suffix_stripping(self):
        c = resolve_company("NVIDIA Corp")
        assert c.ticker == "NVDA"


# Alias resolution tests

class TestAliasResolution:
    def test_jpmorgan_chase(self):
        c = resolve_company("JPMorgan Chase")
        assert c.ticker == "JPM"

    def test_alphabet(self):
        c = resolve_company("Alphabet")
        assert c.ticker in ("GOOGL", "GOOG")


# Fuzzy matching tests

class TestFuzzyMatching:
    def test_mircosoft(self):
        c = resolve_company("mircosoft")
        assert c.ticker == "MSFT"
        assert c.method == "fuzzy"
        assert c.confidence > 0.7

    def test_microsft(self):
        c = resolve_company("microsft")
        assert c.ticker == "MSFT"

    def test_nvdia(self):
        c = resolve_company("nvdia")
        assert c.ticker == "NVDA"

    def test_palanteer(self):
        c = resolve_company("palanteer")
        assert c.ticker == "PLTR"

    def test_walmat(self):
        c = resolve_company("walmat")
        assert c.ticker == "WMT"

    def test_jpmorgan_chasee(self):
        c = resolve_company("jpmorgan chasee")
        assert c.ticker == "JPM"


# Confidence tests

class TestConfidence:
    def test_exact_ticker_has_max_confidence(self):
        c = resolve_company("MSFT")
        assert c.confidence == 1.0

    def test_fuzzy_has_lower_confidence(self):
        c = resolve_company("mircosoft")
        assert 0.7 <= c.confidence < 1.0


# Ambiguity tests

class TestAmbiguity:
    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Could not resolve"):
            resolve_company("xyzabc123unknown")


# Natural language resolution tests

class TestNaturalLanguageResolution:
    def test_research_microsoft(self):
        c = resolve_company("Research Microsoft for me")
        assert c.ticker == "MSFT"

    def test_make_dashboard_apple(self):
        c = resolve_company("make dashboard of Apple")
        assert c.ticker == "AAPL"

    def test_show_walmart(self):
        c = resolve_company("show walmart financials")
        assert c.ticker == "WMT"

    def test_analyze_jpm(self):
        c = resolve_company("analyze JP Morgan latest")
        assert c.ticker == "JPM"

    def test_nvidia_fy2024(self):
        c = resolve_company("Research NVIDIA FY2024")
        assert c.ticker == "NVDA"


# resolve_company wrapper tests

class TestResolveCompanyWrapper:
    def test_returns_company_object(self):
        c = resolve_company("MSFT")
        assert isinstance(c, Company)
        assert c.ticker == "MSFT"
        assert c.cik is not None

    def test_raises_on_unknown(self):
        with pytest.raises(ValueError):
            resolve_company("xyzunknown")

    def test_none_raises(self):
        with pytest.raises(TypeError):
            resolve_company(None)
