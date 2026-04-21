# CAS v7.5 Multi-Modal Cognitive Display Specification

**Status.** Design specification. Resolves Decision 5 from `docs/working/cas_v7_5_rollout_plan.md` (Register heatmap visualization format). Phased implementation plan follows in Part 6.

**Purpose.** Specify the two-modality dashboard visualization system for CAS v7.5: a radial architecture display (visual) and a temporal cognitive score (auditory), formally corresponded via CAS algebra so the same cognitive phenomena render simultaneously as spatial and temporal patterns.

**Scope.** This document specifies visual structure, auditory structure, cross-modal correspondence, accessibility requirements, public-facing naming discipline, and a five-phase rollout. It does not specify implementation code; it defines what must be built.

---

## Overview

CAS v7.5 dashboard visualization renders cognitive architecture in two complementary modalities:

1. **Radial Architecture Display (visual)** — the static structural signature of a Mind's activation pattern across all four CAS axes (Noetic, Domain, Drive, Register).
2. **Temporal Cognitive Score (auditory)** — the dynamic unfolding of cognitive operations over time, rendered as a structured musical sequence.

These modalities are formally corresponded via CAS algebra: the same cognitive phenomena render simultaneously as spatial patterns and temporal patterns. Each visual element has an auditory counterpart derived by principled mapping from the framework, and vice versa.

---

## Design Principles

1. **Formal correspondence.** Every visual element has an auditory counterpart derived by principled mapping from CAS algebra. No aesthetic choices are arbitrary; every mapping is traceable to a specific framework primitive.
2. **Accessibility.** Both modalities stand alone for users who cannot access one or the other. A user with no audio access gets a complete visual + text representation; a user with no visual access gets a complete audio + text representation.
3. **Cross-modal interactivity.** Clicking visual elements plays their auditory counterparts; playback highlights visual regions in real-time. The two modalities are linked at the UI layer, not just at the data layer.
4. **Technical framing.** Public-facing naming is strictly technical. Aesthetic heritage may inform design, but never appears in marketing or product UI. Formal mathematical rationale is documented for every mapping choice.
5. **Export capability.** Both modalities are exportable. Visual exports are SVG and PNG; auditory exports include WAV, MP3, MIDI, and MusicXML; combined exports are video files with synchronized mandala animation and score playback.

---

## PART 1: Radial Architecture Display Specification

### Structure

The radial architecture display is a concentric-ring architecture organized around a central signature:

**Central region: Emergent activation summary glyph.**
A single central element that renders the dominant activation pattern at a glance. Specific glyph form to be determined during implementation; candidates include a compact multi-axis summary icon or a cross-axis heat summary.

**Ring 1 — Domains.**
The four Processing Domains positioned at compass points:
- **Principled (P)** at North (top).
- **Cognitive (C)** at East (right).
- **Evaluative (E)** at South (bottom).
- **Operational (O)** at West (left).

Domain descent (P ≻ C ≻ E ≻ O) is rendered as a ring brightness gradient: Principled is brightest, Operational dimmer. The gradient reflects structural precedence without requiring color alone (value differences work for colorblind users).

**Ring 2 — Noetics.**
Ten Noetic petals radiate from each Domain position. Each Domain has 10 petals representing the 10 Noetics (`^0` through `^9`). Petal length encodes activation strength for that Noetic × Domain combination.

Involution pairs (`^2 ↔ ^3`, `^5 ↔ ^6`, `^8 ↔ ^9`) are marked by shared color-family across paired petals, so involution relationships are visible at the Ring 2 level.

Total petals across all four domains: **40 petals = the 40 Cognitive States**.

**Ring 3 — Registers.**
Each petal is subdivided into four register quadrants:
- `|T` Transcendent — outer quadrant.
- `|A` Analytical — right quadrant.
- `|f` Affective — inner quadrant.
- `|E` Embodied — left quadrant.

Register involutions are positioned geometrically opposite:
- `|T ↔ |E` across the outer-inner axis.
- `|A ↔ |f` across the right-left axis.

Quadrant saturation encodes activation strength for that Register at that Noetic × Domain cell. Register voids render as empty (hollow) quadrants with distinctive dashed-outline styling, making absence diagnostically visible.

Total addressable cells: 4 Domains × 10 Noetics × 4 Registers = **160 Register-resolved state cells**.

**Ring 4 — Drives.**
Drive indicators around the display perimeter. Seven drive markers are positioned at petal-cluster boundaries. The dominant drive per cluster is highlighted. Drive inversion is signaled by color inversion of the relevant marker.

### Color Palette

Designed for colorblind accessibility and high-contrast print reproduction:

- **Domains:** four distinct hues using a colorblind-safe palette. Initial proposal: P = deep blue, C = green, E = warm orange, O = earth brown. Final hues subject to colorblind-palette analysis during implementation.
- **Noetics:** twelve-tone analog (specific colors TBD during implementation; must preserve involution-pair family grouping).
- **Registers:** encoded by value differences (not color alone). Approximate rendering: `|T` bright, `|A` medium, `|f` warm, `|E` dark. Value encoding ensures register distinctions are visible in grayscale and to colorblind users.
- **Activations:** saturation encodes strength. Desaturated = low activation; fully saturated = high activation.
- **Voids:** negative-space rendering (hollow with dashed outline). Registered voids are immediately visually distinguishable from low-activation states.
- **Inversions:** rendered as rotated or mirrored glyph variants of the non-inverted form.

### Interactive Behaviors

1. **Hover petal.** Reveals a cell-detail overlay showing: Noetic authoritative definition, Domain position, Register activation values, and the dominant drive for that cluster.
2. **Click petal.** Zooms into that Noetic's sub-mandala — an expanded view of the 16 Domain × Register combinations for that specific Noetic.
3. **Toggle register layers.** Dim all but one Register to see that Register's activation pattern across the full mandala. Four toggles (`|T`, `|A`, `|f`, `|E`) available.
4. **Toggle involution highlight.** Draw connecting lines across the mandala showing involution-pair relationships (Noetic pairs `^2↔^3`, `^5↔^6`, `^8↔^9`; Register pairs `|T↔|E`, `|A↔|f`).
5. **Composition trace.** Click two petals sequentially to visualize the resulting composed state with an animated flow from the two input cells to the resulting compound cell (per monoid composition rule).
6. **Lacunarity mode.** Inverted rendering where voids glow prominently and activations recede. Makes structural absence diagnostically visible at a glance.
7. **Comparison mode.** Two mandalas rendered side-by-side for comparative analysis (two Minds, or the same Mind at two time points).

### Technical Implementation

- **Rendering:** SVG-based for scalability and print quality.
- **Interactivity:** D3.js or equivalent library with full DOM interactivity.
- **Export formats:** SVG (print/vector), PNG (sharing), interactive HTML (web embedding).
- **Responsive:** scales from full-desktop to mobile tap-to-zoom. On mobile, cluster-level tap reveals zoomed Ring 2; secondary tap reveals Ring 3.
- **Accessibility:** alternative text-based view available; keyboard navigation supported; all information conveyed without color alone (value + shape encoding in parallel).

---

## PART 2: Temporal Cognitive Score Specification

### Structure

Musical staff notation rendering cognitive operations as a temporal sequence:

**Staff arrangement.** Four staves, vertically stacked, one per Processing Domain:
- Top staff: Principled (P).
- Second staff: Cognitive (C).
- Third staff: Evaluative (E).
- Bottom staff: Operational (O).

The vertical ordering reflects domain descent (P ≻ C ≻ E ≻ O). Readers of Western notation naturally read top-to-bottom as high-to-low abstraction, matching the CAS precedence.

### Formal Mapping Specifications

**Pitch (vertical position within each staff) — Noetics.**

Each Noetic maps to a specific scale degree:

| Noetic | Scale degree | Solfège |
| :--- | :--- | :--- |
| `^0` Idea | Tonic | do |
| `^1` Mind | Second | re |
| `^2` Positive | Major third | mi |
| `^3` Negative | Minor third | me |
| `^4` Vibration | Fourth | fa |
| `^5` Female | Fifth | sol |
| `^6` Male | Diminished fifth | solb |
| `^7` Rhythm | Sixth | la |
| `^8` Above/Cause | Seventh | ti |
| `^9` Below/Effect | Octave (do above) | do′ |

*Rationale.* The involution pairs render as chromatic dissonances requiring resolution: `^2 ↔ ^3` (major third vs. minor third) produces chromatic tension; `^5 ↔ ^6` (fifth vs. diminished fifth) produces the classic tritone dissonance; `^8 ↔ ^9` (leading tone vs. tonic octave) produces the strongest cadential tension in Western tonality. The scale itself encodes the Noetic algebra: Idea at the tonic, the sequence walking upward through the Noetics, Below/Effect completing the octave as a higher-order return to Idea-content.

**Dynamics (expression marks) — Registers.**

Each Register maps to a specific performance quality:

| Register | Expression mark | Performance character |
| :--- | :--- | :--- |
| `\|T` Transcendent | Fermata | Held, suspended time |
| `\|A` Analytical | Staccato (dots above notes) | Articulated, sequential precision |
| `\|f` Affective | Legato (slurs) | Flowing, connected phrases |
| `\|E` Embodied | Marcato (accent ∧) | Grounded, emphasized attacks |

*Rationale.* Each Register's phenomenological character corresponds to a distinct performance quality in musical practice: Transcendent suspends temporal flow (fermata); Analytical articulates each element precisely (staccato); Affective flows emotionally across notes (legato); Embodied emphasizes physical impact on each attack (marcato).

**Tempo / character markings — Drives.**

Each Drive maps to a specific Italian musical character indication:

| Drive | Tempo / character |
| :--- | :--- |
| F1 Unity | Largo, ceremonial (slow, reverent) |
| F2 Wisdom | Andante con moto (walking, considered) |
| F3 Vitality | Allegro vivace (energetic, alive) |
| F4 Connection | Cantabile (singing, flowing) |
| F5 Agency | Con forza (with strength, driving) |
| F6 Structure | Tempo giusto (strict time, structured) |
| F7 Purpose | Scherzando (playful, generative) |

*Rationale.* Each Drive's motivational character corresponds to a distinct musical temporal character established in Western classical convention. Readers/listeners familiar with musical terminology can identify the driving motivation at a glance.

**Harmonic structure.**

- **Simple operation** `^n^D_{F_k}|R` — renders as a single note with full attribution (pitch from Noetic, staff from Domain, tempo mark from Drive, expression mark from Register).
- **Composition** `^n^D × ^m^D` — renders as a two-note chord (simultaneous sounding).
- **Compound composition** `(^n × ^m) × ^p` — renders as a multi-note chord.
- **Involution tension** — renders as a dissonant interval requiring resolution (minor third / major third alternation; tritone; leading-tone tension).
- **Involution resolution** — renders as a consonant interval arriving after the dissonance.
- **Chord voicing** reflects domain arrangement: Principled notes on top of the chord stack, Operational on the bottom. Vertical chord layout mirrors domain descent.

**Melodic sequence.**

- **Fractal composition** `^n ∘ ^m ∘ ^p` — renders as a three-note melodic phrase in sequence.
- **Sequential operation order** renders as note order (leftmost first, rightmost last).
- **Recurring fractal patterns** render as motif repetition (classical composition technique: the same three-note figure returning at different staff positions as the composition unfolds).

**Rhythm.**

- `^7` Rhythm Noetic activation literally determines meter/pulse of that section of the score.
- **High `^7` activation:** strong metric regularity (clear downbeats, standard time signatures).
- **Low `^7` activation:** free/rubato time (no clear pulse, freely-flowing rhythm indication).
- **`^7` dominance** in a section produces strong rhythmic character audible as a clear groove.

**Rests (silences).**

Lacunarity renders as rests in the musical score:

- **Register-global voids** — entire bar rests on the affected domain stave (no activation anywhere in that domain for that section).
- **Register-pair voids** — silence in specific beats corresponding to the voided Register axis (e.g., all `|T` cells inactive produces consistent rest pattern across all domains at the `|T` subdivision).
- **Register-selective voids** — rests only in specific Noetic × Domain cells.
- **Register-involution imbalance** — weak or ghost notes rather than full rests (the register on one side of the `|T↔|E` or `|A↔|f` involution is active but weak; the other side is silent).

**Key signature.**

- Overall Mind architecture sets the key.
- Dominant drive determines major/minor modality (drives F3/F5/F7 tend toward major; F1/F2/F4/F6 may produce modal or minor colorings).
- Register balance determines modal flavor (Ionian, Dorian, Phrygian, etc., depending on which register pairs dominate).
- Mind pattern over the assessment window establishes the home key as a weighted aggregate.

Specific key-signature algorithm is a research question for implementation (see Part 7).

### Sonification Implementation

- **Engine:** Tone.js (web audio) for browser playback.
- **Instrument mapping:** four instrument families for four Domains. Initial candidates: strings for P (sustained, abstract), woodwinds for C (articulated, logical), brass for E (emotive, resonant), percussion for O (grounded, kinesthetic). Alternative candidate: all-tonal unified instrument across domains distinguished by pitch range. Decision deferred to musical prototyping (see Part 7).
- **Tempo:** BPM set by dominant Drive's character marking.
- **Duration:** cognitive operation duration determined by operation complexity (simple `^n^D_{F_k}` shorter than compound `^n^D × ^m^D × ^p^D`).
- **Export formats:** WAV, MP3, MIDI (for users who want to edit or remix), standard score notation (PDF and MusicXML for musicians).

---

## PART 3: Multi-Modal Integration

### Cross-Modal Interactivity

1. **Click mandala region** → plays the corresponding score passage.
2. **Playback position** → highlights the corresponding mandala region in real-time.
3. **Involution pair selection** → visualizes geometric symmetry AND plays the dissonant interval requiring resolution.
4. **Composition trace** → animates mandala flow AND plays the harmonic progression (two input cells sounding in sequence, then compound cell sounding as resolution).
5. **Lacunarity mode** → dims mandala activations AND mutes score activations, leaving voids and silences prominent in both modalities simultaneously.

### Synchronized Playback

- **Combined view mode:** mandala and score are rendered side-by-side.
- **Playback cursor** traverses the score timeline.
- **Mandala elements** pulse in synchrony with their sonification (visual highlight on the Register quadrant currently sounding).
- **User controls:** pause, scrub to any point, loop any section.
- **"Perform this signature" button** plays the full assessment as a continuous piece, walking through the operations in sequence with synchronized visualization.

### Export Formats

- **Static image:** full mandala as SVG / PNG.
- **Animated:** mandala pulse animation as video.
- **Audio:** sonification as audio file (WAV, MP3).
- **Combined:** video file with synchronized mandala animation and score playback.
- **Research format:** data file (JSON or CSV) with all axis values for external analysis (R, Python, MATLAB, etc.).

---

## PART 4: Technical Naming Discipline

### Public-Facing Names

All product UI, marketing material, public documentation, and regulator-facing documents use strictly technical names:

- "Radial Architecture Display" — never "Mandala."
- "Temporal Cognitive Score" — never "Cognitive Symphony."
- "Multi-Modal Cognitive Signature" — never "Mind's Song."
- "Sonification Engine" — never "Mind Music Generator."

Additional naming guardrails:
- Prefer "cognitive pattern" over "cognitive energy."
- Prefer "activation signature" over "cognitive aura."
- Prefer "structural resonance" over "vibrational harmony."
- Prefer "synchronized rendering" over "multi-sensory experience."

### Internal Development Names

The internal team may use whatever framing makes development natural (informal nicknames, design-language metaphors, etc.). These are permitted in internal docs, code comments, and design discussions, but **never** surface in public artifacts.

### Rationale

Public framing maintains CAS's position as a rigorous cognitive architecture analysis framework. Aesthetic heritage informs design but never marketing. Every visual and auditory choice must be traceable to a formal CAS mapping specification that can be defended as mathematically motivated, not aesthetically motivated.

This discipline is enforced at code-review and documentation-review time. Artifacts that drift into woo-woo language are blocked pending rename.

---

## PART 5: Accessibility Requirements

- **Alternative text-based view for screen readers.** Every visual cell has a text label; every audio element has a text transcript.
- **Transcript / description view of audio content.** Users who cannot hear the sonification can read the structural content in text form.
- **Keyboard navigation throughout.** Every interactive behavior accessible via keyboard, not only mouse/touch.
- **High-contrast mode available.** Toggle for users with low vision.
- **Language-independent core visualization.** No text required in the core mandala or score rendering; labels are overlays that can be disabled or translated.
- **Reduced-motion option.** Static rendering for users with vestibular issues. Pulse animations can be disabled.
- **Dual-modality information access.** All information accessible via at least two modalities. Users who can't see get audio + text. Users who can't hear get visual + text.

---

## PART 6: Rollout Phasing

Given the scope of the multi-modal system, implementation is staged across the v7.5 integration timeline:

### Phase A — v7.5 minimum viable visualization (ships with v7.5 rollout completion)

- Static mandala rendering (Ring 1-4 structure).
- Basic interactive hover/click (reveal cell details; no composition tracing yet).
- Domain / Noetic / Register / Drive display at all four rings.
- Lacunarity void indication (empty quadrants with dashed outline).

Phase A is the v7.5 rollout dependency. The dashboard cannot be considered v7.5-complete without Phase A.

### Phase B — enhanced mandala

- Full interactive mandala (all behaviors from Part 1 Interactive Behaviors: toggle register layers, toggle involution highlight, composition trace animation, comparison mode).
- Involution visualization (connecting lines).
- Composition tracing with animated flow.
- Side-by-side comparison mode for two Minds or two time points.

### Phase C — auditory modality (sonification)

- Sonification engine implementation (Tone.js).
- Formal pitch / dynamic / tempo mapping per Part 2 specifications.
- Playback controls (play, pause, scrub, loop).
- Audio export (WAV, MP3).

### Phase D — multi-modal integration

- Synchronized playback (cursor traverses score; mandala pulses in sync).
- Cross-modal interactivity (click mandala plays score passage; playback highlights mandala).
- Combined export formats (video with synchronized animation and playback).
- Full multi-modal experience as described in Part 3.

### Phase E — advanced research features

- MIDI export for musicians wanting to edit/remix.
- Score notation export (PDF, MusicXML).
- Scientific audio analysis tools (spectrum analysis, rhythm extraction).
- Research-grade data export (JSON, CSV) with full axis values.

Each phase ships independently. Phase A is the v7.5 rollout minimum. Phases B-D deliver the complete multi-modal vision. Phase E is a research extension for external analytical use.

---

## PART 7: Research Questions for Implementation

Items requiring further development during implementation, not blockers for specification:

1. **Specific color mapping for Noetics.** Awaiting color-theory analysis against colorblind palettes. Must preserve involution-pair family grouping while remaining distinguishable for users with deuteranopia, protanopia, and tritanopia.
2. **Specific instrument choices for Domains.** Requires musical prototyping to test what actually sounds right in practice. Strings/woodwinds/brass/percussion is one candidate; unified-tonal-instrument-across-pitch-ranges is another.
3. **Score duration per cognitive operation.** Requires calibration against natural listening patterns. Too-short produces unintelligible staccato; too-long produces tedium.
4. **Key signature algorithm.** How to algorithmically determine "home key" from assessment data. Candidate: weighted aggregate of dominant-drive modality across the assessment window, with register balance modulating the mode.
5. **Genre / style conventions.** Should sonification sound classical? Ambient? Electronic? Culturally neutral? A default choice is needed, with user option to re-render in alternative styles for accessibility to different listeners.
6. **Rhythm notation edge cases.** What does near-zero `^7` sound like vs. near-maximum `^7`? The free-rubato vs. strong-groove spectrum needs specific implementation.
7. **Cross-modal timing calibration.** How closely should mandala animation track score playback? Millisecond-precise sync? Phrase-level sync? Section-level sync? Choice affects perceived cohesion.

These are engineering/design research questions to resolve during implementation, not blockers for this specification.

---

## Summary

CAS v7.5 dashboard visualization is a multi-modal system rendering cognitive architecture visually (radial architecture display) and temporally (sonification), with formal cross-modal correspondence derived from CAS algebra.

Full implementation ships across five phases. Phase A is the minimum viable visualization and is required for v7.5 rollout completion. Phases B-D deliver the complete multi-modal experience. Phase E is a research extension.

Public naming is strictly technical. Aesthetic heritage informs design without appearing in product marketing. Every visual and auditory choice is traceable to a formal CAS mapping specification.

All four CAS axes (Noetic, Domain, Drive, Register) are rendered in both modalities. Activations, involutions, compositions, and lacunarity all have specific visual and auditory encodings. The framework algebra governs the entire specification: visual structure and musical structure are two instantiations of the same underlying CAS algebra.
