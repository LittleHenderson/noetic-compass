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

function packetWithHashes(hashes: Record<string, unknown>): Record<string, unknown> {
  return {
    ...packet,
    hashes: {
      ...packet.hashes,
      ...hashes,
    },
  };
}

const s3VerifyResponse = {
  overall: 'all_match',
  checks: [
    {
      artifact: 'merged_packet_external_anchor',
      expected: '99999999998888888888777777777766666666665555555555bbbbbbbb',
      actual: '99999999998888888888777777777766666666665555555555bbbbbbbb',
      match: true,
      notes:
        'S3 anchor object was re-read and its manifest commits to this packet hash and hash-log entry',
    },
  ],
};

const s3ObjectLockVerifyResponse = {
  overall: 'all_match',
  checks: [
    {
      artifact: 'merged_packet_external_anchor',
      expected: 'aaaaaaaaaabbbbbbbbbbccccccccccddddddddddeeeeeeeeee11111111',
      actual: 'aaaaaaaaaabbbbbbbbbbccccccccccddddddddddeeeeeeeeee11111111',
      match: true,
      notes:
        'S3 anchor object was re-read, its manifest commits to this packet hash and hash-log entry, and Object Lock GOVERNANCE retention is active until 2026-06-28T00:00:00+00:00',
    },
  ],
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

    expect(fetchImpl).toHaveBeenCalledTimes(2);
    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/evidence/trace-123');
    expect(init.method).toBe('GET');
    expect(init.headers).toMatchObject({ Accept: 'application/json' });
    const [verifyUrl, verifyInit] = fetchImpl.mock.calls[1] as [string, RequestInit];
    expect(verifyUrl).toBe('/api/evidence/trace-123/verify');
    expect(verifyInit.method).toBe('POST');
  });

  it('surfaces S3 anchor proof from the packet hashes block', async () => {
    const anchoredPacket = packetWithHashes({
      packet_without_hashes_sha256:
        'aaaaaaaaaabbbbbbbbbbccccccccccddddddddddeeeeeeeeee11111111',
      hash_log_entry_sha256:
        '11111111112222222222333333333344444444445555555555aaaaaaaa',
      external_anchor: {
        status: 'anchored',
        mode: 's3',
        anchor_uri: 's3://cas-evidence-anchor/audit-1/hash-log.json',
        manifest_sha256:
          '99999999998888888888777777777766666666665555555555bbbbbbbb',
      },
    });
    const fetchImpl = vi.fn(async (_url: string, init?: RequestInit) =>
      jsonResponse(init?.method === 'POST' ? s3VerifyResponse : anchoredPacket),
    );
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'primitive',
          title: 'Anchored packet',
          evidence_ref: { trace_id: 'trace-123' },
        }}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByTestId('evidence-packet-anchor-status')).toHaveTextContent(
      'S3 object verified',
    );
    expect(screen.getByTestId('evidence-packet-anchor-detail')).toHaveTextContent(
      'verifier re-read the S3 anchor object',
    );
    expect(screen.getByTestId('evidence-packet-anchor-uri')).toHaveTextContent(
      's3://cas-evidence-anchor/audit-1/hash-log.json',
    );
    expect(screen.getByTestId('evidence-packet-anchor-hash-log')).toHaveTextContent(
      '1111111111...aaaaaaaa',
    );
    expect(screen.getByTestId('evidence-packet-anchor-packet-hash')).toHaveTextContent(
      'aaaaaaaaaa...11111111',
    );
  });

  it('surfaces WORM-retained Object Lock proof only when /verify confirms retention', async () => {
    const anchoredPacket = packetWithHashes({
      packet_without_hashes_sha256:
        'aaaaaaaaaabbbbbbbbbbccccccccccddddddddddeeeeeeeeee11111111',
      hash_log_entry_sha256:
        '11111111112222222222333333333344444444445555555555aaaaaaaa',
      external_anchor: {
        status: 'anchored',
        mode: 's3',
        anchor_uri: 's3://cas-evidence-anchor/audit-1/hash-log.json',
        manifest_sha256:
          '99999999998888888888777777777766666666665555555555bbbbbbbb',
        object_lock_mode: 'GOVERNANCE',
        object_lock_retain_until: '2026-06-28T00:00:00+00:00',
        retention_days: 30,
      },
    });
    const fetchImpl = vi.fn(async (_url: string, init?: RequestInit) =>
      jsonResponse(init?.method === 'POST' ? s3ObjectLockVerifyResponse : anchoredPacket),
    );
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'primitive',
          title: 'WORM packet',
          evidence_ref: { trace_id: 'trace-123' },
        }}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByTestId('evidence-packet-anchor-status')).toHaveTextContent(
      'WORM retained',
    );
    expect(screen.getByTestId('evidence-packet-anchor-detail')).toHaveTextContent(
      'confirmed active Object Lock retention',
    );
    expect(screen.getByTestId('evidence-packet-anchor-object-lock')).toHaveTextContent(
      'object lock: GOVERNANCE / 30d',
    );
    expect(screen.getByTestId('evidence-packet-anchor-retain-until')).toHaveTextContent(
      '2026-06-28T00:00:00+00:00',
    );
  });

  it('surfaces local anchor proof without claiming S3 durability', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(
        packetWithHashes({
          hash_log_entry_sha256:
            'abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd',
          external_anchor: {
            status: 'anchored',
            mode: 'local',
            anchor_uri: 'file:///var/lib/noetic/evidence-anchor/local.jsonl',
            manifest_sha256:
              '123456789012345678901234567890123456789012345678901234567890abcd',
          },
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'primitive',
          title: 'Local anchor packet',
          evidence_ref: { trace_id: 'trace-123' },
        }}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByTestId('evidence-packet-anchor-status')).toHaveTextContent(
      'Anchored locally',
    );
    expect(screen.getByTestId('evidence-packet-anchor-detail')).toHaveTextContent(
      'local anchor manifest',
    );
    expect(screen.getByTestId('evidence-packet-anchor-mode')).toHaveTextContent('local');
  });

  it('marks disabled external anchoring as a warning state', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(
        packetWithHashes({
          hash_log_entry_sha256:
            'fedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbaabcd',
          external_anchor: {
            status: 'disabled',
            mode: 'disabled',
            reason: 'CAS_HARNESS_EVIDENCE_ANCHOR_MODE=disabled',
          },
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'primitive',
          title: 'Disabled anchor packet',
          evidence_ref: { trace_id: 'trace-123' },
        }}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByTestId('evidence-packet-anchor-status')).toHaveTextContent(
      'Anchor disabled',
    );
    expect(screen.getByTestId('evidence-packet-anchor-detail')).toHaveTextContent(
      'external anchoring is disabled',
    );
    expect(screen.getByTestId('evidence-packet-anchor-hash-log')).toHaveTextContent(
      'fedcbafedc...dcbaabcd',
    );
  });

  it('marks failed external anchoring without hiding the local hash log', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(
        packetWithHashes({
          hash_log_entry_sha256:
            '012345678901234567890123456789012345678901234567890123456789abcd',
          external_anchor: {
            status: 'failed',
            mode: 's3',
            reason: 'S3 write denied',
          },
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'primitive',
          title: 'Failed anchor packet',
          evidence_ref: { trace_id: 'trace-123' },
        }}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByTestId('evidence-packet-anchor-status')).toHaveTextContent(
      'Anchor failed',
    );
    expect(screen.getByTestId('evidence-packet-anchor-detail')).toHaveTextContent(
      'locally hash-logged',
    );
    expect(screen.getByTestId('evidence-packet-anchor-hash-log')).toHaveTextContent(
      '0123456789...6789abcd',
    );
  });

  it('does not invent anchor proof for legacy packets', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(packet));
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'primitive',
          title: 'Legacy packet',
          evidence_ref: { trace_id: 'trace-123' },
        }}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByTestId('evidence-packet-anchor-status')).toHaveTextContent(
      'No external anchor proof',
    );
    expect(screen.getByTestId('evidence-packet-anchor-detail')).toHaveTextContent(
      'does not declare an external hash-log anchor',
    );
  });

  it('derives the Evidence Packet host from VITE_ATLAS_API_BASE_URL in hosted builds', async () => {
    vi.stubEnv('VITE_ATLAS_API_BASE_URL', 'https://api.noeticcompass.com/atlas');
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
    expect(url).toBe('https://api.noeticcompass.com/evidence/trace-hosted');
    const [verifyUrl] = fetchImpl.mock.calls[1] as [string, RequestInit];
    expect(verifyUrl).toBe('https://api.noeticcompass.com/evidence/trace-hosted/verify');
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
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it('renders BlindspotInterpretation rows when the payload carries blindspotInterpretations', () => {
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
          },
          blindspotInterpretations: [
            {
              driveId: 'F5',
              register: 'A',
              confidence: 0.72,
              evidenceSources: ['neuron-cover overlap', 'ablation support'],
            },
          ],
        }}
        onClose={() => {}}
      />,
    );

    expect(screen.getByTestId('evidence-drawer-blindspots')).toBeTruthy();
    expect(screen.getByTestId('blindspot-headline').textContent).toBe(
      'The model may be overlooking whether someone has real choice, permission, responsibility, or control.',
    );
    expect(screen.getByTestId('blindspot-cas-source').textContent).toBe(
      'CAS source: F5 Agency · analytical register',
    );
    expect(screen.getByTestId('blindspot-confidence').textContent).toBe(
      'Confidence: 72% medium',
    );
    expect(screen.getByTestId('blindspot-evidence').textContent).toBe(
      'Evidence: neuron-cover overlap + ablation support',
    );
  });

  it('omits the blindspot section when no interpretations are provided', () => {
    const fetchImpl = vi.fn();
    vi.stubGlobal('fetch', fetchImpl);

    render(
      <EvidenceDrawer
        open={true}
        payload={{
          source: 'neuron',
          title: 'L9N42',
          evidence_ref: { neuron_coordinate: 'L9N42' },
        }}
        onClose={() => {}}
      />,
    );

    expect(screen.queryByTestId('evidence-drawer-blindspots')).toBeNull();
    expect(screen.queryByTestId('blindspot-interpretation')).toBeNull();
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
