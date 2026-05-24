import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import CasBaselineEvidencePanel from './CasBaselineEvidencePanel';

describe('CasBaselineEvidencePanel', () => {
  it('shows explicit CAS results, baselines, and scope', () => {
    render(<CasBaselineEvidencePanel />);

    expect(screen.getByRole('heading', { name: /CAS vs baseline/i })).toBeInTheDocument();
    expect(screen.getAllByText(/78\.6%/).length).toBeGreaterThan(0);
    expect(screen.getByText(/\+28\.9 percentage points/)).toBeInTheDocument();
    expect(screen.getAllByText(/Scope:/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Pythia/i).length).toBeGreaterThan(0);
  });
});
