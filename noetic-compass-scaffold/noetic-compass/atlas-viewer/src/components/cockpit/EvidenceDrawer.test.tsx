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

  it('derives the Evidence Packet host from VITE_ATLAS_API_BASE_URL in hosted builds', async () => {
    vi.stubEnv('VITE_ATLAS_API_BASE_URL', 'https://noetic-compass-api.onrender.com/atlas');
    const fetchImpl = vi.fn(async () => jsonResponse(packet));
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'primitive',
          title: 'Hosted packet',
          evidence_ref: { trace_id: 'trace-hosted', row_id: 'row-hosted' },
        }}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByTestId('evidence-packet-loaded')).toHaveTextContent(
      'evidence_packet.v1',
    );

    const [url] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('https://noetic-compass-api.onrender.com/evidence/trace-hosted');
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

  it('renders constituent tokens for a word-scoped payload', () => {
    const fetchImpl = vi.fn();
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'word',
          title: '"wound." (tokens 5-6)',
          evidence_ref: {
            word: 'wound.',
            token_indices: [5, 6],
            char_range: [30, 36],
          },
          detail: {
            tokens: [
              {
                token_index: 5,
                token: ' wound',
                top_activated_neurons: [
                  { layer: 4, index: 12, activation: 0.8 },
                  { layer: 3, index: 7, activation: 0.6 },
                ],
                mode7_attribution: [
                  { from_token_index: 1, to_token_index: 5, weight: 0.7 },
                ],
                confidence: 0.91,
              },
              {
                token_index: 6,
                token: '.',
                top_activated_neurons: [],
                mode7_attribution: [
                  { from_token_index: 5, to_token_index: 6, weight: 0.4 },
                  // Duplicate of the from-token's edge, will be deduped at
                  // the union level when from/to match.
                  { from_token_index: 1, to_token_index: 5, weight: 0.7 },
                ],
                confidence: 0.85,
              },
            ],
          },
        }}
        onClose={() => {}}
      />,
    );

    expect(
      screen.getByTestId('evidence-drawer-word-token-row-5'),
    ).toHaveTextContent('5');
    expect(
      screen.getByTestId('evidence-drawer-word-token-row-5'),
    ).toHaveTextContent('L4N12');
    expect(
      screen.getByTestId('evidence-drawer-word-token-row-6'),
    ).toHaveTextContent('6');

    // Mode 7 edges deduped: 1→5 appears only once; 5→6 appears once.
    const ul = screen.getByTestId('evidence-drawer-word-mode7');
    const items = ul.querySelectorAll('li');
    expect(items).toHaveLength(2);

    // No packet fetch because no trace_id provided.
    expect(fetchImpl).not.toHaveBeenCalled();
    // Local-fallback label preserved (PR #45/#46 contract).
    expect(screen.getByTestId('evidence-drawer-source-label')).toHaveTextContent(
      'Word click reference',
    );
    expect(screen.getByTestId('evidence-drawer-source-note')).toHaveTextContent(
      'Local replay metadata only',
    );
  });

  it('fetches the Evidence Packet for a word when any constituent token carries trace_id', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(packet));
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'word',
          title: '"hello" (token 4)',
          evidence_ref: { word: 'hello', token_indices: [4], char_range: [0, 5] },
          detail: {
            tokens: [
              {
                token_index: 4,
                token: 'hello',
                top_activated_neurons: [],
                mode7_attribution: [],
                confidence: 0.77,
                trace_id: 'trace-123',
              },
            ],
          },
        }}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByTestId('evidence-packet-loaded')).toHaveTextContent(
      'evidence_packet.v1',
    );
    expect(fetchImpl).toHaveBeenCalledOnce();
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
