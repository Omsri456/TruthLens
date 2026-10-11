/**
 * TruthLens AI — Verification Report Page.
 *
 * Displays detailed verification results for extracted claims:
 * - Claim text and assigned verdict badge
 * - Simple-language explanation
 * - Supporting and contradicting evidence cards with traceable source links
 * - Uncertainties and nuance callouts
 */

import { useEffect, useState } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  HelpCircle,
  ArrowLeft,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Share2,
  FileText,
  Loader2,
  AlertCircle,
  Check,
} from 'lucide-react';
import { getVerification } from '../services/api';
import type { VerificationReport, ClaimVerdict, Verdict } from '../types';

function getVerdictIcon(verdict: Verdict) {
  switch (verdict) {
    case 'VERIFIED':
      return <CheckCircle2 size={16} />;
    case 'FALSE':
      return <XCircle size={16} />;
    case 'OUTDATED':
      return <Clock size={16} />;
    case 'PARTIALLY_SUPPORTED':
      return <AlertTriangle size={16} />;
    case 'CANNOT_BE_CONFIRMED':
    default:
      return <HelpCircle size={16} />;
  }
}

function formatVerdictLabel(verdict: Verdict): string {
  switch (verdict) {
    case 'VERIFIED':
      return 'Verified';
    case 'FALSE':
      return 'False';
    case 'OUTDATED':
      return 'Outdated';
    case 'PARTIALLY_SUPPORTED':
      return 'Partially Supported';
    case 'CANNOT_BE_CONFIRMED':
      return 'Cannot Be Confirmed';
    default:
      return verdict;
  }
}

function formatAssessment(assessment: string): string {
  switch (assessment) {
    case 'strong_evidence':
      return 'Strong Evidence';
    case 'limited_evidence':
      return 'Limited Evidence';
    case 'conflicting_evidence':
      return 'Conflicting Evidence';
    case 'insufficient_evidence':
      return 'Insufficient Evidence';
    default:
      return assessment.replace('_', ' ');
  }
}

export function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();

  const [report, setReport] = useState<VerificationReport | null>(
    (location.state as { report?: VerificationReport })?.report || null
  );
  const [loading, setLoading] = useState<boolean>(!report && !!id);
  const [error, setError] = useState<string | null>(null);
  const [expandedClaims, setExpandedClaims] = useState<Record<string, boolean>>({});
  const [showOriginal, setShowOriginal] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (!report && id) {
      setLoading(true);
      getVerification(id)
        .then((data) => {
          setReport(data);
          setError(null);
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : 'Failed to load report.');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [id, report]);

  // Expand all claims by default when report loads
  useEffect(() => {
    if (report?.claims) {
      const initial: Record<string, boolean> = {};
      report.claims.forEach((c) => {
        initial[c.claim_id] = true;
      });
      setExpandedClaims(initial);
    }
  }, [report]);

  const toggleClaim = (claimId: string) => {
    setExpandedClaims((prev) => ({
      ...prev,
      [claimId]: !prev[claimId],
    }));
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="loading-overlay">
        <Loader2 className="spinner" size={36} />
        <p className="loading-text">Loading verification report...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="card" style={{ maxWidth: 600, margin: '40px auto' }}>
        <div className="error-message">
          <AlertCircle size={20} />
          <div>
            <strong>Unable to view report</strong>
            <p style={{ marginTop: 4 }}>{error || 'Report not found.'}</p>
          </div>
        </div>
        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Link to="/" className="btn btn-primary">
            <ArrowLeft size={16} /> Return to Verify
          </Link>
        </div>
      </div>
    );
  }

  const claimCount = report.claims?.length || 0;
  const verifiedCount = report.claims?.filter((c) => c.verdict === 'VERIFIED').length || 0;
  const falseCount = report.claims?.filter((c) => c.verdict === 'FALSE').length || 0;

  return (
    <div>
      {/* Top Bar Navigation */}
      <div className="flex-between mb-lg">
        <Link to="/" className="btn btn-secondary" style={{ padding: '6px 14px' }}>
          <ArrowLeft size={16} /> New Verification
        </Link>
        <button onClick={handleCopyLink} className="btn btn-secondary" style={{ padding: '6px 14px' }}>
          {copied ? <Check size={16} color="#0f8a4f" /> : <Share2 size={16} />}
          {copied ? 'Link Copied' : 'Share Report'}
        </button>
      </div>

      {/* Report Header */}
      <div className="report-header card mb-lg">
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8, flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: '0.75rem',
                textTransform: 'uppercase',
                fontWeight: 700,
                letterSpacing: '0.05em',
                color: 'var(--color-text-muted)',
                background: 'var(--color-surface-hover)',
                padding: '2px 8px',
                borderRadius: 4,
              }}
            >
              Mode: {report.input_type}
            </span>
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                letterSpacing: '0.03em',
                color: 'var(--color-accent)',
                background: 'var(--color-accent-light)',
                padding: '2px 8px',
                borderRadius: 4,
              }}
            >
              Lang: {report.language === 'hi' ? 'Hindi (हिंदी)' : report.language === 'mr' ? 'Marathi (मराठी)' : 'English'}
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
              {new Date(report.created_at).toLocaleString()}
            </span>
          </div>

          <h1 className="page-title" style={{ fontSize: '1.4rem' }}>
            Verification Assessment Report
          </h1>

          <p style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)', marginTop: 4 }}>
            Found {claimCount} factual claim{claimCount === 1 ? '' : 's'}.{' '}
            {verifiedCount > 0 && <span style={{ color: 'var(--color-verified)', fontWeight: 600 }}>{verifiedCount} verified. </span>}
            {falseCount > 0 && <span style={{ color: 'var(--color-false)', fontWeight: 600 }}>{falseCount} false. </span>}
          </p>

          {/* Collapsible Original / Extracted Input */}
          <div style={{ marginTop: 14 }}>
            <button
              onClick={() => setShowOriginal(!showOriginal)}
              className="expand-toggle"
              type="button"
            >
              <FileText size={14} />
              {showOriginal ? 'Hide original content' : 'View submitted content'}
              {showOriginal ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {showOriginal && (
              <div className="mt-sm">
                {report.original_input && (
                  <div>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 }}>
                      SUBMITTED INPUT:
                    </div>
                    <div className="report-input-preview">{report.original_input}</div>
                  </div>
                )}
                {report.extracted_text && report.extracted_text !== report.original_input && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-accent)', marginBottom: 4 }}>
                      EXTRACTED TEXT:
                    </div>
                    <div className="extracted-text-preview">{report.extracted_text}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Error or Notice Banner */}
      {report.error_message && (
        <div className={report.status === 'failed' ? 'error-message mb-lg' : 'info-message mb-lg'}>
          <AlertCircle size={20} style={{ flexShrink: 0, marginTop: 2 }} />
          <div>
            <strong>{report.status === 'failed' ? 'Verification Notice' : 'System Note'}</strong>
            <p style={{ marginTop: 4, margin: 0 }}>{report.error_message}</p>
          </div>
        </div>
      )}

      {/* No Claims Case */}
      {claimCount === 0 && !report.error_message && (
        <div className="card empty-state">
          <HelpCircle className="empty-state-icon" size={48} />
          <h2 className="empty-state-title">No verifiable claims identified</h2>
          <p className="empty-state-text">
            The submitted content did not contain distinct factual claims (e.g. opinions, greetings, or questions).
          </p>
        </div>
      )}

      {/* Claims List */}
      {report.claims?.map((claim: ClaimVerdict, index: number) => {
        const isExpanded = !!expandedClaims[claim.claim_id];
        const verdictClass = `verdict-${claim.verdict}`;

        return (
          <div key={claim.claim_id || index} className="claim-section">
            <div className="claim-header" onClick={() => toggleClaim(claim.claim_id)}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1 }}>
                <span
                  style={{
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    color: 'var(--color-text-muted)',
                  }}
                >
                  #{index + 1}
                </span>
                <span className="claim-text">{claim.claim_text}</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div className={`verdict-badge ${verdictClass}`}>
                  {getVerdictIcon(claim.verdict)}
                  <span>{formatVerdictLabel(claim.verdict)}</span>
                </div>
                <button
                  type="button"
                  className="expand-toggle"
                  style={{ padding: 4 }}
                  aria-label="Toggle claim details"
                >
                  {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </button>
              </div>
            </div>

            {isExpanded && (
              <div className="claim-body">
                {/* Explanation */}
                <div className="claim-explanation">
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-accent)', marginBottom: 6 }}>
                    Investigation Explanation:
                  </div>
                  <p style={{ margin: 0 }}>{claim.explanation}</p>
                </div>

                {/* Evidence Quality Assessment */}
                {claim.evidence_assessment && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                      Evidence Assessment:
                    </span>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        padding: '2px 8px',
                        borderRadius: 12,
                        background: 'var(--color-surface-hover)',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      {formatAssessment(claim.evidence_assessment)}
                    </span>
                  </div>
                )}

                {/* Supporting Evidence */}
                {claim.supporting_evidence && claim.supporting_evidence.length > 0 && (
                  <div className="mb-lg">
                    <div className="evidence-section-title" style={{ color: 'var(--color-verified)' }}>
                      Supporting Sources ({claim.supporting_evidence.length})
                    </div>
                    <div className="evidence-list">
                      {claim.supporting_evidence.map((ev, i) => (
                        <div key={ev.source_id || i} className="evidence-card supports">
                          <div className="evidence-header">
                            <span className="evidence-title">
                              <a href={ev.url} target="_blank" rel="noopener noreferrer">
                                {ev.title} <ExternalLink size={12} style={{ display: 'inline', verticalAlign: 'middle' }} />
                              </a>
                            </span>
                            {ev.publisher && <span className="evidence-publisher">{ev.publisher}</span>}
                          </div>
                          <p className="evidence-snippet">{ev.snippet}</p>
                          <div className="evidence-meta">
                            {ev.published_at && <span>Published: {ev.published_at}</span>}
                            <span>Retrieved: {new Date(ev.retrieved_at).toLocaleDateString()}</span>
                            {ev.source_type && <span>Type: {ev.source_type}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Contradicting Evidence */}
                {claim.contradicting_evidence && claim.contradicting_evidence.length > 0 && (
                  <div className="mb-lg">
                    <div className="evidence-section-title" style={{ color: 'var(--color-false)' }}>
                      Contradicting Sources ({claim.contradicting_evidence.length})
                    </div>
                    <div className="evidence-list">
                      {claim.contradicting_evidence.map((ev, i) => (
                        <div key={ev.source_id || i} className="evidence-card contradicts">
                          <div className="evidence-header">
                            <span className="evidence-title">
                              <a href={ev.url} target="_blank" rel="noopener noreferrer">
                                {ev.title} <ExternalLink size={12} style={{ display: 'inline', verticalAlign: 'middle' }} />
                              </a>
                            </span>
                            {ev.publisher && <span className="evidence-publisher">{ev.publisher}</span>}
                          </div>
                          <p className="evidence-snippet">{ev.snippet}</p>
                          <div className="evidence-meta">
                            {ev.published_at && <span>Published: {ev.published_at}</span>}
                            <span>Retrieved: {new Date(ev.retrieved_at).toLocaleDateString()}</span>
                            {ev.source_type && <span>Type: {ev.source_type}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Uncertainties */}
                {claim.uncertainties && claim.uncertainties.length > 0 && (
                  <div>
                    <div className="evidence-section-title">
                      Nuances &amp; Uncertainties
                    </div>
                    <ul className="uncertainties-list">
                      {claim.uncertainties.map((u, i) => (
                        <li key={i}>{u}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
