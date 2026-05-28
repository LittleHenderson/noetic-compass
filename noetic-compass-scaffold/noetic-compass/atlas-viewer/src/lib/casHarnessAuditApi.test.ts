import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  buildCasHarnessFleetEvidenceFragmentRef,
  CasHarnessAuditApiError,
  createCasHarnessAuditSession,
  createCasHarnessDistributedAudit,
  createCasHarnessScalePlan,
  dispatchCasHarnessDistributedAudit,
  getCasHarnessAuditSessionStatus,
  getCasHarnessFleetRun,
  heartbeatCasHarnessFleetWorker,
  leaseCasHarnessFleetJob,
  listCasHarnessAuditSessions,
  listCasHarnessFleetRuns,
  listCasHarnessFleetWorkers,
  mergeCasHarnessDistributedAudit,
  mergeCasHarnessFleetRun,
  parseAuditSessionResponse,
  parseDistributedAuditResponse,
  parseFleetVerifierDecisionResponse,
  parseFleetRunResponse,
  parseModelTargetVerificationResponse,
  parseNullableFleetJobResponse,
  parseScalePlanResponse,
  prepareCasHarnessFleetRun,
  registerCasHarnessFleetWorker,
  resolveCasHarnessAuditBaseUrl,
  scanCasHarnessFleetStaleWorkers,
  startCasHarnessAuditSession,
  submitCasHarnessFleetJobReceipt,
  submitCasHarnessDistributedWorkerEvidence,
  verifyCasHarnessFleetRun,
  verifyCasHarnessModelTarget,
} from './casHarnessAuditApi';

function jsonResponse(
  body: unknown,
  status = 200,
  statusText?: string,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    statusText,
    headers: { 'Content-Type': 'application/json' },
  });
}

function pendingSession(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    audit_id: 'cas-audit-unit',
    status: 'SCAFFOLD_PENDING_RUNNER',
    model_status: 'NOT_CONNECTED_MOCK',
    model_id: 'EleutherAI/pythia-160m',
    endpoint_url: null,
    audit_mode: 'BALANCED',
    prompt_summary: null,
    scenario_summary: 'Audit this output.',
    selected_modules: ['model_proof', 'cas_readout'],
    created_at: '2026-05-25T11:00:00Z',
    updated_at: '2026-05-25T11:00:00Z',
    verdict: null,
    confidence: null,
    evidence_packet_trace_id: null,
    atlas_deep_link: null,
    provenance_chips: [
      {
        id: 'model_proof',
        name: 'Model proof',
        status: 'missing',
        detail: 'No model proof has been verified for this audit session yet.',
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

function targetVerification(overrides: Record<string, unknown> = {}): Record<string, unknown> {
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
      'CAS Harness reference target verified locally. No verdict was created.',
    checked_at: '2026-05-26T10:00:00Z',
    provenance_chip: {
      id: 'model_proof',
      name: 'Model proof',
      status: 'verified',
      detail: 'Reference target verified for target connection only.',
    },
    verdict: null,
    confidence: null,
    evidence_packet_trace_id: null,
    reference_evidence_packet_trace_id: 'cas_harness_reference_accept_001',
    atlas_deep_link: null,
    ...overrides,
  };
}

function scalePlan(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    model_id: 'customer/open-100b',
    weight_access: 'open_weight',
    parameter_count_b: 100,
    num_layers: 120,
    scale_tier: 'enterprise_distributed_open_weight',
    recommended_worker_count: 12,
    orchestration_pattern:
      'CAS Orchestrator + distributed Probe Workers assigned by contiguous layer ranges and model shards; one merged Evidence Packet and one verdict.',
    worker_assignments: [
      {
        worker_id: 'probe-worker-01',
        layer_start: 0,
        layer_end: 9,
        shard_id: 'layers-000-009',
        assigned_methods: ['foundation_probe', 'targeted_ablation'],
        expected_outputs: ['layer_activation_summary', 'worker_evidence_manifest'],
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
    ...overrides,
  };
}

function distributedAudit(overrides: Record<string, unknown> = {}): Record<string, unknown> {
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
        assigned_methods: ['foundation_probe', 'targeted_ablation'],
        expected_outputs: ['layer_activation_summary', 'worker_evidence_manifest'],
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

function distributedWorker(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    ...(distributedAudit().worker_evidence[0] as Record<string, unknown>),
    ...overrides,
  };
}

function fleetWorker(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    worker_id: 'probe-worker-01',
    model_id: 'customer/open-100b',
    worker_url: 'https://worker-01.example',
    gpu_type: 'H100-80GB',
    capacity: 1,
    supported_methods: ['foundation_probe', 'targeted_ablation'],
    registered_at: '2026-05-26T10:01:00Z',
    last_heartbeat_at: '2026-05-26T10:02:00Z',
    status: 'active',
    ...overrides,
  };
}

function fleetJob(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    job_id: 'fleet-job-01',
    audit_id: 'cas-dist-unit',
    assigned_worker_id: 'probe-worker-01',
    layer_start: 0,
    layer_end: 9,
    shard_id: 'layers-000-009',
    assigned_methods: ['foundation_probe', 'targeted_ablation'],
    expected_outputs: ['layer_activation_summary', 'worker_evidence_manifest'],
    status: 'queued',
    lease_token: null,
    lease_expires_at: null,
    evidence_packet_fragment_ref: null,
    produced_outputs: [],
    missing_outputs: [],
    error_message: null,
    updated_at: '2026-05-26T10:02:00Z',
    ...overrides,
  };
}

function fleetRun(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    audit_id: 'cas-dist-unit',
    status: 'PREPARED',
    verifier_gate_status: 'waiting_for_receipts',
    merged_packet_trace_id: null,
    merge_reason: 'Waiting for worker Evidence Packet fragment receipts.',
    created_at: '2026-05-26T10:01:00Z',
    updated_at: '2026-05-26T10:02:00Z',
    total_jobs: 1,
    leased_jobs: 0,
    completed_fragments: 0,
    failed_jobs: 0,
    registered_workers: 1,
    stale_workers: [],
    readiness: {
      status: 'waiting',
      headline: 'Large-model eval is waiting on workers or fragment receipts.',
      blockers: ['1 Evidence Packet fragment receipt(s) are still missing.'],
      next_actions: ['Lease queued jobs to their registered workers.'],
      verifier_owned: true,
    },
    jobs: [fleetJob()],
    ...overrides,
  };
}

function fleetVerifierDecision(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    audit_id: 'cas-dist-unit',
    merged_packet_trace_id: 'cas-dist-unit-fleet-merge',
    verdict: 'FLAG_FOR_HUMAN_REVIEW',
    confidence: null,
    source: 'fleet_packet_verifier',
    reason:
      'Fleet receipts are merged, but ACCEPT/SUPPRESS requires an explicit verifier decision over the merged Evidence Packet.',
    decision_scope: 'distributed_fleet_merged_packet',
    coverage: {
      basis: 'fleet_worker_fragments',
      total_jobs: 1,
      completed_fragments: 1,
      failed_jobs: 0,
      missing_output_jobs: 0,
      distributed_merge_status: 'complete',
    },
    proof_chip_gate: 'blocked',
    blockers: [
      'Merged distributed packet has worker receipts but no explicit proof-chip verifier decision.',
    ],
    next_actions: [
      'Attach Stage 19/20/21 verifier output or packet-level explicit_verifier_decision.',
      'Keep the public verdict at FLAG FOR HUMAN REVIEW until proof chips pass.',
    ],
    created_at: '2026-05-26T10:05:00Z',
    ...overrides,
  };
}

async function fleetFragmentRef(
  overrides: Partial<Parameters<typeof buildCasHarnessFleetEvidenceFragmentRef>[0]> = {},
): Promise<string> {
  return buildCasHarnessFleetEvidenceFragmentRef({
    audit_id: 'cas-dist-unit',
    job_id: 'fleet-job-01',
    worker_id: 'probe-worker-01',
    model_id: 'customer/open-100b',
    layer_start: 0,
    layer_end: 9,
    shard_id: 'layers-000-009',
    expected_outputs: ['layer_activation_summary', 'worker_evidence_manifest'],
    produced_outputs: ['layer_activation_summary', 'worker_evidence_manifest'],
    missing_outputs: [],
    ...overrides,
  });
}

describe('casHarnessAuditApi', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('creates an audit session with the expected URL, method, headers, and body', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(pendingSession()));
    const payload = {
      model_id: 'EleutherAI/pythia-160m',
      audit_mode: 'BALANCED' as const,
      prompt: 'Audit this answer.',
      selected_modules: ['foundation_probe', 'verification_stack'],
      license_key: 'license-test',
    };

    const session = await createCasHarnessAuditSession(payload, {
      baseUrl: '/api/cas-harness/audit/',
      fetchImpl,
    });

    expect(session.audit_id).toBe('cas-audit-unit');
    expect(session.model_id).toBe('EleutherAI/pythia-160m');
    expect(session.audit_mode).toBe('BALANCED');
    expect(session.selected_modules).toEqual(['model_proof', 'cas_readout']);
    expect(session.lifecycle[0]?.status).toBe('DRAFT');
    expect(session.provenance_chips[0]).toMatchObject({
      id: 'model_proof',
      status: 'missing',
      statusLabel: 'Missing',
    });
    expect(session.verdict).toBeNull();
    expect(session.confidence).toBeNull();
    expect(session.verifier_decision).toBeNull();
    expect(fetchImpl).toHaveBeenCalledOnce();
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('/api/cas-harness/audit/session');
    expect(init).toMatchObject({
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });
    expect(JSON.parse(String((init as RequestInit).body))).toEqual(payload);
  });

  it('verifies the built-in demo reference target without fabricating a verdict', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(targetVerification()));

    const result = await verifyCasHarnessModelTarget(
      { target: { kind: 'demo_reference' } },
      {
        baseUrl: '/api/cas-harness/audit/',
        fetchImpl,
      },
    );

    expect(result.connection_id).toBe('cas-target-demo');
    expect(result.connection_state).toBe('CONNECTED');
    expect(result.model_status).toBe('CONNECTED');
    expect(result.target).toMatchObject({
      kind: 'demo_reference',
      model_id: 'EleutherAI/pythia-160m',
      credential_mode: 'none',
    });
    expect(result.verdict).toBeNull();
    expect(result.confidence).toBeNull();
    expect(result.reference_evidence_packet_trace_id).toBe(
      'cas_harness_reference_accept_001',
    );
    expect(result.provenance_chip).toMatchObject({
      id: 'model_proof',
      status: 'verified',
      statusLabel: 'Verified',
    });
    expect(fetchImpl).toHaveBeenCalledOnce();
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('/api/cas-harness/audit/target/verify');
    expect(init).toMatchObject({
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });
    expect(JSON.parse(String((init as RequestInit).body))).toEqual({
      target: { kind: 'demo_reference' },
    });
  });

  it('creates an enterprise scale plan through the audit API', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(scalePlan()));
    const result = await createCasHarnessScalePlan(
      {
        model_id: 'customer/open-100b',
        weight_access: 'open_weight',
        parameter_count_b: 100,
        num_layers: 120,
        precision: 'bf16',
        available_gpu_memory_gb: 80,
      },
      {
        baseUrl: '/api/cas-harness/audit',
        fetchImpl,
      },
    );

    expect(result.scale_tier).toBe('enterprise_distributed_open_weight');
    expect(result.weight_access).toBe('open_weight');
    expect(result.worker_assignments[0]).toMatchObject({
      worker_id: 'probe-worker-01',
      layer_start: 0,
      layer_end: 9,
    });
    expect(result.limitations.join(' ')).toMatch(/black-box/);
    expect(fetchImpl.mock.calls[0][0]).toBe('/api/cas-harness/audit/scale-plan');
    expect(JSON.parse(String((fetchImpl.mock.calls[0][1] as RequestInit).body))).toMatchObject({
      model_id: 'customer/open-100b',
      parameter_count_b: 100,
    });
  });

  it('creates, dispatches, records, and merges a distributed audit through the API', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(distributedAudit()))
      .mockResolvedValueOnce(jsonResponse(distributedAudit({ status: 'DISPATCHED' })))
      .mockResolvedValueOnce(jsonResponse(distributedAudit({
        status: 'MERGE_PENDING',
        merge_status: 'partial',
        worker_evidence: [
          distributedWorker({
            worker_status: 'completed',
            produced_outputs: ['layer_activation_summary', 'worker_evidence_manifest'],
            evidence_packet_ref: 'packet://probe-worker-01',
          }),
        ],
        ready_workers: 1,
      })))
      .mockResolvedValueOnce(jsonResponse(distributedAudit({
        status: 'COMPLETE',
        merge_status: 'complete',
        verdict: 'FLAG_FOR_HUMAN_REVIEW',
        confidence: null,
        evidence_packet_trace_id: 'cas-dist-unit-distributed-merge',
        worker_evidence: [
          distributedWorker({
            worker_status: 'completed',
            produced_outputs: ['layer_activation_summary', 'worker_evidence_manifest'],
            evidence_packet_ref: 'packet://probe-worker-01',
          }),
        ],
        ready_workers: 1,
        merge_reason: 'All distributed worker evidence receipts merged. Final ACCEPT/SUPPRESS still requires the verifier decision layer over the merged Evidence Packet.',
      })));

    const created = await createCasHarnessDistributedAudit(
      {
        model_id: 'customer/open-100b',
        weight_access: 'open_weight',
        parameter_count_b: 100,
        num_layers: 120,
      },
      { baseUrl: '/api/cas-harness/audit', fetchImpl },
    );
    const dispatched = await dispatchCasHarnessDistributedAudit(created.audit_id, {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });
    const receipted = await submitCasHarnessDistributedWorkerEvidence(
      created.audit_id,
      'probe-worker-01',
      {
        produced_outputs: ['layer_activation_summary', 'worker_evidence_manifest'],
        evidence_packet_ref: 'packet://probe-worker-01',
      },
      { baseUrl: '/api/cas-harness/audit', fetchImpl },
    );
    const merged = await mergeCasHarnessDistributedAudit(created.audit_id, {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });

    expect(created.status).toBe('PLANNED');
    expect(dispatched.status).toBe('DISPATCHED');
    expect(receipted.ready_workers).toBe(1);
    expect(merged.merge_status).toBe('complete');
    expect(merged.verdict).toBe('FLAG_FOR_HUMAN_REVIEW');
    expect(merged.confidence).toBeNull();
    expect(merged.worker_evidence[0]).toMatchObject({
      worker_status: 'completed',
      evidence_packet_ref: 'packet://probe-worker-01',
      missing_outputs: [],
    });
    expect(merged.merge_reason).toMatch(/Final ACCEPT\/SUPPRESS still requires/);
    expect(fetchImpl.mock.calls.map((call) => call[0])).toEqual([
      '/api/cas-harness/audit/distributed/session',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/dispatch',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/worker/probe-worker-01/evidence',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/merge',
    ]);
  });

  it('adds Authorization when callers supply an audit auth token', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(distributedAudit({ status: 'DISPATCHED' })));

    await dispatchCasHarnessDistributedAudit('cas-dist-unit', {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
      authToken: 'fleet-jwt',
    });

    expect(fetchImpl.mock.calls[0][1]).toMatchObject({
      headers: {
        Accept: 'application/json',
        Authorization: 'Bearer fleet-jwt',
      },
    });
  });

  it('preserves explicit Bearer auth tokens without double-prefixing', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(distributedAudit({ status: 'DISPATCHED' })));

    await dispatchCasHarnessDistributedAudit('cas-dist-unit', {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
      authToken: 'Bearer already-prefixed',
    });

    expect((fetchImpl.mock.calls[0][1] as RequestInit).headers).toMatchObject({
      Authorization: 'Bearer already-prefixed',
    });
  });

  it('registers, lists, heartbeats, and stale-scans fleet workers through the API', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(fleetWorker()))
      .mockResolvedValueOnce(jsonResponse({ workers: [fleetWorker()] }))
      .mockResolvedValueOnce(jsonResponse(fleetWorker({ last_heartbeat_at: '2026-05-26T10:03:00Z' })))
      .mockResolvedValueOnce(jsonResponse({ workers: [fleetWorker({ status: 'stale' })] }));

    const registered = await registerCasHarnessFleetWorker(
      {
        worker_id: 'probe-worker-01',
        model_id: 'customer/open-100b',
        worker_url: 'https://worker-01.example',
        gpu_type: 'H100-80GB',
        supported_methods: ['foundation_probe', 'targeted_ablation'],
        capacity: 1,
      },
      { baseUrl: '/api/cas-harness/audit', fetchImpl },
    );
    const listed = await listCasHarnessFleetWorkers({
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });
    const heartbeat = await heartbeatCasHarnessFleetWorker('probe-worker-01', {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });
    const stale = await scanCasHarnessFleetStaleWorkers(
      { max_heartbeat_age_seconds: 1 },
      { baseUrl: '/api/cas-harness/audit', fetchImpl },
    );

    expect(registered.status).toBe('active');
    expect(listed.workers[0]?.worker_id).toBe('probe-worker-01');
    expect(heartbeat.last_heartbeat_at).toBe('2026-05-26T10:03:00Z');
    expect(stale.workers[0]?.status).toBe('stale');
    expect(fetchImpl.mock.calls.map((call) => call[0])).toEqual([
      '/api/cas-harness/audit/distributed/fleet/worker/register',
      '/api/cas-harness/audit/distributed/fleet/workers',
      '/api/cas-harness/audit/distributed/fleet/worker/probe-worker-01/heartbeat',
      '/api/cas-harness/audit/distributed/fleet/workers/stale-scan',
    ]);
    expect(JSON.parse(String((fetchImpl.mock.calls[3][1] as RequestInit).body))).toEqual({
      max_heartbeat_age_seconds: 1,
    });
  });

  it('prepares, leases, receipts, merges, gets, and lists fleet runs without fabricating ACCEPT', async () => {
    const fragmentRef = await fleetFragmentRef();
    const leasedJob = fleetJob({
      status: 'leased',
      lease_token: 'lease-token-01',
      lease_expires_at: '2026-05-26T10:30:00Z',
    });
    const completedJob = fleetJob({
      status: 'completed',
      lease_expires_at: '2026-05-26T10:30:00Z',
      evidence_packet_fragment_ref: fragmentRef,
      produced_outputs: ['layer_activation_summary', 'worker_evidence_manifest'],
    });
    const readyRun = fleetRun({
      status: 'MERGE_PENDING',
      verifier_gate_status: 'ready_for_verifier',
      completed_fragments: 1,
      readiness: {
        status: 'ready',
        headline: 'Large-model worker receipts are complete; verifier review is unblocked.',
        blockers: [],
        next_actions: [
          'Merge fleet evidence into one distributed Evidence Packet.',
          'Then run the verifier decision layer; fleet merge alone cannot ACCEPT.',
        ],
        verifier_owned: true,
      },
      jobs: [completedJob],
    });
    const mergedRun = fleetRun({
      status: 'COMPLETE',
      verifier_gate_status: 'ready_for_verifier',
      merged_packet_trace_id: 'cas-dist-unit-fleet-merge',
      merge_reason:
        'All fleet job fragments are present. Merged Evidence Packet is ready for the verifier decision layer; fleet executor does not fabricate ACCEPT.',
      completed_fragments: 1,
      readiness: {
        status: 'ready',
        headline: 'Large-model worker receipts are complete; verifier review is unblocked.',
        blockers: [],
        next_actions: ['Run the verifier decision layer over the merged Evidence Packet.'],
        verifier_owned: true,
      },
      jobs: [completedJob],
    });
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(fleetRun()))
      .mockResolvedValueOnce(jsonResponse(leasedJob))
      .mockResolvedValueOnce(jsonResponse(readyRun))
      .mockResolvedValueOnce(jsonResponse(mergedRun))
      .mockResolvedValueOnce(jsonResponse(fleetVerifierDecision()))
      .mockResolvedValueOnce(jsonResponse(mergedRun))
      .mockResolvedValueOnce(jsonResponse({ runs: [mergedRun] }));

    const prepared = await prepareCasHarnessFleetRun('cas-dist-unit', {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });
    const leased = await leaseCasHarnessFleetJob(
      'cas-dist-unit',
      { worker_id: 'probe-worker-01', lease_seconds: 900 },
      { baseUrl: '/api/cas-harness/audit', fetchImpl },
    );
    const receipted = await submitCasHarnessFleetJobReceipt(
      'cas-dist-unit',
      'fleet-job-01',
      {
        worker_id: 'probe-worker-01',
        lease_token: 'lease-token-01',
        produced_outputs: ['layer_activation_summary', 'worker_evidence_manifest'],
        evidence_packet_fragment_ref: fragmentRef,
      },
      { baseUrl: '/api/cas-harness/audit', fetchImpl },
    );
    const merged = await mergeCasHarnessFleetRun('cas-dist-unit', {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });
    const verified = await verifyCasHarnessFleetRun('cas-dist-unit', {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });
    const fetched = await getCasHarnessFleetRun('cas-dist-unit', {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });
    const listed = await listCasHarnessFleetRuns({
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });

    expect(prepared.verifier_gate_status).toBe('waiting_for_receipts');
    expect(prepared.readiness.status).toBe('waiting');
    expect(prepared.readiness.verifier_owned).toBe(true);
    expect(leased).toMatchObject({
      status: 'leased',
      lease_token: 'lease-token-01',
    });
    expect(receipted.verifier_gate_status).toBe('ready_for_verifier');
    expect(receipted.readiness.next_actions).toContain(
      'Then run the verifier decision layer; fleet merge alone cannot ACCEPT.',
    );
    expect(receipted.jobs[0]).toMatchObject({
      status: 'completed',
      evidence_packet_fragment_ref: fragmentRef,
    });
    expect(merged.status).toBe('COMPLETE');
    expect(merged.merged_packet_trace_id).toBe('cas-dist-unit-fleet-merge');
    expect(merged.merge_reason).toMatch(/does not fabricate ACCEPT/);
    expect(merged.readiness.next_actions).toEqual([
      'Run the verifier decision layer over the merged Evidence Packet.',
    ]);
    expect(verified).toMatchObject({
      audit_id: 'cas-dist-unit',
      merged_packet_trace_id: 'cas-dist-unit-fleet-merge',
      verdict: 'FLAG_FOR_HUMAN_REVIEW',
      confidence: null,
      source: 'fleet_packet_verifier',
      proof_chip_gate: 'blocked',
    });
    expect(verified.coverage.completed_fragments).toBe(1);
    expect(verified.blockers.join(' ')).toMatch(/no explicit proof-chip verifier decision/i);
    expect(fetched.audit_id).toBe('cas-dist-unit');
    expect(listed.runs[0]?.status).toBe('COMPLETE');
    expect(fetchImpl.mock.calls.map((call) => call[0])).toEqual([
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/prepare',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/job/lease',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/job/fleet-job-01/receipt',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/merge',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/verifier',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet',
      '/api/cas-harness/audit/distributed/fleet/runs',
    ]);
  });

  it('builds canonical content-addressed fleet Evidence Packet fragment refs', async () => {
    const fragmentRef = await fleetFragmentRef();

    expect(fragmentRef).toMatch(
      /^cas-fragment:\/\/cas-dist-unit\/fleet-job-01\/probe-worker-01\/layers-000-009\/sha256:[a-f0-9]{64}$/,
    );
    expect(fragmentRef).not.toContain('evidence-fragment');
  });

  it('redacts lease tokens from fleet run responses while preserving lease responses', () => {
    const parsedRun = parseFleetRunResponse(fleetRun({
      status: 'LEASING',
      verifier_gate_status: 'waiting_for_receipts',
      leased_jobs: 1,
      jobs: [
        fleetJob({
          status: 'leased',
          lease_token: 'leaked-lease-token',
          lease_expires_at: '2026-05-26T10:30:00Z',
        }),
      ],
    }));
    const parsedLease = parseNullableFleetJobResponse(fleetJob({
      status: 'leased',
      lease_token: 'immediate-lease-token',
      lease_expires_at: '2026-05-26T10:30:00Z',
    }));

    expect(parsedRun.jobs[0]?.lease_token).toBeNull();
    expect(parsedLease?.lease_token).toBe('immediate-lease-token');
  });

  it('verifies an API endpoint target using a credential reference', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(targetVerification({
        connection_id: 'cas-target-api',
        connection_state: 'CONFIGURED',
        model_status: 'READY',
        target: {
          kind: 'api_endpoint',
          provider: 'customer_gateway',
          model_id: 'customer/model-a',
          endpoint_url: 'https://models.example/v1/chat/completions',
          credential_mode: 'credential_ref',
          timeout_ms: 15000,
        },
        provenance_chip: {
          id: 'model_proof',
          name: 'Model proof',
          status: 'present',
          detail: 'Endpoint target configuration passed schema validation.',
        },
        reference_evidence_packet_trace_id: null,
      })),
    );

    const result = await verifyCasHarnessModelTarget(
      {
        target: {
          kind: 'api_endpoint',
          provider: 'customer_gateway',
          model_id: 'customer/model-a',
          endpoint_url: 'https://models.example/v1/chat/completions',
          credential_ref: 'cred_live_customer_model_a',
          timeout_ms: 15000,
        },
      },
      { baseUrl: '/api/cas-harness/audit', fetchImpl },
    );

    expect(result.connection_id).toBe('cas-target-api');
    expect(result.connection_state).toBe('CONFIGURED');
    expect(result.model_status).toBe('READY');
    expect(result.target).toEqual({
      kind: 'api_endpoint',
      provider: 'customer_gateway',
      model_id: 'customer/model-a',
      endpoint_url: 'https://models.example/v1/chat/completions',
      credential_mode: 'credential_ref',
      timeout_ms: 15000,
    });
    expect(result.provenance_chip.status).toBe('present');
    expect(result.verdict).toBeNull();
    expect(result.confidence).toBeNull();
  });

  it('gets session status with an encoded audit id', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(pendingSession({ audit_id: 'id/with spaces' })));

    const session = await getCasHarnessAuditSessionStatus('id/with spaces', {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });

    expect(session.audit_id).toBe('id/with spaces');
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('/api/cas-harness/audit/session/id%2Fwith%20spaces/status');
    expect(init).toMatchObject({
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
  });

  it('lists sessions when the backend exposes the sessions endpoint', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ sessions: [pendingSession(), pendingSession({ audit_id: 'cas-audit-two' })] }),
    );

    const result = await listCasHarnessAuditSessions({
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });

    expect(result.sessions.map((session) => session.audit_id)).toEqual([
      'cas-audit-unit',
      'cas-audit-two',
    ]);
    expect(fetchImpl.mock.calls[0][0]).toBe('/api/cas-harness/audit/sessions');
    expect(fetchImpl.mock.calls[0][1]).toMatchObject({ method: 'GET' });
  });

  it('starts a session when the backend exposes the run endpoint', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(pendingSession({ status: 'RUNNING' })));

    const result = await startCasHarnessAuditSession('cas-audit-unit', {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });

    expect(result.status).toBe('RUNNING');
    expect(fetchImpl.mock.calls[0][0]).toBe('/api/cas-harness/audit/session/cas-audit-unit/run');
    expect(fetchImpl.mock.calls[0][1]).toMatchObject({ method: 'POST' });
  });

  it('turns non-OK backend responses into useful API errors', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ detail: 'Either model_id or endpoint_url is required' }, 422),
    );

    await expect(
      createCasHarnessAuditSession(
        { prompt: 'x', selected_modules: ['verification_stack'] },
        { fetchImpl },
      ),
    ).rejects.toMatchObject({
      name: 'CasHarnessAuditApiError',
      httpStatus: 422,
      detail: 'Either model_id or endpoint_url is required',
      message: expect.stringContaining('Either model_id or endpoint_url is required'),
    });
  });

  it('preserves null verdict and confidence instead of fabricating result values', () => {
    const parsed = parseAuditSessionResponse(pendingSession({
      verdict: null,
      confidence: null,
    }));

    expect(parsed.verdict).toBeNull();
    expect(parsed.confidence).toBeNull();
  });

  it('rejects target verification responses that pretend to include a verdict or confidence', () => {
    expect(() => parseModelTargetVerificationResponse(targetVerification({
      verdict: 'ACCEPT',
      confidence: null,
    }))).toThrow(/target verification must not return a verdict/);

    expect(() => parseModelTargetVerificationResponse(targetVerification({
      verdict: null,
      confidence: 0.88,
    }))).toThrow(/target verification must not return confidence/);
  });

  it('rejects malformed scale plan responses instead of inventing worker coverage', () => {
    expect(() => parseScalePlanResponse(scalePlan({
      weight_access: 'black_box',
    }))).toThrow(/weight_access/);

    expect(() => parseScalePlanResponse(scalePlan({
      worker_assignments: [
        {
          worker_id: 'bad-worker',
          layer_start: 10,
          layer_end: 3,
          shard_id: 'bad',
          assigned_methods: ['foundation_probe'],
          expected_outputs: ['worker_evidence_manifest'],
        },
      ],
    }))).toThrow(/layer range/);
  });

  it('rejects malformed distributed audit responses', () => {
    expect(() => parseDistributedAuditResponse(distributedAudit({
      status: 'DONE',
    }))).toThrow(/distributed audit status/);

    expect(() => parseDistributedAuditResponse(distributedAudit({
      worker_evidence: [
        distributedWorker({
          worker_status: 'finished',
        }),
      ],
    }))).toThrow(/distributed worker status/);
  });

  it('rejects fleet executor responses that fake verifier readiness or final verdicts', () => {
    expect(() => parseFleetRunResponse(fleetRun({
      verifier_gate_status: 'accepted',
    }))).toThrow(/fleet verifier gate status/);

    expect(() => parseFleetRunResponse(fleetRun({
      verdict: 'ACCEPT',
    }))).toThrow(/must not return ACCEPT\/SUPPRESS/);

    expect(() => parseFleetRunResponse(fleetRun({
      confidence: 0.91,
    }))).toThrow(/fleet executor confidence must be null/);

    expect(() => parseFleetRunResponse(fleetRun({
      jobs: [
        fleetJob({
          status: 'completed',
          produced_outputs: ['layer_activation_summary', 'worker_evidence_manifest'],
          evidence_packet_fragment_ref: null,
        }),
      ],
      completed_fragments: 1,
    }))).toThrow(/completed fleet job requires evidence_packet_fragment_ref/);

    expect(() => parseFleetRunResponse(fleetRun({
      verifier_gate_status: 'ready_for_verifier',
      jobs: [fleetJob()],
    }))).toThrow(/ready_for_verifier requires every job to be completed/);

    expect(() => parseFleetRunResponse(fleetRun({
      verifier_gate_status: 'ready_for_verifier',
      completed_fragments: 1,
      jobs: [
        fleetJob({
          status: 'completed',
          produced_outputs: ['layer_activation_summary'],
          missing_outputs: ['worker_evidence_manifest'],
          evidence_packet_fragment_ref:
            'cas-fragment://cas-dist-unit/fleet-job-01/probe-worker-01/layers-000-009/sha256:0000000000000000000000000000000000000000000000000000000000000000',
        }),
      ],
    }))).toThrow(/ready_for_verifier cannot include missing job outputs/);
  });

  it('parses fleet verifier decisions separately from fleet executor state', () => {
    const parsed = parseFleetVerifierDecisionResponse(fleetVerifierDecision({
      proof_chip_gate: 'unavailable',
      confidence: null,
    }));

    expect(parsed).toEqual({
      audit_id: 'cas-dist-unit',
      merged_packet_trace_id: 'cas-dist-unit-fleet-merge',
      verdict: 'FLAG_FOR_HUMAN_REVIEW',
      confidence: null,
      source: 'fleet_packet_verifier',
      reason:
        'Fleet receipts are merged, but ACCEPT/SUPPRESS requires an explicit verifier decision over the merged Evidence Packet.',
      decision_scope: 'distributed_fleet_merged_packet',
      coverage: {
        basis: 'fleet_worker_fragments',
        total_jobs: 1,
        completed_fragments: 1,
        failed_jobs: 0,
        missing_output_jobs: 0,
        distributed_merge_status: 'complete',
      },
      proof_chip_gate: 'unavailable',
      blockers: [
        'Merged distributed packet has worker receipts but no explicit proof-chip verifier decision.',
      ],
      next_actions: [
        'Attach Stage 19/20/21 verifier output or packet-level explicit_verifier_decision.',
        'Keep the public verdict at FLAG FOR HUMAN REVIEW until proof chips pass.',
      ],
      created_at: '2026-05-26T10:05:00Z',
    });
    expect(() =>
      parseFleetVerifierDecisionResponse(fleetVerifierDecision({
        proof_chip_gate: 'pretend_passed',
      })),
    ).toThrow(/proof-chip gate/);
  });

  it('parses distributed worker receipt packet refs, missing outputs, and statuses explicitly', () => {
    const parsed = parseDistributedAuditResponse(distributedAudit({
      status: 'MERGE_PENDING',
      merge_status: 'partial',
      worker_evidence: [
        distributedWorker({
          worker_status: 'completed',
          produced_outputs: ['layer_activation_summary'],
          missing_outputs: ['worker_evidence_manifest'],
          evidence_packet_ref: 'packet://probe-worker-01',
        }),
      ],
      ready_workers: 1,
      missing_outputs: ['probe-worker-01:worker_evidence_manifest'],
    }));

    expect(parsed.status).toBe('MERGE_PENDING');
    expect(parsed.merge_status).toBe('partial');
    expect(parsed.verdict).toBeNull();
    expect(parsed.confidence).toBeNull();
    expect(parsed.worker_evidence[0]).toMatchObject({
      worker_status: 'completed',
      produced_outputs: ['layer_activation_summary'],
      missing_outputs: ['worker_evidence_manifest'],
      evidence_packet_ref: 'packet://probe-worker-01',
    });
    expect(parsed.missing_outputs).toEqual(['probe-worker-01:worker_evidence_manifest']);
  });

  it('rejects distributed merge ACCEPT/SUPPRESS and confidence without verifier output', () => {
    expect(() => parseDistributedAuditResponse(distributedAudit({
      verdict: 'ACCEPT',
    }))).toThrow(/must not return ACCEPT\/SUPPRESS/);

    expect(() => parseDistributedAuditResponse(distributedAudit({
      verdict: 'SUPPRESS',
    }))).toThrow(/must not return ACCEPT\/SUPPRESS/);

    expect(() => parseDistributedAuditResponse(distributedAudit({
      confidence: 0.91,
    }))).toThrow(/distributed merge confidence must be null/);
  });

  it('rejects completed worker receipts without packet refs', () => {
    expect(() => parseDistributedAuditResponse(distributedAudit({
      worker_evidence: [
        distributedWorker({
          worker_status: 'completed',
          produced_outputs: ['layer_activation_summary'],
          evidence_packet_ref: null,
        }),
      ],
      ready_workers: 1,
    }))).toThrow(/completed distributed worker evidence requires evidence_packet_ref/);
  });

  it('rejects impossible distributed worker output receipt accounting', () => {
    expect(() => parseDistributedAuditResponse(distributedAudit({
      worker_evidence: [
        distributedWorker({
          produced_outputs: ['unregistered_output'],
        }),
      ],
    }))).toThrow(/produced unknown output/);

    expect(() => parseDistributedAuditResponse(distributedAudit({
      worker_evidence: [
        distributedWorker({
          produced_outputs: ['layer_activation_summary'],
          missing_outputs: ['layer_activation_summary'],
        }),
      ],
    }))).toThrow(/both produced and missing/);
  });

  it('rejects complete distributed merges before every worker receipt is completed', () => {
    expect(() => parseDistributedAuditResponse(distributedAudit({
      status: 'COMPLETE',
      merge_status: 'complete',
      verdict: 'FLAG_FOR_HUMAN_REVIEW',
    }))).toThrow(/complete distributed merge requires every worker receipt to be completed/);

    expect(() => parseDistributedAuditResponse(distributedAudit({
      status: 'COMPLETE',
      merge_status: 'complete',
      verdict: 'FLAG_FOR_HUMAN_REVIEW',
      worker_evidence: [
        distributedWorker({
          worker_status: 'completed',
          produced_outputs: ['layer_activation_summary'],
          missing_outputs: ['worker_evidence_manifest'],
          evidence_packet_ref: 'packet://probe-worker-01',
        }),
      ],
      ready_workers: 1,
      missing_outputs: ['probe-worker-01:worker_evidence_manifest'],
    }))).toThrow(/complete distributed merge cannot include missing worker outputs/);
  });

  it('rejects malformed target verification payloads', () => {
    expect(() => parseModelTargetVerificationResponse(targetVerification({
      target: {
        kind: 'api_endpoint',
        provider: 'customer_gateway',
        model_id: 'customer/model-a',
        endpoint_url: 'https://models.example/v1/chat/completions',
        credential_mode: 'raw_key_echoed',
        timeout_ms: 15000,
      },
    }))).toThrow(/Unsupported CAS Harness credential mode/);

    expect(() => parseModelTargetVerificationResponse(targetVerification({
      can_run_audit: 'yes',
    }))).toThrow(/can_run_audit must be boolean/);
  });

  it('treats missing verdict and confidence as null, not as ACCEPT or zero', () => {
    const raw = pendingSession();
    delete raw.verdict;
    delete raw.confidence;

    const parsed = parseAuditSessionResponse(raw);

    expect(parsed.verdict).toBeNull();
    expect(parsed.confidence).toBeNull();
  });

  it('validates known session status vocabulary', () => {
    expect(parseAuditSessionResponse(pendingSession({ status: 'COMPLETE' })).status).toBe('COMPLETE');
    expect(parseAuditSessionResponse(pendingSession({ status: 'EVIDENCE_PENDING' })).status).toBe('EVIDENCE_PENDING');
    expect(() => parseAuditSessionResponse(pendingSession({ status: 'DONE_ENOUGH' }))).toThrow(
      /Unsupported CAS Harness audit status/,
    );
  });

  it('validates known verdict vocabulary and rejects unknown verdicts', () => {
    expect(parseAuditSessionResponse(pendingSession({
      status: 'COMPLETE',
      verdict: 'FLAG_FOR_HUMAN_REVIEW',
      confidence: 0.77,
    })).verdict).toBe('FLAG_FOR_HUMAN_REVIEW');
    expect(() => parseAuditSessionResponse(pendingSession({
      verdict: 'ALLOW',
      confidence: 0.9,
    }))).toThrow(/Unsupported CAS Harness audit verdict/);
  });

  it('parses explicit verifier decision reason and source for UI explanation', () => {
    const parsed = parseAuditSessionResponse(pendingSession({
      status: 'COMPLETE',
      verdict: 'ACCEPT',
      confidence: 0.9816,
      verifier_decision: {
        verdict: 'ACCEPT',
        confidence: 0.9816,
        source: 'stage19_verification_stack+stage20_generation_readiness',
        reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
        decision_scope: 'stage9_40e_validation_packet',
        coverage: {
          basis: 'stage9_40e_validation_cases',
          case_count: 80,
          class_count: 40,
        },
      },
    }));

    expect(parsed.verifier_decision).toEqual({
      verdict: 'ACCEPT',
      confidence: 0.9816,
      source: 'stage19_verification_stack+stage20_generation_readiness',
      reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
      decisionScope: 'stage9_40e_validation_packet',
      coverage: {
        basis: 'stage9_40e_validation_cases',
        caseCount: 80,
        classCount: 40,
      },
    });
  });

  it('rejects malformed verifier decision instead of inventing explanation text', () => {
    expect(() => parseAuditSessionResponse(pendingSession({
      verifier_decision: {
        verdict: 'ACCEPT',
        confidence: null,
        source: 'stage19',
        reason: 'missing confidence',
      },
    }))).toThrow(/verifier decision confidence is required/);
  });

  it('rejects invalid confidence instead of coercing it', () => {
    expect(() => parseAuditSessionResponse(pendingSession({ confidence: '0.9' }))).toThrow(
      /confidence must be null or a number/,
    );
    expect(() => parseAuditSessionResponse(pendingSession({ confidence: 1.5 }))).toThrow(
      /confidence must be null or a number/,
    );
  });

  it('derives the audit API URL from the Atlas API env var used by hosted builds', () => {
    vi.stubEnv('VITE_ATLAS_API_BASE_URL', 'https://noetic-compass-api.onrender.com/atlas');

    expect(resolveCasHarnessAuditBaseUrl()).toBe(
      'https://noetic-compass-api.onrender.com/api/cas-harness/audit',
    );
  });

  it('uses the derived hosted audit API URL for target verification', async () => {
    vi.stubEnv('VITE_ATLAS_API_BASE_URL', 'https://noetic-compass-api.onrender.com/atlas');
    const fetchImpl = vi.fn(async () => jsonResponse(targetVerification()));

    await verifyCasHarnessModelTarget(
      { target: { kind: 'demo_reference' } },
      { fetchImpl },
    );

    expect(fetchImpl.mock.calls[0][0]).toBe(
      'https://noetic-compass-api.onrender.com/api/cas-harness/audit/target/verify',
    );
  });

  it('does not call fetch for empty audit ids', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(pendingSession()));

    await expect(
      getCasHarnessAuditSessionStatus('  ', { fetchImpl }),
    ).rejects.toBeInstanceOf(CasHarnessAuditApiError);
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});
