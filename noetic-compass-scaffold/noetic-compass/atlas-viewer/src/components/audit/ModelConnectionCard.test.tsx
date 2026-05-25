import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { ModelConnectionCard } from './ModelConnectionCard';

describe('ModelConnectionCard', () => {
  it('keeps disconnected connection details hidden and disables Run audit', () => {
    render(
      <ModelConnectionCard
        status="disconnected"
        modelName="Pythia 160M"
        provider="Local worker"
        endpointLabel="http://127.0.0.1:8080"
      />,
    );

    expect(screen.getByText('Model connection')).toBeInTheDocument();
    expect(screen.getByText('Not connected')).toBeInTheDocument();
    expect(screen.queryByText('Pythia 160M')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run audit' })).toBeDisabled();
  });

  it('fires connect and run audit actions when available', () => {
    const connect = vi.fn();
    const runAudit = vi.fn();

    render(
      <ModelConnectionCard
        status="connected"
        onConnect={connect}
        onRunAudit={runAudit}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(runAudit).toHaveBeenCalledTimes(1);
    expect(connect).not.toHaveBeenCalled();
  });

  it('fires disconnect action for connected models', () => {
    const disconnect = vi.fn();

    render(
      <ModelConnectionCard status="connected" onDisconnect={disconnect} />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Disconnect' }));
    expect(disconnect).toHaveBeenCalledTimes(1);
  });
});
