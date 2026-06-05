import {
  useId,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react';
import { COLORS, FONT_FAMILY } from '../../lib/designTokens';

export interface DisclosureProps {
  /** Always-visible summary row label. */
  summary: ReactNode;
  /** Optional trailing element on the summary row (count chip, status, etc.). */
  trailing?: ReactNode;
  children: ReactNode;
  /** Uncontrolled default open state. Ignored when `open` is provided. */
  defaultOpen?: boolean;
  /** Controlled open state. Pair with `onOpenChange`. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  className?: string;
  /** Accessible label for the toggle button, when the summary is not text. */
  ariaLabel?: string;
}

const wrapperStyle: CSSProperties = {
  display: 'grid',
  gap: 0,
  fontFamily: FONT_FAMILY,
};

const summaryButtonStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 10,
  width: '100%',
  padding: '9px 11px',
  borderRadius: 8,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(255, 255, 255, 0.03)',
  color: COLORS.textPrimary,
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 13,
  fontWeight: 700,
  textAlign: 'left',
};

const summaryLeftStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 9,
  minWidth: 0,
};

const chevronStyle = (open: boolean): CSSProperties => ({
  display: 'inline-block',
  width: 12,
  color: COLORS.textMuted,
  fontSize: 11,
  transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
  transition: 'transform 0.15s ease',
});

const panelStyle: CSSProperties = {
  padding: '12px 4px 2px',
};

/**
 * Shared collapse primitive promoted from the dashboard declutter pass. Works
 * controlled (`open` + `onOpenChange`) or uncontrolled (`defaultOpen`). Keeps a
 * single, honest toggle so methodology / advanced surfaces can hide behind one
 * affordance without bespoke state in every consumer.
 */
export function Disclosure({
  summary,
  trailing,
  children,
  defaultOpen = false,
  open,
  onOpenChange,
  className,
  ariaLabel,
}: DisclosureProps): JSX.Element {
  const panelId = useId();
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const isControlled = open !== undefined;
  const isOpen = isControlled ? open : internalOpen;

  const toggle = (): void => {
    const next = !isOpen;
    if (!isControlled) setInternalOpen(next);
    onOpenChange?.(next);
  };

  return (
    <div style={wrapperStyle} className={className}>
      <button
        type="button"
        style={summaryButtonStyle}
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-label={ariaLabel}
        onClick={toggle}
      >
        <span style={summaryLeftStyle}>
          <span aria-hidden="true" style={chevronStyle(isOpen)}>
            ▶
          </span>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{summary}</span>
        </span>
        {trailing ? <span style={{ flex: '0 0 auto' }}>{trailing}</span> : null}
      </button>
      {isOpen ? (
        <div id={panelId} style={panelStyle}>
          {children}
        </div>
      ) : null}
    </div>
  );
}

export default Disclosure;
