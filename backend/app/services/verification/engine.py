"""
TruthLens AI — Verification Engine.

Orchestrates the complete verification pipeline:
  Content → Claim Extraction → Evidence Search → Analysis → Verdict → Explanation

This is the central coordinator — it calls the LLM provider for AI tasks
and the search provider for evidence retrieval, then assembles the final report.
"""

from __future__ import annotations

import logging
from typing import Optional

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
from app.services.retrieval.search import search_provider

logger = logging.getLogger(__name__)


class VerificationEngine:
    """
    Orchestrates the fact-verification pipeline.

    Sequence:
      1. Extract claims from text using LLM
      2. Search for evidence for each claim
      3. Analyze evidence against each claim using LLM
      4. Generate human-readable explanation using LLM
      5. Assemble the final report
    """

    async def verify_text(
        self,
        text: str,
        input_type: InputType = InputType.TEXT,
        language: str = "en",
        original_input: Optional[str] = None,
    ) -> VerificationReport:
        """
        Run the full verification pipeline on extracted text.

        Args:
            text: The text content to verify (may be extracted from image/pdf/audio/url).
            input_type: The original input format.
            language: Target language for the explanation.
            original_input: The original input reference (filename, URL, etc.).
        """
        report = VerificationReport(
            input_type=input_type,
            original_input=original_input or text[:500],
            extracted_text=text,
            language=language,
        )

        # ── Gate checks ──────────────────────────────────────────
        if not llm_provider.is_available:
            report.status = ProcessingStatus.FAILED
            report.error_message = (
                "LLM provider is not configured. Please set GEMINI_API_KEY in your .env file "
                "to enable claim extraction and analysis."
            )
            return report

        if not search_provider.is_available:
            report.status = ProcessingStatus.FAILED
            report.error_message = (
                "Search provider is not configured. Please set GOOGLE_SEARCH_API_KEY and "
                "GOOGLE_SEARCH_ENGINE_ID in your .env file to enable evidence retrieval."
            )
            return report

        # ── Stage 1: Claim Extraction ────────────────────────────
        try:
            extraction = await llm_provider.extract_claims(text, language)
        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            report.status = ProcessingStatus.FAILED
            report.error_message = f"Claim extraction failed: {str(e)}"
            return report

        if not extraction.claims:
            report.status = ProcessingStatus.COMPLETED
            report.claims = []
            report.error_message = (
                "No verifiable factual claims were found in the submitted content. "
                "The content may contain only opinions, questions, or non-factual statements."
            )
            return report

        if extraction.input_language:
            report.language = extraction.input_language if language == "en" else language

        # ── Stages 2–6: Per-claim verification ───────────────────
        claim_verdicts: list[ClaimVerdict] = []

        for claim in extraction.claims:
            try:
                verdict = await self._verify_single_claim(claim.text, claim.claim_type, language)
                verdict.claim_id = claim.claim_id
                claim_verdicts.append(verdict)
            except Exception as e:
                logger.error(f"Verification failed for claim '{claim.text[:60]}': {e}")
                claim_verdicts.append(ClaimVerdict(
                    claim_id=claim.claim_id,
                    claim_text=claim.text,
                    verdict=Verdict.CANNOT_BE_CONFIRMED,
                    explanation=f"Verification could not be completed due to a processing error: {str(e)}",
                    evidence_assessment=EvidenceAssessment.INSUFFICIENT_EVIDENCE,
                    uncertainties=["Verification process encountered an error."],
                ))

        report.claims = claim_verdicts
        report.status = ProcessingStatus.COMPLETED
        return report

    async def _verify_single_claim(
        self,
        claim_text: str,
        claim_type: Optional[str],
        language: str,
    ) -> ClaimVerdict:
        """Run evidence retrieval and analysis for a single claim."""

        # ── Stage 2: Evidence Search ─────────────────────────────
        evidence = await search_provider.search_for_claim(claim_text, claim_type)

        if not evidence:
            return ClaimVerdict(
                claim_id="",
                claim_text=claim_text,
                verdict=Verdict.CANNOT_BE_CONFIRMED,
                explanation=(
                    "No relevant evidence could be retrieved for this claim. "
                    "This does not mean the claim is false — it means we could not "
                    "find sufficient online sources to verify or refute it."
                ),
                evidence_assessment=EvidenceAssessment.INSUFFICIENT_EVIDENCE,
                uncertainties=["No evidence was found through web search."],
            )

        # ── Stage 3: Evidence Analysis ───────────────────────────
        analysis = await llm_provider.analyze_evidence(claim_text, evidence)

        # ── Stage 4: Update evidence relationships from analysis ─
        relationships = {
            r["source_id"]: r["relationship"]
            for r in analysis.get("evidence_relationships", [])
            if "source_id" in r and "relationship" in r
        }

        for item in evidence:
            if item.source_id in relationships:
                try:
                    item.relationship = EvidenceRelationship(relationships[item.source_id])
                except ValueError:
                    pass

        supporting = [e for e in evidence if e.relationship == EvidenceRelationship.SUPPORTS]
        contradicting = [e for e in evidence if e.relationship == EvidenceRelationship.CONTRADICTS]

        # ── Stage 5: Generate Explanation ────────────────────────
        verdict = analysis.get("verdict", Verdict.CANNOT_BE_CONFIRMED)
        assessment = analysis.get("evidence_assessment", EvidenceAssessment.INSUFFICIENT_EVIDENCE)
        uncertainties = analysis.get("uncertainties", [])
        key_findings = analysis.get("key_findings", "")

        # Ensure verdict and assessment are proper enum values
        if isinstance(verdict, str):
            try:
                verdict = Verdict(verdict)
            except ValueError:
                verdict = Verdict.CANNOT_BE_CONFIRMED
        if isinstance(assessment, str):
            try:
                assessment = EvidenceAssessment(assessment)
            except ValueError:
                assessment = EvidenceAssessment.INSUFFICIENT_EVIDENCE

        explanation = await llm_provider.generate_explanation(
            claim_text=claim_text,
            verdict=verdict,
            evidence_assessment=assessment,
            key_findings=key_findings,
            uncertainties=uncertainties,
            sources=evidence,
            language=language,
        )

        return ClaimVerdict(
            claim_id="",
            claim_text=claim_text,
            verdict=verdict,
            explanation=explanation,
            evidence_assessment=assessment,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            uncertainties=uncertainties,
        )


# Singleton
verification_engine = VerificationEngine()
