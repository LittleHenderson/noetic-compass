import { useEffect, useState } from 'react';

/** localStorage flag — set once the intro has played so it never shows again. */
const INTRO_SEEN_KEY = 'nc_intro_seen_v1';

/**
 * Cinematic intro:
 *  0.0s  — black screen
 *  0.0s  — tagline starts far away, small + blurred
 *  ~1.6s — tagline reaches full size
 *  1.6s  — pulses softly for ~3s
 *  4.6s  — swiftly slides up + fades out
 *  ~5s   — children (the app) takes over
 *
 * Shows a "Skip" button so returning users aren't trapped.
 * Persists a localStorage flag so it only plays on the first visit.
 */
export function CinematicIntro({ children }: { children: React.ReactNode }) {
  const [phase, setPhase] = useState<'hidden' | 'flying' | 'pulsing' | 'leaving' | 'done'>(
    () => (localStorage.getItem(INTRO_SEEN_KEY) === '1' ? 'done' : 'hidden'),
  );

  useEffect(() => {
    if (phase !== 'hidden') return;
    // Start flying on next frame
    const t1 = setTimeout(() => setPhase('flying'), 60);
    // After the fly-in animation (~1.6s), start pulsing
    const t2 = setTimeout(() => setPhase('pulsing'), 1700);
    // After ~3s of pulsing, start leaving
    const t3 = setTimeout(() => setPhase('leaving'), 4700);
    // After slide-up animation finishes, mark done
    const t4 = setTimeout(() => {
      setPhase('done');
      localStorage.setItem(INTRO_SEEN_KEY, '1');
    }, 5400);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
    };
  }, [phase]);

  function handleSkip() {
    localStorage.setItem(INTRO_SEEN_KEY, '1');
    setPhase('done');
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
        <h1
          className={`intro-tagline px-4 text-center font-bold italic ${
            phase === 'hidden' ? 'intro-phase-hidden' : ''
          } ${phase === 'flying' ? 'intro-phase-flying' : ''} ${
            phase === 'pulsing' ? 'intro-phase-pulsing' : ''
          } ${phase === 'leaving' ? 'intro-phase-leaving' : ''}`}
        >
          <span className="bg-gradient-to-r from-accent-teal to-accent-cyan bg-clip-text text-transparent">
            Measure How AI Thinks — Not Just What It Says
          </span>
        </h1>

        <button
          onClick={handleSkip}
          className="absolute bottom-6 right-6 rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 py-2 text-xs text-slate-400 hover:text-slate-200 hover:bg-white/[0.08] transition-colors"
        >
          Skip →
        </button>
      </div>

      {/* App stays mounted behind the overlay so it's ready when the intro finishes. */}
      {children}
    </>
  );
}
