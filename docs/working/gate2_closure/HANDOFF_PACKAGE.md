# CAS Harness — Engineering Handoff Package

**Status:** Gate 2 OPEN at `0.38`. Nothing in this document licenses a product claim.
**Written:** 2026-07-27
**Audience:** an incoming engineering team with no prior context on this campaign.

---

## 1. How to read this document

This is an honest inventory, not a pitch. It separates four things that are easy to blur:

| Bucket | Meaning |
|---|---|
| **Licensed** | Passed a pre-registered gate. Claimable, within its stated ceiling. |
| **Not licensed** | Ran correctly, did not clear its bar. The apparatus worked; the result was null. |
| **Void** | The measurement was degenerate or the construction was broken. Not a null result — no result. |
| **Open** | Not yet run, or blocked. |

A null result from a correct instrument is **normal and valuable**. A working scale that reads
zero is still a working scale. Most of this campaign is null, and that is reported plainly.

---

## 2. The one licensed result

**`SCRAMBLE-NULL-COMPLETION-v1`** — pre-registration commit `3385aa63`, model
`EleutherAI/pythia-1b`, seeds `1..200`.

| Criterion | Bar | Observed | Result |
|---|---|---|---|
| `E1` below 2.5% of null | — | `0/200` fresh scrambles beat it | **PASS** |
| `E2` bootstrap CI excludes 0 | — | `[0.208537, 0.255985]` | **PASS** |
| `E3` margin beyond lexical | `>= 0.10` | `0.183721` | **PASS** |
| `E4` no saturation | — | clear | **PASS** |
| `W1` ordinal correlation (secondary) | `p < 0.05` | `perm_p = 0.089291` | **FAIL** |

Exact permutation `p = 0.004975`.

**What this licenses, exactly:** the TKS grid's assignment of meanings to cells is
non-arbitrary beyond what vocabulary overlap alone explains, on `pythia-1b`.

**What it does NOT license:** that the grid is *derived*, that TKS beats any alternative
scheme, or anything about other models. The secondary ordinal test (`W1`) failed, so the
"structure is ordered along a gradient" reading is **not** supported.

---

## 2b. The diagnostic that reframes the ledger

**`JUDGE-POSITIVE-CONTROL-v1`** — pre-registration `8ab16b2d` + Amendment 1 (`35c9f62a`),
verdict `JUDGE_FUNCTIONAL`. Full write-up: `RESULT_JUDGE_POSITIVE_CONTROL.md`.

Sixteen instruments ran without ever asking whether the apparatus can detect a signal that is
certainly present. When finally asked:

| Tier | Item text | Accuracy | vs chance `0.0357` |
|---|---|---|---|
| `T0` | definition, verbatim | `1.000` (`28/28`) | `p = 3.0e-41` |
| `T1` | mechanical rewrite | `1.000` (`160/160`) | `p = 2.8e-232` |
| `T2` | real authored scenarios | `0.0429` (`12/280`) | **`p = 0.3011`** |

**Two findings, both load-bearing:**

1. **The harness is sound.** `T0 = 28/28`. Wiring, parsing, validation all correct. The eight
   `NOT_LICENSED` verdicts below stand as interpretable nulls rather than plumbing failures.
2. **The authored scenarios carry no recoverable signal.** `T2` is statistically
   indistinguishable from guessing — `p = 0.3011`, 95% CI `[0.0249, 1.0000]` contains chance.

**Caveat that must travel with the `T1` number:** `T1` items stay lexically close to their
targets, so a pure string matcher would also score `1.000`. `T1` proves the apparatus reads and
maps correctly; it does **not** prove semantic understanding. A middle tier that preserves
meaning while breaking lexical overlap does not exist yet.

---

## 3. Infrastructure that works and is reusable

This is the real asset. Every item below is built, tested, and independent of whether any
particular hypothesis held.

| Component | Path | What it does |
|---|---|---|
| **Admissibility guard** | `research/reconciled/experiment_admissibility.py` | 11 tests. Computes *honest* effective sample size and refuses inadmissible designs. Load-bearing inside `injection_detection_scorer.py` — raises `InadmissibleDatasetError` before any probe is fit. |
| **Matched A/B driver** | `docs/working/gate2_closure/matched_ab_20260726/run_matched_ab.py` | Full two-arm pipeline: authoring, blinding, cross-judging, surface controls, bootstrap, permutation. Ran `2,780` pairs cleanly. |
| **Judge parse repair** | `.../judge_parse_repair.py` | Repairs malformed LLM JSON (fences, prose, trailing commas, truncation) without altering content. |
| **Surface precheck** | `docs/working/cjt_breakdown/surface_precheck.py` | VADER-based check that prompt text does not itself contain the effect being measured. Catches construction defects before GPU spend. |
| **Regression guard** | `check_invariants.py` (commit `0923146b`) | One check per defect found during this campaign. |
| **Signature/receipt chain** | `cas-forex/cas_forex/pcba_authority.py` | 24 receipts, 4 signed, `verify()` True 4/4. |

**The apparatus is sound.** The `2,780`-pair run had correct blinding, symmetric authoring
constraints, a full judge cross to remove choice-set anchoring, char-3-5-gram *and* word
TF-IDF surface controls, `10,000`-iteration bootstrap, and label-preserving permutation.
That is a properly built experiment. It returned null.

---

## 4. Complete verdict ledger

Every instrument run in this campaign. No omissions.

### Geometry track (`docs/working/gate2_closure/geometry/`)

| Instrument | Verdict |
|---|---|
| `scramble_null` | **PRIMARY_LICENSED** \| SECONDARY_NOT_LICENSED |
| `fisher` | VOID_SATURATED |
| `fisher_sweep` | NOT_LICENSED |
| `output_simplex` | NOT_LICENSED |
| `reversal` | NOT_LICENSED |
| `trajectory` | NOT_LICENSED |

### Definition A/B track (`docs/working/gate2_closure/item4_arms/`)

| Instrument | Verdict |
|---|---|
| `v2_pythia1b` | NOT_LICENSED |
| `v3_composition` | VOID_SAME_DISEASE |
| `v4_masked` | NOT_LICENSED |
| `v4_wronglayer` | FAIL_not_layer_matched |
| `v5_multiplicative` | NOT_LICENSED |
| `v5b_simspace` | VOID_DEGENERATE_METRIC |
| `matched_ab_20260726` (scaled) | **NOT_LICENSED_DEGENERATE** |

### Book-prediction track (`docs/working/cjt_breakdown/`)

| Instrument | Verdict |
|---|---|
| Vocabulary escalation ladder | Abandoned — `B4` surface gate failed 3× with contamination *increasing* each revision |
| Repetition-pressure inversion | VOID on `B4` construction guard; **open decision** |
| β (CJT gain) measurement | Computable; hypothesis unsupported — injection `0.452` vs benign `0.427`, separation `+0.025` |

### Diagnostic track

| Instrument | Verdict |
|---|---|
| `JUDGE-POSITIVE-CONTROL-v1` | **`JUDGE_FUNCTIONAL`** — all 4 criteria pass. Harness sound; defect localized to scenario authoring. See §2b. |

**Tally: 1 licensed, 1 diagnostic pass, 8 not licensed, 4 void, 2 abandoned/open.**

---

## 5. The headline failure, and why it is not what it looks like

The scaled matched A/B is the campaign's most careful experiment. Its result:

```
arm A (original TKS wording)          accuracy 0.0636
arm D (generic shorthand composition) accuracy 0.0423
chance                                         0.0357
margin M = -0.010763
bootstrap 95% CI  [-0.019013, -0.001927]   (entirely below zero)
paired permutation, n = 2780 pairs
safety-block accounting: A=7, D=13, total 20 rows — SYMMETRIC
```

**Read it carefully.** Both arms sit near the floor. The judge (`gemini-2.5-flash`) was asked
to match a definition to one of 28 foundations and got roughly `1 in 16` right where blind
guessing gets `1 in 28`. The confidence interval sits entirely below zero, so if anything the
generic arm did *better* — but from a baseline so close to chance that the comparison carries
almost no information either way.

**This is a power failure, not a verdict on TKS.** A referee who can barely tell anything apart
cannot declare a winner. The result replicated at two scales (small run and `10×`), so it is
stable — scaling fixed the statistics, not the task.

**Root cause now identified (§2b).** Both arms sat near the floor because **the scenario text in
both arms carries no recoverable foundation signal** — `p = 0.3011` against chance. The
comparison was never between two definition sets. It was between two piles of noise, measured
very carefully. Every instrument downstream of scenario authoring inherits this defect.

**Disclosed guard shortfall:** two passes scored `2793` and `2787` rows against a pre-registered
floor of `2800`, because the judge API refused 20 rows. Recorded rather than silently rounded.

---

## 6. Root cause — read this before designing anything new

Sixteen instruments failed for one recurring reason: **the confound arrives before the
phenomenon.**

The book's author also wrote the definitions, the test items, and the scoring rubric. So any
signal an instrument detects has at least two explanations:

1. The definitions genuinely share deep structure. *(the hypothesis)*
2. The definitions share an author, a vocabulary, and a set of habits. *(the confound)*

Every instrument that found signal was traceable to (2) once controls were added. Adding
controls is what produced the null results — the controls are correct, and they are what makes
this ledger trustworthy.

**Known specific traps, each discovered the hard way:**

- **Row duplication inflates `n`.** One dataset reported `640` rows; effective `n` was `80`
  (8 byte-identical copies each). Always compute effective sample size, never trust row count.
- **Char n-gram controls are mandatory.** A detector was withdrawn after a char-3-5-gram
  baseline (`0.925`) beat the hidden-state probe. This control never touches the model, so its
  score is constant across model sizes — if it moves, something is wrong with your harness.
- **Split artifacts masquerade as margins.** A `+0.0375` margin had a seed-inclusive mean of
  `-0.0094`, with 14 of 20 fold seeds putting the hidden state at or below raw token embeddings.
  Always report across seeds.
- **Natural-language escalation ladders cannot have flat surface sentiment.** Linguistic
  intensity *is* word choice. Three ladder rewrites made contamination worse, not better.
- **Sentiment lexicons you build yourself will be broken.** A hand-built one scored
  *"I am hopeless as a writer"* as **positive**. Use a published lexicon (VADER).
- **LLM API calls need explicit timeouts.** One hung connection blocked a run for 148 minutes.
- **Buffered logging hides progress.** Use `python -u`. (Piping through `tail` re-introduces the
  same buffering even with `-u`.)
- **No positive control is the meta-trap.** Sixteen instruments compared two things that might
  both be undetectable, and none checked whether the apparatus could find a signal that was
  certainly there. Adding one cost under an hour and reframed the entire ledger. **Every future
  design must include a positive control tier.**
- **A generator can produce items that look right and encode nothing.** The authoring model wrote
  fluent, on-theme vignettes from which the target foundation is unrecoverable. Fluency is not
  signal. **Validate items before comparing arms.**

---

## 7. The one experiment that needs people

This is the single highest-value thing a resourced team can do that could not be done here.

**The problem it solves:** independence. Not power — see the caveat below.

### Protocol sketch

1. **Recruit** `n >= 200` participants with no exposure to the book or framework
   (Prolific/MTurk screening question, plus an attention check).
2. **Split into two arms.** Arm A sees the original TKS foundation wording; arm D sees generic
   drive+register shorthand. Neither arm is told which is which, or that a comparison exists.
3. **Task:** each participant reads a definition and selects the matching foundation from the
   28-cell grid. Same task the LLM judge performed.
4. **Pre-register before collection:** margin floor, alpha, CI method, exclusion rules. Do not
   move them afterward. The pre-registrations in this repo are usable templates.
5. **Surface controls unchanged** — word TF-IDF and char 3-5-gram baselines computed on the
   same items, subtracted per arm.

### RE-SCOPED after the positive control (§2b) — read this before funding anything

The protocol above was written when the near-chance result was still unexplained. It is now
explained, and **running that protocol as written would burn expensive human labour reproducing
a known null.**

`T2` established that the authored scenarios carry no recoverable foundation signal (`p = 0.3011`).
Asking people to recover foundations from those same scenarios would very likely return the same
result — the signal is absent from the items, and human readers cannot recover what was never
written down.

**Two viable re-scopings, in order of cost:**

| Option | Task given to participants | What it establishes |
|---|---|---|
| **A — fix authoring first** | Have *humans* write the scenarios, then judge recovery on human-authored items | Tests whether the foundations are expressible at all, and whether the defect is the generator or the framework |
| **B — move the panel upstream** | Put people on **definition-level matching**, which `T0`/`T1` show is tractable | Cheaper, but note `T1`'s lexical-proximity caveat — a semantic tier must be built first or the task is trivial |

**Option A is the informative one.** It separates two explanations that are currently entangled:
the generator failed to encode the foundation, versus the foundations are not recoverable from
narrative at all. That distinction matters more than any TKS-versus-compact comparison.

**Pilot gate (unchanged in spirit, retargeted):** with `n ~ 30` human-authored items, if judge
recovery stays below `~0.25`, the problem is the framework's expressibility in narrative, not the
generator — and that is a finding worth having before any panel is funded.

---

## 8. What is not in scope of the existing patent

USPTO provisional **`64/037,173`**, filed **`04/13/2026`**. Conversion deadline
**`2027-04-13`** — a utility or PCT filing claiming priority must land by then.

**Not covered by that provisional** (added afterward, needs its own filing or inclusion in the
utility application):

- CAS v7.5 (Phenomenological Register), v7.6 (Production Semantics), v7.7 (Register Multiplicity)
- The Fleet / 300B sharded-audit architecture

The utility filing should **not** wait on the human-panel outcome.

---

## 9. Recommended sequence for the receiving team

1. **Run `check_invariants.py`** and the admissibility guard against your own environment first.
   If those don't pass, nothing downstream is trustworthy.
2. **Re-run the positive control** (`run_judge_positive_control.py`). It is fast, and it verifies
   your environment reproduces `T0 = 28/28` before you trust anything else.
3. **Build the missing semantic tier** — items that preserve meaning while breaking lexical
   overlap. Until that exists, `T1 = 1.000` cannot be read as semantic discrimination, and that
   gap sits underneath every downstream claim.
4. **Pilot Option A** (`n ~ 30` human-authored items, §7). This separates "the generator failed"
   from "the framework isn't recoverable from narrative" — the highest-information question open.
5. **If the pilot clears**, run the full panel against the existing pre-registration templates.
6. **Independently of the panel**, the book-prediction track (§4) is testable without human
   subjects and remains open. Note that it does **not** depend on scenario authoring, so it is
   unaffected by the defect found in §2b.

---

## 10. Status line

```
Gate 1   EARNED  (0.38)
Gate 2   OPEN    (0.46) — "the scoring actually works on a small model,
                          with fair comparisons and honest error bars"
```

Gate 2 is open because no instrument yet demonstrates usable discrimination. The methodology
requirement — fair comparisons, honest error bars — is **met**. The functional requirement —
the scoring actually discriminates — is **not**.

That distinction is the most important sentence in this document.
