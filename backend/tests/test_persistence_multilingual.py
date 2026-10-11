"""
TruthLens AI — Automated Test Suite for Phase 5 Persistence & Multilingual Support.

Tests:
  1. Multilingual language mapping for English, Hindi, and Marathi
  2. Full report persistence with claims and categorized evidence items
  3. Single record retrieval via /api/v1/verification/{id}
  4. Record deletion via DELETE /api/v1/verification/{id}
  5. Full history clear via DELETE /api/v1/history
  6. Language propagation through verification endpoints
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.schemas.models import (
    ClaimVerdict,
    EvidenceAssessment,
    EvidenceItem,
    EvidenceRelationship,
    InputType,
    ProcessingStatus,
    Verdict,
    VerificationReport,
)
from app.services.llm.provider import llm_provider
from app.services.reporting.persistence import (
    clear_history,
    delete_verification,
    get_history,
    get_verification,
    save_verification,
)


client = TestClient(app)


def test_multilingual_language_mapping():
    """Verify that language codes map to descriptive regional prompt names."""
    assert "English" in llm_provider._language_name("en")
    assert "Hindi" in llm_provider._language_name("hi")
    assert "Devanagari" in llm_provider._language_name("hi")
    assert "Marathi" in llm_provider._language_name("mr")
    assert "Devanagari" in llm_provider._language_name("mr")


def test_full_report_persistence_and_retrieval():
    """Verify storing and retrieving a complete report with Hindi language and evidence items."""
    db = SessionLocal()
    try:
        report_id = f"test_rep_{uuid.uuid4().hex[:8]}"
        claim_id = f"claim_{uuid.uuid4().hex[:6]}"

        supporting_ev = EvidenceItem(
            source_id="src_1",
            title="Official Ministry Release",
            url="https://pib.gov.in/PressReleasePage.aspx?PRID=123",
            publisher="pib.gov.in",
            published_at="2026-03-15",
            retrieved_at="2026-10-11T05:00:00Z",
            snippet="Government officially confirmed subsidy rollout.",
            relationship=EvidenceRelationship.SUPPORTS,
        )

        claim = ClaimVerdict(
            claim_id=claim_id,
            claim_text="सरकारने २०२६ मध्ये नवीन अनुदान योजना जाहीर केली आहे.",
            verdict=Verdict.VERIFIED,
            explanation="PIB च्या अधिकृत प्रकाशनानुसार ही माहिती सत्य आहे.",
            evidence_assessment=EvidenceAssessment.STRONG_EVIDENCE,
            supporting_evidence=[supporting_ev],
            contradicting_evidence=[],
            uncertainties=[],
        )

        report = VerificationReport(
            verification_id=report_id,
            status=ProcessingStatus.COMPLETED,
            input_type=InputType.TEXT,
            original_input="Forwarded WhatsApp note in Marathi",
            extracted_text="सरकारने २०२६ मध्ये नवीन अनुदान योजना जाहीर केली आहे.",
            language="mr",
            claims=[claim],
        )

        saved_id = save_verification(db, report)
        assert saved_id == report_id

        # Retrieve via persistence layer
        fetched = get_verification(db, report_id)
        assert fetched is not None
        assert fetched.verification_id == report_id
        assert fetched.language == "mr"
        assert len(fetched.claims) == 1
        assert fetched.claims[0].verdict == Verdict.VERIFIED
        assert len(fetched.claims[0].supporting_evidence) == 1
        assert fetched.claims[0].supporting_evidence[0].url == "https://pib.gov.in/PressReleasePage.aspx?PRID=123"

        # Retrieve via API endpoint
        api_res = client.get(f"/api/v1/verification/{report_id}")
        assert api_res.status_code == 200
        assert api_res.json()["language"] == "mr"
        assert len(api_res.json()["claims"]) == 1

        # Check in history API
        hist_res = client.get("/api/v1/history")
        assert hist_res.status_code == 200
        entries = hist_res.json()
        matching = [e for e in entries if e["verification_id"] == report_id]
        assert len(matching) == 1
        assert matching[0]["language"] == "mr"

        # Delete single record
        del_res = client.delete(f"/api/v1/verification/{report_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # Verify it no longer exists
        assert client.get(f"/api/v1/verification/{report_id}").status_code == 404

    finally:
        db.close()


def test_clear_history_endpoint():
    """DELETE /api/v1/history must delete all records and return cleared count."""
    # Ensure there is at least one entry
    db = SessionLocal()
    try:
        dummy_id = f"dummy_{uuid.uuid4().hex[:6]}"
        dummy_report = VerificationReport(
            verification_id=dummy_id,
            status=ProcessingStatus.COMPLETED,
            input_type=InputType.TEXT,
            language="en",
        )
        save_verification(db, dummy_report)
    finally:
        db.close()

    res = client.delete("/api/v1/history")
    assert res.status_code == 200
    assert res.json()["status"] == "cleared"
    assert res.json()["count"] >= 1

    # Verify history is now empty
    hist_after = client.get("/api/v1/history")
    assert hist_after.status_code == 200
    assert len(hist_after.json()) == 0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
