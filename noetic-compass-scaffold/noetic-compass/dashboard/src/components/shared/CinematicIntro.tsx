import { useEffect, useState } from 'react';
import { BrandTagline } from './BrandTagline';
import { PatentPendingBadge } from './PatentPendingBadge';

/** localStorage flag — set once the user has pressed Skip. Bumped to v2 so
 *  returning users see the new floating/mega-pulse intro at least once. */
const INTRO_SEEN_KEY = 'nc_intro_seen_v2';

/**
 * Cinematic intro:
 *  0.0s  — black screen
 *  0.0s  — tagline starts far away, small + blurred
 *  ~1.6s — tagline reaches full size at center
 *  ~1.6s — drifts like an astronaut in space (floats forever) with strong
 *          pulsing glow. Stays on screen indefinitely until the user
 *          presses Skip.
 *
 * Shows a "Skip" button so users can dismiss the intro whenever they want.
 * Persists a localStorage flag on skip so it doesn't replay on next visit.
 */
export function CinematicIntro({ children }: { children: React.ReactNode }) {
  const [phase, setPhase] = useState<'hidden' | 'flying' | 'floating' | 'leaving' | 'done'>(
    () => (localStorage.getItem(INTRO_SEEN_KEY) === '1' ? 'done' : 'hidden'),
  );

  useEffect(() => {
    if (phase !== 'hidden') return;
    // Start flying on next frame
    const t1 = setTimeout(() => setPhase('flying'), 60);
    // After the fly-in animation (~1.6s), switch to endless floating. No
    // auto-advance past this — only the Skip button can dismiss the intro.
    const t2 = setTimeout(() => setPhase('floating'), 1700);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [phase]);

  function handleSkip() {
    localStorage.setItem(INTRO_SEEN_KEY, '1');
    setPhase('leaving');
    // After slide-up animation, fully unmount
    setTimeout(() => setPhase('done'), 700);
  }

  if (phase === 'done') {
    return <>{children}</>;
  }

  return (
    <>
      {/* Intro overlay — covers the whole viewport on top of the app */}
      <div
        className={`fixed inset-0 z-[9999] flex items-center justify-center bg-black transition-opacity duration-700 ${
          phase === 'leaving' ? 'opacity-0' : 'opacity-100'
        }`}
        style={{ perspective: '1200px' }}
      >
        <div
          className={`intro-tagline px-4 ${
            phase === 'hidden' ? 'intro-phase-hidden' : ''
          } ${phase === 'flying' ? 'intro-phase-flying' : ''} ${
            phase === 'floating' ? 'intro-phase-floating' : ''
          } ${phase === 'leaving' ? 'intro-phase-leaving' : ''}`}
        >
          <div className="flex flex-col items-center gap-5 text-center">
            <PatentPendingBadge />
            <BrandTagline variant="intro" align="center" />
          </div>
        </div>

        <button
          onClick={handleSkip}
          className="absolute bottom-6 right-6 rounded-lg border border-accent-teal/40 bg-accent-teal/10 px-5 py-3 text-sm font-semibold text-accent-teal hover:bg-accent-teal/20 hover:border-accent-teal/60 transition-colors shadow-lg shadow-accent-teal/20"
        >
          Skip →
        </button>
      </div>

      {/* App stays mounted behind the overlay so it's ready when the intro finishes. */}
      {children}
    </>
  );
}
