# ITEM 4 — `SCRAMBLE-NULL-COMPLETION-v1` (+ secondary `WOM-FR`)

**Committed BEFORE the run. Owner authorized: "RUN IT ... YOU HAVE ALL AUTHORIZATION."**

## What this is

NOT a thirteenth attempt at the derivation question — the hail-mary confirmed that question is
unreachable without the independent bank. This run completes the null on the campaign's ONLY
replicated positive (instruments 11+12: TKS beats its own scramble), which currently rests on ONE
shared permutation (seed `20260725`) with no positive-direction significance test. It also takes one
clean shot at a second scoped claim (Def 2.1 world ordering) whose confound was measured SILENT for
TKS before this run.

## Pipeline (instrument 12, unchanged — no invented projection)

`pythia-1b`; each definition → the model's own next-token output distribution (native simplex);
Fisher-Rao geodesic; `recon_fr` verbatim from `output_simplex.py`. Saturation guard: any arm within
`0.05` of `0` or `π` → VOID.

## Arms

TKS (`tks_owner_locked_definitions_20260603.json`); compact (`arm_D_compact_cas.json`);
**200 fresh grid permutations of TKS** (numpy `default_rng(seed)` for seeds `1..200`; seed `20260725`
retired); **200 fresh permutations of compact** (shuffled-compact, the missing symmetry arm).
All per-arm reconstruction distances and 40×40 geodesic matrices dumped to `.npz` — every downstream
number recomputable on CPU forever.

Relative margin of arm X: `rel = (scramble_mean − d_X) / scramble_mean` computed against X's own
200-scramble mean.

## Primary bars (licensing)

| # | Bar |
|---|---|
| E1 | TKS reconstruction below the 2.5th percentile of its 200-scramble model null; exact one-sided `p` (floor `1/201`) |
| E2 | Sanity only, cannot co-license (lexical direction is guaranteed): TKS − scramble-mean bootstrap CI excludes 0 |
| E3 | **Licensing bar:** model relative margin − max(word-BoW, char 3–5 gram) lexical relative margin `>= +0.10`. Lexical channels computed in-run on CPU with the SAME 200 seeds. Frozen precheck facts: recorded model rel `0.3196`; lexical null 95th pcts `0.1588` (word) / `0.1275` (char); harshest sim-softmax sensitivity variant `0.2365` WOULD FAIL at the current point estimate — disclosed now, reported as sensitivity |
| E3b | Affine fit lexical→model across dumped arms; TKS must sit outside the prediction band in the positive direction |
| E4 | Saturation guard (VOID) |
| E5 | Shuffled-compact reported however it lands (lexical predicts it as the MOST "non-arbitrary" arm, rel `0.858` — disclosed now so it cannot be spun later) |

## Secondary (`WOM-FR`) — same dump, zero extra GPU; cannot rescue or void the primary

| # | Bar |
|---|---|
| W1 | Per Noetic column: midrank Spearman of the 6 world-pair geodesics against Def 2.1 ordinal gaps `[1,2,3,1,2,1]` (pair order AB,AC,AD,BC,BD,CD); mean over 10 columns `>= +0.32` (frozen lexical-null 99th pct) AND `p < 0.005` on 10,000 within-column world-label permutations |
| W2 | Frozen lexical facts: TKS word `+0.0401` (`p=0.387`), TKS char `−0.2654` (`p=0.974`) — BOTH at/below chance; compact `+0.6356`/`+0.5864`; tie-capped max `0.9258` |
| W3 | TKS-vs-compact superiority EXCLUDED — compact's lexical floor `0.636` against cap `0.9258` makes any delta a ceiling artifact |

## Confound direction, stated before results

Primary: vocabulary favours the positive DIRECTION (lexical rel `~0.14`), which is why direction earns
nothing — the bar is magnitude beyond the lexical null (`0.166` word / `0.128` char ceilings vs model
`0.3196` recorded). Secondary: vocabulary favours COMPACT and is silent-to-negative for TKS — an
ordinal win cannot be carried by words, and the arm the confound favours is excluded from the claim.

## Licensed wording on a pass, verbatim

Primary: *"the TKS grid assignment is non-arbitrary in pythia-1b's output geometry beyond
exact-vocabulary prediction, margin X ± Y."* Secondary: *"the TKS world axis is ordinally arranged
(A ≻ B ≻ C ≻ D, Def 2.1) in pythia-1b's output geometry, a structure absent from both surface
channels."* **Neither sentence contains the word "derived," and no outcome can put it there.**

`LOCKED / COMMITTED BEFORE RESULTS EXIST / NOTHING LICENSED`
