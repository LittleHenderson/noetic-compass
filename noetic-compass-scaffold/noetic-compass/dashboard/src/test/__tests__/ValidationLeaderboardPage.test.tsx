import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { ValidationLeaderboardPage } from '../../pages/ValidationLeaderboardPage';

const server = setupServer(
  http.get('/api/validation/leaderboard', () =>
    HttpResponse.json({
      stats: {
        total_labels: 12,
        num_raters: 2,
        items_multi_rated: 6,
        total_machine_items: 6,
        overall_pearson_r: 0.61,
        overall_pearson_p: 0.01,
        overall_cohens_kappa: 0.56,
      },
      operator_correlations: [
        {
          operator_index: 0,
          operator_name: 'CO-0 (Generative Potential)',
          n_pairs: 12,
          human_mean: 6.2,
          machine_mean: 6.0,
          pearson_r: 0.72,
          p_value: 0.004,
          ci_lower: 0.41,
          ci_upper: 0.89,
          strength: 'strong',
          scatter_points: [
            { machine: 6, human: 6 },
            { machine: 7, human: 8 },
          ],
        },
        {
          operator_index: 1,
          operator_name: 'CO-1 (Directed Attention)',
          n_pairs: 12,
          human_mean: 5.4,
          machine_mean: 5.7,
          pearson_r: 0.48,
          p_value: 0.03,
          ci_lower: 0.11,
          ci_upper: 0.76,
          strength: 'moderate',
          scatter_points: [
            { machine: 5, human: 5 },
            { machine: 6, human: 4 },
          ],
        },
      ],
      inter_rater: [
        {
          rater_a: 'RaterA',
          rater_b: 'RaterB',
          shared_items: 6,
          cohens_kappa: 0.56,
          agreement_pct: 0.75,
        },
      ],
      recommendations: [
        {
          operator: 'CO-3',
          severity: 'warn',
          message: 'Clarify how partial refusals should affect critical evaluation scoring.',
        },
      ],
      operator_names: ['CO-0', 'CO-1'],
      domain_names: ['P', 'C', 'E', 'O'],
      evidence_summary: {
        scorer_agreement: {
          count: 5,
          recent: [],
          mean_absolute_gap: 0.8,
        },
        benchmark_suites: {
          count: 4,
          recent: [],
          cases_run: 40,
          failed_runs: 0,
        },
        error_cases: {
          count: 2,
          recent: [],
          false_positives: 1,
          false_negatives: 1,
        },
      },
    }),
  ),
  http.get('/api/validation/evidence', () =>
    HttpResponse.json({
      summary: {
        scorer_agreement: {
          count: 5,
          recent: [],
          mean_absolute_gap: 0.8,
        },
        benchmark_suites: {
          count: 4,
          recent: [],
          cases_run: 40,
          failed_runs: 0,
        },
        error_cases: {
          count: 2,
          recent: [],
          false_positives: 1,
          false_negatives: 1,
        },
      },
      review: {
        total: 1,
        returned: 1,
        filters: {
          kind: null,
          provider: null,
          model: null,
          q: null,
          limit: 50,
          offset: 0,
        },
        facets: {
          kinds: [],
          providers: ['xai'],
          models: ['grok-test'],
        },
        entries: [
          {
            kind: 'benchmark_suites',
            kind_label: 'Benchmark suites',
            provider: 'xai',
            model: 'grok-test',
            scoring_mode: 'heuristic_fallback',
            summary: 'sample_prompts on xai, 10 cases, mean 68.2.',
            timestamp: '2026-04-12T10:00:00Z',
          },
        ],
      },
    }),
  ),
  http.get('/api/validation/evidence/trends', () =>
    HttpResponse.json({
      timeline: [
        {
          date: '2026-04-12',
          total: 7,
          scorer_agreement: 5,
          benchmark_suites: 1,
          error_cases: 1,
        },
      ],
      by_provider: [
        {
          provider: 'xai',
          total_entries: 4,
          scorer_agreement: 2,
          benchmark_suites: 1,
          error_cases: 1,
          mean_absolute_gap: 0.6,
          benchmark_cases: 10,
          failed_runs: 0,
          false_positives: 1,
          false_negatives: 0,
          latest_timestamp: '2026-04-12T10:00:00Z',
        },
      ],
      by_model: [
        {
          model: 'grok-test',
          total_entries: 4,
          scorer_agreement: 2,
          benchmark_suites: 1,
          error_cases: 1,
          mean_absolute_gap: 0.6,
          benchmark_cases: 10,
          failed_runs: 0,
          false_positives: 1,
          false_negatives: 0,
          latest_timestamp: '2026-04-12T10:00:00Z',
        },
      ],
      tier_drift: [],
    }),
  ),
  http.get('/api/validation/calibration', () =>
    HttpResponse.json({
      raters: [],
      operators: [],
      items: [],
    }),
  ),
  http.get('/api/validation/admin/catalog', () =>
    HttpResponse.json({
      collections: [
        {
          id: 'sample_prompts',
          label: 'Sample prompts',
          path: 'validation/sample_prompts.json',
          kind: 'prompt_collection',
        },
      ],
    }),
  ),
  http.get('/api/validation/admin/studies', () =>
    HttpResponse.json({
      studies: [
        {
          filename: 'heuristic-study.json',
          path: 'validation/studies/heuristic-study.json',
          provider: 'xai',
          model: 'grok-test',
          scoring_mode: 'heuristic_fallback',
          study_label: 'sample_prompts',
          prompt_count: 10,
          successes: 10,
          failures: 0,
          status: 'completed',
          composite_mean: 68.15,
          composite_std: 3.1,
          study_date: '2026-04-12T10:00:00Z',
        },
        {
          filename: 'external-study.json',
          path: 'validation/studies/external-study.json',
          provider: 'anthropic',
          model: 'claude-test',
          scoring_mode: 'secondary_llm',
          scoring_provider: 'google',
          scoring_model: 'gemini-test',
          study_label: 'sample_prompts',
          prompt_count: 10,
          successes: 10,
          failures: 0,
          status: 'completed',
          composite_mean: 71.07,
          composite_std: 2.5,
          study_date: '2026-04-12T11:00:00Z',
        },
      ],
    }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ValidationLeaderboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ValidationLeaderboardPage', () => {
  it('renders leaderboard content and benchmark tables after data loads', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Validation Leaderboard/i })).toBeInTheDocument();
    });

    expect(screen.getByText(/Neutral Benchmark Table/i)).toBeInTheDocument();
    expect(screen.getByText(/External-Scorer Benchmark Table/i)).toBeInTheDocument();
    expect(screen.getAllByText('xai').length).toBeGreaterThan(0);
    expect(screen.getAllByText('anthropic').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/google/i).length).toBeGreaterThan(0);
  });
});
