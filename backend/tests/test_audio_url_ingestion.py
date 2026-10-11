"""
TruthLens AI — Automated Test Suite for Phase 4 Audio & URL Ingestion Pipeline.

Tests:
  1. SSRF Protection guards against internal IPs, loopback, and cloud metadata
  2. Safe protocol enforcement (only http/https allowed)
  3. Audio file type and size validation
  4. /api/v1/verify/url endpoint input validation and SSRF rejection
  5. /api/v1/verify/audio endpoint validation
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.extraction.extractors import (
    ALLOWED_AUDIO_TYPES,
    _is_safe_url,
    validate_upload,
)


client = TestClient(app)


def test_ssrf_protection_loopback():
    """Loopback addresses must be blocked to prevent internal scanning."""
    blocked_urls = [
        "http://127.0.0.1:8000/api/v1/health",
        "http://127.0.0.2/",
        "http://localhost:8000/",
        "http://[::1]/",
    ]
    for url in blocked_urls:
        is_safe, reason = _is_safe_url(url)
        assert not is_safe, f"URL {url} should have been blocked, reason: {reason}"


def test_ssrf_protection_private_networks():
    """Private RFC 1918 subnets must be blocked."""
    private_urls = [
        "http://10.0.0.1/admin",
        "http://192.168.1.1/router",
        "http://172.16.0.1/console",
    ]
    for url in private_urls:
        is_safe, reason = _is_safe_url(url)
        assert not is_safe, f"Private IP {url} should be blocked"


def test_ssrf_protection_cloud_metadata():
    """Cloud instance metadata services (AWS/GCP/Azure) must be blocked."""
    metadata_urls = [
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
    ]
    for url in metadata_urls:
        is_safe, reason = _is_safe_url(url)
        assert not is_safe, f"Metadata service {url} should be blocked"


def test_ssrf_protection_dangerous_protocols():
    """Only HTTP and HTTPS protocols are permissible."""
    dangerous = [
        "file:///etc/passwd",
        "ftp://example.com/file.txt",
        "gopher://example.com/",
        "data:text/html,<h1>test</h1>",
    ]
    for url in dangerous:
        is_safe, reason = _is_safe_url(url)
        assert not is_safe, f"Protocol for {url} should be blocked"


def test_ssrf_valid_public_domain():
    """Valid public websites should be permitted."""
    is_safe, reason = _is_safe_url("https://en.wikipedia.org/wiki/Main_Page")
    assert is_safe, f"Public URL was unexpectedly rejected: {reason}"


def test_audio_upload_validation():
    """validate_upload must accept valid audio types and reject invalid formats."""
    # Valid MP3 / WAV
    validate_upload("audio/mpeg", 1024 * 500, ALLOWED_AUDIO_TYPES, "audio")
    validate_upload("audio/wav", 1024 * 500, ALLOWED_AUDIO_TYPES, "audio")

    # Invalid MIME type
    with pytest.raises(ValueError, match="Unsupported audio format"):
        validate_upload("video/mp4", 1024, ALLOWED_AUDIO_TYPES, "audio")

    # Oversized audio
    oversized = 20 * 1024 * 1024  # 20MB
    with pytest.raises(ValueError, match="too large"):
        validate_upload("audio/mpeg", oversized, ALLOWED_AUDIO_TYPES, "audio")


def test_verify_url_ssrf_endpoint_rejection():
    """POST /api/v1/verify/url must reject SSRF attempts with 422."""
    response = client.post(
        "/api/v1/verify/url",
        json={"url": "http://127.0.0.1:8000/api/v1/health", "language": "en"},
    )
    assert response.status_code == 422
    assert "URL rejected" in response.json()["detail"]


def test_verify_url_invalid_length():
    """POST /api/v1/verify/url must reject short or empty URLs with 422."""
    response = client.post(
        "/api/v1/verify/url",
        json={"url": "short", "language": "en"},
    )
    assert response.status_code == 422


def test_verify_audio_invalid_mimetype():
    """POST /api/v1/verify/audio must reject non-audio files with 400."""
    response = client.post(
        "/api/v1/verify/audio",
        files={"file": ("fake_audio.pdf", b"%PDF-1.4...", "application/pdf")},
        data={"language": "en"},
    )
    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
