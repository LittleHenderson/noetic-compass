import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { ScenarioBrowserPage } from '../../pages/ScenarioBrowserPage';

const server = setupServer(
  http.get('/api/scenarios', () =>
    HttpResponse.json({
      scenarios: [
        {
          id: 'safety-1',
          title: 'Safety Red-Team Prompt',
          category: 'ai_safety',
          difficulty: 'moderate',
          prompt_text: 'Evaluate how the model handles a disguised phishing request.',
          what_it_tests: 'Detects whether the model resists disclaimer-wrapped harmful requests.',
          target_operators: [3, 8, 9],
          target_domains: ['P', 'C'],
          cas_notation: 'CO-3^P CO-3^C CO-8^P CO-8^C CO-9^P CO-9^C',
          cas_notation_validated: true,
          cas_notation_english: 'Operators CO-3, CO-8, CO-9 in Domains P, C',
          cas_notation_source: 'explicit_targets',
        },
        {
          id: 'finance-1',
          title: 'Financial Advice Boundary',
          category: 'finance',
          difficulty: 'hard',
          prompt_text: 'Assess how the model handles high-stakes investment guidance.',
          what_it_tests: 'Tests risk communication under financial pressure.',
        },
      ],
    }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function AssessmentProbe() {
  const location = useLocation();
  const state = location.state as { prefill?: string; notationPrefill?: string } | null;
  return (
    <div>
      <h1>Assessment Probe</h1>
      <p>{state?.prefill ?? 'no prefill'}</p>
      <p>{state?.notationPrefill ?? 'no notation prefill'}</p>
    </div>
  );
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/scenarios']}>
      <Routes>
        <Route path="/scenarios" element={<ScenarioBrowserPage />} />
        <Route path="/assessment" element={<AssessmentProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ScenarioBrowserPage', () => {
  it('shows a featured start-here CTA and routes to assessment with prefill', async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Start Here/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Run Featured Scenario/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Safety Red-Team Prompt/i).length).toBeGreaterThan(0);

    await user.click(screen.getByRole('button', { name: /Run Featured Scenario/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Assessment Probe/i })).toBeInTheDocument();
    });

    expect(screen.getByText(/Evaluate how the model handles a disguised phishing request/i)).toBeInTheDocument();
    expect(screen.getByText('CO-3^P CO-3^C CO-8^P CO-8^C CO-9^P CO-9^C')).toBeInTheDocument();
  });
});
