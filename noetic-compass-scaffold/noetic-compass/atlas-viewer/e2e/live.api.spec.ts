import { expect, test, type APIRequestContext } from '@playwright/test';

const DEFAULT_ATLAS_API_BASE_URL = 'https://cas-harness-customer-api.onrender.com/atlas';
const REALMODE_PASS = 'REAL_PYTHIA_WEIGHTS_LOADED';

interface RealModeProof {
  verdict?: string;
  is_real_model?: boolean;
  fake_runtime_env?: boolean;
  model_loaded?: boolean;
  load_error?: string | null;
  manifest_is_real_model?: boolean;
  model_id?: string;
  worker_version?: string;
}

interface SseEvent {
  event: string;
  data: Record<string, unknown>;
}

function atlasApiBaseUrl(): string {
  return (
    process.env.ATLAS_LIVE_API_BASE_URL ?? DEFAULT_ATLAS_API_BASE_URL
  ).replace(/\/$/, '');
}

function resolveStreamUrl(streamUrl: string, apiBaseUrl: string): string {
  if (/^https?:\/\//i.test(streamUrl)) return streamUrl;
  const origin = new URL(apiBaseUrl).origin;
  if (streamUrl.startsWith('/')) return `${origin}${streamUrl}`;
  return `${apiBaseUrl}/${streamUrl}`;
}

function parseSseEvents(body: string): SseEvent[] {
  return body
    .split(/\r?\n\r?\n/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      const lines = block.split(/\r?\n/);
      const eventLine = lines.find((line) => line.startsWith('event: '));
      const dataLines = lines
        .filter((line) => line.startsWith('data: '))
        .map((line) => line.slice('data: '.length));
      return {
        event: eventLine ? eventLine.slice('event: '.length) : 'message',
        data: JSON.parse(dataLines.join('\n')) as Record<string, unknown>,
      };
    });
}

async function expectRealModeProof(request: APIRequestContext) {
  const baseUrl = atlasApiBaseUrl();
  const response = await request.get(`${baseUrl}/live/health/realmode`, {
    headers: { Accept: 'application/json' },
    timeout: 60_000,
  });
  const proofText = await response.text();
  expect(response.status(), proofText).toBe(200);

  const proof = JSON.parse(proofText) as RealModeProof;
  expect(proof).toMatchObject({
    verdict: REALMODE_PASS,
    is_real_model: true,
    fake_runtime_env: false,
    model_loaded: true,
    load_error: null,
    manifest_is_real_model: true,
  });
  return proof;
}

test.describe('Atlas LIVE deployed API contract', () => {
  test.skip(
    process.env.ATLAS_LIVE_E2E !== '1',
    'Set ATLAS_LIVE_E2E=1 to run deployed Atlas LIVE checks.',
  );

  test('realmode health proves actual Pythia weights before any LIVE claim', async ({
    request,
  }) => {
    const proof = await expectRealModeProof(request);
    expect(proof.model_id).toBe('EleutherAI/pythia-160m');
    expect(proof.worker_version).toBeTruthy();
  });

  test('LIVE session stream emits a real-model manifest and token events', async ({
    request,
  }) => {
    test.skip(
      !process.env.ATLAS_LIVE_INVITE_CODE,
      'Set ATLAS_LIVE_INVITE_CODE to prove the gated LIVE stream.',
    );

    const baseUrl = atlasApiBaseUrl();
    await expectRealModeProof(request);

    const sessionResponse = await request.post(`${baseUrl}/live/session`, {
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Atlas-Invite-Code': process.env.ATLAS_LIVE_INVITE_CODE!,
      },
      data: {
        prompt: 'Agent A live stream verification: emit three short tokens.',
        model_id: 'EleutherAI/pythia-160m',
        max_new_tokens: 3,
        temperature: 0,
        seed: 25,
        probes: [
          'active_trace',
          'blindspot_covers',
          'mode7_attribution',
          'confidence_margin',
        ],
        method_config: {
          enabled_methods: [
            'foundation_probe',
            'rpm_gate_check',
            'blindspot_detection',
            'verification_stack',
          ],
          knobs: {
            foundation_probe: { layer_range: ['2'], top_k: 3 },
            rpm_gate_check: { strictness_threshold: 0.7 },
          },
        },
      },
      timeout: 60_000,
    });
    const sessionText = await sessionResponse.text();
    expect(sessionResponse.status(), sessionText).toBe(200);

    const session = JSON.parse(sessionText) as {
      model_id: string;
      stream_url: string;
      stream_token: string;
    };
    expect(session.model_id).toBe('EleutherAI/pythia-160m');
    expect(session.stream_token).toBeTruthy();

    const streamResponse = await request.get(
      resolveStreamUrl(session.stream_url, baseUrl),
      { headers: { Accept: 'text/event-stream' }, timeout: 90_000 },
    );
    const streamText = await streamResponse.text();
    expect(streamResponse.status(), streamText).toBe(200);

    const events = parseSseEvents(streamText);
    expect(events[0]?.event).toBe('manifest');

    const manifest = events.find((event) => event.event === 'manifest')?.data as
      | { manifest?: { is_real_model?: boolean; model_id?: string } }
      | undefined;
    expect(manifest?.manifest).toMatchObject({
      is_real_model: true,
      model_id: 'EleutherAI/pythia-160m',
    });

    const tokenEvents = events.filter((event) => event.event === 'token');
    expect(tokenEvents.length).toBeGreaterThan(0);
    expect(tokenEvents[0]?.data).toMatchObject({
      type: 'token',
      token_index: 0,
    });
    expect(events.some((event) => event.event === 'complete')).toBe(true);
  });
});
