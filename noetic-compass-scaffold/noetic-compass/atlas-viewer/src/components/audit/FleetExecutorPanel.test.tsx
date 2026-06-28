import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import FleetExecutorPanel, {
  type FleetExecutorPanelProps,
} from './FleetExecutorPanel';

const readyProps: FleetExecutorPanelProps = {
  registered_workers: 300,
  leased_jobs: 300,
  stale_workers: 0,
  completed_fragments: 300,
  total_jobs: 300,
  merged_packet_status: 'complete',
  verifier_gate_status: 'ready',
};

function renderPanel(overrides: Partial<FleetExecutorPanelProps> = {}) {
  return render(<FleetExecutorPanel {...readyProps} {...overrides} />);
}

describe('FleetExecutorPanel', () => {
  it('shows the distributed fleet executor gates without implying the planner is an audit', () => {
    renderPanel({
      registered_workers: 0,
      leased_jobs: 0,
      completed_fragments: 0,
      total_jobs: 300,
      merged_packet_status: 'not_created',
      verifier_gate_status: 'blocked',
    });

    const panel = screen.getByTestId('fleet-executor-panel');
    expect(panel).toHaveTextContent('Worker registry, leases, receipts');
    expect(panel).toHaveTextContent('does not move forward from a scale plan');
    expect(panel).toHaveTextContent('The planner is only a map');
    expect(screen.getByTestId('fleet-executor-gate')).toHaveTextContent(
      'Blocked: no Probe Workers are registered for this run.',
    );
  });

  it('blocks 300B progress until every job has a lease and receipt', () => {
    renderPanel({
      registered_workers: 300,
      leased_jobs: 299,
      completed_fragments: 298,
      total_jobs: 300,
      merged_packet_status: 'waiting_for_receipts',
      verifier_gate_status: 'waiting_for_packet',
    });

    expect(screen.getByTestId('fleet-leased-jobs')).toHaveTextContent(
      '299 / 300',
    );
    expect(screen.getByTestId('fleet-completed-fragments')).toHaveTextContent(
      '298 / 300',
    );
    expect(screen.getByTestId('fleet-executor-gate')).toHaveTextContent(
      'Blocked: not every distributed job has a worker lease.',
    );
    expect(screen.getByTestId('fleet-gate-leases')).toHaveTextContent(
      'Every layer or shard must be claimed.',
    );
    expect(screen.getByTestId('fleet-gate-receipts')).toHaveTextContent(
      '298 of 300 Evidence Packet fragments returned.',
    );
  });

  it('blocks when any worker heartbeat is stale even if receipts exist', () => {
    renderPanel({
      stale_workers: 2,
      merged_packet_status: 'complete',
      verifier_gate_status: 'ready',
    });

    expect(screen.getByTestId('fleet-stale-workers')).toHaveTextContent('2');
    expect(screen.getByTestId('fleet-executor-gate')).toHaveTextContent(
      'Blocked: stale worker heartbeat detected.',
    );
    expect(screen.getByTestId('fleet-gate-heartbeats')).toHaveTextContent(
      '2 worker heartbeats are stale.',
    );
  });

  it('blocks until the merged packet and verifier gate are ready', () => {
    renderPanel({
      merged_packet_status: 'partial',
      verifier_gate_status: 'waiting_for_packet',
    });

    expect(screen.getByTestId('fleet-merged-packet-status')).toHaveTextContent(
      'Partial',
    );
    expect(screen.getByTestId('fleet-verifier-gate-status')).toHaveTextContent(
      'Waiting For Packet',
    );
    expect(screen.getByTestId('fleet-executor-gate')).toHaveTextContent(
      'Blocked: merged Evidence Packet is not complete.',
    );
  });

  it('shows ready only when registry, leases, receipts, packet, and verifier gate are satisfied', () => {
    renderPanel();

    const gate = screen.getByTestId('fleet-executor-gate');
    expect(gate).toHaveTextContent(
      'Ready: registry, leases, receipts, merged packet, and verifier gate are satisfied.',
    );

    const hardGates = screen.getByRole('heading', { name: 'Hard Gates' });
    expect(hardGates).toBeInTheDocument();
    expect(within(screen.getByTestId('fleet-gate-registry')).getByText(
      'Worker registry',
    )).toBeInTheDocument();
    expect(screen.getByTestId('fleet-gate-verifier')).toHaveTextContent(
      'Verifier gate status: Ready.',
    );
  });

  it('explains S7-F28 balanced-logistic Evidence Packet only when requested', () => {
    renderPanel();

    expect(screen.queryByTestId('fleet-method-faq')).toBeNull();

    const trigger = screen.getByTestId('fleet-method-faq-trigger');
    expect(trigger).toHaveAccessibleName(
      'Explain S7-F28 balanced-logistic Evidence Packet',
    );

    fireEvent.focus(trigger);

    const faq = screen.getByTestId('fleet-method-faq');
    expect(faq).toHaveTextContent('Audit method discipline');
    expect(faq).toHaveTextContent(
      'Use the same label when you check packet rows and verifier logs.',
    );
    expect(faq).toHaveTextContent(
      'positive and negative cases balanced before the verdict is trusted',
    );
    expect(faq).toHaveTextContent(
      'model, prompt set, knobs, worker fragments, score, verdict, and integrity hashes',
    );
    expect(faq).toHaveTextContent(
      'If a text-only classifier can solve the labels from prompt wording alone',
    );
    expect(faq).toHaveTextContent(
      'whether CAS beats a rival coherent labeling',
    );
    expect(faq).toHaveTextContent(
      'If CAS itself is not recoverable from hidden states',
    );
    expect(faq).toHaveTextContent(
      'hold the run instead of treating the verdict as final',
    );
  });
});
