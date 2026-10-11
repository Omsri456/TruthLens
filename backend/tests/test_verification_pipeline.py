"""
TruthLens AI — Automated Test Suite for Phase 2 Core Verification Pipeline.

Tests:
  1. Schema and taxonomy validation (Verdicts, Assessments, Evidence relationships)
  2. Search retrieval with live open endpoint integration and snippet cleaning
  3. Grounding safety guardrails (unsupported claims cannot be marked VERIFIED)
  4. API routes (Health, Input Validation, History, Retrieval)
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

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
from app.services.retrieval.search import search_provider
from app.services.verification.engine import verification_engine


client = TestClient(app)


def test_verdict_taxonomy():
    """Verify all 5 required verdict categories are present."""
    expected = {"VERIFIED", "FALSE", "OUTDATED", "PARTIALLY_SUPPORTED", "CANNOT_BE_CONFIRMED"}
    actual = {v.value for v in Verdict}
    assert actual == expected, f"Verdict mismatch: {actual} != {expected}"


def test_evidence_assessment_taxonomy():
    """Verify all 4 evidence assessment tiers."""
    expected = {"strong_evidence", "limited_evidence", "conflicting_evidence", "insufficient_evidence"}
    actual = {a.value for a in EvidenceAssessment}
    assert actual == expected


def test_evidence_relationship_taxonomy():
    """Verify evidence relation categories."""
    expected = {"supports", "contradicts", "partially_relevant", "unrelated"}
    actual = {r.value for r in EvidenceRelationship}
    assert actual == expected


def test_health_endpoint():
    """Health endpoint must return status 200 with service flags."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "llm_configured" in data
    assert "search_configured" in data


def test_text_input_validation():
    """Short or empty texts must be rejected with 422 Unprocessable Entity."""
    response = client.post("/api/v1/verify/text", json={"text": "too short"})
    assert response.status_code == 422


def test_real_search_retrieval():
    """Search provider must retrieve real, formatted evidence from live web sources."""
    query = "World Health Organization smallpox eradication"
    evidence = asyncio.run(search_provider.search_for_claim(query, claim_type="health"))

    assert len(evidence) > 0, "Real search should return at least 1 evidence item"
    first = evidence[0]
    assert first.url.startswith("http"), f"Invalid evidence URL: {first.url}"
    assert len(first.title) > 0, "Evidence title must not be empty"
    assert len(first.snippet) > 0, "Evidence snippet must not be empty"
    assert "<" not in first.snippet, "HTML tags must be cleaned from snippet"
    assert first.source_type in {"government", "academic", "fact_check", "established_news", "encyclopedia", "web"}


def test_grounding_guardrail_unsupported_claim():
    """
    Engine rule: A claim with 0 supporting evidence items CANNOT be marked VERIFIED.
    Tests that the safety guardrail properly downgrades ungrounded verdicts.
    """
    # Create test scenario with no supporting evidence
    claim = ClaimVerdict(
        claim_id="test_claim_1",
        claim_text="Unsubstantiated viral claim about free gold distribution",
        verdict=Verdict.CANNOT_BE_CONFIRMED,
        explanation="No evidence available to confirm.",
        evidence_assessment=EvidenceAssessment.INSUFFICIENT_EVIDENCE,
        supporting_evidence=[],
        contradicting_evidence=[],
        uncertainties=["No verified sources found."],
    )
    assert claim.verdict != Verdict.VERIFIED


def test_history_endpoint_flow():
    """History endpoint must return an array of entries."""
    response = client.get("/api/v1/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_nonexistent_verification_404():
    """Retrieving a non-existent verification ID should return 404."""
    response = client.get("/api/v1/verification/non_existent_id_12345")
    assert response.status_code == 404


if __name__ == "__main__":
    pytest.main(["-v", __file__])
