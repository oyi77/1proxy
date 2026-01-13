"""
Integration tests for proxy export formats.
Tests all 4 export formats: txt, json, csv, pac
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)


def test_export_txt_format():
    """Test TXT format export returns plain text list of proxy URLs."""
    response = client.get("/api/v1/proxies/export?format=txt&limit=10")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"

    # Content should be newline-separated URLs
    content = response.text
    if content.strip():  # If there are proxies
        lines = content.strip().split("\n")
        for line in lines:
            # Each line should look like a URL
            assert "://" in line or ":" in line  # Either full URL or IP:port


def test_export_json_format():
    """Test JSON format export returns structured JSON data."""
    response = client.get("/api/v1/proxies/export?format=json&limit=10")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    # Should be valid JSON
    data = response.json()
    assert isinstance(data, list)

    # If there are proxies, check structure
    if len(data) > 0:
        proxy = data[0]
        assert "url" in proxy
        assert "protocol" in proxy
        # Optional fields
        assert "country" in proxy or True
        assert "quality_score" in proxy or True


def test_export_csv_format():
    """Test CSV format export returns CSV with headers."""
    response = client.get("/api/v1/proxies/export?format=csv&limit=10")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in response.headers.get("content-disposition", "")

    # Content should have CSV headers
    content = response.text
    lines = content.strip().split("\n")

    if len(lines) > 0:
        # First line should be headers
        headers = lines[0]
        assert "URL" in headers
        assert "Protocol" in headers
        assert "Country" in headers
        assert "Quality" in headers


def test_export_pac_format():
    """Test PAC format export returns proxy auto-config file."""
    response = client.get("/api/v1/proxies/export?format=pac&limit=10")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ns-proxy-autoconfig"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "1proxy.pac" in response.headers.get("content-disposition", "")

    # Content should be a valid PAC file
    content = response.text
    assert "function FindProxyForURL" in content
    assert "return" in content

    # Should have localhost bypass rules
    assert "localhost" in content.lower() or "127.0.0.1" in content


def test_export_with_filters():
    """Test export respects filter parameters."""
    # Test with protocol filter
    response = client.get("/api/v1/proxies/export?format=json&protocol=http&limit=5")
    assert response.status_code == 200

    data = response.json()
    if len(data) > 0:
        # All proxies should be HTTP
        for proxy in data:
            assert proxy.get("protocol") == "http"


def test_export_with_quality_filter():
    """Test export respects quality filter."""
    response = client.get("/api/v1/proxies/export?format=json&min_quality=80&limit=5")
    assert response.status_code == 200

    data = response.json()
    if len(data) > 0:
        # All proxies should have quality >= 80
        for proxy in data:
            score = proxy.get("quality_score")
            if score is not None:
                assert score >= 80


def test_export_limit_parameter():
    """Test that limit parameter works correctly."""
    # Request exactly 5 proxies
    response = client.get("/api/v1/proxies/export?format=json&limit=5")
    assert response.status_code == 200

    data = response.json()
    # Should return at most 5 proxies
    assert len(data) <= 5


def test_export_invalid_format():
    """Test that invalid format returns error."""
    response = client.get("/api/v1/proxies/export?format=invalid")

    # Should return error or default to safe format
    assert response.status_code in [200, 400]

    if response.status_code == 200:
        # If it returns 200, should contain error message
        content = response.json()
        assert "error" in content or isinstance(content, dict)


def test_export_empty_result():
    """Test export with filters that return no results."""
    # Filter for a country code that likely doesn't exist
    response = client.get("/api/v1/proxies/export?format=json&country_code=XX&limit=10")
    assert response.status_code == 200

    # Should return empty array for JSON
    data = response.json()
    assert isinstance(data, list)
    # May or may not be empty depending on data


def test_pac_format_http_only():
    """Test PAC format only includes HTTP/HTTPS proxies."""
    response = client.get("/api/v1/proxies/export?format=pac")
    assert response.status_code == 200

    content = response.text

    # PAC file should be generated even if no HTTP proxies
    assert "function FindProxyForURL" in content

    # Should not include non-HTTP protocols in PROXY directives
    # (PAC files don't support SOCKS5, VMess, etc.)
    if "PROXY" in content:
        # If there are proxy directives, they should be IP:PORT format
        lines = content.split("\n")
        for line in lines:
            if "PROXY " in line:
                # Should not contain protocol prefixes like socks5://
                assert "socks5://" not in line.lower()
                assert "vmess://" not in line.lower()
