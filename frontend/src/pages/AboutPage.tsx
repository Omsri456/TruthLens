/**
 * TruthLens AI — About & Methodology Page.
 *
 * Explains the verification architecture, verdict taxonomy,
 * evidence grounding pipeline, and system health status.
 */

import { useEffect, useState } from 'react';
import {
  ShieldCheck,
  Database,
  Cpu,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  HelpCircle,
  Server,
} from 'lucide-react';
import { getHealth } from '../services/api';
import type { HealthResponse } from '../types';

export function AboutPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    getHealth()
      .then((data) => setHealth(data))
      .catch(() => setHealth(null));
  }, []);

  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>
      <div className="mb-xl">
        <h1 className="page-title">About TruthLens AI</h1>
        <p className="page-subtitle">
          An evidence-grounded multimodal claim verification system designed to inspect forwarded content,
          extract factual claims, and cross-reference them against authoritative reporting.
        </p>
      </div>

      {/* System Health Card */}
      <div className="card mb-xl">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <Server size={18} color="var(--color-accent)" />
          <h2 style={{ fontSize: '1rem', fontWeight: 600, margin: 0 }}>System Status</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
          <div style={{ background: 'var(--color-bg)', padding: 12, borderRadius: 8 }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Backend API</div>
            <div style={{ fontWeight: 600, color: health?.status === 'ok' ? 'var(--color-verified)' : 'var(--color-false)' }}>
              {health?.status === 'ok' ? '● Online (v' + health.version + ')' : '○ Disconnected'}
            </div>
          </div>
          <div style={{ background: 'var(--color-bg)', padding: 12, borderRadius: 8 }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Gemini LLM</div>
            <div style={{ fontWeight: 600, color: health?.llm_configured ? 'var(--color-verified)' : 'var(--color-outdated)' }}>
              {health?.llm_configured ? '● Configured' : '○ Missing API Key'}
            </div>
          </div>
          <div style={{ background: 'var(--color-bg)', padding: 12, borderRadius: 8 }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Google Search API</div>
            <div style={{ fontWeight: 600, color: health?.search_configured ? 'var(--color-verified)' : 'var(--color-outdated)' }}>
              {health?.search_configured ? '● Configured' : '○ Missing Engine ID'}
            </div>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="about-section card mb-xl">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <Cpu size={20} color="var(--color-accent)" />
          <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0 }}>Verification Pipeline</h2>
        </div>
        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6, marginBottom: 16 }}>
          TruthLens AI treats fact verification as an investigative process with strict evidence grounding:
        </p>
        <ol style={{ paddingLeft: 20, color: 'var(--color-text-secondary)', lineHeight: 1.8 }}>
          <li>
            <strong>Multimodal Ingestion:</strong> Normalizes inputs from plain text, images (Gemini Vision OCR),
            PDF files (PyMuPDF parser), audio recordings (Gemini speech transcription), or URLs (safe SSRF-protected parser).
          </li>
          <li>
            <strong>Factual Claim Extraction:</strong> The language model isolates verifiable claims from commentary,
            opinions, greetings, or speculation.
          </li>
          <li>
            <strong>Real Evidence Retrieval:</strong> Search queries are automatically constructed from claims to retrieve
            real, verifiable search results from reliable public sources.
          </li>
          <li>
            <strong>Adversarial Analysis:</strong> The system classifies retrieved evidence into supporting and contradicting
            categories, testing the claims against primary sources and official reports.
          </li>
          <li>
            <strong>Explainable Verdict &amp; Traceability:</strong> Produces a plain-language explanation in the user's selected
            language (English, Hindi, Marathi) with source citations and known uncertainties.
          </li>
        </ol>
      </div>

      {/* Verdict Taxonomy */}
      <div className="about-section card mb-xl">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <ShieldCheck size={20} color="var(--color-accent)" />
          <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0 }}>Verdict Taxonomy</h2>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <span className="verdict-badge verdict-VERIFIED" style={{ flexShrink: 0, marginTop: 2 }}>
              <CheckCircle2 size={14} /> Verified
            </span>
            <div style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
              The claim is directly confirmed by authoritative records, primary data, or credible mainstream coverage.
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <span className="verdict-badge verdict-FALSE" style={{ flexShrink: 0, marginTop: 2 }}>
              <XCircle size={14} /> False
            </span>
            <div style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
              The claim is contradicted by credible evidence, fabricated, or factually incorrect.
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <span className="verdict-badge verdict-OUTDATED" style={{ flexShrink: 0, marginTop: 2 }}>
              <Clock size={14} /> Outdated
            </span>
            <div style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
              The claim was historically true or accurate in a past context, but is no longer valid due to policy updates, new findings, or changed circumstances.
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <span className="verdict-badge verdict-PARTIALLY_SUPPORTED" style={{ flexShrink: 0, marginTop: 2 }}>
              <AlertTriangle size={14} /> Partially Supported
            </span>
            <div style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
              Parts of the claim are accurate, but critical details, numbers, dates, or context are distorted or exaggerated.
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <span className="verdict-badge verdict-CANNOT_BE_CONFIRMED" style={{ flexShrink: 0, marginTop: 2 }}>
              <HelpCircle size={14} /> Cannot Be Confirmed
            </span>
            <div style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
              Reliable evidence is insufficient or contradictory. The system avoids guessing and transparently identifies the gaps in available reporting.
            </div>
          </div>
        </div>
      </div>

      {/* Responsible AI Principles */}
      <div className="about-section card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <Database size={20} color="var(--color-accent)" />
          <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0 }}>Responsible AI Guardrails</h2>
        </div>
        <ul style={{ paddingLeft: 20, color: 'var(--color-text-secondary)', lineHeight: 1.7, fontSize: '0.9rem' }}>
          <li>No hallucinated citations — all referenced links come directly from actual search retrieval results.</li>
          <li>Never return ungrounded confidence — claims lacking sufficient reporting are marked "Cannot Be Confirmed".</li>
          <li>Security-first architecture: URL parser includes SSRF protection preventing access to local network hosts.</li>
          <li>Privacy-friendly design: Local SQLite persistence for audit history with zero user tracking.</li>
        </ul>
      </div>
    </div>
  );
}
