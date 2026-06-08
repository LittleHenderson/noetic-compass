const TOKEN_STORAGE_KEY = 'atlasViewerAuthToken';

export interface ExplainerChatResponse {
  answer: string;
  sources: string[];
  used_gemini: boolean;
  model: string;
  safety_mode: string;
}

/**
 * One cited segment of a packet explanation. `refs` are EP field keys (e.g.
 * "verdict", "proof_chips.causal_proof.status", "anchor.status", "blind_spots.0")
 * that the UI renders as clickable chips scrolling to the matching EP field.
 * Per spec §6, a segment with zero refs is an uncited claim and MUST NOT render.
 */
export interface ExplainPacketSegment {
  text: string;
  refs: string[];
}

/**
 * Output contract for the "Explain this packet" AI reading aid (spec §7).
 *
 * `verdict_echo` is the literal verdict the model was given; the UI MUST assert
 * `verdict_echo === EP.verdict` and, on mismatch, discard this output and show
 * only the raw EP verdict (fail-closed — never the inflated reading).
 */
export interface ExplainPacketResponse {
  trace_id: string;
  verdict_echo: string;
  segments: ExplainPacketSegment[];
  investigate_next: ExplainPacketSegment[];
  used_gemini: boolean;
  model: string;
  safety_mode: 'packet_projection_only';
  disclaimer: string;
}

async function ensureAuthToken(): Promise<string> {
  const existing = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
  if (existing) return existing;

  const response = await fetch('/api/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'atlas-explainer-user' }),
  });
  if (!response.ok) {
    throw new Error(`Unable to mint explainer session (${response.status})`);
  }
  const payload = (await response.json()) as { token?: string };
  if (!payload.token) {
    throw new Error('Explainer session response did not include a token.');
  }
  window.sessionStorage.setItem(TOKEN_STORAGE_KEY, payload.token);
  return payload.token;
}

export async function askExplainer(question: string): Promise<ExplainerChatResponse> {
  const token = await ensureAuthToken();
  const response = await fetch('/api/explainer/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Explainer request failed (${response.status})`);
  }
  return (await response.json()) as ExplainerChatResponse;
}

/**
 * Ask the AI explainer for a plain-English, cited reading of one Evidence Packet
 * (spec §7–§9). Reuses the same session-token mint + Bearer auth as the free
 * Guide chat. The backend resolves the EP only if the caller's tenant owns the
 * trace (G3) and returns a redacted, allow-list-only projection — this client
 * never sees CAS scoring internals or probe methodology.
 *
 * The caller is responsible for asserting `verdict_echo === EP.verdict` and
 * failing closed (raw EP verdict only) on mismatch.
 */
export async function askExplainerForPacket(
  traceId: string,
): Promise<ExplainPacketResponse> {
  const trimmed = traceId.trim();
  if (!trimmed) {
    throw new Error('A packet trace_id is required to explain a packet.');
  }
  const token = await ensureAuthToken();
  const response = await fetch(
    `/api/explainer/evidence/${encodeURIComponent(trimmed)}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      message || `Packet explainer request failed (${response.status})`,
    );
  }
  return (await response.json()) as ExplainPacketResponse;
}
