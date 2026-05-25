import type { CreateLiveSessionRequest, LiveProbeName } from './atlasLiveApi';
import type { VerificationMode } from '../components/cockpit/ControlBar';
import type { KnobValue } from '../components/cockpit/MethodKnobsPanel';

export type LiveMethodId =
  | 'foundation_probe'
  | 'rpm_gate_check'
  | 'inversion_scan'
  | 'sparse_neuron_cover'
  | 'drive_local_eraser'
  | 'blindspot_detection'
  | 'verification_stack';

export interface LiveMethodControls {
  enabledMethodIds: LiveMethodId[];
  knobValues: Partial<Record<LiveMethodId, Record<string, KnobValue>>>;
  verificationMode: VerificationMode;
  showBlindspots: boolean;
  showActiveTrace: boolean;
}

const DEFAULT_PROMPT =
  'I noticed a warm coffee cup beside an open book under a sunny window.';

const PROBES_BY_METHOD: Record<LiveMethodId, LiveProbeName[]> = {
  foundation_probe: ['active_trace'],
  rpm_gate_check: ['mode7_attribution'],
  inversion_scan: ['active_trace', 'confidence_margin'],
  sparse_neuron_cover: ['blindspot_covers'],
  drive_local_eraser: ['active_trace', 'confidence_margin'],
  blindspot_detection: ['blindspot_covers'],
  verification_stack: ['confidence_margin'],
};

export function buildLiveSessionRequest(
  controls: LiveMethodControls,
  overrides?: Partial<CreateLiveSessionRequest>,
): CreateLiveSessionRequest {
  return {
    prompt: DEFAULT_PROMPT,
    max_new_tokens: 24,
    temperature: 0,
    seed: 42,
    ...overrides,
    probes: probesForControls(controls),
    method_config: {
      enabled_methods: controls.enabledMethodIds,
      knobs: controls.knobValues,
      overlays: {
        show_active_trace: controls.showActiveTrace,
        show_blindspots: controls.showBlindspots,
      },
      verification_mode: controls.verificationMode,
    },
  };
}

export function probesForControls(controls: LiveMethodControls): LiveProbeName[] {
  const out: LiveProbeName[] = [];
  const seen = new Set<LiveProbeName>();
  for (const methodId of controls.enabledMethodIds) {
    for (const probe of PROBES_BY_METHOD[methodId] ?? []) {
      if (seen.has(probe)) continue;
      seen.add(probe);
      out.push(probe);
    }
  }
  if (!controls.showActiveTrace) {
    remove(out, 'active_trace');
  }
  if (!controls.showBlindspots) {
    remove(out, 'blindspot_covers');
  }
  return out;
}

function remove(items: LiveProbeName[], probe: LiveProbeName): void {
  const idx = items.indexOf(probe);
  if (idx >= 0) items.splice(idx, 1);
}
