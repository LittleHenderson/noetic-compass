import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import AuditConsolePage from './AuditConsolePage';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/audit-console']}>
      <AuditConsolePage />
    </MemoryRouter>
  );
}

describe('AuditConsolePage', () => {
  it('presents the CAS audit workflow and verdict vocabulary', () => {
    renderPage();

    expect(screen.getAllByRole('heading', { name: /connect model/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Run CAS audit').length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'NO VERDICT YET' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Provenance required before a verdict' }),
    ).toBeInTheDocument();
    expect(screen.getAllByText('Inspect in Atlas').length).toBeGreaterThan(0);

    expect(screen.getByText('ACCEPT')).toBeInTheDocument();
    expect(screen.getByText('SUPPRESS')).toBeInTheDocument();
    expect(screen.getByText('FLAG FOR HUMAN REVIEW')).toBeInTheDocument();
  });

  it('frames Atlas as deep inspection and avoids fake verdict claims', () => {
    renderPage();

    expect(
      screen.getByText(/No final audit verdict is shown until a real audit runner computes it/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Audit Console is the decision workflow/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Confidence not available')).toBeInTheDocument();
  });
});
