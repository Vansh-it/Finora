"""Tests for the SSRF guard that prevents internal network access."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.ssrf_guard import safe_url_or_none, validate_url


class TestSSRFGuard:
    def test_allows_public_urls(self):
        assert safe_url_or_none("https://example.com") is not None
        assert safe_url_or_none("https://www.sec.gov/data") is not None
        assert safe_url_or_none("https://api.tavily.com/search") is not None

    def test_blocks_localhost(self):
        assert safe_url_or_none("http://localhost/api") is None
        assert safe_url_or_none("http://localhost:8000/secret") is None
        assert safe_url_or_none("http://127.0.0.1/api") is None
        assert safe_url_or_none("http://[::1]/api") is None

    def test_blocks_private_ips(self):
        assert safe_url_or_none("http://10.0.0.1/admin") is None
        assert safe_url_or_none("http://172.16.0.1/admin") is None
        assert safe_url_or_none("http://192.168.1.1/admin") is None

    def test_blocks_metadata_endpoint(self):
        assert safe_url_or_none("http://169.254.169.254/metadata") is None

    def test_blocks_file_scheme(self):
        assert safe_url_or_none("file:///etc/passwd") is None

    def test_blocks_unsupported_schemes(self):
        assert safe_url_or_none("ftp://example.com") is None
        assert safe_url_or_none("javascript:alert(1)") is None

    def test_blocks_empty_and_none(self):
        assert safe_url_or_none("") is None
        assert safe_url_or_none(None) is None

    def test_validate_url_good(self):
        ok, reason = validate_url("https://example.com")
        assert ok is True
        assert reason is None

    def test_validate_url_blocks_bad(self):
        ok, reason = validate_url("http://localhost/secret")
        assert ok is False
        assert reason is not None
        assert len(reason) > 0

    def test_validate_url_blocks_private(self):
        ok, reason = validate_url("http://192.168.1.1/admin")
        assert ok is False
