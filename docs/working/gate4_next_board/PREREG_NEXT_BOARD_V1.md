# PREREG — "NEXT BOARD" TEST, v2.1

> ## READ THIS FIRST — THE SDG ARM IS **WITHDRAWN** (v2.1, binding, supersedes every v2 claim about that arm)
>
> **v2 preregistered a second corpus arm (`--generator sdg`) whose primary claim was "INSTRUMENT
> CALIBRATION AGAINST KNOWN GROUND TRUTH". At v2.1 that arm is WITHDRAWN and that claim is
> RETRACTED, on two independent named kills. Neither kill was found by running the arm. Both were
> obtained for $0 by adversarial review plus a 30-line local computation, before any labelling call
> was made.**
>
> **KILL 1 — MAPPING CIRCULARITY.** The turn-type → board answer key was authored by **reading the
> rendered template strings through the same rubric the reader panel is given.** `B1`'s entire
> prescribed class is **one byte-identical string**, 90 of 228 turns: *"I can't take that turn — it
> would break the admissibility of the dialog. Want to try a different angle?"* — and the B1 rubric's
> lead clause is *"Decides whether to answer or to decline … a real answer OR an explicit refusal."*
> That is a **near-verbatim cue, not an independent construction**. `B5` is one template against a
> rubric clause it paraphrases. v2's own §3B.1 justification column quoted template text and rubric
> text side by side — **that table IS the derivation**, which is precisely the defect. The statistic
> therefore measures *"does an LLM panel applying rubric R to string S reproduce the label an author
> assigned to string S by applying rubric R"*. **It has NO INFORMATIVE RANGE:** a pass is guaranteed
> by the authoring, a fail indicates reader noise only. **The phrase "KNOWN GROUND TRUTH" was
> UNEARNED** — the truth was never known independently; it was authored by the process under test.
> v2 disclosed that the mapping was *ours* (§3B) and repeated that in §10B.10, but **neither
> disclosed that the mapping was derived from the same text via the same rubric**, which is the
> defect that voids the statistic.
> **Remedy, binding:** `gt_acc` is renamed **`rubric_adherence_acc`** and is a **RUBRIC-ADHERENCE /
> READER-RELIABILITY** check. **"CALIBRATION AGAINST KNOWN GROUND TRUTH" and "CALIBRATED" are
> DELETED as available verdicts everywhere.** Mapping circularity is preregistered as a **NAMED
> KILL** (`KILL_MAPPING_CIRCULARITY`) alongside GATE RA‑2, in §8B.
>
> **KILL 2 — THE ARM WAS UNFALSIFIABLE; GATE RA‑2 COULD NOT PASS.** Measured on the realised
> 36-conversation corpus (228 labelled turns), LOCO folds grouped by conversation, on the
> ground-truth task itself:
>
> | surface model | accuracy |
> |---|---|
> | char TF‑IDF(3,5) | **1.0000** |
> | word unigram | **1.0000** |
> | **raw character count** (one feature) | **1.0000** |
>
> The corpus is **38 distinct strings with ZERO ambiguity across boards**, so exact-string lookup is
> a **bijection** onto the prescribed board; and the three classes have **disjoint length
> distributions** (B0 30–97 chars, B1 exactly 104, B5 108–117), so a one-feature length classifier is
> perfect. Because `surface_acc = 1.0000`, GATE RA‑2 requires `ra_acc − 1.0000 ≥ 0.05`, which is
> **impossible for any accuracy**. The verdict was **NOT LICENSED before a single labelling call**.
> v2 §6B.2 said *"If the owner runs it anyway, it is to obtain that kill on the record"* — but that
> kill is obtainable **at $0**, with no reader panel, no ~256 label calls and no hours of GLM
> serialisation. v2's dry-run did cite char = 1.0000 but **attributed it to "template-prefix
> memorisation"**, understating the defect: the *length* result shows the corpus is surface-determined
> outright. **Preregistering a foregone kill is not a study.**
> **Remedy, binding:** `--stage precheck` computes this locally for **$0** and `--stage label`
> **REFUSES TO SPEND MONEY** while it fails. The arm is **WITHDRAWN BY DEFAULT**. Reviving it
> requires **a corpus whose surface does not determine the label** and an answer key not derived from
> the rubric — **not a relaxed bar**. `--allow-surface-determined-corpus` overrides the block, is
> **PREREG-DEVIATING**, and must be logged in §14.
>
> **What survives.** The `--generator api` arm is **untouched** by v2 and v2.1 — no constant,
> threshold, seed, gate or verdict of that arm is edited. The forced-path corpus builder, the
> realised transition matrix, the corpus persistence rate (**0.0000**, stickiness genuinely removed)
> and the $0 precheck are retained as **engineering artefacts**. None of them is evidence about any
> model.

> ## TEMPLATE DISCLOSURE (v2, binding, and decisive — retained in full)
>
> **v2 adds a second corpus arm (`--generator sdg`) whose text is TEMPLATE-RENDERED, not
> generated.** `cas-synthetic/generator/multi_turn/conversation_generator.py` calls **no model,
> makes no network request, and runs no inference of any kind**. Its `_render_turn` selects a
> string from a fixed table and performs `template.format(cas=...)`. Its **entire live surface
> vocabulary is 22 authored strings** (7 user openers, 4 user repairs, 2 user closes, 15
> assistant templates — 6 of which differ only by a substituted CAS expression; a further 6
> authored strings are unreachable dead constants). Exactly **7 distinct CAS expressions** exist
> in the whole generator. `PLAN`, `REFUSE` and `REFUSE_CLAIM` have **one template each**, so
> forcing those turn types emits byte-identical text every time apart from the substituted
> expression.
>
> **The consequence, stated plainly:** a lens applied to this text is evidence about **the lens
> and the templates**. It carries **no information whatsoever about model outputs.**
>
> **Therefore the surface control matters MORE here, not less.** Fixed phrasing is trivially
> learnable by a char- or word-level model. **It is preregistered in advance that a surface-control
> WIN on the template corpus KILLS the arm outright** (GATE RA‑2, §8B). This is not
> a hedge added after seeing a number: a mechanical dry-run with *simulated* 75 %-accurate readers
> already produced `gt_acc = 0.9538` against a **char-n-gram accuracy of 1.0000** on the same task
> — i.e. the expected outcome of the real run is a **KILL**, and it is recorded here before any
> labelling call is made.
>
> **v2.1 CORRECTION TO THIS PARAGRAPH.** The dry-run above attributed the 1.0000 to *template-prefix
> memorisation* and to the CAS-expression slot. **That understated the defect.** The corpus is
> surface-determined **outright**: raw character count alone also scores 1.0000, because the three
> classes have disjoint length ranges. The correct statement is not "a surface win would kill the
> claim" but **"the surface control has already won, by a bijection, so the gate is unsatisfiable and
> the arm is withdrawn"** — see the v2.1 banner above and §6B.2.

**Revision:** **v2.1** (the forced-transition SDG arm added at v2 is **WITHDRAWN** on two named
kills; the `--generator api` arm is **Rev 0.4, unchanged in every respect** — no constant,
threshold, seed, gate or verdict of the api arm is edited by v2 or v2.1)
**Gate:** Gate 4 (output-lens, sequential + calibration)
**Status at time of writing:** PREREGISTERED — NOT YET RUN under v2. **No labelling data has been
collected under this revision.** One Rev 0.3 smoke run exists and is quarantined in `rev03_stale/`
marked `DO_NOT_REUSE` — it was generated under the without-replacement follow-up scheme that Rev 0.4
rejects as true-by-construction (§13, FATAL-1). It must not be relabelled or analysed. One Rev 0.4
api-corpus smoke exists and was **REJECTED**; §5B records why, because that rejection is the reason
v2 exists.
**Author:** Claude (agent), for owner review.
**Date written:** 2026-08-19 (Rev 0.4) · **v2 written:** 2026-08-19
**Directory:** `docs/working/gate4_next_board/`
**Runner:** `next_board_test.py` (same directory)
**Descends from:** `docs/working/gate2_closure/PREREG_LENS_NONARBITRARINESS_20260817.md` (L1–L4) and
`docs/working/gate2_closure/CAS_LENS_REPAIR_ROADMAP_20260818.md` (honesty ceiling). This document is an
**extension of that line**, not a fresh design, and it inherits every ceiling stated there.

---

## 0. ONE-PARAGRAPH SUMMARY

We ask whether reading a single assistant turn as one of five **CCB board types** (from the CAS-PCBA
book, Part IV) tells you anything about the board type of the **next** assistant turn. The claim is
tested entirely in **output space** — no weights, no internals. It must beat a marginal base rate, a
**within-conversation** permutation null, the scripted user move, turn position, and — the primary
kill — the **strongest of three surface models** (char n-gram, word unigram, length) reading the *raw
text* of turn N. If a surface model predicts turn N+1's board as well as the board label of turn N
does, the board abstraction is adding nothing and the hypothesis is rejected at v1. A **matched
6-class discourse taxonomy**, read by the same panel on the same corpus, runs *inside v1* so that a
positive result says something about the *board* taxonomy specifically and not merely about "an LLM
ensemble beats TF-IDF".

**Note on the baseline you should have in mind.** The console prints a 1/6 = 0.167 label chance. That
is **not** the relevant baseline. Gate 0 permits the "none dominates" class up to 0.40 of consensus
labels, so an always-predict-the-mode rule can legitimately score up to **≈ 0.40 — about 2.4× the
1/6 figure**. GATE 2 compares against the LOCO-measured marginal, not against 1/6, precisely so that a
dominant class cannot buy a pass.

### 0.1 THE TWO ARMS, AND THE CLAIM CHANGE (v2)

| | `--generator api` (Rev 0.4, unchanged) | `--generator sdg` (added v2, **WITHDRAWN v2.1**) |
|---|---|---|
| corpus | four commercial models write the turns | **forced-transition**, template-rendered by cas-synthetic |
| "ground truth" | **none** — labels come only from readers (κ ≈ 0.54) | **prescribed per turn — but authored from the same strings via the same rubric, so NOT independently known** |
| primary claim | **ecological sequential prediction** | ~~INSTRUMENT CALIBRATION AGAINST KNOWN GROUND TRUTH~~ **RETRACTED v2.1** → at most **RUBRIC ADHERENCE / READER RELIABILITY** |
| primary statistic | `board_acc` (LOCO Markov) | ~~`gt_acc`~~ → **`rubric_adherence_acc`** |
| sequential test | **is** the claim | **SECONDARY, DESCRIPTIVE ONLY** — and the word **SUPPORTED is not available to it** |
| status of a PASS | evidence about model output | **NONE — the arm is WITHDRAWN on two named kills** |
| how the arm ends | runs, gates, verdict | **blocked at `--stage label` for $0; never labelled** |

**This was the most important part of v2, and v2.1 retracts it.** v2 said: *with the SDG arm the
primary claim is no longer ecological prediction; it becomes — given a turn **constructed** to be
board X, does the blind-reader lens read it as X?* **That claim is withdrawn.** It presupposed that
"constructed to be board X" was established independently of the reading. It was not: the
construction *was* a reading, performed by the author, with the same rubric. See KILL 1 in the
banner and §3B.0.

The book's own glossary names the artefact v2 was reaching for: a **"synthetic known-fault board …
used to validate the candidate's code against ground truth by fiat. SOFTWARE-ONLY EVIDENCE."** That
phrase is retained here because it is the correct *genre* — but v2.1 records that **this corpus does
not qualify even as that**. A known-fault board earns its name because the fault is injected
independently of the instrument that must detect it. Here the "fault" is a string chosen *because*
the rubric would read it a certain way, so the board is not known-fault; it is **instrument-shaped**.

> **THERE IS NO PASS AVAILABLE IN THE SDG ARM.** It is withdrawn. Even had it run, a high
> `rubric_adherence_acc` would have shown only that three blind commercial readers apply this rubric
> to fixed strings the way its author did — **a fact about READERS and a RUBRIC**. It would show
> NOTHING about natural model output, and it MAY NEVER BE REPORTED AS IF IT DID.

---

## 1. HYPOTHESIS

**H1 (primary, owner's).** The CCB board type of assistant turn *N* predicts the CCB board type of
assistant turn *N+1* above chance, above the marginal base rate of board types, and above a surface
model of turn *N*'s raw text.

**H0 (null).** Board type of turn *N* carries no information about turn *N+1* beyond (a) the marginal
frequency of board types, (b) the composition of the conversation it sits in, and (c) whatever a
surface text model already extracts from turn *N*.

Directional prediction if H1 holds: the transition matrix P(b_{N+1} | b_N) is non-uniform in a way
that survives leave-one-conversation-out cross-validation **and** a within-conversation permutation.

---

## 2. WHY THIS TEST, AND NOT THE COMPONENT ATLAS

The Component Atlas asked whether CAS-PCBA parts live **inside model weights**. It returned NULL at
1b, GREY at 2.8b, GREY at 20B with both sanity checks passing. The labels do not attach to internal
parts. **This test makes no weights claim of any kind.**

It lives where our evidence already is — output space:

| prior measurement | number | source |
|---|---|---|
| single-cell reading of real outputs | reader agreement 0.5333, Fleiss 0.4479 | `l1_real_report.json` |
| circuit (part-set) reading | reader 0.6099 vs null 0.4002, lift **+0.2097** | `l2_circuit_report.json` |
| wiring (directed edge) reading | 0.2437 vs null 0.0525 = **~4.7× chance** | `l2_wiring_report.json` |
| 20-part "sharpening" | lift +0.231 (flat) coverage 92%→58% | `l2_circuit_wide_report.json` — recorded dead end |

Two directions our own numbers say are stronger: **coarser** (parts beat 40 cells) and **relational**
(wiring's ratio-to-chance beat mere presence). Board type is both coarser (6 classes) and, across
turns, relational. That is the entire rationale.

---

## 3. HONEST SCOPE — WHAT THE BOOK ACTUALLY SAYS ABOUT BOARD SEQUENCING

**This is required disclosure under standing repo discipline (requirement 7).**

> **The CAS-PCBA book does NOT describe board-to-board sequencing. The sequencing claim tested here
> is OURS, not the framework's.**

Evidence for that statement (five independent lines, from a full-text pass over all 783 pages):

1. Appendix D "Standard CCB Reference Designs" has exactly D.1–D.5, one section per board, then a
   flat cross-reference list. There is no D.6, no inter-board topology, no combined diagram. It calls
   itself "the datasheet binder … so a practitioner can copy a known-good design from one place" —
   a parts catalogue, not an assembly.
2. The CCDL grammar (Appendix C §C.8 "Board-Level Statements") contains **no board-composition
   production**. The only inclusion form is `use <circuit>;`, and the book's only use of it is the
   CPMB top-level block including its own five subsystems. No CCDL statement instantiates one CCB
   inside another.
3. `sequence a -> b -> c [enforce=strict]` exists, but its documented meanings are the P→C→E→O
   power-up ordering and the Φ cyclic-waveform label — never board ordering.
4. Chapter 17 frames the five boards as five parallel instances of one process: "This is the process
   you apply to all five reference boards … The flow is the same; only the board changes."
5. Full-text search returns **zero** hits for *backplane, board-to-board, inter-board, multi-board,
   motherboard, daughterboard, "system of boards", "chain of boards", "the next board"*.

The only board-to-board relation the book states is a **power/supply dependency**, not a signal path:
Chapter 22 (printed p.423) calls the CPMB "the board that keeps all the others alive," and Appendix D's
index row reads "Power supply for every other board." A second, weaker claim in §21.12 says the CMB is
"the enabling board" for CSB capabilities — a functional dependency, never a wiring one (no netlist,
no port, no signal path).

**What the framework DOES specify is sequencing *within* a single board** (stage-to-stage flow in every
block diagram, Domain Descent P→C→E→O with the single upward O→P low-gain feedback via, the CPMB
power-up sequencer, the COB's ordered Φ cycle). Intra-board sequencing is framework-predicted and richly
specified; **inter-board sequencing is not in the framework.**

Consequence for reporting: a positive result may **not** be written up as "the CAS-PCBA framework
predicts board transitions." It may only be written up as "conversational turns labelled with the
book's five board types show above-chance sequential structure — a regularity we hypothesised, which
the book does not describe."

---

## 3B. HONEST SCOPE — THE TURN-TYPE → BOARD MAPPING IS OURS (v2)

**Same disclosure discipline as §3.** §3 discloses that the *sequencing* claim is ours. This section
discloses that the *mapping* is ours too.

> **cas-synthetic speaks DIALOG ACTS. The taxonomy speaks BOARDS. Neither framework supplies a
> correspondence between them. The mapping below is AN ASSUMPTION WE ARE MAKING.**

`dialog_grammar.py` defines 11 turn types (`OPEN`, `ACK`, `MIRROR`, `CLARIFY`, `EMPATHIZE`,
`ANSWER`, `PLAN`, `REFUSE`, `REFUSE_CLAIM`, `REPAIR`, `CLOSE`) as *dialog moves*. The CCB taxonomy
names five *board types* plus "none dominates". Nothing in the CAS-PCBA book, in the CAS framework,
or in the dialog grammar relates the two. What follows is our construction, preregistered before
labelling, and it is the assumption that a hostile reviewer should attack first.

### 3B.0 MAPPING CIRCULARITY — a NAMED KILL (v2.1), not a caveat

**v2 disclosed that the mapping is *ours*. It did NOT disclose HOW the mapping was derived, and that
omission is the defect that voids the primary statistic.**

The mapping was produced by **reading the rendered template strings and asking which rubric clause
they matched.** The rubric is the instrument under test. Therefore the answer key and the instrument
share an origin:

| prescribed class | the entire realised text of that class | the rubric clause it was matched against |
|---|---|---|
| **B1** (90 / 228 turns) | **ONE byte-identical string**: *"I can't take that turn — it would break the admissibility of the dialog. Want to try a different angle?"* | *"Decides whether to answer or to decline … a real answer OR an explicit refusal … States a firm standing principle that the request cannot renegotiate."* |
| **B5** (60 / 228) | **ONE template** × 7 CAS slots: *"Given ⟨cas⟩, the next step on the pathway would be to strengthen the prerequisite that's currently weakest."* | *"Treats ordering as a hard gate … sequences explicitly before engaging."* |

Set side by side, the template text and the rubric text are **near-verbatim**. §3B.1's justification
column below *is that side-by-side comparison* — i.e. **the table is the derivation**, which is
exactly why it cannot also serve as an independent answer key.

> **CONSEQUENCE, BINDING.** `rubric_adherence_acc` measures: *does an LLM panel applying rubric R to
> string S reproduce the label an author assigned to string S by applying rubric R?* **This has no
> informative range.** A high value is guaranteed by the authoring. A low value indicates reader
> noise, nothing more. **It is not calibration; the truth is not independently known.**

**Preregistered as a NAMED KILL.** `KILL_MAPPING_CIRCULARITY` is a standing kill for this answer key,
evaluated **alongside GATE RA‑2** in §8B, and it fires **unconditionally** for this corpus. The
verdict vocabulary of the SDG arm therefore **cannot contain CALIBRATED** at any value of any gate.

**What would remove this kill** (all three, not any one): (a) an answer key derived from something
other than the rubric — e.g. the *generator's own* dialog-act semantics fixed in advance, with the
rubric written afterwards by someone who never saw the templates; (b) rubric authorship and answer-key
authorship **separated by person and by time**; (c) more than one string per class, so the key cannot
be a lookup.

### 3B.1 The mapping (frozen; mirrored in `next_board_test.SDG_TURN_TYPE_TO_BOARD`)

> **Read §3B.0 first.** The "justification" column below is *how the key was derived*, which is the
> circularity. It is retained verbatim as the evidence for KILL 1, not as a defence of the mapping.

| turn type | prescribed board | justification | strength |
|---|---|---|---|
| `REFUSE` | **B1** | The single REFUSE template is an explicit decline that cites a firm standing principle ("it would break the admissibility of the dialog"). B1's rubric: "Decides whether to answer or to decline … an explicit refusal … States a firm standing principle that the request cannot renegotiate." | **strong** |
| `PLAN` | **B5** | The single PLAN template is an explicit prerequisite-ordering move ("strengthen the prerequisite that's currently weakest"), matching B5's "Treats ordering as a hard gate … sequences explicitly before engaging." | **WEAK — flagged.** It carries **no** capacity / budget / throttle / reserve / silence content, which is the clause B5's rubric *leads with* ("About CAPACITY, not content"). This is a partial match and is the second thing a reviewer should attack. |
| `ACK`, `MIRROR`, `CLARIFY`, `EMPATHIZE`, `ANSWER` | **B0** | A turn constructed to exhibit none of the five board behaviours is exactly what B0 names ("None of the five above is clearly doing the dominant work"). | strong |
| `REFUSE_CLAIM` | **B0** | Grouped with the above at v2 as part of "the honest read". | **WEAK — flagged at v2.1, on the SAME FOOTING as `PLAN`→B5.** See 3B.1a. |
| `CLOSE` | **NONE → EXCLUDED** | A terminator. It is also role-ambiguous (the renderer decides user-vs-assistant on a 50/50 coin flip), so it is never labelled. | — |
| `OPEN`, `REPAIR` | **NONE → EXCLUDED** | User-side turns. Only assistant turns are ever labelled in this pipeline. | — |

Per the mandate: **where no board is defensible the turn type maps to NONE and is EXCLUDED from the
labelled corpus rather than forced into a class.**

#### 3B.1a `REFUSE_CLAIM` → B0 is WEAK (v2.1 correction)

v2 flagged `PLAN`→B5 as WEAK but presented the six-way B0 group as *"not forcing a fit; the honest
read"*. **That was wrong, and it is corrected here.** B0 is a **positive prescription that readers
are scored against**, not a neutral residue. The single `REFUSE_CLAIM` template renders:

> *"I don't think the structure you're proposing fits. The closer reading I'd stand behind is ⟨cas⟩."*

That is **an explicit decline plus a competing reading**. It plausibly reads as **B1** (the rubric:
*"Decides whether to answer or to decline … an explicit refusal"*) or as **B3** (two readings held
side by side) — and **§3B.2 below already concedes `REFUSE_CLAIM` "comes nearest" to B3**. A reader
choosing B1 or B3 there is scored **WRONG** against an author judgement that has **no greater
standing than the reading being tested**. It is therefore flagged WEAK, machine-readably, in
`next_board_test.SDG_WEAK_MAPPINGS`, and surfaced per class in the report.

#### 3B.1b The effective mapping is SIX turn types, not eleven (v2.1)

The 11-row table **overstates what governs**. **No forced path in `SDG_FORCED_PATHS` contains `ACK`
or `EMPATHIZE`**, so realised B0 mass comes only from `MIRROR` / `ANSWER` / `CLARIFY` /
`REFUSE_CLAIM`. Worse, **every `ACK` and `EMPATHIZE` template is under the 30-character floor**
(*"Got it."* = 7, *"Yeah. That's heavy."* = 19, *"That sounds like a lot."* = 23), so a path using
them would hit `gen_conversation_sdg`'s `len(out) < 30` break and be **silently truncated**
mid-conversation. That was an undisclosed latent trap for whoever next edits the path bank;
`sdg_validated_paths()` now **refuses such a path at load time** rather than leaving it latent.

### 3B.2 STRUCTURAL CEILING — three of the five boards cannot be constructed at all

This is a binding, preregistered limitation, not a caveat added afterwards.

> **B2, B3 and B4 have ZERO prescribed instances and are UNREACHABLE from this generator.**

- **B2 (COB)** needs a rate, a cycle and rigidity. **No** SDG template mentions a rate, a cycle, a
  period, or how hard a pattern is to disturb.
- **B3 (CDAB)** needs two distinct things compared, with the shared part explicitly cancelled and the
  *kind* of difference named. `REFUSE_CLAIM` comes nearest (it sets the user's proposal against its
  own reading) but performs no cancellation and names no kind of difference, so it is mapped to B0,
  not forced into B3.
- **B4 (CMB)** needs resemblance-of-shape retrieval of past cases and reporting of absence. **No**
  SDG template retrieves anything.

**Consequence, binding:** whatever the SDG arm reports, **the instrument remains UNCALIBRATED for
three of the five boards.** The SDG arm calibrates B1 / B5 / B0 only, and every write-up must say so.

### 3B.3 One transition is structurally unrealisable

`PLAN` is admissible only after `MIRROR` or `ANSWER`, both of which are B0. Therefore **a B1 turn can
never be immediately followed by a B5 turn**: `B1→B5` cannot occur in any admissible forced path. The
five realisable off-diagonal transitions are `B1→B0`, `B0→B1`, `B0→B5`, `B5→B0`, `B5→B1`; the bank in
§5B covers all five. This is disclosed so the realised transition matrix is not misread as evidence
of an asymmetry in the boards.

---

## 4. THE TAXONOMY AND THE READER RUBRIC

Six labels. Readers never see the words *CAS*, *TKS*, *Noetic*, *board*, *CCB*, or any board name.
They see plain-English behaviour descriptions only. **No Noetic is renamed to its circuit function**
(book rule, Appendix D; CLAUDE.md Clarification 1) — the rubric describes *behaviour*, and never
substitutes a function-name for an operator name.

| code | internal mapping (never shown to readers) | reader-facing description |
|---|---|---|
| **B1** | CCB-1 CSB, Cognitive Safety Board | Decides whether to answer or to decline. Resolves to one of two clear paths — a real answer OR an explicit refusal — not a hedged blend; once it declines, it stays declined. States a firm, standing principle that the request cannot renegotiate. Surfaces **both** what pulls it toward the request and what pushes it away from **that same one request**, then nets them into a single verdict. May re-read an ambiguous request and name the alternative meanings before judging. Leaves a reason trail — what it caught, which consideration decided it, why. |
| **B2** | CCB-2 COB, Cognitive Oscillator Board | About how **often** something repeats, not what it is. Names or clearly implies a rate ("every two hours", "like clockwork"). Describes a **cycle** that runs a fixed ordered sequence of states and returns to its own start, not a one-off. Talks about how rigid the pattern is — how hard it is to knock off its own rate (a loose preference vs a self-restoring compulsion). Talks about pulling an internal rhythm into step with an outside one, and about changing it by slow incremental drag rather than a jump. Or about how **long** each episode runs at the same frequency. |
| **B3** | CCB-3 CDAB, Cognitive Differential Amplifier Board | Holds **two distinct things side by side** and compares them. Explicitly discards what the two share ("both agree on X, which tells you nothing") and spends its words on how they diverge. Names the **kind** of difference, not its size — never a bare score, never just "A differs from B". Insists both sides are judged against the **same single yardstick**, and flags it as a defect if they were weighed on different standards. Guards against inflating a trivial divergence into a false dichotomy. |
| **B4** | CCB-4 CMB, Cognitive Memory Board | Finds past cases by **resemblance of shape**, not by keyword — "this is like the time when…", "I've seen this kind of pressure before, three times" — matching cases whose surface wording shares nothing. Talks about what is held deeply and near-permanently versus what fades fast, with rehearsal framed as a deliberate policy. Reports what is **absent** — names gaps in its own experience, and separates never-encountered from encountered-then-faded. Summarises an episode as a **sequence of moves** rather than quoting the sentence. Says vivid, high-stakes events were written hard and routine ones barely moved the needle. |
| **B5** | CCB-5 CPMB, Cognitive Power Management Board | About **capacity**, not content — whether there is enough left to do the work at all: fatigue, depletion, budget, headroom. Treats ordering as a hard gate: refuses to act until the governing principle is loaded first, and sequences explicitly before engaging. Budgets and throttles — allocates a limited resource across competing demands, caps how much any one demand may pull, deliberately keeps reserve. Names a **degradation ladder** with tiers — warn, then rest, then stop — ending in explicit **silence**, not a degraded answer. Names confident output from an exhausted system as the worst failure. |
| **B0** | *(none)* | None of the five above is clearly doing the dominant work in this turn. |

### 4.1 Mandatory disambiguators shown to every reader

Carried verbatim into the reader prompt. They exist because the source material makes three specific
confusions likely.

1. **COUNT THE INPUTS.** B1 also weighs a pull-toward against a push-away — but on **one** request.
   B3 needs **two separate things** being compared. The words "difference", "differential",
   "on the one hand / on the other" do **not** by themselves make it B3.
2. **A SAFETY TOPIC DOES NOT MAKE IT B1.** A turn can compare a request against a known-safe baseline;
   that is two inputs and cancellation of what they share → **B3**, however safety-flavoured it reads.
3. **B2 vs B5.** Both use energy/rhythm words. B2 = *how often* and *how locked* a repeating behaviour
   is. B5 = *is there enough*, *what order*, *when to stop*.
4. **REPETITION ALONE IS NOT B2.** B2 needs rate-plus-cycle-plus-rigidity together.
5. **PICK THE DOMINANT ONE.** Real turns mix. If none dominates, choose **B0** — B0 is a legitimate
   answer, not a failure.

### 4.2 A known epistemic mismatch, disclosed

Every board chapter in the book carries an honesty note that all parameters (β, Q, f0, CMRR, rail
voltages, tolerances) are **design values chosen by the author, never measurements from a running
model**. Our rubric therefore contains **no** item asking readers to judge whether a turn "measured"
or "benchmarked" anything. Readers judge observable textual behaviour only.

### 4.3 The matched-taxonomy arm (CONTROL 8) — inside v1

A second, independently constructed **6-class discourse taxonomy of equal granularity** (5 named
classes + "none dominates"), built from ordinary speech-act categories with zero CCB content, is
labelled by the **same panel on the same corpus** and put through the **same prediction test**:

| code | reader-facing description |
|---|---|
| **D1** | Tells the reader what to **do** — instructions, steps, a plan, a recommendation to act. |
| **D2** | **Explains** how or why something is the way it is — mechanism, definitions, background, causes. |
| **D3** | **Argues** for a position — advances and supports a claim, or weighs claims and comes down somewhere. |
| **D4** | Attends to the reader's **feelings** and situation — acknowledges, validates, reassures, softens. |
| **D5** | Talks about **itself** — its own knowledge, limits, uncertainty, process, self-correction. |
| **D0** | None of the five above dominates. |

Rev 0.3 deferred this to v2. That was wrong: without it, a GATE 1 pass licenses only *"a 3-model LLM
consensus reading of turn N beats a TF-IDF logistic regression on turn N"* — which **any** competently
written 6-class discourse taxonomy would likely also achieve — so v1's positive result would be close
to uninformative **about boards specifically**. The arm costs one extra labelling pass on the *same*
corpus (~128 calls) and converts a GREY into an actual finding, versus spending twice on two corpora.

---

## 5. CORPUS DESIGN

### 5.1 Shape

| parameter | full run | `--smoke` |
|---|---|---|
| conversations | **36** (the entire seed bank) | 4 |
| assistant turns per conversation | **7** | 3 |
| total assistant turns | **252** | 12 |
| possible (turn N → turn N+1) pairs | **216** | 8 |
| readers per turn | 3 (of a 4-model panel) | 3 |
| taxonomy arms | 2 (`board`, `alt`) | 2 |

`--n-convos` is **hard-capped at 36** and the runner exits with an error above it. Rev 0.3 defaulted to
30 and would have silently shrunk any larger request to the 36-prompt bank size, quietly invalidating
the Gate 0 pair arithmetic.

### 5.2 Seed prompts

All 36 seed prompts come from the **existing** bank in
`docs/working/gate2_closure/independent_bank/gen_real_outputs.py` (`PROMPTS`), ordered by
`random.Random(20260819).sample(PROMPTS, 36)`. Reusing that bank keeps this corpus comparable to
every `l1_real` / `l2_*` number already on record. The bank is deliberately diverse: decision
dilemmas, factual explanation, grief, ethics, creative writing, code, interpersonal conflict,
self-doubt, science explanation, habit change. **No seed prompt is reused across conversations** —
two conversations from one prompt would be topically correlated and would break LOCO independence.

### 5.3 User follow-up turns — sampled i.i.d. WITH REPLACEMENT

Turns 2–7 of each conversation are driven by a fixed bank of **five board-agnostic follow-up moves**:

- `U1` "Say more about that."
- `U2` "What's the strongest case against what you just said?"
- `U3` "I don't think that's right. Convince me, or change your mind."
- `U4` "Okay — what should I actually do first?"
- `U5` "How would you know if you were wrong here?"

**Each turn's follow-up is an INDEPENDENT draw with replacement** (`random.Random(770000 + conv_id)`,
one `choice()` per turn). A move may appear twice in a conversation or not at all.

> **Rev 0.3 defect, corrected.** Rev 0.3 drew a **permutation** — all five used exactly once. That makes
> f_t and f_{t+1} **dependent**: P(f_{t+1}=u | f_t=u) = 0 against an unconditional 1/5. Turn *t* is
> generated in response to f_t and turn *t+1* in response to f_{t+1}, so b_N carried information about
> which follow-up had been **consumed**, which constrained which follow-up drove b_{N+1} — **a
> b_N → b_{N+1} dependence manufactured entirely by the sampling scheme, with zero board content.**
> Rev 0.3 §5.3 asserted "a randomised stimulus cannot create a spurious correlation between b_N and
> b_{N+1}". **That claim was false for that design and is deleted.** With i.i.d. draws it is true, and
> the user-move control below is a hard kill rather than a downgrade.

Second protection: **CONTROL 5 / GATE 6** predicts b_{N+1} from the follow-up template id alone. In
Rev 0.4 failing it **REJECTS the run** (Rev 0.3 merely downgraded to "SUPPORTED (weak)", which would
have let a fully design-induced signal be reported as support).

### 5.4 Generator / labeller separation (mandatory requirement 4)

Panel (frozen, all four already blindness-probed at 0.033–0.110 against a 0.3 threshold):
`gemini-2.5-flash`, `deepseek-v4-pro`, `qwen3.8-max`, `glm-4.6`.

Conversation *i* is generated by `ORDER[i % 4]`. Its turns are labelled by **the other three models
only**. No model ever labels a turn it wrote. This is enforced at three points: at label time
(`collect_marks` refuses the write), at analyze time (GATE 4 **computes** the violation set), and in
the report (the violating uids are listed). Rev 0.3 hardcoded `g4 = True` and wrote
`{"enforced": true, "assertion_passed": true}` unconditionally, with the real check as a bare `assert`
that crashed the run instead of producing a REJECTED verdict; that report field was not evidence of
anything. Reader count per turn is a constant 3 — required for Fleiss κ.

### 5.5 What a reader sees

A reader sees **one assistant turn, in isolation**: no conversation id, no turn index, no user turn, no
neighbouring turns, no other reader's label. Turn text is truncated to 1000 characters (same as every
`l2_*` run).

**Excerpt ids are per-batch, per-reader ALIASES** drawn from `random.Random(91000 + …).sample(range(1000,10000), k)`.
Rev 0.3 printed the internal `uid`, which equals `turns_per_conv × conv_position + turn_index` and
therefore deterministically encoded **both conversation and turn position** — a direct contradiction of
this section's own blindness guarantee. The uid↔alias map lives only on the analysis side.

Turns are shuffled across labelling batches with a per-reader seed (`4242 + reader_index`), then a
deterministic repair pass swaps any batch-mates from the same conversation. **No batch may contain two
turns from the same conversation.** If any residual collision survives the repair, the run **aborts at
label time** and the residual count is also a hard Gate 0 check. (Rev 0.3 counted residual collisions
and reported them but gated nothing — yet a residual collision is exactly the contamination that lets a
reader smooth its own labels and manufacture the dependence under test.)

### 5.6 Label acceptance — strict, and why

A labelling call is accepted **only if all four hold**:

1. `finish_reason == "stop"`;
2. a **JSON array** is parseable out of the **answer** (`message.content`);
3. every id is an **alias actually shown in that batch** (a fabricated id is dropped, and can never
   overwrite a genuine label from another batch);
4. **exactly** the batch's ids appear, once each.

Anything else yields **zero labels** and routes the batch into the repair pass.

> Rev 0.3 concatenated `content` with `reasoning_content` and scanned the result for the first
> `\b(B[0-5])\b` after `"id":`. A reasoning model that hit `finish_reason="length"` before emitting the
> array, or wrote "not B1, so B3" in its trace, would still yield confident-looking labels harvested from
> chain-of-thought; `finish_reason` was printed but never enforced. It also stored **any** uid the model
> emitted, without checking it belonged to that batch, into a plain dict in `as_completed` order — so a
> hallucinated id could nondeterministically overwrite a real label. Both are closed.

**Reasoning-only responses are refused by default.** `--allow-reasoning-only` exists but is a
**preregistration deviation** and must be recorded in §14 if used. The cost of strictness is paid by
the repair pass, not by coverage.

### 5.7 Repair pass and checkpointing

**Repair pass.** After the main pass, each reader is re-asked *only* for the uids it failed to return, in
batches of 3, for up to 2 rounds (`--repair-rounds`). Coverage on this panel is lost to parse/drop, not
to call failure, so this is cheap — and it is what makes the Gate 0 coverage floors reachable at all.

**Checkpointing.** Both API stages append to JSONL as each unit lands and skip completed units on
restart: conversations to `conversations.jsonl`, individual labelling calls to `label_calls.jsonl`
(keyed by a sha256 of reader+arm+uid-set). Rev 0.3 buffered everything in memory and wrote only after
the executor fully drained, so a KeyboardInterrupt, console-encoding crash, expired key or OOM lost the
**entire** stage — 252 generation calls, or an hour-plus of serialized GLM labelling.

**Partial conversations are kept.** A short/empty or failed turn now **truncates** the conversation at
the last good turn (kept if it reached `--min-turns`, default 3). Rev 0.3 raised and discarded the whole
conversation including its good turns, shrinking the binding constraint (n) and skewing the generator mix.

---

## 5B. THE SDG FORCED-TRANSITION CORPUS (v2, `--generator sdg`)

### 5B.1 Why this arm exists — four corpus problems, named

The Rev 0.4 api-corpus smoke was **REJECTED**, and **every problem was a CORPUS problem**:

1. **Stickiness.** Natural conversation is persistent. Persistence (predict the same board as turn N)
   scored **0.5238** against the Markov model's **0.5079** — the sequence barely moved, so there was
   almost nothing left to predict. GATE 5 was never going to clear.
2. **Unstable generators.** Turn length and quality varied wildly across the four models.
3. **Empty turns.** Short/empty outputs truncated conversations and shrank the binding *n*.
4. **No ground truth.** Labels came only from readers at κ ≈ 0.54. There was **no answer key** at
   any point, so nothing could ever be checked against a known value.

The SDG arm fixes all four **because the path is PRESCRIBED rather than hoped for**. It fixes them at
the cost of the claim: see §0.1 and the template disclosure at the head of this document.

### 5B.2 Forced transitions — construction, not sampling

`generate_dialog_path` **samples** a path and exposes no parameter to supply one; `generate_conversation`
hardcodes `path = generate_dialog_path(seed, target_turns)`. The runner therefore drives
`_render_turn` directly with a **constructed** path, leaving cas-synthetic's own code untouched and
imported, never copied.

Three properties are enforced at load time and the run **aborts** if any fails:

1. **ADMISSIBILITY.** Every `(prev, next)` pair satisfies `dialog_grammar.is_admissible`. *An
   inadmissible path is not a valid conversation.* (cas-synthetic imports `is_admissible` and never
   calls it, so an illegal path would otherwise render happily.)
2. **PERSISTENCE BROKEN BY CONSTRUCTION.** No two consecutive **labelled** turns carry the same
   prescribed board. The corpus persistence rate is therefore **0.0000**, verified and printed by the
   generate stage and written into `corpus_prescribed_structure.CORPUS_PERSISTENCE_RATE` in the
   report. **A reader must be able to see that stickiness was actually removed; that is why this
   number is mandatory output.**
3. **REAL ENUM MEMBERS.** Paths are materialised as `TurnType` members, never bare strings.
   `TurnType` subclasses `str`, so a string path survives every dict lookup and every `==` and then
   dies at the `.value` call inside `to_dict()`.

### 5B.3 The path bank (frozen; `next_board_test.SDG_FORCED_PATHS`)

Six constructed paths, cycled with distinct render seeds (`SEED_SDG_BASE = 880000 + conv_id`, a
**new** constant — no v1 seed is edited).

| path | prescribed board sequence |
|---|---|
| P1 | B1 B0 B5 B1 B0 B5 B1 |
| P2 | B0 B5 B1 B0 B5 B1 |
| P3 | B1 B0 B5 B0 B1 B0 B5 |
| P4 | B0 B1 B0 B5 B1 |
| P5 | B1 B0 B5 B1 B0 B5 B1 |
| P6 | B1 B0 B1 B0 B5 B1 |

**Realised properties, measured on the 4-conversation smoke and re-measured on every run:**

- corpus persistence rate **0.0000**;
- prescribed mix B1 9 / B5 7 / B0 9, **B0 share 0.3600** — inside the Gate 0 cap of 0.40 (the cap
  binds by construction: every `PLAN` must be preceded by a `MIRROR` or `ANSWER`, both B0, so
  `#B0 ≥ #B5` is a structural constraint on any admissible bank);
- realised transitions `B0→B1 2, B0→B5 7, B1→B0 6, B5→B0 1, B5→B1 5` — **all five realisable
  transitions present**, `B1→B5` absent because it is structurally impossible (§3B.3).

Full run: **36 conversations** (6 paths × 6 replicates, the same corpus size as the api arm),
≈ 228 labelled turns and ≈ 192 possible pairs, so the existing `G0_MIN_PAIRS = 90` floor remains
satisfiable at consensus coverage ≥ 0.69. **`G0_MIN_PAIRS` is NOT changed by v2.**

### 5B.4 Reader panel structure — a holdout that is NOT a separation control

`gen_provider` is the literal sentinel **`"sdg"`**, kept so provenance is never lost when these
records sit beside api records (cas-synthetic's own output carries no marker of being synthetic).
Because `"sdg"` is outside `ORDER`, **no reader can ever equal it**, and two things follow that must
be stated rather than quietly enjoyed:

- **GATE 4 becomes VACUOUSLY TRUE.** That is genuine separation by construction, but a vacuous pass
  is not evidence of anything — the same objection §5.4 raises against Rev 0.3's hardcoded
  `g4 = True`. The report says so in those words.
- **Four readers would label every turn**, silently breaking `build_arm`'s hardcoded
  `combinations(range(3), 2)` (which would score only the first 3 of 4) and `fleiss_kappa`'s fixed
  row width (which would change what `G0_FLEISS_MIN = 0.35` means), and raising labelling cost 33 %.

A new per-turn field **`excluded_reader`** therefore carries a deterministic
**structure-preserving holdout** (`ORDER[conv_id % 4]`) so the panel stays **exactly 3 wide**. In the
api arm `excluded_reader == gen_provider`, so api behaviour is byte-identical. **In the SDG arm this
holdout is NOT a separation control and is never described as one.**

### 5B.5 Limitations specific to this arm, disclosed in advance

- **LOCO folds are NOT topically independent.** The path bank repeats every 6 conversations, so a
  held-out fold can share a path — and a template draw — with its training folds. The api arm's
  "no seed prompt is reused" guarantee (§5.2) **does not hold here.**
- **`--n-turns` is ignored.** Path length is prescribed.
- **~~CONTROL 5 / GATE 6 is EXPECTED TO FAIL BY CONSTRUCTION.~~ — WITHDRAWN AT v2.1. THE
  EXPECTATION WAS FALSE, AND IT WAS THE NAMED SAFEGUARD.**
  v2 asserted that the forced path deterministically ties the preceding user move to the next turn
  type, so the scripted stimulus would predict b_{N+1} very well and GATE 6 would fail — and gave
  that as reason #1 why the sequential test could not carry a claim (§6B.3). **Measured on the
  realised corpus, GATE 6 PASSES:**

  | quantity | value |
  |---|---|
  | `usermove_acc` (CONTROL 5, LOCO) | **0.7188** |
  | `board_acc` (LOCO Markov) | **0.8750** |
  | margin | **+0.1562** ≥ 0.05 → **GATE 6 PASSES** |

  The realised follow-up ids are only `U-NONE` (→ B5, 60/60), `U-OPEN` (→ B1 66 / B0 54) and
  `U-REPAIR` (→ B0, 12/12). The stimulus is **informative but not sufficient**, because `U-OPEN`
  splits across two boards. **The one gate v2 nominated to neutralise the sequential arm does not
  fire.**
- **THE REAL REASON THE SEQUENTIAL TEST CANNOT CARRY A CLAIM (v2.1 replacement): THE TRANSITION
  MATRIX IS AUTHORED.** In the forced-path bank **`B1→B0` runs at 60/60 = 100 % deterministic**. A
  Markov model of b_N → b_{N+1} is therefore reading **the path bank we wrote down**, not a property
  of any text or any model. That is a property of the *design*, holds regardless of any gate, and is
  the correct ground for demoting the sequential result.
- **Provenance marking is mandatory.** Every SDG record carries `gen_provider: "sdg"`, the source
  path, the forced path, the render seed and the template disclosure. These records must **never** be
  merged into a corpus of real model outputs without that marker.

---

## 6. THE STATISTIC

Per turn, the **consensus label** is the majority among the readers who returned a label, requiring
**≥ 2 present and ≥ 2 agreeing**. A pair (b_N, b_{N+1}) is usable only if **both** turns have a
consensus label.

**The two Gate-0 metrics are deliberately decoupled** (Rev 0.4): *agreement* (Fleiss κ, raw pairwise) is
computed on **complete cases only** — all 3 readers present — so it is never inflated by non-random
dropout on hard items; *consensus* may form from 2 present labels, so one missing reader does not
destroy a usable turn. Rev 0.3 required 3-of-3 **and** a majority for every usable pair, which is what
made its pair floor unreachable.

**Primary statistic: `board_acc`.** Leave-one-conversation-out (LOCO) cross-validated accuracy of a
first-order Markov predictor:

- On the training folds, count transitions `C[b_N][b_{N+1}]`.
- Predict `argmax_{b'} C[b_N][b']`.
- If `b_N` is unseen in training, back off to the training mode of `b_{N+1}`.
- Groups = conversations, so a conversation is never in both train and test.

**Tie-break rule, disclosed.** Ties resolve first on the **training-fold overall frequency** of the tied
classes, then on sorted class name. Rev 0.3 broke ties on name alone; because `"B0"` sorts before
`B1..B5`, *every* tie in the transition table and every backoff tie resolved to the "none dominates"
class — deterministic, but a systematic tilt. The frequency tie-break removes it; the residual
alphabetical tie-break (used only when frequencies are also tied) is disclosed here and is the only
remaining arbitrary element.

**Reported alongside — descriptive, not gating:** the full transition matrix, per-class marginals, and
NMI(b_N ; b_{N+1}) **with its own within-conversation permutation null and empirical p** (NMI is
upward-biased at small n and is clearly non-zero under independence, so quoting it without a null
invites over-reading).

> **MULTIPLICITY CLAUSE (binding).** `board_acc` is the single preregistered primary statistic, named in
> advance, singular, computed one way. **No individual transition cell may be reported as a result.**
> "B1→B3 runs at 3× chance" is forbidden — that is the forking path this clause closes. The 36-cell
> matrix may be shown in full as description, never mined for a claim.

---

## 6B. THE PRIMARY STATISTIC IN THE SDG ARM — **RUBRIC ADHERENCE, NOT CALIBRATION** (v2, renamed v2.1)

> **v2.1 RENAME, BINDING.** This section was titled *"GROUND-TRUTH ACCURACY"* and its statistic was
> called `gt_acc`. **Both names are withdrawn as unearned** (§3B.0, KILL 1). The truth was never
> known independently — it was authored from these same strings through this same rubric. The
> statistic is now **`rubric_adherence_acc`**, and it is a **RUBRIC-ADHERENCE / READER-RELIABILITY**
> check. **"CALIBRATION AGAINST KNOWN GROUND TRUTH" and "CALIBRATED" are DELETED as available
> verdicts throughout this document and throughout the runner.**

### 6B.1 `rubric_adherence_acc`

**`rubric_adherence_acc` = agreement between the PRESCRIBED board and the CONSENSUS READ board**,
over every turn that has both. Consensus is formed exactly as in §6 (≥ 2 agreeing among ≥ 2 present)
— the consensus rule is **not** changed by v2 or v2.1.

**What it can legitimately be read as:** *do three blind commercial readers apply this rubric to
fixed strings the way its author did?* That is a fact about **readers** and a **rubric**. It is
**never** a fact about model behaviour, and given §3B.0 it has **no informative range** even as a
reader check — a pass is guaranteed by the authoring, a fail indicates reader noise.

Reported with it, all mandatory:

- the **confusion matrix**, prescribed × read, in full;
- **per-class recall** — and, at v2.1, **two separate denominators**, because conflating them hides
  non-random dropout:
  - **`n_prescribed_by_design`** — the design count (**B1 90 · B5 60 · B0 78** on the frozen bank);
  - **`n_prescribed_with_consensus`** — how many of those **survived to a consensus label**;
  - **`consensus_coverage_for_this_prescribed_class`** — the ratio, reported **per class**.

  > **v2 DEFECT, CORRECTED.** v2 promised *"per-class recall, with `n_prescribed` beside each
  > class"*, which a reader would take as the design count. The implementation filtered to consensus
  > turns **first** and then counted, so `n_prescribed` was really the **survivor** count. If readers
  > systematically failed to reach consensus on one class, the accuracy would be computed on a
  > survivor set and **the loss would have been invisible** — there was no per-class consensus
  > coverage figure anywhere in the report. Both denominators are now printed.

  - an explicit `UNREACHABLE` note on **B2, B3, B4**, whose design count is **0** (§3B.2), and an
    explicit `NO CONSENSUS SURVIVED` note on any class whose survivor count is 0;
  - a `weak_mapping` marker on any class carrying a WEAK row (**B5** via `PLAN`, **B0** via
    `REFUSE_CLAIM` — §3B.1a).
- the **chance level, named**. Two numbers are printed and only one is operative:
  - `1/6 = 0.1667` — the uniform label chance. **NOT the operative baseline**; never quote it as the
    bar cleared.
  - **always-predict-the-modal-PRESCRIBED-class** — *this* is the operative chance level. On the
    frozen bank the modal prescribed class (B1) runs at **90/228 = 0.3947**, so an instrument that
    reads nothing at all still scores ≈ 0.39.

  > **v2.1 CONSISTENCY FIX.** v2 computed this chance level **in-sample** (`_mode` over all
  > `y_true`) while the surface control it is compared against was **LOCO**. Mixing an in-sample
  > chance with a cross-validated control is inconsistent. It was *conservative* here (it biases the
  > chance level up), but that is not a reason to leave it unstated. The **gating** chance level is
  > now **LOCO-measured on the same folds**; the in-sample value is still printed beside it as
  > `chance_modal_prescribed_class_in_sample_not_gating`.
- a **paired cluster bootstrap over conversations** on `ra_acc − chance` and on `ra_acc − surface`,
  using the same machinery and the same `BOOT_LOWER_Q = 5` rule as every v1 margin.

### 6B.2 The surface control on the same task — **the kill was already obtained, for $0**

The three v1 surface baselines (**char TF‑IDF(3,5)**, **word unigram**, **length**) are run on the
prescribed-board task itself: predict the *prescribed* board from turn N's raw text, under LOCO folds
grouped by conversation, vectorisers refit per fold, `C` tuned on grouped inner splits of the
training fold only. `ra_surface_acc = max(char, word, length)`.

> **PREREGISTERED KILL (GATE RA‑2).** If the surface model matches or beats the reader panel on this
> task, **the arm is KILLED OUTRIGHT.** The reader would be doing nothing that a bag-of-chars over a
> 38-string lookup table could not do, and no amount of relabelling, re-prompting, or adding readers
> repairs that.

#### 6B.2a MEASURED RESULT — the gate is UNSATISFIABLE (v2.1)

Computed locally on the realised 36-conversation corpus (228 labelled turns), **before any labelling
call, at $0**:

| surface model | accuracy on the prescribed-board task |
|---|---|
| char TF‑IDF(3,5) | **1.0000** |
| word unigram | **1.0000** |
| **raw character count** (one feature) | **1.0000** |

| corpus property | value |
|---|---|
| distinct assistant strings | **38** |
| strings mapping to more than one board | **0** → exact-string lookup is a **bijection** |
| per-class length ranges | B0 **30–97** · B1 **exactly 104** · B5 **108–117** → **disjoint** |

Because `ra_surface_acc = 1.0000`, GATE RA‑2 requires `ra_acc − 1.0000 ≥ 0.05`, which is
**impossible for any accuracy whatsoever**. **The arm's verdict is fixed before a single labelling
call.**

> **v2 UNDERSTATED THIS, AND THAT IS CORRECTED HERE.** v2's dry-run did cite `char = 1.0000` but
> attributed it to *"template-prefix memorisation"* and the CAS-expression slot. The **length**
> result shows the corpus is surface-determined **outright**: the three classes do not overlap in
> length, so one feature suffices. This is not a learnable-prefix artefact; it is a **bijection**.

> **v2 SAID THE WRONG THING ABOUT WHAT TO DO NEXT.** v2 §6B.2 concluded: *"If the owner runs it
> anyway, it is to obtain that kill on the record."* **That kill is obtainable at $0** by the
> ~30-line computation above — **with no reader panel, no ~256 labelling calls and no hours of GLM
> serialisation.** **Preregistering a foregone kill is not a study.**

**BINDING REMEDY.** `--stage precheck` performs exactly this computation locally and writes
`precheck_report_sdg.json`. **`--stage label` REFUSES TO RUN** while the precheck fails. The arm is
**WITHDRAWN BY DEFAULT**. The override `--allow-surface-determined-corpus` exists only so the block
is explicit rather than silent; using it is **PREREG-DEVIATING** and must be logged in §14, and the
resulting numbers are **NOT LICENSED** under any verdict.

**To revive the arm, both of the following are required:**
1. **replace the corpus** with text whose **surface does not determine the label** (many distinct
   realisations per class, overlapping lengths, no one-template classes); and
2. **derive the answer key independently of the rubric** (§3B.0).

**Relaxing `SDG_PRECHECK_SURFACE_MAX` is not a revival; it only hides the defect.**

### 6B.3 The sequential test is SECONDARY and DESCRIPTIVE in this arm

`board_acc`, CONTROLS 1–8 and GATES 1–8 are **still computed and still written to the report**,
unchanged. In the SDG arm they are **descriptive only** and carry no claim.

> **v2.1 CORRECTION TO THE REASON GIVEN.** v2 gave two reasons; **the first was false**. v2 said
> *"the forced path ties the user move to the turn type (so GATE 6 fails by construction)"*.
> **Measured: `usermove_acc` = 0.7188 vs `board_acc` = 0.8750, margin +0.1562 — GATE 6 PASSES**
> (§5B.5). The safeguard v2 relied on does not fire.
>
> **The surviving and correct reason is the second one: THE TRANSITION MATRIX IS AUTHORED.**
> `B1→B0` runs at **60/60 = 100 %** in the frozen bank, so `board_acc` measures the path bank we
> wrote, not any property of text or model. This holds regardless of any gate outcome.

**Verdict hygiene (v2.1).** The report exposes the sequential result under
`SEQUENTIAL_VERDICT_secondary`, never under `VERDICT` — and that field is now **hard-mapped onto a
vocabulary that excludes the word SUPPORTED** (`DESCRIPTIVE-ONLY` / `NOT-LICENSED`). See §8B.

---

## 7. CONTROLS

All controls use the **identical LOCO fold split**, including CONTROL 6 (which has no fitted parameters
but is nonetheless computed over the same test indices, so this sentence is literally true — in Rev 0.3
it was not).

**CONTROL 1 — SURFACE (mandatory req. 1; PRIMARY KILL).** Three baselines on **turn N's raw text**
(the same 1000-char truncation the readers saw), predicting b_{N+1} under the same LOCO folds, with the
vectoriser **refit inside every training fold**:

| baseline | recipe (identical to `acceptance_gate.gate_surface_separability`) |
|---|---|
| char | `TfidfVectorizer(analyzer="char", ngram_range=(3,5), max_features=5000)` |
| **word unigram** | `CountVectorizer(max_features=3000, stop_words="english", binary=True)` |
| length | raw character count |

each → `LogisticRegression(max_iter=500, random_state=42)`, **with `C` tuned on grouped inner splits of
the training fold only** (grid 0.25 / 1 / 4 / 16).
**`surface_acc = max(char_acc, word_acc, length_acc)`.**

> **Rev 0.3 handicapped this control twice.** (a) Only the char baseline ran on the predictive task —
> yet **word unigram (topic) is the single most likely surface route** from turn N's text to turn N+1's
> board, and it was never run. (b) `LogisticRegression` at default `C` on ~145 training rows against 5000
> sparse char features regularises toward the majority class, so `char_acc` lands near `marginal_acc` and
> GATE 1 collapses into GATE 2 — leaving the "PRIMARY KILL" with almost no independent teeth. The
> information given to the control was correctly matched (same text, same folds, refit per fold); the
> model class was not allowed to be competitive. It is now.

> If `surface_acc >= board_acc`, **the board abstraction adds nothing** and the test fails.

*Diagnostic companion (not gating):* same-turn surface separability — can a surface model recover a
turn's **own** label? Reported two ways: a **LOCO-grouped** version (this is the one that flags) and a
direct call to `acceptance_gate.gate_surface_separability` for comparability only. The latter uses
`StratifiedKFold` with **no conversation grouping**, so same-conversation text leaks across folds and
inflates it, and it silently returns `{"error": …}` whenever any class has fewer than 5 members — which
is likely here. **Note also that its `chance` parameter is accepted but never referenced in its body:
passing `chance=1/6` configures nothing.** Our preregistered flag is `same_turn_surface_acc > 0.667`
(4× chance) on the **grouped** numbers → labels are largely a surface artifact, which *downgrades* a
positive result to "surface-driven" but does not by itself kill the sequential claim.

**CONTROL 2 — MARGINAL BASE RATE (mandatory req. 2).** Always predict the training-fold mode of
b_{N+1}. Statistic: `marginal_acc`. With the B0 cap at 0.40 this can legitimately reach ≈ 0.40; the
board predictor must beat *this*, not 1/6.

**CONTROL 3 — SHUFFLE NULL (mandatory req. 3), WITHIN-CONVERSATION.** Hold `b_N` and the grouping fixed;
permute `b_{N+1}` **inside each conversation** (block permutation), 1000 trials, `random.Random(0)`.
Report null mean, 95th percentile, and empirical `p = (#{trials ≥ real} + 1)/1001`.

> **Rev 0.3's null was mis-specified and did not test what it claimed.** It permuted `b_{N+1}` across
> **all** pairs globally, which also destroys **conversation-level clustering**. Each conversation is one
> seed prompt on one topic generated by one model, so its turns are label-homogeneous for reasons that
> have nothing to do with transitions; under a global null that homogeneity **alone** drives `board_acc`
> far above the null and GATE 3 passes with **no transition structure whatsoever**. Rev 0.3's claim that
> the shuffle "preserves both marginals and destroys only the temporal link" was false. A
> within-conversation permutation preserves each conversation's label composition and isolates exactly
> the temporal link. **This is the significance test of the whole study; as written in Rev 0.3 its
> p-value was not interpretable.**
>
> **Consequence, stated in advance:** this null is *strong*. A purely **persistent** (sticky) label
> sequence will **not** clear it, because within-conversation permutation of a run-structured sequence
> still leaves many adjacent identical pairs. That is intended: persistence is CONTROL 6's business, and
> GATE 3 is meant to find transition structure, not stickiness.

**CONTROL 4 — GENERATOR/LABELLER SEPARATION (mandatory req. 4).** Structural; computed, not asserted (§5.4).

**CONTROL 5 — USER-MOVE.** Predict b_{N+1} from the follow-up template id alone. Statistic:
`usermove_acc`. **Gated as a HARD KILL** (GATE 6).

**CONTROL 6 — PERSISTENCE / STICKINESS.** Predict `b_{N+1} = b_N`. Statistic: `persistence_acc`.

**CONTROL 7 — TURN POSITION.** Predict b_{N+1} from the turn index alone. Statistic: `turnpos_acc`.
**Now gated** (GATE 7). Rev 0.3 computed it and gated nothing, so a b_N that was largely a function of
turn position (very plausible — turn 1 is a fresh answer, later turns are defences and action lists)
would let the Markov table merely re-encode the position→label map while every gate still passed.

**CONTROL 8 — MATCHED DISCOURSE TAXONOMY (§4.3).** Same panel, same corpus, same prediction test, on
the D1–D5/D0 taxonomy. Compared **on the pairs usable in both arms**, so the margin is paired.
Statistic: `alt_acc`. Gated as GATE 8.

### 7B. EVERY CONTROL IS RETAINED IN THE SDG ARM (v2) — nothing is dropped

The SDG arm **adds** a control and **removes none**. Explicitly retained, unchanged:

| retained | note in the SDG arm |
|---|---|
| i.i.d. **WITH-replacement** follow-ups | the api arm's `FOLLOWUPS` bank and `SEED_FOLLOWUP_BASE` are untouched; the SDG arm's analogous stimulus id is the preceding user move type, recorded per turn as `followup_id` and fed to CONTROL 5 exactly as before |
| **within-conversation permutation null** (CONTROL 3, 1000 trials, `SEED_PERM_NULL = 0`) | unchanged |
| **per-batch, per-reader alias ids** (`SEED_ALIAS_BASE`) | unchanged — no uid, conversation or turn index ever reaches a reader |
| **`finish_reason == "stop"` enforcement** | unchanged; reasoning-only still refused by default |
| **batch-alias intersection** (a fabricated id can never overwrite a genuine label) | unchanged |
| **exact-id-set completeness** on every parsed array | unchanged |
| **same-conversation batch-collision gating** (hard abort + Gate 0 check) | unchanged |
| **repair rounds** | unchanged |
| **JSONL checkpointing and skip-on-restart** in both API stages | unchanged; SDG generation is local and also checkpoints |
| **the full surface battery INCLUDING the word-unigram arm** | unchanged on the sequential task **and** replicated on the new ground-truth task (§6B.2) |
| **paired cluster bootstrap** on every gating margin | unchanged, and extended to the three new GT margins |
| **LOCO folds grouped by conversation**, vectorisers refit per fold, `C` tuned inside the training fold | unchanged |
| **multiplicity clause** (§6) | unchanged, and extended: no individual **confusion-matrix cell** may be reported as a result either |
| **sha256 immutability record** of prereg + runner | unchanged |

**ADDED:** CONTROL RA — the surface battery on the prescribed-board task (§6B.2), gated as
**GATE RA‑2** *(named CONTROL GT / GATE GT‑2 at v2; renamed at v2.1, thresholds unchanged)*. **It
measured 1.0000 and withdrew the arm** (§6B.2a).

**ADDED at v2.1:** the **$0 precheck** (`--stage precheck`), which runs CONTROL RA locally with no
reader panel and **blocks `--stage label`** while the corpus is surface-determined.

**Vacuous in the SDG arm, and labelled as such:** CONTROL 4 (generator/labeller separation), because
`gen_provider = "sdg"` lies outside the reader panel (§5B.4).

---

## 8. DECISION RULE

Gates are evaluated **in order**. Gate 0 is read **before** any prediction number — and this is now
**enforceable**, not aspirational: `--stage gate0` prints agreement and coverage **only**, computes no
prediction statistic, and writes its own report.

### GATE 0 — AGREEMENT AND VIABILITY FLOOR (mandatory req. 5). Preregistered VACUOUS escape.

| check | threshold | rationale |
|---|---|---|
| Fleiss κ, 3 readers, 6 classes, **complete cases only** | **≥ 0.35** | below this, readers are not assigning a shared thing. Reachable on prior evidence: 0.4479 on a 40-way task, 0.5489 on a 12-way task |
| complete cases available for κ | **≥ 60** | κ on fewer is not interpretable |
| raw pairwise agreement, complete cases only | **≥ max(0.50, P_e + 0.35·(1 − P_e))** | see note below |
| complete-case coverage | **≥ 0.60** of turns | honest κ denominator; measured comparators are l1_real 0.556 (4 readers) and l2_wiring 0.694 |
| consensus coverage (≥2 agreeing of ≥2 present) | **≥ 0.70** of turns | a majority rule must not stand on thin coverage — `l3_minimal_pairs` fired a majority rule that could never trigger |
| B0 share of consensus labels | **≤ 0.40** | if the taxonomy does not fit the corpus, nothing downstream means anything |
| residual same-conversation batch collisions | **= 0** | hard; §5.5 |
| usable pairs after all filtering | **≥ 90** (full run) | see arithmetic below |

**The raw-agreement floor is DERIVED, not asserted.** With 6 classes and the permitted concentration,
chance agreement `P_e = Σ p_k²` is roughly 0.25, so a flat raw floor of 0.50 implies κ ≈ 0.33 — *below*
the 0.35 κ floor. Rev 0.3 stated both as independent hurdles without ever computing their joint
difficulty. Rev 0.4 computes `P_e` from the **observed** marginals and sets the binding raw floor to
`P_e + 0.35·(1 − P_e)`, so the two are one hurdle expressed twice, with an absolute 0.50 kept as a
second, explicit floor. The report prints `P_e`, both floors, and which one bound.

**Pair-count arithmetic, shown so the thresholds are jointly satisfiable** (this is the Rev 0.3
auto-doom, corrected):

> 36 conversations × 7 turns = **252 turns**, and 36 × 6 = **216 possible pairs**. A pair needs a
> consensus label at both ends, so `usable_pairs ≈ 216 · c²` where `c` is consensus coverage:
> **c = 0.70 → 106 pairs** (floor 90, ✓ with margin) · c = 0.65 → 91 · c = 0.60 → 78 (fails, but the
> 0.70 coverage floor fails first — the ordering is consistent).
> Rev 0.3 set a **100-pair floor on 30 × 6 = 150 possible pairs**, which silently demanded **c ≥ 0.82**
> while stating **0.70** two rows above it in the same table. At this panel's measured coverage
> (0.556–0.694) that bought a **near-certain VACUOUS** for the entire spend. The three changes that fix
> it are the repair pass (§5.7), the decoupled metrics (§6), and this larger, arithmetically consistent
> corpus.

**If ANY Gate 0 check fails → VERDICT = VACUOUS.** The prediction statistics are still computed and
written (so the run is not wasted), but they are **not evidence** and may not be cited. The report says
so in those words.

### GATE 1 — SURFACE (primary kill)
`board_acc − surface_acc ≥ 0.05` **and** the 5th percentile of the paired cluster-bootstrap margin > 0.

### GATE 2 — MARGINAL
`board_acc − marginal_acc ≥ 0.05` **and** bootstrap p5 > 0.

### GATE 3 — WITHIN-CONVERSATION PERMUTATION NULL
`p_perm < 0.05` **and** `board_acc > null_p95`.

### GATE 4 — SEPARATION
Computed violation set is empty. A violation → **REJECTED**, not a crash.

### GATE 5 (downgrades — does not kill)
`board_acc − persistence_acc ≥ 0.05` (+ bootstrap p5 > 0). If it fails, the licensed wording drops to
*"board labels are temporally persistent"* and may **not** say *"transition structure predicts the next
board."*

### GATE 6 — USER MOVE (**HARD KILL** in Rev 0.4)
`board_acc − usermove_acc ≥ 0.05` (+ bootstrap p5 > 0). Failure → **REJECTED**. A signal produced by the
scripted stimulus is a design artifact and must not be reportable as support.

### GATE 7 (downgrades — does not kill)
`board_acc − turnpos_acc ≥ 0.05` (+ bootstrap p5 > 0).

### GATE 8 — MATCHED TAXONOMY (downgrades; governs the CAS-specificity wording)
`board_acc − alt_acc ≥ 0.05` on shared pairs (+ bootstrap p5 > 0).
- **Pass** → the finding is *board-taxonomy-specific beyond one matched 6-class discourse taxonomy on
  the same corpus and panel*. It is still **not** "CAS-specific" in any deeper sense — one matched
  control is not the space of possible taxonomies.
- **Fail** → CAS-specificity **stays GREY**, the verdict is downgraded to SUPPORTED (weak), and any
  sequential signal must be reported as **generic conversational structure**.
- **Not run** → GREY by default.

### 8.1 UNCERTAINTY AND POWER — how the 0.05 margins are to be read

Every 0.05 margin is a **preregistered threshold on a paired cluster bootstrap over conversations**
(2000 resamples, seed 7): the point margin must clear 0.05 **and** the 5th percentile must exceed 0. A
confidence interval on every gating margin is written to the report.

This is stated because the naked margins were not defensible. At ~106 pairs over 36 conversations
filling a 6×6 = 36-cell table there are ~3 observations per cell, so the LOCO Markov table backs off to
the training mode for many rows and `board_acc` converges mechanically toward `marginal_acc`;
observations also cluster (up to 6 pairs per conversation), so effective n is well below the pair count.
At p ≈ 0.4 and n ≈ 106 the SE of an accuracy is ≈ 0.05, so a 0.05 point margin is about **1 SE**.
**A failed GATE 2 at this n may reflect power, not truth**, and the report says so.

### VERDICTS

- **VACUOUS** — Gate 0 failed. Nothing is licensed. Repair the lens or the corpus, then re-run.
- **REJECTED** — Gate 0 passed, any of Gates 1, 2, 3, 4, **6** failed.
- **SUPPORTED (weak)** — Gates 0–4 and 6 passed, one or more of Gates 5, 7, 8 failed. Wording is
  downgraded as specified above.
- **SUPPORTED** — Gates 0–8 all passed.

No verdict is amendable after the run. No gate may be moved after seeing a number. The analyze stage
writes a **sha256 of this document and of `next_board_test.py`** into the report; compare it against the
hash recorded when the first labelling call ran. A mismatch means the preregistration or the runner was
edited after data collection began, and the run is not preregistered.

---

## 8B. THE SDG-ARM DECISION RULE (v2, **rewritten at v2.1**)

> **THE ARM IS WITHDRAWN. The rule below is retained so the withdrawal is auditable, not so the arm
> can be run.** `--stage label` refuses to execute while the precheck fails (§6B.2).

Gate 0 is read first here too. **A Gate 0 failure voids the rubric-adherence number exactly as it
voids the prediction numbers**, and the console says so on that line itself.

### GATE 0 IS NOT THE SAME HURDLE IN THE TWO ARMS (v2.1 disclosure)

Gate 0's floors — Fleiss κ ≥ 0.35, the marginal-derived raw-agreement floor, the B0-share cap — were
calibrated against **natural text**. On a **3-effective-class corpus of 38 byte-distinct strings**,
κ is **inflated** and the derived raw floor is **trivially cleared**: because the observed marginals
concentrate on three classes, `Pe` rises and the derived floor moves from ≈ 0.35 toward ≈ 0.58 while
observed agreement moves far higher. **Passing Gate 0 in the SDG arm is not comparable to passing it
in the api arm** and must never be presented as the same check. The report carries this as
`GATE0_NOT_COMPARABLE_ACROSS_ARMS`.

### KILL — MAPPING CIRCULARITY (`KILL_MAPPING_CIRCULARITY`) — **NEW NAMED KILL at v2.1**

Preregistered **alongside GATE RA‑2**, and it **fires unconditionally for this answer key** (§3B.0).
The key was authored by reading these same strings through this same rubric, so
`rubric_adherence_acc` has **no informative range**.

- **Effect:** the SDG verdict is **`NOT LICENSED — MAPPING CIRCULAR`** regardless of every other
  gate. **`CALIBRATED` is not reachable at any value of any statistic.**

### GATE RA‑1 — READS ABOVE CHANCE *(renamed from GATE GT‑1; thresholds unchanged in value)*
All three must hold:
- `ra_acc ≥ RA_ACC_MIN = 0.60`;
- `ra_acc − chance_modal_prescribed_class_LOCO ≥ RA_MARGIN_OVER_CHANCE = 0.10`;
- the 5th percentile of the paired cluster-bootstrap margin `ra_minus_chance > 0`.

### GATE RA‑2 — BEATS SURFACE ON THE SAME TASK (**PRIMARY KILL**) *(renamed from GATE GT‑2)*
- `ra_acc − ra_surface_acc ≥ RA_MARGIN_OVER_SURFACE = 0.05` **and** bootstrap p5 `> 0`.
- **Failure → the arm is KILLED OUTRIGHT** (§6B.2). Not repairable by relabelling.
- **MEASURED: `ra_surface_acc = 1.0000`, so this gate is UNSATISFIABLE by any accuracy.** The arm is
  withdrawn on this ground alone, independently of the circularity kill.

### ALL KILL GATES FAIL CLOSED (v2.1 fix)

> **v2 DEFECT: THE PRIMARY KILL FAILED OPEN.** In the v2 implementation `surface_acc` was
> initialised to `0.0` and the surface battery ran only `if folds and len(set(y_true)) >= 2`. When
> it did **not** run, the comparison vector was filled with zeros and GATE GT‑2 evaluated
> `(gt_acc − 0.0) ≥ 0.05` — i.e. **the PRIMARY KILL silently PASSED with no surface control having
> been computed at all.** `stage_analyze` had the same pattern for GATE 1
> (`... if folds else (0.0, [])`).

**Binding rule, both arms:** if a control **cannot be computed**, its gate is **`null`** — never
`true` — and the verdict is **VACUOUS**. A kill gate must fail closed. This is enforced by
`controls_computed` in `stage_analyze` and by `surface_computed` in `rubric_adherence_check`, and the
report states it under `gates.gates_are_null_when_uncomputable`.

### ADDED CONSTANTS

`RA_ACC_MIN`, `RA_MARGIN_OVER_CHANCE`, `RA_MARGIN_OVER_SURFACE`, `SEED_SDG_BASE`,
`SDG_PRECHECK_SURFACE_MAX`, `SDG_MAPPING_CIRCULARITY_KILL`, `SDG_WEAK_MAPPINGS`,
`SDG_SHORT_TEMPLATE_TURN_TYPES`, `SDG_MIN_TURN_CHARS` are **ADDED** constants. The v2 names
`GT_ACC_MIN` / `GT_MARGIN_OVER_CHANCE` / `GT_MARGIN_OVER_SURFACE` were **renamed** to the `RA_*`
forms **with their values unchanged**; no v2 threshold moved. **No v1 constant, threshold or seed is
edited by v2 or v2.1** — the frozen-constants banner and the sha256 immutability record remain
meaningful, and this document is amended in the same commit as the runner.

### SDG VERDICTS (v2.1 — `CALIBRATED` DELETED)

- **`NOT LICENSED — MAPPING CIRCULAR`** — fires unconditionally for this answer key (§3B.0). **This
  is the standing verdict of the arm.**
- **VACUOUS** — Gate 0 failed, or controls could not be computed, or no prescribed board survived to
  a consensus label. Nothing is licensed.
- **`NOT LICENSED — SURFACE CONTROL WON`** — GATE RA‑2 failed. Say it in those words: *a surface
  model over the template table read the prescribed board as well as the panel did.*
- **NOT RUBRIC-ADHERENT** — GATE RA‑1 failed.
- **RUBRIC-ADHERENT** — reachable only if the circularity kill were removed (§3B.0) **and** RA‑1 and
  RA‑2 both passed. It would license **only** the reader-reliability reading below.

> **~~CALIBRATED (B1/B5/B0 only)~~ — DELETED at v2.1.** Not an available verdict. The word
> `CALIBRATED`, and the phrase `CALIBRATION AGAINST KNOWN GROUND TRUTH`, appear nowhere in the runner
> or the report except inside sentences that withdraw them.

**There is no `SUPPORTED` verdict in this arm, and v2.1 makes that structural rather than
aspirational.**

> **v2 DEFECT: THE CODE CONTRADICTED THIS SENTENCE.** v2 §8B said *"There is no SUPPORTED verdict in
> this arm. The word is reserved for the api arm."* But the runner built
> `sequential_verdict = f"{verdict} (SECONDARY / DESCRIPTIVE ONLY -- forced-path corpus)"` from the
> **unmodified api ladder**, so it could read **`SUPPORTED (weak) (SECONDARY / DESCRIPTIVE ONLY …)`**
> — written to `SEQUENTIAL_VERDICT_secondary` and printed to console. **Anyone grepping the SDG
> report for a verdict could lift the token `SUPPORTED` off a template corpus.**
>
> **Fixed at v2.1:** the sdg sequential verdict is **hard-mapped** onto a vocabulary that excludes
> the word — `SUPPORTED → DESCRIPTIVE-ONLY`, `SUPPORTED (weak) → DESCRIPTIVE-ONLY (weak …)`,
> `REJECTED → NOT-LICENSED (sequential controls failed)`, `VACUOUS → NOT-LICENSED (vacuous)`.

### PROVENANCE IS DECIDED BY THE DATA, NOT BY A CLI FLAG (v2.1 fix)

> **v2 DEFECT.** `is_sdg` was `bool(A.generator == "sdg")`. Since `--label-file` has a CLI override
> and `--stage analyze` does not require `--generator`, the command
> `--stage analyze --label-file labels_board_sdg.json` (flag omitted) analysed **template data as an
> api run**: `VERDICT` came off the sequential ladder, all five SDG claim-ceiling entries were
> dropped, and `TEMPLATE_DISCLOSURE` was **affirmatively written as** *"n/a — the api arm's turns are
> real model outputs"* — **a FALSE PROVENANCE STATEMENT in the report, on the exact axis this
> document spends most of its length defending.**

**Fixed:** `is_sdg` is derived from `payload["generator"]` and from the presence of a `gt_board`
answer key. A disagreement with the flag **aborts the run** with an explicit message. The report
records `generator_recorded_in_label_payload` and `provenance_source`.

### GATE 8 IS `null` IN THE SDG ARM (v2.1 fix)

`GATE8_beats_matched_taxonomy` was still computed and written as a **boolean** in the SDG report even
though ceiling §10B.14 states that **no CAS-specificity claim is available from this arm**. The
`CAS_SPECIFICITY` prose overrode it, but a bare `true` sitting in `gates/` is a **lift surface**. It
is now forced to `null` in the sdg arm.

### BOTH SURFACE KILLS ARE SURFACED AT THE TOP LEVEL (v2.1 fix)

`KILLED_BY_SURFACE_CONTROL` is computed **only from the sequential surface** and can read `false`
while the **ground-truth-task** surface won outright at 1.0000. A second top-level flag
**`KILLED_BY_SURFACE_CONTROL_GT`** is now written beside it, so a skim of the report's headline keys
cannot miss the kill that actually decides this arm.

**Licensed wording if the arm were ever revived and passed — verbatim and exhaustive:**

> *"On a template-rendered forced-transition corpus, a 3-model blind reader panel assigned the
> prescribed board to a turn at `rubric_adherence_acc`, above the LOCO modal-class chance level and
> above the strongest of three surface models on the same task. This is a READER-RELIABILITY result:
> it says three commercial models apply this rubric to fixed strings the way its author did. The text
> is a lookup table, the answer key is ours, and coverage is B1, B5 and B0 only — B2, B3 and B4 have
> zero instances. It says NOTHING about whether board structure exists in natural model output, and
> it is NOT a calibration."*

Anything beyond that sentence is outside the preregistration. **As of v2.1 no such result is
obtainable, because the arm is withdrawn.**

---

## 9. KILL STATEMENT

> **The idea is KILLED if `surface_acc >= board_acc`**, where `surface_acc = max(char, word-unigram,
> length)` on turn N's raw text.

That means: a surface classifier reading the raw text of turn N predicts turn N+1's board as well as, or
better than, the board *label* of turn N does. In that case the board abstraction is a lossy re-encoding
of surface text and contributes nothing of its own. This is **not repairable** by relabelling, by adding
readers, by adding board classes, or by a better prompt — the information was never in the abstraction.
A v2 would need a different corpus and a different construct, argued from scratch.

Three further kills:

- **Design-artifact kill (GATE 6):** if the scripted follow-up predicts b_{N+1} as well as the board
  label does, the "prediction" is the stimulus, not the board. REJECTED.
- **Taxonomy kill:** if Fleiss κ < 0.20, blind readers cannot assign board types to single turns at all.
  That kills the *board taxonomy as an output lens*, not merely the sequential claim, and blocks any
  downstream board work until repaired.
- **Fit kill:** if B0 share > 0.60, the five-board taxonomy does not describe ordinary assistant turns.
  Report it and stop; do not re-run with a "better" rubric on the same corpus.

**SDG-arm kill (GATE RA‑2), stated separately because it is a different claim — and it HAS FIRED:**

> **The arm is KILLED if `ra_surface_acc >= ra_acc`**, or if the RA‑2 margin fails.
>
> **STATUS at v2.1: FIRED.** `ra_surface_acc = 1.0000` on char, word **and raw character count**
> (§6B.2a), so the margin cannot be met by any accuracy. **The arm is WITHDRAWN.** A second,
> independent kill — **mapping circularity** (§3B.0) — fires unconditionally on the same corpus.

The text is a fixed lookup table with one template each for `PLAN`, `REFUSE` and `REFUSE_CLAIM` and a
fixed syntactic slot for every CAS expression. If a char/word model recovers the prescribed board as
well as the panel does, the panel is reading the template prefix — the same **template-prefix
memorisation** that produced the 97 pp swing in the paraphrase diagnostics, and the same
**surface-separability wall** that killed the Gate‑2 G1 pilot at 0.48 / 0.42 against a ≤ 0.10
requirement. **Not repairable within this corpus.** A repair means a corpus whose text is not
authored, which is the api arm, which is the arm that was rejected for stickiness. That tension is
the honest state of this line of work and is not resolved by v2.

**Recorded dead ends that must not be re-attempted as repairs:** adding more classes to lower the
random-overlap floor (the 20-part run: lift +0.231 vs +0.210, coverage 92%→58%, 7 classes unused);
and raising `--workers` to speed GLM up (it produces 429 storms, not throughput — and the semaphore
caps GLM concurrency at 1 regardless).

---

## 10. CLAIM CEILING

Binding. Inherited from `CAS_LENS_REPAIR_ROADMAP_20260818.md` and extended.

1. **Output space only.** Nothing here is a measurement from inside a model. No weights claim, no
   activation claim, no localisation claim. The Component Atlas already returned NULL/GREY on that
   question and this test does not revisit it.
2. **What a GATE 1 pass actually licenses is narrow.** `b_N` is a 3-model **LLM consensus reading**;
   the control is a TF-IDF/count logistic regression. Beating it licenses *"an LLM ensemble reading of
   turn N beats surface models of turn N"* — **not** "the board abstraction carries information". Only
   **GATE 8** speaks to whether the *board* taxonomy specifically matters, and one matched control is
   not the space of taxonomies. CAS-specificity is **GREY unless GATE 8 passes**, and even then the
   licensed phrase is "board-taxonomy-specific beyond one matched discourse taxonomy" — never
   "CAS-specific" (mandatory req. 6).
3. **The sequencing claim is ours, not the book's** (§3). The book describes intra-board stage
   sequencing richly and inter-board sequencing not at all.
4. **Design values, not measurements.** Every board parameter in the source is an author's design
   choice. The rubric judges observable text behaviour and claims nothing about β, Q, f0 or CMRR.
5. **Rating rubric, not physics.** A pass licenses exactly: *"the CCB board lens is a reliable,
   non-arbitrary annotation of assistant turns whose value at turn N carries information about turn N+1
   beyond surface text, marginals, a within-conversation permutation null, the scripted user move and
   turn position, within one 36-conversation corpus of four models."* It licenses no product-ACCEPT, no
   human-cognition claim, no cross-model-universality claim, and no generalisation past the seven-turn,
   follow-up-scripted setting.
6. **One corpus, one panel.** A single run with four related commercial models is not replication.
7. **No individual transition cell is a result** (§6 multiplicity clause).

### 10B. ADDITIONAL CEILINGS THAT BIND ONLY THE SDG ARM (v2, extended v2.1)

7a. **THE ARM IS WITHDRAWN ON TWO NAMED KILLS (v2.1) — this ceiling governs every one below it.**
    (1) **MAPPING CIRCULARITY** (§3B.0): the answer key was authored from these same strings through
    this same rubric, so the primary statistic has **no informative range**. (2) **SURFACE-DETERMINED
    CORPUS** (§6B.2a): char, word **and raw character count** all score **1.0000** on the
    prescribed-board task, so GATE RA‑2 is **unsatisfiable by any accuracy**. Both were obtained for
    **$0**, before any labelling call. **Nothing in this arm is licensed.**
7b. **"CALIBRATED" AND "KNOWN GROUND TRUTH" ARE WITHDRAWN TERMS (v2.1).** The truth was not known
    independently; it was authored by the process under test. At most this arm could have measured
    **RUBRIC ADHERENCE / READER RELIABILITY** — a fact about readers and a rubric.
7c. **THE WORD "SUPPORTED" IS NOT AVAILABLE IN THIS ARM (v2.1),** structurally: the sequential
    verdict is hard-mapped onto `DESCRIPTIVE-ONLY` / `NOT-LICENSED` so the token cannot be lifted off
    a template corpus by anyone grepping the report.
7d. **GATE 0 IS NOT THE SAME HURDLE HERE (v2.1).** Its floors were calibrated on natural text; on a
    3-effective-class corpus of 38 byte-distinct strings κ is inflated and the derived raw floor is
    trivially cleared. A Gate 0 pass in this arm is **not comparable** to one in the api arm.
8. **THE CLAIM IS DIFFERENT AND WEAKER — AND, AT v2.1, RETRACTED ENTIRELY.** v2 called this a
   synthetic known-fault board validated **by fiat**, **SOFTWARE-ONLY EVIDENCE**, licensing exactly
   *"the blind reader panel reads a turn constructed to be board X as X."* **Even that is not
   available**: a known-fault board earns its name because the fault is injected **independently of
   the instrument** that must detect it, and here the "fault" is a string chosen *because* the rubric
   would read it a certain way. The board is not known-fault; it is **instrument-shaped**. It
   licenses **nothing** about natural model output and may never be reported as if it did.
9. **THE TEXT IS A LOOKUP TABLE, NOT GENERATION.** 22 authored strings, 7 CAS expressions, one
   template each for `PLAN` / `REFUSE` / `REFUSE_CLAIM`. Any number from this arm is a fact about the
   lens and the templates. These records must never be merged into a corpus of real outputs without
   the `gen_provider: "sdg"` marker.
10. **THE TURN-TYPE → BOARD MAPPING IS OURS** (§3B), **AND TWO OF ITS ROWS ARE WEAK.** Dialog acts
    are not boards; no framework supplies the correspondence. `PLAN → B5` is flagged as a **partial**
    match (no capacity/budget/throttle/silence content). **`REFUSE_CLAIM → B0` is flagged WEAK at
    v2.1 on the same footing** (§3B.1a): it is an explicit decline plus a competing reading, which
    plausibly reads as **B1** or **B3**, so a reader choosing either is scored WRONG against an
    author judgement with no greater standing than the reading under test. **The effective mapping
    is SIX turn types, not eleven** — no forced path uses `ACK` or `EMPATHIZE` (§3B.1b).
11. **THREE OF FIVE BOARDS HAVE NO INSTANCES WHATEVER HAPPENS.** B2, B3, B4 have zero prescribed
    instances and cannot be constructed from this generator (§3B.2). `B1→B5` is structurally
    unrealisable (§3B.3).
11a. **THE `cas_state_after` SEQUENCE IS NOISE, NOT EVOLUTION (v2.1).** `gen_conversation_sdg`
    threads `current_cas` into `_render_turn`, but **`_render_turn` never reads it** — it re-samples
    an independent CAS row from `_USER_TEMPLATES` on every load-bearing turn, and cas-synthetic's own
    docstring states *"There is NO coherence constraint across CAS states within a single record."*
    The CAS sequence of these records must never be described as evolution, refinement, or a response
    to a `REPAIR` turn. It is irrelevant to the prescribed boards, which come from the turn **type**.
12. **LOCO FOLDS ARE NOT TOPICALLY INDEPENDENT HERE** (§5B.5). The path bank repeats every 6
    conversations.
13. **GATE 4 IS VACUOUS HERE** (§5B.4), and `excluded_reader` is a structure-preserving holdout, not
    a separation control.
14. **NO CAS-SPECIFICITY CLAIM IS AVAILABLE FROM THIS ARM.** A matched-taxonomy comparison on
    template text measures the template table. CAS-specificity stays **GREY** regardless of GATE 8.
15. **NO INDIVIDUAL CONFUSION-MATRIX CELL IS A RESULT** — the §6 multiplicity clause extends to the
    calibration matrix.

---

## 11. COST ESTIMATE

| stage | calls | notes |
|---|---|---|
| generate (full) | **252** | 36 convos × 7 turns, sequential *within* a conversation, parallel across; `max_tokens=800`, `temperature=0.7`; context grows to ~5k by turn 7 |
| label, board arm | **128** | each reader labels the 3/4 of turns it did **not** generate: 189 turns ÷ 6 per batch = 32 batches × 4 readers |
| label, alt arm (CONTROL 8) | **128** | same corpus, same panel, D-taxonomy |
| repair pass | **~40–70** | batches of 3, ≤2 rounds, only the uids a reader failed to return |
| analyze | 0 | local; sklearn + numpy only |
| **full total** | **~550–580 calls** | |
| **`--smoke` total** | **~30 calls** | 12 gen + 8 label calls per arm × 2 arms + repair |

> Rev 0.3's arithmetic was wrong: it wrote "180 turns ÷ 6 = 30 batches × 3 readers = 90". Labelling is
> **4 readers × ⌈(3/4 · turns)/6⌉**, because every reader labels three-quarters of the corpus — not
> 3 readers labelling all of it.

**Tokens and money.** Rev 0.3 claimed ~0.32M output while simultaneously arguing that `max_tokens=16000`
is non-negotiable *because* readers spend most of it on trace — internally inconsistent (296 label calls
× 16k is a **4.7M ceiling**). Realistic: **~1.4M input, ~0.9–2.0M output**. At this panel's blended rates
that is roughly **$8–$25** for the full two-arm run; smoke is well under **$1**.

**Wall clock.** Dominated by GLM, pinned to `Semaphore(1)` plus a 7.0 s proactive interval:
GLM *labelling* is ~64 serialized calls (32 per arm) ≈ **45–60 min**; GLM *generation* is ~63 serialized
calls ≈ **20–35 min**. Rev 0.3 omitted the generation leg entirely. Budget **2–3.5 hours** for the full
run. Worker pools are sized to the **sum of the per-provider semaphores (9)** so a thread blocked on GLM
never starves gemini/deepseek/qwen; raising `--workers` does not raise GLM throughput.

**SDG-ARM COST AT v2.1: $0, AND IT STAYS $0.** The SDG arm is **withdrawn** and `--stage label`
refuses to run for it (§6B.2). The ~256 labelling calls and the 45–60 min of GLM serialisation the
arm would have cost are **not spent**. Generation is local and template-rendered (no API), and
`--stage precheck` is local sklearn/numpy. **The two kills cost nothing.**

**Spend discipline.**
1. `--stage generate --smoke`, then **eyeball three turns**. (A Rev 0.3 smoke run produced ~143-char
   gemini turns on one seed against ~4000-char deepseek turns — read the sample line the stage prints.)
2. **sdg arm only:** `--stage precheck --generator sdg` — **$0**, no reader panel, no network. If it
   returns `ARM WITHDRAWN — DO NOT LABEL`, **stop here.** This is the cheapest kill in the design and
   it must be run before any labelling of any forced-path corpus, present or future.
3. `--stage label --taxonomy board --smoke`.
4. `--stage gate0 --smoke` — this prints agreement/coverage and **no** prediction number.
5. **Smoke can never PASS Gate 0** — but the *reason* differs by arm, and v2 stated only the api one.
   - **api arm:** the relaxed pair floor of 8 is exactly the number of pairs the smoke corpus can
     produce (4 convos × 2), so passing would require 100 % consensus coverage.
   - **sdg arm (v2.1 correction):** that reason is **false here.** An sdg smoke of 4 conversations
     yields **~21 pairs**, not 8, because forced paths are 5–7 labelled turns long rather than 3. It
     is still blocked — by **`G0_COMPLETE_N_MIN = 60`**, against only **25 labelled turns available**
     — but by that floor, not the pair floor.

   **Smoke is a RED-LIGHT-ONLY check** in both arms: a smoke κ near zero is enough to stop before the
   full spend; a smoke VACUOUS is not a stop signal and must not be read as one.

---

## 12. WHAT WOULD COME NEXT (not part of v1, listed so it is not mistaken for a finding)

1. **A second matched taxonomy, and a second corpus.** GATE 8 passing against one matched taxonomy is a
   real finding but not a general one.
2. **Set-valued board reading** — if v1 is VACUOUS on the B0 share or on κ, the natural v2 is multi-label
   boards scored by Jaccard against a rate-preserving shuffled null, exactly as `l2_circuit.py` does.
   Single-label forcing is the most likely v1 failure mode, given that the circuit reading (sets) beat
   the single-cell reading (0.61 vs 0.53) on the same corpus.
3. **Naturalistic user turns** — remove the scripted follow-up entirely, at the cost of a user-simulator
   model and a fourth confound.
4. **Higher-order structure** — a second-order Markov or a duration model, but only with the n to
   support it; at 216 possible pairs a 6×6 table is already thin (§8.1).

---

## 13. REVISION LOG — Rev 0.3 → Rev 0.4

Every change below is a correction made **before any Rev 0.4 data was collected**. Rev 0.3's smoke data
is quarantined and unusable.

**FATAL**
1. **True-by-construction follow-ups.** Permutation (without replacement) → **i.i.d. with replacement**;
   GATE 6 promoted from downgrade to **hard kill**; the false claim in §5.3 deleted.
2. **Permutation null mis-specified.** Global shuffle → **within-conversation block permutation**, which
   preserves conversation composition and isolates the temporal link.
3. **Gate 0 arithmetically and empirically unreachable.** Added a repair pass; decoupled agreement
   (complete cases) from consensus (≥2 of ≥2 present); grew the corpus to 36 × 7 = 216 possible pairs;
   restated the floors as jointly satisfiable and **showed the arithmetic**.

**MAJOR**
4. **Position index leaked to readers** — `uid` in the prompt → per-batch, per-reader **alias ids**.
5. **CONTROL 7 gated nothing** → **GATE 7** added.
6. **Labels could be harvested from a reasoning trace** → strict acceptance (finish_reason, JSON array
   from the answer, exact id set, reasoning-only refused by default).
7. **Hallucinated ids accepted and could overwrite real labels** → batch-alias intersection, first-write-wins.
8. **Residual same-conversation batch collisions reported but not gated** → **hard abort + Gate 0 check**.
9. **No checkpointing or resume** → JSONL append + skip-on-restart in both API stages.
10. **Surface control handicapped** → word-unigram and length added to the predictive task; `C` tuned
    inside the training fold; kill on `max(char, word, length)`.
11. **No uncertainty or power analysis** → paired cluster bootstrap over conversations on every gating
    margin; explicit power note.
12. **Gate 0's two agreement floors mutually inconsistent** → raw floor **derived** from observed marginals.
13. **Gate 1 licensed less than the framing implied** → **matched-taxonomy arm folded into v1** as
    CONTROL 8 / GATE 8.

**MINOR** — corrected call arithmetic (§11); corrected token/cost figures; disclosed that
`gate_surface_separability`'s `chance` argument is unused; same-turn diagnostic moved to LOCO-grouped
folds; CONTROL 6 computed over the LOCO folds so §7's claim is literally true; `_mode` tie-break changed
to frequency-then-name and disclosed; NMI given its own null; `--stage gate0` added; smoke declared
red-light-only; partial conversations kept instead of discarded; GATE 4 computed rather than hardcoded;
worker pool sized to the provider semaphores; multiplicity clause added; sha256 immutability record added.

**UNCHANGED because it was already correct** — the claim ceiling (§10) and the honest-scope disclosure
(§3) survive the review intact, as does the base-rate handling (GATE 2 compares against the LOCO-measured
marginal, never 1/6); §0 now states the absolute always-predict-mode ceiling implied by the B0 ≤ 0.40 cap.

---

## 13B. REVISION LOG — Rev 0.4 → v2

**v2 is ADDITIVE.** The `--generator api` arm is Rev 0.4 in every respect: no v1 constant, seed,
threshold, gate, control, verdict or licensed wording is edited. `--generator` defaults to `api`, so
every existing command line behaves exactly as before, and `build_conversation_plan` returns an
identical plan (verified).

**ADDED**
1. `--generator {api,sdg}` (default `api`), and the derived-path `tag` extended to `_sdg` so an SDG
   run can never contaminate an api run's `label_calls*.jsonl`, `labels_alt*.json` or
   `gate0_report_*.json` — the three derived paths that have **no CLI override**.
2. Forced-path builder + admissibility / persistence / enum-type validation (§5B.2), driving
   cas-synthetic's `_render_turn` directly. cas-synthetic is **imported by file path, never copied**.
3. The turn-type → board mapping, preregistered as **our assumption** (§3B), with `NONE → EXCLUDED`
   for every turn type with no defensible board.
4. `gt_board` / `gt_turn_type` / `excluded_reader` carried end-to-end, **including through the
   `payload["turns"]` projection in `stage_label`** — the silent-break point where any unnamed
   per-turn field is dropped without an error and would otherwise never reach the analysis.
5. `ground_truth_calibration()` — `gt_acc`, confusion matrix, per-class recall, both chance levels,
   the surface battery on the GT task, three bootstrap margins, GATE GT‑1 and GATE GT‑2.
   **RENAMED at v2.1** to `rubric_adherence_check()` / `rubric_adherence_acc` / GATE RA‑1 / GATE RA‑2,
   with `KILL_MAPPING_CIRCULARITY` added and `CALIBRATED` deleted from the verdict vocabulary
   (§3B.0, §6B, §8B).
6. `prescribed_corpus_structure()` — realised transition matrix and **corpus persistence rate**,
   printed and written so a reader can verify stickiness was removed.
7. Constants `SEED_SDG_BASE`, `GT_ACC_MIN`, `GT_MARGIN_OVER_CHANCE`, `GT_MARGIN_OVER_SURFACE`
   *(the three `GT_*` renamed to `RA_*` at v2.1 with values unchanged; v2.1 further adds
   `SDG_PRECHECK_SURFACE_MAX`, `SDG_MAPPING_CIRCULARITY_KILL`, `SDG_WEAK_MAPPINGS`,
   `SDG_SHORT_TEMPLATE_TURN_TYPES`, `SDG_MIN_TURN_CHARS`)*.
8. Template, mapping, ceiling and vacuity disclosures in the console banner, in the report's first
   keys, and in `claim_ceiling`.

**CHANGED (behaviour-preserving in the api arm)**
9. Reader-panel selection now reads `excluded_reader` via `_excluded_reader()` instead of
   `gen_provider` directly, at all four sites (`stage_label` main pass and repair want-set,
   `collect_marks`, `build_arm`). In the api arm `excluded_reader == gen_provider`, so the api arm is
   unchanged; in the SDG arm it keeps the panel exactly 3 wide (§5B.4).
10. `VERDICT` in the SDG arm reports the **calibration** verdict; the sequential verdict moves to
    `SEQUENTIAL_VERDICT_secondary`.
11. Gate 0 is now printed **before** the calibration line as well as before the prediction lines.

**UNCHANGED AND DELIBERATELY SO** — every Rev 0.4 control, every Rev 0.4 threshold, the consensus
rule, the multiplicity clause, the claim ceiling §10, the honest-scope disclosure §3, and the sha256
immutability record.

---

## 13C. REVISION LOG — v2 -> v2.1 (SDG ARM WITHDRAWN)

**FATAL-A. Circular calibration.** The answer key was authored by reading the rendered strings
through the rubric under test. Statistic renamed to rubric adherence; CALIBRATED deleted as a
verdict; mapping circularity preregistered as a named kill. (Sec 3B.0, 6B, 8B)

**FATAL-B. The arm was unfalsifiable.** Surface accuracy on the prescribed-board task is 1.0000 on
char, word AND raw character count, so GATE RA-2 is unsatisfiable by any accuracy. New `--stage
precheck` takes the kill for $0 and `--stage label` refuses to spend. (Sec 6B.2a)

**MAJOR-C.** The preregistered expectation that GATE 6 would fail by construction was FALSE
(measured +0.1562, GATE 6 passes). Replaced by the real reason: the transition matrix is authored.

**MAJOR-D.** The runner could emit the token SUPPORTED in the sdg arm, contradicting Sec 8B. Now
hard-mapped out of the vocabulary.

**MAJOR-E.** Provenance was decided by a CLI flag; omitting it wrote a false provenance statement.
Now derived from the data, with a fatal mismatch check.

**MAJOR-F.** The primary kill failed open when its control could not be computed. All kill gates now
fail closed (null, never true; verdict VACUOUS).

**MAJOR-G.** `n_prescribed` was the survivor count, hiding non-random dropout. Split into design
count and consensus count, with per-class coverage.

**MAJOR-H.** `REFUSE_CLAIM -> B0` flagged WEAK on the same footing as `PLAN -> B5`.

**MINORS.** Effective mapping is 6 turn types not 11 (short-template paths now rejected at load
time); Gate 0 non-comparability disclosed; chance level made LOCO; smoke-block reason corrected per
arm; GATE 8 forced null in the sdg arm; `KILLED_BY_SURFACE_CONTROL_GT` added; dead `n_convos`
clamp removed; `cas_state_after` documented as noise, not evolution.

**API ARM: NO REGRESSION.** Shared-code edits are additive keys, the data-derived `is_sdg`, the
fail-closed gate helper, and a tag line that is the identity for `api`. `build_conversation_plan`,
`FOLLOWUPS`, `SEED_FOLLOWUP_BASE` and every v1 constant are untouched; pre-v2 label files still
analyse.

---

## 14. AMENDMENT LOG

**2026-08-19 — v2. Claim change, mapping disclosure, template disclosure.**
Recorded **before** any v2 labelling call. Reason: the Rev 0.4 api-corpus smoke was REJECTED, and
every cause was a corpus problem — stickiness (persistence 0.5238 vs Markov 0.5079), unstable
generators, empty turns, and no ground truth (labels came only from readers at κ ≈ 0.54, never from
an answer key). v2 adds a forced-transition corpus that fixes all four by prescribing the path.

Three things are amended, all of them disclosures rather than relaxations:

1. **THE PRIMARY CLAIM CHANGES IN THE NEW ARM.** From **ecological prediction** to **INSTRUMENT
   CALIBRATION AGAINST KNOWN GROUND TRUTH** — a different and weaker claim, a *synthetic known-fault
   board … validated against ground truth by fiat, SOFTWARE-ONLY EVIDENCE*. The sequential test is
   demoted to secondary and descriptive. See §0.1, §6B, §8B, §10B.
2. **THE TURN-TYPE → BOARD MAPPING IS OURS, NOT THE FRAMEWORK'S.** Disclosed on the same footing as
   the §3 sequencing disclosure. Turn types with no defensible board map to NONE and are excluded,
   not forced. Three of five boards (B2, B3, B4) are structurally unreachable and the instrument
   stays uncalibrated for them. See §3B.
3. **THE SDG RENDERS FROM TEMPLATES, NOT FROM A MODEL.** Stated in the first paragraph of this
   document. Consequence: the surface control matters **more**, and a surface win **kills** the
   calibration claim outright (GATE GT‑2). A mechanical dry-run with simulated readers already gives
   `gt_acc 0.9538` vs `char 1.0000`, so **a kill is the expected outcome** and is recorded here in
   advance.

No gate was moved after seeing data. No v1 constant was edited. The api arm's verdicts, thresholds
and licensed wording are untouched. This document and `next_board_test.py` are amended in the same
commit so the sha256 immutability comparison stays meaningful.

---

**2026-08-19 — v2.1. THE SDG ARM IS WITHDRAWN. The v2 claim above is RETRACTED.**
Recorded **before any v2 labelling call was made** — no SDG labelling data exists, and none will be
collected under this design. Reason: adversarial review of the v2 preregistration, plus a ~30-line
local computation over the realised corpus, found **two independent fatal defects**. Neither required
running the arm; both cost **$0**.

**RETRACTED from the v2 entry above:**

1. **~~"THE PRIMARY CLAIM CHANGES … to INSTRUMENT CALIBRATION AGAINST KNOWN GROUND TRUTH"~~ —
   RETRACTED.** The answer key was authored by **reading the rendered template strings through the
   same rubric the reader panel is given**. B1's entire prescribed class is **one byte-identical
   string** (90 of 228 turns) whose wording is a near-verbatim cue for the B1 rubric's lead clause;
   B5 is one template against a rubric clause it paraphrases. **v2 §3B.1's justification column IS
   the derivation.** The statistic therefore has **no informative range** — a pass is guaranteed by
   the authoring, a fail indicates reader noise. **"KNOWN GROUND TRUTH" was unearned.** v2 disclosed
   that the mapping was *ours* (§3B, §10B.10) but **never disclosed that it was derived from the same
   text via the same rubric**, which is the defect that voids the statistic.
   **Remedy:** `gt_acc` → **`rubric_adherence_acc`**; the section is renamed to **RUBRIC ADHERENCE /
   READER RELIABILITY**; **`CALIBRATED` and `CALIBRATION AGAINST KNOWN GROUND TRUTH` are DELETED as
   available verdicts**; **mapping circularity is preregistered as a NAMED KILL**
   (`KILL_MAPPING_CIRCULARITY`) alongside GATE RA‑2. See §3B.0, §6B, §8B.
2. **~~"a kill is the expected outcome and is recorded here in advance"~~ — INSUFFICIENT. The arm was
   UNFALSIFIABLE: GATE RA‑2 could not pass at all.** Measured with LOCO folds grouped by
   conversation: char TF‑IDF **1.0000**, word unigram **1.0000**, **raw character count 1.0000**. The
   corpus is **38 distinct strings, zero ambiguous** (exact-string lookup is a **bijection**) with
   **disjoint per-class length ranges** (B0 30–97, B1 exactly 104, B5 108–117). Since
   `surface_acc = 1.0000`, the gate `ra_acc − 1.0000 ≥ 0.05` is **impossible for any accuracy**. v2
   attributed the 1.0000 to *"template-prefix memorisation"*, which **understated** it — the length
   result shows the corpus is surface-determined outright. v2 §6B.2 said *"If the owner runs it
   anyway, it is to obtain that kill on the record"*; **that kill is obtainable at $0**, with no
   reader panel, no ~256 labelling calls and no hours of GLM serialisation.
   **Preregistering a foregone kill is not a study.**
   **Remedy:** new **`--stage precheck`** takes both kills locally for **$0**; **`--stage label`
   REFUSES TO SPEND MONEY** while it fails; the arm is **WITHDRAWN BY DEFAULT**. Reviving it requires
   a corpus whose **surface does not determine the label** *and* an answer key not derived from the
   rubric — **not a relaxed bar**. See §6B.2a.

**Also corrected at v2.1 (each was a defect in v2, none is a relaxation):**

3. **A PREREGISTERED EMPIRICAL EXPECTATION WAS FALSE, AND IT WAS THE NAMED SAFEGUARD.** v2 §5B.5 and
   §6B.3 stated *"CONTROL 5 / GATE 6 is EXPECTED TO FAIL BY CONSTRUCTION"* and gave that as reason #1
   why the sequential test could not carry a claim. **Measured: `usermove_acc` 0.7188 vs `board_acc`
   0.8750, margin +0.1562 — GATE 6 PASSES.** Corrected to the real reason: **the transition matrix is
   authored** (`B1→B0` = 60/60 = 100 %), so `board_acc` measures the path bank.
4. **THE CODE CONTRADICTED THE PREREG ON THE WORD "SUPPORTED".** §8B said the word was reserved for
   the api arm, but the runner wrapped the **unmodified api ladder**, so
   `SEQUENTIAL_VERDICT_secondary` could read `SUPPORTED (weak) (SECONDARY …)`. Now **hard-mapped**
   onto `DESCRIPTIVE-ONLY` / `NOT-LICENSED`.
5. **PROVENANCE WAS DECIDED BY A CLI FLAG, NOT BY THE DATA.** `--stage analyze --label-file
   labels_board_sdg.json` with `--generator` omitted analysed template data as an api run and wrote
   `TEMPLATE_DISCLOSURE: "n/a — the api arm's turns are real model outputs"` — **a false provenance
   statement**. `is_sdg` is now derived from the payload and the answer key, and a mismatch **aborts**.
6. **THE PRIMARY KILL FAILED OPEN.** `surface_acc` was initialised to `0.0` and the battery ran only
   `if folds and …`; when it did not run, the gate evaluated `(acc − 0.0) ≥ 0.05` and **silently
   PASSED with no control computed**. `stage_analyze` had the same pattern for GATE 1. **All kill
   gates now fail closed:** an uncomputable control yields `null`, never `true`, and a VACUOUS verdict.
7. **`n_prescribed` WAS NOT THE PRESCRIBED COUNT.** It counted only instances that survived to a
   consensus label, hiding non-random dropout. Split into **`n_prescribed_by_design`** and
   **`n_prescribed_with_consensus`**, with **per-class consensus coverage** now reported.
8. **`REFUSE_CLAIM → B0` WAS AN UNFLAGGED WEAK MAPPING.** v2 flagged `PLAN → B5` but presented the
   B0 group as *"the honest read"*. B0 is a **positive prescription readers are scored against**;
   `REFUSE_CLAIM` plausibly reads as B1 or B3 (v2 §3B.2 already conceded it "comes nearest" to B3).
   **Now flagged WEAK on the same footing**, machine-readably.
9. **Minor corrections.** The effective mapping is **6 turn types, not 11** (no path uses `ACK` or
   `EMPATHIZE`, whose templates are all under the 30-char floor — now a load-time failure rather than
   a latent silent-truncation trap). **Gate 0 is not the same hurdle across arms** — disclosed. The
   chance level is now **LOCO** rather than in-sample, matching the control it is compared against.
   The **smoke-cannot-pass reason differs by arm** — an sdg smoke yields ~21 pairs, not 8, and is
   blocked by `G0_COMPLETE_N_MIN`. **`GATE8` is forced to `null`** in the sdg arm. A second top-level
   **`KILLED_BY_SURFACE_CONTROL_GT`** flag is written. The dead `n_convos` clamp in `main()` was
   removed so the plan's capacity check is live. The `cas_state_after` sequence is documented as
   **noise, not evolution**.

**No gate was moved after seeing data**, because **no data was collected in this arm**. The `RA_*`
thresholds keep the v2 values under new names. **No v1 constant, threshold, seed or verdict was
edited by v2 or v2.1**, and the `--generator api` arm is untouched — verified: the only shared-code
edits are additive keys, the data-derived `is_sdg`, the fail-closed gate helper, and a tag line that
is the identity for `api`. This document and `next_board_test.py` are amended in the same commit so
the sha256 immutability comparison stays meaningful.

*(No other amendments. Any change after the first `--stage label` call must be recorded here with a
timestamp and a reason, and any gate moved after seeing data invalidates the preregistration. Using
`--allow-reasoning-only` or `--allow-surface-determined-corpus` is a deviation and must be logged
here.)*
