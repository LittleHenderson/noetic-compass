import type { CSSProperties } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ACCENT_TEAL, COLORS, SPRING_GENTLE, THEME } from '../../lib/designTokens';

export interface HelpOverlayProps {
  open: boolean;
  onClose: () => void;
}

const backdropStyle: CSSProperties = {
  position: 'absolute',
  inset: 0,
  background: 'rgba(2, 6, 23, 0.78)',
  backdropFilter: 'blur(8px)',
  WebkitBackdropFilter: 'blur(8px)',
  zIndex: 50,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 24,
};

const panelStyle: CSSProperties = {
  width: '100%',
  maxWidth: 720,
  maxHeight: '85vh',
  overflowY: 'auto',
  background: 'rgba(2, 6, 23, 0.95)',
  border: '1px solid rgba(255, 255, 255, 0.10)',
  borderRadius: 8,
  padding: '24px 28px',
  color: COLORS.textPrimary,
  fontFamily: THEME.fontFamily,
  fontSize: 13,
  lineHeight: 1.6,
};

const headerRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'baseline',
  justifyContent: 'space-between',
  marginBottom: 14,
};

const titleStyle: CSSProperties = {
  margin: 0,
  fontSize: 18,
  fontWeight: 700,
  letterSpacing: -0.2,
  color: COLORS.textPrimary,
};

const subtitleStyle: CSSProperties = {
  margin: 0,
  fontSize: 11,
  letterSpacing: 1.5,
  textTransform: 'uppercase',
  color: COLORS.textMuted,
  fontWeight: 600,
};

const closeButtonStyle: CSSProperties = {
  padding: '4px 10px',
  borderRadius: 6,
  border: '1px solid rgba(255, 255, 255, 0.10)',
  background: 'transparent',
  color: COLORS.textSecondary,
  fontSize: 11.5,
  cursor: 'pointer',
  fontFamily: THEME.fontFamily,
};

const sectionStyle: CSSProperties = {
  marginTop: 18,
};

const sectionHeaderStyle: CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: 1.4,
  textTransform: 'uppercase',
  color: ACCENT_TEAL,
  margin: '0 0 8px 0',
};

const bodyTextStyle: CSSProperties = {
  margin: '0 0 8px 0',
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.6,
};

const orderedListStyle: CSSProperties = {
  margin: '0 0 0 18px',
  padding: 0,
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.55,
};

const listItemStyle: CSSProperties = {
  marginBottom: 8,
  paddingLeft: 4,
};

const inlineStrongStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontWeight: 700,
};

const kbdStyle: CSSProperties = {
  display: 'inline-block',
  padding: '1px 6px',
  borderRadius: 4,
  border: '1px solid rgba(255, 255, 255, 0.12)',
  background: 'rgba(255, 255, 255, 0.04)',
  color: COLORS.textPrimary,
  fontFamily: THEME.fontMono,
  fontSize: 11,
  letterSpacing: 0.3,
};

const tableStyle: CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: 12.5,
};

const thStyle: CSSProperties = {
  textAlign: 'left',
  padding: '6px 8px',
  color: COLORS.textMuted,
  fontSize: 10.5,
  fontWeight: 600,
  letterSpacing: 0.8,
  textTransform: 'uppercase',
  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
};

const tdStyle: CSSProperties = {
  padding: '6px 8px',
  color: COLORS.textSecondary,
  borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
  verticalAlign: 'top',
};

const COMPONENTS: Array<{ name: string; what: string }> = [
  {
    name: 'Neural net (center)',
    what:
      'A 3D map of Pythia-160M. Each glowing dot is one neuron at one layer. Layers stack top to bottom; columns and rows inside a layer are the neuron index. Brighter dots = more active for the token currently selected on the timeline.',
  },
  {
    name: 'Picture panel (left)',
    what:
      'The stimulus that was fed to the model when this trace was recorded, plus the spatial primitives the model attended to (points, boxes, regions). Click a primitive to highlight where in the picture the model was looking when the active token was emitted.',
  },
  {
    name: 'Mode 7 timeline (bottom)',
    what:
      'The token stream from left to right. Each cell is one token. The active cell has a teal border. The curved arcs show attribution — which earlier tokens influenced the current one. Click any cell to jump.',
  },
  {
    name: 'Controls panel (right)',
    what:
      'The testing-method catalog. Each card is one diagnostic the cockpit can run on the active trace. Toggle a method on / off, expand it to tune knobs, read what it reveals. The cost badge is GPU minutes.',
  },
  {
    name: 'Active trace overlay (T)',
    what:
      'Highlights the neurons most-activated by the current token — the real top-activation set captured from the Pythia-160M forward pass for this prompt. Use it to see "where the thought lives" at this moment.',
  },
  {
    name: 'Blindspots overlay (B)',
    what:
      'Every cognitive operation in CAS lives in one of four registers — Analytical, Transcendent, affective, Embodied. The F1 drive (Unity) has a known set of neurons that cover each of those registers. The Blindspot overlay paints those four cover sets together. What it tells you: which parts of the network the F1 drive would have to fire to handle a Unity-related thought, and therefore — when Unity-related content shows up in the input but those neurons are quiet — what the model could be missing right now.',
  },
  {
    name: 'Confidence badges',
    what:
      'Each spatial primitive carries a `conf 0.NN` badge. The number is the model\'s self-reported certainty for that grounding — derived from the softmax margin (top-1 minus runner-up logit) at the token where the primitive was emitted, normalised into [0, 1]. > 0.80 = green / confident; 0.50–0.80 = amber / caveat; < 0.50 = orange / constrain.',
  },
];

const SHORTCUTS: Array<{ keys: string[]; action: string }> = [
  { keys: ['Space'], action: 'Play / pause' },
  { keys: ['R'], action: 'Rewind to first token' },
  { keys: [',', '.'], action: 'Step token back / forward' },
  { keys: ['[', ']'], action: 'Zoom out / in' },
  { keys: ['B'], action: 'Toggle blindspots' },
  { keys: ['T'], action: 'Toggle active trace' },
  { keys: ['F'], action: 'Fullscreen neural net' },
  { keys: ['?'], action: 'Open this help panel' },
  { keys: ['Esc'], action: 'Close help' },
];

const CAS_HARNESS_METHOD_STEPS: Array<{ title: string; body: string }> = [
  {
    title: 'Use the original source-defined taxonomy.',
    body:
      'For the 20B replication, that means the exact Stage 7 TKS Foundation-28 grid: seven drives times four registers, with the legacy 1a..7d mapping preserved.',
  },
  {
    title: 'Capture real hidden states from the open-weight model.',
    body:
      'Run the actual model weights, save layer-by-layer activations, and keep model id, revision, dtype, layer count, scenario hash, and label distribution.',
  },
  {
    title: 'Read the CAS axis with the original balanced linear probe.',
    body:
      'Use StandardScaler plus LogisticRegression(C=0.1, class_weight="balanced"). On GPT-NeoX-20B Stage 7, layer 40 reached 86.8622% heldout Foundation accuracy.',
  },
  {
    title: 'Run matched causal controls.',
    body:
      'Suppress the true Foundation cover, then compare against same-size random covers and wrong-Foundation covers. The true cover must damage the readout more than controls.',
  },
  {
    title: 'Check the eta-to-epsilon behavioral bridge.',
    body:
      'Read the model state, realize it as readable English context, run the model again, and measure whether likelihood moves in the CAS-predicted direction. On 20B, probe-readable delta was +0.596413 with 90/112 positive rows.',
  },
  {
    title: 'Run trace diagnostics before claiming closure.',
    body:
      'Compute Foundation lacunarity and layer-trace class. On 20B, lacunarity was 0.006715 against a <= 0.05 pass gate, with numeric trace class Amplifying.',
  },
  {
    title: 'Only then merge an Evidence Packet.',
    body:
      'A final ACCEPT, SUPPRESS, or FLAG verdict requires the verifier and Evidence Packet. The current 20B result is strong evidence, not yet the final verdict layer.',
  },
];

const CAS_METHOD_SUMMARY =
  'Canonical label: S7-F28-BALANCED-BRIDGE. Plain name: S7-F28 Balanced Bridge Method. CAS Harness is not a pretty label overlay; this method means source-defined labels, real hidden states, balanced probe, targeted removal, matched controls, output-likelihood bridge, trace diagnostics, then Evidence Packet verdict.';

const TKS40_TEXT_BASELINE_SUMMARY =
  'TKS40 compact-gloss v0 stays guarded: text-only reached 100.00%, so it cannot support a CAS-beats-text claim. The corrected GPT-NeoX-20B original Stage 9 40E run is the claim-bearing baseline: hidden readout 95.625%, confirmed text baseline 49.241%, text-hash 50.000%, shuffled-label mean 2.619%.';

const TKS40_TEXT_BASELINE_STEPS: Array<{ title: string; body: string }> = [
  {
    title: 'What text baseline means.',
    body:
      'It is a classifier that sees only the scenario words. It does not load the model and does not inspect hidden states.',
  },
  {
    title: 'Why 100% blocks the TKS40 comparison claim.',
    body:
      'If text alone gets every heldout label right, the scenario wording is acting like an answer key. Hidden readout can still be real, but it has not beaten a meaningful text adversary.',
  },
  {
    title: 'What the corrected 20B run proves.',
    body:
      'On the original Stage 9 role-bound/counterfactual fixture, GPT-NeoX-20B hidden states read the 40-Element grid far above surface text on the same fixed split: 95.625% hidden versus 49.241% text-only.',
  },
  {
    title: 'What the standing rule is.',
    body:
      'Every future 40E library must run the text-baseline diagnostic first. If text-only is above the pre-registered ceiling, the packet can show hidden-state signal but cannot claim CAS beats text.',
  },
];

const EVIDENCE_PACKET_FLIGHT_RECORDER_SUMMARY =
  'The Evidence Packet is the black-box flight recorder for a CAS Harness run: one trace_id-keyed record of what model was audited, what CAS saw, what verdict was returned, which proof chips supported it, and how the packet is integrity-checked afterward.';

const EVIDENCE_PACKET_FLIGHT_RECORDER_STEPS: Array<{ title: string; body: string }> = [
  {
    title: 'What it records.',
    body:
      'Input, output, model metadata, audit config, proof chips, confidence basis, verifier decision, packet hash, hash-log entry, and external anchor receipt.',
  },
  {
    title: 'What tamper-evidence means.',
    body:
      'Changing the packet changes its SHA-256 hash. Changing the hash-log entry breaks the recorded chain. The verifier re-reads the external S3 anchor object and checks that it commits to the same packet hash and hash-log entry.',
  },
  {
    title: 'What Object Lock retained means now.',
    body:
      'Production strict smoke passed with S3 Object Lock required. New anchored packets are written with Object Lock GOVERNANCE retention and verified by HeadObject before the UI may show Object Lock GOVERNANCE.',
  },
  {
    title: 'What it does not prove by itself.',
    body:
      'It does not prove the model is safe or objectively correct. It proves what CAS observed and decided under that audit configuration, and that the resulting record is hash-bound, externally anchored, and retention-protected.',
  },
];

const HOW_IT_RELATES = `The picture is the stimulus. The token stream is the model's response.
The neural net shows how the response was built — which neurons fired
to land each token. The Mode 7 arcs link the token currently being
produced back to the earlier tokens whose information was integrated.`;

const DATA_PROVENANCE = `What's real, what's demo, right now:

• Neural net positions + activations + Mode 7 attribution arcs + neuron-cover blindspots
  are captured from an actual Pythia-160M forward pass on the prompt below — recorded
  offline and replayed here. Every glowing neuron and every arc is a real number from
  the real model. (model_id: EleutherAI/pythia-160m · 12 layers · 162M params · validated.)

• The picture and its spatial primitives (boxes / points / regions) are demo fixtures.
  Live picture grounding requires the vision-grounding pipeline to be wired to a running
  Pythia + vision encoder — that's the next milestone (roadmap items #6 + #8).

When the live wire-up lands, every primitive shown here will be replaced with primitives
emitted by the running model in real time. Until then: trace is real, picture is demo.`;

export default function HelpOverlay({ open, onClose }: HelpOverlayProps): JSX.Element {
  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          style={backdropStyle}
          role="dialog"
          aria-modal="true"
          aria-labelledby="help-overlay-title"
          data-testid="help-overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) onClose();
          }}
          onKeyDown={(e) => {
            if (e.key === 'Escape') onClose();
          }}
          tabIndex={-1}
        >
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={SPRING_GENTLE}
            style={panelStyle}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={headerRowStyle}>
              <div>
                <p style={subtitleStyle}>Atlas Viewer · Alpha</p>
                <h2 style={titleStyle} id="help-overlay-title">
                  How to read the cockpit
                </h2>
              </div>
              <button
                type="button"
                style={closeButtonStyle}
                onClick={onClose}
                aria-label="Close help"
                data-testid="help-overlay-close"
              >
                Close · Esc
              </button>
            </div>

            <section style={sectionStyle}>
              <h3 style={sectionHeaderStyle}>What you're looking at</h3>
              <p style={bodyTextStyle}>{HOW_IT_RELATES}</p>
            </section>

            <section style={sectionStyle}>
              <h3 style={sectionHeaderStyle}>Data provenance — real vs demo</h3>
              <p style={{ ...bodyTextStyle, whiteSpace: 'pre-line', color: COLORS.textPrimary }}>
                {DATA_PROVENANCE}
              </p>
            </section>

            <section style={sectionStyle}>
              <h3 style={sectionHeaderStyle}>Components</h3>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Component</th>
                    <th style={thStyle}>What it shows</th>
                  </tr>
                </thead>
                <tbody>
                  {COMPONENTS.map((row) => (
                    <tr key={row.name}>
                      <td style={{ ...tdStyle, color: COLORS.textPrimary, fontWeight: 600, width: 180 }}>
                        {row.name}
                      </td>
                      <td style={tdStyle}>{row.what}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section style={sectionStyle} data-testid="cas-harness-method-faq">
              <h3 style={sectionHeaderStyle}>FAQ: S7-F28 Balanced Bridge Method</h3>
              <p style={bodyTextStyle}>{CAS_METHOD_SUMMARY}</p>
              <ol style={orderedListStyle}>
                {CAS_HARNESS_METHOD_STEPS.map((step) => (
                  <li key={step.title} style={listItemStyle}>
                    <span style={inlineStrongStyle}>{step.title}</span> {step.body}
                  </li>
                ))}
              </ol>
            </section>

            <section style={sectionStyle} data-testid="tks40-text-baseline-faq">
              <h3 style={sectionHeaderStyle}>FAQ: TKS40 Text Baseline Guard</h3>
              <p style={bodyTextStyle}>{TKS40_TEXT_BASELINE_SUMMARY}</p>
              <ol style={orderedListStyle}>
                {TKS40_TEXT_BASELINE_STEPS.map((step) => (
                  <li key={step.title} style={listItemStyle}>
                    <span style={inlineStrongStyle}>{step.title}</span> {step.body}
                  </li>
                ))}
              </ol>
            </section>

            <section style={sectionStyle} data-testid="evidence-packet-flight-recorder-faq">
              <h3 style={sectionHeaderStyle}>FAQ: Evidence Packet Flight Recorder</h3>
              <p style={bodyTextStyle}>{EVIDENCE_PACKET_FLIGHT_RECORDER_SUMMARY}</p>
              <ol style={orderedListStyle}>
                {EVIDENCE_PACKET_FLIGHT_RECORDER_STEPS.map((step) => (
                  <li key={step.title} style={listItemStyle}>
                    <span style={inlineStrongStyle}>{step.title}</span> {step.body}
                  </li>
                ))}
              </ol>
            </section>

            <section style={sectionStyle}>
              <h3 style={sectionHeaderStyle}>Keyboard shortcuts</h3>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Keys</th>
                    <th style={thStyle}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {SHORTCUTS.map((row) => (
                    <tr key={row.action}>
                      <td style={{ ...tdStyle, width: 160 }}>
                        {row.keys.map((k, i) => (
                          <span key={k}>
                            {i > 0 ? <span style={{ color: COLORS.textMuted }}>{' / '}</span> : null}
                            <span style={kbdStyle}>{k}</span>
                          </span>
                        ))}
                      </td>
                      <td style={tdStyle}>{row.action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
