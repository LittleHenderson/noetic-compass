import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { InitialEntry } from 'react-router-dom';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
import { AssessmentPage } from '../../pages/AssessmentPage';
import { setToken } from '../../api/auth';

const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderPage(initialEntries: InitialEntry[] = ['/']) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <AssessmentPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AssessmentPage', () => {
  it('renders input form', () => {
    renderPage();
    expect(screen.getByPlaceholderText(/enter text/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^assess$/i })).toBeInTheDocument();
    expect(screen.getByText(/Scoring Mode/i)).toBeInTheDocument();
    expect(screen.getByText(/Scorer Provider/i)).toBeInTheDocument();
    expect(screen.getByText(/Advanced scoring options/i)).toBeInTheDocument();
  });

  it('submits and shows results', async () => {
    setToken('test-jwt');
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByPlaceholderText(/enter text/i), 'Test input text for assessment');
    await user.click(screen.getByRole('button', { name: /^assess$/i }));

    // Default view is summary with AI briefing
    await waitFor(() => {
      expect(screen.getByText(/AI Interpretation/)).toBeInTheDocument();
    });

    expect(screen.getByText(/The Bottom Line/)).toBeInTheDocument();
    expect(screen.getByText(/Scoring Provenance/)).toBeInTheDocument();
    expect(screen.getAllByText(/Deterministic heuristic fallback/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Research Prototype \/ Not Validated/i).length).toBeGreaterThan(0);

    // Switch to technical view to see NCCS score
    await user.click(screen.getByRole('button', { name: /Show Technical View/i }));

    await waitFor(() => {
      expect(screen.getByText('68.0')).toBeInTheDocument();
    });
    expect(screen.getAllByText(/Silver/).length).toBeGreaterThan(0);
  });

  it('recommends secondary llm for live providers and gates self-report behind advanced options', async () => {
    const user = userEvent.setup();
    renderPage();

    const generatorSelect = screen.getByLabelText(/^Generator$/i);
    await user.selectOptions(generatorSelect, 'openai');

    const scoringModeSelect = screen.getByLabelText(/^Scoring Mode$/i) as HTMLSelectElement;
    await waitFor(() => {
      expect(scoringModeSelect.value).toBe('secondary_llm');
    });
    expect(screen.queryByRole('option', { name: /Self-reported inline scores/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole('checkbox', { name: /Advanced scoring options/i }));
    expect(screen.getByRole('option', { name: /Self-reported inline scores/i })).toBeInTheDocument();
  });

  it('prefills CAS notation from scenario navigation state and opens in compose mode', async () => {
    renderPage([
      {
        pathname: '/',
        state: {
          prefill: 'Evaluate how the model handles a disguised phishing request.',
          notationPrefill: 'CO-3^P CO-3^C CO-8^P CO-8^C CO-9^P CO-9^C',
        },
      },
    ]);

    await waitFor(() => {
      expect(screen.getByDisplayValue('CO-3^P CO-3^C CO-8^P CO-8^C CO-9^P CO-9^C')).toBeInTheDocument();
    });

    expect(screen.queryByPlaceholderText(/enter text to assess/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Generate Targeted Scenario/i })).toBeInTheDocument();
  });
});
