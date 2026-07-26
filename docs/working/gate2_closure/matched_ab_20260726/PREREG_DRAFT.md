# PRE-REGISTRATION (DRAFT) — Matched A/B: Original TKS Foundation Wording vs Generic Drive+Register Shorthand Composition
## MATCHED-AB-DEFTEXT-v2 — Gate 2 closure, drafted 2026-07-26 (v2 after adversarial review)

STATUS: DRAFT. Not owner-authorized. No Gemini API call has been made for this
experiment. This document must be committed (or owner-acknowledged) BEFORE the
first authoring call. Driver: `run_matched_ab.py` in this directory (dry-run
verified 2026-07-26, no API calls; v2 re-verified after the adversarial-review
fixes below).

v2 incorporates the adversarial reviewer's FIX_FIRST list in full:
char-gram surface control (Hole 1), two-tier frozen criteria, symmetric judge
cross (Hole 2), banned-term symmetry (Asymmetry 1), a real byte-compare
template-identity guard (Asymmetry 3), the framing correction ("wording
provenance, not length"), pre-registered disclosure of the inherent
HARD_SOURCE_FORBIDDEN asymmetry (Asymmetry 2), and judge temperature 0.0 with
single-pin fallback rules.

---

## 1. What this replaces and why

The June 2026 comparison — original TKS subfoundation wording (89/140 = 63.57%
blind recovery) vs compact shorthand compositions (22/140 = 15.71%) — is NOT
LICENSED as evidence that original TKS wording carries more recoverable
meaning, because the June record has five confounds:

1. **Different fixture sets on different days.** The arms were authored in
   separate sessions (2026-06-16 winning lineage vs 2026-06-15 quarantined
   lineage) with no shared session window.
2. **Different judges behind the two headline numbers.** 63.57% is the
   gemini-2.5-flash judge on the delink arm; 15.71% is the gemini-2.5-PRO
   judge on the quarantined arm (the flash judge on that same arm gave
   26/140 = 18.57%). The headline comparison mixes judges.
3. **Blind row ids leaked the answer.** June blind rows used ids like
   `F1A_000` — the foundation label was literally inside the id string the
   judge received. Both arms were affected, but this contaminates any absolute
   recovery number.
4. **No reproducible authoring seeds.** The in-prompt variety seed was drawn
   from unseeded `random.randint(100000, 999999)` per batch attempt.
5. **Choice-set anchoring toward arm A.** The June judge used the original
   TKS 28 meanings as the choice set for BOTH arms and its prompt instructed
   "Use the original TKS meanings below, not shorthand drive/register
   summaries" — structurally favoring recovery of arm-A prompts.

This A/B fixes exactly these: both arms authored in ONE session under ONE
protocol, differing ONLY in definition text; one frozen judge model crossed
symmetrically over both choice keys; opaque ids; deterministic seeds.

## 2. Hypothesis, arms, and framing (CORRECTED)

**Framing (binding for all result wording):** the manipulation is **"original
TKS foundation wording vs generic drive+register shorthand composition"** —
NOT "original vs shortened". Measured definition lengths: compact texts are
125–150 characters vs TKS 98–152 characters. The compact arm is NOT shorter.
Any result statement implying a length manipulation is out of scope and
unlicensed.

**H1 (directional):** Scenario prompts authored from original TKS 28
subfoundation meanings (Arm A) carry more blind-judge-recoverable foundation
meaning than prompts authored from generic drive+register shorthand
compositions (Arm D), beyond what each arm's own surface-text leakage
explains, symmetrically over both judge choice keys.

**H0:** After subtracting per-arm surface baselines, the arms do not differ
beyond the frozen criteria.

- **Arm A definition source:** `C:/Users/wakil/Downloads/Everthing-Tootra-TKS/canon/normalized/canon_subfoundations_28_defs.json`
  sha256 `5507bf6f85f63dc62847ea5f9018b6ad4471ca8acfe851a0f50d2b4ebbf6c88d` (verified).
- **Arm D definition source:** `compact_defs_28.json` (this directory)
  sha256 `d6fb9ea114abaad583f3933d3c88882b4ba1b6e6e04cf11021dc39417d9209b9` —
  28 shorthands extracted VERBATIM from the quarantined June plan
  (`docs/working/_quarantine/mtc_f28_goemotions_wrong_short_defs_20260616/build_confirmatory_authoring_plan.py`,
  DRIVES × REGISTERS, composed as `drive = …; register = …` exactly as June composed them).
- The driver refuses to run if either sha256 mismatches.

## 3. How the arms are identical (R1) — and the three audited asymmetries

Everything below is byte-identical across arms, enforced by a REAL
template-identity guard (Section 3.1):

- One authoring-instruction template (June's delink `authoring_instructions()`
  wording) with exactly two injection points: the definition label and the
  definition text.
- One authoring prompt builder: the June winner's `prompt_for_chunk_delink()`
  IMPORTED from `docs/working/mtc_f28_goemotions_20260615/author_confirmatory_chunks_gemini.py`
  (June bytes, not a paraphrase). Same de-leak rules, same validators.
- Same cover controls: June's row-index-controlled COVER_SETTINGS ×
  COVER_TASKS × COVER_OBJECTS; the guard verifies cover setting, task,
  objects, surface_frame_id, assigned GoEmotion, and row id are identical for
  every (foundation, row_index) pair across arms. Row ids are arm-independent
  (`F1T_000` in both arms; the arm lives in metadata and file location, and
  the judge only ever sees opaque `row_NNNN` ids).
- Same row counts: 280 rows/arm = 10 per foundation × 28 foundations;
  1 chunk of 10 rows per foundation per arm; 2 authoring batches of 5
  (June-exact batch size).
- Same seeds: in-prompt variety seed =
  `100000 + int(sha256("20260726|{foundation}|{batch_index}|{attempt}")[:12],16) % 900000`,
  keyed WITHOUT the arm — paired A/D batches receive the SAME seed. Verified
  deterministic (two dry-runs produce byte-identical prompt transcripts,
  re-verified for v2).
- Same session window, interleaved chunk order A,D,A,D,… (56 chunks) to
  neutralize temporal drift.
- Same authoring model + generation config (Section 6).

### 3.1 REAL template-identity guard (Asymmetry 3 fix — replaces the v1 tautological check)

The v1 audit compared the template against itself with placeholder fields
(tautologically true). The v2 guard operates on the ACTUAL prompts: for every
paired authoring batch (28 foundations × 2 batches = 56 paired prompts), the
driver builds both arms' full authoring prompts (attempt 1, shared variety
seed), strips EXACTLY the two injection segments —

1. the definition line (June's `authoring_instructions` line, which carries
   the definition label, the definition text, and the banned literal list
   mechanically derived from that text), and
2. the `Especially avoid these source terms` JSON line —

and BYTE-COMPARES the remainders. Any diff hard-fails the driver (SystemExit)
before any API call. The real per-chunk comparison results (byte-equal flag,
remainder byte counts, remainder sha256 per arm, stripped-segment lengths,
shared-seed flag) are written to `template_identity_audit.json`. Verified
2026-07-26: 56/56 paired prompts byte-equal on clean plans; guard confirmed to
trip (with a first-diff line pointer) on an injected template tamper.

### 3.2 Banned-term symmetry (Asymmetry 1 fix)

Both arms derive `source_banned_terms` with the SAME call signature:
`source_terms_to_avoid(meaning, name)` — the definition text plus its label
name. Arm A (June bytes): `source_terms_to_avoid(original_tks_meaning,
legacy_tks_name)`. Arm D (v2): `source_terms_to_avoid(compact_meaning,
"<Drive>-<Register> shorthand")`. The ban lists still differ in CONTENT
because the definition texts differ — that is the manipulation — but the
derivation procedure is now identical.

### 3.3 Inherent asymmetry disclosure (ASYMMETRY 2 — pre-registered, not fixable)

The original TKS definition text intersects the June validator's
`HARD_SOURCE_FORBIDDEN` mystical vocabulary (13 terms measured on the pinned
canon file: divine, esoteric, ghost, holy, meditation, mystical, occult,
prayer, rapture, sacred, soul, spiritual, transcending). The compact texts
intersect it on 0 terms. Consequence: Arm A authoring faces extra
regeneration constraints (validator rejections and retries) that Arm D never
faces. This is inherent to the manipulation ("definition text" includes the
constraints it induces). **Direction of pressure: AGAINST arm A** (harder
authoring), so it cannot manufacture an A win; it can only shrink a real A
advantage or amplify a D one. Retry counts per arm are recorded in
`authoring_prompts.jsonl` and will be reported descriptively.

## 4. Frozen blind judge — SYMMETRIC CROSS (R2, Hole 2 fix)

June's design used the original TKS meanings as the judge's choice set for
BOTH arms, and the June prompt contained the sentence "Use the original TKS
meanings below, not shorthand drive/register summaries" — anchoring the
choice set toward arm A. v2 removes that sentence and crosses the choice key:

- ONE judge model for both arms and both passes: `models/gemini-2.5-flash`
  (June-exact), pinned. **Temperature 0.0 for both passes** — a DELIBERATE
  pre-registered change from June's 0.1, chosen for determinism.
- **Two judge passes over the SAME shuffled 560-row pool** (same opaque ids,
  same order, no arm labels, answer key withheld):
  - **Pass K_A:** choice key = the original TKS 28 meanings (sha-pinned canon
    file).
  - **Pass K_D:** choice key = the compact drive+register shorthand
    compositions (`compact_defs_28.json`).
  - Prompts otherwise IDENTICAL (same June `judge_prompt()` bytes, same
    batching, same generation config).
- **Per-arm recovery = MEAN over the two passes.** Rationale: any choice-set
  anchoring advantage is granted to each arm exactly once, killing choice-set
  anchoring symmetrically instead of assuming either definition style is the
  neutral key.
- **Three pre-registered prompt neutralizations**, applied identically to
  BOTH passes and verified at runtime by exact occurrence counts (driver
  hard-fails otherwise):
  1. remove the line `Use the original TKS meanings below, not shorthand
     drive/register summaries.` (must occur exactly once);
  2. replace the header `Foundation options from original TKS definitions:`
     with `Foundation options:` (must occur exactly once);
  3. rename the JSON field `original_tks_meaning` to `meaning` (must occur
     exactly 28 times).
- Judge sees ALL 560 rows (both arms pooled) per pass, in a seeded shuffled
  order (seed `20260726*1000003+17`, permutation persisted), with OPAQUE ids
  `row_0000..row_0559` and NO arm labels. Answer key withheld
  (`blind_key.json` maps opaque id → arm + truth; never sent).
- Batches of 10, 3 retries, resume-safe per pass; invalid labels coerced to
  `__invalid__` and scored wrong (June-exact scoring).
- Judging cost roughly DOUBLES vs a single pass (Section 9).
- Optional gemini-2.5-pro adjudication pass may be run AFTER the primary
  result is written; it is reported separately and can never change the
  primary verdict.

## 5. Gate 1 surface control per arm (R3, Hole 1 fix) — word AND char

Per arm, on the 280-row fixture, answer-word stripping (EMO_SYN + CAS_JARGON)
then TWO baselines, both 5-fold StratifiedKFold (shuffle=True,
**random_state=0**, same fixed seed for both, identical config across arms),
LogisticRegression(max_iter=2000, class_weight=balanced), mean CV accuracy:

1. **Word baseline (June-exact bytes):** TF-IDF (1-2)-grams, min_df=2,
   max_features=20000, sublinear_tf. The driver runtime-verifies that its
   parameterized replica reproduces the imported June `cv_accuracy` value
   exactly at random_state=0 (config-fidelity hard-stop).
2. **Char baseline (standing mandatory char-level surface control):** TF-IDF
   `analyzer='char'`, (3-5)-grams, min_df=2, max_features=20000, sublinear_tf
   — all other pipeline elements identical to the word baseline.

**Frozen surface definition:** `surface_X = max(word_baseline, char_baseline)`
per arm, per label task (foundation and goemotion, answer-stripped). This
`max` is what enters BOTH the Gate-1 threshold and the primary endpoint.

Threshold 0.60 (June-exact, now applied to the max):
`surface_foundation <= 0.60 AND surface_goemotion <= 0.60` per arm, else that
arm is BLOCKED and the run verdict is BLOCKED_SURFACE.

**CV-seed sensitivity report (descriptive only, pre-registered):** the two
surface numbers entering `surface_X` (word and char foundation baselines) are
recomputed at 5 CV seeds (random_state ∈ {0,1,2,3,4}) per arm and reported in
`gate1_arm_{A,D}.json` as `cv_seed_sensitivity`. The primary numbers remain
the random_state=0 values; the seed spread is reported so the margin cannot
silently ride on a lucky fold split.

Note (pre-registered): at 280 docs the TF-IDF baselines are weaker than
June's 2,800-doc baseline. June's 0.5721 is NOT reused; each arm's own
measured `max(word, char)` surface baseline is the floor entering the primary
endpoint. Chance = 1/28 = 3.57%.

## 6. Model pins (R7)

| Role | Pin (June-exact) | Note |
|---|---|---|
| Authoring, BOTH arms | `models/gemini-2.5-flash-lite` | **Correction to the R7 brief:** June authored with flash-LITE, not flash — confirmed in per-chunk `model` fields of both June lineages. |
| Blind judge, BOTH arms, BOTH passes | `models/gemini-2.5-flash` | temp 0.0 both passes (deliberate change from June 0.1, for determinism) |
| Optional adjudication | `models/gemini-2.5-pro` | separate report only, never primary |

**Fallback rule:** if either June-exact model is unavailable at run time, BOTH
roles for BOTH arms (and both judge passes) move to the single pin
`models/gemini-3.1-pro-preview`. Mixed pins (one arm, one role, or one pass on
a different model) are prohibited; the driver enforces this. Models actually
used are recorded in every chunk file, transcript line, and in
`results_matched_ab.json` (`models_used`).

Authoring generation config (June-exact): JSON mime, temperature 0.95,
top_p 0.95, max_output_tokens 8192, 3 retries, sleep 2.0×attempt.

## 7. Primary endpoint and TWO-TIER frozen criteria (R3/R4 — FROZEN BEFORE AUTHORING)

Let `recovery_X` = blind foundation accuracy of arm X (n=280), averaged over
judge passes K_A and K_D (per-row correctness = mean over the two passes, in
{0, 0.5, 1}), and `surface_X` = that arm's Gate-1
`max(word, char) foundation_answer_stripped` (Section 5).

- **De-leaked margin delta:**
  `M = (recovery_A − surface_A) − (recovery_D − surface_D)`
- **Permutation test:** rows are naturally paired across arms by
  (foundation, row_index) — identical cover controls and GoEmotion. Per-pair
  difference `d_i = correct_A,i − correct_D,i ∈ {−1, −0.5, 0, +0.5, +1}` on
  pass-averaged foundation correctness. One-sided label-preserving sign-flip
  permutation, 10,000 iterations, seed `20260726*7919+42`,
  `p = (#{perm mean ≥ observed mean}+1)/(N+1)`.
- **Bootstrap CI:** percentile bootstrap over the 280 pairs (resample pairs
  with replacement, 10,000 iterations, seed `20260726*104729+7`); statistic
  per resample = `mean(d_i) − (surface_A − surface_D)` with the surface terms
  held as fixed arm-level point estimates (pre-registered convention,
  consistent with the margin definition). 95% CI.

**PRIMARY tier — licenses the strong claim (`PASS_TKS_SUPERIORITY_LICENSED`):**

> `M ≥ +0.10` AND permutation `p < 0.01` (10,000 label-preserving
> permutations on paired per-row correctness) AND the bootstrap 95% CI of M
> excludes 0. (Plus: both arms Gate-1 PASS, no degeneracy-guard failure, no
> ceiling.)

**SECONDARY tier — licenses ONLY the wording "directionally supported below
the pre-registered strong margin" (`SECONDARY_DIRECTIONAL_SUPPORT`):**

> `0 < M < 0.10` AND permutation `p < 0.01` AND the bootstrap 95% CI of M
> excludes 0. The strong claim is NOT licensed at this tier, in any wording.

**Otherwise:** `FAIL_NO_LICENSED_SUPERIORITY` (or the specific guard verdict).

**Sanity note (pre-registered):** with n=280/arm, the SE of the paired
accuracy difference is ~0.042, so the +0.10 primary floor sits ~2.4 SE from
zero. The two-tier structure exists precisely so a real-but-smaller effect is
reported honestly instead of being rounded up to the strong claim or down to
"no effect".

**Pre-registered convention:** the surface subtraction enters as arm-level
point estimates in the margin criterion and the bootstrap; the permutation
p-value is computed on the raw paired recovery difference. All named criteria
of a tier must pass for that tier.

**GoEmotion floor decision (frozen, option (a)):** the June rival floor
(`goemotion ≥ max(surface_goemotion, 0.50)`) is computed and reported per arm
as a DESCRIPTIVE June-comparability verdict only. It is NOT part of the
primary endpoint. Rationale: the winning June delink recipe itself scored
goemotion 0.0786; reusing the delink prompt verbatim (required for June
fidelity) makes both arms likely to fail that floor identically, and the
question under test is foundation-meaning recovery, not emotion recovery.

## 8. Degeneracy / saturation guards (V6-F5 spirit, frozen)

Any failure ⇒ verdict `NOT_LICENSED_DEGENERATE` (no superiority claim, no
"fail" claim either — the run is uninterpretable and must be redesigned):

1. Scored rows per arm = 280 in EACH judge pass (all rows judged twice; no
   partial scoring).
2. Judge invalid-prediction rate ≤ 5% per arm per pass.
3. Judge collapse guard: no single predicted foundation label may exceed 30%
   of an arm's predictions in either pass.
4. Authoring completeness: all 56 chunks pass June validators
   (`validate_chunk_payload`, June bytes); any failed/missing chunk blocks
   assembly (hard stop, June behavior).
5. Ceiling guard: if BOTH arms' pass-averaged recovery ≥ 0.95, verdict
   `NOT_LICENSED_CEILING` (margin uninterpretable at saturation).

The June `assert_original_tks_inputs` hard-stop (which would refuse Arm D) is
replaced by a dual-arm guard: Arm A rows must carry meanings from the
sha-pinned canon file, Arm D rows from the sha-pinned compact file, plus the
byte-compare template-identity guard (Section 3.1) and cover-parity audit. No
silent bypass of the June check: the replacement is strictly stronger on
provenance and is itself pre-registered here.

## 9. Cost estimate (R6) — updated for the two-pass judge cross

From the executed v2 dry-run (`dryrun_report.json`, real constructed prompts,
zero API calls):

- Authoring: 112 requests (56 chunks × 2 batches), ~224K input + ~77K output
  tokens; ×1.5 retry worst case ⇒ ~337K/116K. flash-lite ($0.10/$0.40 per 1M):
  **~$0.08**.
- Judging: **112 requests (2 passes × 56)** — pass K_A ~3,387 prompt
  tokens/call, pass K_D ~3,625 — ~589K input + ~45K output with retry factor.
  flash ($0.30/$2.50 per 1M): **~$0.29** (the symmetric cross roughly doubles
  June-style judging cost, as pre-registered).
- Total at June models: **~$0.37**. Optional pro adjudication (both passes):
  ~$1.19.
- Worst case (everything on fallback `gemini-3.1-pro-preview`, $2/$12 per 1M):
  **~$3.79**.
- **Cap: $25.00 — all scenarios far under cap.**

## 10. Licensed wording

**On PRIMARY pass (`PASS_TKS_SUPERIORITY_LICENSED`):**
> LICENSED (fixture-level only): under a matched single-session A/B in which
> both arms were authored by the same pinned model from one template differing
> only in definition text, scenario prompts authored from original TKS
> foundation wording carried more blind-judge-recoverable class meaning than
> prompts authored from generic drive+register shorthand compositions, beyond
> each arm's own surface baseline (max of word TF-IDF and char 3-5-gram),
> symmetric over both judge choice keys (per-arm recovery = mean over passes
> K_A and K_D; de-leaked margin ≥ 0.10, one-sided paired permutation p < 0.01,
> bootstrap 95% CI of the margin excluding 0). This licenses NO hidden-state,
> GPU-probe, or model-internals claim, and NO claim that the TKS grid itself
> is "derived" or uniquely correct. The manipulation is wording provenance,
> not length: the compact texts are NOT shorter (125–150 chars vs TKS 98–152).

**On SECONDARY tier (`SECONDARY_DIRECTIONAL_SUPPORT`):**
> SECONDARY TIER ONLY: the pre-registered strong margin (≥ 0.10) was NOT met.
> The ONLY licensed wording is: "directionally supported below the
> pre-registered strong margin" (margin > 0, one-sided paired permutation
> p < 0.01, bootstrap 95% CI excluding 0, margin < 0.10). The strong claim
> "original TKS foundation wording beats generic drive+register shorthand
> composition" is NOT licensed. This licenses NO hidden-state, GPU-probe, or
> model-internals claim.

**On FAIL (`FAIL_NO_LICENSED_SUPERIORITY`):**
> NOT LICENSED: the matched A/B cleared neither the pre-registered PRIMARY
> tier (margin ≥ 0.10 with p < 0.01 and CI excluding 0) nor the SECONDARY tier
> (positive margin with the same statistical floors). The June
> 63.57%-vs-15.71% comparison remains NOT LICENSED, and "original TKS
> foundation wording beats generic drive+register shorthand composition" may
> not be claimed in any form from this campaign. Descriptive per-arm numbers
> may be reported only with this verdict attached.

**On BLOCKED_SURFACE / NOT_LICENSED_DEGENERATE / NOT_LICENSED_CEILING:** no
directional claim in either direction; the specific guard that fired is named;
a redesign requires a NEW pre-registration.

In ALL outcomes the June headline numbers stay retired from claim-bearing use;
this A/B supersedes them. All result wording obeys the Section 2 framing
(wording provenance, not length).

## 11. Raw artifacts (R5) — all under this directory

`frozen_config.json`, `plan_arm_{A,D}.json`, `plan_arm_{A,D}_chunks.jsonl`,
`template_identity_audit.json` (real per-chunk byte-compare results),
`authoring_prompts.jsonl` (full transcript incl. per-batch seeds and retries),
`chunks_{A,D}/*.json`, `fixture_arm_{A,D}.json` (+ manifests with sha256),
`gate1_arm_{A,D}.json` (word + char + max surface, CV-seed sensitivity),
`blind_pool.json`, `blind_key.json` (answer key, never sent to judge),
`blind_permutation.json`, `judge_prompts_{K_A,K_D}.jsonl`,
`judge_preds_{K_A,K_D}.json`, `results_matched_ab.json` (incl. permutation,
bootstrap CI, models_used), `compact_defs_28.json`, `dryrun_report.json`.

## 12. Execution protocol

1. Owner reviews/authorizes this prereg; freeze by commit BEFORE first API call.
2. `python run_matched_ab.py --dry-run` (already verified for v2; re-run at
   will — exits 0, zero API calls, template guard 56/56 byte-equal).
3. `python run_matched_ab.py` — one session: plan → template guard →
   interleaved authoring → assemble → Gate 1 (word+char) per arm → blind pool
   → judge pass K_A → judge pass K_D → score. Resume-safe at every stage;
   resume does not re-randomize (all seeds derived).
4. Optional: pro adjudication pass, reported separately.
5. Record result in the attempts registry with the exact verdict string and
   tier.

## 13. Open decisions for owner sign-off

1. Confirm the two-tier criteria as frozen: PRIMARY = M ≥ 0.10 AND p < 0.01
   AND bootstrap 95% CI excluding 0; SECONDARY = 0 < M < 0.10 with the same
   statistical floors, wording capped at "directionally supported below the
   pre-registered strong margin". (Margin floor rationale unchanged from v1:
   June's own de-leaked Arm-A signal was +0.064 against a 2,800-row surface
   baseline; the 280-row baseline sits lower, leaving headroom. The +0.10
   floor is ~2.4 SE at n=280/arm.)
2. Confirm judge temperature 0.0 (vs keeping June's 0.1 for exactness) —
   frozen for BOTH passes.
3. Confirm goemotion floor as descriptive-only (option (a)).
4. Confirm the fallback single-pin rule (`gemini-3.1-pro-preview` for both
   roles, both arms, both passes) and that a mid-run model deprecation aborts
   rather than mixes pins.
5. Confirm the symmetric judge cross (two passes, mean recovery) and the
   three judge-prompt neutralizations as pre-registered.
