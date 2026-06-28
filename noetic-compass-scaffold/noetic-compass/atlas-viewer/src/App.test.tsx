import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('./pages/CockpitPage', () => ({
  default: () => <main data-testid="cockpit-page">Guided cockpit</main>,
}));

import App from './App';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe('App product routes', () => {
  it('renders the guided product surface at /audit-console', async () => {
    renderAt('/audit-console');

    expect(await screen.findByTestId('cockpit-page')).toBeInTheDocument();
    expect(screen.getByTestId('guide-chat-launcher')).toBeInTheDocument();
  });

  it('keeps /cockpit as the same guided product surface', async () => {
    renderAt('/cockpit');

    expect(await screen.findByTestId('cockpit-page')).toBeInTheDocument();
    expect(screen.getByTestId('guide-chat-launcher')).toBeInTheDocument();
  });

  it('redirects the old standalone /explainer route into the guided product surface', async () => {
    renderAt('/explainer');

    expect(await screen.findByTestId('cockpit-page')).toBeInTheDocument();
    expect(screen.getByTestId('guide-chat-launcher')).toBeInTheDocument();
  });
});
