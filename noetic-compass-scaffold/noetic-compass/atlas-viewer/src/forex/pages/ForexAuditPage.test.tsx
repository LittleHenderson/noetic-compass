import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { ForexAuditPage } from './ForexAuditPage';

describe('ForexAuditPage', () => {
  it('lists a trace per routed candidate and renders the pipeline', async () => {
    render(<ForexAuditPage />);
    expect(await screen.findByTestId('trace-card-US30')).toBeTruthy();
    expect(await screen.findByTestId('trace-card-NAS100')).toBeTruthy();
    expect(await screen.findByTestId('trace-stage-list')).toBeTruthy();
  });

  it('shows the macro gate PASS and an honest NOT_RUN on the CAS compiler stage', async () => {
    render(<ForexAuditPage />);
    const macro = await screen.findByTestId('stage-gate2_macro');
    expect(within(macro).getByText('PASS')).toBeTruthy();
    const compiler = await screen.findByTestId('stage-gate0_compiler');
    expect(within(compiler).getByText('NOT_RUN')).toBeTruthy();
  });

  it('selecting the NAS100 trace updates the pipeline header', async () => {
    render(<ForexAuditPage />);
    const nas = await screen.findByTestId('trace-card-NAS100');
    fireEvent.click(nas);
    expect(await screen.findByText('Pipeline · NAS100')).toBeTruthy();
  });

  it('shows the evidence packet SUPPRESSED with WORM unavailable', async () => {
    render(<ForexAuditPage />);
    // SUPPRESSED appears on the trace card and the evidence packet header
    const suppressed = await screen.findAllByText('SUPPRESSED');
    expect(suppressed.length).toBeGreaterThan(0);
    expect(await screen.findByText('UNAVAILABLE')).toBeTruthy();
  });
});
