import { apiFetch } from './client';
import type {
  WrapRequest,
  WrapResult,
  AssessRequest,
  NccsResult,
  BatchRequest,
  BatchResult,
  DialConfig,
  HealthStatus,
} from './types';

export function postWrap(req: WrapRequest): Promise<WrapResult> {
  return apiFetch<WrapResult>('/wrap', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export function postAssess(req: AssessRequest): Promise<NccsResult> {
  return apiFetch<NccsResult>('/assess', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export function postBatch(req: BatchRequest): Promise<BatchResult> {
  return apiFetch<BatchResult>('/batch', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export function getConfig(): Promise<DialConfig> {
  return apiFetch<DialConfig>('/config');
}

export function putConfig(config: DialConfig): Promise<DialConfig> {
  return apiFetch<DialConfig>('/config', {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

export function getHealth(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>('/health');
}
