# DIAGNOSIS BRIEF FOR DEEPSEEK — HELM-R1 wave 7 "CHAT WAVE", job c51, and every failure of the 2026-10-20 session

Written 2026-10-20 (Pacific) by the coordinating agent (Claude) at the owner's order: "give DeepSeek a write-up of everything it will need
in order to diagnose the issues thoroughly and totally". You (DeepSeek) are being asked to **diagnose**, not to decide. Every code excerpt
below is verbatim from the sealed package or the operator kit. Every number is exact. Where I state a cause, I say how sure I am.

## 0. Rules you must respect while diagnosing

1. **Claim status comes only from a program reading, never from prose.** The frozen reader's words for job c51 are verdict `FAILURE`,
   status word `INCONCLUSIVE`. No analysis of yours or mine changes them. A failed hard gate is a FAILURE, never "a pass with caveats".
2. **The preregistration forbids re-reading sealed run data with a repaired reader** (`PREREGISTRATION_R1W7.md` line 4: "Every number
   below is frozen now; the frozen reader applies them; no one re-reads them after the data exists"). You may say what a repaired reader
   *would* compute, as analysis; it is never a result.
3. **Nobody opens the exam.** `x7_custody/out/exam/` (keys, samples, seeds, multipliers) is laptop-only, custodian-only. The builder and
   the operator never saw an item. Do not ask the owner to paste item text, keys or seeds.
4. **Only the owner's own typed words approve money or a re-run.** You may recommend; you may not say anything is approved.
5. **Owner's colour scale** (reading aid, never a claim status): ✅ confirmed win, 🟩 strong, 🟨 partial, 🟧 weak, 🟥 failed / withdrawn
   (kept in the record), ⬜ null / inconclusive / not run (distinct from a failure), 🔧 method or process win (not a result), 🔒 blocked on
   owner (not a result). Claim status is always one of: REAL / VALIDATED / LICENSED / NOT LICENSED / GREY / VACUOUS / WITHDRAWN /
   ENGINEERED-NOT-VALIDATED / FLAG_FOR_HUMAN_REVIEW. Never delete a negative.
6. Plain English for the owner. Define each term when first used.

## 1. Context in one page

**HELM** is a recipe-arithmetic "brain" plus a live loop and a chat window, all pure Python, no neural network in the answer path. It learns a
recipe from an English lesson ("We made 2 loaves from 4 cups flour and 1 cup water"), records stock ("We have 8 cups flour and 1 cup water"),
and answers "How many loaves can we make?" exactly, or asks when it cannot. Two brains exist: the licensed wave-1 brain (`helm_brain_canonical.py`,
byte-pinned to git commit `d4488f2a`) and the **wide brain** (`helm_brain_wide.py` + reader `helm_wide_turn.py`), which the owner ruled
canonical on 2026-10-20 and which is now ON by default (`HELM_WIDE_BRAIN` off only by `0`/`OFF`/`FALSE`/`NO`).

**Governance (how a result is produced).** A design is written and hashed before any code (preregistration). A builder writes a package: the
HELM code under test cut from one git commit (`helm_now/`), the exam generators, the unit runners, the host runner, and a **frozen reader**
(`r1w7/merge_r1w7.py`) that computes instrument rows, hard gates, marks and the one status word. The package is zipped and its sha256 is the
"seal". The owner signs a line (`CHAT WAVE at 1 USD`); a program writes the approval record binding the line to the zip. A **custodian** (a
separate agent) derives exam seeds from sha256(line + ":" + zip sha256), draws the exam from public frames and sealed generators, and ships a
**carrier** (inputs + pins only, no keys). An **operator** builds a payload (the zip + five neighbour zips + the carrier), places a ledger hold,
launches ONE AWS machine (m6i.xlarge, us-west-2) with a run-proven controller/worker kit, downloads the deliverable, terminates, proves cleanup
three ways, then runs the frozen reader on the laptop against the custodian's keys. Status words for wave 7, frozen order: 1 `INCONCLUSIVE`
(verdict not PASS), 2 `CHAT_WAVE_HARMED`, 3 `CHAT_WAVE_NO_GAIN`, 4 `CHAT_WAVE_EARNED_KEEP`. Verdict: `INSTRUMENT_ERROR` if any instrument
row false; else `FAILURE` if any hard gate false; else `PASS`.

**Wave 7 question** (preregistration §1): "When a person types to HELM's chat, with the canonical wide brain on, does HELM learn real recipes,
answer right, ask where it should, say it plainly, and stay unbroken by ordinary small talk, as well as the loop did when driven directly?"
Exams: X7_REAL (128 real recipes from the public frames, typed as lesson + stock + question), X7_CONV (64 templated dialogues, 13 families),
X7_NOISE (the same 64 with two of twelve frozen small-talk sentences inserted). Arms: CHAT_ON (under test), CHAT_OFF (`HELM_WIDE_BRAIN=0`),
CHAT_ON_REPLAY, CHAT_DIAG (voice bypassed), LOOP_ON (wave 6's harness, loop driven directly), ALWAYS_ASK. 14 host units.
Marks: NH-CHAT (≤ 2 lost vs LOOP_ON per exam), K1 (≥ ceil(0.9·D) fully learned), K3 (0 wrong answers, 0 wrong lessons), K4 (0 unexplained asks),
P PLAIN (RIGHT − RIGHT_AND_PLAIN ≤ 2), N NOISE (≤ 2 lost to noise, 0 misrouted scored turns). Hard gates HG1–HG10 (receipts, replay, key-blind,
no network, sandbox, no crash, voice changes no answer, switch hygiene, same inputs, chat never exits). Instrument rows I0, I1, I6, I7, I9, I10,
I12, I14.

**Where everything lives (Windows laptop):** package and run under `C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\`; the repository
`noetic-compass` (branch `claude/project-thread-pmbzd6`; record PR #418 from `claude/helm-r1w7-c51-result-20261020`); spec sheet
`docs/CAS_HARNESS_SPEC_SHEET.md` sections 7.98 (packet) and 7.101 (c51; first numbered 7.99, renumbered because another session took 7.99 and 7.100 the same hour); repo copies `docs/working/r1_wave7/`; backup
`D:\tksCAS-archive\r1_wave7_c51_20261020\` (162 files, three sha256 passes, tree `d4d8151f…`).

## 2. Timeline of the session, with every red square

| When (PDT) | What | Mark |
|---|---|---|
| afternoon | Wave 7 package v1 sealed on HELM cut `974fe36c`. The builder's PRACTICE run showed the chat as shipped would fail: the chat handed a sentence to the brain only when the OLD (licensed) reader recognised it; it said a third as "about 0.33"; it answered a recorded stock turn "That's outside what I know". | 🟥 found in practice |
| | FIX FIRST round 1 in HELM (PR #416 commit `1b0c6d62`): `helm_end_to_end_loop.wants_turn` consults the wide reader when the switch is on; `helm_chat._speak` says wide-path turns with the wide path's own sentence; `helm_voice.say_amount` says kitchen fractions exactly. Package resealed v2 (`7e7fa066…`). | 🔧 |
| | PRACTICE on v2: a kitchen sentence containing "run" ("...but we've run out of c-sugar") reached the loop's tool engine and a shell command ran (`python --version`); two question forms and a greeting prefix unread; "1 cup dry beans or whole peas" learned under a made-up name. | 🟥 found in practice |
| | FIX FIRST round 2 (PR #416 commit `dfc7158d`): no tool engine on kitchen sentences, whole-word keywords, wide reader claims the forms, "X or Y" binds X, "but we've run out of X" is a reader question. Package resealed v3 (zip `5063baba…`, freeze `2366e85d…`). 31 wave-7 tests OK, 201 HELM tests OK. Builder reported every mark met on practice. | 🔧 |
| evening | PR #416 and PR #417 merged into the thread branch; hub republished. | 🔧 |
| 7:41 PM | Owner typed `CHAT WAVE at 1 USD`. Approval record by program (`f28543bc…`). | 🔒 cleared |
| ~7:47 PM | Custodian (separate agent) sealed X7: 23 of 23 receiver checks true; handoff `3f216852…`; carrier `51eb15db…`. One flag: 3 REAL ids also sit in old X6/X6v3 CONV lists, which the contract excludes only from the conversation pool (no violation). | 🔧 |
| ~7:50 PM | Operator kit generation (`make_c51_kit.py`, text substitution from the run-proven c50 scripts) **refused four times** on leftover c50 names until four substitution passes were added. Then my hash fill **overwrote the controller's own worker-template token** (`'__PAYLOAD_SHA__'` on line 294 of `aws_control_c51.py`); caught by inspection, restored, worker fill simulated. First `launch 1` call **refused itself**: `WATCHDOG_NOT_READY` (the `watch` process must run first). No AWS call made by any of these. | 🟥 operator slips, 0 USD |
| 7:55 PM | **c51 attempt 1**: machine booted, payload verified (1,136 members, 0 bad), then the job supervisor refused the plan: `ValueError: PLAN_INVALID:r1w7_host_run:pythonpath`. 0 units started. Terminated, cleanup proven three ways. | 🟥 plumbing |
| 8:00 PM | Operator fix D-OP-C51-1 (job plan only: `pythonpath: ["HELM_R1_W7_20261020"]`), validated against the real supervisor on the laptop. **c51 attempt 2**: `SUPERVISOR_ALL_STAGES_PASS`; HELM suites 201 OK; wave-7 suites 31 OK; 14 of 14 units exit 0 in 15.89 s. Terminated, cleanup proven three ways. | 🔧 |
| 8:05 PM | Frozen reader on the laptop: instrument rows all true; **all six marks true**; 9 of 10 hard gates true; **HG5 false** → verdict `FAILURE`, word `INCONCLUSIVE`. Cause found by inspection after the reading: the reader demands a per-unit field the recorder-equality unit never writes. | 🟥 result |
| 8:10 PM | Closeout: 0.02 USD charged at list for both attempts; ledger 114.23 → 113.25 combined, 86.75 unreserved of 200. Spec 7.99, CHANGELOG, dictionary, hub, repo copies, backup. | 🔧 |

Earlier the same day, same operator pattern, for your pattern analysis: job c49 (another wave) needed its closeout script patched because it
asserted AWS still listed a terminated instance that had aged out; job c50's pre-written scripts carried the previous job's payload sha as
placeholders and had to be filled after the fact; an inline shell heredoc turned `\b` regex word boundaries into literal backspace bytes
(0x08) inside `helm_end_to_end_loop.py` (caught by the suites, fixed from a script file). c50 itself read `PASS` / `WIDE_WAVE_EARNED_KEEP`.

## 3. Failure dossiers

### F1 — Attempt 1: `PLAN_INVALID:r1w7_host_run:pythonpath` (plumbing; 0 units started)

**Symptom (host `supervisor.stderr.log`, verbatim):**
```
Traceback (most recent call last):
  File "/opt/helm-shared-r2/execution/job_supervisor.py", line 362, in <module>
    raise SystemExit(main())
  File "/opt/helm-shared-r2/execution/job_supervisor.py", line 321, in main
    validate_plan(plan)
  File "/opt/helm-shared-r2/execution/job_supervisor.py", line 134, in validate_plan
    need(isinstance(stage.get('pythonpath'), list) and stage['pythonpath']
  File "/opt/helm-shared-r2/execution/job_supervisor.py", line 116, in need
    raise ValueError('PLAN_INVALID:' + reason)
ValueError: PLAN_INVALID:r1w7_host_run:pythonpath
```
`worker.log`: `PHASE BOOT` → `input.zip: OK` → `PHASE UNPACK_AND_PIN` → `PAYLOAD_MEMBERS 1136 BAD 0` → `SLICE systemd_scope_2cpu_14G` →
`PHASE RUN_SUPERVISOR` → `SUPERVISOR_EXIT 1`. Deliverable 1,819 bytes (`a98b8140…`). Instance `i-05ec6cdce28860185`, 02:55:10Z–02:56:34Z.

**The sealed stage plan (`kit/STAGE_R1W7.json`, verbatim excerpt):**
```json
 "cwd": "HELM_R1_W7_20261020",
 "env": {},
 "layout_note": "... Every python process is `python -X utf8 -B -I` (isolated; no PYTHONPATH).",
 "limit": 3000,
 "name": "r1w7_host_run",
 "pythonpath": [],
 "required_outputs": ["r1w7_out/R1_W7_HOST.json", "r1w7_out/R1_W7_HOST.json.sha256"],
 "requires": [],
 "source": "r1w7",
 "type": "command"
```
**The supervisor's rule (`kit/job_supervisor.py`, byte copy sha256 `3b2337ca…`, run-proven on waves RB-W1T, X-REAL, 6; lines 134–135 and 179):**
```python
        need(isinstance(stage.get('pythonpath'), list) and stage['pythonpath']
             and all(isinstance(item, str) and item for item in stage['pythonpath']), name + ':pythonpath')
...
    environment['PYTHONPATH'] = os.pathsep.join(str((source_root / entry).resolve()) for entry in stage['pythonpath'])
```
and line 238: `command = [sys.executable, '-B', '-u', *arguments]` (the supervisor itself does NOT run the stage with `-I`; the runner's own
children are `python -X utf8 -B -I`, `kit/run_r1w7.py` line 237 and `r1w7/pool_w7.py` line 28).

**The package's own kit test pins the bad value (`tests_r1w7/test_kit_w7.py` lines 30–35):**
```python
    def test_plan_check_passes(self):
        pc = load("plan_check")
        stage = json.loads((KIT / "STAGE_R1W7.json").read_text(encoding="utf-8"))
        out = pc.check(stage, KIT / "run_r1w7.py")
        self.assertEqual(out["verdict"], "PASS", out["problems"])
        self.assertEqual(stage["pythonpath"], [])
```
`kit/plan_check.py` is also a byte copy (sha256 `84257a23…`) and it PASSES a stage with `pythonpath: []`, while `job_supervisor.validate_plan`
refuses it. **Open question for you:** why do the two byte-copied checkers disagree on this rule, and what else do they disagree on?

**Comparison with the run-proven wave 6 plan (job c50):** field sets identical; the only value differences besides names were
`pythonpath: ['HELM_R1_W6_20261019']` vs `[]`. The operator fix D-OP-C51-1 set `["HELM_R1_W7_20261020"]` in `execution/job_plan.json`
only (the sealed zip is byte-identical; payload `7268c6f1…` → `ed3072f5…`, 1,136 members both, only `execution/job_plan.json` and
`payload_inventory.json` differ). Validation before launch: `validate_plan(new plan) == True`; `validate_plan(attempt-1 plan)` raises
`PLAN_INVALID:r1w7_host_run:pythonpath`. Attempt 2 then passed every stage.

**My confidence in the cause: high.** Classification: builder defect in the sealed kit plan, plus a test that asserts the defect, plus the
builder's dry runs never executing the real supervisor. Status: worked around for c51 (D-OP-C51-1); NOT fixed in the sealed package.

### F2 — The result: HG5 (sandbox gate) false; verdict `FAILURE`; word `INCONCLUSIVE`

**The reading (`R1_W7_READING.json`, sha256 `8f2f76468fef11e4d755083d2581578e04466e0d028a92848c8019ad945a5d4d`):**
```
"failing_gates": ["HG5_sandbox"], "failing_instruments": [], "marks_missed": [], "verdict": "FAILURE", "status_word": "INCONCLUSIVE"
"HG5_sandbox": {
  "canonical_brain_equals_base": true,
  "helm_now_files_changed": {},
  "holds": false,
  "session_files_under_scratch": { 10 chat units ... all true },
  "wave1_tree_same": true }
```
Host `sandbox`: `{"start": "65795c8c05fb687c7206fa9a449861ef988fa8b6be6d7d4061914c36db3a33c5", "end": "65795c8c05fb687c7206fa9a449861ef988fa8b6be6d7d4061914c36db3a33c5"}`.

**The reader's code (`r1w7/merge_r1w7.py` lines 255–264, verbatim):**
```python
    sb = R.host.get("sandbox") or {}
    changed = {u: ((R.sm.get(u) or {}).get("unit") or {}).get("helm_now_files_changed") for u, *_x in C.unit_list()}
    sess = {u: ((R.sm.get(u) or {}).get("unit") or {}).get("session_files_under_scratch") for u, *_x in chat}
    canon = (inst.get("helm_cut") or {}).get("canonical_equals_base") is True and C.check_helm_cut()["canonical_equals_base"]
    g["HG5_sandbox"] = {"holds": bool(sb.get("start")) and sb.get("start") == sb.get("end") and canon and
                        all(v == [] for v in changed.values()) and all(v is True for v in sess.values()),
                        "wave1_tree_same": bool(sb.get("start")) and sb.get("start") == sb.get("end"),
                        "canonical_brain_equals_base": canon,
                        "helm_now_files_changed": {u: v for u, v in changed.items() if v},
                        "session_files_under_scratch": sess}
```
Note the display filter `{u: v ... if v}` hides a `None` value, so the reading shows `{}` while the test `v == []` is false for `None`.

**What each of the 14 host unit files actually holds (top-level fields, values only, no item text):**
```
W7_RECORDER_EQUALITY      helm_now_files_changed: null   session_files_under_scratch: null   helm_outside: []
W7_X7_CONV_CHAT_DIAG      []    true    []        W7_X7_CONV_CHAT_OFF   []  true  []      W7_X7_CONV_CHAT_ON  []  true  []
W7_X7_CONV_CHAT_ON_REPLAY []    true    []        W7_X7_CONV_LOOP_ON    []  null  []      W7_X7_NOISE_CHAT_OFF []  true  []
W7_X7_NOISE_CHAT_ON       []    true    []        W7_X7_REAL_ALWAYS_ASK []  null  []      W7_X7_REAL_CHAT_DIAG []  true  []
W7_X7_REAL_CHAT_OFF       []    true    []        W7_X7_REAL_CHAT_ON    []  true  []      W7_X7_REAL_CHAT_ON_REPLAY [] true []
W7_X7_REAL_LOOP_ON        []    null    []
```
`unit_list()` has 14 entries including `W7_RECORDER_EQUALITY`; `chat` (10 units) is used for `sess`, so the `null` of the loop arms does not
matter there. The recorder unit's `null` in `changed` makes `all(v == [] ...)` false.

**Who writes the field (`r1w7/chat_harness.py`):** chat arms, lines 299–307, write `"helm_now_files_changed": changed` and
`"session_files_under_scratch": all(...)`; loop arms, lines 337–341, write `"helm_now_files_changed": sorted(...)`. The recorder unit,
`run_recorder_equality` lines 352–396, returns
```python
    return {"schema": "helm.r1w7.recorder-equality/1", "exam": "RECORDER", "arm": "EQUALITY", "rows": rows,
            "items": len(rows), "all_equal": ok, "crashed": 0, "system_exit": 0, ...
```
with **no** `helm_now_files_changed`. `r1w7/units_w7.py` `cmd_recorder` (line 97) passes that dict through; the common wrapper at line 133 adds
`helm_cut_commit`, `unit_id`, `netguard`, `python`, `peak_memory_mib` etc., not the sandbox fields.

**Why no test caught it (`tests_r1w7/fixture_run.py` lines 257–261):** the synthetic recorder unit used by every reader test is
```python
        if uid == C.RECORDER_UNIT:
            units[uid] = {"schema": "helm.r1w7.recorder-equality/1", "exam": "RECORDER", "arm": "EQUALITY", "items": 3,
                          "all_equal": plant != "I12", "rows": [], "crashed": 0, "system_exit": 0, "items_sha256": "f" * 64,
                          "netguard": {"installed": True, "attempts": 0}, "wide_modules_imported": WIDE, "helm_outside": [],
                          "wide_env_after": None, "helm_now_files_changed": [], "seconds": 1.0, "synthetic_fixture": True}
```
i.e. the fixture gives the recorder the field the real unit lacks. `tests_r1w7/test_units_w7.py::test_every_hard_gate_can_fail` plants
`HG5` (start ≠ end) and `HG5b` (a changed file) and asserts `failing_gates == [gate]` and `verdict == "INSTRUMENT_ERROR"` ("the synthetic run
is never an instrument pass"). There is no test that the gate CAN HOLD on records shaped like the real units.

**Why the builder's practice run did not reveal it (`TEST_RECORD_R1W7.md` lines 50–51, verbatim):** "Reader: `INSTRUMENT_ERROR` /
`INCONCLUSIVE` as designed for a practice mock (I0, I1, I6, I7, I9, I10; HG5 only for want of host sandbox hashes)." The practice reading
(`dry_run/run5_v3_from_seal/R1_W7_READING_DRY.json`) shows `HG5_sandbox.holds: false` with `wave1_tree_same: false` and
`canonical_brain_equals_base: false`; the builder attributed the false to the missing host hashes and never isolated the recorder term.
The builder's summary line "marks met on practice: all six" was true of the marks and silent about the gates.

**My confidence in the cause: high** (the four other HG5 terms are all true in the reading; the fourteen unit records above are the complete
input to `changed`). Classification: builder defect in the frozen reader (or in the recorder unit's record), fixture–reality divergence,
and a test suite that asserted failures could be planted but never that the gate could pass. Status: NOT fixed (the package is sealed; a
v4 would be needed). The word `INCONCLUSIVE` stands.

**Open questions for you:** (a) Should HG5 read `helm_now_files_changed` only from units that run HELM (`chat` + loop arms), or should the
recorder unit write it? Which is the smaller, safer change to the sealed contract wording ("every unit records helm_now/ unchanged")?
(b) Are there OTHER gates or marks where the fixture supplies a field the real unit lacks, or vice versa? Compare the fixture dicts in
`fixture_run.py` (chat units lines ~270–283, loop units, recorder) field-by-field with the real unit outputs listed in
`unit_fields()` of `merge_r1w7.py` lines 124–128 and with the `R1_W7_READING.json` `reported.unit_fields` block (included below). (c) Does
`HG9_same_inputs`, `HG8_switch_hygiene` or `I12` have a similar `None`-vs-value trap?

### F3 — Operator kit slips (none reached AWS; recorded because they recur)

- **F3a** `make_c51_kit.py` (generates the c51 kit from the c50 `.orig` scripts by string substitution, then refuses if any of
  `c50, C50, r1w6v3, R1W6V3, FIX K4, PAIR WAVE, da1ec4d2, 4054cfd6, 19d6c42d, X6V3, x6v3` survives) refused four times: leftovers were the
  usage line, the shared-slot comment, `payload_c50` folder name, `ANOTHER_C50_INSTANCE_IS_LIVE`, the undated reservation name
  `r1w6v3_c50_reservation`, the console marker `'C50 '` in single quotes, `"c50 already used"`, `r1w6v3-c50-` ids, and docstrings. Fixed by
  adding substitution pairs. The same technique (text substitution of a run-proven kit) produced the c50 stale-placeholder incident.
- **F3b** The kit leaves `PAYLOAD_SHA = '__PAYLOAD_SHA__'` for later fill. My fill replaced **every** `__PAYLOAD_SHA__` in
  `aws_control_c51.py`, including the controller's own template substitution on line 294:
  `worker = (worker.replace('__JOB__', JOB).replace('__PAYLOAD_SHA__', PAYLOAD_SHA)`, which became
  `.replace('7268c6f1…', PAYLOAD_SHA)`. Had it launched, the worker's `PS='__PAYLOAD_SHA__'` would never have been filled and the host's
  `sha256sum -c` would have failed (a plumbing failure). Caught by reading the grep output before launch; restored; simulated the fill.
- **F3c** The controller's `launch` asserts `WATCH.read_bytes()` says `READY` (line 282), so `watch N` must be started first and left
  running. My first `launch 1` ran before any watch and raised `FileNotFoundError` on `aws-c51-a1-watch.json`. No AWS call. The c50 brief
  did not state this ordering. Logs kept as `launch_a1_refused_no_watchdog.*`.
- **F3d** Attempt 2 logged one `CONTROL_ERROR` at 03:00:24Z: `InvalidInstanceID.NotFound` on the first `DescribeInstances` right after
  `run_instances` (EC2 eventual consistency). The controller continued; all later steps succeeded. Not a failure; recorded.

### F4 — HELM chat defects found in PRACTICE before the paid run (fixed; PR #416)

Listed so you can judge whether the fixes are complete and whether they could interact with the exam results.
1. `helm_end_to_end_loop.wants_turn` consulted only the licensed reader; wide-readable lines never reached the wide brain through the chat
   (practice: 13 REAL items lost vs LOOP_ON; 8 unexplained asks). Fix: when `wide_on`, `helm_wide_turn.read_wide(...)["status"] != "NOT_MINE"`.
2. `helm_voice.say_amount` said "about 0.33" for a third. Fix: exact kitchen fractions (denominator ≤ 16), "about" otherwise.
3. The chat answered a recorded stock turn with "That's outside what I know" (110 of 110 in practice v1). Fix: `_speak` early return for
   `res["path"] == "wide"` using the wide path's own sentence through the voice guard.
4. "We have 6 C-peaches, sliced but we've run out of c-sugar." reached the loop's tool engine via the keyword "run" and `python --version`
   ran (practice v2, 4 tool-engine turns). Fix: whole-word keyword regex, `kitchen_talk` exclusion, no tool engine when the wide reader
   claims the sentence; test patches `subprocess.run` to fail on any call. On the exam: 0 tool-engine turns in every chat unit (D-W7-19).
5. Question forms "Could you tell me how much X that makes?" / "How much X do we have the makings of?" and a leading "Hi again." were unread;
   "1 cup dry beans or whole peas" bound a made-up name; "…but we've run out of X" was treated as stock. Fixed in `helm_wide_turn.py`.

### F5 — Open HELM negatives from the exam (facts; nothing licensed)

CHAT_ON on X7_CONV: 20 of 64 undetermined: S1_WISDOM_STATED 6 of 6, S2_POWER_STATED 6 of 6, S7_NOT_A_FACE 4 of 4, S6_TWO_FACES 2 of 2,
R4_WITNESS_IN_ENGLISH 2 of 4 (`CV23`, `CV25`). LOOP_ON shows the same families (22 undetermined), so this is HELM's wide path, not the chat.
In practice the same families were undetermined ("the wide path asks for stock it was just given"). CHAT_OFF (licensed brain alone):
REAL 0 right / 112 asks; CONV 30 right, 8 misrouted scored turns, 6 unrouted. REAL CHAT_ON: 96 right, 0 wrong, 16 asks (all explained by
K4's rule), 16 not scored (undetermined keys). Custodian flag: 3 of 128 REAL ids also in old X6/X6v3 CONV lists (contract excludes those
only from the conversation pool).

## 4. My pattern hypotheses (for you to confirm, refute or extend)

1. **Fixture–reality divergence.** Every reader test feeds synthetic unit dicts built in `fixture_run.py`; none feeds a real unit output.
   The recorder fixture carries a field the real unit lacks. The plan test asserts the empty list the supervisor refuses. Proposed check:
   a test that runs one REAL unit of each kind (chat, loop, recorder) on the practice fixture and asserts its keys ⊇ the keys the reader
   reads for every gate; and a test that feeds real practice unit files into the reader and asserts HG5 CAN hold when the host sandbox
   hashes are equal.
2. **Byte-copied tools applied to a new plan without executing them.** `job_supervisor.py` and `plan_check.py` are byte copies; the builder
   verified their hashes (`test_byte_copies`) but never ran `validate_plan` on the real `STAGE_R1W7.json`. `plan_check.py` accepted what
   `validate_plan` refused. Proposed check: the kit test calls `job_supervisor.validate_plan` on a plan built exactly as `build_payload`
   builds it.
3. **Kit generation by text substitution.** Each wave's operator kit is produced by substituting names in the previous wave's scripts and
   grepping for leftovers. Three incidents in two days (c50 placeholders, c51 four refusals, c51 template-token overwrite). Proposed:
   a parameterised kit (one values file, one template set) or at least a token scheme where fill-targets and template-targets differ.
4. **Masking by `INSTRUMENT_ERROR`.** The practice mock is designed to read `INSTRUMENT_ERROR`, so any gate that is wrongly false in
   practice is invisible behind the instrument verdict. Proposed: the dry run reports every gate's row individually and the builder's record
   must show each gate true (or explain each false term), not just the marks.
5. **Reports that say "all marks met" without "all gates hold".** The builder's TEST_RECORD and my packet section repeated "every mark met on
   practice"; the gates were never seen to hold on a real-shaped record. Proposed: the sealed record carries a line per gate.

## 5. What a thorough diagnosis should deliver

1. For F1 and F2: confirm or refute the stated causes from the excerpts; name every other place the same class of defect could exist in
   the wave-7 package (fields read by the reader vs fields written by the units; plan fields checked by `plan_check` vs `validate_plan`).
2. A field-by-field table: for each of the 14 units, the fields the reader reads (`unit_fields()` list + every `.get(...)` in
   `hard_gates`, `instrument_rows`, `marks`) against the fields the real unit writes (from `reported.unit_fields` below) and the fixture.
3. A v4 change list, minimal and contract-preserving: reader HG5 scope or recorder record; `STAGE_R1W7.json` `pythonpath`; the kit test;
   fixtures matched to real records; a dry-run gate-by-gate report. State which changes alter the preregistered contract wording and which
   do not (any contract change needs an amendment and the owner's word).
4. A judgement on whether anything in the exam numbers (section 6) suggests a HELM defect rather than an instrument defect — in particular
   the S1/S2/S6/S7 undetermined families and the 16 REAL asks — with the specific HELM code paths you would inspect (`helm_wide_turn.py`
   reader, `helm_chat.py` routing, `helm_end_to_end_loop.py` `_not_checked_turn`), and what free (0 USD) laptop experiment would settle each.
5. For the operator kit: a safer fill/template design and a launch checklist (watch first; fill only the constant line; simulate the worker
   fill; run `validate_plan`; verify the lease) that a future agent can follow without the c50/c51 history.
6. Say plainly what is and is not known. Mark hypotheses as hypotheses. Do not state any word other than `INCONCLUSIVE` for c51.

## 6. Evidence appendix

### 6.1 Reading summary (`R1_W7_READING.json` `8f2f7646…`)
- Instrument rows: `I0_not_a_practice_mock`, `I1_data_identity`, `I6_completeness`, `I7_reading_from_the_sealed_zip`, `I9_governance`,
  `I10_seed_rule`, `I12_recorder_transparent`, `I14_not_vacuous` — all true.
- Hard gates: HG1 receipts (0 problems) true; HG2 replay (REAL, CONV) true; HG3 key-blind (carrier = `INPUTS_CONV_X7.json`,
  `INPUTS_NOISE_X7.json`, `INPUTS_REAL_X7.json`, `X7_PINS.json`) true; HG4 no network (14 units, 0 attempts) true; **HG5 false**; HG6 no crash
  (0) true; HG7 voice changes no answer (REAL, CONV) true; HG8 switch hygiene (0 problems) true; HG9 same inputs (one sha256 per exam:
  REAL `60cfc44c…`, CONV `cf222764…`, NOISE `cfd6f9a3…`) true; HG10 chat never exits (0) true.
- Marks: `K1_LEARNS` fully_learned 95, need 88, of 97 → true; `K3_SAFE` 0/0/0/0 → true; `K4_HONEST` unexplained 0, not routed 0, unsettled 0 →
  true; `NH_CHAT` REAL CHAT_ON 96 vs LOOP_ON 94 (lost 0, gained `RW:pg:65061@224840`, `RW:pg:69364@87584`), CONV 44 vs 42 (lost 0, gained
  `CV30:pg:48695@36383`, `CV31:pg:65061@749282`) → true; `P_PLAIN` REAL 96 = 96, CONV 44 = 44 → true; `N_NOISE` lost 0, misrouted 0, 128 noise
  turns, 0 CAS tokens in noise replies → true.
- Totals CHAT_ON: X7_REAL items 128: RIGHT 96, WRONG 0, ASKS 16, NOT_SCORED 16 (undetermined keys 16, same-name 7), RIGHT_AND_PLAIN 96,
  fully learned 95 of 97. X7_CONV 64: RIGHT 44, WRONG 0, UNDETERMINED 20, RIGHT_AND_PLAIN 44, misrouted 0, not routed 0. X7_NOISE 64: RIGHT
  44, WRONG 0, UNDETERMINED 20, noise turns 128, misrouted 0. CHAT_DIAG and CHAT_ON_REPLAY identical to CHAT_ON on every scored answer.
- CHAT_OFF: REAL RIGHT 0 / ASKS 112 / lessons NOT_LEARNED 662 / plain 128; CONV RIGHT 30, UNDETERMINED 34, misrouted scored turns 8, not
  routed 6; NOISE RIGHT 30. LOOP_ON: REAL RIGHT 94 (fully learned 93), CONV RIGHT 42, UNDETERMINED 22. ALWAYS_ASK present.
- Stock turns (REAL, CHAT_ON): STOCK_RECORDED 107, CLARIFY_ENGLISH_UNKNOWN_INGREDIENT 14, CLARIFY_NOT_CCE 3,
  CLARIFY_ENGLISH_NO_INGREDIENT_NAMED 2, INVENTORY_RECORDED 2; "recorded but reply says don't know" 0. CHAT_OFF: CLARIFY_ENGLISH_UNKNOWN_INGREDIENT
  106, CLARIFY_ENGLISH_NO_INGREDIENT_NAMED 12, NOT_ROUTED:GENERAL_KNOWLEDGE_INQUIRY 6, NOT_ROUTED:USER_AFFECT 1, CLARIFY_STOCK_NOT_RECORDED 1,
  INVENTORY_RECORDED 2.
- Noise intents by sentence (CHAT_ON): 1 GENERAL_CONVERSATION 8; 2 USER_NARRATIVE 15; 3 USER_PREFERENCE 15; 4 USER_AFFECT 11; 5 CREATIVE_HUMOR 8;
  6 USER_KNOWLEDGE_QUERY 8; 7 SESSION_SUMMARY 13; 8 USER_AFFECT 7; 9 GENERAL_KNOWLEDGE_INQUIRY 10; 10 GENERAL_CONVERSATION 13;
  11 QUERY_MEMORY_RECALL 8; 12 USER_AFFECT 12. Misrouted noise 0.
- Recorder (I12): 6 dialogues, all rows `two_wrapped_runs_byte_identical`, `wrapped_equals_unwrapped_memory`, `stored_copies_equal_returned`,
  `wrapped_restored` true; `all_equal` true.
- `reported.unit_fields` (per unit, the fields the reader lifts): `seconds, seconds_process, netguard, wide_modules_imported, helm_outside,
  wide_env, wide_env_after, helm_now_files_changed, scratch_files, agentic_tool_turns, session_files_under_scratch, peak_memory_mib, python,
  helm_cut_commit, restored, audit, unsettled_fired`. For `W7_RECORDER_EQUALITY`: `helm_now_files_changed: null`, `session_files_under_scratch:
  null`, `scratch_files: null`, `agentic_tool_turns: null`, `wide_modules_imported: ["helm_brain_wide", "helm_wide_turn"]`, `peak_memory_mib 30.9`,
  `python 3.12.3`.
- Claim ceiling now `SYNTHETIC_ONLY` (unchanged); if earned would have been `NAMED_CORPORA_ONLY (the real recipes) + SYNTHETIC_ONLY`.

### 6.2 Host record (attempt 2)
`R1_W7_HOST.json` `525156dc…`; `RUN_RECORD.json` `4cd0184d…`: suites helm Ran 201 OK (skipped 2), w7 Ran 31 OK (skipped 1); `w1_tree_sha256_start`
= `w1_tree_sha256_end` = `65795c8c…`; neighbour freezes w1 `8c55c413…` (110 members), w3 `bd06f324…` (205), w3b `a6d9dbc7…` (27), w6 `da1ec4d2…`
(194), all 0 bad; `x7_pins_sha256` `464b6596…`, `x7_pins_practice_flag` false. Completeness: planned 14, exit_0 14, deadline_hit false, elapsed
15.89 s. Unit seconds: RECORDER 0.82, CONV_CHAT_DIAG 1.57, CONV_CHAT_OFF 1.32, CONV_CHAT_ON 1.97, CONV_CHAT_ON_REPLAY 1.97, CONV_LOOP_ON 1.52,
NOISE_CHAT_OFF 1.42, NOISE_CHAT_ON 2.02, REAL_ALWAYS_ASK 0.46, REAL_CHAT_DIAG 3.22, REAL_CHAT_OFF 2.57, REAL_CHAT_ON 4.32, REAL_CHAT_ON_REPLAY 4.32,
REAL_LOOP_ON 3.97. Host: Ubuntu 24.04.5, Python 3.12.3, 4 vCPU, 15,701 MiB, slice `systemd_scope_2cpu_14G`.

### 6.3 Custodian (handoff `X7_SEALED_20261021T024717Z.json` `3f216852…`)
`MANIFEST_X7.json` `0fc90b02…`; `RECEIVER_CHECK_X7.json` `78ab76c2…` (23 rows true, `bad_files: []`, `practice: false`); carrier `X7_CARRIER_V1.zip`
`51eb15db…`. X7_REAL: 128 items, answer keys 112, representable-and-answer-keyed 97 (floor 16), undetermined keys 16 (same-name 7), by cell
C23 14/14/14, C46 15/14/14, C710 15/14/14; excluded ids applied 1,021 (removed by id 998, by text 53). X7_CONV: 64, families R1 14, R2 4, R3 4,
R4 4, R5 4, R7 2, S1 6, S2 6, S3 6, S4 4, S5 4, S6 2, S7 4; expected keys ANSWER 30 / ASK 30 / LEARN 4; pool eligible 3,204, excluded 1,402.
X7_NOISE: 64, 128 noise turns, positions between_stock_and_question 54 / after_first_scored_turn 10, all 12 sentences used. Overlap: REAL vs
the contract's REAL exclusions 0; CONV vs everything 0; REAL vs all 14 lists 3 (2 in `x6_conv`, 1 in `x6v3_conv`; contract applies those
lists to the conversation pool only).

### 6.4 Approval, package, money
Owner line `CHAT WAVE at 1 USD` (18 bytes, sha256 `61c398c192226bc57eb46714f74fd4c0f6a018b6b3b9992d1f8533ad6bfa40ad`), recorded 2026-10-20
7:41 PM Pacific; `APPROVAL_RECORD_R1W7.json` `f28543bc…`; seed source `767f2f72…`. Package v3 zip `5063baba8be9ba807e7905d5f86732cb1a535ff5a533e67c79f5cbe16edbc6a9`,
freeze `2366e85d7a3b73fa0c6cefb94715aa7ba9cfeb6f3b384c4c0ad88d5ed0165da2`, HELM cut `dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6`; v1 `5107b9c6…`
and v2 `7e7fa066…` void. Payloads `7268c6f1…` (a1) and `ed3072f5…` (a2). Charge 0.02 USD list (a1 107.262583 s → 0.006 raw → 0.01; a2 160.151385 s →
0.008959 → 0.01); cautious 0.05; hold 1.00 consumed; ledger 114.23 → 113.25 combined, 86.75 unreserved of 200; `CLEANUP_PROOF_R1W7_C51.json`
`12ce9208…`; addendum `BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_R1W7_C51_20261021T030608Z.json` `8554484f…`. Cleanup a1: controller `1a608ab7…`,
independent `9d37ff53…`, direct `7cd0d712…`; a2: `3c3f3ab0…`, `fe585f97…`, `ddd59e0c…`. `RETRY_DECISION_C51.json` `c44d9817…`;
`OPERATOR_I_CHECKS_C51.json` `80939df4…` (all true, 194 freeze members).

### 6.5 Files you may ask the owner to paste (never the exam folder or any `KEYS_*` file)
`HELM_R1_W7_20261020/r1w7/merge_r1w7.py`, `r1w7/chat_harness.py`, `r1w7/units_w7.py`, `r1w7/common_w7.py`, `r1w7/summary_w7.py`,
`kit/STAGE_R1W7.json`, `kit/run_r1w7.py`, `kit/job_supervisor.py`, `kit/plan_check.py`, `tests_r1w7/fixture_run.py`, `tests_r1w7/test_units_w7.py`,
`tests_r1w7/test_kit_w7.py`, `PREREGISTRATION_R1W7.md`, `TEST_RECORD_R1W7.md`; run folder `run_c51_r1w7_20261020/R1_W7_READING.json`,
`deliverable_unpacked_a2/results/r1w7_host_run/out/RUN_RECORD.json`, `.../r1w7_out/R1_W7_HOST.json`, `job_record/RETRY_DECISION_C51.json`,
`job_record/make_c51_kit.py` (in `r1_wave7/`), `job_record/aws_control_c51.py`; HELM: `helm_chat.py`, `helm_end_to_end_loop.py`,
`helm_wide_turn.py`, `helm_brain_wide.py`, `helm_voice.py`, `test_helm_wide_alongside.py`. The 14 unit files under `r1w7_out/` contain exam
item text and must NOT be pasted; their top-level fields (section 3, F2) are already listed here.
