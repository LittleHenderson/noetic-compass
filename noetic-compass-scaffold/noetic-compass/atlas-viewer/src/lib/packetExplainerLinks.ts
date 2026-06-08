// Ref-chip → Evidence-Packet-field linking (AI Explainer spec §6).
//
// The packet explainer returns each claim with structured `refs` — EP field
// keys like "verdict", "proof_chips.causal_proof.status", "anchor.status", or
// "blind_spots.0". The widget renders each ref as a clickable chip that
// scrolls/links to that exact field in the real Evidence Packet view.
//
// This module is the single source of truth for that wiring: it maps a ref key
// to a stable DOM id, and the EP view (EvidenceRail) stamps the same ids on its
// field zones via `epFieldAnchorProps`. Keeping the id derivation in one place
// means the chip target and the field anchor can never drift apart.

const EP_FIELD_ID_PREFIX = 'ep-field';

/**
 * Normalize a raw ref into the stable suffix used in its DOM id. Lowercased,
 * dots/spaces collapsed to single hyphens, and only `[a-z0-9-]` kept so the id
 * is always a valid, collision-resistant attribute selector.
 */
function refSlug(ref: string): string {
  return ref
    .trim()
    .toLowerCase()
    .replace(/[.\s/]+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

/**
 * The DOM element id an EP field is anchored to. Both the ref-chip target and
 * the field zone in EvidenceRail derive their id from this function, so a chip
 * for `proof_chips.causal_proof.status` always finds the matching anchor.
 *
 * Refs are coarsened to the field zone that actually renders: any
 * `proof_chips.<id>.*` ref resolves to that chip's row; any `anchor.*` ref
 * resolves to the packet/anchor panel; `verdict` and `verdict_echo` both
 * resolve to the verdict zone.
 */
export function epFieldElementId(ref: string): string {
  const slug = refSlug(ref);

  // verdict / verdict_echo → the verdict zone.
  if (slug === 'verdict' || slug === 'verdict-echo') {
    return `${EP_FIELD_ID_PREFIX}-verdict`;
  }

  // proof_chips.<chipId>(.status|.label|...) → that chip's row.
  const proofMatch = /^proof-chips-([a-z0-9-]+?)(?:-(?:status|label|detail))?$/.exec(slug);
  if (proofMatch) {
    return `${EP_FIELD_ID_PREFIX}-proof-${proofMatch[1]}`;
  }

  // anchor.* (status / retention / trace_id) → the packet/anchor panel.
  if (slug === 'anchor' || slug.startsWith('anchor-')) {
    return `${EP_FIELD_ID_PREFIX}-anchor`;
  }

  // Everything else (blind_spots.N, scope, counts, model_target, …) gets a
  // 1:1 anchor; the EP view can stamp these where the field renders.
  return `${EP_FIELD_ID_PREFIX}-${slug}`;
}

/**
 * Props the EP view spreads onto a field-zone element so a ref-chip can find
 * it. `data-ep-field` carries the original ref for debugging/tests; `id` is the
 * scroll target. Pass the canonical ref for the zone (e.g. "verdict",
 * "proof_chips.causal_proof", "anchor.status").
 */
export function epFieldAnchorProps(ref: string): {
  id: string;
  'data-ep-field': string;
} {
  return { id: epFieldElementId(ref), 'data-ep-field': ref };
}

const HIGHLIGHT_CLASS = 'ep-field-flash';

/**
 * Scroll the EP field matching `ref` into view and flash a brief highlight so
 * the user sees exactly which field a claim is anchored to. No-op (returns
 * false) when the target isn't in the DOM — e.g. the EP view is on another tab
 * or the field didn't render — so a chip click never throws.
 */
export function scrollToEpField(ref: string): boolean {
  if (typeof document === 'undefined') return false;
  const el = document.getElementById(epFieldElementId(ref));
  if (!el) return false;

  el.scrollIntoView({ behavior: 'smooth', block: 'center' });

  // Restart the flash animation if it's already running.
  el.classList.remove(HIGHLIGHT_CLASS);
  // Force reflow so re-adding the class re-triggers the animation.
  void el.offsetWidth;
  el.classList.add(HIGHLIGHT_CLASS);
  window.setTimeout(() => el.classList.remove(HIGHLIGHT_CLASS), 1600);
  return true;
}

// The keyframes for the flash highlight. Injected once into the EP view (the
// PacketExplainerPanel mounts it) so the linked field pulses with the teal
// accent without each consumer re-declaring the animation.
export const EP_FIELD_FLASH_CSS = `
@keyframes epFieldFlash {
  0%   { box-shadow: 0 0 0 0 rgba(45, 212, 191, 0.0); }
  18%  { box-shadow: 0 0 0 3px rgba(45, 212, 191, 0.55); }
  100% { box-shadow: 0 0 0 0 rgba(45, 212, 191, 0.0); }
}
.${HIGHLIGHT_CLASS} {
  animation: epFieldFlash 1.5s ease-out;
  border-radius: 8px;
}
@media (prefers-reduced-motion: reduce) {
  .${HIGHLIGHT_CLASS} { animation: none; box-shadow: 0 0 0 2px rgba(45, 212, 191, 0.5); }
}
`;
