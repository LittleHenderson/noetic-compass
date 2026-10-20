# RB-W1T, the sealed test of the wide recipe brain, job c46 (2026-10-19 Pacific): verdict `PASS`; status word `WIDE_LEARNING_DID_NOT_EARN_KEEP`

Status: REAL run. Every word below comes from a program, not from prose: `RBW1T_READING.json` (sha256
`698c2faf05b619e5f225be32f2d14b34511185ff9d723bf401ead7a00af163b1`) was written by the frozen reader
`rbw1t/merge_rbw1t.py` (`rbw1t.merge_rbw1t v1 (2026-10-19)`), run from a fresh extract of the sealed zip
`7c04a40855b81c6bfc5c1a44fc4486e112fcc4bf16bc37b1e84d7b457c6b009e` (freeze `b22690ce…`; every freeze member re-hashed,
0 bad). Merge input `MERGE_INPUT_RBW1T.json` sha256 `f7174777ec97fc971508a254266f1a609443da20f62a8fc81d510b06196011a8`.
Reader exit 0, empty stderr.

**Said plainly first.**
- HELM was taught 128 real cookbook recipes, drawn blind by the custodian. Each recipe was taught by one "we made it and
  ran out of X" batch per ingredient. Then it got fresh amounts and was asked "how much can we make?".
- The wide brain gave **0 wrong answers** and learned **0 wrong amounts** 🟩. It answered **89** recipes right. The
  licensed brain, the learning-off control and always-ask all answered **0** (they ask every time).
- But it fully learned only **90 of the 110** recipes it should be able to learn. The frozen bar is **99** (90%). It
  missed by 9 🟥. So the status word is `WIDE_LEARNING_DID_NOT_EARN_KEEP` 🟧.
- Switching the wide brain ON or OFF changed **nothing** on the four English-64 / Faces-64 files: 0 items lost, ON
  records equal OFF records 64 of 64 on each file 🟩.
- The biggest single reason for the misses (HELM's own refusal code): in **22 recipes HELM did not recognise the dish
  name** (`CLARIFY_ENGLISH_UNKNOWN_PRODUCT`), so it refused every lesson of that recipe. This was 2 → 0 on the practice
  draw, so the practice fixes did not carry over to fresh recipes on this point 🟥.
- The builder predicted this word at about 0.3 (and `WIDE_BRAIN_EARNED_KEEP` at about 0.35).

## The reading

- **Verdict `PASS`.** Instrument rows all true: I1 data identity (receiver check 17 of 17 rows true: frames pinned,
  sample / inputs / keys / turns recomputed, no excluded item or text, carrier exact and key-free, owner line frozen,
  seed rule), I6 completeness (21 of 21 units exit 0, every arm holds every item, carried suites OK), I7 reading from
  the sealed package, I9 governance, I10 seed rule, I14 not vacuous (110 representable ANSWER-keyed items ≥ 16).
- **Hard gates all true:** HR replay (WIDE = WIDE_REPLAY record for record; OFF_NOW = OFF_NOW_REPLAY on all 4 NH
  files), HC control, HP parameter audit, HSW switch hygiene, HK key-blind, HN no network, HS sandbox (wave-1 brain
  folder `65795c8c05fb687c7206fa9a449861ef988fa8b6be6d7d4061914c36db3a33c5` at start = end), HB same inputs
  (`8d3ff26b…` in every arm).
- **Marks:** K1 LEARNS **false** (90 < 99) 🟥; K3 SAFE true 🟩; K4 HONEST true (0 unexplained asks) 🟩; NH-OFF true 🟩;
  NH-ON true 🟩.
- **Status word** (frozen order, PREREGISTRATION §11): not 1 (K1 missed); not 2 (K3, NH-OFF, NH-ON all met); so
  **3. `WIDE_LEARNING_DID_NOT_EARN_KEEP`**.

## Main exam, per arm (128 recipes; keys: 118 ANSWER, 10 UNDETERMINED; 110 representable and ANSWER-keyed)

| Arm | fully learned / representable | RIGHT | WRONG | asks | not scored | lessons learned / wrong / not learned (of 651) | unexplained asks | answers on UNDETERMINED items | plain replies |
|---|---|---|---|---|---|---|---|---|---|
| LICENSED (yardstick) | 0 / 110 | 0 | 0 | 118 | 10 | 0 / 0 / 651 | 0 | 0 | 124 / 128 |
| **WIDE** | **90 / 110 (81.82%; bar 99)** | **89** | **0** | 29 | 10 | 483 / **0** / 168 | **0** | 7 | 125 / 128 |
| WIDE_REPLAY | identical record for record (HR) | 89 | 0 | 29 | 10 | 483 / 0 / 168 | 0 | 7 | 125 / 128 |
| ALWAYS_ASK (baseline) | 0 / 110 | 0 | 0 | 118 | 10 | 0 / 0 / 651 | 0 | 0 | 0 / 128 |
| WIDE with learning disabled (control) | 0 / 110 | 0 | 0 | 118 | 10 | 0 / 0 / 651 | 0 | 0 | 124 / 128 |

"Asks" = any non-answer on a scored item (scored UNDETERMINED, never WRONG). Right on representable items: WIDE 89 of 110.

### WIDE per stratum (fully learned / representable · RIGHT · WRONG · asks · not scored)

| Cell | Integer | Fraction | Mixed |
|---|---|---|---|
| 2–3 ingredients | 11/12 · 11 · 0 · 3 · 0 | 12/13 · 12 · 0 · 2 · 0 | 11/14 · 10 · 0 · 4 · 0 |
| 4–6 ingredients | 12/12 · 12 · 0 · 1 · 1 | 11/15 · 11 · 0 · 4 · 0 | 13/13 · 13 · 0 · 0 · 1 |
| 7–10 ingredients | **3/10** · 3 · 0 · 9 · 2 | 10/12 · 10 · 0 · 3 · 2 | 7/9 · 7 · 0 · 3 · 4 |

- By size: 2–3 ingredients 34/39 (RIGHT 33); 4–6 ingredients 36/40 (RIGHT 36); 7–10 ingredients **20/31** (RIGHT 20).
- By form: integer 26/34 (RIGHT 26); fraction 33/40 (RIGHT 33); mixed 31/36 (RIGHT 30).
- The weakest cell is 7–10 ingredients with whole-number amounts: 3 of 10.
- LICENSED, ALWAYS_ASK and the control: 0 RIGHT, 0 WRONG in every cell (they asked on every scored item).

### Why lessons were not learned (HELM's own refusal codes, WIDE, read from the host records by program; ids and codes only)

| HELM code on the lesson turn | lessons | recipes where it is the first miss |
|---|---|---|
| `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` (dish name not recognised) | 123 | 22 (every lesson of these 22 refused) |
| `CLARIFY_FACE_FACE_UNREAD` | 22 | 3 |
| `CLARIFY_ENGLISH_UNKNOWN_INGREDIENT` | 10 | 1 |
| `CLARIFY_NOT_CCE` | 8 | 1 |
| `TEACH_REFUSED_REFUSED_RAN_OUT_NOT_IN_BATCH` (ran-out name not in the batch) | 3 | 3 |
| `CLARIFY_ENGLISH_BATCH_NEEDS_PRODUCT` | 2 | 1 |
| **total not learned** | **168** of 651 | 31 recipes of 128 had at least one miss (97 had every lesson admitted) |

- Stock turn (fresh amounts) not recorded: `CLARIFY_ENGLISH_UNKNOWN_INGREDIENT` 20, `CLARIFY_ENGLISH_NO_INGREDIENT_NAMED`
  3, `CLARIFY_FACE_FACE_UNREAD` 3, `CLARIFY_ENGLISH_NO_STOCK_FRAME` 1, `CLARIFY_NOT_CCE` 1 (recorded: `STOCK_RECORDED` 98,
  `INVENTORY_RECORDED` 2).
- Question turn: `SUCCESS_EVALUATED` 96 (89 RIGHT + 7 on UNDETERMINED items, 0 WRONG), `CLARIFY_ENGLISH_UNKNOWN_PRODUCT`
  24, `UNDETERMINED_CLARIFY` 5, `CLARIFY_NOT_CCE` 3.
- **Not computed:** the builder's text classes (vague amount, unit outside the 20-unit table, same ingredient on two
  lines, alternatives). They need the lesson TEXT of the exam, which the operator may not open. The custodian or the
  builder's `diag_classes_rbw1t.py` (not in the sealed package) can compute them on the laptop exam copy if the
  coordinator asks. Practice had them at: no amount 25, unit not in table 45, duplicate 10 (of 660).

## No harm (switch OFF vs base; switch ON vs OFF)

| File | OFF_NOW = OFF_BASE (byte for byte) | OFF replay | lost by WIDE (≤ 2) | ON records = OFF records (operator check, report-only) | RIGHT / WRONG / UNDET (all four arms equal) |
|---|---|---|---|---|---|
| practice English-64 (`43ddd755…`) | 64 / 64 | identical | **0** | 64 / 64 | 61 / 0 / 3 |
| practice Faces-64 (`358df496…`) | 64 / 64 | identical | **0** | 64 / 64 | 60 / 2 / 2 |
| spent X5 English-64 (`1eb17c91…`) | 64 / 64 | identical | **0** | 64 / 64 | 62 / 0 / 2 |
| spent X5 Faces-64 (`2c7cac21…`) | 64 / 64 | identical | **0** | 64 / 64 | 60 / 2 / 2 |

Items lost: none (lost_ids empty on all four). WIDE's `build_loop` swap was restored on all four (`restored` true) and
its brain audit passed on all four.

## Parameter audit (hard gate HP: true)

After every WIDE item the only numbers in the brain's learned state were its coefficients, one per (recipe,
ingredient) on a support; the 9 unit factors equal their pinned exact values; the brain object held only its four
named attributes. So no learned number lives outside the table. Same on the four NH WIDE runs. In OFF units the wide
modules were never imported (HSW). The learning-off control kept the empty brain's digest after every lesson (HC).

## Custodian's strict-overlap note (REPORT_ONLY, carried forward from `RBW1T_SEALED_20261020T021432Z.json`)

Not in the preregistration; never used to step the seed. The frozen rule (id + equal text) is 0 and PASS. Against the
practice draw: 0 by id, 0 equal text, 85 items share a 16-character run, 0 share an 8-word run. Against the builder's
files (470): 0 id mentions, 87 items share a 16-character run, 0 share an 8-word run. The custodian's note: the
16-character runs are shared ingredient phrases.

## What this licenses, and what it does not

- **Licensed (PREREGISTRATION §12, word 3):** no move. The wide brain stays **`ENGINEERED-NOT-VALIDATED`**. It does
  NOT become HELM's canonical-brain candidate (that needed `WIDE_BRAIN_EARNED_KEEP`). The licensed brain keeps its
  license and stays canonical. The misses are recorded as negatives: K1 missed (90 of 110, bar 99).
- **What the run does show, as measured counts only (ceiling `NAMED_CORPORA_ONLY`, one run, one draw):** on these 128
  recipes the wide brain committed 0 wrong answers and 0 wrong lessons, asked with an explanation every time it asked,
  and left English-64 / Faces-64 unchanged with its switch OFF and ON. These are recorded facts of this run, not a
  license.
- **`NOT LICENSED`:** "the wide brain learns real recipes" (K1 missed); the wide brain as canonical-brain candidate;
  real kitchens or cooks; typed English; anything about the transformer (CTT); coverage of real cooking beyond these
  counts; "better than the licensed brain" outside these items; the 28 drive cells or 22 pathways; statistical claims.

## Operator checks (beside the reader's own rows)

- **Seed source:** owner line `WIDE TEST at 1 USD` re-checked by program: 18 UTF-8 bytes, sha256
  `759046548efa99a177ce6286d69c825b9bc5c09d7ac57c3f21fd3379d9d8ed8e` (approvals file line 160 shows it as
  `""WIDE TEST at 1 USD"."`; the pinned form is used, as the approval record states). sha256(line + ":" + zip sha256) =
  `07b27cdd6b0a9ed6b156df359776b98de2322e008e006a804eb76aa8d870e84f` = the custodian derivation's `input_sha256`;
  derivation `zip_sha256` = the zip; `overlap_check` PASS; derivation sha256 `b008971a…` (work copy = exam copy, by hash).
  The reader's I10 also re-derived it and found it equal.
- **Manifest** `MANIFEST_RBW1T.json` sha256 `9895fd95cd027590f8baed5ffb2e44bc45a9a632c8eb8db7cb113f4b54186658` (checked
  before ship and before the reading). Keys file by hash only: `efe9ee0d…`.
- **Package zip** `7c04a408…` verified before shipping; v1 `b50f4ca4…` (void) not used. Carriers shipped by path and
  checked by sha256 and member names only: `rw` = `RW_CARRIER_V1.zip` `f133e59b…` (INPUTS `8d3ff26b…` + PINS `8c296432…`,
  no key file), `x5spent` = `653372b4…` (`1eb17c91…`, `2c7cac21…`).
- **The operator never opened, printed or summarised an exam file.** The frozen reader read the exam; the operator's
  own tallies above read only HELM's status codes and record equality in the host output.

## Job, machine, money

| Job | What | Instance | Launch / terminated (UTC) | Host s | Charge |
|---|---|---|---|---|---|
| c46 | scored host run, stage `rbw1t_host_run`, supervisor `SUPERVISOR_ALL_STAGES_PASS` | `i-024d15d881ce9982e` m6i.large (2 vCPU, 8 GiB), us-west-2b, `ami-0dddfa1ffa6b87af7`, 40 GiB gp3 | 02:20:18 / 02:22:25 (cleanup verified 02:22:46) | 148.95 | 0.01 |

- **Pacific time:** launched 7:20 PM, terminated 7:22 PM, 2026-10-19.
- **Source:** payload `c46-payload.zip` sha256 `29e986ca19cac838dd7a10f3f382ca9a9f6066847fd52d7a722847e6b9da7d70` (743 members;
  host checked every one, 0 bad; after the run 741 source members unchanged, 0 extra); sources rbw1t `7c04a408…`, r1w3
  v3 `152bca2a…`, r1w3b `a4f82556…`, w1 v3 `31f97d67…`; carriers above; job plan `5a050757…` (`kit/plan_check.py`
  PASS, supervisor `validate_plan` OK); supervisor = the package's `kit/job_supervisor.py` `3b2337ca…` (byte-equal to c44's).
- **Purpose:** RB-W1T scored host run per `LAUNCH_BRIEF_RBW1T_20261019.md` step 3.
- **Limits:** cap 1.00 USD (scored + one plumbing retry); stage limit 3,000 s; runner deadline 2,400 s (record shows
  2,399); supervisor deadline 3,150 s; worker timeout 3,200 s; OS shutdown +60 min; controller and watchdog force cutoff
  62 min. No automatic retry.
- **Timing:** runner 24.87 s (HELM suites Ran 170 OK, skipped 2 — the laptop dry run had skipped 1; RB-W1T suites Ran
  24 OK; 21-unit pool 18.99 s at 2 workers). Host had 2 CPUs, 7,776 MiB, 25 GiB free disk.
- **Attempts:** ONE scored attempt; 0 plumbing retries.
- **Transport deviation (recorded, not a package change):** job c45 (CTT-1 rerun, g5.xlarge `i-0e8770f343f394444`)
  held the shared four-key prefix exclusively, so c46 used its own prefix `helm-rbw1t-c46-20261020/` in the same bucket,
  NO instance profile and NO SSM, four presigned HTTPS URLs only (the c44 pattern). Project tag `HELM-rbw1t-c46`.
  RUN_LIMITS named m6i.xlarge with a 2-CPU slice "or smaller if the operator's controller allows"; c46 used m6i.large
  (2 vCPU, no slice needed). The c45 folder, instance, tags and prefix were never touched.
- **Charge:** **0.01 USD** (list price from host time 0.00436 USD, rounded up to the cent; the bill is not posted).
  Cautious figure (the RUN_LIMITS conservative 0.46 USD per host-hour): **0.02 USD**. Far under the 1.00 cap. Good.
- **Ledger:** read 119.34 (c45's hold in it). Hold 1.00 placed: 119.34 → 120.34 (reservation
  `BUDGET_RESERVATION_RBW1T_C46.json` `68d20ec0…`; HISTORY line added). Closed 120.34 → **119.35** of 200.00
  (unreserved 80.65). Addendum `BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_RBW1T_C46_20261020T022413Z.json` (`37124bdb…`);
  ledger after `66ac69af…`. Both writes re-read the shared pointer just before writing (sha256 check). c45 stays open in
  `last_jobs`.
- **Cleanup VERIFIED, confirmed three ways:**
  - controller: terminated ("User initiated"), volume `vol-0c4c177f4972f7cf7` DELETED, own prefix purged (4 versions)
    and verified empty (`6d88fa77…`);
  - independent check: `VERIFIED` at 02:22:57 UTC, within an hour (`8d26c4f1…`);
  - direct read-only look at 02:22:59 UTC: instance terminated; no live c46 instance, no volume, no prefix version or
    delete marker, no multipart upload (`49355754…`).
  Proof `CLEANUP_PROOF_RBW1T_C46.json` (`cf54f083…`). No temporary role, profile or bucket was created.
- Free console: empty at termination (0 bytes); not needed, nothing failed.

## Files

- Reading `RBW1T_READING.json` `698c2faf…`; host `deliverable_unpacked_a1/results/rbw1t_host_run/out/rbw1t_out/RBW1T_HOST.json`
  `ac36b0155c6d7d1baa01d08bea46a42652b4365f1afeef7ad4c5b390e1fc91ab`; run record `222c7610…`; deliverable zip
  `1d80952e9dab4b385dfcfd85ba7f0d42ac323eabefb99bf63c842f577d93a24c`; reader logs `reader.stdout.log`, `reader.stderr.log`;
  job record `job_record/`.
- Controller: `Documents\Codex\2026-10-01\task-2\helm_operator_preparation\controller_claude_rbw1t_c46\`.
- Backup: `D:\tksCAS-archive\rbw1t_c46_20261020\`.
