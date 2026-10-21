The "Unity Eye" in the records is several separate builds that share one set of rules. None of them may write to the brain. The Eye may only act in a separate, frozen test the owner approved by name. As of today, nothing gives the Eye a role in deciding how deep the RPM chain goes.

**Sources and scope.** All repo references are to `origin/claude/project-thread-pmbzd6` in `C:\tmp\helm-ctt2r-c49-read`, read with `git show`. Nothing was checked out or written. `OWNER_RULING_UNITY_EYE*` and `UNITY_EYE.md` are not in any remote branch of that clone. They are off-repo, in `C:\Users\wakil\Documents\Codex\2026-10-15\helm_language_faculties_circuit_design_v1\`. I read them there, and the line numbers the code quotes from them match. Spec lines are `docs/CAS_HARNESS_SPEC_SHEET.md:<line>` on the branch.

**The separate Eyes:**
- **A. Package-health watcher.** In-repo code: `docs/working/noetic_council/faculties_v2/eye/`. Report-only. It reads the recorded test results of two packages.
- **B. Station watcher.** Report-only, inside LM-T4 and LM-T6. Off-repo.
- **C. Acting Eye.** U1 and U1b: whispers, an "autonomic" repair tier and a two-way "concert" ledger with the brain. Off-repo.
- **D. Self-scan.** U3-T1 and the wave 4 switch `EYE_SCAN`: a Mind scan and a Body scan, with report and whisper. `helm_ui/eye_runner.py` imports it read-only.
- **E. Pairing Eye.** RB-I3 and the wave 5 switch `EYE_PAIRING`.
- **F. Eye trim.** RB-P1.

---

## (1) The three properties and where each is enforced (Eye A, the in-repo code)

Stated in `eye/eye.py:8-21` and repeated in `faculties_v2/README.md:272-280`.

**1. It sits outside what it watches.**
- It reads each package only through `eye/tap.py`.
- `Tap.read()` hashes the folder before and after reading (`tap.py:147-174`). If the two hashes differ, it refuses with `WATCHED_VALUE_MOVED` (`tap.py:168-173`).
- The Eye's own folder and `__pycache__` are excluded from the hash, and the exclusion is printed in every reading (`tap.py:43-46`).
- It never imports the packages it watches. It parses their source as text (`signals.py:34-41`, `signals.py:199-215`).
- Tests: `test_the_eye_cannot_alter_any_watched_value` (`test_all.py:1379-1413`) re-hashes the watched folders from outside the Eye. `test_the_eye_tap_refuses_a_reading_across_a_write_and_the_check_can_fail` (`test_all.py:1416-1438`) proves the refusal can actually fire.

**2. It cannot write.**
- Its only store is `self._log`, an in-memory list (`eye.py:141`).
- No public method name contains "write" or "save", and the eye files contain no `os.remove`, `shutil`, `os.rename`, `os.replace` or `os.makedirs` (`test_all.py:1399-1413`).
- `read()` records `eye_wrote_nothing` (`eye.py:181`).
- A comment marks it "UNDECIDED IN SOURCES" whether the log may ever go to disk. This build keeps it in memory only (`eye.py:66`).

**3. It never gates.**
- `read()` returns a reading and `would_propose()` returns records marked report-only (`eye.py:17-21`).
- No brain module imports it: `faculties.py:57-62`, `drive_loop.py:55-62` and `guard.py:62-63` import no eye.
- The ablation test `test_removing_the_eye_changes_no_decision_anywhere` (`test_all.py:1441-1478`) runs 12 ticks with and without the Eye. It requires every TurnRecord, the buffer digest, the Bias digest and version, and the satisfactions to be identical. It also forbids "import eye" in `guard`, `held`, `faculties`, `drive_loop`, `restart` and `bias`, and forbids methods named `passes`, `gates`, `blocks`, `admit`, `allow` or `deny`.

Claim ceiling, verbatim (`eye.py:30-31`): "MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM."

The same three properties come from the design: `UNITY_EYE.md:105-113` (outside the stations, digest-checked taps) and `:146-163` (guardrails 1-8, including guardrail 6, the report-only switch, at `:159-161`).

## (2) What signals it reads, and could read

**What Eye A reads today.** It reads package health only, never a question in progress.
- It reads five ingredients, each an exact `Fraction` with requirement a_i = 1 (`signals.py:12-23`, built at `signals.py:289-304`):
  - `tests_passing`
  - `suite_complete`
  - `mechanism_proofs`
  - `design_coverage`
  - `read_only`
- It reads recorded suite results from `eye/recorded_suite_results.json` and never runs a suite itself (`signals.py:34-38`, `:149-174`).
- It watches two packages, `faculties_v2` and `language_v2` (`signals.py:106-127`).
- The code says why: "these builds have no stations, no drive loop and no dialogues" (`signals.py:78`).

**How the readout works.**
- **Score (Y_T).** Y_T = min_i(x_i / a_i), the share of the most-short ingredient (`recipe.py:192-197`).
- **Limiting reagent.** The ingredient(s) at that minimum (`recipe.py:199-204`).
- **Gate words, per package.** They are words, never a score (`recipe.py:46-51`, `:219-236`):
  - G1 = an ingredient is ABSENT
  - G2 = nothing was read
  - G3 = a tie at the minimum
- **Headline gate across packages.** Only G2, G3 or G4 can appear (`eye.py:338-375`). G4 ("last receipt failed") is set only by `recheck()` (`eye.py:218-220`). G1 appears only inside each package's own record (`recipe.py:247`).
- **ABSENT is not zero.** An absent ingredient reads UNDETERMINED (`recipe.py:75-77`). "Limiting Reagent ≠ Lacunarity" (`recipe.py:23-24`). There is no `×` in the recipe (`recipe.py:21-22`).
- **Receipt.** eta = the written record (`recipe.py:239-248`). epsilon = recompute Y_T and the limiting reagent from the stored counts (`recipe.py:250-259`). The two are compared in `receipt()` (`recipe.py:261-280`) and in `UnityEye.recheck()` (`eye.py:196-226`).
- **Output on this branch:** "weakest package: faculties_v2 (Y_T 4/9). Limiting reagent: design_coverage -- 4 of 9 faculties carried" (`faculties_v2/README.md:288-294`).

**What the design says a brain-wide Eye would read.** This is design only, defaults PROPOSED.
- Nine health ingredients (`UNITY_EYE.md:69-103`): receipts passing, lacunae on cadence, stations aligned, drive pair balance, drive entropy, continuity lawful, memory check holding, answers determined, language skin exact.
- Signals station by station (`UNITY_EYE.md:115-129`):
  - S0: π_t against the pair cap and the entropy check; STARVED; open questions and their age.
  - S2: ABSENT slots, FADED cells and DIRTY flags.
  - S3: UNDETERMINED and its gate word.
  - S4: region × outcome; the ALIGNED and MISALIGNED counts; UNASSESSED counted apart.
  - **S5 RPM link: "receipts passing / checked; depth n against 5; G5; memory-check losses".**
  - S6: seams and interpolations.
  - Also the faculty buffers, the growth ledger and the language skin.
- LM-T4 ran this report-only over every station, as Eye B (spec:1381):
  - 6,716 stage events; would-FIX 280; would-HELP 7,548.
  - It most often named "the F1↔F7 dial gap" as most short of unity, and read UNDETERMINED on most stages.
  - It logged 504 would-HELP on clean dialogues. That is the false-alarm baseline U1 must beat.
- The owner's fourth acting message has a dispatch reading, marked PROPOSED (`OWNER_RULING_UNITY_EYE_ACTING_20261015.md:87-97`). In idle time the Eye picks past "erroneous" or "expensive" decisions. "Expensive" includes **"deep RPM descents"** and "long chains for small gains". It then assigns a drive × faculty pairing to examine them.

**What Eye D (U3 self-scan) reads** (spec:2583):
- **Mind scan:** what the brain was taught, tested on, slipped on and never used.
- **Body scan:** record read-back, seal match, whether store answers still re-derive, and the gap ledger.
- **Triggers:** periodic, self-initiated or owner-initiated.
- **Timing:** no scans while awake. A whisper due while awake "waits for the turn to end" (`docs/working/r1_wave4/PREREGISTRATION_R1W4.md:200-203`).

**What Eye E (pairing) reads.** Verifier verdicts only, kept in a 7 × 7 table of tries and successes (spec:2628).

## (3) "would_propose" and "whisper", and how a proposal travels

**`would_propose` (Eye A, `eye.py:229-303`).**
- It returns a tuple of plain records. Each record has package, kind, ingredient, detail, `through` (the route a later acting build would use), `never` (what it must never do), and `mode: REPORT_ONLY` (`eye.py:324-335`).
- Mapping from ingredient to kind:

  | Reading | Kind |
  |---|---|
  | `mechanism_proofs` | FIX |
  | `tests_passing`, `suite_complete` | HELP |
  | `design_coverage`, `read_only` | REPORTED |
  | nothing measured | REPORTED |
  | Y_T ≥ 1 | NONE |

- **Travel:** none. The records go back to the caller, and `report()` prints them (`eye.py:305-318`). No module consumes them.
- FIX "must go through the same VERIFY and receipt path as any other change; the eye never performs either" (`eye.py:23-28`).
- The code comment says "the owner's acting ruling approves acting only inside test U1 ... so this build marks every proposal REPORT_ONLY" (`eye.py:64`).
- The guard rule: "Randomness may only propose; the verifier, the receipts and the RPM Gate always decide" (`guard.py:8-10`).

**What fix and help mean in the design** (`UNITY_EYE.md:43-49`, `:131-142`).
- **FIX** = a rollback or re-fit proposal sent through VERIFY V1-V7 and the η∘ε receipt.
- **HELP** = a faculty start through the faculty-start door, a question naming the exact gap, or an advisory attention proposal.
- An injection carries its own tag, `EYE_PROPOSED`, which is never a witness (`UNITY_EYE.md:112-113`).
- Rate limit (PROPOSED): 1 FIX + 2 HELP per 16-tick stage (`:153-154`).

**Whisper (the ladder put to the owner and answered "U1 now", `..._ACTING_20261015.md:17-29`).**
- **Soft whisper:** breaks a tie in the drive loop or at a faculty door.
- **Strong whisper:** "can redirect the brain's next station, never past a gate or receipt".
- **Safe repair:** re-check, revisit, roll back to the last verified state, or mark an answer UNDETERMINED.
- **Escalate:** ask the owner.
- **Never:** see section (5).
- The brain may decline a whisper, and must log why.
- The record lists two more items as dispatch readings marked PROPOSED, not owner words:
  - a shared, append-only "concert ledger" between Eye and brain (`:33-37`);
  - an "involuntary" tier with no veto, which "adds no new fact, learned value, recipe or capacity; restores a digest-verified prior state" (`:59-71`).

**Later definition (owner approvals record, `C:\Users\wakil\Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md:92`).** "whisper = a nudge of the brain's attention toward a finding, through the normal gate, never a write."

**Wave 4 route** (`PREREGISTRATION_R1W4.md:60-77`, `:200-210`).
- After a complete scan, the Eye may send at most 2 whispers, Body findings only, each `{target, finding_id, evidence, notice}`.
- The gate admits a whisper only if three checks pass:
  - the target exists (else `GATE`);
  - every evidence reference resolves in that scan's facts (else `RECEIPT`);
  - fewer than 2 were admitted this idle window (else `BUDGET`).
- `r1w4/eye_live.py WhisperReceiver.present` sits between `ExamLoop3.process_turn` and `helm_chat._speak`.
- If the turn touches a held whisper's target, the answer is held back as `CLARIFY_SELF_CHECK` and the notice is spoken. It calls no loop, store, triad or brain.

**Wave 5 route** (`PREREGISTRATION_R1W5.md:181-186`, Q5 PROPOSED).
- STRONG whisper = the Eye's best cell, first try on an item. It is always followed.
- SOFT whisper = a seeded alternative after a failure. It is declined if the cell has at least 4 tries and a score (S+1)/(T+2) below 1/4. The decline is written by the brain as `RESPONSE followed=False`.

**`helm_ui/eye_runner.py`.** It runs one U3 scan in arm `OWNER_INITIATED/REPORT_ONLY`: "the owner asked, the Eye reports, no whisper" (`:5`, `:19`). It runs on a dev-seed test copy, not this chat (`:50-51`). It reports `eye_writes_to_brain` and `whisper_writes` (`:55`).

## (4) Every measured Eye result, with exact words

Claim-status words below are the sheet's own vocabulary.

- **§7.35 LM-T4, Eye B report-only** (spec:1360, 1381, 1384).
  - The sealed reading is `INCONCLUSIVE`. A corrected reading gives `EYE_REPORTED`, but it is post-run and does not count.
  - EYE-R2: 106,400 of 106,400 reads digest-equal. Receipts 6,716 of 6,716. Door calls 0.
  - "the eye's judgement": NOT LICENSED.
- **§7.100 LM-T4b** (spec:3605, 3635). Sealed reader: `HARD_GATES_PASS` and `EYE_REPORTED`. The language sentence is `LICENSED` (`SYNTHETIC_ONLY`). "the eye's judgement" is NOT LICENSED (504 would-HELP on clean dialogues).
- **§7.38 U1, Eye acting** (spec:1434-1462). `INCONCLUSIVE` in both readings; test verdict INSTRUMENT_PROBLEM.
  - The random-whisper control A5 broke G_CLEAN_A5.
  - EYE_EARNED_KEEP, CONCERT_EARNED_KEEP, CHECKLIST_SUFFICES and EYE_HARMFUL were "not awarded and not refuted".
  - A4 (concert) fixed 148 of 148 with 1,816 clean-world interventions. A6 (checklist) fixed 128 with 10,152.
  - Flag kept as found: under the frozen rules, A2-A4 would have read `EYE_HARMFUL` (counts 155 / 258 / 258).
  - "The eye's acting stays NOT LICENSED; claim ceiling SYNTHETIC_ONLY" (spec:1460).
- **§7.40 U1b, fresh-world retest** (spec:1507-1513). READ; `EYE_EARNED_KEEP` and `CONCERT_EARNED_KEEP` "for this test only".
  - A4: 148 of 148 fixed vs A6's 128. Clean interventions 1,816 vs 10,152. 0 keyed answers worse than A0.
  - SYNTHETIC_ONLY; "No real-world or HELM production claim follows".
  - It does not rewrite U1's reading.
- **§7.41 LM-T6** (spec:1515-1521). `EYE_REPORTED` was earned among five words. The Eye stayed report-only.
- **§7.42 RB-P1, Eye trim and pruner** (spec:1523-1529). Overall FAIL, `PRUNER_DID_NOT_EARN_KEEP`. EYE_TRIM_ONLY kept answers on 704 of 704. The pruner claim is NOT LICENSED.
- **§7.65 RB-I1c** (spec:2224). This is a faculties and drive-loop retest, not an Eye test. `HARD_GATES_PASS`, status `INCONCLUSIVE`. It carries no Eye word.
- **§7.69 wave 3** (spec:2266, 2398). The `EYE` switch was "U1b's whispers + autonomic sweep, IDLE only; off in every awake exam". Result: EYE `EARNED_KEEP` (cascade 64 vs 56). `LICENSED` only within `SYNTHETIC_ONLY` and only for the reader's own sentence.
- **§7.73 U3-T1 self-scan** (spec:2581-2624). `SELF_SCAN_EARNED_KEEP` and `WHISPER_EARNED_KEEP`.
  - 176 of 176 faults found, 0 false alarms.
  - Next presentation pointed at the fault: 240 of 240 with whispers, 49 of 240 with report only.
  - `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY`.
  - Negative: the self-initiated trigger alone found 16 of 176 (spec:2622).
- **§7.74 RB-I3 pairing** (spec:2626-2664). `EYE_PAIRING_EARNED_KEEP`, `HARD_GATES_PASS`.
  - 77.28% resolved vs random 37.33%.
  - `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY`.
  - NOT LICENSED includes "that the Eye should act outside tests".
- **§7.77 wave 4, c39** (spec:2742-2793). PASS; `EYE_SCAN_EARNED_KEEP`.
  - 88 of 88 found, 88 of 88 acted on, 0 lost, 0 false alarms, 0 Eye writes.
  - `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY`.
  - Negative: the self-trigger alone found 0 of 88 (spec:2792).
- **§7.78 wave 5, c40** (spec:2795-2840). `HARD_GATES_PASS`; `EYE_PAIRING_EARNED_KEEP`.
  - 70.18% resolved vs random 35.32% and the frozen-table control 38.83%.
  - `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY`.
  - NOT LICENSED: "that the Eye may act outside tests" (spec:2839).
  - Negatives (spec:2840): slow drift recovery (1 of 3 lives); the decline rule cost 60 items; the Fisher-Rao step was −2.9158 points.
- **§7.81 X-REAL** (spec:2982). The Eye self-scan is `VALIDATED` only for catching D1 and E1 on real damage kinds, ceiling `NAMED_CORPORA_ONLY`. NOT LICENSED: "that the Eye beats a file checksum on any kind; that the Eye acts on real damage".
- **§7.93 and §7.96, wave 6** (spec:3404, 3498). Eye writes 0, 0 false alarms, NH-EYE passed next to each Eye.
- **§7.97, 28 cells** (spec:3514-3532). Census found 0 fillable cells. Status: design and stage-1 tags only, `ENGINEERED-NOT-VALIDATED`.
- **§7.115 memory compaction design** (spec:4094). "Eye acting stays `NOT LICENSED`". The Eye is REPORT-ONLY in TEACH-1.
- **Eye A** (§7.48 table, spec:1711): `ENGINEERED-NOT-VALIDATED`. Its suite is recorded 49 of 49 in `recorded_suite_results.json`. It is mechanism only.

## (5) Owner rulings that bind what the Eye may never do

1. **Form and mode, ACCEPTED_BY_OWNER** ("LET'S GO WITH YOUR RECOMMENDATION").
   - Form is MINI-VERSION. LM-T4 mode is REPORT-ONLY. It sits outside the stations, uses read-only digest-checked taps, and enters only through the faculty-start door.
   - "U1 is not approved by this ruling" (`OWNER_RULING_UNITY_EYE_20261015.md:23-32`).
   - Owner purpose, verbatim: "IT'S MAIN PURPOSE MUST BE AND ONLY BE THE FIRST FOUNDATION /DESIRE UNITY" (`UNITY_EYE.md:19-22`).
   - Still PROPOSED, not accepted: "The eye never starts growth" (Q21), the rate limit (Q20), and a_i = 1 (Q24) (`OWNER_RULING_UNITY_EYE_20261015.md:33-39`).
2. **Acting ruling (2026-10-15).**
   - The "never" list in the recommendation the owner answered with "U1 now" (`..._ACTING_20261015.md:21-22`): "write a fact or a learned value itself; skip a gate; change its own rules; start growth; whisper for anything but Unity".
   - Status block (`:47-49`): "Approved: U1, laptop, no spend ... Not approved: the eye acting in any other test (LM-T6 keeps it report-only ...), any AWS spend, growth started by the eye."
   - Also: "never pruning (no pruning operator exists)" (`:40-41`, PROPOSED reading). RB-P1 later tested an Eye trim. I found no owner word for it in these files.
3. **Report and whisper (2026-10-19, verbatim).** "WHY CAN'T THE EYE REPORT AND WHISPER BUT IF IT CAN'T DO BOTH THEN DEFINITELY WHISPER". Recorded as: whisper through the normal gate, "never a write" (`OWNER_APPROVALS_20261018.md:91-92`).
4. **Pairing (2026-10-15, verbatim).** The Eye is "INCHARGE OF PAIRING AND ROTATING THE BRAINS 7 DESIRES OR GRAVITIONAL WELLS WITH CAS FACULTIES" (`..._ACTING_20261015.md:81-85`). It learns from verifier verdicts only and never writes (`OWNER_APPROVALS_20261018.md:117`).
5. **Involuntary tier.** The owner's words are verbatim (`..._ACTING_20261015.md:55-57`). The rule that bounds it ("adds no new fact, learned value, recipe or capacity; restores a digest-verified prior state") is the dispatch session's PROPOSED reading (`:59-62`).
6. **2026-10-21 memory compaction.** "ALSO USE THE EYE IN THESE SITUATIONS, CORRECTLY APPLIED" is recorded as a statement of intent, not an approval (`OWNER_APPROVALS_20261018.md:235-236`).
7. **Claim limits, not owner rulings.** Eye acting is NOT LICENSED (spec:1460, 4094). "that the Eye may act outside tests" is NOT LICENSED (spec:2839).

## Facts relevant to "the Eye decides RPM depth"

- **What decides depth today is the cascade's decoupling-stop rule, not the Eye.**
  - The owner adopted it as primary ("YES YES VERY GOOD"), with HORIZON 12 kept only as a fuse (spec:2254, 2266).
  - The rule: "a child is skipped only if absorbed AND consolidated AND every face Peak; a binding child is always descended" (spec:2266).
  - Wave 3 result: `DECOUPLING_EARNED`, with 203 descents vs 609, and 64 good chains vs 60 (spec:2369-2371).
  - LM-T6's looser A8 stop read `DECOUPLING_STOPPED_EARLY`: 269 of 800 deep faults found vs 800 of 800 with full descent (spec:1519).
- **Depth limits.**
  - `HORIZON = 12` and `DESIRE_BOUND = 12` by owner ruling; "5 remains canon's own number" (`docs/working/noetic_council/OWNER_RULING_DEPTH_12_20261016.md:13-40`).
  - Faculty nesting cap: `MAX_NESTING_DEPTH = 5` (`faculties.py:85-86`, enforced at `faculties.py:619-627`).
- **What the Eye design says about depth.**
  - The Eye reads "depth n against 5" at S5 (`UNITY_EYE.md:124`).
  - For a SATURATION station: "recursing harder is not a fix", report only (`UNITY_EYE.md:139`).
  - Deep RPM descents are listed as "expensive decisions" for idle-time reflection (`..._ACTING_20261015.md:94-95`, PROPOSED).
- **Timing.** No Eye scan, whisper or faculty call is allowed during an awake turn in the scored waves: no awake scans (`PREREGISTRATION_R1W4.md:203`), and 0 faculty calls in conversation (spec:2795-2840).