"""
TruthLens AI — LLM Provider (Gemini).

Encapsulates all LLM interactions behind a clean interface.
Three distinct operations:
  1. extract_claims — pull structured factual claims from text
  2. analyze_evidence — compare a claim against retrieved evidence
  3. generate_explanation — produce a human-readable explanation

All prompts are defined in this module so they can be versioned and reviewed.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import google.generativeai as genai

from app.core.config import settings
from app.schemas.models import (
    ClaimExtractionResult,
    EvidenceAssessment,
    EvidenceItem,
    EvidenceRelationship,
    Verdict,
)

logger = logging.getLogger(__name__)


# ── Prompts ─────────────────────────────────────────────────────────

CLAIM_EXTRACTION_PROMPT = """You are a factual claim extraction engine for a fact-checking system.

Given the following user-submitted content, extract every distinct factual claim.

RULES:
- Extract ONLY factual claims (statements that can be verified as true or false).
- Do NOT extract opinions, questions, greetings, or instructions.
- Separate compound claims into individual claims.
- Preserve specific numbers, dates, names, locations, amounts, and conditions exactly as stated.
- Do NOT add information that is not present in the original text.
- Do NOT evaluate whether claims are true or false — just extract them.
- If there are no factual claims, return an empty claims list.
- Detect the language of the input.

Respond with ONLY valid JSON matching this schema:
{{
  "claims": [
    {{
      "claim_id": "claim_1",
      "text": "The exact factual claim",
      "claim_type": "category (e.g., government_scheme, health, finance, science, general)",
      "entities": ["named entities mentioned"],
      "amounts": ["any monetary amounts or quantities"],
      "dates": ["any dates or time periods"],
      "locations": ["any locations mentioned"],
      "requires_current_information": true
    }}
  ],
  "input_language": "detected language code (e.g., en, hi, mr)",
  "extraction_notes": "any notes about extraction quality"
}}

USER CONTENT:
{content}"""

EVIDENCE_ANALYSIS_PROMPT = """You are an evidence analysis engine for a fact-checking system.

CLAIM TO VERIFY:
"{claim_text}"

RETRIEVED EVIDENCE:
{evidence_json}

Analyze each piece of evidence against the claim. Consider:
1. Does the evidence directly support, contradict, or partially address the claim?
2. Are there differences in specific numbers, dates, eligibility, or scope?
3. Is the evidence from a primary/authoritative source for this topic?
4. Is the evidence current or potentially outdated?
5. Do different sources agree or conflict?

IMPORTANT:
- Base your analysis ONLY on the provided evidence.
- Do NOT use your own knowledge to verify the claim.
- If evidence is insufficient, say so — do NOT guess.
- Clearly state what the evidence does and does not establish.

For each evidence item, assign a relationship:
- "supports" — evidence directly supports the claim
- "contradicts" — evidence directly contradicts the claim
- "partially_relevant" — evidence is related but doesn't fully confirm or deny

Then assign an overall verdict from EXACTLY one of:
- "VERIFIED" — evidence sufficiently supports the specific claim
- "FALSE" — credible evidence directly contradicts the claim
- "OUTDATED" — claim was once accurate but is no longer current
- "PARTIALLY_SUPPORTED" — some parts supported, but important details are wrong/missing
- "CANNOT_BE_CONFIRMED" — insufficient, ambiguous, or conflicting evidence

And an evidence assessment:
- "strong_evidence" — multiple authoritative sources agree
- "limited_evidence" — some relevant evidence but not conclusive
- "conflicting_evidence" — sources disagree
- "insufficient_evidence" — not enough evidence to make a determination

Respond with ONLY valid JSON:
{{
  "verdict": "VERDICT_CATEGORY",
  "evidence_assessment": "assessment_category",
  "evidence_relationships": [
    {{
      "source_id": "the source_id from the evidence",
      "relationship": "supports|contradicts|partially_relevant",
      "reasoning": "brief explanation of why"
    }}
  ],
  "key_findings": "what the evidence establishes",
  "uncertainties": ["list of things that remain uncertain"],
  "explanation_points": ["key points for the final explanation"]
}}"""

EXPLANATION_PROMPT = """You are an explanation writer for a fact-checking system.

Write a clear, simple explanation for a general audience.

ORIGINAL CLAIM: "{claim_text}"
VERDICT: {verdict}
EVIDENCE ASSESSMENT: {evidence_assessment}
KEY FINDINGS: {key_findings}
UNCERTAINTIES: {uncertainties}

SOURCES USED:
{sources_summary}

Write the explanation in {language}. Follow these rules:
1. Start with what the claim says.
2. State what the evidence shows.
3. Explain what is correct, incorrect, uncertain, or outdated.
4. Reference specific sources by their title (do NOT invent sources).
5. Keep it concise (3-5 sentences).
6. Do NOT add any facts not present in the evidence.
7. If evidence is insufficient, say so clearly.

Respond with ONLY valid JSON:
{{
  "explanation": "The full explanation text"
}}"""


class LLMProvider:
    """Gemini-backed LLM provider for the verification pipeline."""

    def __init__(self):
        if not settings.is_llm_configured:
            logger.warning("Gemini API key not configured. LLM features will be unavailable.")
            self._model = None
            return

        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(
            settings.gemini_model,
            generation_config=genai.GenerationConfig(
                temperature=0.1,  # Low variance for factual analysis
                top_p=0.95,
                max_output_tokens=4096,
            ),
        )
        logger.info(f"LLM provider initialized with model: {settings.gemini_model}")

    @property
    def is_available(self) -> bool:
        return self._model is not None

    def _call_llm(self, prompt: str, max_retries: int = 2) -> str:
        """Send a prompt to the LLM with bounded retries."""
        if not self.is_available:
            raise RuntimeError(
                "LLM is not configured. Set GEMINI_API_KEY in your .env file."
            )

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self._model.generate_content(prompt)
                if response.text:
                    return response.text.strip()
                raise ValueError("Empty response from LLM")
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
                if attempt == max_retries:
                    break

        raise RuntimeError(f"LLM call failed after {max_retries + 1} attempts: {last_error}")

    def _parse_json_response(self, raw: str) -> dict:
        """Extract JSON from LLM response, handling markdown code fences."""
        text = raw.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        return json.loads(text)

    async def extract_claims(self, text: str, language: str = "en") -> ClaimExtractionResult:
        """Extract factual claims from user-submitted text."""
        prompt = CLAIM_EXTRACTION_PROMPT.format(content=text)
        raw = self._call_llm(prompt)

        try:
            data = self._parse_json_response(raw)
            return ClaimExtractionResult(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse claim extraction response: {e}\nRaw: {raw[:500]}")
            # Return empty result rather than crashing
            return ClaimExtractionResult(
                claims=[],
                input_language=language,
                extraction_notes=f"Extraction parsing failed: {str(e)}",
            )

    async def analyze_evidence(
        self,
        claim_text: str,
        evidence: list[EvidenceItem],
    ) -> dict:
        """Analyze retrieved evidence against a specific claim."""
        evidence_json = json.dumps(
            [e.model_dump(exclude={"relevance"}) for e in evidence],
            indent=2,
        )
        prompt = EVIDENCE_ANALYSIS_PROMPT.format(
            claim_text=claim_text,
            evidence_json=evidence_json,
        )
        raw = self._call_llm(prompt)

        try:
            data = self._parse_json_response(raw)
            # Validate verdict and assessment
            data["verdict"] = Verdict(data.get("verdict", "CANNOT_BE_CONFIRMED"))
            data["evidence_assessment"] = EvidenceAssessment(
                data.get("evidence_assessment", "insufficient_evidence")
            )
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse evidence analysis: {e}\nRaw: {raw[:500]}")
            return {
                "verdict": Verdict.CANNOT_BE_CONFIRMED,
                "evidence_assessment": EvidenceAssessment.INSUFFICIENT_EVIDENCE,
                "evidence_relationships": [],
                "key_findings": "Analysis could not be completed due to a processing error.",
                "uncertainties": ["The analysis could not be completed."],
                "explanation_points": [],
            }

    async def generate_explanation(
        self,
        claim_text: str,
        verdict: Verdict,
        evidence_assessment: EvidenceAssessment,
        key_findings: str,
        uncertainties: list[str],
        sources: list[EvidenceItem],
        language: str = "en",
    ) -> str:
        """Generate a plain-language explanation grounded in evidence."""
        sources_summary = "\n".join(
            f"- {s.title} ({s.url})" for s in sources
        ) or "No sources available."

        prompt = EXPLANATION_PROMPT.format(
            claim_text=claim_text,
            verdict=verdict.value,
            evidence_assessment=evidence_assessment.value,
            key_findings=key_findings,
            uncertainties=json.dumps(uncertainties),
            sources_summary=sources_summary,
            language=self._language_name(language),
        )
        raw = self._call_llm(prompt)

        try:
            data = self._parse_json_response(raw)
            return data.get("explanation", raw)
        except (json.JSONDecodeError, Exception):
            # If JSON parsing fails, use the raw text as explanation
            return raw

    async def extract_text_from_image(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Use Gemini vision to extract text from an image."""
        if not self.is_available:
            raise RuntimeError("LLM is not configured.")

        prompt = (
            "Extract ALL readable text from this image exactly as written. "
            "Preserve the original language, formatting, numbers, and special characters. "
            "If no text is readable, respond with: [NO_TEXT_FOUND]. "
            "Do NOT add any commentary or interpretation — only the extracted text."
        )

        import PIL.Image
        import io
        image = PIL.Image.open(io.BytesIO(image_bytes))

        response = self._model.generate_content([prompt, image])
        text = response.text.strip() if response.text else ""

        if text == "[NO_TEXT_FOUND]":
            return ""
        return text

    async def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """Use Gemini to transcribe audio content."""
        if not self.is_available:
            raise RuntimeError("LLM is not configured.")

        prompt = (
            "Transcribe the speech in this audio file. "
            "Preserve the original language. "
            "If no speech is detected, respond with: [NO_SPEECH_FOUND]. "
            "Output ONLY the transcript text, nothing else."
        )

        # Upload inline audio data
        import base64
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        audio_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": audio_b64,
            }
        }

        response = self._model.generate_content([prompt, audio_part])
        text = response.text.strip() if response.text else ""

        if text == "[NO_SPEECH_FOUND]":
            return ""
        return text

    @staticmethod
    def _language_name(code: str) -> str:
        """Map language code to full name."""
        mapping = {
            "en": "English",
            "hi": "Hindi",
            "mr": "Marathi",
        }
        return mapping.get(code, "English")


# Singleton
llm_provider = LLMProvider()
