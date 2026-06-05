import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { AuditComposer } from './AuditComposer';

function baseProps() {
  return {
    connectionStatus: 'disconnected' as const,
    byokApiKey: '',
    onByokApiKeyChange: vi.fn(),
    onRun: vi.fn(),
    runEnabled: true,
    runLabel: 'Prepare target',
  };
}

describe('AuditComposer', () => {
  it('renders the target -> mode -> modules -> Run surface in one panel', () => {
    render(<AuditComposer {...baseProps()} />);

    expect(screen.getByRole('heading', { name: 'Set up an audit' })).toBeInTheDocument();
    // Folds in the model connection card.
    expect(screen.getByRole('heading', { name: 'Model connection' })).toBeInTheDocument();
    // Mode + the customer-facing module chips (plain relabels, no Stage vocab).
    expect(screen.getByText('BALANCED')).toBeInTheDocument();
    expect(screen.getByText('CAS readout')).toBeInTheDocument();
    expect(screen.getByText('Causal check')).toBeInTheDocument();
    expect(screen.getByText('Matched control')).toBeInTheDocument();
    expect(screen.getByText('Output match')).toBeInTheDocument();
    expect(screen.getByText('Evidence packet')).toBeInTheDocument();
    // The BYOK key field is part of the composer.
    expect(
      screen.getByLabelText('Bring your own provider API key (optional)'),
    ).toBeInTheDocument();
  });

  it('fires onRun from the primary Run button', () => {
    const props = baseProps();
    render(<AuditComposer {...props} runLabel="Run CAS audit" />);

    fireEvent.click(screen.getByRole('button', { name: 'Run CAS audit' }));
    expect(props.onRun).toHaveBeenCalledTimes(1);
  });

  it('disables the primary Run button when runEnabled is false', () => {
    render(<AuditComposer {...baseProps()} runEnabled={false} runLabel="Running audit" />);
    expect(screen.getByRole('button', { name: 'Running audit' })).toBeDisabled();
  });

  it('renders demo presets and fires their onSelect', () => {
    const onSelect = vi.fn();
    render(
      <AuditComposer
        {...baseProps()}
        presets={[{ id: 'p1', label: 'Load 20B validation packet', onSelect }]}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Load 20B validation packet' }));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it('wires the BYOK key field to onByokApiKeyChange', () => {
    const props = baseProps();
    render(<AuditComposer {...props} />);

    fireEvent.change(
      screen.getByLabelText('Bring your own provider API key (optional)'),
      { target: { value: 'sk-test' } },
    );
    expect(props.onByokApiKeyChange).toHaveBeenCalledWith('sk-test');
  });

  it('renders the live-trace chip with the honest label, not "live worker status"', () => {
    render(
      <AuditComposer
        {...baseProps()}
        liveChip={{ accent: '#fbbf24', label: 'Live worker reachable · demo mode (not real weights)' }}
      />,
    );

    const chip = screen.getByRole('status', { name: /Live trace status:/i });
    expect(chip).toHaveTextContent('demo mode (not real weights)');
  });
});
