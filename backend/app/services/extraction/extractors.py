"""
TruthLens AI — Content Extraction Services.

Handles text extraction from images (OCR via Gemini Vision),
PDFs (PyMuPDF), audio (Gemini transcription), and URLs (HTTPX + BeautifulSoup).
"""

from __future__ import annotations

import io
import ipaddress
import logging
import re
import socket
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── PDF Extraction ──────────────────────────────────────────────────

async def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF using PyMuPDF with text cleanup and scanned fallback."""
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            raise RuntimeError("PyMuPDF is required for PDF processing. Install it with: pip install PyMuPDF")

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Could not open PDF file: {e}")

    if doc.page_count > settings.max_pdf_pages:
        raise ValueError(
            f"PDF has {doc.page_count} pages, which exceeds the limit of {settings.max_pdf_pages}. "
            "Please submit a shorter document."
        )

    text_parts = []
    for page_num in range(min(doc.page_count, settings.max_pdf_pages)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        if text.strip():
            # Clean up hyphenated line breaks (e.g. "appro-\npriate" -> "appropriate")
            cleaned = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text.strip())
            text_parts.append(cleaned)

    full_text = "\n\n".join(text_parts).strip()

    # If text is empty, check for scanned pages and try OCR if LLM is available
    if not full_text and doc.page_count > 0:
        from app.services.llm.provider import llm_provider
        if llm_provider.is_available:
            logger.info("PDF has no selectable text; attempting Gemini Vision OCR on first page(s)...")
            ocr_parts = []
            for page_num in range(min(doc.page_count, 3)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                try:
                    ocr_text = await llm_provider.extract_text_from_image(img_bytes, "image/png")
                    if ocr_text.strip():
                        ocr_parts.append(ocr_text.strip())
                except Exception as err:
                    logger.warning(f"OCR failed on PDF page {page_num}: {err}")
            if ocr_parts:
                full_text = "\n\n".join(ocr_parts).strip()

    doc.close()

    if not full_text:
        raise ValueError(
            "No readable text was extracted from this PDF. "
            "It appears to be a scanned document (image-based PDF). "
            "Ensure GEMINI_API_KEY is configured for OCR or upload a screenshot directly."
        )

    # Truncate very long texts
    max_chars = 15000
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "\n\n[Text truncated due to length limits]"

    return full_text


# ── URL Content Extraction ──────────────────────────────────────────

# SSRF protection: blocked IP ranges
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),         # Private
    ipaddress.ip_network("172.16.0.0/12"),      # Private
    ipaddress.ip_network("192.168.0.0/16"),     # Private
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / cloud metadata
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 private
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
]


def _is_safe_url(url: str) -> tuple[bool, str]:
    """Validate a URL for safety (SSRF protection)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format."

    # Protocol check
    if parsed.scheme not in ("http", "https"):
        return False, f"Unsupported protocol: {parsed.scheme}. Only HTTP and HTTPS are allowed."

    # Hostname check
    hostname = parsed.hostname
    if not hostname:
        return False, "URL has no hostname."

    # Block cloud metadata endpoints
    if hostname in ("metadata.google.internal", "metadata.internal"):
        return False, "Access to cloud metadata endpoints is blocked."

    # Resolve hostname and check IP
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in addr_info:
            ip = ipaddress.ip_address(sockaddr[0])
            for blocked in BLOCKED_IP_RANGES:
                if ip in blocked:
                    return False, "Access to private/internal network addresses is blocked."
    except socket.gaierror:
        return False, f"Could not resolve hostname: {hostname}"

    return True, ""


async def extract_text_from_url(url: str) -> dict:
    """
    Safely fetch and extract readable text from a URL.

    Returns:
        dict with keys: text, title, publisher, url
    """
    # SSRF check
    is_safe, reason = _is_safe_url(url)
    if not is_safe:
        raise ValueError(f"URL rejected: {reason}")

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("BeautifulSoup is required for URL processing. Install with: pip install beautifulsoup4")

    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        max_redirects=3,
    ) as client:
        try:
            response = await client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36 (TruthLens/1.0; contact: admin@truthlens.ai)"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            response.raise_for_status()
        except httpx.TooManyRedirects:
            raise ValueError("Too many redirects. The URL may be unsafe.")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Could not retrieve URL: HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            raise ValueError(f"Could not retrieve URL: {e}")

    # Size check (max 5MB)
    content_length = len(response.content)
    if content_length > 5 * 1024 * 1024:
        raise ValueError("Page content is too large (over 5MB).")

    # Parse HTML
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Remove script, style, nav, footer, header elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
        tag.decompose()

    # Try to find main content
    main_content = soup.find("article") or soup.find("main") or soup.find("body")
    if main_content:
        text = main_content.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    if not text.strip():
        raise ValueError("No readable text could be extracted from the page.")

    # Truncate to keep verification prompt fast and focused
    max_chars = 3500
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[Text truncated due to length limits]"

    parsed = urlparse(url)
    publisher = parsed.netloc.replace("www.", "")

    return {
        "text": text,
        "title": title,
        "publisher": publisher,
        "url": url,
    }


# ── File Validation ─────────────────────────────────────────────────

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
ALLOWED_PDF_TYPES = {"application/pdf"}
ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/mpeg", "audio/mp3", "audio/mp4",
    "audio/x-m4a", "audio/m4a", "audio/ogg", "audio/webm",
}


def validate_upload(
    content_type: str,
    file_size: int,
    allowed_types: set[str],
    label: str = "file",
) -> None:
    """Validate an uploaded file's type and size."""
    if content_type not in allowed_types:
        raise ValueError(
            f"Unsupported {label} format: {content_type}. "
            f"Allowed formats: {', '.join(sorted(allowed_types))}"
        )

    if file_size > settings.max_upload_size_bytes:
        raise ValueError(
            f"{label.capitalize()} is too large ({file_size / 1024 / 1024:.1f} MB). "
            f"Maximum allowed size: {settings.max_upload_size_mb} MB."
        )
