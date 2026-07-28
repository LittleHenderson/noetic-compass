# APPENDIX E
## The TKS Crosswalk — 40 Elements, 7 Foundations, 12 Prerequisites
*A native-coordinate reference with every unresolved translation left visible*

This appendix is a map between related vocabularies, not a declaration that
they are identical. That distinction is load-bearing.

The repository contains strong evidence for the **Noetic-position** part of the
map: TKS positions 1 through 9 carry the same names as CAS `^1` through `^9`,
and TKS position 10 is Idea, written `^0` in CAS. It does **not** yet contain an
owner-ratified, tested decision about what the four TKS Worlds become on a CAS
literal. Two hypotheses remain live:

- World A/B/C/D may correspond to CAS Domains P/C/E/O.
- World A/B/C/D may correspond to CAS Registers T/A/f/E.

Domain and Register are separate CAS axes. A single World letter cannot be both
by silent substitution. The 40-Element tables therefore preserve native TKS
coordinates (`A1` through `D10`). Candidate CAS renderings are labeled
**PROPOSED / OPEN**. Nothing in this appendix fills the empty crosswalk binding
required by the research registry, ratifies an ontology, or upgrades an
empirical claim.

That is not a reason to avoid the table. It is a reason to use the table without
erasing its provenance.

---

### E.1 The three coordinate systems

| System | First axis | Second axis | Example | Status here |
|---|---|---|---|---|
| Native TKS Element | Noetic position 1–10 | World A–D | `B6` | preserved source coordinate |
| CAS state | Noetic `^0`–`^9` | Domain P/C/E/O | `^6^C` | canonical CAS |
| CAS state with Register | Noetic + Domain | orthogonal Register T/A/f/E | `^6^C\|A` | canonical CAS |

The native TKS Worlds are:

| World | Native description | Keep in records as |
|---|---|---|
| A | Spiritual | `tks_world=A` |
| B | Mental | `tks_world=B` |
| C | Emotional | `tks_world=C` |
| D | Physical | `tks_world=D` |

Do not turn `B6` directly into `^6^C`, `^6\|A`, or `^6^C\|A` unless the record
also names the versioned hypothesis that licensed that translation. `B6` is
complete and auditable as a native TKS coordinate. An unsupported conversion is
less informative, not more.

---

### E.2 The 40 Elements in native TKS coordinates

The short descriptions below reproduce the quick-reference semantics used by
the TKS manuscript. They are lookup handles, not full definitions.

| Position | Function | World A — Spiritual | World B — Mental | World C — Emotional | World D — Physical |
|---|---|---|---|---|---|
| 1 | Mind | `A1` Divine / soul awareness | `B1` Ego, memory, logic | `C1` Emotional awareness | `D1` Body awareness |
| 2 | Positive | `A2` Soul evolution | `B2` Mental clarity | `C2` Joy, love | `D2` Health, order |
| 3 | Negative | `A3` Soul hindrance | `B3` Confusion, pessimism | `C3` Sadness, anger | `D3` Illness, chaos |
| 4 | Vibration | `A4` Aether / aura | `B4` Mental energy | `C4` Mood, atmosphere | `D4` Physical energy |
| 5 | Female | `A5` Soul yearning | `B5` Subconscious, creativity | `C5` Compassion, sensuality | `D5` Women, receptacles |
| 6 | Male | `A6` Spiritual discipline | `B6` Focus, structure | `C6` Courage, assertiveness | `D6` Men, penetrating |
| 7 | Rhythm | `A7` Life journey | `B7` Mental cycles | `C7` Emotional cycles | `D7` Physical rhythms |
| 8 | Above / Cause | `A8` Inner meaning | `B8` Mental triggers | `C8` Emotional triggers | `D8` Physical triggers |
| 9 | Below / Effect | `A9` Outer expression | `B9` Mental results | `C9` Emotional results | `D9` Physical results |
| 10 | Idea | `A10` Archetypes, purpose | `B10` Thoughts, concepts | `C10` Felt sense | `D10` Objects, matter |

#### The evidenced Noetic-position map

| Native position | Native name | Proposed CAS Noetic | Evidence status |
|---|---|---|---|
| 1 | Mind | `^1` | evidenced |
| 2 | Positive | `^2` | evidenced |
| 3 | Negative | `^3` | evidenced |
| 4 | Vibration | `^4` | evidenced |
| 5 | Female | `^5` | evidenced |
| 6 | Male | `^6` | evidenced |
| 7 | Rhythm | `^7` | evidenced |
| 8 | Above | `^8` Above/Cause | evidenced by name and prefix correspondence |
| 9 | Below | `^9` Below/Effect | evidenced by name and prefix correspondence |
| 10 | Idea | `^0` | evidenced; this is the one cyclic index change |

The one-based-to-zero-based symbol rule under proposal is therefore:

```text
A1…A9 stay A1…A9; A10 ↔ A0
B1…B9 stay B1…B9; B10 ↔ B0
C1…C9 stay C1…C9; C10 ↔ C0
D1…D9 stay D1…D9; D10 ↔ D0
```

That code map is not a blanket meaning claim. The proposal's row-level review
flags five positions where a compressed normalized definition does not cleanly
carry the CAS meaning:

| Normalized row | Review | Why it remains marked |
|---|---|---|
| `A0` | weak | “Divine Blueprint” is only a weak match for canonical `^0` Idea |
| `D5` | weak | the compressed row refers to a literal woman, not the compositional `^5` definition |
| `D6` | weak | the compressed row refers to a literal man, not the compositional `^6` definition |
| `D8` | divergent | the compressed row reads Above spatially as elevation; CAS `^8` is associative Cause |
| `D9` | divergent | the compressed row reads Below spatially as foundation; CAS `^9` is associative Effect |

Preserve `source_symbol`, `normalized_index`, and the definition version in any
dataset that uses these rows. A name match does not authorize overwriting a
meaning conflict.

---

### E.3 The World-axis decision is open

Here are the two live hypotheses side by side. They are alternatives, not two
columns to concatenate into a new identity.

| Native TKS World | Domain hypothesis `H_WD_v1` | Register hypothesis `H_WR_v1` |
|---|---|---|
| A Spiritual | P Principled | `\|T` Transcendent |
| B Mental | C Cognitive | `\|A` Analytical |
| C Emotional | E Evaluative | `\|f` Affective |
| D Physical | O Operational | `\|E` Embodied |

The ordering inside either hypothesis is well motivated: both descend from
high abstraction to concrete engagement. The choice **between** them is not
settled. Repository evidence points in both directions, and CAS explicitly
defines Domain and Register as orthogonal. For that reason:

1. Keep the native World field.
2. Name the hypothesis before translating.
3. Store the translated axis in its own field.
4. Never train, score, or publish a result that silently mixes the hypotheses.
5. Continue to stamp any dependent comparison
   `CONDITIONAL_ON_UNRATIFIED_CROSSWALK`.

The circuit equivalent is a keyed selector whose key is visible in the ledger.
It is not a wire soldered across both candidate outputs.

---

### E.4 Seven Foundations and their 28 native positions

The owner-supplied 28-Foundation source describes seven Foundation positions
across the same four native Worlds. The CAS teaching vocabulary has seven
Drives. A repository translation key aligns them by position, but the research
registry records that position mapping as outside the ratified claim-bearing
crosswalk. Read the CAS column below as a **positional teaching hypothesis**,
not a signed identity claim.

| Position | Native TKS Foundation description | Candidate CAS Drive name | Four native positions |
|---|---|---|---|
| 1 | desire to be and be with God | F1 Unity | `1a`, `1b`, `1c`, `1d` |
| 2 | wisdom, insight, and knowledge | F2 Wisdom | `2a`, `2b`, `2c`, `2d` |
| 3 | life, vitality, and health | F3 Vitality | `3a`, `3b`, `3c`, `3d` |
| 4 | companionship, love, and friendship | F4 Connection | `4a`, `4b`, `4c`, `4d` |
| 5 | worldly power, influence, and control | F5 Agency | `5a`, `5b`, `5c`, `5d` |
| 6 | material food and things | F6 Structure | `6a`, `6b`, `6c`, `6d` |
| 7 | lust, sex, and reproduction | F7 Purpose | `7a`, `7b`, `7c`, `7d` |

The native suffixes mean:

| Suffix | Native World | Typical expression in the owner-supplied elaboration |
|---|---|---|
| `a` | Spiritual | orienting meaning, metaphysical or devotional expression |
| `b` | Mental | concepts, models, reasoning, planning |
| `c` | Emotional | feeling-tone, valuation, emotional relation |
| `d` | Physical | bodily, material, sensorimotor expression |

If the Register hypothesis were ratified for a particular use, the candidate
renderings would be:

| Foundation | Spiritual `a` | Mental `b` | Emotional `c` | Physical `d` |
|---|---|---|---|---|
| 1 | `F1\|T` | `F1\|A` | `F1\|f` | `F1\|E` |
| 2 | `F2\|T` | `F2\|A` | `F2\|f` | `F2\|E` |
| 3 | `F3\|T` | `F3\|A` | `F3\|f` | `F3\|E` |
| 4 | `F4\|T` | `F4\|A` | `F4\|f` | `F4\|E` |
| 5 | `F5\|T` | `F5\|A` | `F5\|f` | `F5\|E` |
| 6 | `F6\|T` | `F6\|A` | `F6\|f` | `F6\|E` |
| 7 | `F7\|T` | `F7\|A` | `F7\|f` | `F7\|E` |

Until ratification, write the native coordinate alongside any candidate:

```text
source_position = 4c
source_world = C / Emotional
candidate = F4|f
crosswalk = H_WR_v1 / PROPOSED_UNRATIFIED
```

This makes a later correction mechanical. Without those four fields, a later
correction becomes archaeology.

---

### E.5 The 12 canonical Prerequisites

The Prerequisites are three four-stage cycles used by the Recursive
Prerequisite Model. The card and zodiac symbols are identifiers in this system;
they do not import conventional divinatory or astrological meanings.

#### Desire cycle — Kings

| ID | Card | Stage | Diagnostic reading |
|---|---|---|---|
| P1 | King of Clubs | Beginning Desire | the want is just dawning |
| P2 | King of Hearts | Strong Desire | the will is fully engaged |
| P3 | King of Spades | Weakening Desire | motivation is fading |
| P4 | King of Diamonds | Absent Desire | the will is gone |

#### Power cycle — Queens

| ID | Card | Stage | Diagnostic reading |
|---|---|---|---|
| P5 | Queen of Diamonds | Birth of Power | ability is just emerging |
| P6 | Queen of Clubs | Adolescent Power | ability is progressing but not yet effective |
| P7 | Queen of Hearts | Mature Power | ability is fully effective for the task |
| P8 | Queen of Spades | Waning Power | capability is diminishing |

#### Wisdom cycle — Jacks

| ID | Card | Stage | Diagnostic reading |
|---|---|---|---|
| P9 | Jack of Clubs | Learning Wisdom | knowledge is being acquired |
| P10 | Jack of Diamonds | Knowing Wisdom | knowledge is present; application may lag |
| P11 | Jack of Spades | Understanding Wisdom | a working grasp of the pathway |
| P12 | Jack of Hearts | Mastering Wisdom | comprehension and application are integrated |

These are states to diagnose, not a sequence to force every goal through. An
operator begins with the actual Prime Desire, checks the required Desire,
Wisdom, and Power conditions, and recurses on the first unmet acquisition.
“Absent Desire” is information. It is not an invitation to manufacture desire
through pressure, nor does an unmet condition authorize acting on somebody
else.

---

### E.6 A safe crosswalk record

Use one record per translated item:

| Field | Example |
|---|---|
| Source artifact | owner-supplied 40-Element definition set |
| Source version / hash | ______________________________ |
| Native symbol | `B6` |
| Native title | Mental Male |
| Native World | B / Mental |
| Native Noetic position | 6 |
| Proposed CAS Noetic | `^6` |
| World hypothesis | `H_WR_v1` / proposed-unratified |
| Proposed second factor | `\|A` |
| Meaning review | consistent / weak / divergent / unreviewed |
| Reviewer and date | ______________________________ |

The record separates source fact from translation choice. If an owner later
ratifies the Domain hypothesis instead, the native row does not change; only
the versioned translation field does.

---

### E.7 Source and status ledger

| Material used | Role | Status at publication build |
|---|---|---|
| TKS manuscript quick-reference Tables 2 and 3 | 40-Element and 12-Prerequisite summaries | book source |
| `28 fOUNDATIONS 1.0.pdf`, owner-supplied 2026-07-27, represented in the repository's full-definition JSON | native 28-Foundation descriptions | owner-supplied source |
| CAS Foundational Clarifications | canonical Noetic, Domain, Drive, and Register meanings | repository-normative CAS authority |
| proposed TKS↔CAS crosswalk artifact | row evidence and conflict disclosure | `PROPOSAL_UNRATIFIED`; not tested |
| 28-Foundation translation key | positional teaching scaffold | reference; semantic identity remains non-claim-bearing |

This appendix deliberately stops where the evidence stops. When a ratified,
tested crosswalk exists, revise the status block first, preserve this revision,
and only then promote any candidate rendering to a binding map.
