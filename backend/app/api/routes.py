"""
TruthLens AI — API Routes.

All verification endpoints, history, and health check.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.schemas.models import (
    HealthResponse,
    HistoryEntry,
    InputType,
    TextVerifyRequest,
    URLVerifyRequest,
    VerificationReport,
)
from app.services.extraction.extractors import (
    ALLOWED_AUDIO_TYPES,
    ALLOWED_IMAGE_TYPES,
    ALLOWED_PDF_TYPES,
    extract_text_from_pdf,
    extract_text_from_url,
    validate_upload,
)
from app.services.llm.provider import llm_provider
from app.services.reporting.persistence import (
    clear_history,
    delete_verification,
    get_history,
    get_verification,
    save_verification,
)
from app.services.verification.engine import verification_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


# ── Health ──────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        version="1.0.0",
        llm_configured=llm_provider.is_available,
        search_configured=settings.is_search_configured,
    )


# ── Text Verification ──────────────────────────────────────────────

@router.post("/verify/text", response_model=VerificationReport)
async def verify_text(request: TextVerifyRequest, db: Session = Depends(get_db)):
    """Verify factual claims from plain text input."""
    report = await verification_engine.verify_text(
        text=request.text,
        input_type=InputType.TEXT,
        language=request.language,
    )
    try:
        save_verification(db, report)
    except Exception as e:
        logger.error(f"Failed to save verification: {e}")
    return report


# ── Image Verification ──────────────────────────────────────────────

@router.post("/verify/image", response_model=VerificationReport)
async def verify_image(
    file: UploadFile = File(...),
    language: str = Form(default="en"),
    db: Session = Depends(get_db),
):
    """Verify factual claims from an uploaded image (screenshot, photo)."""
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        validate_upload(content_type, len(content), ALLOWED_IMAGE_TYPES, "image")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Extract text using Gemini Vision
    if not llm_provider.is_available:
        raise HTTPException(
            status_code=503,
            detail="LLM provider is not configured. Image text extraction requires GEMINI_API_KEY.",
        )

    try:
        extracted_text = await llm_provider.extract_text_from_image(content, content_type)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract text from image: {str(e)}. Try pasting the text directly.",
        )

    if not extracted_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No readable text was found in the image. Try uploading a clearer image or pasting the text.",
        )

    report = await verification_engine.verify_text(
        text=extracted_text,
        input_type=InputType.IMAGE,
        language=language,
        original_input=f"Image: {file.filename}",
    )
    try:
        save_verification(db, report)
    except Exception as e:
        logger.error(f"Failed to save verification: {e}")
    return report


# ── PDF Verification ────────────────────────────────────────────────

@router.post("/verify/pdf", response_model=VerificationReport)
async def verify_pdf(
    file: UploadFile = File(...),
    language: str = Form(default="en"),
    db: Session = Depends(get_db),
):
    """Verify factual claims from an uploaded PDF document."""
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        validate_upload(content_type, len(content), ALLOWED_PDF_TYPES, "PDF")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        extracted_text = await extract_text_from_pdf(content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    report = await verification_engine.verify_text(
        text=extracted_text,
        input_type=InputType.PDF,
        language=language,
        original_input=f"PDF: {file.filename}",
    )
    try:
        save_verification(db, report)
    except Exception as e:
        logger.error(f"Failed to save verification: {e}")
    return report


# ── Audio Verification ──────────────────────────────────────────────

@router.post("/verify/audio", response_model=VerificationReport)
async def verify_audio(
    file: UploadFile = File(...),
    language: str = Form(default="en"),
    db: Session = Depends(get_db),
):
    """Verify factual claims from an uploaded audio file or voice note."""
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        validate_upload(content_type, len(content), ALLOWED_AUDIO_TYPES, "audio")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not llm_provider.is_available:
        raise HTTPException(
            status_code=503,
            detail="LLM provider is not configured. Audio transcription requires GEMINI_API_KEY.",
        )

    try:
        transcript = await llm_provider.transcribe_audio(content, content_type)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not transcribe audio: {str(e)}. Try pasting the text content directly.",
        )

    if not transcript.strip():
        raise HTTPException(
            status_code=422,
            detail="No speech was detected in the audio file. Try uploading a clearer recording.",
        )

    report = await verification_engine.verify_text(
        text=transcript,
        input_type=InputType.AUDIO,
        language=language,
        original_input=f"Audio: {file.filename}",
    )
    try:
        save_verification(db, report)
    except Exception as e:
        logger.error(f"Failed to save verification: {e}")
    return report


# ── URL Verification ────────────────────────────────────────────────

@router.post("/verify/url", response_model=VerificationReport)
async def verify_url(request: URLVerifyRequest, db: Session = Depends(get_db)):
    """Verify factual claims from a webpage URL."""
    try:
        page_data = await extract_text_from_url(request.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    report = await verification_engine.verify_text(
        text=page_data["text"],
        input_type=InputType.URL,
        language=request.language,
        original_input=request.url,
    )
    try:
        save_verification(db, report)
    except Exception as e:
        logger.error(f"Failed to save verification: {e}")
    return report


# ── History & Report Retrieval ──────────────────────────────────────

@router.get("/verification/{verification_id}", response_model=VerificationReport)
async def get_verification_report(verification_id: str, db: Session = Depends(get_db)):
    """Retrieve a previously saved verification report."""
    report = get_verification(db, verification_id)
    if not report:
        raise HTTPException(status_code=404, detail="Verification report not found.")
    return report


@router.get("/history", response_model=list[HistoryEntry])
async def get_verification_history(db: Session = Depends(get_db)):
    """Get recent verification history."""
    return get_history(db)


@router.delete("/verification/{verification_id}")
async def delete_verification_report(verification_id: str, db: Session = Depends(get_db)):
    """Delete a previously saved verification report."""
    success = delete_verification(db, verification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Verification report not found.")
    return {"status": "deleted", "id": verification_id}


@router.delete("/history")
async def clear_verification_history(db: Session = Depends(get_db)):
    """Clear all verification history."""
    count = clear_history(db)
    return {"status": "cleared", "count": count}
