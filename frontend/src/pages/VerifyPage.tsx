/**
 * TruthLens AI — Verification Workspace Page.
 *
 * The main page where users submit content for verification.
 * Supports 5 input modes: Text, Image, PDF, Audio, URL.
 */

import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Type,
  Image,
  FileText,
  Mic,
  Link2,
  Upload,
  X,
  AlertCircle,
  Search,
  Loader2,
  CheckCircle2,
  Globe,
} from 'lucide-react';
import {
  verifyText,
  verifyImage,
  verifyPdf,
  verifyAudio,
  verifyUrl,
} from '../services/api';
import type { VerificationReport } from '../types';

type InputMode = 'text' | 'image' | 'pdf' | 'audio' | 'url';

const TABS: { mode: InputMode; label: string; icon: React.ReactNode }[] = [
  { mode: 'text', label: 'Text', icon: <Type size={16} /> },
  { mode: 'image', label: 'Image', icon: <Image size={16} /> },
  { mode: 'pdf', label: 'PDF', icon: <FileText size={16} /> },
  { mode: 'audio', label: 'Audio', icon: <Mic size={16} /> },
  { mode: 'url', label: 'URL', icon: <Link2 size={16} /> },
];

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'Hindi' },
  { code: 'mr', label: 'Marathi' },
];

const LOADING_STEPS = [
  'Extracting factual claims...',
  'Searching for evidence...',
  'Analyzing evidence against claims...',
  'Generating explanation...',
];

export function VerifyPage() {
  const navigate = useNavigate();

  // State
  const [activeTab, setActiveTab] = useState<InputMode>('text');
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState('en');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // File accept types per mode
  const fileAccept: Record<string, string> = {
    image: 'image/png,image/jpeg,image/webp,image/gif',
    pdf: 'application/pdf',
    audio: 'audio/wav,audio/mpeg,audio/mp3,audio/mp4,audio/x-m4a,audio/ogg,audio/webm',
  };

  const fileHints: Record<string, string> = {
    image: 'PNG, JPEG, or WebP — max 10MB',
    pdf: 'PDF files — max 10MB, 50 pages',
    audio: 'WAV, MP3, M4A, OGG — max 10MB',
  };

  // Handlers
  const handleFileSelect = useCallback(
    (selectedFile: File | null) => {
      setFile(selectedFile);
      setError(null);
    },
    []
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) {
        handleFileSelect(droppedFile);
      }
    },
    [handleFileSelect]
  );

  const canSubmit = (): boolean => {
    if (isLoading) return false;
    switch (activeTab) {
      case 'text':
        return text.trim().length >= 10;
      case 'url':
        return (
          url.trim().length >= 10 &&
          (url.trim().startsWith('http://') || url.trim().startsWith('https://'))
        );
      case 'image':
      case 'pdf':
      case 'audio':
        return file !== null;
      default:
        return false;
    }
  };

  const handleSubmit = async () => {
    if (!canSubmit()) return;
    setError(null);
    setIsLoading(true);
    setLoadingStep(0);

    // Simulate step progress
    const stepInterval = setInterval(() => {
      setLoadingStep((prev) => Math.min(prev + 1, LOADING_STEPS.length - 1));
    }, 3000);

    try {
      let report: VerificationReport;

      switch (activeTab) {
        case 'text':
          report = await verifyText(text, language);
          break;
        case 'image':
          report = await verifyImage(file!, language);
          break;
        case 'pdf':
          report = await verifyPdf(file!, language);
          break;
        case 'audio':
          report = await verifyAudio(file!, language);
          break;
        case 'url':
          report = await verifyUrl(url, language);
          break;
        default:
          throw new Error('Unknown input type');
      }

      clearInterval(stepInterval);

      // Navigate to report page with the report data
      navigate(`/report/${report.verification_id}`, {
        state: { report },
      });
    } catch (err) {
      clearInterval(stepInterval);
      setError(err instanceof Error ? err.message : 'Verification failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      {/* Hero */}
      <div className="hero">
        <h1 className="hero-title">
          Verify claims with <span>evidence</span>
        </h1>
        <p className="hero-desc">
          Paste a forwarded message, upload a screenshot, PDF, audio note, or
          enter a URL. TruthLens AI will extract factual claims, search for
          evidence, and explain what's supported and what's not.
        </p>
      </div>

      {/* Verification Panel */}
      <div className="card" style={{ maxWidth: 800, margin: '0 auto' }}>
        {/* Tab Bar */}
        <div className="tab-bar" role="tablist" aria-label="Input type">
          {TABS.map((tab) => (
            <button
              key={tab.mode}
              role="tab"
              aria-selected={activeTab === tab.mode}
              className={`tab-btn ${activeTab === tab.mode ? 'active' : ''}`}
              onClick={() => {
                setActiveTab(tab.mode);
                setError(null);
              }}
              disabled={isLoading}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Input Area */}
        {isLoading ? (
          <div className="loading-overlay">
            <div className="spinner" />
            <p className="loading-text">
              Verifying your content…
            </p>
            <div className="loading-steps">
              {LOADING_STEPS.map((step, i) => (
                <div
                  key={i}
                  className={`loading-step ${
                    i === loadingStep
                      ? 'active'
                      : i < loadingStep
                        ? 'done'
                        : ''
                  }`}
                >
                  {i < loadingStep ? (
                    <CheckCircle2 size={14} />
                  ) : i === loadingStep ? (
                    <Loader2 size={14} className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                  ) : (
                    <span style={{ width: 14, display: 'inline-block' }} />
                  )}
                  {step}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* Text Input */}
            {activeTab === 'text' && (
              <textarea
                className="textarea-field"
                placeholder="Paste a forwarded WhatsApp message, news claim, or any factual statement you want to verify…"
                value={text}
                onChange={(e) => {
                  setText(e.target.value);
                  setError(null);
                }}
                aria-label="Text to verify"
                maxLength={10000}
              />
            )}

            {/* URL Input */}
            {activeTab === 'url' && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Globe size={18} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
                  <input
                    type="url"
                    className="input-field"
                    placeholder="https://example.com/article"
                    value={url}
                    onChange={(e) => {
                      setUrl(e.target.value);
                      setError(null);
                    }}
                    aria-label="URL to verify"
                  />
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: 8 }}>
                  Enter a URL to an article or webpage. The system will extract text
                  and verify claims found on the page.
                </p>
              </div>
            )}

            {/* File Upload (Image, PDF, Audio) */}
            {(activeTab === 'image' ||
              activeTab === 'pdf' ||
              activeTab === 'audio') && (
              <div>
                <div
                  className={`drop-zone ${isDragging ? 'dragging' : ''}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  role="button"
                  tabIndex={0}
                  aria-label={`Upload ${activeTab} file`}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      fileInputRef.current?.click();
                    }
                  }}
                >
                  <div className="drop-zone-icon">
                    <Upload size={32} />
                  </div>
                  <p className="drop-zone-text">
                    Drag & drop or click to select a file
                  </p>
                  <p className="drop-zone-hint">
                    {fileHints[activeTab]}
                  </p>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept={fileAccept[activeTab]}
                  onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
                  style={{ display: 'none' }}
                  aria-hidden="true"
                />

                {file && (
                  <div style={{ marginTop: 'var(--space-md)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
                    {activeTab === 'image' && (
                      <div style={{ maxWidth: 220, maxHeight: 160, overflow: 'hidden', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-sm)' }}>
                        <img
                          src={URL.createObjectURL(file)}
                          alt="Upload preview"
                          style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', maxHeight: 160 }}
                        />
                      </div>
                    )}
                    {activeTab === 'audio' && (
                      <div style={{ width: '100%', maxWidth: 360, marginTop: 4 }}>
                        <audio
                          controls
                          src={URL.createObjectURL(file)}
                          style={{ width: '100%', height: 36, borderRadius: 8 }}
                        />
                      </div>
                    )}
                    <div className="drop-zone-file">
                      <FileText size={16} />
                      <span className="drop-zone-file-name">
                        {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                      </span>
                      <button
                        className="drop-zone-file-remove"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleFileSelect(null);
                          if (fileInputRef.current) fileInputRef.current.value = '';
                        }}
                        aria-label="Remove file"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* Error */}
        {error && (
          <div className="error-message mt-md">
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 2 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Actions */}
        {!isLoading && (
          <div
            className="flex-between mt-lg"
            style={{ flexWrap: 'wrap', gap: 12 }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <label
                htmlFor="language-select"
                style={{
                  fontSize: '0.85rem',
                  color: 'var(--color-text-secondary)',
                }}
              >
                Explain in:
              </label>
              <select
                id="language-select"
                className="select-field"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.label}
                  </option>
                ))}
              </select>
            </div>

            <button
              className="btn btn-primary btn-lg"
              onClick={handleSubmit}
              disabled={!canSubmit()}
            >
              <Search size={18} />
              Verify Claim
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
