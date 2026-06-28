/**
 * ViewToggle — switch between the IdeaAtlas view and the notation/diagram view.
 *
 * The toggle is the central UX affordance the user requested: two natural
 * representations of the same prediction, switchable in-place, with state
 * preserved across the toggle (selection, viewport, expand-collapse).
 *
 * State preservation contract (enforced by the parent IdeaAtlasView, not by
 * this component):
 *
 *   1. Viewport transform survives the toggle. If the user has zoomed into
 *      the upper-right of the atlas, switching to diagram view re-fits to
 *      bounds; switching back restores the prior atlas viewport.
 *   2. Selection survives the toggle. If the user has clicked an atlas node
 *      with id "^3^E_{F2}|A", toggling to diagram view highlights the
 *      corresponding diagram node(s) (looked up via
 *      `correspondence[atlas_id]`).
 *   3. The generation_id never changes during a toggle — both views are
 *      *of the same prediction*.
 */

import type { AtlasViewMode } from './types';

export interface ViewToggleProps {
  /** Currently active view. */
  mode: AtlasViewMode;
  /** Called when the user clicks the inactive view button. */
  on_change: (mode: AtlasViewMode) => void;
  /** Optional disable flag (e.g. while the diagram is loading). */
  disabled?: boolean;
  /** Optional class for the outer wrapper. */
  className?: string;
  /** Optional generation_id displayed for traceability. */
  generation_id?: string | null;
}

const ATLAS_LABEL = 'Idea Atlas';
const DIAGRAM_LABEL = 'Notation / Diagram';

const BUTTON_BASE: React.CSSProperties = {
  padding: '6px 14px',
  fontFamily: 'inherit',
  fontSize: 14,
  border: '1px solid var(--toggle-border, #2b3445)',
  background: 'var(--toggle-inactive-bg, transparent)',
  color: 'var(--toggle-inactive-fg, #94a3b8)',
  cursor: 'pointer',
};

const BUTTON_ACTIVE: React.CSSProperties = {
  background: 'var(--toggle-active-bg, #22d3ee)',
  color: 'var(--toggle-active-fg, #0b1320)',
  fontWeight: 600,
};

const BUTTON_LEFT: React.CSSProperties = {
  borderTopLeftRadius: 6,
  borderBottomLeftRadius: 6,
  borderRight: 'none',
};

const BUTTON_RIGHT: React.CSSProperties = {
  borderTopRightRadius: 6,
  borderBottomRightRadius: 6,
};

export function ViewToggle(props: ViewToggleProps) {
  const { mode, on_change, disabled = false, className, generation_id } = props;

  const handle_atlas = () => {
    if (disabled || mode === 'atlas') return;
    on_change('atlas');
  };

  const handle_diagram = () => {
    if (disabled || mode === 'diagram') return;
    on_change('diagram');
  };

  return (
    <div
      className={className ?? 'idea-atlas-view-toggle'}
      role="tablist"
      aria-label="Switch between Idea Atlas and Notation Diagram views"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 12,
      }}
    >
      <div style={{ display: 'inline-flex' }}>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'atlas'}
          aria-controls="idea-atlas-view"
          tabIndex={mode === 'atlas' ? 0 : -1}
          onClick={handle_atlas}
          disabled={disabled}
          style={{
            ...BUTTON_BASE,
            ...BUTTON_LEFT,
            ...(mode === 'atlas' ? BUTTON_ACTIVE : {}),
          }}
          data-testid="view-toggle-atlas"
        >
          {ATLAS_LABEL}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'diagram'}
          aria-controls="diagram-view"
          tabIndex={mode === 'diagram' ? 0 : -1}
          onClick={handle_diagram}
          disabled={disabled}
          style={{
            ...BUTTON_BASE,
            ...BUTTON_RIGHT,
            ...(mode === 'diagram' ? BUTTON_ACTIVE : {}),
          }}
          data-testid="view-toggle-diagram"
        >
          {DIAGRAM_LABEL}
        </button>
      </div>

      {generation_id ? (
        <span
          style={{
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            fontSize: 11,
            color: 'var(--toggle-trace-fg, #64748b)',
          }}
          title="generation_id (1:1 mapping to the prediction that produced this view)"
          data-testid="view-toggle-generation-id"
        >
          gen={generation_id.slice(0, 8)}
        </span>
      ) : null}
    </div>
  );
}

export default ViewToggle;
