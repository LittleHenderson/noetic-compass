import { getToken } from './auth';
import { apiFetch } from './client';
import { API_BASE } from './config';
import {
  createFetchEventSource,
  type EventSourceLike,
} from '../lib/sggs_stream';

export interface Mode7LiveUrlArgs {
  prompt: string;
  expression?: string;
  delayMs?: number;
}

export interface Mode7RuntimeStatus {
  schema_version: 'mode7_runtime_status.v1';
  active_mode: 'cas_native_live_predictor' | 'deterministic_fallback' | string;
  predictor_ready: boolean;
  predictor_enabled: boolean;
  predictor_loaded: boolean;
  load_checked: boolean;
  configured: {
    run_dir: string;
    device: string;
  };
  artifacts: {
    ready: boolean;
    files: Record<string, { path: string; exists: boolean; size_bytes: number | null }>;
  };
  torch: {
    available: boolean;
    version: string | null;
    diagnostic: string | null;
  };
  runtime_files: {
    root: string;
    ready: boolean;
    missing: string[];
  };
  diagnostics: string[];
}

export function mode7LiveUrl({
  prompt,
  expression,
  delayMs = 140,
}: Mode7LiveUrlArgs): string {
  const params = new URLSearchParams();
  params.set('prompt', prompt);
  if (expression?.trim()) {
    params.set('expression', expression.trim());
  }
  params.set('delay_ms', String(delayMs));
  return `${API_BASE}/mode7/live?${params.toString()}`;
}

export function authenticatedSggsEventSource(url: string): EventSourceLike {
  const token = getToken();
  return createFetchEventSource(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
}

export function getMode7RuntimeStatus(): Promise<Mode7RuntimeStatus> {
  return apiFetch<Mode7RuntimeStatus>('/mode7/runtime');
}
