import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ScopeRibbon } from './ScopeRibbon';

describe('ScopeRibbon', () => {
  it('shows the Stage 9 40E scope and boundary string for a validation packet', () => {
    render(
      <ScopeRibbon
        verifierDecision={{ decisionScope: 'stage9_40e_validation_packet' }}
      />,
    );

    expect(screen.getByText('Scope: Stage 9 40E validation packet')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Boundary: this is a validation-packet verdict, not a live customer-production row.',
      ),
    ).toBeInTheDocument();
  });

  it('renders a non-validation scope without the validation boundary caveat', () => {
    render(
      <ScopeRibbon verifierDecision={{ decisionScope: 'live_customer_production' }} />,
    );

    expect(screen.getByText('Scope: live customer production')).toBeInTheDocument();
    expect(
      screen.queryByText(/validation-packet verdict/),
    ).not.toBeInTheDocument();
  });

  it('renders nothing when no scope signal is present', () => {
    const { container } = render(<ScopeRibbon verifierDecision={null} auditScope={null} />);
    expect(container.firstChild).toBeNull();
  });
});
