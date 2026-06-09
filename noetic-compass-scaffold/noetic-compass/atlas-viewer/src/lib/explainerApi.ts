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

export interface ExplainerApiOptions {
  authToken?: string | null;
  fetchImpl?: typeof fetch;
}

export async function askExplainer(
  question: string,
  options?: ExplainerApiOptions,
): Promise<ExplainerChatResponse> {
  const fetchImpl = fetchForExplainer(options);
  const response = await fetchImpl('/api/explainer/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: requiredAuthorizationHeader(options?.authToken),
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
 * (spec §7–§9). Reuses the same account-mode Bearer auth as the free Guide
 * chat. The backend resolves the EP only if the caller's tenant owns the
 * trace (G3) and returns a redacted, allow-list-only projection — this client
 * never sees CAS scoring internals or probe methodology.
 *
 * The caller is responsible for asserting `verdict_echo === EP.verdict` and
 * failing closed (raw EP verdict only) on mismatch.
 */
export async function askExplainerForPacket(
  traceId: string,
  options?: ExplainerApiOptions,
): Promise<ExplainPacketResponse> {
  const trimmed = traceId.trim();
  if (!trimmed) {
    throw new Error('A packet trace_id is required to explain a packet.');
  }
  const fetchImpl = fetchForExplainer(options);
  const response = await fetchImpl(
    `/api/explainer/evidence/${encodeURIComponent(trimmed)}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: requiredAuthorizationHeader(options?.authToken),
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

function fetchForExplainer(options?: ExplainerApiOptions): typeof fetch {
  const fetchImpl = options?.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  if (!fetchImpl) {
    throw new Error('Explainer API requires fetch support.');
  }
  return fetchImpl;
}

function requiredAuthorizationHeader(authToken?: string | null): string {
  const trimmed = authToken?.trim();
  if (!trimmed) {
    throw new Error('Account session is required for the CAS Harness Guide.');
  }
  return /^Bearer\s+/i.test(trimmed) ? trimmed : `Bearer ${trimmed}`;
}
