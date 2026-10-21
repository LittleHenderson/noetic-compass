# U1b on 2026-10-21: the owner said "run U1b"; U1b had already run. What was checked instead, and what stands.

Plain English. Every number is exact and comes from the sealed files named. Nothing was re-run. No claim status moved.

## 1. What U1b is (from its own freeze file)

U1b is the retest of U1, the test of the Unity Eye *acting* on the recipe brain (whispering to it, and an involuntary
tier that may only restore verified state). U1 (section 7.38) was `INCONCLUSIVE`: its random-whisper control arm A5
repeated answers on clean dialogues, and the frozen rule counted any change on a clean dialogue as worse.

U1b keeps U1's design unchanged (the brain, the eye, the planted faults, the seven arms A0 to A6, every threshold, every
status word) and fixes only the instrument. The three fixes were chosen after reading U1's numbers and say so in the
freeze (`FROZEN.precode.json`, sha256 `a77758f41d5aaa01adbb12b674e62d549bff4d34955c394e93373313621e26b2`, written at
laptop clock 17:31 PDT on 2026-10-15, before any U1b code):

- (a) The control A5 is no longer bound by the clean-world gate G_CLEAN. Its clean-dialogue answer changes are reported
  as the mark `A5_CONTROL_COST`. Its validity check stays G_CONTROLS (it must find planted faults at chance).
- (b) On faulted worlds, "worse than no eye" is scored against the true answer key (what a correct, unbroken brain
  answers), not against A0's faulty or lucky answers. U1's old-style counts are reported beside it, unscored.
- (c) The work-queue runner runs from the first part, so a loaded laptop cannot trip the time guard.

Fresh worlds everywhere, because the rule changes came after U1's numbers: Task B draws 100 to 119 (calibration draw
200) and dialogue seeds 131, 137, 139 (calibration seed 149). Predictions were written before the build (builder:
`EYE_EARNED_KEEP` about 0.7, `CONCERT_EARNED_KEEP` about 0.7, `EYE_HARMFUL` about 0.15, `INCONCLUSIVE` about 0.1).

Status words, computed by `merge_u1.py` from counts only, in this order: `INCONCLUSIVE` (instrument problem) blocks all
others; `EYE_HARMFUL` (any eye arm answers worse than A0 on a clean world by G_CLEAN, or on a faulted world by the true
key) blocks the keep words; `EYE_EARNED_KEEP` = A4 fixes more than A6 and intervenes less on clean worlds and is never
worse than A0 and has 0 unverified writes; `CONCERT_EARNED_KEEP` = A4 intervenes less than A3 on clean worlds and
fixes at least as many; `CHECKLIST_SUFFICES` = A6 fixes at least as many as A4 with no more clean interventions.

Cost: 0 USD, laptop only (`LOCAL_CPU_ONCE on MSI`, 300 s cap per part, sockets blocked, no network, no AWS, no LLM call).

## 2. The run (2026-10-15 evening) and its reading

- Parts `U1B_MSI_P01` to `P21`, driver started 17:46:06 PDT, first part 17:48:09 PDT, last part ended 20:16:10 PDT.
  Part wall time summed 4,228.659 s. 1,544 planned worlds counted exactly once. 0 deadline hits. 0 throttle firings.
  18 of 18 code tests in every part. Source manifest sha256 `ecba90709b58b2294ecad6fe0e2e5bf8077ca072c6fddf526774417443271640` (121 files).
- Sign line, as composed by the builder-operator (its own evidence file says it "is not an owner signature and
  promotes no claim"): `APPROVE u1b, source ecba9070, LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.`
- Authorization of record: the coordinator's reading of the owner's words of about 5:10 PM PDT 2026-10-15
  ("why don't you know that if the test is fucked up that a retest is in order why don't you know that or if it's a
  trivial matter than say so") as the word to retest U1.
- Reading (`runs\MERGED_READING.json`, sha256 `d00189a185d5110d97fc815d7b77afd01775e0e6332ed93e51c063ba7aa41a88`):
  test verdict `READ`; status words `EYE_EARNED_KEEP` and `CONCERT_EARNED_KEEP`; `CHECKLIST_SUFFICES` false;
  0 of 39 hard gates failed.

| Arm | Faults fixed (of 148) | Clean-world interventions | Worse than no eye, true key (faulted, 8,852 keyed items) | Old A0 yardstick, unscored |
|---|---|---|---|---|
| A0 no eye | 0 | 0 | 0 | 0 |
| A1 report only | 0 | 0 (2,666 would-act records) | 0 | 0 |
| A2 whispers only | 60 | 1,410 | 0 | 149 |
| A3 one-way + autonomic | 148 | 2,610 | 0 | 259 |
| A4 concert | 148 | 1,816 | 0 | 259 |
| A5 random whispers (control) | 13 | 558 | 23 (all F_SEAM) | 70 |
| A6 checklist | 128 | 10,152 | 239 (all F_MISALIGNED) | 498 |

- Control: A5 named 2 planted faults; chance 1.3160; bound 4.6412 (G_CONTROLS holds). `A5_CONTROL_COST`: 25 changed
  turns across 22 clean dialogues (20 same-answer repeats, 5 other); 0 Task B answers worse.
- Concert: A4 answered 8,125 of 8,125 brain requests; A4 148 fixed = A3 148 with 794 fewer clean interventions.
- Recorded as spec sheet section 7.40 by PR #268 (commit 60321a14, 2026-10-16), carried in from staged edits.

## 3. What this session did on 2026-10-21 (0 USD, laptop, read-only on the sealed folder)

| Mark | Check | Result |
|---|---|---|
| 🟩 | Re-hash of all 121 files in `SOURCE_MANIFEST.json` | 121 equal, 0 changed, 0 missing |
| 🟩 | `FROZEN.precode.json` sha256 vs its record | equal (`a77758f4…`) |
| 🟩 | `runs\MERGED_READING.json` sha256 vs section 7.40 | equal (`d00189a1…`) |
| 🟩 | Frozen reader `merge_u1.py` replayed read-only on the sealed part outputs (`replay_u1b_reader.py`, output to the scratchpad; copy `MERGED_READING.replay.json`) | byte-identical to the sealed reading; `READ`; same two words; 0.654 s |
| 🟩 | First archive copies (none existed): `D:\tksCAS-archive\u1b_unity_eye_20261015\` (268 files, listing sha256 `1500a2e6…`) and `D:\tksCAS-archive\u1_unity_eye_20261015\` (277 files, listing sha256 `5c91617a…`) | three sha256 listing passes equal, each |
| 🔧 | Memory note of 2026-10-15 16:59 PDT ("U1b only on owner word"), written before the 17:31 PDT freeze | corrected |
| ⬜ | Hub change-log row of 2026-10-21 09:42 PDT cites section 7.38 only for the Eye's acting | noted; not edited |
| ⬜ | Re-run of U1b | not done; settled work is not re-run (spec sheet rule) |

## 4. What stands, and what is open

- `INCONCLUSIVE` for U1 (7.38), unchanged. `READ` with `EYE_EARNED_KEEP` and `CONCERT_EARNED_KEEP` for U1b (7.40),
  for that test only, ceiling `SYNTHETIC_ONLY`, unchanged. The Eye's ACTING stays `NOT LICENSED` (7.38). Later
  work imports U1b's `ConcertLedger` unchanged (7.73, 7.74, 7.76); the Eye's report-and-whisper words (7.77, 7.78)
  are separate results.
- Open, the owner's call, not the operator's: does the typed line of 2026-10-21 ("RUN the follow-up test called U1b",
  "run U1b") stand as the owner's after-the-fact word on the 2026-10-15 run, or does it ask for a fresh run on new
  seeds (a U1c: its own pre-code freeze, laptop, 0 USD expected, about 2.5 h of parts)?
