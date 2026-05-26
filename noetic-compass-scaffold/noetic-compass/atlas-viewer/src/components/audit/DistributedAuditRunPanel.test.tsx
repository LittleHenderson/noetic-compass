import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DistributedAuditRunPanel from './DistributedAuditRunPanel';
import type { CasHarnessDistributedAudit } from '../../lib/casHarnessAuditApi';

function audit(overrides: Partial<CasHarnessDistributedAudit> = {}): CasHarnessDistributedAudit {
  return {
    audit_id: 'cas-dist-unit',
    plan_id: 'cas-plan-unit',
    status: 'PLANNED',
    merge_status: 'pending',
    verdict: null,
    confidence: null,
    evidence_packet_trace_id: null,
    merge_reason: 'Distributed audit planned; no worker evidence has been merged yet.',
    created_at: '2026-05-26T10:00:00Z',
    updated_at: '2026-05-26T10:00:00Z',
    ready_workers: 0,
    failed_workers: 0,
    total_workers: 1,
    missing_outputs: [],
    plan: {
      model_id: 'customer/open-100b',
      weight_access: 'open_weight',
      parameter_count_b: 100,
      num_layers: 120,
      scale_tier: 'enterprise_distributed_open_weight',
      recommended_worker_count: 1,
      orchestration_pattern: 'CAS Orchestrator + Probe Workers.',
      worker_assignments: [],
      memory_estimate: {
        precision: 'bf16',
        total_weight_memory_gb: 200,
        activation_overhead_gb: 36,
        estimated_total_runtime_gb: 236,
        estimated_memory_per_worker_gb: 236,
      },
      expected_capability: [],
      evidence_requirements: [],
      limitations: [],
    },
    worker_evidence: [
      {
        worker_id: 'probe-worker-01',
        layer_start: 0,
        layer_end: 9,
        shard_id: 'layers-000-009',
        assigned_methods: ['foundation_probe'],
        expected_outputs: ['layer_activation_summary'],
        worker_status: 'queued',
        produced_outputs: [],
        missing_outputs: [],
        evidence_packet_ref: null,
        error_message: null,
        updated_at: '2026-05-26T10:00:00Z',
      },
    ],
    ...overrides,
  };
}

describe('DistributedAuditRunPanel', () => {
  it('distinguishes planner state from actual worker evidence', () => {
    render(
      <DistributedAuditRunPanel
        audit={null}
        onCreateRun={vi.fn()}
        onDispatchRun={vi.fn()}
        onMergeRun={vi.fn()}
      />,
    );

    expect(screen.getByText(/Worker evidence, not planner theater/i)).toBeInTheDocument();
    expect(screen.getByText(/scale card above is a plan/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create run' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Dispatch workers' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Merge evidence' })).toBeDisabled();
  });

  it('renders worker receipts and merge reason for an existing run', () => {
    render(
      <DistributedAuditRunPanel
        audit={audit({ status: 'DISPATCHED', merge_status: 'partial' })}
        onCreateRun={vi.fn()}
        onDispatchRun={vi.fn()}
        onMergeRun={vi.fn()}
      />,
    );

    expect(screen.getByText('cas-dist-unit')).toBeInTheDocument();
    expect(screen.getByText('0/1 ready')).toBeInTheDocument();
    expect(screen.getByText('probe-worker-01')).toBeInTheDocument();
    expect(screen.getByText('No verdict')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Merge evidence' })).toBeEnabled();
  });

  it('fires command callbacks', () => {
    const onCreateRun = vi.fn();
    const onDispatchRun = vi.fn();
    const onMergeRun = vi.fn();
    render(
      <DistributedAuditRunPanel
        audit={audit()}
        onCreateRun={onCreateRun}
        onDispatchRun={onDispatchRun}
        onMergeRun={onMergeRun}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Create run' }));
    fireEvent.click(screen.getByRole('button', { name: 'Dispatch workers' }));

    expect(onCreateRun).toHaveBeenCalledOnce();
    expect(onDispatchRun).toHaveBeenCalledOnce();
    expect(onMergeRun).not.toHaveBeenCalled();
  });
});
