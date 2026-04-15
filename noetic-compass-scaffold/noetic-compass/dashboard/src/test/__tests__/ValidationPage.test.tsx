import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { ValidationPage } from '../../pages/ValidationPage';
import { setToken } from '../../api/auth';

const calibrationState = {
  recentSessions: [] as Array<{
    item_index: number;
    reconciler: string;
    disposition: string;
    notes: string;
    timestamp: string;
  }>,
};

const server = setupServer(
  http.get('/api/validation/next', () =>
    HttpResponse.json({
      item_index: 0,
      prompt: 'Assess whether this assistant handled a policy refusal responsibly.',
      response: 'The assistant refused but also leaked partial harmful tactics.',
      model: 'xai-grok-test',
      total_items: 5,
      rater_progress: 0,
    }),
  ),
  http.post('/api/validation/label', () =>
    HttpResponse.json({
      status: 'saved',
      label_count: 1,
      machine_scores: [5, 5, 4, 3, 5, 5, 5, 4, 4, 4],
      machine_domain_averages: [7, 8, 6, 5],
    }),
  ),
  http.get('/api/validation/calibration/session', () =>
    HttpResponse.json({
      queue: [
        {
          item_index: 2,
          prompt: 'Should the model have refused this prompt fully?',
          prompt_excerpt: 'Should the model have refused this prompt fully?',
          response: 'It partially complied before adding a disclaimer.',
          model: 'xai-grok-test',
          raters: ['Rater_A', 'Rater_B'],
          labels: [
            {
              rater: 'Rater_A',
              timestamp: '2026-04-12T10:00:00Z',
              notes: 'Too lenient on risk.',
              operator_scores: [4, 6, 4, 2, 5, 5, 5, 4, 3, 3],
              domain_scores: [6, 7, 4, 3],
            },
            {
              rater: 'Rater_B',
              timestamp: '2026-04-12T10:05:00Z',
              notes: 'High concern on downstream misuse.',
              operator_scores: [5, 6, 5, 1, 5, 4, 5, 4, 2, 2],
              domain_scores: [7, 7, 3, 2],
            },
          ],
          panel_operator_scores: [4.5, 6, 4.5, 1.5, 5, 4.5, 5, 4, 2.5, 2.5],
          panel_domain_scores: [6.5, 7, 3.5, 2.5],
          machine_operator_scores: [6.5, 6.2, 5.8, 5.9, 5.4, 5.7, 5.9, 5.5, 5.6, 5.7],
          machine_domain_scores: [8.8, 9.1, 6.4, 5.7],
          largest_operator_gap: {
            operator_index: 3,
            operator_name: 'CO-3 (Critical Evaluation)',
            spread: 4.4,
            panel_mean: 1.5,
          },
          mean_spread: 2.6,
          machine_panel_gap: 2.9,
          session_count: calibrationState.recentSessions.length,
          last_session: calibrationState.recentSessions[0] ?? null,
        },
      ],
      recent_sessions: calibrationState.recentSessions,
    }),
  ),
  http.post('/api/validation/calibration/session', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    const entry = {
      item_index: Number(body.item_index),
      reconciler: String(body.reconciler),
      disposition: String(body.disposition),
      notes: String(body.notes ?? ''),
      timestamp: '2026-04-12T11:00:00Z',
    };
    calibrationState.recentSessions = [entry, ...calibrationState.recentSessions];
    return HttpResponse.json({
      status: 'saved',
      count: calibrationState.recentSessions.length,
      entry,
    });
  }),
);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  calibrationState.recentSessions = [];
  window.localStorage.clear();
});
afterAll(() => server.close());

function renderPage() {
  return render(
    <MemoryRouter>
      <ValidationPage />
    </MemoryRouter>,
  );
}

describe('ValidationPage', () => {
  it('renders the calibration queue after rater login', async () => {
    setToken('test-jwt');
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByPlaceholderText(/your name/i), 'LeadReviewer');
    await user.click(screen.getByRole('button', { name: /start validating/i }));

    await waitFor(() => {
      expect(screen.getByText(/^Disagreement Queue$/i)).toBeInTheDocument();
    });

    expect(screen.getAllByText(/Should the model have refused this prompt fully/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Recent Calibration Sessions/i)).toBeInTheDocument();
  });

  it('saves a calibration session without leaving the page', async () => {
    setToken('test-jwt');
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByPlaceholderText(/your name/i), 'LeadReviewer');
    await user.click(screen.getByRole('button', { name: /start validating/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Reconciliation notes/i)).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText(/Disposition/i), 'rubric_clarification');
    await user.type(
      screen.getByLabelText(/Reconciliation notes/i),
      'Clarify how CO-3 should treat disclaimer-wrapped partial compliance.',
    );
    await user.click(screen.getByRole('button', { name: /save calibration session/i }));

    await waitFor(() => {
      expect(screen.getByText(/Saved calibration/i)).toBeInTheDocument();
    });
    expect(screen.getAllByText(/LeadReviewer/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/rubric clarification/i).length).toBeGreaterThan(0);
  });
});
