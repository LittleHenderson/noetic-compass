import { http, HttpResponse } from 'msw';
import type { NccsResult, WrapResult, HealthStatus, DialConfig } from '../../api/types';

const mockNccs: NccsResult = {
  operator_profile: 18.5,
  domain_coherence: 16.0,
  drive_rpm_integrity: 14.0,
  pathway_quality: 7.5,
  inversion_resistance: 12.0,
  social_engineering: 0.74,
  bias_flags: 1,
  composite: 68.0,
  certification: 'Silver',
  not_measured: [],
};

const mockWrapResult: WrapResult = {
  nccs: mockNccs,
  scoring_method: 'heuristic_fallback',
  stages: [
    { stage: 'input_analyzer', success: true, data: { token_count: 130, word_count: 100 } },
    { stage: 'rpm_gate', success: true, data: { a0_score: 0.7, rpm_completeness: 0.5, drive_scores: [[0.6, 0.5, 0.4], [0.6, 0.5, 0.4], [0.6, 0.5, 0.4], [0.6, 0.5, 0.4], [0.6, 0.5, 0.4], [0.6, 0.5, 0.4], [0.6, 0.5, 0.4]] } },
    { stage: 'dial_adjustment', success: true, data: { dial_values: [6, 6, 6, 6, 6, 6, 6, 6, 6, 6] } },
    { stage: 'base_llm_call', success: true, data: { model: 'mock-v1', latency_ms: 42.5 } },
    { stage: 'operator_scoring', success: true, data: { profile_score: 0.74, scores: [0.8, 0.7, 0.6, 0.65, 0.75, 0.7, 0.72, 0.68, 0.77, 0.73], raw_scores_0_to_10: [8, 7, 6, 6.5, 7.5, 7, 7.2, 6.8, 7.7, 7.3], involution_balances: [0.95, 0.97, 0.96], scoring_method: 'heuristic_fallback', scorer_provider: null, scorer_model: null, evidence: {} } },
    { stage: 'domain_coherence', success: true, data: { dci: 0.8, domain_averages: [0.274, 0.258, 0.242, 0.226] } },
    { stage: 'inversion_scan', success: true, data: { resistance_score: 0.8, stealth_resistance: 0.9, axis_scores: [0.85, 0.8, 0.75, 0.7, 0.65, 0.8, 0.7] } },
    { stage: 'output_gate', success: true, data: { composite: 68.0, certification: 'Silver', social_engineering: 0.74, bias_flags: 1, manipulation_resistance: 0.78, overton_drift_resistance: 0.69 } },
  ],
  llm_response: { text: 'Mock analysis', model: 'mock-v1', usage: {}, latency_ms: 42.5 },
  provenance: {
    scoring_method: 'heuristic_fallback',
    requested_scoring_mode: 'heuristic_fallback',
    scorer_provider: null,
    scorer_model: null,
  },
  interpretation: {
    bottom_line: 'This system demonstrates solid cognitive architecture fundamentals with room for targeted improvement.',
    findings: [
      'Strong self-consistency and identity preservation across responses',
      'Good balance between exploration of new ideas and focused execution',
      'Some difficulty translating abstract principles into concrete actions',
    ],
    recommendations: [
      'Prioritize exercises that bridge abstract reasoning to actionable outputs',
      'Strengthen the connection between evaluative judgment and operational follow-through',
    ],
  },
};

export const handlers = [
  http.post('/api/wrap', () => HttpResponse.json(mockWrapResult)),

  http.post('/api/assess', () => HttpResponse.json(mockNccs)),

  http.post('/api/batch', () =>
    HttpResponse.json({
      results: [mockWrapResult],
      total: 1,
      succeeded: 1,
      failed: 0,
    }),
  ),

  http.get('/api/config', () =>
    HttpResponse.json({ values: [6, 6, 6, 6, 6, 6, 6, 6, 6, 6] } satisfies DialConfig),
  ),

  http.put('/api/config', async ({ request }) => {
    const body = await request.json() as DialConfig;
    return HttpResponse.json(body);
  }),

  http.get('/api/health', () =>
    HttpResponse.json({ status: 'ok', version: '0.1.0', engine: 'cas-engine' } satisfies HealthStatus),
  ),

  http.post('/api/notation/analyze', () =>
    HttpResponse.json({
      source: 'CO-3^P CO-5^C',
      valid: true,
      english: 'CO-3 (Aversion / Critical Evaluation) and CO-5 (Receptive Integration) in the Principled and Cognitive Domains',
      provenance: { operators_found: 2, compiler_valid: true },
      signals: { operator_scores: [0, 0, 0, 6, 0, 8, 0, 0, 0, 0], domain_scores: [0.6, 0.5, 0.3, 0.2], drive_scores: [0, 0, 0, 0, 0, 0, 0], rpm_signal: 0, word_count: 15 },
    }),
  ),
];
