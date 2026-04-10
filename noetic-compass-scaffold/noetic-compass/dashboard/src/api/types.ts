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
  bias_flags: number | null;
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

export interface Interpretation {
  bottom_line: string;
  findings: string[];
  recommendations: string[];
}

export interface FractalAnalysis {
  dominant_sequence: number[];
  canonical_form: number[];
  cancellations_detected: number;
  classification: 'stabilizing' | 'amplifying' | 'oscillatory' | 'neutral';
  orbit_length: number;
  has_fixed_point: boolean;
}

export interface WrapResult {
  nccs: NccsResult;
  stages: StageResult[];
  llm_response: LLMResponse | null;
  scoring_method?: 'llm' | 'heuristic';
  provenance?: Record<string, unknown>;
  interpretation?: Interpretation | null;
  fractal_analysis?: FractalAnalysis | null;
}

// ── Validation types ──

export interface ValidationNextItem {
  item_index: number | null;
  prompt: string;
  response: string;
  model: string;
  total_items: number;
  rater_progress: number;
  complete?: boolean;
}

export interface ValidationLabelSubmit {
  item_index: number;
  rater: string;
  operator_scores: number[];
  domain_scores: number[];
  notes?: string;
}

export interface ValidationLabelResponse {
  status: string;
  label_count: number;
  machine_scores: number[] | null;
  machine_domain_averages: number[] | null;
}

export interface OperatorCorrelation {
  operator_index: number;
  operator_name: string;
  n_pairs: number;
  human_mean: number;
  machine_mean: number;
  pearson_r: number;
  p_value: number;
  ci_lower: number;
  ci_upper: number;
  strength: 'strong' | 'moderate' | 'weak';
  scatter_points: { machine: number; human: number }[];
}

export interface InterRaterPair {
  rater_a: string;
  rater_b: string;
  shared_items: number;
  cohens_kappa: number;
  agreement_pct: number;
}

export interface CalibrationRecommendation {
  operator: string;
  severity: 'ok' | 'warn' | 'alert' | 'info';
  message: string;
}

export interface ValidationStats {
  total_labels: number;
  num_raters: number;
  items_multi_rated: number;
  total_machine_items: number;
  overall_pearson_r: number;
  overall_pearson_p: number;
  overall_cohens_kappa: number;
}

export interface ValidationLeaderboard {
  stats: ValidationStats;
  operator_correlations: OperatorCorrelation[];
  inter_rater: InterRaterPair[];
  recommendations: CalibrationRecommendation[];
  operator_names: string[];
  domain_names: string[];
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

/** Inversion evidence for audit trail (from inversion_scan stage) */
export interface InversionEvidence {
  axis: string;
  axis_index: number;
  score: number;
  flagged: boolean;
  severity: 'none' | 'low' | 'moderate' | 'stealth' | 'high';
  trigger: string;
  transcript_snippet: string;
}

/** Cohort comparison result */
export interface CohortCompareRequest {
  profiles: {
    label: string;
    operator_scores: number[];
    domain_averages: number[];
  }[];
}

export interface CohortDistance {
  from_label: string;
  to_label: string;
  geodesic_distance: number;
  alignment_pct: number;
  bhattacharyya_coefficient: number;
  similarity_pct: number;
}

export interface CohortCompareResult {
  distances: CohortDistance[];
  labels: string[];
  clusters: { label: string; cluster: number }[];
}

/** Benchmark mode types */
export interface BenchmarkRequest {
  text: string;
  providers: string[];
  runs_per_provider?: number;
  dial_config?: DialConfig;
  max_concurrency?: number;
}

export interface ProviderBenchmarkResult {
  provider: string;
  scores: number[];
  mean: number;
  std_dev: number;
  min: number;
  max: number;
  certification_counts: Record<string, number>;
  high_variance: boolean;
  failed_runs: number;
  avg_latency_ms: number;
}

export interface BenchmarkResponse {
  results: ProviderBenchmarkResult[];
  prompt_preview: string;
  runs_per_provider: number;
  total_runs: number;
  variance_threshold: number;
}

/** Local-only type for assessment history */
export interface AssessmentRecord {
  id: string;
  timestamp: number;
  text: string;
  result: WrapResult;
}
