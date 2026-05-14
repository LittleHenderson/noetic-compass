import { getToken } from './auth';
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
