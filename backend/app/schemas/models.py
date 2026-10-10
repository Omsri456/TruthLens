"""
TruthLens AI — Pydantic schemas for request/response validation.

These schemas define the API contract between the frontend and backend,
as well as internal data structures for the verification pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


# ── Verdict Categories ──────────────────────────────────────────────

class Verdict(str, Enum):
    VERIFIED = "VERIFIED"
    FALSE = "FALSE"
    OUTDATED = "OUTDATED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CANNOT_BE_CONFIRMED = "CANNOT_BE_CONFIRMED"


class EvidenceAssessment(str, Enum):
    STRONG_EVIDENCE = "strong_evidence"
    LIMITED_EVIDENCE = "limited_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceRelationship(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    PARTIALLY_RELEVANT = "partially_relevant"
    UNRELATED = "unrelated"


class InputType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"
    AUDIO = "audio"
    URL = "url"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    SEARCHING = "searching"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Claim Extraction (LLM output) ──────────────────────────────────

class ExtractedClaim(BaseModel):
    """A single factual claim extracted from user input by the LLM."""
    claim_id: str = Field(default_factory=lambda: f"claim_{uuid.uuid4().hex[:8]}")
    text: str = Field(..., description="The factual claim text")
    claim_type: Optional[str] = Field(default=None, description="Category of the claim")
    entities: list[str] = Field(default_factory=list)
    amounts: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    requires_current_information: bool = Field(default=True)


class ClaimExtractionResult(BaseModel):
    """Structured output from the claim extraction LLM call."""
    claims: list[ExtractedClaim] = Field(default_factory=list)
    input_language: str = Field(default="en")
    extraction_notes: Optional[str] = None


# ── Evidence ────────────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    """A single piece of evidence retrieved from a source."""
    source_id: str = Field(default_factory=lambda: f"src_{uuid.uuid4().hex[:8]}")
    title: str
    url: str
    publisher: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    snippet: str
    relevance: Optional[float] = None
    source_type: Optional[str] = None
    relationship: EvidenceRelationship = EvidenceRelationship.PARTIALLY_RELEVANT


# ── Claim Verdict ───────────────────────────────────────────────────

class ClaimVerdict(BaseModel):
    """Full verdict for a single claim, with evidence and explanation."""
    claim_id: str
    claim_text: str
    verdict: Verdict
    explanation: str
    evidence_assessment: EvidenceAssessment
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)
    contradicting_evidence: list[EvidenceItem] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


# ── Verification Report ────────────────────────────────────────────

class VerificationReport(BaseModel):
    """Complete verification response returned to the frontend."""
    verification_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    status: ProcessingStatus = ProcessingStatus.COMPLETED
    input_type: InputType
    original_input: Optional[str] = None
    extracted_text: Optional[str] = None
    language: str = "en"
    claims: list[ClaimVerdict] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    error_message: Optional[str] = None


# ── API Request Schemas ─────────────────────────────────────────────

class TextVerifyRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=10000)
    language: str = Field(default="en")


class URLVerifyRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=2000)
    language: str = Field(default="en")


# ── History ─────────────────────────────────────────────────────────

class HistoryEntry(BaseModel):
    verification_id: str
    input_type: InputType
    claim_summary: str
    verdict_summary: Optional[str] = None
    created_at: str


# ── Health Check ────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    llm_configured: bool = False
    search_configured: bool = False
