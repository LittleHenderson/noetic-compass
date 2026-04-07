import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
import { AssessmentPage } from '../../pages/AssessmentPage';
import { setToken } from '../../api/auth';

const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AssessmentPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AssessmentPage', () => {
  it('renders input form', () => {
    renderPage();
    expect(screen.getByPlaceholderText(/enter text/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /assess/i })).toBeInTheDocument();
  });

  it('submits and shows results', async () => {
    setToken('test-jwt');
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByPlaceholderText(/enter text/i), 'Test input text for assessment');
    await user.click(screen.getByRole('button', { name: /assess/i }));

    await waitFor(() => {
      expect(screen.getByText('76.0')).toBeInTheDocument();
    });

    expect(screen.getByText(/Gold/)).toBeInTheDocument();
  });
});
