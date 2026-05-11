# v1e Phase 1B Shadow Eval — Findings

**Date:** 2026-05-10
**Driver:** `cas-synthetic/scripts/v1e_phase1b_shadow_eval.py`
**Suite:** 35 stratified fractals (k=2..8) + 7 non-fractal negative controls
**Configs:** A_control / B_smoke / C_eos_bias / D_first_n / E_both
**Checkpoint:** archived v1c_VALIDTOK_5ep at v0-rc1
**Auto-summary:** `v1e_phase1b_shadow_eval_20260510T225013Z_summary.md`
**Raw JSONL:** `v1e_phase1b_shadow_eval_20260510T225013Z.jsonl`

## TL;DR

The phrase-trie + state machine works mechanically on **every** fractal
record (slot-commits = 35/35 expected k-sequence). Lever 2
(`first_n_mode`) materially unlocks **+12 records** of first-n exact-
match output (1/35 → 13/35). Lever 1 (`eos_bias=3.0`) alone is
ineffective. **D/E (first_n_mode on) damage Record 14's prose quality
visibly.** No non-fractal drift. v0 canary still passes.

The honest verdict maps to **Path β / partial success** in the v1e
design doc: B helps structurally but at a prose-quality cost on the
canonical short-fractal case. Three options surface to user.

## Three-metric breakdown (the auto-summary missed two)

The auto-summary reports only `full sequence_match` from the verifier on
the chosen output's full text. That misses the underlying mechanism's
behavior. Three metrics tell the real story:

| Metric | A_control | B_smoke | C_eos_bias | D_first_n | E_both |
|---|---:|---:|---:|---:|---:|
| **Slot-commit match** (constrained run's in-decoder commits == expected) | 0/35 | **35/35** | **35/35** | **35/35** | **35/35** |
| **First-n seq_match** (chosen output's `found_k[:n] == expected`) | 1/35 | 1/35 | 1/35 | **13/35** | **13/35** |
| **Full seq_match** (chosen output's full verifier `sequence_matches`) | 0/35 | 0/35 | 0/35 | 0/35 | 0/35 |

Reading row 1: the constrained decoder commits the exact source
k-sequence at the trie-leaf level on EVERY fractal record under B/C/D/E.
The phrase-state-machine inductive bias works as designed. This is the
strongest single signal from the eval.

Reading row 2: under D/E, 13 records now produce a chosen output whose
first-n extracted noetics exactly match the source k-sequence. Under A,
B, C the chosen output rarely produces a first-n match (1/35 only —
that record being k=2 `Φ<3:7>` where baseline happens to start with
"struck a chord, then became drawn to it" which is wrong content but
matches by coincidence on some position).

Reading row 3: full seq_match stays at 0/35 because trailing prose past
the final slot contaminates the verifier's full extraction with extra
noetic indicators. Neither EOS-bias nor first_n_mode addresses this on
their own.

## What does and doesn't work

**Works:**
- Phrase trie commits 35/35 expected slot sequences — fundamentally
  sound mechanism, including extreme repeats (`Φ<9:9:9>`, `Φ<5:5:5:5:5:5>`,
  `Φ<8:8:8:8:8:8:8:8>`) and the v1d regression records 13/15.
- `first_n_mode` correctly identifies 20/35 records as constrained-better,
  selecting 13 of them as first-n exact matches in the chosen output.
- Non-fractal source-shape gate: all 7 negative controls byte-match the
  control config across all 4 constrained configs.
- No hard notation / jargon / truncation regression.
- v0 canary (`v0_canary.py --check`) still PASS.

**Doesn't work:**
- `eos_bias=3.0` alone is ineffective. Constrained output retains
  trailing prose despite the bias; comparator never flips. Bias may need
  to be much stronger (5.0-10.0) to actually nudge greedy decoder to
  EOS over high-probability prose tokens.
- Token-boundary handling at trie leaf-exit: phrases like "averse"
  reach the leaf, but the next-token (free decode) emits "n" continuing
  into "aversen", which the verifier's word-boundary rule rejects. This
  causes ~22/35 records to have the right slot-commit sequence but a
  rendered output the verifier won't extract correctly.
- **Record 14 prose damage**: under D/E the constrained output for
  `Φ<3:7>` reads " aversen into a groove led to becoming aware, which
  then became practice makes perfect, and finally struck a chord." —
  visibly lower prose quality than the A/B/C baseline ("Something that
  struck a chord, then became drawn to it, which triggered a memory,
  and finally muscle memory."). Both are wrong-noetic, but D/E reads as
  broken prose with "aversen" and stiff transitions.

## Lever-individual safety

| Config | Lever | Negative drift | Prose damage | First-n lift |
|---|---|---|---|---|
| C_eos_bias | EOS bias 3.0 | none | none | +0 |
| D_first_n | first_n_mode | none | **Record 14: ↓ visible** | **+12** |
| E_both | both | none | **Record 14: ↓ visible** | +12 (= D) |

EOS-bias alone is SAFE but INEFFECTIVE at strength 3.0. First_n_mode is
EFFECTIVE on the structural metric but DAMAGES the canonical short-
fractal prose. Combining (E) does not add to D's first-n lift, which
confirms EOS-bias at this strength doesn't help even alongside first_n.

## Promotion-gate against user criteria

1. **"Exact k-sequence improves materially on fractal suite"** —
   AMBIGUOUS: full seq_match 0→0, but first-n seq_match 1→13 (+12) under
   D/E. Depends on which metric is load-bearing.
2. **"Record 14 does not lose prose quality"** — FAIL under D/E. The
   `Φ<3:7>` rendering visibly degrades when first_n_mode flips selection.
3. **"No non-fractal drift"** — PASS for all configs.
4. **"v0 canary stays PASS"** — PASS.
5. **"No hard notation/jargon/truncation regression"** — PASS for all.

Net: **B (smoke)** and **C (eos_bias)** are safe but ineffective.
**D (first_n)** and **E (both)** are partially effective on structural
metric but fail the Record-14 prose-quality criterion. Per the audit's
heuristic decision rule, **none of the four constrained configs meet
the promotion gate as defined.**

## Three options to surface to user

### Option α — Ship Phase 1B as-is in opt-in shadow mode

Treat the implementation as a diagnostic surface. `apply_fractal_decoder`
stays default-False. The phrase-trie commits and dual-decode artifacts
are available to eval scripts and traceability surfaces, but the
production v0 path is unchanged. Future work re-enters whenever the
rendering-side issues (lever 3 below, training-side aux heads, or
simplex) are ready.

### Option β — Lever 3: leaf-exit boundary-token bias

Add a third lever: when the trie reaches a leaf, force the NEXT token
to be a whitespace / punctuation / EOS token (bias +λ on those, OR
mask everything else for one step). This addresses the "averse →
aversen" token-boundary failure. Combined with first_n_mode it should
push first-n match closer to slot-commit match (toward 25-30/35) AND
restore prose quality (boundary tokens give the rest of the sentence
a clean entry point).

Estimated cost: ~1-2 eng days. Re-runs the same eval suite under a new
config F. If it works, the promotion gate becomes coherent.

### Option γ — Pivot to simplex Δ°₃₉ rebuild

Per the v1e design doc and the Wave-2 critic agents: simplex is a peer
option, not just a kill-switch. The current evidence is that v0+B
(with all levers) can structurally land slot sequences but not produce
a user-quality rendering. If the rendering issue is fundamentally a
training-side modality-mismatch problem, simplex rebuild is the cleaner
route. ~10-14 eng-weeks vs the 1-2 days for lever 3.

## My recommendation

**Option β (lever 3)** is the cheapest informative experiment. The
phrase-trie mechanism is provably sound on the structural axis (35/35
slot-commit match). The remaining gap is token-boundary handling at
trie leaf-exit, a small surgical fix. If lever 3 closes the gap to
≥20/35 full seq_match AND restores Record 14, **D/E (with lever 3
added) becomes a real promotion candidate** for `apply_fractal_decoder`
default-on.

If lever 3 doesn't close the gap, the rendering issue is deeper than
boundary handling and we're in **Path γ** territory: surface simplex
rebuild to user.

## Sample records (read for context)

### Record k4_one_repeat (Φ<3:5:3:5>) — first_n_mode flipped

- A baseline: `"Something that struck a chord, then became shaped by experience, which became an aversion, in turn shaped by experience, and finally muscle memory."` found_k=[4, 5, 3, 5, 7] — WRONG opening (^4 not ^3)
- D constrained: `"rubs the wrong way shaped by experience, rubs the wrong way, shaped by experience, which became an aversion, and finally an aversion to it again."` found_k=[3, 5, 3, 5, 3, 3]
- D's first-4 = [3, 5, 3, 5] — **EXACT MATCH** to expected
- Slot commits: (3, 'rubs the wrong way'), (5, 'shaped by experience'), (3, 'rubs the wrong way'), (5, 'shaped by experience')
- Constrained text reads as somewhat repetitive but coherent; trailing prose adds the spurious tail.

### Record k6_diverse (Φ<1:2:3:4:5:6>) — first_n_mode flipped

- A baseline: `"Something drawn to it led to paying attention, which then became drawn to it, then an aversion, then pushed away again, then breaking it down, and finally muscle memory took over."` found_k=[2, 1, 2, 3, 3, 6, 7]
- D constrained: `"cognitive attention drawn to an aversion, struck a chord, shaped by experience, breaking it down, then an aversion took over, which in turn became breaking it down, and finally muscle memory took over"` found_k=[1, 2, 3, 4, 5, 6, 3, 6, 7]
- D's first-6 = [1, 2, 3, 4, 5, 6] — **EXACT MATCH**
- Slot commits all six exact

### Record 14 analog (Φ<3:7>) — first_n_mode flipped but PROSE DAMAGED

- A/B/C all: `"Something that struck a chord, then became drawn to it, which triggered a memory, and finally muscle memory."` — readable prose, wrong content
- D/E: `" aversen into a groove led to becoming aware, which then became practice makes perfect, and finally struck a chord."` — broken prose ("aversen", "becoming aware", stiff transitions)
- Slot commits (0, 3, 'averse'), (1, 7, 'into a groove') — exact match
- Verifier on full text: found_k = [7, 7, 4] — only 'into a groove', 'practice makes perfect', 'struck a chord' extracted; 'averse' missed due to "aversen" word-boundary, content drift on the trailing prose
- This is the load-bearing prose-quality regression that vetoes promotion as-is.
