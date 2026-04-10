import { apiFetch } from './client';
import type {
  WrapRequest,
  WrapResult,
  AssessRequest,
  NccsResult,
  BatchRequest,
  BatchResult,
  BenchmarkRequest,
  BenchmarkResponse,
  CohortCompareRequest,
  CohortCompareResult,
  DialConfig,
  HealthStatus,
  ValidationNextItem,
  ValidationLabelSubmit,
  ValidationLabelResponse,
  ValidationStats,
  ValidationLeaderboard,
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

export function postCohortCompare(req: CohortCompareRequest): Promise<CohortCompareResult> {
  return apiFetch<CohortCompareResult>('/batch/compare', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export function postBenchmark(req: BenchmarkRequest): Promise<BenchmarkResponse> {
  return apiFetch<BenchmarkResponse>('/benchmark', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export function getHealth(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>('/health');
}

// ── Validation endpoints ──

export function getValidationNext(rater: string): Promise<ValidationNextItem> {
  return apiFetch<ValidationNextItem>(`/validation/next?rater=${encodeURIComponent(rater)}`);
}

export function postValidationLabel(submission: ValidationLabelSubmit): Promise<ValidationLabelResponse> {
  return apiFetch<ValidationLabelResponse>('/validation/label', {
    method: 'POST',
    body: JSON.stringify(submission),
  });
}

export function getValidationStats(): Promise<ValidationStats> {
  return apiFetch<ValidationStats>('/validation/stats');
}

export function getValidationLeaderboard(): Promise<ValidationLeaderboard> {
  return apiFetch<ValidationLeaderboard>('/validation/leaderboard');
}
