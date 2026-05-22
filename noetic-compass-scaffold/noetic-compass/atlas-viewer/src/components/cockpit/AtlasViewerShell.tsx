import { useCallback, useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import ControlBar, {
  type Speed,
  type VerificationMode,
  type ZoomLevel,
} from './ControlBar';
import {
  NeuralNetScene,
  type NeuronCoord,
  type PerTokenFrame,
} from './NeuralNetScene';
import Mode7Timeline, {
  type Mode7Frame,
  type Token,
} from './Mode7Timeline';
import MethodKnobsPanel, { type KnobValue } from './MethodKnobsPanel';
import SpatialEvidencePanel from './SpatialEvidencePanel';
import VisualPrimitiveCanvas from './VisualPrimitiveCanvas';
import EvidenceDrawer, { type EvidenceDrawerPayload } from './EvidenceDrawer';
import { useReplayController } from '../../hooks/useReplayController';
import type { ReplayTrace } from '../../lib/replayController';
import type { ModelArchitecture } from '../../lib/modelArchitecture';
import {
  TESTING_METHODS,
  type TestingMethod,
} from '../../lib/testingMethods';
import {
  primitivesForStep,
  type EvidenceRef,
  type SpatialEvidenceArtifact,
  type VisualPrimitive,
} from '../../lib/visualPrimitives';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';
import { parseCoord } from '../../lib/neuronCover';

interface TraceNeuronCovers {
  per_class_neuron_covers?: Record<string, string[]>;
}
interface TraceWithCovers {
  neuron_covers?: TraceNeuronCovers;
}

const BLINDSPOT_DEMO_CLASSES = ['F1A', 'F1T', 'F1f', 'F1E'];

export interface AtlasViewerShellProps {
  trace: ReplayTrace;
  spatialEvidence: SpatialEvidenceArtifact;
  architecture: ModelArchitecture;
  methods?: readonly TestingMethod[];
  className?: string;
}

type LeftTab = 'spatial' | 'notation';

const shellStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  minHeight: 0,
  background: '#05070d',
  color: '#e5e7eb',
  fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
};

const mainGridStyle: CSSProperties = {
  flex: 1,
  display: 'grid',
  gridTemplateColumns: '40% 40% 20%',
  minHeight: 0,
  overflow: 'hidden',
};

const columnStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  minWidth: 0,
  minHeight: 0,
  borderRight: '1px solid #1f2937',
  overflow: 'hidden',
};

const lastColumnStyle: CSSProperties = {
  ...columnStyle,
  borderRight: 'none',
};

const tabBarStyle: CSSProperties = {
  display: 'flex',
  borderBottom: '1px solid #1f2937',
  background: '#111827',
};

const tabBaseStyle: CSSProperties = {
  flex: 1,
  padding: '8px 12px',
  background: 'transparent',
  color: '#9ca3af',
  border: 'none',
  borderBottom: '2px solid transparent',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 500,
};

const tabActiveStyle: CSSProperties = {
  ...tabBaseStyle,
  color: ATLAS_STATUS_COLORS.activeTrace,
  borderBottom: `2px solid ${ATLAS_STATUS_COLORS.activeTrace}`,
};

const tabPanelStyle: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: 12,
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  minHeight: 0,
};

const centerColumnStyle: CSSProperties = {
  ...columnStyle,
  background: '#02040a',
};

const rightColumnStyle: CSSProperties = {
  ...lastColumnStyle,
  overflowY: 'auto',
};

const bottomTimelineStyle: CSSProperties = {
  padding: '8px 12px 12px 12px',
  background: '#0b1220',
  borderTop: '1px solid #1f2937',
};

const placeholderCardStyle: CSSProperties = {
  padding: 16,
  borderRadius: 6,
  background: '#0f172a',
  border: '1px dashed #334155',
  color: '#9ca3af',
  fontSize: 13,
  lineHeight: 1.5,
};

function defaultValueForKnob(knob: { type: string; default: unknown }): KnobValue {
  if (knob.type === 'multiselect') {
    return Array.isArray(knob.default) ? [...(knob.default as string[])] : [];
  }
  if (knob.type === 'boolean') return Boolean(knob.default);
  if (knob.type === 'number') {
    return typeof knob.default === 'number' ? knob.default : 0;
  }
  return String(knob.default ?? '');
}

function initialKnobValues(
  methods: readonly TestingMethod[],
): Record<string, Record<string, KnobValue>> {
  const out: Record<string, Record<string, KnobValue>> = {};
  for (const method of methods) {
    const knobMap: Record<string, KnobValue> = {};
    for (const knob of method.knobs) {
      knobMap[knob.id] = defaultValueForKnob(knob);
    }
    out[method.id] = knobMap;
  }
  return out;
}

function frameToToken(frame: unknown): Token | null {
  if (typeof frame !== 'object' || frame === null) return null;
  const f = frame as { token_index?: unknown; token?: unknown };
  if (typeof f.token_index !== 'number' || typeof f.token !== 'string') return null;
  return { token_index: f.token_index, token: f.token };
}

function frameToMode7Frame(frame: unknown): Mode7Frame | null {
  if (typeof frame !== 'object' || frame === null) return null;
  const f = frame as {
    token_index?: unknown;
    mode7_attribution?: unknown;
  };
  if (typeof f.token_index !== 'number') return null;
  const attr = Array.isArray(f.mode7_attribution) ? f.mode7_attribution : undefined;
  return {
    token_index: f.token_index,
    mode7_attribution: attr as Mode7Frame['mode7_attribution'],
  };
}

function frameAtIndex(frames: unknown[], index: number): PerTokenFrame | undefined {
  const candidate = frames[index];
  if (typeof candidate !== 'object' || candidate === null) return undefined;
  return candidate as PerTokenFrame;
}

export function AtlasViewerShell(props: AtlasViewerShellProps): JSX.Element {
  const {
    trace,
    spatialEvidence,
    architecture,
    methods = TESTING_METHODS,
    className,
  } = props;

  const {
    state,
    toggle,
    seek,
    setSpeed,
  } = useReplayController(trace);

  const [leftTab, setLeftTab] = useState<LeftTab>('spatial');
  const [selectedNeuron, setSelectedNeuron] = useState<NeuronCoord | undefined>(
    undefined,
  );
  const [activePrimitiveId, setActivePrimitiveId] = useState<string | undefined>(
    undefined,
  );
  const [enabledMethodIds, setEnabledMethodIds] = useState<Set<string>>(
    () => new Set(methods.map((m) => m.id)),
  );
  const [knobValues, setKnobValues] = useState<
    Record<string, Record<string, KnobValue>>
  >(() => initialKnobValues(methods));
  const [zoomLevel, setZoomLevel] = useState<ZoomLevel>(0);
  const [showBlindspots, setShowBlindspots] = useState<boolean>(true);
  const [showActiveTrace, setShowActiveTrace] = useState<boolean>(true);
  const [verificationMode, setVerificationMode] =
    useState<VerificationMode>('BALANCED');
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState<boolean>(false);
  const [evidencePayload, setEvidencePayload] = useState<
    EvidenceDrawerPayload | undefined
  >(undefined);

  // Derive Token + Mode7 frame lists from the raw per_token_frames payload.
  // ReplayTrace.per_token_frames is typed as unknown[] to keep the controller
  // agnostic of trace schema; this shell narrows them for the timeline.
  const tokens = useMemo<Token[]>(() => {
    if (trace.tokens && trace.tokens.length > 0) return trace.tokens;
    return trace.per_token_frames
      .map(frameToToken)
      .filter((t): t is Token => t !== null);
  }, [trace.tokens, trace.per_token_frames]);

  const mode7Frames = useMemo<Mode7Frame[]>(() => {
    return trace.per_token_frames
      .map(frameToMode7Frame)
      .filter((f): f is Mode7Frame => f !== null);
  }, [trace.per_token_frames]);

  const currentTokenIndex = state.currentTokenIndex;
  const currentFrame = useMemo<PerTokenFrame | undefined>(
    () => frameAtIndex(trace.per_token_frames, currentTokenIndex),
    [trace.per_token_frames, currentTokenIndex],
  );

  // Derive the active grounded step from the current token index.
  // The visual-grounding fixture pins each grounded_step to a specific
  // token_index (5, 9, 13, 17 in the demo). We find the grounded_step whose
  // token_index EXACTLY matches the current scrub position; absent a match
  // (e.g. the scrubber is between two anchor tokens or before the first one),
  // the spatial panel shows its empty state per the wave-2 spec.
  const activeStep = useMemo(() => {
    return spatialEvidence.grounded_steps.find(
      (s) => s.token_index === currentTokenIndex,
    );
  }, [spatialEvidence.grounded_steps, currentTokenIndex]);

  const activePrimitives = useMemo<VisualPrimitive[]>(() => {
    if (!activeStep) return [];
    return primitivesForStep(spatialEvidence, activeStep.step_id);
  }, [spatialEvidence, activeStep]);

  const activePrimitiveIds = useMemo<string[]>(
    () => activePrimitives.map((p) => p.id),
    [activePrimitives],
  );

  // Active-trace coords for the 3D scene: the current token's high-activation
  // neurons (above 0.3). Wave 2.1: gated by showActiveTrace.
  const activeTraceCoords = useMemo<NeuronCoord[] | undefined>(() => {
    if (!showActiveTrace || !currentFrame) return undefined;
    return currentFrame.top_activated_neurons
      .filter((n) => n.activation >= 0.3)
      .map((n) => ({
        layer: n.layer,
        index: n.index,
        label: `L${n.layer}N${n.index}`,
      }));
  }, [showActiveTrace, currentFrame]);

  // Blindspot coords: union of the F1 (Unity) drive eraser-channel covers from
  // the trace's neuron_covers block (Stage 27F shape). At v0 we surface the
  // four F1|R covers (A/T/f/E) so the user sees the cross-register footprint
  // of one drive's blindspot. Wave 3 will let the user pick which drive.
  const blindspotCoords = useMemo<NeuronCoord[] | undefined>(() => {
    if (!showBlindspots) return undefined;
    const covers = (trace as unknown as TraceWithCovers).neuron_covers?.per_class_neuron_covers;
    if (!covers) return undefined;
    const seen = new Set<string>();
    const out: NeuronCoord[] = [];
    for (const cls of BLINDSPOT_DEMO_CLASSES) {
      const labels = covers[cls];
      if (!labels) continue;
      for (const label of labels) {
        if (seen.has(label)) continue;
        seen.add(label);
        try {
          out.push(parseCoord(label));
        } catch {
          // Skip malformed cover entries; don't crash the scene.
        }
      }
    }
    return out;
  }, [showBlindspots, trace]);

  // Clear primitive selection when the active step changes so stale highlight
  // state doesn't leak from one step to the next.
  useEffect(() => {
    setActivePrimitiveId(undefined);
  }, [activeStep?.step_id]);

  const handlePlayToggle = useCallback(() => {
    toggle();
  }, [toggle]);

  const handleSpeedChange = useCallback(
    (s: Speed) => {
      setSpeed(s);
    },
    [setSpeed],
  );

  const handleTokenSeek = useCallback(
    (idx: number) => {
      seek(idx);
    },
    [seek],
  );

  const handleToggleMethod = useCallback(
    (methodId: string, enabled: boolean) => {
      setEnabledMethodIds((prev) => {
        const next = new Set(prev);
        if (enabled) next.add(methodId);
        else next.delete(methodId);
        return next;
      });
    },
    [],
  );

  const handleKnobChange = useCallback(
    (methodId: string, knobId: string, value: KnobValue) => {
      setKnobValues((prev) => ({
        ...prev,
        [methodId]: {
          ...(prev[methodId] ?? {}),
          [knobId]: value,
        },
      }));
    },
    [],
  );

  const openDrawer = useCallback((payload: EvidenceDrawerPayload) => {
    setEvidencePayload(payload);
    setEvidenceDrawerOpen(true);
  }, []);

  const closeDrawer = useCallback(() => {
    setEvidenceDrawerOpen(false);
  }, []);

  const handleNeuronClick = useCallback(
    (coord: NeuronCoord) => {
      setSelectedNeuron(coord);
      openDrawer({
        source: 'neuron',
        title: coord.label,
        evidence_ref: {
          neuron_coordinate: coord.label,
          layer: coord.layer,
          neuron_index: coord.index,
          token_index: currentTokenIndex,
        },
        detail: {
          token: tokens[currentTokenIndex]?.token,
          architecture: architecture.family,
        },
      });
    },
    [openDrawer, currentTokenIndex, tokens, architecture.family],
  );

  const handlePrimitiveSelect = useCallback((p: VisualPrimitive) => {
    setActivePrimitiveId(p.id);
  }, []);

  const handlePrimitiveOpenEvidence = useCallback(
    (ref: EvidenceRef) => {
      openDrawer({
        source: 'primitive',
        title: 'Spatial primitive',
        evidence_ref: ref,
      });
    },
    [openDrawer],
  );

  const handlePrimitiveCanvasClick = useCallback(
    (p: VisualPrimitive, ref?: EvidenceRef) => {
      setActivePrimitiveId(p.id);
      if (ref) {
        openDrawer({
          source: 'primitive',
          title: p.label ?? p.id,
          evidence_ref: ref,
          detail: {
            cas_label: p.cas_label,
            cas_axis: p.cas_axis,
            confidence: p.confidence,
          },
        });
      }
    },
    [openDrawer],
  );

  return (
    <div
      className={className}
      data-testid="atlas-viewer-shell"
      style={shellStyle}
    >
      <ControlBar
        playbackMode={state.playbackMode}
        speed={state.speed as Speed}
        zoomLevel={zoomLevel}
        currentTokenIndex={currentTokenIndex}
        tokenCount={state.tokenCount}
        verificationMode={verificationMode}
        showBlindspots={showBlindspots}
        showActiveTrace={showActiveTrace}
        onPlayToggle={handlePlayToggle}
        onSpeedChange={handleSpeedChange}
        onZoomLevelChange={setZoomLevel}
        onTokenSeek={handleTokenSeek}
        onVerificationModeChange={setVerificationMode}
        onToggleBlindspots={() => setShowBlindspots((v) => !v)}
        onToggleActiveTrace={() => setShowActiveTrace((v) => !v)}
      />

      <div style={mainGridStyle} data-testid="atlas-viewer-main">
        <div style={columnStyle} data-testid="atlas-viewer-left">
          <div role="tablist" aria-label="Evidence views" style={tabBarStyle}>
            <button
              type="button"
              role="tab"
              aria-selected={leftTab === 'spatial'}
              data-testid="left-tab-spatial"
              onClick={() => setLeftTab('spatial')}
              style={leftTab === 'spatial' ? tabActiveStyle : tabBaseStyle}
            >
              Spatial Evidence
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={leftTab === 'notation'}
              data-testid="left-tab-notation"
              onClick={() => setLeftTab('notation')}
              style={leftTab === 'notation' ? tabActiveStyle : tabBaseStyle}
            >
              2D Notation
            </button>
          </div>
          <div
            role="tabpanel"
            data-testid="left-tab-panel"
            style={tabPanelStyle}
          >
            {leftTab === 'spatial' ? (
              <>
                <VisualPrimitiveCanvas
                  imageUrl={spatialEvidence.image_url}
                  imageWidth={spatialEvidence.image_width}
                  imageHeight={spatialEvidence.image_height}
                  primitives={spatialEvidence.primitives}
                  activeStepPrimitiveIds={activePrimitiveIds}
                  onPrimitiveClick={handlePrimitiveCanvasClick}
                />
                <SpatialEvidencePanel
                  primitives={activePrimitives}
                  selectedPrimitiveId={activePrimitiveId}
                  onPrimitiveSelect={handlePrimitiveSelect}
                  onOpenEvidence={handlePrimitiveOpenEvidence}
                  emptyStateLabel={
                    activeStep
                      ? 'No spatial evidence for this step'
                      : 'Scrub forward to reach a grounded step'
                  }
                />
              </>
            ) : (
              <div
                style={placeholderCardStyle}
                data-testid="notation-placeholder"
              >
                <strong>2D Notation — pending wave 3.</strong>
                <p style={{ margin: '8px 0 0 0' }}>
                  This slot will render the 169-primitive CAS notation map
                  (wrapping <code>dashboard/src/lib/notation2DMap</code>). Not
                  yet wired in v0.0 — the dashboard package lives outside
                  atlas-viewer's tsconfig include, so the wrap requires either
                  a published shared package or a vendored copy. Tracked as a
                  v0.0 → v0.1 follow-up.
                </p>
              </div>
            )}
          </div>
        </div>

        <div style={centerColumnStyle} data-testid="atlas-viewer-center">
          <NeuralNetScene
            architecture={architecture}
            currentFrame={currentFrame}
            selectedNeuron={selectedNeuron}
            blindspotCoords={blindspotCoords}
            activeTraceCoords={activeTraceCoords}
            onNeuronClick={handleNeuronClick}
          />
        </div>

        <div style={rightColumnStyle} data-testid="atlas-viewer-right">
          <MethodKnobsPanel
            methods={[...methods]}
            enabledMethodIds={enabledMethodIds}
            knobValues={knobValues}
            onToggleMethod={handleToggleMethod}
            onKnobChange={handleKnobChange}
          />
        </div>
      </div>

      <div style={bottomTimelineStyle} data-testid="atlas-viewer-bottom">
        <Mode7Timeline
          tokens={tokens}
          frames={mode7Frames}
          currentTokenIndex={currentTokenIndex}
          onTokenSelect={handleTokenSeek}
        />
      </div>

      <EvidenceDrawer
        open={evidenceDrawerOpen}
        payload={evidencePayload}
        onClose={closeDrawer}
      />
    </div>
  );
}

export default AtlasViewerShell;
