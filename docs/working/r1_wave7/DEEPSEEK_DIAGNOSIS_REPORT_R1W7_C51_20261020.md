# DIAGNOSIS — HELM-R1 wave 7 "CHAT WAVE", job c51, session 2026-10-20

Written 2026-10-20 (Pacific) by DeepSeek, answering `DEEPSEEK_DIAGNOSIS_BRIEF_HELM_WAVE7_C51_20261020.md`.
**This is a diagnosis, not a decision, and not a result.** Every claim below is labelled:

- **MEASURED** — I ran a program and read its output.
- **INFERRED** — I reasoned from what I read; I did not run it.
- **NOT KNOWN** — I could not settle it.

The c51 status word stays `INCONCLUSIVE`. Verdict stays `FAILURE`. Nothing here changes either, and nothing
here is a licence, a pass, or a promotion. No exam item text, no key file and no seed was read: the exam folder
`x7_custody/out/exam/` was never opened, and every experiment used sentences I invented.

---

## 0. What I did

I worked on the laptop, read-only apart from my own scratch files. I read the sealed package's own source
(194 freeze members), the sealed stage plan, both checkers, the frozen reader, the reader's fixtures and tests,
the recorded run records of attempt 2, and the HELM code under test. I ran seven small probe programs, all
listed in section 9 with the exact command.

Three things I verified before relying on them:

| Item | Value | How |
|---|---|---|
| The reading I diagnose | `R1_W7_READING.json` sha256 `8f2f76468fef11e4d755083d2581578e04466e0d028a92848c8019ad945a5d4d` | recomputed from disk; matches the sidecar and the brief |
| The package | `PACKAGE_FREEZE.json` sha256 `2366e85d7a3b73fa0c6cefb94715aa7ba9cfeb6f3b384c4c0ad88d5ed0165da2` | recomputed; matches brief |
| The frozen reader actually running | `r1w7/merge_r1w7.py` sha256 `975ccd6f0d84cf7278f1ebea67fd72e00e1844bc2f3d0f545fd50da602f6a7ae` | recomputed; **equals the pin inside the freeze** |

That last line matters for everything in section 2: the code I re-ran is byte-for-byte the sealed code, not a
transcription of it.

---

## 1. F1 — `PLAN_INVALID:r1w7_host_run:pythonpath`

### 1.1 The stated cause is correct. **MEASURED.**

I ran both sealed checkers against the sealed stage plan, unmodified:

```
kit/plan_check.py on kit/STAGE_R1W7.json  ->  {"verdict": "PASS", "problems": []}
job_supervisor.validate_plan, pythonpath=[]                        -> ValueError: PLAN_INVALID:r1w7_host_run:pythonpath
job_supervisor.validate_plan, pythonpath=['HELM_R1_W7_20261020']   -> True
```

So: one field, one value, and the operator's fix D-OP-C51-1 is exactly right. With that one value changed the
whole plan passes `validate_plan` — which also proves no **other** field of the sealed stage is wrong. That
answers a question the brief left open: `pythonpath` is the only bad plan field.

### 1.2 Why the two checkers "disagree": they never tested the same thing. **MEASURED.**

The brief calls `plan_check.py` and `job_supervisor.py` "byte-copied checkers" that disagree. They are not two
copies of one rule, and they cannot disagree, because their scopes do not overlap at all:

- `plan_check.check()` reads **only** `stage["required_outputs"]` and compares it with three constants it lifts
  out of the runner's source (`KEPT_SUBDIR`, `KEPT_SUFFIXES`, `DECLARED_OUTPUTS`). Its whole purpose is the old
  c34-g defect: outputs declared at a path the runner does not use. It contains no rule about `pythonpath`, or
  about `cwd`, `env`, `limit`, `name`, `source`, `requires`, or anything else.
- `validate_plan()` reads `job`, `scope`, `guard_names`, and per stage `name`, `type`, `source`, `limit`,
  `pythonpath`, `cwd`, `env`, `requires`, `requires_ran`, `argv`, `required_outputs`, `expected_tests`,
  `expected_skips`, `gate_file`, `preflight_modules`.

The only field both of them look at is `required_outputs`. So the "PASS" from `plan_check` was never evidence
about `pythonpath`. The two byte-copies agree on their one shared field.

### 1.3 The real defect is narrower and worse than "a test asserts the defect". **MEASURED.**

`tests_r1w7/test_kit_w7.py::test_plan_check_passes` does two things:

```python
out = pc.check(stage, KIT / "run_r1w7.py")
self.assertEqual(out["verdict"], "PASS", out["problems"])
self.assertEqual(stage["pythonpath"], [])          # <- line 35: the bad value is pinned by a test
```

Line 35 asserts the empty list is correct. So this test would have *failed* if someone had corrected the plan.
It is not a test that misses a defect; it is a test that forbids the fix.

And **nothing in the whole package ever calls `validate_plan`**. I grepped every `.py` in `r1w7/`, `tests_r1w7/`
and `kit/`: `validate_plan` appears only where it is defined (`kit/job_supervisor.py` line 112) and where the
supervisor calls it (line 321). `kit/job_supervisor.py` is pinned by hash (`3b2337ca75b1…`) and never executed.
The builder verified the tool's bytes and never ran the tool.

### 1.4 Where else this same class can exist. **MEASURED.**

I checked every place that turns a sealed template into a launched plan:

1. `make_c51_kit.py` — derives the operator kit from the previous wave's scripts. It refuses leftovers of old
   wave names (line 136–138) but knows nothing about the stage plan.
2. `build_payload_c51.py` — reassembles the stage plan into `execution/job_plan.json`. The attempt-1 version
   (`build_payload_c51.py.a1.orig`) contains **no** occurrence of `pythonpath` and **no** call to
   `validate_plan`; it only asserted `sha256(job_supervisor.py) == 3b2337ca…`. The current version contains the
   D-OP-C51-1 patch but **still no call to `validate_plan`**. This is the exact point where one line would have
   caught the whole failure before any money was spent:

   ```python
   from job_supervisor import validate_plan      # the same bytes the host will run
   validate_plan(plan)                           # refuses the plan on the laptop, 0 USD
   ```

3. The stage plan also carries a **second** fill-target of the same class that neither checker validates:
   `"--expected-freeze-sha256": "<PACKAGE_FREEZE sha256 named in APPROVAL_RECORD_R1W7.json>"`. It is not a `{…}`
   placeholder, so `validate_plan` accepts it; if the operator had forgotten to fill it, `run_r1w7.py` would
   have refused on the host (`R1W7_FREEZE_IS_NOT_THE_APPROVED_ONE`, exit 7) and burned a boot. It was filled
   correctly (`2366e85d…`), but nothing checked that it was.
4. `execution/job_plan.json` is **not** a member of the 194-member package freeze — I checked. So the
   operator's payload-side fix does **not** alter the sealed package: attempt 2 ran the approved freeze. That is
   the load-bearing fact that keeps attempt 2 legitimate. `kit/STAGE_R1W7.json` **is** a freeze member, so the
   bad `pythonpath` value is inside the seal and stays there until a v4.

---

## 2. F2 — HG5 false → `FAILURE` → `INCONCLUSIVE`

### 2.1 The stated cause is correct, and it is exactly one field on one unit. **MEASURED.**

I rebuilt `HG5_sandbox` by calling the sealed reader's **own** `hard_gates()` on the **real** attempt-2 unit
files, using the sealed reader's own `unit_fields()`. It reproduces the reading's HG5 block exactly
(`holds: false`, `helm_now_files_changed: {}`, all ten `session_files_under_scratch: true`,
`wave1_tree_same: true`, `canonical_brain_equals_base: true`). Decomposed in the sealed expression's own order:

| # | Term of `HG5_sandbox.holds` | Value |
|---|---|---|
| 1 | `bool(host.sandbox.start)` | `True` |
| 2 | `start == end` (both `65795c8c05fb687c7206fa9a449861ef988fa8b6be6d7d4061914c36db3a33c5`) | `True` |
| 3 | `canon` (host `helm_cut.canonical_equals_base` AND the laptop `check_helm_cut()`) | `True` |
| 4 | `all(v == [] for v in changed.values())` | **`False`** — refusing unit: `{"W7_RECORDER_EQUALITY": null}` |
| 5 | `all(v is True for v in sess.values())` (10 chat units) | `True` |

Thirteen of the fourteen units write `helm_now_files_changed: []`. `W7_RECORDER_EQUALITY` does not write the
key at all. `unit_fields()` uses `d.get(k)`, so the missing key becomes `None`, and `None == []` is `False`.
That one `False` is the entire verdict.

Counterfactual, run through the same sealed function (**analysis, not a result**): with the recorder's entry set
to `[]` and nothing else touched, `HG5_sandbox.holds` becomes `True`.

### 2.2 The display hid it, and that is a separate defect. **MEASURED.**

The reader builds the reported block with a filter:

```python
"helm_now_files_changed": {u: v for u, v in changed.items() if v},
```

`[]` and `None` are both falsy, so **both** the healthy value and the missing value render as an empty dict. The
gate that failed on a missing value displayed exactly what a gate that passed displays. This is independent of
which repair is chosen and should be fixed in any v4 reader:

```python
"helm_now_files_changed": {u: v for u, v in changed.items() if v != []},
```

### 2.3 The practice run was not silent — the explanation was incomplete. **MEASURED.**

The brief's hypothesis 4 says the practice run masked this behind `INSTRUMENT_ERROR`. That is not quite what
happened. `dry_run/run5_v3_from_seal/DRY_RUN_SUMMARY.json` carries `"failing_gates": ["HG5_sandbox"]` — the gate
was named. What happened is subtler and more instructive:

1. In practice, `HG5_sandbox` had **three** false terms, not one: `wave1_tree_same: false` and
   `canonical_brain_equals_base: false` (no host hashes on a laptop practice run) **and** the recorder term.
2. The builder's record explained the gate as "HG5 only for want of host sandbox hashes"
   (`TEST_RECORD_R1W7.md`). Two false terms were enough to explain, so nobody decomposed the gate into its five
   terms.
3. The display filter (2.2) rendered the third term as absent — the same as healthy.

The practice unit file `dry_run/run5_v3_from_seal/units/W7_RECORDER_EQUALITY.json` has **no**
`helm_now_files_changed` key either. **The exact defect that killed c51 was present, and visible, in the free
practice run.** Had the gate been reported as five named terms instead of one boolean, it would have been caught
before the seal.

### 2.4 Why no test caught it, precisely. **MEASURED.**

`tests_r1w7/fixture_run.py` line 261 gives the synthetic recorder unit `"helm_now_files_changed": []` — the field
the real recorder unit does not write. The clean fixture therefore passes the gate term the real record fails.

Two tests are close to the gap but neither closes it:

- `test_chat_on_learns_answers_and_records_transparently` (line 309) asserts
  `out["helm_now_files_changed"] == []` on a **real** chat unit run in-process. The chat arm is tested against
  reality. The recorder arm is not.
- `test_recorder_equality_on_practice_turns` (line 347) calls `H.run_recorder_equality` directly and asserts only
  `all_equal` and `items`. It never inspects the record's top-level fields, and it never goes through
  `units_w7.py cmd_recorder`, which is the path the host uses.
- `test_every_hard_gate_can_fail` (line 236) asserts `failing_gates == [gate]` for 14 planted failures. That
  proves each gate *can* fail. No test asserts that HG5 *can hold* on records shaped like the real ones. That is
  the asymmetry: failures were tested, passes were assumed.

### 2.5 Field-by-field table: what the reader reads vs what the real record and the fixture write. **MEASURED.**

Built by running `fixture_run.make_run()` into a temp folder and comparing its unit dicts with the 14 real
attempt-2 unit files. `R:` = real, `F:` = fixture, `n/N` = present in n of N records of that class.

| field the reader reads | always_ask | chat | loop | recorder |
|---|---|---|---|---|
| `seconds` | R:1/1 F:1/1 | R:10/10 F:10/10 | R:2/2 F:2/2 | R:1/1 F:1/1 |
| `seconds_process` | R:1/1 F:0/1 | R:10/10 F:0/10 | R:2/2 F:0/2 | R:1/1 F:0/1 |
| `netguard` | R:1/1 F:1/1 | R:10/10 F:10/10 | R:2/2 F:2/2 | R:1/1 F:1/1 |
| `wide_modules_imported` | R:1/1 F:1/1 | R:10/10 F:10/10 | R:2/2 F:2/2 | R:1/1 F:1/1 |
| `helm_outside` | R:1/1 F:1/1 | R:10/10 F:10/10 | R:2/2 F:2/2 | R:1/1 F:1/1 |
| `wide_env` | R:1/1 F:0/1 | R:10/10 F:0/10 | R:2/2 F:0/2 | R:1/1 F:0/1 |
| `wide_env_after` | R:1/1 F:1/1 | R:10/10 F:10/10 | R:2/2 F:2/2 | R:1/1 F:1/1 |
| **`helm_now_files_changed`** | R:1/1 ( `[]` ) F:1/1 ( `[]` ) | R:10/10 ( `[]` ) F:10/10 ( `[]` ) | R:2/2 ( `[]` ) F:2/2 ( `[]` ) | **R:0/1 (absent)  F:1/1 ( `[]` )** |
| `scratch_files` | R:0/1 F:0/1 | R:10/10 F:0/10 | R:0/2 F:0/2 | R:0/1 F:0/1 |
| `agentic_tool_turns` | R:0/1 F:0/1 | R:10/10 F:0/10 | R:0/2 F:0/2 | R:0/1 F:0/1 |
| **`session_files_under_scratch`** | R:0/1 F:1/1 | R:10/10 F:10/10 | R:0/2 F:2/2 | R:0/1 F:0/1 |
| `peak_memory_mib` | R:1/1 F:0/1 | R:10/10 F:0/10 | R:2/2 F:0/2 | R:1/1 F:0/1 |
| `python` | R:1/1 F:0/1 | R:10/10 F:0/10 | R:2/2 F:0/2 | R:1/1 F:0/1 |
| `helm_cut_commit` | R:1/1 F:0/1 | R:10/10 F:0/10 | R:2/2 F:0/2 | R:1/1 F:0/1 |
| `restored` | R:1/1 F:0/1 | R:0/10 F:0/10 | R:2/2 F:0/2 | R:0/1 F:0/1 |
| `audit` | R:0/1 F:0/1 | R:0/10 F:0/10 | R:2/2 F:0/2 | R:0/1 F:0/1 |
| `unsettled_fired` | R:1/1 F:0/1 | R:0/10 F:0/10 | R:2/2 F:0/2 | R:0/1 F:0/1 |

Two divergences, one live and one dormant:

- **Live (`helm_now_files_changed` on the recorder):** fixture writes it, reality does not. This is HG5.
- **Dormant (`session_files_under_scratch` on the loop and always_ask units):** fixture writes `True`, reality
  does not. Harmless today only because the reader builds `sess` from chat arms alone. If anyone widened that
  set to "all units", the fixture would keep passing while real records would fail — the identical trap, one
  edit away.

The fixture's *missing* fields (`seconds_process`, `scratch_files`, `agentic_tool_turns`, `peak_memory_mib`,
`python`, `helm_cut_commit`, `restored`, `audit`, `unsettled_fired`, `wide_env`) are read by no gate and no mark.
They reach the output only through `reported.unit_fields`. That is safe.

### 2.6 Answers to the brief's three HG5 questions.

**(a) Reader scope or recorder record?**

The preregistration already decides this. `PREREGISTRATION_R1W7.md` line 265 says the unit records
`helm_now_files_changed`, "**must be empty: HG5**", and line 114–115 defines HG5 as "the wave-1 brain folder
hashes the same at host start and end; `helm_now/helm_brain_canonical.py` equals its pinned base bytes; every file the chat
wrote lies under the unit's scratch". The reader's `all(v == [] for v in changed.values())` over all fourteen
units is a faithful implementation of "every unit records it empty". **The reader is not wrong. The recorder
unit's record is incomplete.**

So the smaller and safer change is **the recorder's record, not the reader's gate**:

- Making the reader read `changed` from "units that run HELM" does **not** exclude the recorder — the recorder
  constructs three `HELMConversationalSession` objects and calls `handle_turn` on each, so it runs HELM exactly
  as the chat arms do. Excluding it would exempt the one unit most likely to write a file, because it builds
  three sessions per dialogue.
- Restricting the term to chat and loop arms only would **weaken a hard gate** and would need a contract
  amendment and the owner's word.
- Treating a missing field as a refusal (a third option) is the honest reading of the current contract and would
  keep c51 at `FAILURE` — because the fact genuinely was not recorded.

Recommended: `run_recorder_equality` (or `cmd_recorder`) takes the same before/after `tree_listing(ns.helm_now)`
that `run_chat_unit` already takes, and writes `helm_now_files_changed` with the same meaning. Four lines, same
helper, no threshold, no mark, no gate, no word changes. The contract wording does not change; the record starts
matching it.

**(b) Other gates or marks fed a field the real unit lacks?**

No. I enumerated every string key the reader passes to `.get()` inside `instrument_rows`, `hard_gates`, `marks`,
`every_item`, `arm_summary` and `recorder_summary`, and checked each against the real records. The gate-bearing
unit fields are `netguard`, `wide_modules_imported`, `helm_outside`, `wide_env_after`,
`helm_now_files_changed`, `session_files_under_scratch`, `items_sha256`, `crashed`, `system_exit`, `items`,
`present`, `receipt_problems`, `receipt_inconsistent_turns`. All present on every record that needs them, with
the single HG5 exception above. Marks read only scorer totals (`RIGHT`, `WRONG`, `RIGHT_AND_PLAIN`,
`fully_learned_rep`, `lessons_WRONG`, `rep_answer`, `unexplained_asks_strict`, `misrouted_scored_turns`,
`not_routed_scored_turns`) and have no unit-field dependency. The one dormant case is
`session_files_under_scratch` (2.5).

**(c) The same `None`-vs-value trap in `HG9_same_inputs`, `HG8_switch_hygiene` or `I12`?**

- `HG9`: no. It requires `len(v) == 1 and None not in v` — the `None` case is explicitly refused in the
  expression. All 14 real records carry `items_sha256`; the recorder is excluded from the arm list by
  construction, so its `items_sha256 = fixture_sha256` can never leak in. The reading's `HG9` is `true`.
- `HG8`: no trap in the current data, but it has a **shape** fragility worth naming. It requires
  `imported == set(C.WIDE_MODULES)` for a wide unit, so `wide_modules_imported` must be exactly
  `["helm_brain_wide", "helm_wide_turn"]` — a list, and equality with a set. If a future HELM import added a
  third wide module, `HG8` would go false for a reason unrelated to switch hygiene. The recorder is treated as
  `wide = True` by a hardcoded special case, which is correct today and undocumented in the contract.
- `I12`: no. It reads `present`, `all_equal`, `items`, and the host's per-unit `exit`; all four are present and
  true, and `all_equal` is `True`, not truthy-string.

---

## 3. The one class that covers both F1 and F2

Both failures are the same mistake in two costumes:

> **A checkable fact was asserted in one place and never exercised in the other.**
> F1: the supervisor's rule was known, hash-pinned, and never executed on the plan.
> F2: the requirement "every unit records it empty" was asserted of the fixture and never of a real record.

The fix is the same in both: **run the checker against the real artefact, once, for free, before the seal.**

---

## 4. Is anything in the exam numbers a HELM defect rather than an instrument defect?

Short answer: **the undetermined families are a real HELM capability gap, not an instrument defect — and the
scoring has a blind spot that turns one behaviour into both wins and losses.** The 16 REAL asks are principled
refusals, not a defect. Evidence below.

### 4.1 CONV: all 32 clause-bearing items record the identical outcome. **MEASURED.**

X7_CONV `CHAT_ON` totals: `RIGHT 44`, `WRONG 0`, `UNDETERMINED 20`. The 20 undetermined are
S1 6/6, S2 6/6, S7 4/4, S6 2/2, and R4 2/4. I added S3 (6), S4 (4) and S5 (4) to the same scan, because they
share the sentence shape. Result for all seven families — **32 items** — in `CHAT_ON`:

| family | items | terminal scored status | stock recorded |
|---|---|---|---|
| S1_WISDOM_STATED | 6 | `UNDETERMINED_CLARIFY` ×6 | 0 of 6 |
| S2_POWER_STATED | 6 | `UNDETERMINED_CLARIFY` ×6 | 0 of 6 |
| S3_FACE_UNKNOWN | 6 | `UNDETERMINED_CLARIFY` ×6 | 0 of 6 |
| S4_RECIPE_PURPOSE_ABSENT | 4 | `UNDETERMINED_CLARIFY` ×4 | 0 of 4 |
| S5_INGREDIENT_PURPOSE_ABSENT | 4 | `UNDETERMINED_CLARIFY` ×4 | 0 of 4 |
| S6_TWO_FACES | 2 | `UNDETERMINED_CLARIFY` ×2 | 0 of 2 |
| S7_NOT_A_FACE | 4 | `UNDETERMINED_CLARIFY` ×4 | 0 of 4 |

Every one of the 32 ends with `stock_after: {}` and the clause-bearing turn returning a clarify about an
ingredient (`CLARIFY_ENGLISH_UNKNOWN_INGREDIENT` or `CLARIFY_ENGLISH_NO_INGREDIENT_NAMED`), `writes: 0`.

**Then the key decides everything.** `gen_conv.score_item` (line 302):
- key expects `ASK` → any asking status with `writes == 0` is `RIGHT`.
- key expects `ANSWER` → anything other than `SUCCESS_EVALUATED` is `UNDETERMINED`.

So the same recorded event is **RIGHT for 14 items** (S3 6 + S4 4 + S5 4) and **UNDETERMINED for 18 items**
(S1 6 + S2 6 + S6 2 + S7 4). Consequence, stated plainly:

- The 14 "wins" in S3/S4/S5 do **not** show that HELM understood a purpose clause. They show that HELM asked.
  The record cannot distinguish "asked because the stated purpose was missing" from "asked because the stock
  line was rejected" — because the stock line was rejected in all 14 as well.
- The 18 "undetermined" are not a scoring puzzle. They are the same refusal, penalised because the key demanded
  an answer.

### 4.2 Where the refusal lives. **MEASURED on invented sentences; INFERRED for the exam instances.**

Free probes, run on this laptop, with sentences I wrote (never exam text):

```
read_wide("We have 4 cups flour and 2 cups milk.")                             -> STOCK
read_wide("We have 4 cups flour and 2 cups milk, but I'm a bit rusty with the milk.") -> CLARIFY  code=UNREAD_CLAUSE
read_wide("We have 4 cups flour and 2 cups milk, but the milk is getting old.")       -> CLARIFY  code=UNREAD_CLAUSE
read_wide("We have 4 cups flour and 2 cups milk, but I love baking with milk.")       -> CLARIFY  code=UNREAD_CLAUSE
```

`helm_wide_turn.py`'s own docstring states the design: "Three sentence shapes, all or nothing (one doubtful part
-> one question, nothing saved)". There is no shape for "stock plus a stated face or purpose clause", so the
clause becomes `UNREAD_CLAUSE` and nothing is saved.

The wide path also has, and uses, an explicit refusal for exactly this: the status
`CLARIFY_WIDE_FACE_NOT_HELD`. In `LOOP_ON` (loop driven directly) it fires **8 times** — S1 2 of 6, S2 2 of 6,
S3 2 of 6, S6 2 of 2. So HELM itself says, in its own recorded status word, that it cannot apply a stated
WISDOM/POWER face. In `LOOP_ON` the stock is recorded on 3 of the 32 items; in `CHAT_ON` on none.

So: **the wide brain implements no face effect and no purpose clause.** Those exam families require one. That is
a capability gap, honestly signalled by HELM, and it is not an instrument error.

What I could **not** pin without opening the exam: why the licensed reader says
`CLARIFY_ENGLISH_UNKNOWN_INGREDIENT` on the exam instances when my invented sentence of the same shape binds its
stock fine (`status CONTENT`, both stocks bound). Plausibly the exam's phrase pool supplies a form my sentence
did not, or the face ingredient's name is compound. Either way both readers refuse the clause, so the outcome
does not depend on the answer.

### 4.3 R4 (2 of 4): the paraphrase lesson form is not recognised. **MEASURED.**

`gen_conv` builds R4 two ways: even `k` sends the canonical lesson sentence, odd `k` sends
`"Yesterday we made 1 N from <the same ingredients>, and the <ingredient> ran out first."` The two failures are
`CV23` and `CV25` — both odd — and both recorded `CLARIFY_ENGLISH_UNKNOWN_PRODUCT`, i.e. not learned at all.

Probe on invented sentences with the same content:

```
canonical lesson form     read_wide=WITNESS    read_english=CLARIFY(UNKNOWN_PRODUCT)
R4 paraphrase form        read_wide=NOT_MINE   read_english=CLARIFY(UNKNOWN_PRODUCT)
```

(The `read_english` clarify is expected in that probe: "scone" was never taught in that fresh session.) The
finding is the `read_wide` column: the identical content in natural past-tense paraphrase is `NOT_MINE`. So the
2-of-4 loss is a specific, small, fixable reader gap — the wide reader learns the canonical lesson sentence and
not a paraphrase of it. That is HELM, not the instrument.

### 4.4 The 16 REAL asks are principled refusals. **MEASURED.**

`X7_REAL CHAT_ON`: `RIGHT 96`, `WRONG 0`, `ASKS 16`, `NOT_SCORED 16`, `unexplained_asks_strict 0`,
`fully_learned_rep 95` of `97`. I split the 128 records by outcome:

| | items | lessons admitted |
|---|---|---|
| answered (`SUCCESS_EVALUATED`) | 107 | all admitted ≥ 2; 539 of 753 lines = `0.7158` |
| asked (clarify) | 21 | **20 of 21 admitted zero lessons**; 13 of 165 lines = `0.0788` |

The arithmetic reconciles with the totals: `107 = 96 RIGHT + 11` items in the custodian's undetermined set that
received a commitment (`commitments_on_unsettled 11`), and `21 = 16 ASKS + 5` more from that set.

So the asks track "nothing was learned from that recipe", not a fault in asking. K4's rule accepts them, and
`unexplained_asks_strict 0` in **both** `CHAT_ON` and `LOOP_ON`. I read this as: HELM asked because its lesson
book was empty for that item. That is the honest behaviour the wave tests for. It is not a defect.

Two related numbers the marks do not see, and the owner should:

- **`commitments_on_unsettled = 11`, `commitments_on_same_name = 2`, `unsettled_ask_fired = 0`.** On 11 of the
  16 items whose key says the answer is undetermined, HELM produced a definite answer instead of asking; 2 of
  those are the "same ingredient name" case. Nothing flags this because those items are not scored, and the
  wave-7 chat carries no unsettled-ask rule by design (deviation D-W7-6). `LOOP_ON` records the same 11, so it
  is the brain, not the chat. If the owner wants the deferred "say I can't tell when the name is ambiguous" rule,
  these 11 items are the population it would act on.
- **`lessons_NOT_LEARNED = 110` of 662** on `CHAT_ON` (116 on `LOOP_ON`). Reading past "all marks met": about a
  sixth of the lesson lines in the real exam were never learned. K1's bar (95 of 97 fully learned) is met on the
  representable answer-keyed subset; it says nothing about the other 110 lines.

### 4.5 The free experiments that would settle each open item (0 USD, laptop only)

1. **S-family mechanism, per item.** The custodian replays one item's two turns through
   `HELMConversationalSession` with a debug hook that prints `read_english()` and `read_wide()` status and
   clarify code for each turn. No keys, no exam text emitted. Settles whether the exam instance fails at clause
   parse or at ingredient binding.
2. **S3/S4/S5 are RIGHT for the wrong reason.** Feed the same two turns to a session where the coach records the
   stock first and then the clause as a second sentence. If HELM then *answers* instead of asking, the RIGHT in
   the exam rests entirely on the lost stock line.
3. **R4.** Already settled by probe; a unit test pinning `read_wide(paraphrase) == "NOT_MINE"` would keep it
   fixed.
4. **The 16 asks.** For one of the 20 zero-lesson items, print the teaching turns' loop statuses. If they are
   `CLARIFY_*`, the recipe line itself was rejected — then it is a reader gap; if they are `WITNESS_*` with no
   admitted lesson, it is a brain gap.
5. **The 11 commitments.** Print, for those items, whether the brain had a coefficient for every ingredient. If
   yes, the ambiguity is in the exam's name mapping and HELM answered reasonably; if no, HELM guessed.

---

## 5. v4 change list

Split by what needs the owner's word. **Contract-preserving** means: no mark, threshold, arm, seed band, exam
size, instrument row, hard gate, or status word changes, and the preregistration text still describes the
system correctly.

### 5.1 Contract-preserving (a v4 re-seal, but no amendment)

| # | Change | File | Why |
|---|---|---|---|
| 1 | Record `helm_now_files_changed` (+ `scratch_files`, `agentic_tool_turns`) on the recorder unit, using the same before/after `tree_listing(ns.helm_now)` the chat unit uses | `r1w7/chat_harness.py` `run_recorder_equality` | Completes the record the preregistration already requires; the direct cause of `FAILURE` |
| 2 | Show a missing or non-empty value in the reported block: filter `if v != []`, and additionally report `null` explicitly | `r1w7/merge_r1w7.py` line 263 | The gate that failed displayed like a gate that passed |
| 3 | Set `pythonpath` to the stage's own package folder in the sealed plan | `kit/STAGE_R1W7.json` | Makes the seal self-consistent with the run-proven supervisor and with what attempt 2 actually ran |
| 4 | Change the kit test from `assertEqual(stage["pythonpath"], [])` to assert the stage survives `validate_plan` | `tests_r1w7/test_kit_w7.py` line 35 | The test currently forbids the fix |
| 5 | New test: `job_supervisor.validate_plan` is called on the plan exactly as `build_payload` builds it | `tests_r1w7/test_kit_w7.py` | The tool was pinned by hash and never executed; this is F1's whole cause |
| 6 | New test: no `<…>` fill-token survives in a shipped plan, and `--expected-freeze-sha256` equals the freeze hash | `tests_r1w7/test_kit_w7.py` | The second unchecked fill-target |
| 7 | Recorder fixture: drop the field the real unit does not write, or (better) make the fixture read a captured real record | `tests_r1w7/fixture_run.py` line 261 | Fixture–reality divergence |
| 8 | New test: feed the **real** unit files from a practice run into the reader and assert each gate holds, term by term | `tests_r1w7/test_units_w7.py` | No test ever proved HG5 *can* hold on real-shaped records |
| 9 | New test: HG5 holds on the practice records with host hashes stubbed equal | same | The practice run contained the defect and nothing pinned it |
| 10 | New test: every reader-read field name is written by at least one real unit of each class (a key-set assertion, not a value assertion) | `tests_r1w7/test_units_w7.py` | Catches the whole class, not just HG5 |
| 11 | Dry-run summary prints every gate's five terms, and the builder's record must state a reason per false term | `build/dry_run_w7.py`, `TEST_RECORD_R1W7.md` | Practice already reported `failing_gates: ["HG5_sandbox"]`; the reason given was incomplete |
| 12 | `build_payload` calls `validate_plan` on the assembled plan before writing the zip; `serve`-side asserts no `<…>` remains | operator kit | 0 USD, laptop, catches F1 four steps earlier |

### 5.2 Needs the owner's word (contract change or a new run)

| # | Change | Why it needs the owner |
|---|---|---|
| 13 | Re-running wave 7 (v4 package) at all | Money and a new exam require the owner's typed approval |
| 14 | If the recorder is instead exempted from HG5 | Weakening a hard gate is an amendment to the preregistration |
| 15 | A corrected `HG5` reading of the existing c51 data | The preregistration forbids re-reading sealed data with a repaired reader (line 4). The counterfactual in 2.1 is analysis, not a result, and must never be filed as one |
| 16 | Scoring S3/S4/S5 separately from the S-family refusal | The scoring rule is preregistered; noticing that 14 RIGHTs are mis-attributed does not change the word, but any rescoring would |

### 5.3 What I would *not* change

- The record shape of `HG5_sandbox` beyond the display filter. Its five terms are correct and each is
  meaningful.
- The `ASK`-key scoring rule `K.is_asking(status) and writes == 0`. It is preregistered and right for its
  purpose. The blind spot in 4.1 is better handled by adding a *reported row* (which S items reached the answer
  by clause understanding vs by generic clarify) than by changing the rule mid-wave.
- `plan_check.py`. It does one job and does it. It should not grow a `pythonpath` rule; the supervisor's own
  `validate_plan` should simply be called.

---

## 6. Operator kit: a safer design, and a checklist that needs no history

### 6.1 What goes wrong today, in one sentence

Each wave's operator scripts are produced by **literal text substitution of the previous wave's scripts**, with a
grep that refuses old wave names; three incidents in two days came out of that method:

- c50: pre-written scripts carried the previous payload's sha as a placeholder.
- c51 F3a: `make_c51_kit.py` refused four times on leftovers — the usage line, a shared-slot comment, the
  `payload_c50` folder name, `ANOTHER_C50_INSTANCE_IS_LIVE`, an undated reservation name, a console marker in
  single quotes, `"c50 already used"`, `r1w6v3-c50-` ids, docstrings. Each refusal added another substitution
  pair; the pair list is now 60+ entries.
- c51 F3b: the fill for `PAYLOAD_SHA` replaced **every** `__PAYLOAD_SHA__` in `aws_control_c51.py`, including the
  controller's own substitution site on line 294 (`.replace('__PAYLOAD_SHA__', PAYLOAD_SHA)`). Had it launched,
  the worker's own `PS='__PAYLOAD_SHA__'` would never have been filled and the host's `sha256sum -c` would have
  failed.

The root cause of F3b is precise and worth stating: **one token is used for two different jobs.** `__PAYLOAD_SHA__`
is both "the constant an operator must fill" (line 38) and "the string a template substitutes at run time"
(line 294). Any global fill damages one of them.

### 6.2 Proposed design: one values file, one template set, two token namespaces

1. **Keep the previous wave's scripts as the templates.** That part works; do not rewrite 6,000 lines of
   AWS-control code.
2. **Never derive a wave's scripts by substituting the previous wave's *values*.** Substitute only `{{…}}`
   tokens, and keep the token set in one place.
3. **Two namespaces, never shared:**

   | purpose | token | who fills it | when |
   |---|---|---|---|
   | an operator-supplied value | `{{PAYLOAD_SHA}}`, `{{FREEZE_SHA}}`, `{{ZIP_SHA}}`, `{{CARRIER_SHA}}`, `{{OWNER_LINE}}`, `{{RUN_DIR}}`, … | `fill_values.py` | after build, before launch |
   | a string a shipped script substitutes at run time | `[[PAYLOAD_SHA]]` | nothing on the operator side | never |

   With the two namespaces disjoint, a global fill of `{{…}}` can never touch a run-time substitution site, and
   `aws_control.py` keeps exactly one `[[PAYLOAD_SHA]]` in its worker template.
4. **One values schema, validated.** `kit_values.schema.json` lists every key, its type, and a regex. The filler
   refuses a values file with a missing key, an extra key, or a malformed hash.
5. **Three assertions after the fill, all free:**
   - no `{{` remains in any written file;
   - every `[[…]]` site is still present exactly where the template had it (compare site counts before/after);
   - no previous wave's name survives — but derive the forbidden list from the *values file's* `wave`, not from a
     hand-written list of 60 strings.
6. **Delete `make_c51_kit.py`'s substitution-pair list after this wave.** It is a liability that grows a pair per
   incident.

### 6.3 Launch checklist (each line is a program, not a sentence)

Run in order. Every line is free and runs on the laptop. Stop at the first failure.

| # | Check | Command / assertion |
|---|---|---|
| 1 | The watchdog is running **before** any launch | `watch N` started in its own job; `aws-c51-aN-watch.json` says `READY`. The controller asserts this at line 282 and raises `WATCHDOG_NOT_READY`, which is correct — leave `watch` running |
| 2 | The attempt is unused | controller line 277: `assert not INTENT.exists() and not STATE.exists()` |
| 3 | The sealed stage plan passes the **supervisor's own** validator | `from job_supervisor import validate_plan; validate_plan(plan)` using the bytes copied into `execution/` |
| 4 | `--expected-freeze-sha256` equals `sha256(payload PACKAGE_FREEZE.json)` | compare strings |
| 5 | No `<…>` or `{{…}}` token survives in `execution/job_plan.json` | regex over the file |
| 6 | Every value in `C51_VALUES.json` equals the artefact on disk | re-hash zip, freeze, approval, carrier |
| 7 | The worker template's substitution sites are intact | assert the count of `[[…]]` sites equals the count in the template |
| 8 | Simulate the worker fill | run the fill over the template in memory and assert no `[[` remains and the expected sha appears exactly once |
| 9 | The ledger hold exists and its sha is in the controller | `RESERVATION_SHA256` filled, hold record present |
| 10 | The payload's member count and every member hash match `payload_inventory.json` | re-walk the zip |
| 11 | Preflight reports the instance type, AZ, price and the 62-minute life | `aws_control preflight N` |
| 12 | Only after 1–11: `launch N` | — |
| 13 | After: terminate, then prove cleanup three ways | controller, independent script, direct AWS read |
| 14 | Read the reading with the sealed reader from the sealed zip | never from a working copy |

Line 3 alone would have prevented attempt 1. Line 7 alone would have prevented F3b.

### 6.4 One process note

`CLAIM` discipline held: attempt 1 made no AWS call until `launch`, and the slips in F3 were all caught by
refusal-before-launch. That design worked. The two things that escaped were both *not executable assertions*:
"the plan is valid" (assumed) and "the record has the field" (assumed).

---

## 7. What is and is not known

**Known (measured):**
- F1's cause, and that `pythonpath` is the only wrong plan field.
- The two checkers have no overlapping rule; `plan_check` cannot see `pythonpath`.
- Nothing in the package executes `validate_plan`; the payload builder does not either.
- F2's cause: one field, one unit, `None != []`.
- The reader's code is byte-identical to the freeze pin.
- The display filter hides exactly the value that failed.
- The practice run named `HG5_sandbox` as failing and had the same missing field.
- HG5 is the only live `None`-vs-value trap among gates, marks and instruments; one dormant case exists.
- All 32 S-family items in `CHAT_ON` record `UNDETERMINED_CLARIFY` with empty stock; 14 are scored RIGHT and 18
  UNDETERMINED by key alone.
- The wide reader returns `UNREAD_CLAUSE` for a stock sentence with a face/purpose clause, on invented text.
- The wide reader returns `NOT_MINE` for the R4 paraphrase of a lesson, on invented text.
- 20 of the 21 REAL asking items admitted zero lessons.

**Inferred, not measured:**
- That the S3/S4/S5 RIGHTs are unattributable to clause understanding for *these particular* items. The status
  sequences make it the only available reading, but I did not inspect the items.
- That the exam's face phrases reach the licensed reader's `UNKNOWN_INGREDIENT` through ingredient-name binding.
- That `HG8`'s set-equality is fragile to a future third wide module.

**Not known:**
- Which word in each exam face phrase the licensed reader binds as an ingredient. (Needs the item; I did not
  open it.)
- Whether the 20 zero-lesson recipes are unlearnable-by-design or a HELM gap. My invented-sentence probe suggests
  the clause is the problem, but those 20 include the custodian's own undetermined items, so the population is
  mixed.
- Whether a v4 run would earn `CHAT_WAVE_EARNED_KEEP`. All six marks are true and nine of ten gates are true on
  the existing data, and the tenth gate's false term is a record defect — but **that is not a prediction and not
  a claim**. A re-run is a new exam.

---

## 8. Answers to the brief's six delivery items, in one place

1. **F1 confirmed; F2 confirmed.** F1: `pythonpath: []` vs a supervisor rule requiring non-empty; pinned by a
   test; both checkers never overlapped; nothing executed the validator. F2: `W7_RECORDER_EQUALITY` omits
   `helm_now_files_changed`; the fixture supplies it; one `all(v == [])` over 14 records is False. Same-class
   risks elsewhere: only the frozen `<…>` fill-token and the dormant `session_files_under_scratch` on loop/
   always_ask records.
2. **Field table:** section 2.5.
3. **v4 change list:** section 5, split by whether the owner's word is needed.
4. **HELM vs instrument:** section 4. S1/S2/S6/S7 and half of R4 are real HELM gaps, honestly signalled; the
   RIGHTs in S3/S4/S5 are not evidence of clause understanding; the 16 REAL asks are principled; paths to inspect
   are `helm_wide_turn.read_wide` (`UNREAD_CLAUSE`, `NOT_MINE`), `helm_end_to_end_loop.wants_turn` (line 549),
   `helm_chat.handle_turn` step 4b (line 260), `helm_chat` steps 5b/`GENERAL_KNOWLEDGE_INQUIRY` (lines 315, 520),
   and `r1w6/gen_conv.score_item` (line 302). Five free experiments in 4.5.
5. **Operator kit:** sections 6.2 (two token namespaces, one values file) and 6.3 (14-line checklist).
6. **Known vs unknown:** section 7. The word for c51 is `INCONCLUSIVE`, and only the frozen reader may say it.

---

## 9. Evidence index

### 9.1 Frozen artefacts I re-hashed myself

| Artefact | sha256 |
|---|---|
| `R1_W7_READING.json` | `8f2f76468fef11e4d755083d2581578e04466e0d028a92848c8019ad945a5d4d` |
| `PACKAGE_FREEZE.json` | `2366e85d7a3b73fa0c6cefb94715aa7ba9cfeb6f3b384c4c0ad88d5ed0165da2` |
| `r1w7/merge_r1w7.py` (equals its freeze pin) | `975ccd6f0d84cf7278f1ebea67fd72e00e1844bc2f3d0f545fd50da602f6a7ae` |
| `kit/job_supervisor.py` (equals its freeze pin) | `3b2337ca75b189287c4591ed44671e308d37ef92d043f7bebb37ede77e6a1b01` |
| `kit/plan_check.py` (equals its freeze pin) | `84257a23545bfe87d7d4ef4565feae12adc9c325fa0fff06fefcb626c3301035` |
| host sandbox start = end | `65795c8c05fb687c7206fa9a449861ef988fa8b6be6d7d4061914c36db3a33c5` |

### 9.2 Readings I took from the sealed reading (all confirmed by my own extraction, not copied from prose)

- `verdict FAILURE`; `status_word INCONCLUSIVE`; `status_reason "verdict FAILURE"`.
- `failing_gates ["HG5_sandbox"]`; `failing_instruments []`; `marks_missed []`.
- Instruments: `I0, I1, I6, I7, I9, I10, I12, I14` all `true` (8 of 8).
- Gates: `HG1, HG2, HG3, HG4, HG6, HG7, HG8, HG9, HG10` `true`; `HG5_sandbox` `false` (9 of 10).
- Marks: `NH_CHAT, K1_LEARNS, K3_SAFE, K4_HONEST, P_PLAIN, N_NOISE` all `true` (6 of 6).
- `X7_REAL CHAT_ON`: `RIGHT 96`, `WRONG 0`, `ASKS 16`, `NOT_SCORED 16`, `RIGHT_AND_PLAIN 96`,
  `fully_learned_rep 95`, `rep_answer 97`, `lessons_LEARNED 552`, `lessons_NOT_LEARNED 110`, `lessons_WRONG 0`,
  `unexplained_asks_strict 0`, `not_routed_scored_turns 0`, `commitments_on_unsettled 11`,
  `commitments_on_same_name 2`, `same_name_items 7`, `undetermined_items 16`, `unsettled_ask_fired 0`,
  `plain 128`, `missing 0`.
- `X7_REAL LOOP_ON`: `RIGHT 94`, `WRONG 0`, `ASKS 18`, `fully_learned_rep 93`, `lessons_NOT_LEARNED 116`.
- `X7_REAL CHAT_OFF`: `RIGHT 0`, `ASKS 112`, `lessons_NOT_LEARNED 662`, `not_routed_scored_turns 4`.
- `X7_CONV`: `CHAT_ON 44/0/20`, `LOOP_ON 42/0/22`, `CHAT_OFF 30/0/34` (`RIGHT/WRONG/UNDETERMINED`); `missing 0` in
  every arm.
- `X7_NOISE CHAT_ON`: `RIGHT 44`, `WRONG 0`, `UNDETERMINED 20`, `noise_turns 128`, `misrouted_noise_turns 0`,
  `misrouted_scored_turns 0`, `noise_replies_with_cas 0`.
- `reported.unit_fields["W7_RECORDER_EQUALITY"]`: `helm_now_files_changed null`, `session_files_under_scratch
  null`, `scratch_files null`, `agentic_tool_turns null`, `wide_modules_imported ["helm_brain_wide",
  "helm_wide_turn"]`, `peak_memory_mib 30.9`, `python "3.12.3"`.

### 9.3 Program findings

| Finding | Where |
|---|---|
| `plan_check` PASS / `validate_plan` ValueError / fixed plan True | `diag_deepseek/plan_checks.py` |
| The 14 real unit records' structural fields; 13 write `[]`, 1 writes nothing | `diag_deepseek/extract_unit_fields.py` |
| HG5 rebuilt with the sealed reader's own code; counterfactual holds | `diag_deepseek/replay_hg5.py` |
| Field-by-field reader/real/fixture table; key-set diffs per class | `diag_deepseek/field_table.py` |
| All 32 S-family items: `UNDETERMINED_CLARIFY`, empty stock, 0 stock writes | `diag_deepseek/count_not_routed.py` |
| Per-turn routing and per-item statuses for the S and R families | `diag_deepseek/conv_undetermined.py`, `diag_deepseek/probe_turns.py` |
| Asking vs answering lesson-admission split on REAL | `diag_deepseek/probe_real_asks.py` |
| `read_wide(stock + clause)` → `CLARIFY/UNREAD_CLAUSE`; plain stock → `STOCK` | `diag_deepseek/probe_read_wide.py` |
| `read_english(stock + clause)` → `CONTENT` with both stocks bound (invented text) | `diag_deepseek/probe_read_english.py` |
| `read_wide(canonical lesson)` → `WITNESS`; `read_wide(R4 paraphrase)` → `NOT_MINE` | `diag_deepseek/probe_r4.py` |
| A live chat session routes a stock+clause turn to the loop and saves the stock | `diag_deepseek/probe_chat_route.py` |

All probe scripts are under `C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\diag_deepseek\` and can be re-run
on this laptop. None reads the exam folder or any `KEYS_*` file.

### 9.4 Files in the sealed package I read in full

`r1w7/merge_r1w7.py`, `r1w7/common_w7.py`, `r1w7/chat_harness.py`, `r1w7/units_w7.py`, `r1w7/score_w7.py`,
`kit/job_supervisor.py`, `kit/plan_check.py`, `kit/run_r1w7.py`, `kit/STAGE_R1W7.json`,
`tests_r1w7/fixture_run.py`, `tests_r1w7/test_units_w7.py`, `tests_r1w7/test_kit_w7.py`, `PREREGISTRATION_R1W7.md`
(searched, not read end to end), plus HELM's `helm_wide_turn.py` (structure and probes), `helm_chat.py` lines
118–330, `helm_end_to_end_loop.py` lines 549–580, and `deps/HELM_R1_W6_20261019/r1w6/gen_conv.py` lines 175–269
and 302–338, `r1w6/score_w6.py` lines 28–82.

---

## 10. One paragraph for the record

The exam was run honestly and its data is intact: eight of eight instruments true, nine of ten hard gates true,
six of six marks true, zero wrong answers, zero crashes, zero network attempts, zero CAS tokens in noise replies,
and the package on the host was byte-for-byte the approved freeze. The verdict is `FAILURE` and the word is
`INCONCLUSIVE` because one unit did not write one field, and one gate read the absence of that field as a
violation — which, under the preregistration's own wording, it is. The workaround for attempt 1 was legitimate
because the execution plan is not inside the freeze. Nothing is licensed, nothing is promoted, and a negative has
not been deleted.
