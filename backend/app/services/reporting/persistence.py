"""
TruthLens AI — Persistence service.

Stores and retrieves verification reports from the database.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.database import ClaimRecord, EvidenceRecord, VerificationRecord
from app.schemas.models import (
    ClaimVerdict,
    EvidenceItem,
    HistoryEntry,
    InputType,
    VerificationReport,
)

logger = logging.getLogger(__name__)


def save_verification(db: Session, report: VerificationReport) -> str:
    """Persist a verification report to the database. Returns the verification ID."""
    record = VerificationRecord(
        id=report.verification_id,
        input_type=report.input_type.value,
        original_input=(report.original_input or "")[:2000],  # Truncate for storage
        extracted_text=(report.extracted_text or "")[:10000],
        language=report.language,
        status=report.status.value,
        error_message=report.error_message,
    )
    db.add(record)

    for cv in report.claims:
        claim_rec = ClaimRecord(
            verification_id=report.verification_id,
            claim_text=cv.claim_text,
            claim_type=None,
            verdict=cv.verdict.value if cv.verdict else None,
            explanation=cv.explanation,
            evidence_assessment=cv.evidence_assessment.value if cv.evidence_assessment else None,
            uncertainties_json=json.dumps(cv.uncertainties),
        )
        db.add(claim_rec)
        db.flush()  # Get the generated ID

        for ev in cv.supporting_evidence + cv.contradicting_evidence:
            ev_rec = EvidenceRecord(
                claim_id=claim_rec.id,
                source_url=ev.url,
                source_title=ev.title,
                publisher=ev.publisher,
                published_at=ev.published_at,
                snippet=ev.snippet,
                relationship_type=ev.relationship.value if ev.relationship else "partially_relevant",
            )
            db.add(ev_rec)

    db.commit()
    return report.verification_id


def get_verification(db: Session, verification_id: str) -> Optional[VerificationReport]:
    """Retrieve a verification report by ID."""
    record = db.query(VerificationRecord).filter(VerificationRecord.id == verification_id).first()
    if not record:
        return None

    claims = []
    for cr in record.claims:
        supporting = []
        contradicting = []
        for ev in cr.evidence_items:
            item = EvidenceItem(
                source_id=ev.id,
                title=ev.source_title or "Untitled",
                url=ev.source_url,
                publisher=ev.publisher,
                published_at=ev.published_at,
                snippet=ev.snippet or "",
                relationship=ev.relationship_type,
            )
            if ev.relationship_type == "supports":
                supporting.append(item)
            elif ev.relationship_type == "contradicts":
                contradicting.append(item)
            else:
                supporting.append(item)  # Default to supporting for display

        claims.append(ClaimVerdict(
            claim_id=cr.id,
            claim_text=cr.claim_text,
            verdict=cr.verdict or "CANNOT_BE_CONFIRMED",
            explanation=cr.explanation or "",
            evidence_assessment=cr.evidence_assessment or "insufficient_evidence",
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            uncertainties=cr.uncertainties,
        ))

    return VerificationReport(
        verification_id=record.id,
        status=record.status,
        input_type=record.input_type,
        original_input=record.original_input,
        extracted_text=record.extracted_text,
        language=record.language or "en",
        claims=claims,
        created_at=record.created_at.isoformat() if record.created_at else "",
        error_message=record.error_message,
    )


def get_history(db: Session, limit: int = 50) -> list[HistoryEntry]:
    """Get recent verification history entries."""
    records = (
        db.query(VerificationRecord)
        .order_by(VerificationRecord.created_at.desc())
        .limit(limit)
        .all()
    )

    entries = []
    for r in records:
        # Build a summary from claims
        if r.claims:
            first_claim = r.claims[0]
            summary = first_claim.claim_text[:120] if first_claim.claim_text else "No claims extracted"
            verdict = first_claim.verdict
        else:
            summary = (r.original_input or "")[:120] or "No content"
            verdict = None

        entries.append(HistoryEntry(
            verification_id=r.id,
            input_type=r.input_type,
            claim_summary=summary,
            verdict_summary=verdict,
            created_at=r.created_at.isoformat() if r.created_at else "",
        ))

    return entries
