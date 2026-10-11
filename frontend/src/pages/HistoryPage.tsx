/**
 * TruthLens AI — History Page.
 *
 * Displays previous verification runs stored in the local SQLite database.
 * Supports keyword search, media type filters, entry deletion, and history clearing.
 */

import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Clock,
  Search,
  ExternalLink,
  Loader2,
  AlertCircle,
  FileText,
  Image,
  Mic,
  Link2,
  RefreshCw,
  Trash2,
  Filter,
} from 'lucide-react';
import { getHistory, deleteVerification, clearHistory } from '../services/api';
import type { HistoryEntry, InputType } from '../types';

function getInputIcon(type: InputType) {
  switch (type) {
    case 'image':
      return <Image size={16} />;
    case 'pdf':
      return <FileText size={16} />;
    case 'audio':
      return <Mic size={16} />;
    case 'url':
      return <Link2 size={16} />;
    case 'text':
    default:
      return <Search size={16} />;
  }
}

function getLanguageLabel(code?: string): string {
  switch (code) {
    case 'hi':
      return 'हिंदी';
    case 'mr':
      return 'मराठी';
    case 'en':
    default:
      return 'EN';
  }
}

export function HistoryPage() {
  const navigate = useNavigate();
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  const fetchHistory = () => {
    setLoading(true);
    setError(null);
    getHistory()
      .then((data) => {
        setHistory(data);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to fetch verification history.');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDeleteItem = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this verification record?')) return;

    try {
      setActionLoading(true);
      await deleteVerification(id);
      setHistory((prev) => prev.filter((item) => item.verification_id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete record.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Are you sure you want to clear all verification records? This action cannot be undone.')) return;

    try {
      setActionLoading(true);
      await clearHistory();
      setHistory([]);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to clear history.');
    } finally {
      setActionLoading(false);
    }
  };

  const filtered = history.filter((item) => {
    const matchesSearch =
      item.claim_summary.toLowerCase().includes(searchFilter.toLowerCase()) ||
      (item.verdict_summary && item.verdict_summary.toLowerCase().includes(searchFilter.toLowerCase()));
    const matchesType = typeFilter === 'all' || item.input_type === typeFilter;
    return matchesSearch && matchesType;
  });

  return (
    <div>
      <div className="flex-between mb-lg" style={{ flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 className="page-title">Verification History</h1>
          <p className="page-subtitle" style={{ marginBottom: 0 }}>
            Audit log of previously analyzed claims, evidence sources, and verdicts.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {history.length > 0 && (
            <button
              onClick={handleClearAll}
              disabled={loading || actionLoading}
              className="btn btn-secondary"
              style={{ padding: '8px 12px', color: 'var(--color-false)' }}
              title="Clear all records"
            >
              <Trash2 size={14} /> Clear All
            </button>
          )}
          <button
            onClick={fetchHistory}
            disabled={loading || actionLoading}
            className="btn btn-secondary"
            style={{ padding: '8px 14px' }}
          >
            <RefreshCw size={14} className={loading ? 'spinner' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* Search & Media Type Filter Bar */}
      <div className="card mb-lg" style={{ padding: '16px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Search size={18} color="var(--color-text-muted)" />
            <input
              type="text"
              className="input-field"
              style={{ border: 'none', padding: '6px 0', boxShadow: 'none' }}
              placeholder="Search past claims, source URLs, or verdicts..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
            />
          </div>

          {/* Type Filter Pills */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', borderTop: '1px solid var(--color-border-light)', paddingTop: 12 }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: 4, marginRight: 6 }}>
              <Filter size={12} /> Filter:
            </span>
            {['all', 'text', 'image', 'pdf', 'audio', 'url'].map((mode) => (
              <button
                key={mode}
                onClick={() => setTypeFilter(mode)}
                className={`tab-btn ${typeFilter === mode ? 'active' : ''}`}
                style={{
                  padding: '4px 10px',
                  borderRadius: 16,
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="loading-overlay">
          <Loader2 className="spinner" size={36} />
          <p className="loading-text">Loading history records...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="error-message mb-lg">
          <AlertCircle size={20} />
          <div>{error}</div>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filtered.length === 0 && (
        <div className="card empty-state">
          <Clock className="empty-state-icon" size={48} />
          <h2 className="empty-state-title">
            {searchFilter || typeFilter !== 'all'
              ? 'No matching verifications found'
              : 'No verification records yet'}
          </h2>
          <p className="empty-state-text">
            {searchFilter || typeFilter !== 'all'
              ? 'Try adjusting your search terms or filter mode.'
              : 'Submit claims on the verify workspace to see past results here.'}
          </p>
          {!searchFilter && typeFilter === 'all' && (
            <div style={{ marginTop: 20 }}>
              <Link to="/" className="btn btn-primary">
                Start First Verification
              </Link>
            </div>
          )}
        </div>
      )}

      {/* History Items */}
      {!loading && !error && filtered.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {filtered.map((item) => (
            <div
              key={item.verification_id}
              onClick={() => navigate(`/report/${item.verification_id}`)}
              className="history-item"
              style={{ position: 'relative' }}
            >
              <div className="history-meta">
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 4, color: 'var(--color-accent)' }}>
                  {getInputIcon(item.input_type)}
                </div>
                <div className="history-date">
                  {new Date(item.created_at).toLocaleDateString([], {
                    month: 'short',
                    day: 'numeric',
                  })}
                </div>
                <div className="history-type">{item.input_type}</div>
              </div>

              <div className="history-summary">
                <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 4 }}>
                  {item.claim_summary}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {item.verdict_summary && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                      Verdict: <strong>{item.verdict_summary}</strong>
                    </span>
                  )}
                  <span
                    style={{
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      color: 'var(--color-accent)',
                      background: 'var(--color-accent-light)',
                      padding: '1px 6px',
                      borderRadius: 4,
                    }}
                  >
                    {getLanguageLabel(item.language)}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
                <button
                  onClick={(e) => handleDeleteItem(e, item.verification_id)}
                  className="expand-toggle"
                  style={{ padding: 6, color: 'var(--color-text-muted)' }}
                  title="Delete this record"
                  aria-label="Delete record"
                >
                  <Trash2 size={16} />
                </button>
                <div style={{ color: 'var(--color-accent)' }}>
                  <ExternalLink size={16} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
