"""
TruthLens AI — Automated Tests for Phase 3 Image & PDF Ingestion Pipeline.

Tests:
  1. PDF text extraction with PyMuPDF
  2. PDF corrupt file & page limit validation
  3. Image file type and size validation
  4. /api/v1/verify/pdf endpoint behavior
  5. /api/v1/verify/image endpoint validation
"""

import asyncio
import io
import pytest
import pymupdf
from fastapi.testclient import TestClient

from app.main import app
from app.services.extraction.extractors import (
    ALLOWED_IMAGE_TYPES,
    ALLOWED_PDF_TYPES,
    extract_text_from_pdf,
    validate_upload,
)


client = TestClient(app)


def create_sample_pdf(text: str = "Government announced new solar subsidy scheme for 2026.") -> bytes:
    """Helper to generate an in-memory PDF with known text."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pdf_extraction_valid():
    """PyMuPDF extractor must extract readable text from a valid PDF."""
    sample_text = "NASA confirmed the discovery of water ice deposits on the Moon."
    pdf_data = create_sample_pdf(sample_text)

    extracted = asyncio.run(extract_text_from_pdf(pdf_data))
    assert sample_text in extracted


def test_pdf_corrupt_file_handling():
    """Corrupt or non-PDF bytes must raise ValueError."""
    corrupt_bytes = b"This is not a real PDF document header"
    with pytest.raises(ValueError, match="Could not open PDF file"):
        asyncio.run(extract_text_from_pdf(corrupt_bytes))


def test_image_upload_validation():
    """validate_upload must accept valid images and reject invalid formats."""
    # Valid PNG
    validate_upload("image/png", 1024 * 50, ALLOWED_IMAGE_TYPES, "image")

    # Invalid MIME type
    with pytest.raises(ValueError, match="Unsupported image format"):
        validate_upload("application/x-sh", 1024, ALLOWED_IMAGE_TYPES, "image")

    # Exceeding size limit
    oversized = 50 * 1024 * 1024  # 50MB
    with pytest.raises(ValueError, match="too large"):
        validate_upload("image/png", oversized, ALLOWED_IMAGE_TYPES, "image")


def test_verify_pdf_endpoint():
    """POST /api/v1/verify/pdf must accept a valid PDF file."""
    pdf_data = create_sample_pdf("Government declared state holiday on upcoming Monday.")
    response = client.post(
        "/api/v1/verify/pdf",
        files={"file": ("notice.pdf", pdf_data, "application/pdf")},
        data={"language": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["input_type"] == "pdf"
    assert "notice.pdf" in data["original_input"]
    assert "Government declared state holiday" in data["extracted_text"]


def test_verify_pdf_invalid_mimetype():
    """POST /api/v1/verify/pdf must reject non-PDF uploads with 400."""
    response = client.post(
        "/api/v1/verify/pdf",
        files={"file": ("test.txt", b"plain text", "text/plain")},
        data={"language": "en"},
    )
    assert response.status_code == 400
    assert "Unsupported PDF format" in response.json()["detail"]


def test_verify_image_invalid_mimetype():
    """POST /api/v1/verify/image must reject dangerous or non-image uploads with 400."""
    response = client.post(
        "/api/v1/verify/image",
        files={"file": ("malicious.exe", b"binary", "application/x-dosexec")},
        data={"language": "en"},
    )
    assert response.status_code == 400
    assert "Unsupported image format" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
