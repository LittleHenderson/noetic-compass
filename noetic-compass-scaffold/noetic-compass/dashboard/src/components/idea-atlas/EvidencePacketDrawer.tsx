/**
 * EvidencePacketDrawer — Stage 21B Atlas reviewer drawer.
 *
 * Slides in from the right when the user clicks a thought-tree node
 * whose verification carries an evidence packet trace_id. Fetches the
 * full Stage 21A Evidence Packet from
 * `GET /api/harness/evidence/{trace_id}` and surfaces it across seven
 * tabs:
 *
 *   1. Readout              — probe output + per-axis votes
 *   2. Diagnostics          — lacunarity / blindspot / RPM / stability
 *   3. Controls             — random null / text baseline / ablation
 *   4. Generation Readiness — Stage 20 action + reasons + recommended_mode
 *   5. Provenance           — model revision, fixture sha, commit, paths
 *   6. Caveats              — bounded-claim language
 *   7. Rejected Claims      — explicit no-license items
 *
 * Tabs are lazy-rendered: only the active tab's content is mounted,
 * matching the existing dashboard convention (NodeDetailPanel,
 * EvidencePacket v1). The drawer does not block the Atlas tree view
 * behind it — the backdrop is dim but the underlying view stays
 * interactive once the drawer is closed.
 *
 * Reserved language: badge text is the verbatim Stage 20 action
 * ("Allow", "Caveat", "Constrain", "Suppress"). Section titles say
 * "Caveats", "Rejected Claims", "Generation Readiness" — never
 * "rejected", "failed", "blocked", or "error" except inside the actual
 * error UI ("evidence packet not found").
 *
 * Accessibility:
 *   - role="dialog" + aria-modal + aria-labelledby on the panel root
 *   - Escape key closes the drawer
 *   - Backdrop click closes the drawer (drawer body clicks do NOT)
 *   - Tab buttons are <button> elements with role="tab" + aria-selected
 *   - Active tabpanel has role="tabpanel" + aria-labelledby pointing at
 *     the active tab button
 *   - Focus moves to the close button on open
 */
import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  isEvidencePacket,
  type EvidencePacket,
  type EvidenceReadout,
  type EvidenceDiagnostics,
  type EvidenceControls,
  type EvidenceGenerationReadiness,
  type EvidenceProvenance,
  type GenerationReadinessAction,
} from '../../lib/evidencePacket';
import { apiFetch, apiFetchText } from '../../api/client';
import { VerificationPanel } from './VerificationPanel';
import type { NodeVerification } from '../../lib/trace';

// ── Public API ─────────────────────────────────────────────────────────────

export interface EvidencePacketDrawerProps {
  /** Trace id of the packet to load. When null, the drawer is closed. */
  traceId: string | null;
  /** Called when the user dismisses the drawer (Escape, backdrop, close). */
  onClose: () => void;
  /**
   * Optional packet override. When supplied, the drawer skips the
   * fetch and renders this packet directly. Used for tests and for
   * inline "preview" callers that already have the packet in memory.
   */
  initialPacket?: EvidencePacket | null;
  /**
   * Optional fetch override. Defaults to global `fetch`. Tests inject
   * a mock implementation here.
   */
  fetchImpl?: typeof fetch;
}

// ── Tab definitions ────────────────────────────────────────────────────────

type TabId =
  | 'readout'
  | 'diagnostics'
  | 'controls'
  | 'readiness'
  | 'provenance'
  | 'caveats'
  | 'rejected_claims';

interface TabSpec {
  id: TabId;
  label: string;
}

const TABS: readonly TabSpec[] = [
  { id: 'readout', label: 'Readout' },
  { id: 'diagnostics', label: 'Diagnostics' },
  { id: 'controls', label: 'Controls' },
  { id: 'readiness', label: 'Generation Readiness' },
  { id: 'provenance', label: 'Provenance' },
  { id: 'caveats', label: 'Caveats' },
  { id: 'rejected_claims', label: 'Rejected Claims' },
] as const;

// ── Stage 20 action → badge style mapping ──────────────────────────────────
// Mirrors the VerificationPanel decision_tier palette. The four action
// values are reserved language — surface them exactly.

interface ReadinessBadgeStyle {
  label: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
}

const READINESS_STYLES: Record<GenerationReadinessAction, ReadinessBadgeStyle> =
  {
    allow: {
      label: 'Allow',
      badgeBg: 'bg-emerald-500/20',
      badgeText: 'text-emerald-300',
      badgeBorder: 'border-emerald-400/40',
    },
    caveat: {
      label: 'Caveat',
      badgeBg: 'bg-amber-500/20',
      badgeText: 'text-amber-300',
      badgeBorder: 'border-amber-400/40',
    },
    constrain: {
      label: 'Constrain',
      badgeBg: 'bg-sky-500/20',
      badgeText: 'text-sky-300',
      badgeBorder: 'border-sky-400/40',
    },
    suppress: {
      label: 'Suppress',
      badgeBg: 'bg-rose-500/20',
      badgeText: 'text-rose-300',
      badgeBorder: 'border-rose-400/40',
    },
  };

function readinessStyleFor(action: string): ReadinessBadgeStyle {
  if (action in READINESS_STYLES) {
    return READINESS_STYLES[action as GenerationReadinessAction];
  }
  return {
    label: action,
    badgeBg: 'bg-slate-500/20',
    badgeText: 'text-slate-300',
    badgeBorder: 'border-slate-400/40',
  };
}

/**
 * Map Stage 20 action onto a VerificationPanel-compatible NodeVerification
 * shape so the existing badge component can render the headline status
 * inside the Generation Readiness tab. `allow` and `caveat` map to
 * ACCEPT; `constrain` and `suppress` map to SUPPRESS.
 */
function readinessAsVerification(
  action: GenerationReadinessAction | string,
  recommended: string,
): NodeVerification {
  const isAccept = action === 'allow' || action === 'caveat';
  const tier: NodeVerification['decision_tier'] =
    action === 'allow'
      ? 'high'
      : action === 'caveat'
        ? 'medium'
        : action === 'suppress' || action === 'constrain'
          ? 'suppress'
          : 'uncertain';
  return {
    decision: isAccept ? 'ACCEPT' : 'SUPPRESS',
    decision_tier: tier,
    suppression_reasons: !isAccept ? [recommended] : undefined,
  };
}

// ── Per-tab body renderers ─────────────────────────────────────────────────
// Each renderer is small + self-contained so the drawer composes them
// without a render-prop or large switch table.

function ReadoutTab({ readout }: { readout: EvidenceReadout }) {
  const voteEntries = Object.entries(readout.votes ?? {});
  return (
    <div
      data-testid="evidence-packet-tab-readout"
      id="evidence-packet-tab-readout"
      role="tabpanel"
      aria-labelledby="evidence-packet-tab-button-readout"
      className="space-y-3 font-mono text-[11px] text-slate-300"
    >
      <h3 className="text-accent-teal text-xs font-bold">Readout</h3>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
        <Field label="axis" value={readout.axis} />
        <Field label="label" value={readout.label} />
        <Field
          label="layer"
          value={readout.layer == null ? '—' : String(readout.layer)}
        />
        <Field label="position" value={readout.position ?? '—'} />
        <Field
          label="confidence"
          value={
            readout.confidence == null
              ? '—'
              : readout.confidence.toFixed(3)
          }
        />
        <Field
          label="confidence source"
          value={readout.confidence_source ?? '—'}
        />
      </dl>
      <section>
        <h4 className="mt-2 text-[10px] uppercase tracking-wide text-slate-500">
          stable agree
        </h4>
        <ul
          data-testid="evidence-packet-readout-stable-agree"
          className="mt-1 flex flex-wrap gap-1.5"
        >
          {(readout.stable_agree ?? []).length === 0 ? (
            <li className="italic text-slate-500">no stable-agree positions</li>
          ) : (
            (readout.stable_agree ?? []).map((p) => (
              <li
                key={p}
                className="rounded border border-emerald-400/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-200"
              >
                {p}
              </li>
            ))
          )}
        </ul>
      </section>
      <section>
        <h4 className="mt-2 text-[10px] uppercase tracking-wide text-slate-500">
          per-position votes
        </h4>
        {voteEntries.length === 0 ? (
          <p className="mt-1 italic text-slate-500">no per-position votes</p>
        ) : (
          <dl
            data-testid="evidence-packet-readout-votes"
            className="mt-1 space-y-1"
          >
            {voteEntries.map(([position, label]) => (
              <div key={position} className="flex items-center gap-2">
                <dt className="w-44 text-slate-500">{position}</dt>
                <dd className="text-slate-200">{label}</dd>
              </div>
            ))}
          </dl>
        )}
      </section>
    </div>
  );
}

function DiagnosticsTab({
  diagnostics,
  readiness,
}: {
  diagnostics: EvidenceDiagnostics;
  readiness: EvidenceGenerationReadiness;
}) {
  const evidence = readiness.evidence ?? null;
  return (
    <div
      data-testid="evidence-packet-tab-diagnostics"
      id="evidence-packet-tab-diagnostics"
      role="tabpanel"
      aria-labelledby="evidence-packet-tab-button-diagnostics"
      className="space-y-3 font-mono text-[11px] text-slate-300"
    >
      <h3 className="text-accent-teal text-xs font-bold">Diagnostics</h3>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
        <Field
          label="lacunarity"
          value={
            diagnostics.lacunarity == null
              ? '—'
              : String(diagnostics.lacunarity)
          }
        />
        <Field
          label="inversion flags"
          value={
            evidence
              ? String(evidence.inversion_flag_count)
              : '—'
          }
        />
        <Field
          label="RPM satisfaction"
          value={
            evidence
              ? evidence.rpm_satisfaction.toFixed(3)
              : '—'
          }
        />
        <Field
          label="max gap probability"
          value={
            evidence ? evidence.max_gap_probability.toFixed(3) : '—'
          }
        />
        <Field
          label="mean gap probability"
          value={
            evidence ? evidence.mean_gap_probability.toFixed(3) : '—'
          }
        />
        <Field
          label="max lacunarity"
          value={
            evidence ? evidence.max_lacunarity.toFixed(3) : '—'
          }
        />
        <Field
          label="min domain confidence"
          value={
            evidence ? evidence.min_domain_confidence.toFixed(3) : '—'
          }
        />
        <Field
          label="trace stability"
          value={
            evidence?.verification_accepted ? 'stable' : 'flagged'
          }
        />
      </dl>
      <section>
        <h4 className="mt-2 text-[10px] uppercase tracking-wide text-slate-500">
          blindspot flags
        </h4>
        <ul
          data-testid="evidence-packet-diagnostics-blindspots"
          className="mt-1 flex flex-wrap gap-1.5"
        >
          {(diagnostics.blindspot_flags ?? []).length === 0 ? (
            <li className="italic text-slate-500">no blindspot flags</li>
          ) : (
            diagnostics.blindspot_flags.map((flag, i) => (
              <li
                key={`${flag}-${i}`}
                className="rounded border border-amber-400/30 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-200"
              >
                {flag.replace(/_/g, ' ')}
              </li>
            ))
          )}
        </ul>
      </section>
      {diagnostics.note ? (
        <p
          data-testid="evidence-packet-diagnostics-note"
          className="text-[11px] italic text-slate-500"
        >
          {diagnostics.note}
        </p>
      ) : null}
    </div>
  );
}

function ControlsTab({ controls }: { controls: EvidenceControls }) {
  return (
    <div
      data-testid="evidence-packet-tab-controls"
      id="evidence-packet-tab-controls"
      role="tabpanel"
      aria-labelledby="evidence-packet-tab-button-controls"
      className="space-y-3 font-mono text-[11px] text-slate-300"
    >
      <h3 className="text-accent-teal text-xs font-bold">Controls</h3>
      <dl className="space-y-2">
        <Field
          label="random null ablation"
          value={controls.random_ablation ?? '—'}
          wide
        />
        <Field
          label="text baseline"
          value={controls.text_baseline ?? '—'}
          wide
        />
        <Field
          label="metadata baseline"
          value={controls.metadata_baseline ?? '—'}
          wide
        />
        <Field
          label="raw symbol delta"
          value={
            controls.raw_symbol_delta == null
              ? '—'
              : controls.raw_symbol_delta.toFixed(4)
          }
          wide
        />
      </dl>
    </div>
  );
}

function GenerationReadinessTab({
  readiness,
}: {
  readiness: EvidenceGenerationReadiness;
}) {
  const style = readinessStyleFor(readiness.generation_readiness);
  const verification = readinessAsVerification(
    readiness.generation_readiness,
    readiness.recommended_mode,
  );
  return (
    <div
      data-testid="evidence-packet-tab-readiness"
      id="evidence-packet-tab-readiness"
      role="tabpanel"
      aria-labelledby="evidence-packet-tab-button-readiness"
      className="space-y-3 font-mono text-[11px] text-slate-300"
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-accent-teal text-xs font-bold">
          Generation Readiness
        </h3>
        <span
          data-testid="evidence-packet-readiness-badge"
          className={[
            'rounded border px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider',
            style.badgeBg,
            style.badgeText,
            style.badgeBorder,
          ].join(' ')}
        >
          {style.label}
        </span>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
        <Field label="mode" value={readiness.mode} />
        <Field label="recommended mode" value={readiness.recommended_mode} />
        <Field
          label="risk score"
          value={readiness.risk_score.toFixed(2)}
        />
        <Field label="policy version" value={readiness.policy_version} />
      </dl>
      <section>
        <h4 className="mt-2 text-[10px] uppercase tracking-wide text-slate-500">
          reasons
        </h4>
        <ul
          data-testid="evidence-packet-readiness-reasons"
          className="mt-1 space-y-1"
        >
          {(readiness.reasons ?? []).length === 0 ? (
            <li className="italic text-slate-500">no reason codes recorded</li>
          ) : (
            readiness.reasons.map((reason, i) => (
              <li
                key={`${reason}-${i}`}
                className="rounded border border-slate-500/30 bg-slate-500/10 px-2 py-0.5 text-[10px] text-slate-200"
              >
                {reason}
              </li>
            ))
          )}
        </ul>
      </section>
      {/* Reuse the existing VerificationPanel badge/colors per the spec */}
      <VerificationPanel verification={verification} />
    </div>
  );
}

function ProvenanceTab({
  provenance,
  traceId,
  createdAt,
  modelRevision,
}: {
  provenance: EvidenceProvenance;
  traceId: string;
  createdAt: string;
  modelRevision: string;
}) {
  return (
    <div
      data-testid="evidence-packet-tab-provenance"
      id="evidence-packet-tab-provenance"
      role="tabpanel"
      aria-labelledby="evidence-packet-tab-button-provenance"
      className="space-y-3 font-mono text-[11px] text-slate-300"
    >
      <h3 className="text-accent-teal text-xs font-bold">Provenance</h3>
      <dl className="space-y-2">
        <Field label="trace id" value={traceId} wide />
        <Field label="created at" value={createdAt} wide />
        <Field label="model revision" value={modelRevision} wide />
        <Field label="source stage" value={provenance.source_stage} wide />
        <Field label="code commit" value={provenance.code_commit} wide />
        <Field label="fixture sha256" value={provenance.fixture_sha256} wide />
        <Field label="activation file" value={provenance.activation_file} wide />
        <Field
          label="activation sha256"
          value={provenance.activation_sha256}
          wide
        />
      </dl>
      <section>
        <h4 className="mt-2 text-[10px] uppercase tracking-wide text-slate-500">
          source reports
        </h4>
        <ul
          data-testid="evidence-packet-provenance-source-reports"
          className="mt-1 space-y-1"
        >
          {(provenance.source_reports ?? []).map((report, i) => (
            <li
              key={`${report}-${i}`}
              className="rounded border border-slate-500/30 bg-slate-500/10 px-2 py-0.5 text-[10px] text-slate-200 break-all"
            >
              {report}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function CaveatsTab({ caveats }: { caveats: string[] }) {
  return (
    <div
      data-testid="evidence-packet-tab-caveats"
      id="evidence-packet-tab-caveats"
      role="tabpanel"
      aria-labelledby="evidence-packet-tab-button-caveats"
      className="space-y-3 font-mono text-[11px] text-slate-300"
    >
      <h3 className="text-accent-teal text-xs font-bold">Caveats</h3>
      {caveats.length === 0 ? (
        <p className="italic text-slate-500">No caveats recorded.</p>
      ) : (
        <ul
          data-testid="evidence-packet-caveats-list"
          className="list-disc space-y-2 pl-5 text-slate-200"
        >
          {caveats.map((c, i) => (
            <li key={i} className="leading-relaxed">
              {c}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RejectedClaimsTab({ rejectedClaims }: { rejectedClaims: string[] }) {
  return (
    <div
      data-testid="evidence-packet-tab-rejected-claims"
      id="evidence-packet-tab-rejected_claims"
      role="tabpanel"
      aria-labelledby="evidence-packet-tab-button-rejected_claims"
      className="space-y-3 font-mono text-[11px] text-slate-300"
    >
      <h3 className="text-accent-teal text-xs font-bold">Rejected Claims</h3>
      <p className="text-[10px] italic text-slate-500">
        Explicit no-license list. This packet does NOT make any of the
        claims below.
      </p>
      {rejectedClaims.length === 0 ? (
        <p className="italic text-slate-500">No rejected-claims list recorded.</p>
      ) : (
        <ul
          data-testid="evidence-packet-rejected-claims-list"
          className="list-disc space-y-2 pl-5 text-rose-200"
        >
          {rejectedClaims.map((c, i) => (
            <li
              key={i}
              data-testid={`evidence-packet-rejected-claim-${i}`}
              className="rounded border border-rose-400/30 bg-rose-500/[0.08] px-2 py-1 leading-relaxed"
            >
              {c}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Shared <Field> ─────────────────────────────────────────────────────────

function Field({
  label,
  value,
  wide = false,
}: {
  label: string;
  value: string;
  wide?: boolean;
}) {
  return (
    <div className={wide ? 'col-span-2' : undefined}>
      <dt className="text-[10px] uppercase tracking-wide text-slate-500">
        {label}
      </dt>
      <dd className="break-words text-slate-200">{value}</dd>
    </div>
  );
}

// ── Export helpers ─────────────────────────────────────────────────────────

/**
 * Trigger a Blob-based download. Uses the existing dashboard pattern
 * (createObjectURL + anchor click + revokeObjectURL) so it works
 * unchanged under jsdom + the export-JSON test.
 */
function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

// ── Main component ────────────────────────────────────────────────────────

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; packet: EvidencePacket }
  | { kind: 'not_found' }
  | { kind: 'error'; message: string };

export function EvidencePacketDrawer({
  traceId,
  onClose,
  initialPacket,
  fetchImpl,
}: EvidencePacketDrawerProps) {
  const open = traceId != null;
  const headingId = useId();
  const [activeTab, setActiveTab] = useState<TabId>('readout');
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  const initialState: LoadState = initialPacket
    ? { kind: 'ready', packet: initialPacket }
    : { kind: 'idle' };
  const [state, setState] = useState<LoadState>(initialState);

  // Reset to the first tab whenever the drawer reopens with a new id
  useEffect(() => {
    if (open) setActiveTab('readout');
  }, [traceId, open]);

  // Fetch on open (unless initialPacket is supplied)
  useEffect(() => {
    if (!open) return;
    if (initialPacket) {
      setState({ kind: 'ready', packet: initialPacket });
      return;
    }
    if (!traceId) return;
    let cancelled = false;
    setState({ kind: 'loading' });
    void (async () => {
      try {
        const json: unknown = fetchImpl
          ? await (async () => {
              const res = await fetchImpl(
                `/api/harness/evidence/${encodeURIComponent(traceId)}`,
              );
              if (res.status === 404) {
                return { __evidence_packet_not_found__: true };
              }
              if (!res.ok) {
                throw new Error(`Server responded with status ${res.status}.`);
              }
              return res.json();
            })()
          : await apiFetch<unknown>(
              `/harness/evidence/${encodeURIComponent(traceId)}`,
            );
        if (cancelled) return;
        if (
          typeof json === 'object' &&
          json !== null &&
          '__evidence_packet_not_found__' in json
        ) {
          setState({ kind: 'not_found' });
          return;
        }
        if (!isEvidencePacket(json)) {
          setState({
            kind: 'error',
            message: 'Returned payload did not match the Evidence Packet schema.',
          });
          return;
        }
        setState({ kind: 'ready', packet: json });
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : String(err);
        if (message.includes('evidence packet not found')) {
          setState({ kind: 'not_found' });
          return;
        }
        setState({ kind: 'error', message });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [traceId, open, initialPacket, fetchImpl]);

  // Escape key + focus management
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    // Pull focus to the close button on open so keyboard users land
    // somewhere predictable rather than at the top of the page.
    requestAnimationFrame(() => {
      closeButtonRef.current?.focus();
    });
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const handleExportJson = useCallback(() => {
    if (state.kind !== 'ready' || !traceId) return;
    const blob = new Blob([JSON.stringify(state.packet, null, 2)], {
      type: 'application/json',
    });
    triggerDownload(blob, `evidence_packet_${traceId}.json`);
  }, [state, traceId]);

  const handleExportMarkdown = useCallback(async () => {
    if (state.kind !== 'ready' || !traceId) return;
    try {
      if (!fetchImpl) {
        const text = await apiFetchText(
          `/harness/evidence/${encodeURIComponent(traceId)}/markdown`,
        );
        const blob = new Blob([text], { type: 'text/markdown' });
        triggerDownload(blob, `evidence_packet_${traceId}.md`);
        return;
      }
      const res = await fetchImpl(
        `/api/harness/evidence/${encodeURIComponent(traceId)}/markdown`,
      );
      if (!res.ok) {
        // Surface no UI alert — caller's audit log / network panel
        // shows the failure. Reserved-language discipline: no toast.
        return;
      }
      const text = await res.text();
      const blob = new Blob([text], { type: 'text/markdown' });
      triggerDownload(blob, `evidence_packet_${traceId}.md`);
    } catch {
      // Swallow; markdown export is best-effort.
    }
  }, [state, traceId, fetchImpl]);

  // Tab rendering — only the active tab body mounts (lazy).
  const activeTabBody = useMemo(() => {
    if (state.kind !== 'ready') return null;
    const packet = state.packet;
    switch (activeTab) {
      case 'readout':
        return <ReadoutTab readout={packet.readout} />;
      case 'diagnostics':
        return (
          <DiagnosticsTab
            diagnostics={packet.diagnostics}
            readiness={packet.generation_readiness}
          />
        );
      case 'controls':
        return <ControlsTab controls={packet.controls} />;
      case 'readiness':
        return (
          <GenerationReadinessTab readiness={packet.generation_readiness} />
        );
      case 'provenance':
        return (
          <ProvenanceTab
            provenance={packet.provenance}
            traceId={packet.trace_id}
            createdAt={packet.created_at}
            modelRevision={packet.model?.revision ?? '—'}
          />
        );
      case 'caveats':
        return <CaveatsTab caveats={packet.caveats ?? []} />;
      case 'rejected_claims':
        return (
          <RejectedClaimsTab rejectedClaims={packet.rejected_claims ?? []} />
        );
      default:
        return null;
    }
  }, [activeTab, state]);

  if (!open) return null;

  const exportsDisabled = state.kind !== 'ready';

  return (
    <div
      data-testid="evidence-packet-drawer-root"
      className="fixed inset-0 z-50 flex"
    >
      {/* Backdrop — dim, but clicks pass through to close so the
          underlying Atlas remains the focus. */}
      <div
        data-testid="evidence-packet-drawer-backdrop"
        aria-hidden="true"
        onClick={onClose}
        className="absolute inset-0 bg-black/60"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        data-testid="evidence-packet-drawer"
        className={[
          'relative ml-auto flex h-full w-full max-w-[560px] flex-col',
          'border-l border-white/[0.08] bg-[#0d1117] shadow-2xl',
          'animate-[fadeSlideIn_0.18s_ease-out]',
        ].join(' ')}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <header className="flex items-start justify-between gap-3 border-b border-white/[0.06] px-5 py-4">
          <div className="min-w-0">
            <h2
              id={headingId}
              className="font-mono text-sm font-semibold text-accent-teal"
            >
              Evidence Packet
            </h2>
            <p className="mt-1 font-mono text-[10px] text-slate-500 break-all">
              {traceId}
            </p>
            {state.kind === 'ready' ? (
              <p
                data-testid="evidence-packet-drawer-export-label"
                className="mt-1 font-sans text-[10px] text-slate-500"
              >
                {state.packet.export_label}
              </p>
            ) : null}
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="shrink-0 rounded border border-white/[0.08] px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-slate-400 transition-colors hover:border-emerald-400/30 hover:text-emerald-200"
          >
            Close
          </button>
        </header>

        {/* Boundary blurb — surfaces the bounded-claim language so the
            reviewer sees it before any tab content. */}
        {state.kind === 'ready' ? (
          <div
            data-testid="evidence-packet-drawer-boundary"
            className="border-b border-white/[0.06] bg-slate-500/[0.04] px-5 py-3 font-sans text-[11px] leading-relaxed text-slate-300"
          >
            {state.packet.boundary}
          </div>
        ) : null}

        {/* Tab strip */}
        <nav
          role="tablist"
          aria-label="Evidence Packet sections"
          className="flex shrink-0 gap-1 overflow-x-auto border-b border-white/[0.06] px-3 py-2"
        >
          {TABS.map((t) => {
            const isActive = activeTab === t.id;
            return (
              <button
                key={t.id}
                id={`evidence-packet-tab-button-${t.id}`}
                role="tab"
                type="button"
                aria-selected={isActive}
                aria-controls={`evidence-packet-tab-${t.id}`}
                data-testid={`evidence-packet-tab-button-${t.id}`}
                onClick={() => setActiveTab(t.id)}
                className={[
                  'shrink-0 rounded px-3 py-1 font-mono text-[11px] transition-colors',
                  isActive
                    ? 'bg-accent-teal/20 text-accent-teal'
                    : 'text-slate-400 hover:text-slate-200',
                ].join(' ')}
              >
                {t.label}
              </button>
            );
          })}
        </nav>

        {/* Body */}
        <div
          data-testid="evidence-packet-drawer-body"
          className="flex-1 overflow-y-auto px-5 py-4"
        >
          {state.kind === 'loading' && (
            <div
              data-testid="evidence-packet-drawer-loading"
              className="font-mono text-xs text-slate-400 animate-pulse"
            >
              Loading evidence packet…
            </div>
          )}
          {state.kind === 'not_found' && (
            <div
              data-testid="evidence-packet-drawer-not-found"
              className="rounded border border-amber-500/20 bg-amber-500/[0.05] p-4 font-mono text-xs text-amber-300"
            >
              evidence packet not found
            </div>
          )}
          {state.kind === 'error' && (
            <div
              data-testid="evidence-packet-drawer-error"
              className="rounded border border-rose-500/20 bg-rose-500/[0.05] p-4 font-mono text-xs text-rose-300"
            >
              {state.message}
            </div>
          )}
          {state.kind === 'idle' && (
            <div className="font-mono text-xs text-slate-500 italic">
              No evidence packet selected.
            </div>
          )}
          {state.kind === 'ready' && activeTabBody}
        </div>

        {/* Footer — export buttons */}
        <footer className="flex shrink-0 items-center justify-end gap-2 border-t border-white/[0.06] px-5 py-3">
          <button
            type="button"
            data-testid="evidence-packet-drawer-export-json"
            disabled={exportsDisabled}
            onClick={handleExportJson}
            className="rounded border border-accent-teal/30 bg-accent-teal/10 px-3 py-1.5 font-mono text-[11px] text-accent-teal transition-colors hover:bg-accent-teal/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Download JSON
          </button>
          <button
            type="button"
            data-testid="evidence-packet-drawer-export-markdown"
            disabled={exportsDisabled}
            onClick={handleExportMarkdown}
            className="rounded border border-violet-400/30 bg-violet-500/10 px-3 py-1.5 font-mono text-[11px] text-violet-200 transition-colors hover:bg-violet-500/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Download Markdown
          </button>
        </footer>
      </aside>
    </div>
  );
}

export default EvidencePacketDrawer;
