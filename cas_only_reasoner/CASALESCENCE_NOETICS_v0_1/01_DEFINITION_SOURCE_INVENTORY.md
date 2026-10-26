# 01 — Definition and source inventory

Purpose: say exactly which documents define the Noetics for this study, which version of each was used, and what is not used.

## 1. The governing source

| Item | Value |
|---|---|
| File | `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` |
| Section | Clarification 1, "The Ten Noetics — Authoritative Definitions" |
| Last commit touching the file | `1c8531ea` (2026-04-21, CAS v7.7) |
| File sha256 on 2026-10-04 | `cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880` |
| Working-tree state | unmodified |
| What the file says about its own source | "verbatim from the Tootra Math Handbook" |

The ten definitions, copied character for character:

- `^0` **Idea** — All things in and outside the Mind.
- `^1` **Mind** — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
- `^2` **Positive** — An Idea the Mind has an affinity for and is attracted toward.
- `^3` **Negative** — An Idea the Mind is adverse to and repelled by.
- `^4` **Vibration** — The degree to which an Idea resonates with the Mind, its impression.
- `^5` **Female** — A Mind impregnated with an Idea, the Ideas a Mind is composed of.
- `^6` **Male** — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
- `^7` **Rhythm** — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- `^8` **Above/Cause** — An Idea that triggers a different Idea than itself to come to Mind.
- `^9` **Below/Effect** — The Idea brought to Mind by an Above/Cause trigger.

The set is ten. The names are Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect. Clarification 3 of the same file says there is no alternative naming scheme.

## 2. Supporting sections of the same file that this study uses

| Section | Used for |
|---|---|
| Clarification 2, Universal Applicability Test | A description of a Noetic must fit human, AI, biological and hypothetical minds alike. Cases may involve any of these. |
| Clarification 4, structural language | Labels and guidance use the verbs of the definitions: affinity for, attracted toward, adverse to, repelled by, resonates with, impregnated with, triggers, brought to Mind. |
| Clarification 5, scope of `^5` Female | "The Ideas a Mind is composed of" includes accumulated experience, expertise, beliefs, skills, cultural formation. |
| Clarification 6, the Colloquialism Test | The labelers' check. It also carries two warnings: `^3` is felt aversion, not analysis (analysis is `^6`); `^8` is triggering, not reasoning. |

Where a colloquialism and a definition seem to disagree, the definition governs (Clarification 6, last section).

## 3. Other canon, and how it relates

| Source | Location | Role here |
|---|---|---|
| *Thinking in Cognitive Architecture* | `book/manuscript/FULL_MANUSCRIPT_v2.md` | Canon by owner ruling of 2026-09-21. Not used to define the Noetics in this study; consulted only if a labeling question cannot be settled from Clarification 1. |
| *CAS PCBA Engineer* | `book/CAS_PCBA_Engineer/*.md` | Same. |
| *Reality Engineering* | location not pinned in the records I read | Same. Not opened for this inventory. |
| 28 Foundations 1.0 | PDF sha256 `2c27443f447bd69901372edb1316be56a92490afc6f88055ce0c84ce7a871017` | Canon for the Foundations (Drives by World). **Not part of this study.** Drives are not labeled. |
| 40-cell composition grid | `docs/working/TKS_40_CELL_COMPOSITION_GRID_20260725.txt` | World-by-Noetic cells. **Not part of this study.** Worlds are not labeled. |
| Tootra Math Handbook | **not found locally** | Named as the origin of the ten definitions. A file-name search (names containing "handbook" or "tootra math", repository root to four levels deep) found only `book/CAS_PCBA_Engineer/build/appendix_j_handbook.pdf`, which I have not opened or verified. The study therefore cites Clarification 1, not the handbook itself. |

## 4. Kept distinct, and not labeled in this study

| Thing | Set | In this study |
|---|---|---|
| Noetics | `^0` to `^9` | **Labeled.** |
| Worlds / Domains | TKS Worlds: Spiritual, Mental, Emotional, Physical. CAS Domains: P, C, E, O. | Not labeled. |
| Drives / Foundations | 7, and 28 with Worlds | Not labeled. |
| Registers | T, A, f, E | Not labeled. |
| Operators (`+`, `×`, `|⟨…⟩`) | Clarification 10 | Not used. Several Noetics in one passage are recorded as a plain list, with no claim about how they combine. |

## 5. Conflicts found, and how each is resolved

1. **Notation in the pilot.** The pilot package wrote its two classes as `^8|C` and `^9|C` and called them "Cognitive Cause" and "Cognitive Effect". In CAS notation the bar marks a Register (T, A, f, E); C is a Domain and would be written `^8^C`. Resolution: this study writes `^8` and `^9` with no Domain and no Register. The pilot's records are left as they are and are quoted exactly when cited.
2. **`CO-n` and `^n`.** Clarification 1 prints both. Owner ruling of 2026-09-21: write `^n`. Resolution: `^n` everywhere; `CO-n` only when quoting code.
3. **Older alternative names** ("Attraction", "Critical Evaluation", "Receptive Integration", "Projective Assertion", "Causal Reasoning"). Clarification 3 calls these drift. Resolution: never used.
4. **`^0` Idea covers all things.** Owner decision recorded in the directive: `^0` stays in the representation; "is an Idea present" is not scored; which Ideas are found and how they relate is.

## 6. What I did not do

- I did not compare Clarification 1 against the handbook itself, because I did not find the handbook.
- I did not audit the whole repository for drifted names. That is outside this study.
- I did not open the three books.
