# HELM-R1 wave 6, the PAIR WAVE, job c48 (2026-10-19 Pacific): verdict `PASS`; status word `WIDE_WAVE_NO_GAIN`

Status: REAL run. Every word below comes from a program, not from prose: `R1_W6_READING.json` (sha256
`8fa07631ae89db38cae5ea9da84ca6ebebfbeb6b282385eee74021ffb326ad97`) was written by the frozen reader
`r1w6/merge_r1w6.py` (`r1w6.merge_r1w6 v2 (2026-10-20)`), run on the laptop from a fresh extract of the sealed v2 zip
`729623429832c5fa99141d96876434d9ebed7417055c87173e7a582b3677be0a` (freeze `83983cd4…`; 193 of 193 freeze members
re-hashed, 0 bad). Merge input `MERGE_INPUT_R1W6.json` sha256
`ec5d5efe49008b7c6d6301590e261518f503d8da66c12e23e260fe29de3dc8b9`. Reader exit 0, empty stderr.
`failing_instruments` [] and `failing_gates` []. `status_reason`: `missed: K4_HONEST`.

**Said plainly first.**
- This wave switched the wide recipe brain ON together with HELM's other parts (cube store, English reader, triad,
  voice, the Unity Eye's self-scan and its pairing loop) and added one caution rule (UNSETTLED_ASK: if a recipe names
  one ingredient on two lines, ask instead of answering).
- It did no harm anywhere: **0 items lost** on every exam, next to each Eye, and in conversation 🟩.
- It learned well: **97 of 101** learnable real recipes fully learned (bar 91), **96 right, 0 wrong**, 0 wrong lessons 🟩.
- The Eyes raised **0 false alarms** and wrote **0** times; **0 guard trips** 🟩.
- But it asked **once** on a recipe it had fully learned and could have answered. The frozen rule K4 allows **0**
  such asks. So the word is `WIDE_WAVE_NO_GAIN` 🟥 (a miss, recorded as a negative).
- Result: **no move.** The wide brain stays HELM's canonical-brain CANDIDATE from c47 (a candidate pending a pair
  wave). The licensed brain stays canonical. The builder forecast `WIDE_WAVE_EARNED_KEEP` at about 0.5; it did not happen.

## How we got here (governance)

- **Package:** `HELM_R1_W6_20261019_SOURCE_R1W6.zip` v2 sha256 `729623429832c5fa99141d96876434d9ebed7417055c87173e7a582b3677be0a`,
  freeze `83983cd4d70efe31d993822fca2f38392327a6f72b9066246af5cd17c014341a`. v1 `f307bdbc…` is void and was never shipped.
- **Owner's line** (verbatim, pinned 18 UTF-8 bytes, sha256 `003f4051bd5f77686d36b4489c40680842ce89f9534ff9ca2be1749eb7979e45`):
  `PAIR WAVE at 1 USD`. Records: `APPROVAL_RECORD_R1W6.md` (`7f0bd262…`) / `.json` (`5187cb7c…`) v2: cap 1.00 USD, one
  attempt + one plumbing retry.
- **Operator I-checks by program before the reader** (`OPERATOR_I_CHECKS_C48.json`, `9e918bd2…`), all true: zip
  sha256; owner-line file = the 18 pinned bytes; seed source sha256("PAIR WAVE at 1 USD" + ":" + zip sha256) =
  `e0fce92d2f49bce33a1d8c883cb097f19295100e96ac3cc415cb26b50d29a66e` = the approval record's value; approval binds this
  zip and freeze; `MANIFEST_X6.json` = `4d81abff31238559c69a646faad33e74e70a413c8acd96794292e81d41741d78`; carrier pins
  `75fbd80b…`; carrier zip `6de3d782…`; c40 host file `c243a4cd…`; the nine spent language files present.
- **Sealed exam X6:** custodian handoff `X6_SEALED_20261020T045328Z.json` (`f157fff6…`), receiver check `all_pass: true`.
  Host carrier `X6_CARRIER_V1.zip` `6de3d78255a8bf5cb1bbcaae12f5aa2d4191b85c497544a7dd027364d1bbebc8` (top folder `x6`,
  six inputs + `X6_PINS.json`, no key file); spent-X5 carrier `X5SPENT_CARRIER_V1.zip` `653372b4…`.
- **The operator never opened, printed or parsed an X6 exam file.** Exam and carrier files were shipped by path and
  checked by sha256 and member NAMES only. Only the frozen reader read the keys, on the laptop.
- **Attempts:** ONE scored attempt; 0 plumbing retries used.
- **One laptop plumbing step, recorded (not a package change):** the first reader call refused at setup
  (`PinRefused: neighbour packages do not match their freezes`) because the seven neighbour packages were not yet
  extracted beside the fresh extract. The operator extracted the seven neighbour zips (each checked by sha256) to
  `reading_pkg/deps/` and ran the same reader on the SAME merge input (`ec5d5efe…`). First-call logs kept as
  `reader_try1.stdout.log` / `reader_try1.stderr.log`. Script: `job_record/reread_with_deps_c48.py`.

## Job, machine, money

| Job | What | Instance | Launch / end (UTC) | Host s | Charge |
|---|---|---|---|---|---|
| c48 | scored host run, stage `r1w6_host_run` PASS (supervisor exit 0) | `i-06ac5186ff7df015c` m6i.xlarge, us-west-2, `ami-0dddfa1ffa6b87af7`, 2-CPU / 14 GiB systemd slice (`systemd_scope_2cpu_14G`), 40 GiB gp3 | 05:00:55 / 05:05:09 (terminated); cleanup record 05:05:30 | 276.3 | 0.02 |

- **Source:** payload `c48-payload.zip` sha256 `af33fee8c92058bff19256e76d9e9a4339b82849ef5d2877b7341cd78cb17ac7`
  (1,197 members: the R1W6 v2 zip; neighbours w1 `31f97d67`, r1w2 `21ad185d`, r1w3 `152bca2a`, r1w3b `a4f82556`, r1w4
  `4bd0d740`, r1w5 `b6598687`, rbw1t `3a8ae37e`; carriers x6 `6de3d782`, x5spent `653372b4`). Builder:
  `job_record/build_payload_c48.py`; the kit's plan check PASS; the supervisor's plan validator True.
- **Purpose:** the R1W6 scored run per `LAUNCH_BRIEF_R1W6_20261019.md`. **Limits:** cap 1.00 USD; force cutoff 62 min,
  OS shutdown +60 min; stage limit 3000 s; runner deadline 2400 s; no automatic retry.
- **Transport:** own prefix `helm-r1w6-c48-20261020/` via four presigned URLs; no instance profile, no SSM; the shared
  four-key prefix was never touched (lease `CLAUDE_R1W6_C48_TRANSPORT_LEASE.json`).
- **Pacific time:** launched 10:00 PM, terminated 10:05 PM, 2026-10-19.
- **Timing:** runner 139.48 s; host unit pool 136.04 s; 77 of 77 units exit 0; deadline not hit.
- **Tests on host:** HELM's own suites (scratch copy of `helm_now/`): Ran 187, OK (skipped=2). Wave-6 unit and kit
  tests: Ran 24, OK (skipped=2). Host run test: Ran 3, OK. Wave-1 brain folder `65795c8c…` equal at start and end (HG15).
- **Charge:** **0.02 USD** (actual list price from host time: m6i.xlarge 0.192 USD/h + root disk + public IPv4 =
  0.015458 USD, rounded up to the cent; bill not posted). Cautious figure at 0.46 USD/h: **0.04 USD** (shown, not
  charged). Far under the 1.00 USD cap. Good.
- **Ledger:** read 112.97 before the hold (the brief said 112.99; the file said 112.97 and wins). Hold 1.00 USD:
  112.97 → 113.97 (reservation `BUDGET_RESERVATION_R1W6_C48.json` `4b2d3cee…`). Closed 113.97 → **112.99** of 200.00
  (unreserved 87.01). Addendum `BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_R1W6_C48_20261020T050828Z.json` (`3ef1ca34…`);
  ledger after `89bc2c52…`. One HISTORY line each for hold and closeout.
- **Cleanup VERIFIED, three ways:**
  - controller: terminated, volume `vol-0bd0b4e0f0c82afe6` deleted, own prefix purged (4 keys) and verified empty
    (`aws-c48-a1-cleanup.json` `5d5728a1…`);
  - independent check: `VERIFIED` at 05:06:28 UTC, within an hour (`3b7f9c15…`);
  - direct read-only look at 05:06:31 UTC: instance terminated ("User initiated (2026-10-20 05:05:09 GMT)"), no live
    project instance, no volume, no prefix version or delete marker, no multipart upload (`9f355671…`).
  - Proof `CLEANUP_PROOF_R1W6_C48.json` (`9d685627…`). No temporary role, profile or bucket created.
- Benign control note (as at c47): `InvalidInstanceID.NotFound` once, 0.1 s after launch, while AWS registered the instance.

## The reading

- **Verdict `PASS`.** Instrument rows all true: I0 not a practice mock, I1 data identity, I4 parameter counts, I6
  completeness, I7 laptop reading, I9 governance, I10 seed rule, I11 cut can fire (violator calls 214, 219, 215),
  I12 guard and canary can fire (violator trips 1016, 1044, 1056), I13 job maps, I14 not vacuous.
- **Hard gates all true (HG1-HG18):** receipts, no invention, replay, equal budgets, cut (0 honest faculty calls and 0
  steps in conversation), Eye writes 0, keys and learning audit, open simplex, guard trips 0, wide control, parameter
  audit, switch hygiene, key-blind, no network, sandbox, same inputs, Eye budget, voice changes no answer.
- **Marks:** NH ✅, NH-EYE ✅, NH-CONV ✅, QUIET ✅, K1 ✅, K3 ✅, **K4 🟥 missed**, K5 ✅, P ✅ (readable).
- **Status word** (frozen order): 1 no (PASS); 2 no (NH, NH-EYE, QUIET, K3 all met); **3 holds: K4 missed →
  `WIDE_WAVE_NO_GAIN`**.

## No harm (items lost vs FULL; ≤ 2 allowed)

| Exam | Lost by WIDE | Next to EYE_SCAN | Next to EYE_PAIRING |
|---|---|---|---|
| X6_E64 (English-64) | **0** (58 vs 58) | **0** | **0** |
| X6_F64 (Faces-64) | **0** (60 vs 60) | **0** | **0** |
| X6_PAIR A / B / C (resolved) | **0** (522 / 555 / 726 each) | — | **0** on A (1096 vs 1096) |
| X6_REAL (RIGHT, WIDE vs WIDE+Eye) | — | **0** (96 vs 96) | **0** (96 vs 96) |
| X6_CONV (conversation, NH-CONV) | **0** lost, 0 new wrong (FULL wrong 0, WIDE wrong 0) | — | — |
| REPRO_X5 (spent wave-5 files vs c40 FULL) | E64: 0 lost, 62 = c40's 62, 0 items changed; F64: 0 lost, 60 = c40's 60, 0 changed | — | — |

The 2 WRONG on X6_F64 are in FULL too (old HELM behaviour, not the wide brain).

## X6_REAL (128 fresh blind real recipes; 110 ANSWER keys, 18 UNDETERMINED; 101 representable and ANSWER-keyed)

| Arm | fully learned / 101 | RIGHT | WRONG | asks | not scored | lessons learned / wrong / not learned (of 673) | unexplained asks |
|---|---|---|---|---|---|---|---|
| ALWAYS_ASK | 0 | 0 | 0 | 110 | 18 | 0 / 0 / 673 | 0 |
| FULL (licensed only) | 0 | 0 | 0 | 110 | 18 | 0 / 0 / 673 | 0 |
| **FULL+WIDE** | **97 (bar 91)** | **96** | **0** | 14 | 18 | 573 / **0** / 100 | **1 (strict 1)** 🟥 |
| FULL+WIDE+EYE_PAIRING | 97 | 96 | 0 | 14 | 18 | 573 / 0 / 100 | 1 |
| FULL+WIDE+EYE_SCAN | 97 | 96 | 0 | 14 | 18 | 573 / 0 / 100 | 1 |
| FULL+WIDE_REPLAY | identical (HG3) | 96 | 0 | 14 | 18 | 573 / 0 / 100 | 1 |
| FULL+WIDE_NOASK (rule off) | 97 | 96 | 0 | 14 | 18 | 573 / 0 / 100 | 1 |
| WIDE_NO_LEARNING (control) | 0 | 0 | 0 | 110 | 18 | 0 / 0 / 673 | 0 |

- `caution_on_artifact_items` 0 in every arm. The one unexplained ask is also there with the rule OFF (NOASK arm: 1),
  so the new rule did not cause it. UNSETTLED_ASK fired 10 times, 0 on ANSWER keys.
- HELM's question codes, FULL+WIDE (codes only, from host records): `SUCCESS_EVALUATED` 100,
  `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` 17, `CLARIFY_WIDE_UNSETTLED_SAME_NAME` 10, `UNDETERMINED_CLARIFY` 1. Which ask is
  the unexplained one needs the keys, which the operator may not open; not computed.
- Per stratum (FULL+WIDE, fully learned / representable ANSWER, RIGHT): 2–3 ingredients integer 13/14 · 13, fraction
  11/11 · 11, mixed 11/13 · 11; 4–6 integer 10/10 · 10, fraction 13/14 · 13, mixed 13/13 · 12; 7–10 integer 7/7 · 7,
  fraction 11/11 · 11, mixed 8/8 · 8. WRONG 0 in every cell.
- vs c47 (different draw): c47 92 / 96 fully learned, 93 RIGHT, 0 WRONG, 0 unexplained; c48 97 / 101, 96, 0, **1**.

**UNSETTLED_ASK caution (K5):**
- Adapted mark (D-W6-6, same-name UNDETERMINED items): **1 commitment of 12** items, limit 2 → met ✅.
- Literal reading (all UNDETERMINED items, reported only): **4 commitments of 18**, limit would be 3 → it would be over 🟧
  (reported, not the mark).
- With the rule OFF (NOASK): 9 of 12 same-name and 14 of 18 UNDETERMINED answered. The rule cut them to 1 and 4 🟩.

## X6_CONV (64 conversation items; per arm RIGHT / WRONG / asks)

| Arm | RIGHT | WRONG | asks (UNDETERMINED) |
|---|---|---|---|
| FULL, FULL+EYE_PAIRING, FULL+EYE_SCAN, FULL−CUBE_STORE, FULL−ENGLISH_IN, FULL−TRIAD, FULL−VOICE | 30 | 0 | 34 |
| FULL+WIDE, +EYE_PAIRING, +EYE_SCAN, WIDE_NOASK, WIDE_REPLAY, FULL+WIDE−CUBE_STORE, −ENGLISH_IN, −VOICE | **38** | **0** | 26 |
| FULL+WIDE−TRIAD | 35 | **7** | 22 |

Reported: without the triad the wide path answers 7 conversation items wrongly; the triad is what makes it ask.

## X6_PAIR / X6_PAIRW backlog resolved (pooled over lives; WRONG 0 in every arm)

| Exam / family | Arm | Resolved |
|---|---|---|
| X6_PAIR A (1,558) | FULL / FULL+WIDE | 522 = 33.50% / 522 = 33.50% |
| | FULL+EYE_PAIRING / FULL+WIDE+EYE_PAIRING (and replay) | 1096 = 70.35% / 1096 = 70.35% |
| | CUT_VIOLATOR+WIDE / GUARD_VIOLATOR+WIDE (controls) | 1113 = 71.44% / 0 = 0.00% |
| X6_PAIR B drift (1,521) | FULL / FULL+WIDE | 555 = 36.49% / 555 = 36.49% |
| X6_PAIR C null (1,546) | FULL / FULL+WIDE | 726 = 46.96% / 726 = 46.96% |
| X6_PAIRW A (1,550; K7 = a real recipe) | FULL | 390 = 25.16% |
| | FULL+WIDE | 544 = 35.10% |
| | FULL+EYE_PAIRING | 929 = 59.94% |
| | FULL+WIDE+EYE_PAIRING | **1045 = 67.42%** |
| | FULL+WIDE−CUBE_STORE / −ENGLISH_IN / −TRIAD | 403 = 26.00% / 422 = 27.23% / 397 = 25.61% |
| | FULL−CUBE_STORE / −ENGLISH_IN / −TRIAD | 291 = 18.77% / 309 = 19.94% / 287 = 18.52% |

## The six pair words (word `PAIR_NOT_READ` because the status word is not EARNED_KEEP; `word_if_read` shown)

Numbers on X6_PAIRW A (1,550 items), where both parts are active. M(all) = both on, M(no_wide), M(no_x), M(none).
L = loss from switching off; E = L_wide + L_x; margin 775/4 = 193.75.

| Pair | M all / no_wide / no_x / none | L_wide | L_x | L_both | E | word_if_read |
|---|---|---|---|---|---|---|
| WIDE × CUBE_STORE | 544 / 390 / 403 / 291 | 154 | 141 | 253 | 295 | `ADDITIVE` |
| WIDE × ENGLISH_IN | 544 / 390 / 422 / 309 | 154 | 122 | 235 | 276 | `ADDITIVE` |
| WIDE × TRIAD | 544 / 390 / 397 / 287 | 154 | 147 | 257 | 301 | `ADDITIVE` (also X6_CONV, both active: 38 / 30 / 35 / 30, L 8 / 3 / 8, E 11, margin 8: `ADDITIVE`) |
| WIDE × EYE_PAIRING | 1045 / 929 / 544 / 390 | 116 | 501 | 655 | 617 | `ADDITIVE` |
| WIDE × VOICE | — | — | — | — | — | `NOT_EXERCISED_BY_CONSTRUCTION` |
| WIDE × EYE_SCAN | — | — | — | — | — | `NOT_EXERCISED_BY_CONSTRUCTION` |

All four read pairs are readable (mark P met). None is `CEILING_NOT_READABLE`.

## Eye writes, guard trips, false alarms

- **Eye writes:** 0 (EYE_PAIRING non-brain writes 0; EYE_SCAN writes 0; wide book changed by an Eye 0; whisper authors Eye only).
- **Guard trips on clean arms:** 0. GUARD_VIOLATOR trips 1016, 1044, 1056 (must be > 0; they are).
- **False alarms (QUIET):** 0 Body findings, 0 admitted whispers. EYE_SCAN scans: X6_E64 186, X6_F64 243, X6_CONV 457,
  X6_REAL 958; findings 0, admitted 0, presentation writes 0 on each.
- **Faculty calls in conversation (honest arms):** 0; attention steps 0.

## What this licenses, and what it does not

- **Licenses:** nothing new. The word is `WIDE_WAVE_NO_GAIN`, so by PREREGISTRATION_R1W6.md the wide brain does
  **not** become HELM's canonical brain across the switches. The c47 status stands as it was: RB-W1 v3 is a
  canonical-brain CANDIDATE (`VALIDATED` for c47's sentence only, ceiling `NAMED_CORPORA_ONLY`), pending a pair wave.
  Claim ceiling now `SYNTHETIC_ONLY`. The licensed brain keeps its license.
- **Recorded as negatives:** K4 missed (1 unexplained ask on a fully learned, answerable recipe; also present with the
  rule off); the literal K5 count 4 of 18 would be over a limit of 3 (reported only).
- **Facts that hold (real run, not a license):** 0 items lost on every exam; 97 of 101 learned; 0 wrong answers and
  0 wrong lessons; 0 false alarms; 0 Eye writes; 0 guard trips; four pair words read `ADDITIVE`.
- **Never, by this wave:** real kitchens or cooks; typed English in general; anything about CTT or any transformer;
  the 28 drive cells or 22 pathways; statistical superiority (one run, one draw).

## Files

Run folder `C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave6\run_c48_r1w6_20261020\`: `R1_W6_READING.json` (+ `.sha256`),
`MERGE_INPUT_R1W6.json`, `OPERATOR_I_CHECKS_C48.json`, `reader*.log`, `deliverable_unpacked_a1\` (host `R1_W6_HOST.json`
`07d5454bbb71dd1ae69dd52f85524a0879b718a9b6223f83ee86b77d8e1c8493`, `RUN_RECORD.json` `2b8eaa0f…`, unit files, logs),
`reading_pkg\`, `payload_c48\`, `job_record\` (controller, worker, receipts, deliverable zip `1381fa58…`, cleanup proof).
