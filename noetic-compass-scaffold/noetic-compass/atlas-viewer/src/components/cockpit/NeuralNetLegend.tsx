import { useState, type CSSProperties } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';
import { COLORS, SPRING_GENTLE, THEME } from '../../lib/designTokens';

const wrapStyle: CSSProperties = {
  position: 'absolute',
  top: 12,
  right: 12,
  zIndex: 20,
  pointerEvents: 'auto',
  fontFamily: THEME.fontFamily,
};

const containerStyle: CSSProperties = {
  background: 'rgba(2, 6, 23, 0.78)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
  borderRadius: 6,
  backdropFilter: 'blur(14px) saturate(120%)',
  WebkitBackdropFilter: 'blur(14px) saturate(120%)',
  color: COLORS.textPrimary,
  fontSize: 11.5,
  overflow: 'hidden',
};

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 12,
  padding: '6px 10px',
  cursor: 'pointer',
  userSelect: 'none',
  borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
};

const titleStyle: CSSProperties = {
  fontSize: 10.5,
  fontWeight: 700,
  letterSpacing: 1.2,
  textTransform: 'uppercase',
  color: COLORS.textMuted,
};

const toggleLabelStyle: CSSProperties = {
  fontSize: 10,
  color: COLORS.textMuted,
};

const rowsStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  padding: '8px 10px 10px 10px',
};

const rowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'auto 1fr',
  alignItems: 'center',
  columnGap: 8,
};

const swatchStyle = (fill: string, outline?: string): CSSProperties => ({
  width: 10,
  height: 10,
  borderRadius: 2,
  background: fill,
  border: outline ? `1px solid ${outline}` : '1px solid rgba(255, 255, 255, 0.15)',
});

const labelStyle: CSSProperties = {
  fontWeight: 600,
  color: COLORS.textPrimary,
  fontSize: 11.5,
};

const descStyle: CSSProperties = {
  gridColumn: '2 / 3',
  color: COLORS.textSecondary,
  fontSize: 10.5,
  lineHeight: 1.4,
  marginTop: 1,
};

interface LegendRow {
  swatch: string;
  outline?: string;
  label: string;
  desc: string;
}

const ROWS: LegendRow[] = [
  {
    swatch: ATLAS_STATUS_COLORS.intervention,
    label: 'Selected',
    desc: 'You clicked this neuron; the drawer shows its evidence.',
  },
  {
    swatch: ATLAS_STATUS_COLORS.suppress,
    label: 'Blindspot',
    desc: "In the selected drive's cover set. Toggle with B.",
  },
  {
    swatch: ATLAS_STATUS_COLORS.activeTrace,
    label: 'Active now',
    desc: 'Highest activation for the current token. Toggle with T.',
  },
  {
    swatch:
      'linear-gradient(90deg, hsl(220, 70%, 55%), hsl(160, 70%, 55%), hsl(320, 70%, 55%))',
    label: 'Drive-tinted',
    desc: 'Activation hue varies by drive when a drive overlay is on.',
  },
  {
    swatch: '#2a2a3a',
    label: 'Inactive',
    desc: 'Below the activation threshold for the current token.',
  },
];

export default function NeuralNetLegend(): JSX.Element {
  const [open, setOpen] = useState<boolean>(true);

  return (
    <div style={wrapStyle} data-testid="neural-net-legend">
      <motion.div style={containerStyle} layout transition={SPRING_GENTLE}>
        <div
          style={headerStyle}
          onClick={() => setOpen((value) => !value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              setOpen((value) => !value);
            }
          }}
          role="button"
          tabIndex={0}
          aria-expanded={open}
          aria-controls="neural-net-legend-rows"
          data-testid="neural-net-legend-toggle"
        >
          <span style={titleStyle}>Neuron colors</span>
          <span style={toggleLabelStyle} aria-hidden="true">
            {open ? 'Hide' : 'Show'}
          </span>
        </div>
        <AnimatePresence initial={false}>
          {open ? (
            <motion.div
              key="rows"
              id="neural-net-legend-rows"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={SPRING_GENTLE}
              style={{ overflow: 'hidden' }}
            >
              <div style={rowsStyle}>
                {ROWS.map((row) => (
                  <div key={row.label} style={rowStyle}>
                    <span style={swatchStyle(row.swatch, row.outline)} aria-hidden="true" />
                    <span style={labelStyle}>{row.label}</span>
                    <span style={descStyle}>{row.desc}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
