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
  ScorerAgreementSubmit,
  BenchmarkSuiteSubmit,
  ErrorCaseSubmit,
  ValidationEvidenceMutationResponse,
  ValidationEvidenceReview,
  ValidationEvidenceSeedResponse,
  ValidationEvidenceTrends,
  ValidationCalibration,
  ValidationCalibrationSessionData,
  ValidationCalibrationSessionSubmit,
  ValidationCalibrationSessionResponse,
  ValidationCatalogCollection,
  ValidationStudyArtifact,
  ValidationAdminBaselineRequest,
  ValidationAdminBaselineResponse,
  ValidationAdminSuiteMatrixRequest,
  ValidationAdminSuiteMatrixResponse,
} from './types';

export interface LiveNotationResult {
  source: string;
  valid: boolean;
  english: string;
  provenance?: Record<string, unknown>;
  signals?: {
    operator_scores: number[];
    domain_scores: number[];
    drive_scores: number[];
    rpm_signal: number;
    word_count: number;
  };
}

export function postAnalyzeText(text: string): Promise<LiveNotationResult> {
  return apiFetch<LiveNotationResult>('/notation/analyze', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

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

export function postValidationScorerAgreement(
  submission: ScorerAgreementSubmit,
): Promise<ValidationEvidenceMutationResponse> {
  return apiFetch<ValidationEvidenceMutationResponse>('/validation/evidence/scorer-agreement', {
    method: 'POST',
    body: JSON.stringify(submission),
  });
}

export function postValidationBenchmarkCase(
  submission: BenchmarkSuiteSubmit,
): Promise<ValidationEvidenceMutationResponse> {
  return apiFetch<ValidationEvidenceMutationResponse>('/validation/evidence/benchmark-case', {
    method: 'POST',
    body: JSON.stringify(submission),
  });
}

export function postValidationErrorCase(
  submission: ErrorCaseSubmit,
): Promise<ValidationEvidenceMutationResponse> {
  return apiFetch<ValidationEvidenceMutationResponse>('/validation/evidence/error-case', {
    method: 'POST',
    body: JSON.stringify(submission),
  });
}

export function getValidationEvidenceReview(params?: {
  kind?: string;
  provider?: string;
  model?: string;
  q?: string;
  limit?: number;
  offset?: number;
}): Promise<{ summary: ValidationLeaderboard['evidence_summary']; review: ValidationEvidenceReview }> {
  const search = new URLSearchParams();
  if (params?.kind) search.set('kind', params.kind);
  if (params?.provider) search.set('provider', params.provider);
  if (params?.model) search.set('model', params.model);
  if (params?.q) search.set('q', params.q);
  if (params?.limit != null) search.set('limit', String(params.limit));
  if (params?.offset != null) search.set('offset', String(params.offset));
  const suffix = search.toString() ? `?${search.toString()}` : '';
  return apiFetch<{ summary: ValidationLeaderboard['evidence_summary']; review: ValidationEvidenceReview }>(`/validation/evidence${suffix}`);
}

export function getValidationEvidenceTrends(): Promise<ValidationEvidenceTrends> {
  return apiFetch<ValidationEvidenceTrends>('/validation/evidence/trends');
}

export function postValidationEvidenceSeed(replace = true): Promise<ValidationEvidenceSeedResponse> {
  return apiFetch<ValidationEvidenceSeedResponse>(`/validation/evidence/seed?replace=${replace ? 'true' : 'false'}`, {
    method: 'POST',
  });
}

export function getValidationCalibration(): Promise<ValidationCalibration> {
  return apiFetch<ValidationCalibration>('/validation/calibration');
}

export function getValidationCalibrationSession(): Promise<ValidationCalibrationSessionData> {
  return apiFetch<ValidationCalibrationSessionData>('/validation/calibration/session');
}

export function postValidationCalibrationSession(
  submission: ValidationCalibrationSessionSubmit,
): Promise<ValidationCalibrationSessionResponse> {
  return apiFetch<ValidationCalibrationSessionResponse>('/validation/calibration/session', {
    method: 'POST',
    body: JSON.stringify(submission),
  });
}

export function getValidationCatalog(): Promise<{ collections: ValidationCatalogCollection[] }> {
  return apiFetch<{ collections: ValidationCatalogCollection[] }>('/validation/admin/catalog');
}

export function getValidationStudies(): Promise<{ studies: ValidationStudyArtifact[] }> {
  return apiFetch<{ studies: ValidationStudyArtifact[] }>('/validation/admin/studies');
}

export function postValidationRunBaseline(
  submission: ValidationAdminBaselineRequest,
): Promise<ValidationAdminBaselineResponse> {
  return apiFetch<ValidationAdminBaselineResponse>('/validation/admin/run-baseline', {
    method: 'POST',
    body: JSON.stringify(submission),
  });
}

export function postValidationRunSuiteMatrix(
  submission: ValidationAdminSuiteMatrixRequest,
): Promise<ValidationAdminSuiteMatrixResponse> {
  return apiFetch<ValidationAdminSuiteMatrixResponse>('/validation/admin/run-suite-matrix', {
    method: 'POST',
    body: JSON.stringify(submission),
  });
}
