/** TypeScript types mirroring api/models.py */

export type ScoringMode = 'secondary_llm' | 'self_reported' | 'heuristic_fallback';

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
  scoring_mode?: ScoringMode;
  scoring_provider?: string | null;
  scoring_model?: string | null;
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

export interface WrapProvenance {
  pipeline_version?: string;
  engine?: string;
  input_hash?: string;
  connector?: string;
  requested_scoring_mode?: ScoringMode;
  scoring_method?: ScoringMode;
  scorer_provider?: string | null;
  scorer_model?: string | null;
  elapsed_ms?: number;
  rpm_heuristic?: string;
  [key: string]: unknown;
}

export interface CompiledNotation {
  source: string;
  valid: boolean;
  english: string;
  provenance?: Record<string, unknown>;
}

/**
 * CAS v7.5 Phenomenological Register axis (Clarification 8).
 * Register specifies the operational character of a cognitive operation
 * without changing what the operation IS.
 *   T = Transcendent | A = Analytical | f = Affective (lowercase authoritative) | E = Embodied
 * Registers appear in assessments only when the scoring pathway emits them
 * (currently: self-reported scoring with register-annotated scores).
 * Null entries indicate register-neutral scores.
 */
export type PhenomenologicalRegister = 'T' | 'A' | 'f' | 'E';

export interface WrapResult {
  nccs: NccsResult;
  stages: StageResult[];
  llm_response: LLMResponse | null;
  scoring_method?: ScoringMode;
  provenance?: WrapProvenance;
  interpretation?: Interpretation | null;
  fractal_analysis?: FractalAnalysis | null;
  compiled_notation?: CompiledNotation | null;
  lacunarity?: {
    state: number;
    fractal: number;
    domain: number;
    drive: number;
    rpm_resolution: number;
    composite: number;
    classification: string;
    gap_map: {
      absent_operators: number[];
      absent_domains: string[];
      absent_drives: number[];
      strongest_cluster: number[];
      largest_void: string;
    };
  } | null;
  /**
   * CAS v7.5 Register data flow (Clarification 8). Parallel to the 10
   * operator scores; each entry is a `PhenomenologicalRegister` character
   * or `null` when the score is register-neutral. Null/absent at the top
   * level when the assessment is fully register-neutral (v7.4-compatible).
   */
  score_registers?: (PhenomenologicalRegister | null)[] | null;
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

export interface ScorerAgreementSubmit {
  generator_provider: string;
  generator_model?: string | null;
  scorer_provider: string;
  scorer_model?: string | null;
  prompt_excerpt: string;
  machine_score: number;
  scorer_score: number;
  notes?: string;
  item_index?: number | null;
}

export interface BenchmarkSuiteSubmit {
  suite_name: string;
  provider: string;
  model?: string | null;
  scoring_mode?: ScoringMode;
  scoring_provider?: string | null;
  scoring_model?: string | null;
  cases_run: number;
  mean_score: number;
  variance: number;
  notes?: string;
}

export interface ErrorCaseSubmit {
  kind: 'false_positive' | 'false_negative';
  provider?: string | null;
  model?: string | null;
  prompt_excerpt: string;
  expected_tier: string;
  observed_tier: string;
  notes?: string;
  item_index?: number | null;
}

export interface ValidationEvidenceMutationResponse {
  status: string;
  count: number;
  summary: Record<string, unknown>;
}

export interface ValidationEvidenceFacetOption {
  value: string;
  label: string;
}

export interface ValidationEvidenceEntry {
  kind: 'scorer_agreement' | 'benchmark_suites' | 'error_cases';
  kind_label: string;
  case_kind?: string;
  provider?: string | null;
  model?: string | null;
  scoring_mode?: ScoringMode | null;
  scoring_provider?: string | null;
  scoring_model?: string | null;
  summary: string;
  timestamp: string;
  notes?: string;
  prompt_excerpt?: string;
  suite_name?: string;
  status?: string;
  successes?: number;
  failures?: number;
  expected_tier?: string;
  observed_tier?: string;
  machine_score?: number;
  scorer_score?: number;
  mean_score?: number | null;
  item_index?: number | null;
}

export interface ValidationEvidenceReview {
  total: number;
  returned: number;
  filters: {
    kind?: string | null;
    provider?: string | null;
    model?: string | null;
    q?: string | null;
    limit: number;
    offset: number;
  };
  facets: {
    kinds: ValidationEvidenceFacetOption[];
    providers: string[];
    models: string[];
  };
  entries: ValidationEvidenceEntry[];
}

export interface ValidationEvidenceSummaryGroup {
  count: number;
  recent: Record<string, unknown>[];
  mean_absolute_gap?: number;
  cases_run?: number;
  failed_runs?: number;
  false_positives?: number;
  false_negatives?: number;
}

export interface ValidationEvidenceSeedResponse {
  status: string;
  summary: {
    scorer_agreement: ValidationEvidenceSummaryGroup;
    benchmark_suites: ValidationEvidenceSummaryGroup;
    error_cases: ValidationEvidenceSummaryGroup;
  };
  counts: {
    scorer_agreement: number;
    benchmark_suites: number;
    error_cases: number;
  };
}

export interface ValidationEvidenceTrendRow {
  provider?: string;
  model?: string;
  total_entries: number;
  scorer_agreement: number;
  benchmark_suites: number;
  error_cases: number;
  mean_absolute_gap: number;
  benchmark_cases: number;
  failed_runs: number;
  false_positives: number;
  false_negatives: number;
  latest_timestamp: string;
}

export interface ValidationEvidenceTimelinePoint {
  date: string;
  total: number;
  scorer_agreement: number;
  benchmark_suites: number;
  error_cases: number;
}

export interface ValidationEvidenceTierDrift {
  expected_tier: string;
  observed_tier: string;
  count: number;
}

export interface ValidationEvidenceTrends {
  timeline: ValidationEvidenceTimelinePoint[];
  by_provider: ValidationEvidenceTrendRow[];
  by_model: ValidationEvidenceTrendRow[];
  tier_drift: ValidationEvidenceTierDrift[];
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
  calibration?: ValidationCalibration;
  recommendations: CalibrationRecommendation[];
  operator_names: string[];
  domain_names: string[];
  evidence_summary?: {
    scorer_agreement: ValidationEvidenceSummaryGroup;
    benchmark_suites: ValidationEvidenceSummaryGroup;
    error_cases: ValidationEvidenceSummaryGroup;
  };
}

export interface ValidationCalibrationRaterRow {
  rater: string;
  label_count: number;
  item_count: number;
  mean_panel_gap: number;
  mean_abs_panel_gap: number;
  mean_abs_machine_gap: number;
  top_operator_drift?: {
    operator_index: number;
    operator_name: string;
    signed_gap: number;
  } | null;
}

export interface ValidationCalibrationOperatorRow {
  operator_index: number;
  operator_name: string;
  shared_items: number;
  mean_spread: number;
  max_spread: number;
}

export interface ValidationCalibrationItemRow {
  item_index: number;
  prompt_excerpt: string;
  raters: string[];
  label_count: number;
  largest_operator_gap: {
    operator_index: number;
    operator_name: string;
    spread: number;
    panel_mean: number;
  };
  mean_spread: number;
  machine_mean: number | null;
  panel_mean: number;
}

export interface ValidationCalibration {
  raters: ValidationCalibrationRaterRow[];
  operators: ValidationCalibrationOperatorRow[];
  items: ValidationCalibrationItemRow[];
}

export type ValidationCalibrationDisposition =
  | 'resolved_panel'
  | 'resolved_machine'
  | 'rubric_clarification'
  | 'false_positive'
  | 'false_negative'
  | 'needs_more_review';

export interface ValidationCalibrationQueueLabel {
  rater: string;
  timestamp: string;
  notes: string;
  operator_scores: number[];
  domain_scores: number[];
}

export interface ValidationCalibrationSessionEntry {
  item_index: number;
  reconciler: string;
  disposition: ValidationCalibrationDisposition;
  notes: string;
  timestamp: string;
  resolved_operator_scores?: number[] | null;
  resolved_domain_scores?: number[] | null;
}

export interface ValidationCalibrationQueueItem {
  item_index: number;
  prompt: string;
  prompt_excerpt: string;
  response: string;
  model: string;
  raters: string[];
  labels: ValidationCalibrationQueueLabel[];
  panel_operator_scores: number[];
  panel_domain_scores: number[];
  machine_operator_scores: number[];
  machine_domain_scores: number[];
  largest_operator_gap?: {
    operator_index: number;
    operator_name: string;
    spread: number;
    panel_mean: number;
  } | null;
  mean_spread: number;
  machine_panel_gap: number;
  session_count: number;
  last_session?: ValidationCalibrationSessionEntry | null;
}

export interface ValidationCalibrationSessionData {
  queue: ValidationCalibrationQueueItem[];
  recent_sessions: ValidationCalibrationSessionEntry[];
}

export interface ValidationCalibrationSessionSubmit {
  item_index: number;
  reconciler: string;
  disposition: ValidationCalibrationDisposition;
  notes?: string;
  resolved_operator_scores?: number[] | null;
  resolved_domain_scores?: number[] | null;
}

export interface ValidationCalibrationSessionResponse {
  status: string;
  count: number;
  entry: ValidationCalibrationSessionEntry;
}

export interface ValidationCatalogCollection {
  id: string;
  label: string;
  path: string;
  kind: string;
}

export interface ValidationStudyArtifact {
  filename: string;
  path: string;
  provider?: string | null;
  model?: string | null;
  scoring_mode?: ScoringMode | null;
  scoring_provider?: string | null;
  scoring_model?: string | null;
  study_label?: string | null;
  prompt_source?: string | null;
  prompt_count?: number | null;
  successes?: number | null;
  failures?: number | null;
  status?: string | null;
  composite_mean?: number | null;
  composite_std?: number | null;
  study_date?: string | null;
}

export interface ValidationAdminBaselineRequest {
  provider: string;
  prompt_collection: string;
  count: number;
  label?: string | null;
  model?: string | null;
  scoring_mode?: ScoringMode;
  scoring_provider?: string | null;
  scoring_model?: string | null;
  reseed?: boolean;
}

export interface ValidationAdminBaselineResponse {
  status: string;
  summary: Record<string, unknown>;
  archive_path: string;
  output_path?: string | null;
  evidence_summary?: ValidationLeaderboard['evidence_summary'];
}

export interface ValidationAdminSuiteMatrixRequest {
  provider: string;
  suite_ids?: string[];
  count_per_suite: number;
  model?: string | null;
  scoring_mode?: ScoringMode;
  scoring_provider?: string | null;
  scoring_model?: string | null;
  reseed?: boolean;
}

export interface ValidationAdminSuiteMatrixRun {
  suite_id: string;
  label?: string;
  status: string;
  provider?: string;
  model?: string | null;
  successes?: number;
  failures?: number;
  prompt_count?: number;
  composite_mean?: number;
  archive_path?: string;
  error?: string;
}

export interface ValidationAdminSuiteMatrixResponse {
  status: string;
  provider: string;
  suite_count: number;
  success_count: number;
  partial_count: number;
  failed_count: number;
  runs: ValidationAdminSuiteMatrixRun[];
  evidence_summary?: ValidationLeaderboard['evidence_summary'];
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
