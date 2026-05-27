import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AuditConsolePage from './AuditConsolePage';
import { buildCasHarnessFleetEvidenceFragmentRef } from '../lib/casHarnessAuditApi';

const S7_F28_TRACE_ID = 's7-f28-balanced-bridge-gpt-neox-20b-20260526';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/audit-console']}>
      <AuditConsolePage />
    </MemoryRouter>
  );
}

function sessionResponse(overrides: Record<string, unknown> = {}) {
  return {
    audit_id: 'cas-audit-test-session',
    status: 'DRAFT',
    model_status: 'NOT_CONNECTED_MOCK',
    model_id: 'EleutherAI/pythia-160m',
    endpoint_url: null,
    audit_mode: 'BALANCED',
    prompt_summary: null,
    scenario_summary:
      'Reference audit smoke scenario: validate the CAS Harness audit contract without fabricating a verdict.',
    selected_modules: [
      'model_proof',
      'cas_readout',
      'causal_proof',
      'control_proof',
      'output_proof',
      'packet_proof',
    ],
    created_at: '2026-05-25T11:00:00Z',
    updated_at: '2026-05-25T11:00:00Z',
    verdict: null,
    confidence: null,
    evidence_packet_trace_id: null,
    atlas_deep_link: null,
    verifier_decision: null,
    provenance_chips: [
      {
        id: 'model_proof',
        name: 'Model proof',
        status: 'missing',
        detail: 'No model proof has been verified for this audit session yet.',
      },
      {
        id: 'cas_readout',
        name: 'CAS readout',
        status: 'unavailable',
        detail: 'No CAS readout exists until an Evidence Packet is attached.',
      },
      {
        id: 'causal_proof',
        name: 'Causal proof',
        status: 'unavailable',
        detail: 'No causal proof exists yet.',
      },
      {
        id: 'control_proof',
        name: 'Control proof',
        status: 'unavailable',
        detail: 'No matched control proof exists yet.',
      },
      {
        id: 'output_proof',
        name: 'Output proof',
        status: 'unavailable',
        detail: 'No output proof exists yet.',
      },
      {
        id: 'packet_proof',
        name: 'Packet proof',
        status: 'missing',
        detail: 'No Evidence Packet has been attached.',
      },
    ],
    lifecycle: [
      {
        status: 'DRAFT',
        message: 'Audit session created.',
        timestamp: '2026-05-25T11:00:00Z',
      },
    ],
    ...overrides,
  };
}

function targetVerification(overrides: Record<string, unknown> = {}) {
  return {
    connection_id: 'cas-target-demo',
    connection_state: 'CONNECTED',
    model_status: 'CONNECTED',
    can_run_audit: true,
    target: {
      kind: 'demo_reference',
      provider: 'cas_harness_reference',
      model_id: 'EleutherAI/pythia-160m',
      endpoint_url: null,
      credential_mode: 'none',
      timeout_ms: 10000,
    },
    detail:
      'CAS Harness reference target verified locally. No external model call, credential, Evidence Packet, or audit verdict was created.',
    checked_at: '2026-05-26T10:00:00Z',
    provenance_chip: {
      id: 'model_proof',
      name: 'Model proof',
      status: 'verified',
      detail: 'Reference target verified for non-secret Audit Console demos.',
    },
    verdict: null,
    confidence: null,
    evidence_packet_trace_id: null,
    reference_evidence_packet_trace_id: 'cas_harness_reference_accept_001',
    atlas_deep_link: null,
    ...overrides,
  };
}

function allPresentChips() {
  return [
    'model_proof',
    'cas_readout',
    'causal_proof',
    'control_proof',
    'output_proof',
    'packet_proof',
  ].map((id) => ({
    id,
    name: id === 'cas_readout'
      ? 'CAS readout'
      : `${id.replace('_', ' ')}`
          .replace(/\b\w/g, (letter) => letter.toUpperCase()),
    status: 'present',
    detail: `${id} present`,
  }));
}

function scalePlan() {
  return {
    model_id: 'customer/open-weight-100b',
    weight_access: 'open_weight',
    parameter_count_b: 100,
    num_layers: 120,
    scale_tier: 'enterprise_distributed_open_weight',
    recommended_worker_count: 12,
    orchestration_pattern: 'CAS Orchestrator + distributed Probe Workers.',
    worker_assignments: [
      {
        worker_id: 'probe-worker-01',
        layer_start: 0,
        layer_end: 9,
        shard_id: 'layers-000-009',
        assigned_methods: ['foundation_probe'],
        expected_outputs: ['layer_activation_summary'],
      },
    ],
    memory_estimate: {
      precision: 'bf16',
      total_weight_memory_gb: 200,
      activation_overhead_gb: 36,
      estimated_total_runtime_gb: 236,
      estimated_memory_per_worker_gb: 19.67,
    },
    expected_capability: ['single orchestrated Evidence Packet across all workers'],
    evidence_requirements: ['open model weights or customer-hosted activation hooks'],
    limitations: ['does not support black-box/API-only model audits in this product lane'],
  };
}

function distributedAudit(overrides: Record<string, unknown> = {}) {
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
    plan: scalePlan(),
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
    ready_workers: 0,
    failed_workers: 0,
    total_workers: 1,
    missing_outputs: [],
    ...overrides,
  };
}

function fleetWorker(overrides: Record<string, unknown> = {}) {
  return {
    worker_id: 'probe-worker-01',
    model_id: 'customer/open-weight-100b',
    worker_url: 'local://probe-worker-01',
    gpu_type: 'H100-80GB',
    capacity: 1,
    supported_methods: [
      'foundation_probe',
      'rpm_gate_check',
      'inversion_scan',
      'blindspot_detection',
      'verification_stack',
      'evidence_packet',
    ],
    registered_at: '2026-05-26T10:00:00Z',
    last_heartbeat_at: '2026-05-26T10:00:01Z',
    status: 'active',
    ...overrides,
  };
}

function fleetJob(overrides: Record<string, unknown> = {}) {
  return {
    job_id: 'fleet-job-001',
    audit_id: 'cas-dist-unit',
    assigned_worker_id: 'probe-worker-01',
    layer_start: 0,
    layer_end: 9,
    shard_id: 'layers-000-009',
    assigned_methods: ['foundation_probe'],
    expected_outputs: ['layer_activation_summary'],
    status: 'queued',
    lease_token: null,
    lease_expires_at: null,
    evidence_packet_fragment_ref: null,
    produced_outputs: [],
    missing_outputs: [],
    error_message: null,
    updated_at: '2026-05-26T10:00:00Z',
    ...overrides,
  };
}

function fleetRun(overrides: Record<string, unknown> = {}) {
  return {
    audit_id: 'cas-dist-unit',
    status: 'PREPARED',
    verifier_gate_status: 'waiting_for_workers',
    merged_packet_trace_id: null,
    merge_reason: 'Fleet jobs prepared; waiting for registered workers.',
    created_at: '2026-05-26T10:00:00Z',
    updated_at: '2026-05-26T10:00:00Z',
    total_jobs: 1,
    leased_jobs: 0,
    completed_fragments: 0,
    failed_jobs: 0,
    registered_workers: 0,
    stale_workers: [],
    jobs: [fleetJob()],
    ...overrides,
  };
}

async function fleetFragmentRef(
  overrides: Partial<Parameters<typeof buildCasHarnessFleetEvidenceFragmentRef>[0]> = {},
) {
  return buildCasHarnessFleetEvidenceFragmentRef({
    audit_id: 'cas-dist-unit',
    job_id: 'fleet-job-001',
    worker_id: 'probe-worker-01',
    model_id: 'customer/open-weight-100b',
    layer_start: 0,
    layer_end: 9,
    shard_id: 'layers-000-009',
    expected_outputs: ['layer_activation_summary'],
    produced_outputs: ['layer_activation_summary'],
    missing_outputs: [],
    ...overrides,
  });
}

describe('AuditConsolePage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('presents the CAS audit workflow without the old explanatory clutter', () => {
    renderPage();

    const heading = screen.getByRole('heading', {
      name: 'Connect a model. Run a CAS audit. Return a verdict with evidence.',
    });
    expect(heading).toHaveClass('cas-heading-wave');
    expect(heading).not.toHaveAttribute('title');
    expect(screen.getByText('TURN YOUR BLACK BOX INTO A GLASS HOUSE')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Audit command center' })).toBeInTheDocument();
    expect(screen.getByText(/Worker evidence, not planner theater/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'CONNECT' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'RUN' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'VERDICT' })).toBeInTheDocument();
    expect(screen.getAllByText('Run CAS audit').length).toBeGreaterThan(0);
    expect(screen.getByText('Return verdict + evidence')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'NO VERDICT YET' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Proof chips' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Hover help' })).not.toBeInTheDocument();
    expect(screen.queryByText('License/API')).not.toBeInTheDocument();
    expect(screen.queryByText('Audit mode')).not.toBeInTheDocument();
    expect(screen.queryByText('Inspect in Atlas')).not.toBeInTheDocument();
    expect(screen.queryByText('Evidence count')).not.toBeInTheDocument();
    expect(screen.queryByText('Verdict vocabulary')).not.toBeInTheDocument();

    expect(screen.getByRole('button', { name: 'Run audit' })).toBeDisabled();
    expect(screen.getByRole('heading', { name: 'Audit not started' })).toBeInTheDocument();
    expect(
      screen.getByRole('note', {
        name: 'Connect a supported target before running an audit.',
      }),
    ).toBeInTheDocument();
  });

  it('keeps explanatory wording on hover targets instead of visible paragraphs', () => {
    renderPage();

    expect(
      screen.queryByText(/the UI shows ACCEPT or SUPPRESS only when the/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Audit Console is the decision workflow/i)).not.toBeInTheDocument();
    const commandSubtitle = screen.getByText('Connect. Run. Decide.');
    expect(commandSubtitle).not.toHaveAttribute('title');
    fireEvent.mouseEnter(commandSubtitle);
    expect(screen.getByRole('tooltip')).toHaveTextContent(
      'connect the target, run CAS, then return a verdict',
    );
  });

  it('keeps the pending verdict compact', () => {
    renderPage();

    expect(screen.getByLabelText('Confidence not available')).toBeInTheDocument();
    expect(screen.queryByText(/No verdict yet\. Run a CAS audit/i)).not.toBeInTheDocument();
    expect(screen.queryByText('Not created')).not.toBeInTheDocument();
    expect(screen.queryByText('Not available')).not.toBeInTheDocument();
  });

  it('creates a reference-backed backend session and shows the evidence-gated verdict', async () => {
    const chips = allPresentChips();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => targetVerification(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            evidence_packet_trace_id: 'cas_harness_reference_accept_001',
            provenance_chips: chips,
            verifier_decision: {
              verdict: 'ACCEPT',
              confidence: 0.9816,
              source: 'stage19_verification_stack+stage20_generation_readiness',
              reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
            },
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            status: 'COMPLETE',
            verdict: 'ACCEPT',
            confidence: 0.9816,
            evidence_packet_trace_id: 'cas_harness_reference_accept_001',
            provenance_chips: chips,
            verifier_decision: {
              verdict: 'ACCEPT',
              confidence: 0.9816,
              source: 'stage19_verification_stack+stage20_generation_readiness',
              reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
            },
            updated_at: '2026-05-25T11:01:00Z',
            lifecycle: [
              {
                status: 'DRAFT',
                message: 'Audit session created.',
                timestamp: '2026-05-25T11:00:00Z',
              },
              {
                status: 'VALIDATING',
                message: 'Input contract validated.',
                timestamp: '2026-05-25T11:00:30Z',
              },
              {
                status: 'RUNNING',
                message: 'Run requested.',
                timestamp: '2026-05-25T11:00:45Z',
              },
              {
                status: 'COMPLETE',
                message: 'M3 verdict runner returned the explicit verifier decision from the attached evidence contract.',
                timestamp: '2026-05-25T11:01:00Z',
              },
            ],
          }),
      });
    vi.stubGlobal('fetch', fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Prepare target' }));
    expect(await screen.findByText('Target verified')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run audit' })).toBeEnabled();
    expect(screen.getByRole('note', { name: /reference target verified/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(await screen.findByText('cas-audit-test-session')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'ACCEPT' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Audit complete' })).toBeInTheDocument();
    expect(screen.getByText('Confidence: 98%')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/cas-harness/audit/target/verify',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body))).toEqual({
      target: { kind: 'demo_reference' },
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/cas-harness/audit/session',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(JSON.parse(String((fetchMock.mock.calls[1][1] as RequestInit).body))).toMatchObject({
      evidence_packet_trace_id: 'cas_harness_reference_accept_001',
      model_id: 'EleutherAI/pythia-160m',
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      '/api/cas-harness/audit/session/cas-audit-test-session/run',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('loads the S7-F28 20B evidence packet into the audit lifecycle', async () => {
    const chips = allPresentChips();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            model_id: 'EleutherAI/gpt-neox-20b',
            scenario_summary:
              'Stage 7 Foundation-28 GPT-NeoX-20B evidence packet review using the S7-F28 Balanced Bridge Method.',
            evidence_packet_trace_id: S7_F28_TRACE_ID,
            provenance_chips: chips,
            verifier_decision: {
              verdict: 'FLAG_FOR_HUMAN_REVIEW',
              confidence: 0.803571,
              source: 'S7-F28-BALANCED-BRIDGE',
              reason:
                'S7-F28 packet is strong evidence but routes to human review until the final verifier merge layer closes.',
            },
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            status: 'COMPLETE',
            model_id: 'EleutherAI/gpt-neox-20b',
            verdict: 'FLAG_FOR_HUMAN_REVIEW',
            confidence: 0.803571,
            scenario_summary:
              'Stage 7 Foundation-28 GPT-NeoX-20B evidence packet review using the S7-F28 Balanced Bridge Method.',
            evidence_packet_trace_id: S7_F28_TRACE_ID,
            atlas_deep_link: `/cockpit?trace_id=${S7_F28_TRACE_ID}`,
            provenance_chips: chips,
            verifier_decision: {
              verdict: 'FLAG_FOR_HUMAN_REVIEW',
              confidence: 0.803571,
              source: 'S7-F28-BALANCED-BRIDGE',
              reason:
                'S7-F28 packet is strong evidence but routes to human review until the final verifier merge layer closes.',
            },
            updated_at: '2026-05-26T22:06:00Z',
            lifecycle: [
              {
                status: 'DRAFT',
                message: 'Audit session created with S7-F28 Evidence Packet.',
                timestamp: '2026-05-26T22:05:00Z',
              },
              {
                status: 'COMPLETE',
                message:
                  'S7-F28 Balanced Bridge packet returned a conservative human-review verdict.',
                timestamp: '2026-05-26T22:06:00Z',
              },
            ],
          }),
      });
    vi.stubGlobal('fetch', fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Load 20B packet' }));

    expect(screen.getByText('EleutherAI/gpt-neox-20b')).toBeInTheDocument();
    expect(screen.getByText('S7-F28 Balanced Bridge Method')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run audit' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(
      await screen.findByRole('heading', { name: 'FLAG FOR HUMAN REVIEW' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Confidence: 80%')).toBeInTheDocument();
    expect(screen.getAllByText(S7_F28_TRACE_ID).length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/cas-harness/audit/session',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body))).toMatchObject({
      evidence_packet_trace_id: S7_F28_TRACE_ID,
      model_id: 'EleutherAI/gpt-neox-20b',
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/cas-harness/audit/session/cas-audit-test-session/run',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('creates and dispatches a distributed audit run from the enterprise plan panel', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => distributedAudit(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => distributedAudit({ status: 'DISPATCHED' }),
      });
    vi.stubGlobal('fetch', fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Create run' }));
    expect(await screen.findByText('cas-dist-unit')).toBeInTheDocument();
    expect(screen.getByText('0/1 ready')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Dispatch workers' }));
    expect(await screen.findByText('DISPATCHED')).toBeInTheDocument();
    expect(screen.getByTestId('distributed-merge-gate')).toHaveTextContent(/worker receipt is still pending/i);
    expect(screen.getByRole('button', { name: 'Merge distributed receipts' })).toBeDisabled();

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      '/api/cas-harness/audit/distributed/session',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/dispatch',
    ]);
  });

  it('wires fleet executor controls to prepare, register, lease, receipt, and merge APIs', async () => {
    const fragmentRef = await fleetFragmentRef();
    const leasedJob = fleetJob({
      status: 'leased',
      lease_token: 'lease-token-001',
      lease_expires_at: '2026-05-26T10:05:00Z',
      updated_at: '2026-05-26T10:01:00Z',
    });
    const completedJob = fleetJob({
      status: 'completed',
      evidence_packet_fragment_ref: fragmentRef,
      produced_outputs: ['layer_activation_summary'],
      updated_at: '2026-05-26T10:02:00Z',
    });
    const readyRun = fleetRun({
      status: 'MERGE_PENDING',
      verifier_gate_status: 'ready_for_verifier',
      merge_reason: 'All worker Evidence Packet fragments returned; verifier gate is ready.',
      registered_workers: 1,
      completed_fragments: 1,
      jobs: [completedJob],
    });
    const mergedRun = fleetRun({
      status: 'COMPLETE',
      verifier_gate_status: 'ready_for_verifier',
      merged_packet_trace_id: 'cas-dist-unit-merged-packet',
      merge_reason:
        'Merged packet ready for verifier decision. Final ACCEPT/SUPPRESS still requires verifier decision layer.',
      registered_workers: 1,
      completed_fragments: 1,
      jobs: [completedJob],
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => distributedAudit(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          distributedAudit({
            status: 'DISPATCHED',
            worker_evidence: [
              {
                ...distributedAudit().worker_evidence[0],
                worker_status: 'assigned',
              },
            ],
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => fleetRun(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => fleetWorker(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => leasedJob,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => readyRun,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mergedRun,
      });
    vi.stubGlobal('fetch', fetchMock);

    renderPage();

    expect(screen.getByRole('button', { name: 'Prepare fleet' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Merge fleet' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Protected API token'), {
      target: { value: 'fleet-jwt' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Create run' }));
    expect(await screen.findByText('cas-dist-unit')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Dispatch workers' }));
    expect(await screen.findByText('DISPATCHED')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Prepare fleet' }));
    expect(await screen.findByTestId('fleet-executor-gate')).toHaveTextContent(
      /waiting for registered/i,
    );
    expect(screen.getByRole('button', { name: 'Lease one job' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Merge fleet' })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Register demo worker' }));
    expect(await screen.findByText('1/1')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Lease one job' }));
    expect(await screen.findByText('1/1')).toBeInTheDocument();
    expect(screen.getByTestId('fleet-executor-gate')).toHaveTextContent(/receipts are still missing/i);
    expect(screen.getByRole('button', { name: 'Merge fleet' })).toBeDisabled();
    expect(screen.queryByText('lease-token-001')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Submit one receipt' }));
    expect(await screen.findByText('ready for verifier')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Merge fleet' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: 'Merge fleet' }));
    expect(await screen.findByText(/cas-dist-unit-merged-packet/)).toBeInTheDocument();
    expect(screen.getByText(/Final ACCEPT\/SUPPRESS still requires verifier decision layer/i)).toBeInTheDocument();

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      '/api/cas-harness/audit/distributed/session',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/dispatch',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/prepare',
      '/api/cas-harness/audit/distributed/fleet/worker/register',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/job/lease',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/job/fleet-job-001/receipt',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/merge',
    ]);
    expect(JSON.parse(String((fetchMock.mock.calls[3][1] as RequestInit).body))).toMatchObject({
      worker_id: 'probe-worker-01',
      gpu_type: 'H100-80GB',
    });
    expect(JSON.parse(String((fetchMock.mock.calls[5][1] as RequestInit).body))).toMatchObject({
      worker_id: 'probe-worker-01',
      lease_token: 'lease-token-001',
      evidence_packet_fragment_ref: fragmentRef,
      job_status: 'completed',
    });
    for (const call of fetchMock.mock.calls) {
      expect((call[1] as RequestInit).headers).toMatchObject({
        Authorization: 'Bearer fleet-jwt',
      });
    }
  });

  it('keeps fleet merge disabled when the backend verifier gate is blocked', async () => {
    const blockedFragmentRef = await fleetFragmentRef({
      produced_outputs: [],
      missing_outputs: ['layer_activation_summary'],
    });
    const leasedJob = fleetJob({
      status: 'leased',
      lease_token: 'lease-token-001',
      lease_expires_at: '2026-05-26T10:05:00Z',
      updated_at: '2026-05-26T10:01:00Z',
    });
    const blockedJob = fleetJob({
      status: 'completed',
      evidence_packet_fragment_ref: blockedFragmentRef,
      produced_outputs: [],
      missing_outputs: ['layer_activation_summary'],
      updated_at: '2026-05-26T10:02:00Z',
    });
    const blockedRun = fleetRun({
      status: 'MERGE_PENDING',
      verifier_gate_status: 'blocked_missing_outputs',
      merge_reason: 'At least one worker receipt is missing required outputs; cannot ACCEPT.',
      registered_workers: 1,
      completed_fragments: 1,
      jobs: [blockedJob],
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => distributedAudit() })
      .mockResolvedValueOnce({ ok: true, json: async () => distributedAudit({ status: 'DISPATCHED' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => fleetRun() })
      .mockResolvedValueOnce({ ok: true, json: async () => fleetWorker() })
      .mockResolvedValueOnce({ ok: true, json: async () => leasedJob })
      .mockResolvedValueOnce({ ok: true, json: async () => blockedRun });
    vi.stubGlobal('fetch', fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Create run' }));
    expect(await screen.findByText('cas-dist-unit')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Dispatch workers' }));
    expect(await screen.findByText('DISPATCHED')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Prepare fleet' }));
    expect(await screen.findByTestId('fleet-executor-gate')).toHaveTextContent(/waiting for registered/i);
    fireEvent.click(screen.getByRole('button', { name: 'Register demo worker' }));
    expect(await screen.findByText('1/1')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Lease one job' }));
    expect(await screen.findByText('waiting for receipts')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Submit one receipt' }));

    expect(await screen.findByTestId('fleet-executor-gate')).toHaveTextContent(/missing required outputs/i);
    expect(screen.getByRole('button', { name: 'Merge fleet' })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(6);
  });

  it('explains a backend ACCEPT verdict with verifier reason and proof chips', async () => {
    const chips = allPresentChips();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => targetVerification(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sessionResponse({
          evidence_packet_trace_id: 'stage21-allow-001',
          provenance_chips: chips,
          verifier_decision: {
            verdict: 'ACCEPT',
            confidence: 0.9816,
            source: 'stage19_verification_stack+stage20_generation_readiness',
            reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            status: 'COMPLETE',
            verdict: 'ACCEPT',
            confidence: 0.9816,
            evidence_packet_trace_id: 'stage21-allow-001',
            provenance_chips: chips,
            verifier_decision: {
              verdict: 'ACCEPT',
              confidence: 0.9816,
              source: 'stage19_verification_stack+stage20_generation_readiness',
              reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
            },
            lifecycle: [
              {
                status: 'DRAFT',
                message: 'Audit session created.',
                timestamp: '2026-05-25T11:00:00Z',
              },
              {
                status: 'COMPLETE',
                message: 'M3 verdict runner returned the explicit verifier decision from the attached evidence contract.',
                timestamp: '2026-05-25T11:01:00Z',
              },
            ],
          }),
      });
    vi.stubGlobal('fetch', fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Prepare target' }));
    expect(await screen.findByText('Target verified')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(await screen.findByRole('heading', { name: 'ACCEPT' })).toBeInTheDocument();
    expect(screen.getByText(/Accepted because the verifier explicitly allowed it/i)).toBeInTheDocument();
    expect(screen.getByText('Proof chips ready: 6/6')).toBeInTheDocument();
    expect(screen.getByText('Confidence: 98%')).toBeInTheDocument();
    expect(
      screen.getByRole('note', { name: /Stage 19 accepted the row and Stage 20 readiness action is allow/i }),
    ).toBeInTheDocument();
  });
});
