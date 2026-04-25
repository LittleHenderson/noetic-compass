# Codex Build Directive — Temporal Cognitive Score (Audio Sonification)

**Generated:** 2026-04-25
**Repository:** `LittleHenderson/noetic-compass` at commit `96d215b` or later
**Companion:** `docs/CODEX_DEPLOY_DIRECTIVE.md` (deploy phase, runs AFTER this build phase)
**Authority:** `docs/design/cas_v7_5_multimodal_display_specification.md` Part 2 (the spec) + Part 6 Phases B-E (rollout phasing)

---

## Why this directive exists

The Multi-Modal Cognitive Display has two halves:

1. **Radial Architecture Display** — visual, SVG-based, **already built and tested** (19 passing tests in `dashboard/src/components/RadialArchitectureDisplay.test.tsx`)
2. **Temporal Cognitive Score** — auditory, sonification of cognitive operations, **specification-only with zero implementation files**

User wants the full multi-modal experience live. This directive builds the auditory half so both can ship together.

**Estimated scope:** 4-8 hours of focused work. Phase B (minimum viable sonification) only — Phases C/D/E (advanced features) stay roadmap.

---

## Spec authority and naming discipline (read first)

**Source of truth:** `docs/design/cas_v7_5_multimodal_display_specification.md` Part 2 (lines 106-217). Every musical mapping must trace to a formal CAS primitive. No improvised mappings, no aesthetic choices outside what the spec specifies.

**Naming discipline (load-bearing per `CLAUDE.md`):**
- ✅ Public-facing UI: **Temporal Cognitive Score** (always)
- ❌ Never use in user-facing surfaces: aesthetic-heritage names, mystical labels, "music of the soul" type framing
- ✅ Performance terminology is fine where the spec uses it (fermata, staccato, legato, marcato, allegro, andante, etc.)
- ✅ Use authoritative Noetic names (Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect)

---

## What to build (Phase B minimum viable scope)

### 1. Audio engine setup

**Library:** **Tone.js** (per spec Part 2 line 212 — non-negotiable, this is the spec's choice)

```bash
cd noetic-compass-scaffold/noetic-compass/dashboard
npm install tone
```

Tone.js is a Web Audio API wrapper providing transport control, instrument synthesis, and timing primitives. Standard choice for browser-based music rendering.

### 2. Core mapping module

**Create:** `dashboard/src/lib/temporal_score/cas_to_audio.ts`

Translates a `CognitiveStateData` object (same input type the Radial Architecture Display consumes) into an audio score. Must implement the formal mapping specifications from Part 2 of the spec:

**Pitch mapping (Noetics → scale degrees):**

```typescript
// Use C major as default tonic; key is overridden by Mind-architecture aggregate (Phase C)
const NOETIC_TO_SCALE_DEGREE: Record<NoeticIndex, number> = {
  0: 0,   // Idea — tonic (do, e.g. C4)
  1: 2,   // Mind — second (re, D4)
  2: 4,   // Positive — major third (mi, E4)
  3: 3,   // Negative — minor third (me / Eb4)
  4: 5,   // Vibration — fourth (fa, F4)
  5: 7,   // Female — fifth (sol, G4)
  6: 6,   // Male — diminished fifth (solb / Gb4)
  7: 9,   // Rhythm — sixth (la, A4)
  8: 11,  // Above/Cause — seventh / leading tone (ti, B4)
  9: 12,  // Below/Effect — octave (do above, C5)
};
```

Document the rationale inline (involution pairs render as chromatic dissonances per spec line 139): `^2↔^3` major/minor third tension, `^5↔^6` tritone, `^8↔^9` leading-tone-to-tonic resolution.

**Domain mapping (staves vertical position):**

Top stave: P (Principled). Second: C (Cognitive). Third: E (Evaluative). Bottom: O (Operational). Vertical ordering reflects domain descent (P ≻ C ≻ E ≻ O).

**Register mapping (dynamics / expression marks):**

```typescript
const REGISTER_TO_EXPRESSION = {
  T: { type: 'fermata', sustainMultiplier: 2.5, articulation: 'sustained' },
  A: { type: 'staccato', sustainMultiplier: 0.4, articulation: 'detached' },
  f: { type: 'legato', sustainMultiplier: 1.0, articulation: 'connected' },
  E: { type: 'marcato', sustainMultiplier: 0.9, attack: 1.4, articulation: 'accented' },
};
```

(Lowercase `|f` for Affective register — preserve throughout per `CLAUDE.md`.)

**Drive mapping (tempo in BPM):**

```typescript
const DRIVE_TO_TEMPO_BPM = {
  F1: { name: 'Largo', bpm: 50, character: 'ceremonial' },
  F2: { name: 'Andante con moto', bpm: 84, character: 'walking, considered' },
  F3: { name: 'Allegro vivace', bpm: 152, character: 'energetic' },
  F4: { name: 'Cantabile', bpm: 76, character: 'singing' },
  F5: { name: 'Con forza', bpm: 120, character: 'driving' },
  F6: { name: 'Tempo giusto', bpm: 100, character: 'strict time' },
  F7: { name: 'Scherzando', bpm: 138, character: 'playful' },
};
```

The dominant Drive (highest activation in cognitive state) sets the score's BPM.

**Instrument mapping (Domain → instrument family):** per spec Part 2 line 213, initial candidates:
- P (Principled): strings — Tone.js `Synth` with sustained envelope
- C (Cognitive): woodwinds — Tone.js `MonoSynth` with articulated envelope
- E (Evaluative): brass — Tone.js `FMSynth` with resonant envelope
- O (Operational): percussion — Tone.js `MembraneSynth` or `MetalSynth`

These are reasonable defaults from the spec. Phase C may revisit; Phase B uses these.

**Lacunarity → rests:**
- Domain with zero activation → bar rest on that stave for the duration
- Register-pair voids → consistent rest pattern at that register's beat subdivisions
- Register-selective voids → rests in specific Noetic×Domain cells

### 3. Score generation function

```typescript
export function generateTemporalScore(
  cognitiveState: CognitiveStateData,
  options: ScoreOptions = {}
): TemporalScore {
  // Determine BPM from dominant Drive
  // Determine instrument per Domain
  // Walk activations; for each active (Noetic, Domain, Register, Drive):
  //   - Pitch from Noetic
  //   - Stave from Domain
  //   - Expression from Register
  //   - Render rests where lacunarity present
  // Return a TemporalScore object: ordered events with timing, pitch, instrument, expression
}
```

`TemporalScore` is a structured representation Tone.js can play. Keep it serializable so the same data can drive both playback and visual score rendering (Phase C+).

### 4. Playback component

**Create:** `dashboard/src/components/TemporalCognitiveScore.tsx`

UI component with:
- **Play / Pause / Stop controls** (standard transport)
- **Scrub bar** showing playback position
- **Volume control** (Tone.js master volume)
- **Tempo override** (slider — user can override BPM if they want to slow down for analysis)
- **Stave display panel** showing which Domain is currently sounding (visual companion to the audio)
- **Synchronized highlight** with `RadialArchitectureDisplay` — when a Domain plays, that Domain's segment in the Radial Display can pulse (cross-modal link per spec Part 3)

```typescript
interface TemporalCognitiveScoreProps {
  cognitiveState: CognitiveStateData;
  onPlayStateChange?: (state: 'playing' | 'paused' | 'stopped') => void;
  onCurrentDomainChange?: (domain: Domain | null) => void;  // for cross-modal sync
}
```

### 5. Cross-modal integration with Radial Architecture Display

When user hits play on the Temporal Cognitive Score:
- Radial Display can highlight the currently-sounding Domain (subtle pulse or border glow)
- Hovering a Noetic petal in the Radial Display can cue the corresponding pitch in the score

Implement with shared state (React context or props lift). Don't tightly couple the components — both should work standalone, but offer the cross-modal hook when mounted together.

### 6. Accessibility (load-bearing per spec Part 5)

- **Visual transcript:** the entire score must have a text-based equivalent. List of operations sounding at each beat, with pitch / Domain / Register / Drive labeling. Screen readers must be able to navigate the score sequentially.
- **Captions:** when a note plays, a visible label can show "P stave, ^2 Positive (mi), |T Transcendent, F2 Wisdom"
- **Volume controls always accessible** via keyboard
- **No auto-play** — user always initiates playback. Silent until user presses play. (Preserves accessibility, avoids startle, complies with browser autoplay policies.)
- **Pause-able mid-playback** — accessibility requirement
- **No flashing visuals tied to audio** — avoid photosensitive epilepsy triggers

### 7. Tests

**Create:** `dashboard/src/lib/temporal_score/cas_to_audio.test.ts` (~20-30 tests)

Required coverage:

- All 10 Noetic→pitch mappings correct (one test per Noetic)
- All 4 Register→expression mappings correct
- All 7 Drive→BPM mappings correct
- Empty cognitive state → empty score (no notes, no errors)
- Single-Noetic activation → single note at correct pitch on correct stave
- Lacunarity in a Domain → rest on that stave
- Involution pair tension renders as expected dissonant interval
- BPM determined by dominant Drive
- Score is deterministic (same input → same output, byte-for-byte score JSON)
- Score JSON is serializable (round-trip JSON.stringify / JSON.parse)

**Create:** `dashboard/src/components/TemporalCognitiveScore.test.tsx` (~10-15 tests)

Required coverage:

- Component renders without errors
- Play / Pause / Stop controls present and keyboard-accessible
- Volume control present
- Visual transcript renders
- No auto-play (silent on mount)
- Cross-modal callback fires on Domain change during playback
- Cleanup on unmount (Tone.js Transport stops, no hanging audio)

Use Vitest + React Testing Library (the dashboard's existing test stack). Mock Tone.js where appropriate to keep tests fast.

### 8. Update site copy

After build lands:

- **`docs/NOETICCOMPASS_COM_FEATURE_SPEC.md`:** update the "/visualization" section to say Temporal Cognitive Score is LIVE (Phase B) rather than roadmap. Keep Phases C-E (advanced features) as roadmap.
- **`docs/CODEX_DEPLOY_DIRECTIVE.md`:** strike the "Coming Soon placeholder for Temporal Cognitive Score" section. The component is now mountable.
- **`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`** and **CLAUDE.md:** no changes needed (these are framework docs, not feature inventories).

---

## What's deliberately out of scope (Phase B only)

Do NOT build the following — these are Phase C/D/E roadmap and would scope-creep this directive:

- ❌ Score export to MIDI / WAV / MP3 / MusicXML (Phase C — needs separate audio export pipeline)
- ❌ Visual musical staff notation rendering using VexFlow or similar (Phase C — distinct from audio playback)
- ❌ Mind-architecture-derived key signature algorithm (Phase D — research question, see spec Part 7)
- ❌ Real-time generative variation as user interacts with assessment (Phase E)
- ❌ Multi-instrument orchestration beyond the four Domain instruments (Phase D — composition pedagogy)
- ❌ Mood/key inference from drive balance (Phase D — research)

Document these as "future work" comments in the source where appropriate. Do not stub them out.

---

## File structure (target)

```
dashboard/
  src/
    lib/
      temporal_score/
        cas_to_audio.ts            # core mapping + score generation
        cas_to_audio.test.ts       # unit tests
        types.ts                   # TemporalScore, ScoreOptions, etc.
        constants.ts               # NOETIC_TO_SCALE_DEGREE, etc.
    components/
      TemporalCognitiveScore.tsx        # playback UI component
      TemporalCognitiveScore.test.tsx   # component tests
      TemporalCognitiveScore.css        # styles
```

Pair with existing `RadialArchitectureDisplay.tsx` and `RadialArchitectureDisplay.test.tsx` patterns.

---

## Verification before commit

- [ ] `npm install` succeeds (Tone.js installed cleanly)
- [ ] `npm run build` succeeds (TypeScript clean, no errors)
- [ ] `npm test -- temporal_score` passes (all new tests green)
- [ ] `npm test` passes the full suite (no regressions in Radial Display or other components)
- [ ] `npm run lint` clean
- [ ] Lighthouse Accessibility score >90 on a page mounting the component (verify after deploy)
- [ ] Manual playback test: load a sample cognitive state fixture, hit play, hear distinct pitches per Noetic, distinct stave-instrument per Domain, expression marks audibly distinguishable per Register
- [ ] No auto-play on page load (silent by default)
- [ ] Cross-modal sync with RadialArchitectureDisplay verified in browser

---

## Commit + handoff to deploy

When build verifies green:

```bash
git add dashboard/src/lib/temporal_score/ \
        dashboard/src/components/TemporalCognitiveScore.tsx \
        dashboard/src/components/TemporalCognitiveScore.test.tsx \
        dashboard/src/components/TemporalCognitiveScore.css \
        dashboard/package.json dashboard/package-lock.json \
        docs/NOETICCOMPASS_COM_FEATURE_SPEC.md \
        docs/CODEX_DEPLOY_DIRECTIVE.md
git commit -m "feat: Temporal Cognitive Score Phase B — audio sonification per CAS v7.5 multi-modal spec

Tone.js-based browser audio rendering of cognitive operations as a
4-stave musical score (one stave per Processing Domain). Implements
Phase B (minimum viable sonification) per docs/design/cas_v7_5_multimodal_display_specification.md.

- Noetic → scale degree (chromatic dissonance for involution pairs)
- Register → expression mark (fermata / staccato / legato / marcato)
- Drive → tempo (Italian markings, dominant drive sets BPM)
- Domain → instrument family + stave position (P/C/E/O top-to-bottom)
- Lacunarity → rests
- Cross-modal sync with RadialArchitectureDisplay
- Accessibility: visual transcript, no auto-play, keyboard controls

Phases C-E (export formats, score notation rendering, key signature
algorithm, generative variation) remain roadmap.

Site spec + deploy directive updated to mark this LIVE.

Co-Authored-By: Codex <noreply@openai.com>"
git push origin master
```

After this commit lands, proceed with `docs/CODEX_DEPLOY_DIRECTIVE.md` Phase 1 (deploy the dashboard) — the dashboard now ships with both halves of the multi-modal display.

---

## What to do if Codex hits blockers

- **Tone.js build errors:** check Vite config — Tone.js needs proper ESM handling. Refer to Tone.js docs for Vite-specific setup.
- **AudioContext requires user gesture:** browsers require a user click before AudioContext starts. Make sure play button initiates the AudioContext (Tone.js handles this if you call `Tone.start()` in the play handler).
- **Mock Tone.js for tests:** unit tests should NOT actually play audio. Use Vitest mocks for `Tone.Transport`, `Tone.Synth`, etc.
- **Cross-browser issues:** verify in Chrome, Firefox, Safari. Tone.js generally handles this but Safari has historically had quirks with Web Audio.
- **Performance:** for large cognitive states (full 40-state activations), score generation should be <100ms. Profile if it's slower.
- If a blocker takes >30 minutes: stop, report status, await direction.

---

## Anti-patterns to avoid

- ❌ Implementing without reading Part 2 of the spec — every musical mapping has a formal CAS rationale, don't substitute aesthetic choices
- ❌ Auto-playing audio on page load (accessibility violation, browser policy violation, startles users)
- ❌ Using stock music or sample loops — every sound must be synthesized from the cognitive state
- ❌ Skipping the visual transcript (accessibility requirement is non-negotiable)
- ❌ Hardcoding instrument or tempo choices not derived from cognitive state
- ❌ Tight-coupling TemporalCognitiveScore to RadialArchitectureDisplay — both must work standalone
- ❌ Adding voice-acting / spoken-word elements (out of spec scope)
- ❌ Calling it "music" in marketing surfaces — "Temporal Cognitive Score" or "auditory cognitive signature" stays technical

---

## Reporting

When build commits:

- Commit hash
- New file list with line counts
- Test counts before/after
- Tone.js version pinned in package.json
- Audio playback verification: which sample cognitive state fixture was used, browser tested in
- Accessibility verification: visual transcript renders, keyboard navigation works, no auto-play
- Cross-modal sync verification: yes/no with method

Then immediately proceed to `docs/CODEX_DEPLOY_DIRECTIVE.md` for the deploy phase. Both halves of the multi-modal display now deploy together.

---

## Source of truth

- This document: `docs/CODEX_BUILD_TEMPORAL_COGNITIVE_SCORE.md`
- Spec: `docs/design/cas_v7_5_multimodal_display_specification.md` Part 2
- Companion deploy directive: `docs/CODEX_DEPLOY_DIRECTIVE.md`
- Site copy: `docs/NOETICCOMPASS_COM_FEATURE_SPEC.md`
- Naming discipline: `CLAUDE.md`
- Existing visual half (pattern reference): `dashboard/src/components/RadialArchitectureDisplay.tsx`
