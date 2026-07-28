# The Cognitive Circuit Grimoire — Build Specification

**This file is authoritative.** Every chapter writer reads it before writing a
word. It exists because 24 chapters written independently will not cohere unless
the voice, notation, safety posture, and structure are pinned down first.

---

## 1. What this book is

A bench manual for cognitive circuit engineering. It takes the CAS component
library (resistors, capacitors, diodes, the Cognitive Junction Transistor) and
the TKS symbolic system, and builds working boards from them — for desire
operations, hyperstition, Overton progression, deprogramming, hypnosis,
advertising analysis, psychological-warfare *defense*, and self-programming.

It sits alongside three companion volumes and must not contradict them:

| Book | Owns |
|---|---|
| *Thinking in Cognitive Architecture* | the CAS framework itself — the 10 Noetics, 4 Domains, 7 Drives, 4 Registers |
| *CAS PCBA Engineer* | the component library and the five reference CCBs |
| *Reality Engineering* | TKS — the 40 Elements, 7 Foundations, 12 Prerequisites |
| **this book** | the *grimoire*: applied boards for operations the others do not cover |

Where this book restates something the others own, it restates it **correctly**
and cites them. It never redefines a primitive.

---

## 2. Voice

Read `manuscript/02_preface.md` before writing. Match it.

- **Second person, direct.** "You will build," not "one might construct."
- **Bench-manual register.** This is a manual for someone with the book open
  beside the work, not an essay about the work.
- **Concrete before abstract.** Open a section with the thing, then explain it.
- **No hedging into mysticism.** The claim is structural, not supernatural. A
  candle is a resistor because it constrains attention, not because of any
  occult property of wax.
- **No hype.** Never "revolutionary," "unlock," "secret," "they don't want you
  to know." The material is interesting enough without a carnival barker.
- **Earned authority.** State the parameter, state why it has that value, state
  what breaks at other values. Every number is a design choice with a reason.

**Sentence rhythm matters.** Vary length. A long explanatory sentence that
carries a chain of reasoning, then a short one. Like that.

---

## 3. Notation — non-negotiable

The full CAS spec lives in the repo's `CLAUDE.md`. Read it. The parts that get
broken most often:

- **Canonical Noetic names, verbatim.** `^0` Idea, `^1` Mind, `^2` Positive,
  `^3` Negative, `^4` Vibration, `^5` Female, `^6` Male, `^7` Rhythm,
  `^8` Above/Cause, `^9` Below/Effect. Never rename a Noetic to its function.
- **`^3` Negative is VISCERAL, not analytical.** Aversion, repulsion,
  can't-stomach-it. Analytical critique is `^6` Male. This drift has already
  shipped in this codebase once and was caught; do not reintroduce it.
- **`^8` Above/Cause is associative TRIGGERING, not deductive reasoning.**
  "That reminds me," not "therefore."
- **State literal:** `^n^D_{Fk}|R` — Noetic, Domain (P/C/E/O), Drive (F1–F7),
  Register (T/A/f/E). Register is optional.
- **Operators (v7.7):** `+` co-presence, terms stay distinct. `×` genuine
  integration, requires a *named emergent result*. `|⟨A,f,T⟩` register-set
  occupancy, no operational claim. Same-Noetic multi-register with `×` and no
  named result is **invalid** — use `+` or `|⟨…⟩`.
- **`|` introduces the Register.** Never use it as a label or gloss. `F3|Vitality`
  is a syntax error, not a helpful annotation.
- **Domain descent:** P ≻ C ≻ E ≻ O. `×` may not ascend. `^O × ^P` is invalid.
- **Involution pairs:** `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`. Self-dual: `^0`, `^1`,
  `^4`, `^7`. Drive inversions: F1↔F7, F2↔F6, F3↔F5; F4 self-dual.
- **β=∞ is a limit, not a value.** A validator rejects non-finite input. Write
  the idealization if you mean it, and say a real build uses a large finite gain.

Every CCDL listing you write must be one a validator would accept.

---

## 4. Safety posture — read this twice

Several chapters analyze coercive systems: MK-Ultra conditioning, hypnosis,
propaganda, advertising, Overton progression. **The framing is structural
analysis for detection, resistance, and reversal.** That is not a disclaimer
bolted on top; it is what the chapters actually do.

Rules, applied without exception:

1. **Analyze mechanism, never supply a protocol against a person.** Explain how
   a trigger-installation circuit is *architected* so a reader can recognize one.
   Do not write installation instructions, scripts, dosing, isolation schedules,
   or any step-by-step a person could run on someone else.
2. **Every coercive board ends with its counter-circuit**, and the counter gets
   equal or greater depth. CCB-MK ends in the Deprogramming Board. CCB-PW ends in
   the Hearts-and-Minds counter. CCB-ADV ends in consumer-side detection.
3. **Keep the `DETECTION-ONLY SCHEMATIC — DO NOT BUILD` banner** on any circuit
   whose purpose is to act on a non-consenting person. It is already in Ch16.
4. **Self-directed work is different.** CCB-SELF, self-hypnosis, and desire
   operations act on the operator's own mind with their own consent. Write those
   fully and practically.
5. **Historical cases stay historical and sourced.** MK-Ultra is declassified and
   documented; the Willie Lynch letter is of disputed authorship and must be
   labelled as such. Analyze what is on the record. Invent nothing.
6. **No medical or psychiatric claims.** No treating trauma, dissociation,
   addiction, or mental illness. Where a reader might be in real distress, say
   plainly: see a clinician; nothing here replaces care.

If a section cannot be written within these rules, write the analytical version
and say in the text why the operational version is absent.

---

## 5. Chapter structure — every chapter, same skeleton

```
# CHAPTER n
## Title
*Italic subtitle — what this chapter is for*

[Cold open: a concrete scene, object, or failure. 150-300 words. No throat-clearing.]

### n.1 … through n.k    (follow the TOC exactly; do not renumber)

> **Bench Note — <specific claim>.** [Used for the counterintuitive thing, the
> thing that breaks, or the check a reader should run by hand. 80-200 words.
> At least two per chapter, and they must earn their place.]

### Component / Parameter table   (every Part II and Part III chapter)

### Full CCDL listing             (every Part III chapter)

### Worked example                (every Part III chapter — real numbers, carried through)

### Failure modes                 (table: mode | mechanism | what you observe | fix)

### Test points                   (TP1-TP4, what each reads, expected range)

### What This Chapter Established  (5-8 bullets, each a claim not a summary)

### Exercises                      (4-8, with answers in Appendix E)
```

---

## 6. Chapter map and word targets

Total target: **110,000–120,000 words.** Current: 23,737. Sections marked
*(draft exists)* must be expanded and corrected, not discarded — the existing
prose carries the voice.

### Front matter — 4,000
Title, dedication, epigraph, preface *(draft exists)*, How to Use This Grimoire,
Quick-Start: If You Only Have One Hour.

### Part I — Foundations — 24,500
| Ch | Title | Target |
|---|---|---|
| 1 | The Landscape *(draft exists)* | 3,500 |
| 2 | CAS Notation in One Chapter | 6,000 |
| 3 | The Cognitive Junction Transistor | 5,000 |
| 4 | CAS Ohm's Law *(draft exists)* | 4,500 |
| 5 | St. John's Equation *(draft exists)* | 5,500 |

### Part II — The Component Library — 24,500
| Ch | Title | Target |
|---|---|---|
| 6 | Resistors *(draft exists)* | 4,000 |
| 7 | Capacitors | 4,500 |
| 8 | Diodes | 3,500 |
| 9 | Inductors | 3,000 |
| 10 | The CJT — Deep Dive | 5,000 |
| 11 | Special-Purpose Components *(draft exists)* | 4,500 |

### Part III — The Board Catalog — 42,500
| Ch | Title | Target |
|---|---|---|
| 12 | How to Read a CCB Schematic | 3,000 |
| 13 | CCB-D Desire *(draft exists)* | 6,000 |
| 14 | CCB-H Hyperstition *(draft exists)* | 4,500 |
| 15 | CCB-O Overton *(draft exists)* | 5,500 |
| 16 | CCB-MK / Deprogramming *(draft exists)* | 5,000 |
| 17 | CCB-HYP Hypnosis *(draft exists)* | 4,500 |
| 18 | CCB-ADV Advertising *(draft exists)* | 4,500 |
| 19 | CCB-PW / counter-circuit *(draft exists)* | 4,500 |
| 20 | CCB-SELF *(draft exists)* | 5,000 |

### Part IV — Operations — 16,000
| Ch | Title | Target |
|---|---|---|
| 21 | The RPM Prerequisite Gate *(draft exists)* | 3,500 |
| 22 | The Quantitative Table *(draft exists)* | 3,500 |
| 23 | St. John's Advanced Calibration *(draft exists)* | 4,000 |
| 24 | The Cognitive Safety Board *(draft exists)* | 5,000 |

### Appendices — 14,000
A CCDL Grammar · B Component Datasheets · C The 40 States Quick Reference ·
D Board Selection Guide · E Exercise Answers (**all of them, worked**) ·
F Glossary · G Failure-Mode Index · H The Quantitative Table Sheets ·
I Operation Log Templates · J Further Reading ·
K Safety Checklist · L Mathematical Foundations *(draft exists)*

---

## 7. Figures

Schematics are **drawn**, not ASCII. Every figure is TikZ, rendered by the same
LaTeX pipeline the companion volumes use. The existing ASCII in
`diagrams/board_assembly_drawings.md` is the *specification* for what to draw —
read it, then draw it properly.

Each Part III chapter needs, at minimum:
- a **block diagram** (signal path, left to right, labelled stages)
- a **full schematic** (components with reference designators, drawn symbols)
- an **assembly drawing** (board layout with test-point callouts and a BOM box)

Part II chapters need a component symbol plate and at least one characteristic
curve. Figure numbering: `Figure n-A`, `n-B`, … per chapter.

---

## 8. Hard rules

- Never invent a citation, a study, a statistic, or a historical quotation.
- Every parameter value is a design choice, stated as such — not a measurement,
  unless something was actually measured, in which case say what and how.
- Cross-references must resolve. If you cite "Chapter 9," Chapter 9 must contain
  what you say it does.
- Exercises get real answers in Appendix E. No "left to the reader."
- The reader has no electronics background and no CAS background. Both are
  taught in passing, at the point of need.
