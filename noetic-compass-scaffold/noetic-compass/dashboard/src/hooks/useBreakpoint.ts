import { useEffect, useState } from 'react';

/**
 * Tailwind-default breakpoint hook.
 *
 *   sm: ≥ 640px   md: ≥ 768px   lg: ≥ 1024px   xl: ≥ 1280px
 *
 * `current` is the largest matching named breakpoint. Below 640px we still
 * report 'sm' (treat sub-sm as sm for mobile semantics).
 *
 * Uses window.matchMedia listeners (one per threshold) rather than reading
 * window.innerWidth on every resize event.
 */
export type Breakpoint = 'sm' | 'md' | 'lg' | 'xl';

interface BreakpointState {
  current: Breakpoint;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
}

const QUERIES: { bp: Exclude<Breakpoint, 'sm'>; query: string }[] = [
  { bp: 'md', query: '(min-width: 768px)' },
  { bp: 'lg', query: '(min-width: 1024px)' },
  { bp: 'xl', query: '(min-width: 1280px)' },
];

function computeBreakpoint(): Breakpoint {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    // SSR / non-DOM: assume desktop.
    return 'lg';
  }
  if (window.matchMedia('(min-width: 1280px)').matches) return 'xl';
  if (window.matchMedia('(min-width: 1024px)').matches) return 'lg';
  if (window.matchMedia('(min-width: 768px)').matches) return 'md';
  return 'sm';
}

export function useBreakpoint(): BreakpointState {
  const [current, setCurrent] = useState<Breakpoint>(() => computeBreakpoint());

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }
    const lists = QUERIES.map(({ query }) => window.matchMedia(query));
    const update = () => setCurrent(computeBreakpoint());
    update();
    // Modern API: addEventListener('change', ...). Fallback to addListener for
    // older Safari (pre-14). Symmetric in cleanup.
    lists.forEach((mql) => {
      if (typeof mql.addEventListener === 'function') {
        mql.addEventListener('change', update);
      } else if (typeof (mql as MediaQueryList).addListener === 'function') {
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        (mql as MediaQueryList).addListener(update);
      }
    });
    return () => {
      lists.forEach((mql) => {
        if (typeof mql.removeEventListener === 'function') {
          mql.removeEventListener('change', update);
        } else if (typeof (mql as MediaQueryList).removeListener === 'function') {
          // eslint-disable-next-line @typescript-eslint/no-deprecated
          (mql as MediaQueryList).removeListener(update);
        }
      });
    };
  }, []);

  return {
    current,
    isMobile: current === 'sm',
    isTablet: current === 'md',
    isDesktop: current === 'lg' || current === 'xl',
  };
}

export default useBreakpoint;
