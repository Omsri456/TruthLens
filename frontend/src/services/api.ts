/**
 * TruthLens AI — API Service Layer.
 * All backend communication goes through this module.
 */

import axios, { type AxiosInstance, type AxiosError } from 'axios';
import type {
  VerificationReport,
  HistoryEntry,
  HealthResponse,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 minutes — verification can take time
});

/** Normalize error messages from backend responses */
function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axErr = error as AxiosError<{ detail?: string }>;
    if (axErr.response?.data?.detail) {
      return axErr.response.data.detail;
    }
    if (axErr.response?.status === 503) {
      return 'The verification service is temporarily unavailable. Please check that API keys are configured.';
    }
    if (axErr.code === 'ECONNABORTED') {
      return 'The request timed out. Please try again with shorter content.';
    }
    if (!axErr.response) {
      return 'Could not connect to the TruthLens backend. Make sure the server is running.';
    }
    return `Server error (${axErr.response.status}). Please try again.`;
  }
  return 'An unexpected error occurred.';
}

// ── Verification Endpoints ───────────────────────────────────────

export async function verifyText(
  text: string,
  language: string = 'en'
): Promise<VerificationReport> {
  try {
    const { data } = await api.post<VerificationReport>('/verify/text', {
      text,
      language,
    });
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function verifyImage(
  file: File,
  language: string = 'en'
): Promise<VerificationReport> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language', language);
    const { data } = await api.post<VerificationReport>(
      '/verify/image',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function verifyPdf(
  file: File,
  language: string = 'en'
): Promise<VerificationReport> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language', language);
    const { data } = await api.post<VerificationReport>(
      '/verify/pdf',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function verifyAudio(
  file: File,
  language: string = 'en'
): Promise<VerificationReport> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language', language);
    const { data } = await api.post<VerificationReport>(
      '/verify/audio',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function verifyUrl(
  url: string,
  language: string = 'en'
): Promise<VerificationReport> {
  try {
    const { data } = await api.post<VerificationReport>('/verify/url', {
      url,
      language,
    });
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

// ── History & Report ─────────────────────────────────────────────

export async function getVerification(
  id: string
): Promise<VerificationReport> {
  try {
    const { data } = await api.get<VerificationReport>(`/verification/${id}`);
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function getHistory(): Promise<HistoryEntry[]> {
  try {
    const { data } = await api.get<HistoryEntry[]>('/history');
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

// ── Health Check ─────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse> {
  try {
    const { data } = await api.get<HealthResponse>('/health');
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}
