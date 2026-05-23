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
      'Highlights the neurons most-activated by the current token. Use it to see "where the thought lives" at any moment.',
  },
  {
    name: 'Blindspots overlay (B)',
    what:
      'Highlights neurons known to cover the F1 (Unity) drive\'s register set — A / T / f / E. These are the model\'s blindspots: the structural footprint of a single drive\'s coverage. Tells you what could be missed.',
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

const HOW_IT_RELATES = `The picture is the stimulus. The token stream is the model's response.
The neural net shows how the response was built — which neurons fired
to land each token. The Mode 7 arcs link the token currently being
produced back to the earlier tokens whose information was integrated.`;

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
