import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { ForexProofPage } from './ForexProofPage';

describe('ForexProofPage', () => {
  it('renders the active lead and 1/30 paper proof from real evidence', async () => {
    render(<ForexProofPage />);
    expect(await screen.findByText('index_tsmom_126_d1')).toBeTruthy();
    // paper-day counter "1 / 30" appears in both the banner and the panel aside
    const counters = await screen.findAllByText('1 / 30');
    expect(counters.length).toBeGreaterThan(0);
  });

  it('surfaces the NOT LICENSED boundary and an OPEN trading edge', async () => {
    render(<ForexProofPage />);
    // at least one NOT LICENSED chip is shown
    const notLicensed = await screen.findAllByText('NOT LICENSED');
    expect(notLicensed.length).toBeGreaterThan(0);
    // OPEN appears on the trading-edge chip and several eligibility rows
    const open = await screen.findAllByText('OPEN');
    expect(open.length).toBeGreaterThan(0);
  });

  it('disables every live and payment control', async () => {
    render(<ForexProofPage />);
    const placeLive = await screen.findByTitle('Live trading is NOT LICENSED.');
    expect((placeLive as HTMLButtonElement).disabled).toBe(true);

    const withdraw = await screen.findByTitle('Debit/card/bank transfer is NOT LICENSED.');
    expect((withdraw as HTMLButtonElement).disabled).toBe(true);
  });

  it('shows the recommended next-action command', async () => {
    render(<ForexProofPage />);
    const cmd = await screen.findByTestId('recommended-command');
    expect(cmd.textContent).toContain('run_daily_paper_bundle.py');
  });

  it('renders the evidence chain as verified', async () => {
    render(<ForexProofPage />);
    const chainRow = await screen.findByText('local hash chain');
    // the row's container holds the verified marker
    const row = chainRow.closest('[data-testid="evidence-hash-row"]');
    expect(row).toBeTruthy();
    expect(within(row as HTMLElement).getByTitle('Chain verified')).toBeTruthy();
  });
});
