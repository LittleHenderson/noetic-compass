import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LicenseChip } from './LicenseChip';

describe('LicenseChip', () => {
  it('returns LICENSE UNKNOWN when the entitlement signal is unresolvable', () => {
    render(<LicenseChip signal={{}} />);
    expect(screen.getByText('LICENSE UNKNOWN')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute(
      'aria-label',
      'License status: LICENSE UNKNOWN',
    );
  });

  it('returns LICENSE UNKNOWN when no signal is provided at all', () => {
    render(<LicenseChip />);
    expect(screen.getByText('LICENSE UNKNOWN')).toBeInTheDocument();
  });

  it('reads LICENSED from an explicit entitlement', () => {
    render(<LicenseChip signal={{ entitled: true }} />);
    expect(screen.getByText('LICENSED')).toBeInTheDocument();
  });

  it('reads LICENSED from a non-empty bearer token', () => {
    render(<LicenseChip signal={{ authToken: 'bearer-abc' }} />);
    expect(screen.getByText('LICENSED')).toBeInTheDocument();
  });

  it('reads NOT LICENSED from an explicit negative entitlement', () => {
    render(<LicenseChip signal={{ entitled: false }} />);
    expect(screen.getByText('NOT LICENSED')).toBeInTheDocument();
  });

  it('honors an explicit pre-resolved state prop', () => {
    render(<LicenseChip state="NOT LICENSED" />);
    expect(screen.getByText('NOT LICENSED')).toBeInTheDocument();
  });
});
