import { useEffect, useRef, useState } from 'react';

/**
 * useRippleAnimation
 * ------------------
 * Animates a brief "ripple" pulse when a target idea changes (e.g. an idea
 * was just inverted, or its edges recomputed). The hook injects a stylesheet
 * on first use defining the `idea-atlas-ripple` keyframe animation, and
 * exposes a per-id class accessor.
 *
 * Keyframe CSS (auto-injected, but documented here for parity):
 *
 *   @keyframes idea-atlas-ripple {
 *     0%   { box-shadow: 0 0 0 0 rgba(34, 211, 238, 0.55); }
 *     60%  { box-shadow: 0 0 0 14px rgba(34, 211, 238, 0); }
 *     100% { box-shadow: 0 0 0 0 rgba(34, 211, 238, 0); }
 *   }
 *   .idea-atlas-ripple-active { animation: idea-atlas-ripple 700ms ease-out 1; }
 *
 * Returns:
 *   rippleClass(id) → '' or the active animation class for the given id
 *   ripplePulse     → boolean that flips true at start and false at end
 */
export interface UseRippleAnimationResult {
  rippleClass: (ideaId: string) => string;
  ripplePulse: boolean;
}

const RIPPLE_DURATION_MS = 700;
const STYLE_ELEMENT_ID = 'idea-atlas-ripple-keyframes';
const ACTIVE_CLASS = 'idea-atlas-ripple-active';

const KEYFRAME_CSS = `
@keyframes idea-atlas-ripple {
  0%   { box-shadow: 0 0 0 0 rgba(34, 211, 238, 0.55); }
  60%  { box-shadow: 0 0 0 14px rgba(34, 211, 238, 0); }
  100% { box-shadow: 0 0 0 0 rgba(34, 211, 238, 0); }
}
.${ACTIVE_CLASS} { animation: idea-atlas-ripple ${RIPPLE_DURATION_MS}ms ease-out 1; }
`;

function injectStyles(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(STYLE_ELEMENT_ID)) return;
  const style = document.createElement('style');
  style.id = STYLE_ELEMENT_ID;
  style.textContent = KEYFRAME_CSS;
  document.head.appendChild(style);
}

export function useRippleAnimation(triggerIdeaId: string | null): UseRippleAnimationResult {
  const [ripplePulse, setRipplePulse] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const previousId = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Inject keyframe stylesheet once
  useEffect(() => {
    injectStyles();
  }, []);

  // Trigger ripple when triggerIdeaId changes to a non-null new value
  useEffect(() => {
    if (triggerIdeaId === null) {
      previousId.current = null;
      return;
    }
    if (triggerIdeaId === previousId.current) return;
    previousId.current = triggerIdeaId;

    setActiveId(triggerIdeaId);
    setRipplePulse(true);

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setActiveId(null);
      setRipplePulse(false);
      timerRef.current = null;
    }, RIPPLE_DURATION_MS);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [triggerIdeaId]);

  function rippleClass(ideaId: string): string {
    return ideaId === activeId ? ACTIVE_CLASS : '';
  }

  return { rippleClass, ripplePulse };
}

export default useRippleAnimation;
