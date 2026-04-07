/** TypeScript types mirroring api/models.py */

export interface DialConfig {
  values: number[]; // 10 ints, each [3,9]
}

export interface AssessRequest {
  operator_scores: number[]; // 10
  domain_averages: number[]; // 4
  drive_scores: number[];    // 7
  rpm_completeness: number;
  pathway_rpm_completeness?: number;
  bias_flag_count?: number;
  inversion_axis_scores?: number[]; // 7
  stealth_resistance?: number;
  compound_severity?: number;
  manipulation_resistance?: number;
  overton_drift_resistance?: number;
}

export interface WrapRequest {
  text: string;
  provider?: string;
  dial_config?: DialConfig;
  model?: string | null;
  mock?: boolean;
}

export interface BatchRequest {
  texts: string[];
  provider?: string;
  dial_config?: DialConfig;
  model?: string | null;
  mock?: boolean;
  max_concurrency?: number;
}

export interface NccsResult {
  operator_profile: number;
  domain_coherence: number;
  drive_rpm_integrity: number;
  pathway_quality: number;
  inversion_resistance: number;
  social_engineering: number | null;
  composite: number;
  certification: string;
  not_measured?: string[];
}

export interface StageResult {
  stage: string;
  success: boolean;
  data: Record<string, unknown>;
  error?: string | null;
}

export interface LLMResponse {
  text: string;
  model: string;
  usage: Record<string, unknown>;
  latency_ms: number;
}

export interface WrapResult {
  nccs: NccsResult;
  stages: StageResult[];
  llm_response: LLMResponse | null;
  provenance?: Record<string, unknown>;
}

export interface BatchResult {
  results: WrapResult[];
  total: number;
  succeeded: number;
  failed: number;
}

export interface HealthStatus {
  status: string;
  version: string;
  engine: string;
}

export interface ErrorResponse {
  detail: string;
  error_type: string;
}

/** Local-only type for assessment history */
export interface AssessmentRecord {
  id: string;
  timestamp: number;
  text: string;
  result: WrapResult;
}
