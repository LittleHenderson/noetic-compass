import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { NccsGauge } from '../../components/charts/NccsGauge';

describe('NccsGauge', () => {
  it('renders composite score', () => {
    render(<NccsGauge composite={76.0} certification="Gold" />);
    expect(screen.getByText('76.0')).toBeInTheDocument();
    expect(screen.getByText('NCCS Composite')).toBeInTheDocument();
  });

  it('renders zero score', () => {
    render(<NccsGauge composite={0} certification="Fail" />);
    expect(screen.getByText('0.0')).toBeInTheDocument();
  });

  it('renders perfect score', () => {
    render(<NccsGauge composite={100} certification="Platinum" />);
    expect(screen.getByText('100.0')).toBeInTheDocument();
  });
});
