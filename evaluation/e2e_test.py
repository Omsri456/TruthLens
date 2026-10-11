"""
TruthLens AI — Comprehensive End-to-End (E2E) Integration Test Suite.

Validates the full verification lifecycle:
1. Health & Root Endpoints
2. Text Verification Pipeline with Live Open Search Evidence Retrieval
3. PDF Content Ingestion & Verification
4. URL Scraping & Enterprise SSRF Protection
5. History Management & MediaType Filtering
6. Single Record Lookup & Deletion
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend directory is importable
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.schemas.models import (
    ClaimExtractionResult,
    ExtractedClaim,
    Verdict,
    EvidenceAssessment,
    EvidenceRelationship,
)
from app.services.llm.provider import llm_provider

client = TestClient(app)


def run_e2e_tests():
    print("======================================================================")
    print("TruthLens AI — Comprehensive End-to-End (E2E) Test Suite")
    print("======================================================================")

    # 1. Root & Health Check
    print("\n[1/7] Testing Root & Health Check Endpoints...")
    res_root = client.get("/")
    assert res_root.status_code == 200, f"Root endpoint failed: {res_root.text}"
    print(f"      [OK] GET / -> 200 OK: {res_root.json()['name']} v{res_root.json()['version']}")

    res_probe = client.get("/health")
    assert res_probe.status_code == 200, f"Probe endpoint failed: {res_probe.text}"
    print(f"      [OK] GET /health -> 200 OK: {res_probe.json()['status']}")

    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200, f"Health endpoint failed: {res_health.text}"
    health_data = res_health.json()
    print(f"      [OK] GET /api/v1/health -> 200 OK (Status: {health_data['status']})")

    # If LLM key not configured locally, provide mock responses so E2E flow tests
    # the entire pipeline with REAL live search retrieval & SQLite persistence.
    should_mock_llm = not llm_provider.is_available

    async def mock_extract(text, language="en"):
        return ClaimExtractionResult(
            claims=[
                ExtractedClaim(
                    claim_id="claim_e2e_1",
                    text=text[:120].strip(),
                    claim_type="general",
                )
            ],
            input_language=language,
        )

    async def mock_analyze(claim_text, evidence):
        rel_list = []
        for i, ev in enumerate(evidence):
            rel_list.append({
                "source_id": ev.source_id,
                "relationship": EvidenceRelationship.SUPPORTS.value if i == 0 else EvidenceRelationship.PARTIALLY_RELEVANT.value
            })
        return {
            "verdict": Verdict.VERIFIED,
            "evidence_assessment": EvidenceAssessment.STRONG_EVIDENCE,
            "evidence_relationships": rel_list,
            "key_findings": f"Live web sources verify: {claim_text[:80]}",
            "uncertainties": [],
            "explanation_points": ["Verified by authoritative sources."],
        }

    async def mock_explanation(*args, **kwargs):
        return "This factual claim was evaluated and confirmed against live retrieved evidence."

    ctx_mgrs = []
    if should_mock_llm:
        print("      (Note: Mocking LLM interface to test full pipeline with live open search & persistence)")
        from unittest.mock import PropertyMock
        patch_avail = patch.object(type(llm_provider), "is_available", new_callable=PropertyMock, return_value=True)
        patch_ext = patch.object(llm_provider, "extract_claims", side_effect=mock_extract)
        patch_ana = patch.object(llm_provider, "analyze_evidence", side_effect=mock_analyze)
        patch_exp = patch.object(llm_provider, "generate_explanation", side_effect=mock_explanation)
        patch_avail.start()
        patch_ext.start()
        patch_ana.start()
        patch_exp.start()

    try:
        # 2. Text Verification with Live Retrieval
        print("\n[2/7] Testing Text Claim Verification & Live Evidence Retrieval...")
        claim_text = "The Reserve Bank of India announced currency demonetization in November 2016."
        res_text = client.post(
            "/api/v1/verify/text",
            json={"text": claim_text, "language": "en"}
        )
        assert res_text.status_code == 200, f"Text verification failed: {res_text.text}"
        text_data = res_text.json()
        text_id = text_data["verification_id"]
        claims = text_data.get("claims", [])
        assert len(claims) > 0, "Expected at least 1 claim verdict"
        primary_claim = claims[0]
        total_sources = len(primary_claim.get("supporting_evidence", [])) + len(primary_claim.get("contradicting_evidence", []))
        print(f"      [OK] Verification ID: {text_id}")
        print(f"      [OK] Claim Verdict: {primary_claim['verdict']}")
        print(f"      [OK] Total Evidence Sources: {total_sources} retrieved items from live search")
        if primary_claim.get("supporting_evidence"):
            top_source = primary_claim["supporting_evidence"][0]
            print(f"           Top Live Citation: {top_source['title']} ({top_source['url']})")

        # 3. PDF Ingestion & Verification
        print("\n[3/7] Testing PDF Document Ingestion & Verification...")
        sample_pdf = os.path.join(os.path.dirname(__file__), "..", "samples", "sample_government_notice.pdf")
        with open(sample_pdf, "rb") as f:
            pdf_bytes = f.read()

        res_pdf = client.post(
            "/api/v1/verify/pdf",
            files={"file": ("sample_government_notice.pdf", pdf_bytes, "application/pdf")},
            data={"language": "en"}
        )
        assert res_pdf.status_code == 200, f"PDF verification failed: {res_pdf.text}"
        pdf_data = res_pdf.json()
        pdf_id = pdf_data["verification_id"]
        print(f"      [OK] PDF Verification ID: {pdf_id}")
        print(f"      [OK] PDF Extracted Text Length: {len(pdf_data.get('extracted_text', ''))} characters")
        print(f"      [OK] Claims Identified: {len(pdf_data.get('claims', []))}")

        # 4. Enterprise SSRF Guard & URL Verification
        print("\n[4/7] Testing Enterprise SSRF Guards & Public URL Verification...")
        # Cloud metadata block
        ssrf_meta = client.post("/api/v1/verify/url", json={"url": "http://169.254.169.254/latest/meta-data/"})
        assert ssrf_meta.status_code == 422, "SSRF guard should reject cloud metadata IP"
        print("      [OK] SSRF Guard blocked AWS/GCP metadata IP (169.254.169.254) with HTTP 422")

        # Loopback block
        ssrf_loopback = client.post("/api/v1/verify/url", json={"url": "http://127.0.0.1:8000/api/v1/health"})
        assert ssrf_loopback.status_code == 422, "SSRF guard should reject loopback IP"
        print("      [OK] SSRF Guard blocked local loopback IP (127.0.0.1) with HTTP 422")

        # Dangerous scheme block
        ssrf_file = client.post("/api/v1/verify/url", json={"url": "file:///etc/passwd"})
        assert ssrf_file.status_code == 422, "SSRF guard should reject file:// protocol"
        print("      [OK] SSRF Guard blocked dangerous protocol (file://) with HTTP 422")

        # Valid public URL
        res_url = client.post("/api/v1/verify/url", json={"url": "https://en.wikipedia.org/wiki/Earth"})
        assert res_url.status_code == 200, f"Valid URL failed: {res_url.text}"
        url_data = res_url.json()
        print(f"      [OK] Public URL Ingestion ID: {url_data['verification_id']}")
        print(f"      [OK] Extracted Page Text Length: {len(url_data.get('extracted_text', ''))} characters")
        print(f"      [OK] Claims Evaluated: {len(url_data.get('claims', []))}")

        # 5. History Listing & Media Filtering
        print("\n[5/7] Testing Verification History & Media Filtering...")
        res_hist = client.get("/api/v1/history")
        assert res_hist.status_code == 200
        all_items = res_hist.json()
        print(f"      [OK] Total History Records: {len(all_items)} entries")

        res_pdf_filter = client.get("/api/v1/history?input_type=pdf")
        assert res_pdf_filter.status_code == 200
        pdf_items = res_pdf_filter.json()
        print(f"      [OK] PDF Filtered Count: {len(pdf_items)} entries")
        assert any(item["verification_id"] == pdf_id for item in pdf_items), "PDF record missing in filtered query"

        # 6. Single Record Fetch
        print("\n[6/7] Testing Single Record Lookup by ID...")
        res_fetch = client.get(f"/api/v1/verification/{text_id}")
        assert res_fetch.status_code == 200
        fetched_entry = res_fetch.json()
        assert fetched_entry["verification_id"] == text_id
        print(f"      [OK] Successfully retrieved single record: {text_id}")

        # 7. Single Record Deletion & 404 Check
        print("\n[7/7] Testing Single Record Deletion & 404 State Verification...")
        res_del = client.delete(f"/api/v1/verification/{text_id}")
        assert res_del.status_code == 200
        res_404 = client.get(f"/api/v1/verification/{text_id}")
        assert res_404.status_code == 404
        print(f"      [OK] Deleted record {text_id} cleanly; subsequent fetch returns 404 Not Found")

        print("\n======================================================================")
        print("ALL 7 END-TO-END SUITES EXECUTED & PASSED WITH 100% SUCCESS!")
        print("======================================================================\n")

    finally:
        if should_mock_llm:
            patch.stopall()


if __name__ == "__main__":
    run_e2e_tests()
