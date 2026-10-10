/**
 * TruthLens AI — History Page.
 *
 * Displays previous verification runs stored in the local database.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
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
} from 'lucide-react';
import { getHistory } from '../services/api';
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

export function HistoryPage() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>('');

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

  const filtered = history.filter((item) =>
    item.claim_summary.toLowerCase().includes(searchFilter.toLowerCase()) ||
    (item.verdict_summary && item.verdict_summary.toLowerCase().includes(searchFilter.toLowerCase()))
  );

  return (
    <div>
      <div className="flex-between mb-lg">
        <div>
          <h1 className="page-title">Verification History</h1>
          <p className="page-subtitle" style={{ marginBottom: 0 }}>
            Audit log of previously analyzed claims and reports.
          </p>
        </div>
        <button
          onClick={fetchHistory}
          disabled={loading}
          className="btn btn-secondary"
          style={{ padding: '8px 14px' }}
        >
          <RefreshCw size={14} className={loading ? 'spinner' : ''} /> Refresh
        </button>
      </div>

      {/* Search Bar */}
      <div className="card mb-lg" style={{ padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Search size={18} color="var(--color-text-muted)" />
          <input
            type="text"
            className="input-field"
            style={{ border: 'none', padding: '6px 0', boxShadow: 'none' }}
            placeholder="Search past claims or verdicts..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
          />
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
            {searchFilter ? 'No matching verifications found' : 'No verifications yet'}
          </h2>
          <p className="empty-state-text">
            {searchFilter
              ? 'Try a different search keyword.'
              : 'Submit claims on the verify workspace to see past results here.'}
          </p>
          {!searchFilter && (
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
            <Link
              key={item.verification_id}
              to={`/report/${item.verification_id}`}
              className="history-item"
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
                {item.verdict_summary && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                    {item.verdict_summary}
                  </div>
                )}
              </div>

              <div style={{ flexShrink: 0, color: 'var(--color-text-muted)' }}>
                <ExternalLink size={16} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
