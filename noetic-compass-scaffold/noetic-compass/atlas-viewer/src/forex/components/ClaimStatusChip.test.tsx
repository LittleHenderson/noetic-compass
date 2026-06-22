import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ClaimStatusChip } from './ClaimStatusChip';

describe('ClaimStatusChip', () => {
  it('renders the status word', () => {
    render(<ClaimStatusChip status="NOT LICENSED" />);
    expect(screen.getByText('NOT LICENSED')).toBeTruthy();
  });

  it('uses the danger tone for NOT LICENSED', () => {
    render(<ClaimStatusChip status="NOT LICENSED" />);
    expect(screen.getByTestId('claim-status-chip').getAttribute('data-tone')).toBe('danger');
  });

  it('uses the teal tone for PASS / VERIFIED', () => {
    render(<ClaimStatusChip status="VERIFIED" />);
    expect(screen.getByTestId('claim-status-chip').getAttribute('data-tone')).toBe('teal');
  });

  it('uses the amber tone for OPEN', () => {
    render(<ClaimStatusChip status="OPEN" />);
    expect(screen.getByTestId('claim-status-chip').getAttribute('data-tone')).toBe('amber');
  });

  it('honors an explicit tone override', () => {
    render(<ClaimStatusChip status="OPEN" tone="muted" />);
    expect(screen.getByTestId('claim-status-chip').getAttribute('data-tone')).toBe('muted');
  });
});
