# PREREGISTRATION_R1W2 - HELM-R1 wave 2: the licensed recipe brain in GB3's slot, every earned part on its own switch, one part switched off at a time

Written 2026-10-18 (Pacific) by the wave-2 builder session (Claude) on the owner's order "wave 2 plan". Plain
language. Frozen when sealed (`HELM_R1_W2_20261018/FROZEN_R1W2.json`); one scored attempt plus at most one plumbing
retry; a FAIL on any row is a finding. NOT LAUNCHED. No ledger hold placed.

Sealed package: `HELM_R1_W2_20261018_SOURCE_R1W2.zip`, sha256 `21ad185d885a11c4ee498e31e106c71ca608dc9edea1b201a283347086d58dc5` (772,593 bytes); `PACKAGE_FREEZE.json` sha256 `c8f82a6d652ae6f910021e9d1c19ad7e67bcf29bdacc0613b8eb469d84b29224` (181 members; resealed byte-identical).

## 0. What the owner ordered, and what this seal is

Wakil's words tonight, verbatim: "wave 2 plan". Standing rulings that bind it
(`Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`): "recipe brain is canonical" (the wave-1 c34-g brain is
HELM's one official brain, spec sheet §7.56), "no more GPU for now", "plain-rule valve", "Desire is Purpose", one stage
scale for all three faces, "min", "earliest", Wisdom rule C, "use my GitHub email".

**Scope of this seal.** Wave 1 (c34-g, §7.47) put the recipe brain in GB3's slot with five parts each on a switch,
and credited a part only "where switching it off lost". Wave 2 asks that question part by part: FULL (every switch
on) against the same brain with ONE part switched off, for the five wave-1 parts and the three parts added this week
(the triad adapter, everyday English in, the everyday voice), on HELM's own exams. T (GB3) is the frozen bar and is
not rerun; the lookup table is the no-recipe baseline.

**Relation to wave 1.** Wave 1's PASS (`R1_BEATS_GB3`, 32 against 9 and 17/2) stands and is not re-litigated. Wave 2
reuses wave 1's sealed v3 package byte for byte (zip `31f97d67...`, freeze `8c55c413...`), shipped beside this one,
and runs every recipe arm through wave 1's own command-line entry points. Wave 1's rows and margins are carried
verbatim where they apply; every new row is labelled PROPOSED.

## 1. Gate answer (the one paragraph CLAUDE.md asks for)

HELM ability advanced: attribution, which of the brain's and the live path's parts actually do work, measured by
taking each part away alone (retention and reasoning outcome types on Gate B and Task B; plain-English intake and
plain replies on English-16; not cooperation between parts, not growth). Before: wave 1 credited RECIPE_MATH, the
RPM gate and the restart fallback, read the cadence as mixed and the skin's form as broken, on one fresh exam; the
three new parts (§7.60, §7.62, voice) have never been switched off on a sealed exam. After: on two exposed exams
(c21's Gate B worlds, RB2c's Task B worlds), one fresh custodian-sealed exam (X1) and a sealed 16-turn English exam,
each of the eight switches gets one frozen word: EARNED_KEEP, NEUTRAL, HARMFUL or NOT_EXERCISED. Control that lacks the
mechanism: the same brain with that one part off, every other part held equal, plus wave 1's controls (replay,
label shuffle, untaught twins, the lookup table). Frozen criteria and denominators: section 4. What it will not show:
how the parts work together, anything outside synthetic worlds, whether the voice sounds natural to people.

## 2. The experiment

Eleven arms (`r1w2/arms_w2.py`, the full arm-by-exam table):

| Arm | What is off | Where it runs | Torch? |
|---|---|---|---|
| FULL | nothing (RECIPE_MATH, RPM_GATE, LACUNA_CADENCE, RESTART_FALLBACK, CCE_SKIN, TRIAD at Peak, ENGLISH_IN, VOICE on) | E1-E4 | no |
| -RECIPE_MATH | lookup table in its place (wave-1 A1_RM) | E1, E2, E3 Gate B and Task B | no |
| -RPM_GATE | wave-1 gate-off rules (A1_GATE, A1_GATE_LS, A1_GATE_D) | E1, E2, E3 incl. depth | no |
| -LACUNA_CADENCE | round-robin (A1_LC; wave 1's rule also needs A1_LC_R, carried) | E1, E2, E3 Gate B and Task B | no |
| -RESTART_FALLBACK | the fixed start only (A1_RF) | E3 depth families only | no |
| -CCE_SKIN | structured in and out only (A1_SK) | E3 CCE | no |
| -TRIAD | the wrapper off (FULL runs it with every face Peak; 0 learned parameters) | E4 | no |
| -ENGLISH_IN | checked form only | E4 | no |
| -VOICE | the loop's old adapter text | E4 | no |
| T | GB3, NOT RERUN: c21 Gate B 15/16 and 15/16; c27 Task B SUM 7 (T, 97 parameters), 19/2 (T+, 385) | frozen numbers | n/a |
| LUT | the no-recipe baselines: LUT_ARGMAX, EXACT_KEY / DIV_TOTAL / SMALLEST_INPUT, SMALLEST_LEAF | E1-E3 | no |

**Which arms need torch.** None. Torch is needed only for the WORLD LOADER: the host regenerates X1's Gate B worlds
with GB3's own `world()` (instrument I5, one subprocess) because GB3's worlds are defined by GB3's torch code. Every
answering process runs with wave 1's torch blocker (`rb.no_torch`). MLP_B (99 parameters) is pure Python but a neural
net, so by the GPU-first rule it runs on AWS only.

**A switch with no code path on an exam is NOT_EXERCISED there, stated now:** TRIAD (no exam carries a face
statement; the reader has no English for faces yet, §7.62), RESTART_FALLBACK on Gate B and Task B (wave 1: "the order
names the shape, so the fallback cannot fire"), CCE_SKIN outside the CCE exam, the three new switches outside
English-16.

## 3. Exams and seeds

| Exam | Data | Exposure | Mark |
|---|---|---|---|
| E1 Gate B | c21's sealed worlds, SAME_WORLDS_AS_C21 (wave-1 `frozen_exposed/worlds_sealed_c23.json` 1fb7a1c7...) | exposed | 12 of 16 per panel; T = 15 / 15 |
| E2 Task B | RB2c's worlds = c25's 20 draws (`frozen_c26/worlds_rb2c.json` 807cecdb...) | exposed | as frozen there: SUM of 32; T = 7, T+ = 19/2 |
| E3 fresh X1 | GB-X1, TB-X1, D34-X1 (two depth families, laptop), CCE-X1 (1,280 rendered inputs + 64 planted items) | fresh | wave 1's rows |
| E4 English-16 | 16 plain-English turns, sealed inside X1 | fresh | PROPOSED: FULL RIGHT >= 10 of 16, WRONG = 0 |

**X0 or X1: X1 is required.** Verified 2026-10-18 with the receiver's own checker (wave-1 `r1/check_fresh_format.py`):
X0's ORIGINAL custodian files still fail 3 of 5 (`CCE_PLANTED_W1.json` 1 problem; `D34_FRESH_TaskB_d3.json` and `_d4`
a TypeError); only the coordinator's converted copies pass 5 of 5 (`X0_RECHECK_20261018.json`). And wave 1's own
frozen rule makes X0 exposed after one scoring ("FRESH-W1 is scored once here; afterwards it is EXPOSED and serves
only as a regression exam", FROZEN.precode.json `exams.one_fresh_exam_per_wave`); c34-g scored it. So X1 is sealed
by a separate custodian session (`x1_contract/X1_CUSTODIAN_CONTRACT.md`): seeds from the sha256 of the exact bytes of
the owner's R1W2 sign line (X0's seed rule, word for word, with X0's own blocks added to the used regions); the five
wave-1-format files plus `ENGLISH16_X1.json`; the receiver's check (`r1w2/check_x1_format.py`, which runs wave 1's own
checker) must pass BEFORE sealing and its output goes into the seal record; the builder sees hashes only. X0 stays in
the run only as an exposure control (no X1 seed may occur in X0).

**English-16** (`r1w2/english16.py`): each item = setup through the loop's own channels (checked-form sentences and
witnessed batches, identical in every arm) + plain-English turns; only the last turn is scored. Families and counts:
stock then ask 4, absent then ask 2, question forms 3, "bake a batch" 2, a witnessed batch told in English 2,
must-ask (approximate, what-if, negated, relative) 3. Scored 3-valued from the loop's structured result: an ANSWER
item is RIGHT only with the exact yield and limiting ingredient, WRONG with any other number; an ASK item is RIGHT when
the loop asks and writes nothing, WRONG when it answers, teaches or records; a LEARN item is RIGHT when the brain now
holds exactly the key's requirement. UNDETERMINED is never WRONG. Reply rows for VOICE: PLAIN = no CAS token by
`helm_voice.cas_tokens` (the voice's own frozen detector, a stated limit); FACT_KEPT = a RIGHT answer's reply names
the limiting ingredient.

## 4. Frozen rows

**Instrument rows** (wave 1's I1-I8, adapted only where T is not rerun; I9 new and PROPOSED). I1 data identity (X1
pins given = host = depth; every file by hash; the seal record lists the same hashes and carries the receiver check
with all_pass; exposed files, the wave-1 package and the GB3 zip by hash; X1 valid by wave 1's loaders and label
audit; no X1 seed in c23, c26 or X0; no English-16 turn equal to a string in the packaged English tests). I2 T's
frozen references by hash (T is not rerun). I3 reproduction, wave 1 verbatim (FULL on E1 = c23 RB-det, FULL on E2 =
c26 RB-det on all 20 draws, depth D00). I4 parameter counts (RB-A 68, RB-B 32, MLP-B 99, TRIAD 0 learned; T 97 / T+
385 printed). I5 X1 Gate B regeneration equal (torch). I6 completeness (every unit exit 0, no deadline, host tests and
wave 1's 128 carried tests OK, English-16 complete in all five units, every depth part COMPLETED). I7 readings by
hash, the reader runs from the sealed zip, the host and run record name its freeze, the depth ran under wave 1's d34
manifest `59f1be24...`. I8 wave 1's proven floors on TB-X1. **I9 governance (PROPOSED, the owner's order):** the
approval record names THIS zip and freeze, its sign line carries this zip's first 8 hex, the controller shipped
exactly this zip, no reseal after signing; and the supervisor's stage is PASS with no missing outputs and found
`r1w2_out/R1_W2_HOST.json` with the host reading's sha256. Any row false: INSTRUMENT_ERROR.

**Hard gates** (wave 1's H1-H7 without T's parts; H8 new and PROPOSED). H1 every admitted write receipted (all recipe
arms on E1-E3, depth, no English-16 turn REFUSE_RECEIPT_INCONSISTENT). H2 no invention. H3 replay (A1 = A1_REPLAY on
E1-E3; depth; FULL = FULL_REPLAY on English-16 record for record). H4 restart (Gate B 16 of 16 same with same state on
E1 and E3; Task B 16 of 16 on every draw on E2 and E3). H5 skin neutral (1,280 identical). H6 controls on the fresh
exam (twins, shuffled, label shuffle at most 6 of 16; depth controls zero). H7 equal budgets (512 / 512; MLP-B 512;
depth). **H8 (PROPOSED):** the triad at Peak and the voice change no answer (FULL = -TRIAD and FULL = -VOICE on every
English-16 structured result). Any gate false: FAILURE, the gates named.

**Margins** (wave 1's, verbatim): Task B 4 of 32; Gate B panel 2 of 16 (cadence harm); Gate B hold 1 (A1 >= T - 1);
depth 16 of 512; controls band 6 of 16; the gate has no margin (rule (a) RIGHT(FULL) >= RIGHT(off) on every panel,
rule (b) pooled WRONG strictly fewer). **PROPOSED:** English-16 2 of 16 (wave 1's 4 of 32 as a ratio); plain replies
2 of 16.

**One comparison per switch per exam** (WIN / TIE / LOSS; `FROZEN_R1W2.json` `per_exam_comparisons`): wave 1's own
switch rules applied exam by exam (RECIPE_MATH on Task B with the no-recipe baselines below 12; RPM_GATE rules (a) and
(b), depth only (a); cadence; restart fallback per depth family); CCE_SKIN a TIE by construction (H5) with wave 1's
form word reported beside it; ENGLISH_IN and VOICE by the PROPOSED margins.

**One word per switch:** HARMFUL if any LOSS (checked first); EARNED_KEEP if at least one WIN and no LOSS; NEUTRAL if
exercised and all TIE; NOT_EXERCISED if no exam has a comparison (TRIAD, stated now); INCOMPLETE if a needed
comparison is missing (never a pass). Words are licensed only when the test verdict is PASS.

**Marks for FULL, reported beside the words (a miss is a finding, not a gate):** FULL holds wave 1's Gate B rows on
E1 (12 of 16; panel-1 + new >= 30 - 1) and on X1; FULL beats T's frozen c27 sums by 4 on E2; FULL's SUM on TB-X1;
English-16 PROPOSED RIGHT >= 10 and WRONG = 0.

**What PASS, FAILURE and INSTRUMENT_ERROR mean.** PASS: every instrument row and hard gate held; each word stands as
written, inside SYNTHETIC_ONLY. FAILURE: a part broke a rule it must keep (named); no word is licensed. INSTRUMENT_ERROR:
the measuring went wrong (data, completeness, governance); nothing about the brain is read; the attempt is consumed.

## 5. Evidence the run produces

Host (raw only): `r1w2_out/R1_W2_HOST.json` and its `.sha256` sidecar, `INSTRUMENTS_R1W2.json`, `I5_GB_X1.json`,
`R1W2_UNITS.json`, every unit's TEACH / panel / twin / restart / CCE files, `E4_ENGLISH16/E16_<unit>.json`, the unit
logs, `RUN_RECORD.json`, `unittest.log`, `unittest_w1.log`, the supervisor receipt. Laptop: `d34_runs/` (20 part
folders, `D34_READING.json`). Reader: `R1_W2_READING.json` and its sidecar.

## 6. Deviations (each a recorded decision, not a tuning)

- D1 T is not rerun (owner's design): its c21 and c27 numbers are read from wave 1's frozen reference files (I2);
  wave 1's T-dependent rows (I2 re-teach, I5 Task B fairness, H4/H6/H7 T parts) do not apply.
- D2 E1 and E2 are exposed exams by the owner's design; a WIN there is on worlds the brain was scored on before
  (c23, c26). Attribution, not freshness. FULL on E1 and E2 must reproduce c23 and c26 exactly (I3).
- D3 The depth families stay a LAPTOP stage, as in wave 1: wave 1's depth code and its 197 pinned sources hard-code
  Windows paths (e.g. `rb_c4/casform.py` COMPILER_ROOT, `rb_c4/taskb.py` RB2_PKG); porting them to the AWS host is a
  separate build. Each part is small (D00 measured 35.1 s on 2026-10-18; cap 300 s, 300 MiB) and starts only with
  at least 300 MB free RAM. If the laptop cannot host them, the coordinator reports the blocker; there is no silent
  fallback and the reading waits (I6).
- D4 The c34-g supervisor defect is fixed and tested before sealing (section 7): the plan declares the outputs at
  `r1w2_out/`, where the runner keeps them; the runner keeps `.sha256` sidecars; the supervisor records the sha256 of
  every declared output and names a same-named file found elsewhere; `kit/plan_check.py` proves the plan and the runner
  agree and replays c34-g's own plan and runner to show the old pair fails it.
- D5 English-16 harness settings, the same in every arm: the agentic executor is a refusing stub (the loop's agentic
  path is outside the circuit and can touch files); the loop's `_bias_digest` is read through the triad wrapper (a
  marked copy, tested equal for an unwrapped brain); no trace file.
- D6 Wave 1's random-order cadence control A1_LC_R and the label-shuffle and gate-off-shuffle controls are carried
  (wave 1's word rules need them); they are not among the eleven arms.
- D7 The depth gate comparison can only TIE or LOSE (wave 1 has no rule (b) on depth).

## 7. Laptop dry run on exposed data (facts, not claims; `TEST_RECORD_R1W2.md`)

68 units on exposed data, one at a time: 68 exit 0 in 391.9 s. FULL reproduces c23 RB-det on E1 and c26 RB-det on all 20 draws of E2 (wave 1's I3, verbatim), and c34-g's own A1 labels on X0 (Task B every draw, Gate B new worlds). The reader runs end to end and says INSTRUMENT_ERROR on that input, as designed. Details: `TEST_RECORD_R1W2.md` section 7.

## 8. Cost and limits

One AWS host (`m6i.xlarge`, 2-CPU slice, 14 GiB, the c21 image, us-west-2), two units at a time; command deadline
5,400 s; host window 120 minutes. From c34-g's measured unit times (Gate B 25.6 s and Task B 413.9 s of CPU per exam,
on a host where 95 percent of the compute was the T and T+ reruns wave 2 drops): about 1,100-1,300 s of pure-Python
CPU, about 15-25 minutes of command, about 30-45 minutes of host. About 0.25-0.35 USD per attempt at the conservative
rate (0.46 USD per host hour; list 0.192); at most 0.92 at the window. Worst case for the wave: X1 custodian job
0.50 + scored attempt 0.92 + one plumbing retry 0.92 = 2.34 USD. **Proposed cap: 5 USD for the wave, PROPOSED.** Wave
1 needed 7 attempts for plumbing; wave 2 budgets ONE scored attempt plus ONE plumbing retry, and says so. Ledger read
2026-10-18: 110.35 of 200.00 used, 89.65 free. No hold placed.

## 9. What wave 2 may and may not license

May (only with PASS): "On synthetic worlds only, with one part switched off at a time and everything else held
equal, HELM's licensed recipe brain and its live English path were scored on HELM's own exams; each part's word says
whether switching it off lost (EARNED_KEEP), changed nothing (NEUTRAL), helped (HARMFUL) or was never on the exam's
path (NOT_EXERCISED)."

Never: any cooperation or interaction claim between parts (one part off at a time cannot show it); anything outside
synthetic worlds; that the voice sounds natural to people (the 50-row rating sheet is still open); that real
reagents carry a triad; statistical superiority (one run); any claim about T beyond its frozen c21 and c27 numbers;
operation in real kitchens or on real data.

## Amendment log

(empty at sealing)
