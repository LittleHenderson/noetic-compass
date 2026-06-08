// Decoupled open-channel for the packet explainer float.
//
// The "Explain this packet" button lives in the Evidence Packet view
// (EvidenceRail), but the explanation panel is mounted once at the console
// shell level (AuditAppFrame) so it floats over everything — the same place the
// Guide widget lives. They are in different React subtrees with no shared
// props, so the button asks the panel to open via a tiny window CustomEvent
// carrying just what the panel needs: the packet `traceId` and the EP's own
// `verdict` (used for the §7 verdict-echo fail-closed assertion).

export const PACKET_EXPLAINER_OPEN_EVENT = 'cas:packet-explainer:open';

export interface PacketExplainerOpenDetail {
  /** The Evidence Packet trace_id to explain. */
  traceId: string;
  /**
   * The verdict exactly as the EP records it. The panel asserts
   * `response.verdict_echo === epVerdict` and fails closed on mismatch.
   */
  epVerdict: string;
}

/** Fire the open-request. No-op outside a browser (SSR / tests without DOM). */
export function requestPacketExplanation(detail: PacketExplainerOpenDetail): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(
    new CustomEvent<PacketExplainerOpenDetail>(PACKET_EXPLAINER_OPEN_EVENT, {
      detail,
    }),
  );
}

/**
 * Subscribe to open-requests. Returns an unsubscribe fn. The panel uses this in
 * an effect so it opens whenever any EP view's button is pressed.
 */
export function onPacketExplanationRequested(
  handler: (detail: PacketExplainerOpenDetail) => void,
): () => void {
  if (typeof window === 'undefined') return () => undefined;
  const listener = (event: Event): void => {
    const detail = (event as CustomEvent<PacketExplainerOpenDetail>).detail;
    if (detail && typeof detail.traceId === 'string') {
      handler(detail);
    }
  };
  window.addEventListener(PACKET_EXPLAINER_OPEN_EVENT, listener);
  return () => window.removeEventListener(PACKET_EXPLAINER_OPEN_EVENT, listener);
}
