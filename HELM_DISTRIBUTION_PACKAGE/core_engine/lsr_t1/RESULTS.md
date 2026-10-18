# LSR-T1 results (run LSR_T1_MSI_RUN2, 2026-10-14)

Claim ceiling: **SYNTHETIC_ONLY**. No HELM claim. No SDG meaning claim. Every verdict below was computed by
`run_t1.py` and copied from `runs/LSR_T1_MSI_RUN2/SUMMARY.json`. It is not a prose judgment.

- Sign line: `APPROVE lsr_t1, source ec01febf, LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.`
- Owner's words: "Run it locally as long as it Quick if long use aws." / "Run both" / "Yes on parallel prod".
  They are recorded in `FROZEN.json` and in `runs/LSR_T1_MSI_RUN2/OWNER_APPROVAL_EVIDENCE.md`.
- The parallel-production arm (A3) is **ADMITTED_BY_OWNER_20261014**, so mark M6 counts.

## Verdict (program)

| Item | Result |
|---|---|
| Hard gates | M1 do-nothing **PASS**, M9 carried gaps **PASS**, M4 beat both dumb baselines **FAIL** |
| test_verdict | **FAILURE** (one hard gate failed, so there is no "pass with caveats") |
| loop_status | **INCONCLUSIVE** (frozen rule: M4 failed, and LSR did not beat the single recipe on a2 or a, so VERIFY_DID_THE_WORK does not apply either) |
| Other marks | M2 FAIL, M3 FAIL, M5 FAIL, M6 FAIL, M7 PASS, M8 (reported) PASS |

## Held-out accuracy (5% tolerance), family × arm, exact fractions

Each color compares the arm with A0 under the 5% rule (fair-data v1): 🟩 wins by the rule, 🟨 ahead but not
by the rule, 🟥 loses, ties, or halts as predicted, ⬜ no arm learned anything (every arm below 0.10).

| Family | A0 single | B1 chunk-16 | A1 LSR×2 | A2 LSR×4 | A3 LSR+parallel | B2 random s11 / s29 / s47 |
|---|---|---|---|---|---|---|
| S2v2 clean 2-input | 1 (ref) | 🟥 1 | 🟥 1 | 🟥 1 | 🟥 1 | 🟥 1 / 1 / 1 |
| S3v2 clean 3-input | 1 (ref) | 🟥 1 | 🟥 1 | 🟥 1 | 🟥 1 | 🟥 1 / 1 / 1 |
| S1 clean (v2 data) | 1 (ref) | 🟥 1 | 🟥 1 | 🟥 1 | 🟥 1 | 🟥 1 / 1 / 1 |
| a2 best-of-two | 143/256 (ref) | 🟥 143/256 | 🟥 143/256 | 🟥 143/256 | 🟥 143/256 | 🟥 143/256 each |
| b additive | 0 (ref) | 🟥 0 | 🟩 7/16 | 🟩 7/16 | 🟩 7/16 | 🟥 0 each |
| a CES | ⬜ 0 | ⬜ 0 | ⬜ 0 | ⬜ 0 | ⬜ 0 | ⬜ 0 each |
| c noisy recipe | 1/8 (ref) | 🟥 1/8 | 🟥 1/8 | 🟥 1/8 | 🟥 1/8 | 🟥 1/8 each |

On the clean rows (S families), 🟥 is the predicted result: a tie, with nothing added.

Recipes admitted by the loop, all families: **0**, except on b. There, A1, A2 and A3 each admitted **8
capacity terms** (one each on 8 of the 16 Omegas). No alternative recipe was ever admitted, by LSR or by the
random baseline.

Halts on a2 under A2: 13 KNOWLEDGE_MISSING, 2 RECIPE_SHAPED_RESIDUAL_CARRIED, 1 NOISE_LIMITED. Every
unfinished halt carried its gaps: 334 rows on a2. The lacunarity machine agreed with the loop's row states
everywhere.

## Did gap-reading earn anything?

**No.** On a2 and on a, A2 tied B1 and every B2 seed exactly.

Nor did VERIFY "do the work": random proposals were also all refused. On a2 Omega 0, for example, all 15
random tries were refused for too little support.

**Root cause (a design finding, not a code bug):** the starting single recipe is fitted with the witnessed
ratio over all training rows. That fit always predicts at least y on every training row. So the first READ
sees only over-predicted rows. The design opens alternative-recipe and parallel-line proposals only from
under-predicted rows, so they never fire. ARCHITECTURE section 7, step 1 assumes the opposite. I did not
change the loop; that redesign is the owner's call.

## Additive family b, both readings

- **Without parallel production (pick-the-best): FAIL (M5).** The required halt NOT_RECIPE_SHAPED appeared on
  0 of 16 Omegas. A1 and A2 halted 11 KNOWLEDGE_MISSING, 4 NOISE_LIMITED and 1 RECIPE_SHAPED_RESIDUAL_CARRIED.
  The over-predicted residual routes to KNOWLEDGE_MISSING instead.
- **With parallel production (owner-admitted): FAIL (M5 and M6).** A3 never proposed the lines, for the same
  root cause. It is identical to A2: 16 recipes, 8 capacity stages, 8 admissions.
- **Direct check of claim 3** (lines offered to the fit without the proposer; a diagnostic, not a mark):
  VERIFY admitted 4 one-input lines on 16 of 16 Omegas. On the **8 Omegas whose capacity shows in the
  training rows**, 4 lines plus the capacity stage fit 64/64 training rows and **32/32 held-out rows each**
  (256/256). On the other 8, the training inputs never reach the cap. So no capacity stage could be fitted,
  and held-out accuracy collapsed (12/256). Overall: 67/128. Reading: the claim holds whenever the cap is
  observable. It is not falsified. But the loop as built cannot reach it.

## Tests

- Code tests: 4 of 4 pass (halt carries gaps, witnessed-ratio exactness, Clarification 10 `+` never `×`,
  machine-reader agreement).
- Behavior tests: 1 of 4 pass. Clean SDG adds zero recipes: PASS. Best-of-two solved by cap 2 and not by
  single: FAIL. Additive halts NOT_RECIPE_SHAPED: FAIL. Parallel production fits additive: FAIL.
- Every rendered recipe parses with bridge v2. No `×` appears anywhere.

## Cost

Worker 6.347 s wall and 6.359 s CPU. Supervisor 7.30 s wall. Peak working set 59,420,672 bytes (partial
peak, 200 ms poll). Sockets blocked. Spend 0. Free RAM before launch: 517,868 KB. Per-arm CPU seconds are
in SUMMARY.json and are all under 0.32 s per family.

Run 1 (`LSR_T1_MSI_ONCE`) did all the computing, then crashed while writing the JSON (an exact fraction had
more than 4,300 digits). I kept it on record, fixed the serializer only, and reran under a new run ID. The
computation is deterministic.

## What I could not do

- Panel 2 (chains) was not run.
- No random-pooled baseline (B3), and no A4 arm (parallel production with cap 2).
- No spec-sheet row and no CHANGELOG entry: this folder is outside the tksCAS repo.
- I saw the Omega-0 behavior in dev runs before the official run (disclosed in FROZEN.json `dev_runs`). No
  mark or loop rule was changed afterwards.
