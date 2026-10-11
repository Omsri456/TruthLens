/**
 * TruthLens AI — TypeScript type definitions.
 * Mirrors the backend Pydantic schemas.
 */

export type Verdict =
  | 'VERIFIED'
  | 'FALSE'
  | 'OUTDATED'
  | 'PARTIALLY_SUPPORTED'
  | 'CANNOT_BE_CONFIRMED';

export type EvidenceAssessment =
  | 'strong_evidence'
  | 'limited_evidence'
  | 'conflicting_evidence'
  | 'insufficient_evidence';

export type EvidenceRelationship =
  | 'supports'
  | 'contradicts'
  | 'partially_relevant'
  | 'unrelated';

export type InputType = 'text' | 'image' | 'pdf' | 'audio' | 'url';

export type ProcessingStatus =
  | 'pending'
  | 'extracting'
  | 'searching'
  | 'analyzing'
  | 'completed'
  | 'failed';

export interface EvidenceItem {
  source_id: string;
  title: string;
  url: string;
  publisher?: string;
  published_at?: string;
  retrieved_at: string;
  snippet: string;
  relevance?: number;
  source_type?: string;
  relationship: EvidenceRelationship;
}

export interface ClaimVerdict {
  claim_id: string;
  claim_text: string;
  verdict: Verdict;
  explanation: string;
  evidence_assessment: EvidenceAssessment;
  supporting_evidence: EvidenceItem[];
  contradicting_evidence: EvidenceItem[];
  uncertainties: string[];
}

export interface VerificationReport {
  verification_id: string;
  status: ProcessingStatus;
  input_type: InputType;
  original_input?: string;
  extracted_text?: string;
  language: string;
  claims: ClaimVerdict[];
  created_at: string;
  error_message?: string;
}

export interface HistoryEntry {
  verification_id: string;
  input_type: InputType;
  claim_summary: string;
  verdict_summary?: string;
  language?: string;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  llm_configured: boolean;
  search_configured: boolean;
}
