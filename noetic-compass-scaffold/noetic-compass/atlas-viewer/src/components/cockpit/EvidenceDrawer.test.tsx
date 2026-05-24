import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import EvidenceDrawer from './EvidenceDrawer';

function jsonResponse(body: unknown, init: { status?: number } = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

const packet = {
  schema_version: 'evidence_packet.v1',
  trace_id: 'trace-123',
  generated_at: '2026-05-23T10:00:00Z',
  input: {
    text: 'What does ^3^P|A mean?',
    user_id: 'unit-user',
    session_id: 'unit-session',
  },
  cas_expression: {
    text: '^3^P|A',
    compiler_valid: true,
    grammar_category: 'state_literal',
  },
  output: {
    text: '^3^P|A is a principled aversion state.',
    n_tokens: 9,
    max_new_tokens: 64,
  },
  copy_slot_trace: [
    {
      role: 'register',
      name: 'A',
      copied: true,
      source_token_index: 2,
      target_token_index: 5,
      claim_level: 'source_copy_evidence',
    },
  ],
  provenance: {
    model_checkpoint_id: 'ckpt-unit',
    checkpoint_label: 'unit checkpoint',
    code_commit_sha: 'abc123',
    run_command: 'python run.py',
    config_snapshot: { fixture: true },
  },
  hashes: {
    weights_sha: 'w-sha',
    tokenizer_hash: 'tok-sha',
    english_bpe_hash: null,
    corpus_sha256: 'corpus-sha',
    on_disk_paths: { weights_path: '/tmp/model.pt' },
  },
  claim_levels: [
    {
      claim: 'The expression is compiler-valid.',
      level: 'cas_hard_trace',
      support_status: 'supported',
      rationale: 'Compiler accepted the expression.',
    },
  ],
  caveats: ['Unit fixture packet.'],
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('EvidenceDrawer', () => {
  it('fetches and renders a packet when the payload carries trace_id', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(packet));
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'primitive',
          title: 'Primitive A',
          evidence_ref: { trace_id: 'trace-123', row_id: 'row-a' },
        }}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByTestId('evidence-packet-loaded')).toHaveTextContent(
      'evidence_packet.v1',
    );
    expect(screen.getByTestId('evidence-packet-input')).toHaveTextContent(
      'What does ^3^P|A mean?',
    );
    expect(screen.getByTestId('evidence-packet-cas')).toHaveTextContent('^3^P|A');
    expect(screen.getByTestId('evidence-packet-output')).toHaveTextContent(
      'principled aversion',
    );
    expect(screen.getByTestId('evidence-packet-provenance')).toHaveTextContent(
      'ckpt-unit',
    );
    expect(screen.getByTestId('evidence-packet-hashes')).toHaveTextContent('w-sha');
    expect(screen.getByTestId('evidence-packet-claim-levels')).toHaveTextContent(
      'cas_hard_trace',
    );

    expect(fetchImpl).toHaveBeenCalledOnce();
    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/evidence/trace-123');
    expect(init.method).toBe('GET');
    expect(init.headers).toMatchObject({ Accept: 'application/json' });
  });

  it('labels neuron refs as local replay metadata when no trace_id is supplied', () => {
    const fetchImpl = vi.fn();
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'neuron',
          title: 'L3N142',
          evidence_ref: {
            neuron_coordinate: 'L3N142',
            layer: 3,
            neuron_index: 142,
            token_index: 4,
          },
          detail: { token: ' patient', architecture: 'pythia' },
        }}
        onClose={() => {}}
      />,
    );

    expect(screen.getByTestId('evidence-drawer-source-label')).toHaveTextContent(
      'Neuron click reference',
    );
    expect(screen.getByTestId('evidence-drawer-source-note')).toHaveTextContent(
      'not presenting this as a verified Evidence Packet',
    );
    expect(screen.getByTestId('evidence-drawer-ref-json')).toHaveTextContent('L3N142');
    expect(screen.getByTestId('evidence-drawer-detail-json')).toHaveTextContent(
      'pythia',
    );
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('falls back to the local reference when packet fetch fails', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ detail: 'trace_id not found' }, { status: 404 }),
    );
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'primitive',
          title: 'Missing packet',
          evidence_ref: { trace_id: 'missing-trace', row_id: 'row-x' },
        }}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByTestId('evidence-drawer-error')).toHaveTextContent(
      'trace_id not found',
    );
    expect(screen.getByTestId('evidence-drawer-source-note')).toHaveTextContent(
      'showing only the local reference metadata',
    );
    expect(screen.getByTestId('evidence-drawer-ref-json')).toHaveTextContent(
      'missing-trace',
    );
  });
});
