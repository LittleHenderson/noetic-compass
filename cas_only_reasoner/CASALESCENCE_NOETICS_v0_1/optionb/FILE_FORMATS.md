# Option B — file formats, version 1.0

**Status: PROPOSED. Sealed together with `08_OPTION_B_PLAN_v1_0.md` and `PLAN_CONSTANTS.json` in seal step 1.**

**Revised on 2026-10-05 after review round 1** (plan section 26). The parts that changed are marked "(review round 1)". Where two programs read a format differently, this file now says which reading holds.

**Amended on 2026-10-05 after the outside review** (plan section 27). The parts that changed are marked with their amendment, "A1" to "A11". Section 20 is new. No older section number changed.

**Amended again on 2026-10-05 by amendment A13 and for a short list of small faults** (plan sections 27.3 and 27.4). The parts that changed are marked "A13". No section number changed.

**Changed on 2026-10-05 by the operator's decisions of round 3** (plan section 27.5). Three decisions changed this file. The parts that changed are marked "operator decision C3", "operator decision C4" and "operator decision C6". These numbers are not the conditions C1 to C5 of the plan's section 15.3. No section number changed.

This file fixes the exact shape of every file that passes between programs. Builders code against it. If a program needs a field that is not here, the plan is changed first, not the program.

All examples use made-up content. They are never cases. Where a real file holds a canon definition line, the example shows a placeholder such as `<canon line ^7>`. Programs copy canon lines from the guide. Nobody retypes them. Where a real file holds a canonical sayings line (A13), the example shows a placeholder such as `<sayings line ^7>`. Programs copy the sayings from the table of Clarification 6. Nobody retypes them.

---

## 0. Rules for every file

**Where.** Every path below is relative to
`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/optionb/`
unless it starts with `work/` or `controller/` (those are inside the AWS job).

**Text.** UTF-8. LF line ends. No byte-order mark.

**JSON files.** Written with `json.dumps(value, indent=1, ensure_ascii=False)` plus one LF. On the laptop a tool writes `<name>.partial` and then renames it. (Inside the job the runner never renames. See section 16.)

**JSONL files.** One JSON object per line. Lines are only ever added at the end.

**Every JSON file starts with these fields:**

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | the name given in its section below |
| `made_by` | object | `{"program": "tools/ob_x.py", "sha256": "<hash of the program file>", "utc": "2026-10-06T10:00:00Z"}` |
| `inputs` | list | `[{"path": "...", "sha256": "..."}]`, every file the program read |

The examples below leave these three out to stay short. Exception: the two job files in section 17.2 and 17.3 hold no time and no host name, so that their bytes are the same on any machine.

**Names used in paths.**

| Name | Values |
|---|---|
| `<set>` | `practice` or `final` |
| `<pass>` | `p1` (first pass) or `p2` (spare pass) |
| `<nn>` | a two-digit sheet number: `01`, `02`, … |

**Ids.**

| Id | Form | Example |
|---|---|---|
| passage id | as in the sealed passages | `V123` |
| question id | `<passage>.<pass>.<FORM>` | `V123.p1.GOES_FOR`, `V123.p2.FACT` |
| task id | `<passage>.<FORM>` | `V123.GOES_FOR`, `V123.FACT` |
| note id | `<passage>\|<group>\|<length>\|v<version>` | `V123\|ORD-INFORMED\|090\|v1` |
| call id | `<phase>\|<task id>\|<group>\|L<level>\|W<wording>` | `final\|V123.GOES_FOR\|ROLE\|L1\|W2` |
| solver item id | a letter prefix and four digits | `Q0001`, `G0001`, `N0001` |

`FACT` is the form id and the type of a plain-fact question. Form ids, type names and group names are the ones in `PLAN_CONSTANTS.json`.

**Counts and shares.** A share is stored as a pair of whole numbers `[part, whole]`. Where a decimal is useful for a reader it is stored as text in a field whose name ends in `_text`, for example `"16.41"`. No JSON file in the job holds a decimal number. So a not-a-number value can not appear. Job files are written with `allow_nan=False`.

**Keys of outside services.** Read from the environment variables named in `PLAN_CONSTANTS.json`. Never read from a file. Never written to any file or log. An error text is scrubbed of the key before it is logged.

**The model name of every reply (amendment A9).** Four tools call an outside service: `tools/ob_write_questions.py`, `tools/ob_check_support.py`, `tools/ob_solve_blind.py` (step `deepseek`) and `tools/ob_write_ordinary_notes.py`. Every line of their call logs (sections 4.2, 6.2, 8.2 and 9.3) holds these two fields:

| Field | Type | Meaning |
|---|---|---|
| `model` | string | the model name the tool asked for |
| `model_in_reply` | string or null | the model name the service put in its reply: the reply's own field `model`, copied as it is. Null when no readable reply came back (a refused call, no answer, an unreadable reply). |

The tool stores the name. It does not judge it. A Claude sub-agent is not called by a tool, so it has no call log; its model name is stored by the `import` step (sections 6.4 and 6.5).

**The DeepSeek token limits (amendment A11).** DeepSeek may cost at most 4.00 USD in total. The two DeepSeek tools enforce that as two token limits: `outside_services.deepseek.spend_cap_input_tokens` (2,430,240) and `spend_cap_output_tokens` (1,156,520) in `PLAN_CONSTANTS.json`.

- The count is kept in the call logs, which are the checkpoints of these two tools. Every line of the four DeepSeek call logs holds `usage`: the usage object of the reply as the service gave it, or null. The four logs are `solve/deepseek_calls_practice.jsonl`, `solve/deepseek_calls_final.jsonl`, `notes_ord/ordinary_calls_practice.jsonl` and `notes_ord/ordinary_calls_final.jsonl`.
- Input count: the sum of `usage.prompt_tokens` over every line of the four logs. Output count: the sum of `usage.completion_tokens` over the same lines. A line whose `usage` is null adds nothing.
- Before each call the tool knows both counts as the four logs then stand. If the input count has reached its limit, or the output count has reached its limit, the tool makes no call and stops with the status `STOPPED_TOKEN_CAP`.
- A reply with `http_status` 200 whose `usage` does not hold the whole numbers `prompt_tokens` and `completion_tokens` is logged. Then the tool stops with the status `STOPPED_NO_TOKEN_COUNT`.
- The two tools are not run at the same time. Calls that are running when a limit is reached still finish, so a count can pass its limit by a few calls.
- A tool whose work folder sits under `optionb/dry/` calls no service and counts nothing.

**Blindness.** A tool that calls an outside model sends only what its section says it sends. It never sends a field that holds a label, a note of another group, or a key.

**Frozen functions.** `clean`, `select`, `same_span`, `same_field`, `lenient_span`, `content` and `REQUIRED` are imported from `tools/verdict.py` after its sha256 is checked against `PLAN_CONSTANTS.json`.

**What a laptop tool prints (A13, small faults).** Every `tools/ob_*.py` program sets its standard output and its standard error to UTF-8 before it prints anything. So a character that the Windows code page does not hold can never crash a tool after it has saved its work.

**Exit codes of the laptop tools (A13, small faults).** Every `tools/ob_*.py` program ends with one of four codes. A code means the same thing in every tool.

| Code | Meaning |
|---:|---|
| 0 | Done. The work due in this command is finished. The next step of the run order may start. |
| 1 | Not finished. Something is still open. What the tool prints says what is open. Either the same command is run again later (a call budget is used up, a call was refused, a token limit is reached, no answer came). Or the step it names is run first (a note must be written again, the next reserve setting must move). |
| 2 | Not started, or stopped by a check or a refusal. The reason is printed. |
| 3 | Done, and the result says: do not launch. |

- Only code 0 lets the next step of the run order start.
- The printed status word is the record of what happened. The exit code never disagrees with it.
- A run with `--max-calls 0` that leaves calls open ends with code 1.
- A crash (a Python traceback) never ends with code 0.
- The job programs are not laptop tools. Their rule is in section 16.

---

## 1. Pipeline order at a glance

| # | Program | Writes | Seal step after it |
|---:|---|---|---|
| 1 | `tools/ob_eligibility.py` | `elig/exclusions.json`, `elig/eligibility.json` | 1 |
| 2 | `tools/ob_role_notes.py` | `notes_role/role_notes.json`, `notes_role/owner_sample_20.json` | 2 |
| 3 | `tools/ob_write_questions.py` (practice) | `questions/writer_state_practice_<pass>.json`, `questions/writer_calls_practice_<pass>.jsonl`, `questions/raw_questions_practice_<pass>.json` | |
| 4 | `tools/ob_check_questions.py` (practice) | `checks/form_check_practice.json`, `checks/anchor_check_practice.json`, `checks/option_check_practice.json`, `checks/candidates_practice.json` | |
| 5 | `tools/ob_solve_blind.py` (practice) | the `solve/` files | |
| 6 | `tools/ob_select.py` (practice) | `select/selection_practice.json`, then `select/split_fixed.json` | 3A, then 3B |
| 7 | programs 3 to 6 again for `final` | the same files with `final` in the name | 3C |
| 8 | `tools/ob_write_ordinary_notes.py` | `notes_ord/ordinary_notes_<set>.json`, `notes_ord/ordinary_calls_<set>.jsonl` | |
| 9 | `tools/ob_check_support.py` | the `support/` files | 4 |
| 10 | `tools/ob_screen_notes.py` | `screen/leak_screen_<set>.json` | |
| 11 | `tools/ob_assemble.py` | `removal_log.json`, `prompts/prompt_parts_<set>.json`, `keys_practice/…`, `keys_final/…`, `review/review_pack.json` | 5 |
| 12 | the job programs are finished and reviewed | `job/runner_b1.py`, `job/scorer_v0_1_1.py`, `job/gate_b1.py`, `job/analysis_b1.py`, `job/scorer_examples_v0_1_1.json` | 6 |
| 13 | the pre-check job (AWS, CPU only) | `work/run_b1/selftest.json` and the two hashes | 7 |
| 14 | the GPU job (AWS) | the files of section 17 | |

`tools/ob_seal.py` writes `SEAL_OPTIONB.jsonl` (section 15). Every program first checks that the seal steps it depends on exist and that the sealed files have not changed. If not, it stops.

Steps 8 to 10 loop once: a note that fails the support check is written again once (step 8), then checked again (step 9).

**Order of work on the practice set (review round 1; plan section 10, "Practice first").**

1. Rows 3 to 6 run for `practice`. If the reserve rule is not finished (section 7.1), the next reserve setting is moved and rows 3 to 6 run again. Only then is seal step 3A written, then `split_fixed.json`, then seal step 3B.
2. Rows 8 and 9 then run for `practice`, both rounds. Then row 10 runs for `practice` with `--report-only` (section 10.2).
3. Only then does row 7 start. If the practice set is by then under the launch floor, row 7 does not start.

No program enforces points 2 and 3. The times in the call logs and in `made_by` show the order.

**The ten tools of rows 1 to 11 and `tools/ob_seal.py`, eleven files in all, are sealed in step 1** (section 15). A tool that changed after that stops with `SEALED_FILE_CHANGED`, as any sealed file does.

**Before seal step 1: the development test (amendment A10).** One CPU-only AWS job of kind `DEVELOPMENT_TEST`, at most two, runs the runner's self-test on a made-up package before seal step 1 is written (plan section 19.1). It is outside the seal chain. Section 20 describes its package.

---

## 2. Eligibility and exclusions

### 2.1 `elig/exclusions.json`

- **Written by:** `tools/ob_eligibility.py`
- **Read by:** `tools/ob_seal.py`, `tools/ob_assemble.py`
- **Schema name:** `casalescence/optionb/exclusions/v1`

| Field | Type | Meaning |
|---|---|---|
| `count` | whole number | must be 104 |
| `by_kind` | object | passages per writer kind |
| `passages` | list | one object per excluded passage |
| `passages[].id` | string | passage id |
| `passages[].kind` | string | `K1` … `K9` |
| `passages[].reasons` | list of strings | `<team>:<code>`; team is `A` or `B`; code is `UNCERTAIN_8_OR_9`, `OTHER_CANDIDATE_REASONING` or `REACHED_BY_REASONING` |

```json
{"schema": "casalescence/optionb/exclusions/v1",
 "count": 104,
 "by_kind": {"K1": 1, "K3": 29, "K4": 11, "K5": 3, "K6": 30, "K7": 30},
 "passages": [{"id": "V900", "kind": "K6", "reasons": ["A:UNCERTAIN_8_OR_9", "B:OTHER_CANDIDATE_REASONING"]}]}
```

### 2.2 `elig/eligibility.json`

- **Written by:** `tools/ob_eligibility.py`
- **Read by:** `tools/ob_role_notes.py`, `tools/ob_write_questions.py` (only `id`, `kind`, `setting`, `setting_role`, `writer_asks`, `text`), `tools/ob_check_questions.py`, `tools/ob_select.py`, `tools/ob_assemble.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/eligibility/v1`
- It lists all 428 passages.

| Field | Type | Meaning |
|---|---|---|
| `practice_settings` | list of 8 strings | in sealed order |
| `reserve_settings_in_order` | list of 4 strings | in sealed order |
| `counts` | object | the same keys as `counts_real` in `PLAN_CONSTANTS.json` |
| `counts_match_plan` | true | the program stops before writing if this would be false |
| `passages[].id`, `.kind`, `.setting`, `.text` | strings | copied from the sealed passages |
| `passages[].setting_role` | string | `practice`, `reserve_1` … `reserve_4`, or `final` |
| `passages[].writer_asks` | true/false | true when the kind is K1 to K5 |
| `passages[].excluded` | true/false | the rule-15 exclusion |
| `passages[].barred` | true/false | true for `V009` and `V076` |
| `passages[].eligible` | true/false | not excluded and at least one open form |
| `passages[].agreed`, `.only_a`, `.only_b` | objects | entry counts per Noetic; a Noetic with zero is left out |
| `passages[].open_forms` | list of form ids | in the order of `forms_in_order` |
| `passages[].open_types` | list of type names | |
| `passages[].max_role_step_tasks` | 0, 1 or 2 | the ceiling for this passage |
| `passages[].leftover_on_type` | object | per open type: true when an only-one-team entry exists on its Noetics |
| `passages[].any_leftover_2_to_9` | true/false | |
| `passages[].entries` | object or null | null for an excluded passage |
| `…entries.agreed[]` | list | `{"noetic", "a": {entry}, "b": {entry}}` |
| `…entries.only_a[]`, `.only_b[]` | lists | `{"noetic", entry fields}` |
| entry fields | | `index` (place in that team's raw entry list, from 0), `words`, `mind`, `relative_to` |

A passage belongs to the practice set, for a given number N of practice settings (8 to 12), when its `setting_role` is `practice` or `reserve_k` with k ≤ N − 8. Otherwise it belongs to the final set. A barred passage is in the writer's batches but never becomes a task.

```json
{"schema": "casalescence/optionb/eligibility/v1",
 "practice_settings": ["a locksmith's van", "…"],
 "reserve_settings_in_order": ["a cheese cellar", "…"],
 "counts": {"passages": 428, "excluded_passages": 104, "eligible_passages": 192},
 "counts_match_plan": true,
 "passages": [
  {"id": "V901", "kind": "K5", "setting": "a swimming pool", "text": "Oksana had weighed out flour …",
   "setting_role": "practice", "writer_asks": true, "excluded": false, "barred": false, "eligible": true,
   "agreed": {"^1": 1, "^7": 1}, "only_a": {"^5": 1}, "only_b": {},
   "open_forms": ["LONG_BREAK", "NEW_STARTER"], "open_types": ["HABIT"], "max_role_step_tasks": 2,
   "leftover_on_type": {"HABIT": false}, "any_leftover_2_to_9": true,
   "entries": {
    "agreed": [{"noetic": "^7",
                "a": {"index": 1, "words": "Every weekday for eleven years", "mind": "Oksana", "relative_to": "weighed out flour"},
                "b": {"index": 2, "words": "Every weekday for eleven years", "mind": "Oksana", "relative_to": "flour"}}],
    "only_a": [{"noetic": "^5", "index": 2, "words": "her hands stopped the scoop", "mind": "Oksana", "relative_to": ""}],
    "only_b": []}}]}
```

---

## 3. Role notes

### 3.1 `notes_role/role_notes.json`

- **Written by:** `tools/ob_role_notes.py`
- **Read by:** `tools/ob_write_ordinary_notes.py` (only the `size` fields; it never sends a role text anywhere), `tools/ob_screen_notes.py`, `tools/ob_assemble.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/role_notes/v1`
- One object per eligible passage (192).

| Field | Type | Meaning |
|---|---|---|
| `canon.source`, `canon.sha256` | strings | the guide file and its hash |
| `canon.lines` | object | per Noetic `^1` … `^9`: the note line built from the guide line |
| `canon.names` | object | per Noetic: its name, read from the guide |
| `canon.sayings_source`, `canon.sayings_sha256` | strings | A13: the file that holds the table of sayings, written `../../docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, and its hash |
| `canon.sayings_lines` | object | A13: per Noetic `^1` … `^9`: the sayings line built from that Noetic's table row |
| `passages[].id` | string | |
| `passages[].entries[]` | list | the agreed entries, in note order: the `^1` entries first, then the others, each part in passage order |
| `…entries[].noetic`, `.name` | strings | the true Noetic and its name |
| `…entries[].mixed_noetic`, `.mixed_name` | strings | after the swap table |
| `…entries[].label` | string | the short label |
| `…entries[].mind`, `.relative_to` | strings | `""` when not printed |
| `…entries[].supporting_quote` | string or null | null for a `^1` entry |
| `…entries[].same_as_label` | string or null | set when the quote was already printed |
| `…entries[].offset` | whole number | where the entry starts in the passage |
| `…entries[].a_index`, `.b_index` | whole numbers | the two paired raw entries |
| `passages[].role_text` | string | the ROLE notes text, without the padding line |
| `passages[].mixed_text` | string | the MIXED notes text |
| `passages[].quotes_only_text` | string | the QUOTES-ONLY notes text |
| `passages[].frame_blanked` | object | `role`, `mixed`, `quotes_only`: the same three texts with every quoted passage part emptied (`""`); used by the answer-leak screen |
| `passages[].size` | object | `role_size_count`, `role_words`, `passage_size_count`, `passage_words` (whole numbers). A13: the two role numbers are counted on the whole ROLE text, its sayings lines included. |
| `passages[].left_out` | object | `only_a` and `only_b` counts per Noetic |

Lines inside a notes text are joined with LF. The text has no heading and no padding line.

**The head of a ROLE or MIXED text (A13).** For each Noetic that appears in the text, in number order: its canon line (`canon.lines`), then its sayings line (`canon.sayings_lines`). Then come the entry lines. So the head has two lines per Noetic. In a MIXED text the head follows the swapped tags: each swapped tag brings its own canon line and its own sayings line. A QUOTES-ONLY text has no head.

**The sayings line (A13).** Its template is `role_notes.sayings_note_line` in `PLAN_CONSTANTS.json`: the word `Sayings`, a colon, one space, then the sayings cell. The sayings cell is the third cell of that Noetic's row in the table under the heading `### Canonical colloquialism map` of the source `sources.canonical_sayings`. It is copied character for character. The tool reads the table from the file when it runs. It writes nothing unless all three hold:

- the file has the pinned size and sha256;
- the table has 10 rows, one for each of `^0` to `^9`;
- in each row the definition cell equals, character for character, the definition of that Noetic's line in Part A of the guide.

If a definition cell and the guide differ, the tool stops and reports. Nobody picks one of the two texts.

**`frame_blanked` and the sayings line (A13).** A sayings line holds quote marks, but it is not a passage part. It stays whole in the blanked text, like a canon line. So the answer-leak screen tests the word `Sayings` and the sayings text as fixed frame words.

**`inputs` (A13).** It names the sayings file with the path `../../docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` and its sha256, next to the guide.

```json
{"schema": "casalescence/optionb/role_notes/v1",
 "canon": {"source": "02_LABELING_GUIDE_v1_2.md", "sha256": "3ed4…022e",
           "lines": {"^1": "<canon line ^1>", "^7": "<canon line ^7>"},
           "names": {"^1": "Mind", "^7": "Rhythm"},
           "sayings_source": "../../docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md", "sayings_sha256": "cda8…1880",
           "sayings_lines": {"^1": "<sayings line ^1>", "^7": "<sayings line ^7>"}},
 "passages": [
  {"id": "V901",
   "entries": [
    {"noetic": "^1", "name": "Mind", "mixed_noetic": "^1", "mixed_name": "Mind", "label": "Oksana", "mind": "", "relative_to": "",
     "supporting_quote": null, "same_as_label": null, "offset": 31, "a_index": 0, "b_index": 0},
    {"noetic": "^7", "name": "Rhythm", "mixed_noetic": "^4", "mixed_name": "Vibration", "label": "Every weekday for eleven years",
     "mind": "Oksana", "relative_to": "flour",
     "supporting_quote": "Every weekday for eleven years Oksana had weighed out flour at the same bench before dawn.",
     "same_as_label": null, "offset": 0, "a_index": 1, "b_index": 2}],
   "role_text": "<canon line ^1>\n<sayings line ^1>\n<canon line ^7>\n<sayings line ^7>\n- ^1 Mind: \"Oksana\".\n- ^7 Rhythm: \"Every weekday for eleven years\". For the Mind \"Oksana\". Relative to \"flour\". Supporting quote: \"Every weekday for eleven years Oksana had weighed out flour at the same bench before dawn.\"",
   "mixed_text": "<canon line ^1>\n<sayings line ^1>\n<canon line ^4>\n<sayings line ^4>\n- ^1 Mind: \"Oksana\".\n- ^4 Vibration: \"Every weekday for eleven years\". For the Mind \"Oksana\". Relative to \"flour\". Supporting quote: \"…\"",
   "quotes_only_text": "- \"Oksana\".\n- \"Every weekday for eleven years\". Supporting quote: \"…\"",
   "frame_blanked": {"role": "…", "mixed": "…", "quotes_only": "…"},
   "size": {"role_size_count": 78, "role_words": 49, "passage_size_count": 52, "passage_words": 45},
   "left_out": {"only_a": {"^5": 1}, "only_b": {}}}]}
```

### 3.2 `notes_role/owner_sample_20.json`

- **Written by:** `tools/ob_role_notes.py`. **Read by:** the owner. No program reads it.
- **Schema name:** `casalescence/optionb/owner_role_note_sample/v1`
- 20 eligible passages drawn with `random.Random(<owner_role_note_sample>).sample(sorted eligible ids, 20)`.
- Fields: `seed`, `passages[]` with `id`, `text`, `role_text`, `left_out`.

---

## 4. Question writer

Three files per set and pass. **Written by:** `tools/ob_write_questions.py`.

**Batches.** A set is written in waves. For the practice set, wave 0 is the 8 practice settings and wave k is reserve setting k. For the final set there is one wave: every final setting. Inside a wave: take the K1 to K5 passage ids, sort them, shuffle them with `random.Random(<writer_batch_order_p1 or _p2>)`, and cut them into groups of 4 (amendment A1; the number is `outside_services.gemini_question_writer.passages_per_call`). A wave that was already written is never batched again. A real run does not give the option `--batch-size`: every batch of a real run holds up to 4 passages (A13, small faults).

**What is sent.** The question brief with its lists filled in, then the fenced passages of the batch. Nothing else.

**One model (amendment A1).** The model is `gemini-3.5-flash-lite`. It writes the practice set, the final set and both passes. The tool takes the name from `model_by_set` in `PLAN_CONSTANTS.json` and refuses any other name.

**Refused calls (amendment A1).** A call with `http_status` 429 is not counted as an attempt. The tool stops cleanly, keeps the checkpoint, and resumes when it is run again later. The daily cap of this model is not known.

**The reserve rule (amendment A8).** For the practice set the tool adds wave k (k is 1 or more) only as the reserve rule of section 7.1 allows. It reads the block `reserve` of `select/selection_practice.json`, exactly as `tools/ob_select.py` and `tools/ob_seal.py` do. It adds wave k only when that file exists, its `practice_setting_count` equals 8 + k − 1, and its `reserve.finished` is false. A file with no `reserve` block also stops the tool. The stop is `RESERVE_RULE_NOT_MET`, and its text names the two reserve targets. The tool does not read `floor.met` for this rule. (A wave that the other pass of the same set already holds is added without this check, as before.)

### 4.1 `questions/writer_state_<set>_<pass>.json` (the checkpoint)

- **Read by:** `tools/ob_write_questions.py` (to resume), `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/writer_state/v1`

| Field | Type | Meaning |
|---|---|---|
| `set`, `pass`, `model` | strings | `model` is the name asked for. The tool refuses any model but the one of `PLAN_CONSTANTS.json`; one model writes both sets and both passes. |
| `seed` | whole number | the batch-order seed of this pass |
| `waves[].wave` | whole number | |
| `waves[].settings` | list of strings | |
| `waves[].batches[].batch` | whole number | from 0, inside the wave |
| `waves[].batches[].passage_ids` | list | up to 4 |
| `waves[].batches[].status` | string | `PENDING`, `DONE` or `UNREADABLE` |
| `waves[].batches[].attempts` | whole number | a refused call (`http_status` 429) is not counted |
| `cap_stops_utc` | list of strings | one per clean stop after a refused call (`http_status` 429) |
| `complete` | true/false | true when no batch is `PENDING` |

```json
{"schema": "casalescence/optionb/writer_state/v1", "set": "practice", "pass": "p1", "model": "gemini-3.5-flash-lite", "seed": 20261005,
 "waves": [{"wave": 0, "settings": ["a locksmith's van", "…"],
            "batches": [{"batch": 0, "passage_ids": ["V901", "V902"], "status": "DONE", "attempts": 1}]}],
 "cap_stops_utc": [], "complete": true}
```

### 4.2 `questions/writer_calls_<set>_<pass>.jsonl` (the call log)

- **Read by:** `tools/ob_seal.py`, the reviewer
- One line per call that reached the service.

| Field | Type |
|---|---|
| `utc`, `set`, `pass`, `model` | strings; `model` is the name asked for |
| `model_in_reply` | string or null: the model name the service put in its reply (section 0; amendment A9) |
| `wave`, `batch`, `attempt`, `http_status` | whole numbers |
| `passage_ids` | list |
| `prompt_sha256`, `reply_sha256` | strings (sha256 of the UTF-8 text) |
| `ok` | true/false |
| `error` | string or null (key scrubbed) |
| `usage` | object or null |
| `prompt`, `reply` | strings, the full texts |

```json
{"utc": "2026-10-06T10:00:00Z", "set": "practice", "pass": "p1", "model": "gemini-3.5-flash-lite", "model_in_reply": "<the name in the reply>", "wave": 0, "batch": 0, "attempt": 1, "http_status": 200, "passage_ids": ["V901", "V902"], "prompt_sha256": "ab…", "reply_sha256": "cd…", "ok": true, "error": null, "usage": {"total_tokens": 4100}, "prompt": "You will get several short passages. …", "reply": "[{\"passage\": \"V901\", …}]"}
```

### 4.3 `questions/raw_questions_<set>_<pass>.json`

- **Read by:** `tools/ob_check_questions.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/raw_questions/v1`
- One object per passage that was asked. Texts are stored as returned, with outer white space removed. Nothing else is edited.

| Field | Type | Meaning |
|---|---|---|
| `passages[].passage_id` | string | |
| `passages[].wave`, `.batch` | whole numbers | |
| `passages[].status` | string | `OK`, `MISSING` (not in the reply) or `BAD_OBJECT` (not readable) |
| `passages[].what_follows[]` | list | role-step questions |
| `….question_id` | string | |
| `….form` | string | as the writer wrote it; an unknown name is kept and dropped in Step 2 |
| `….question`, `.right` | strings | |
| `….wrong` | list of strings | in the writer's order |
| `….anchors` | list of strings | |
| `passages[].plain_fact` | object or null | `question_id`, `question`, `right`, `wrong` |
| `passages[].extra_dropped` | list | later questions for a form the writer already used on this passage |

```json
{"schema": "casalescence/optionb/raw_questions/v1", "set": "practice", "pass": "p1", "model": "gemini-3.5-flash-lite",
 "passages": [
  {"passage_id": "V901", "wave": 0, "batch": 0, "status": "OK",
   "what_follows": [{"question_id": "V901.p1.LONG_BREAK", "form": "LONG_BREAK",
     "question": "Oksana takes a desk job for two years and never weighs flour. Going only by the passage, which of these has most likely faded when she comes back?",
     "right": "stopping the scoop without a glance",
     "wrong": ["tying her apron at the bench", "calling out for the trays", "hearing the radio on the shelf", "finding her bench before dawn", "reading numbers on the scale"],
     "anchors": ["Every weekday for eleven years", "her hands stopped the scoop"]}],
   "plain_fact": {"question_id": "V901.p1.FACT", "question": "Where was the new radio?", "right": "on the shelf", "wrong": ["on the bench", "beside the scale", "in the tray rack"]},
   "extra_dropped": []}]}
```

---

## 5. Form check, anchor check, option check, candidates

**Written by:** `tools/ob_check_questions.py`. It reads both passes of a set, `elig/eligibility.json` and (for `final`) `select/split_fixed.json`.

Option index everywhere: `0` is the right option; `1` to `5` are the wrong options in the writer's order.

### 5.1 `checks/form_check_<set>.json` (Step 2)

- **Read by:** `tools/ob_assemble.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/form_check/v1`
- One row per raw question of both passes, both families.

| Field | Type | Meaning |
|---|---|---|
| `rows[].question_id` | string | |
| `rows[].family` | string | `role_step` or `plain_fact` |
| `rows[].passed` | true/false | |
| `rows[].reasons` | list of strings | empty when passed |
| `counts` | object | `checked`, `passed`, `dropped_by_reason` |

Reason codes: `FORM_NAME_UNKNOWN`, `EMPTY_TEXT`, `OPTION_COUNT`, `OPTIONS_NOT_DIFFERENT`, `OPTION_TOO_LONG`, `QUESTION_TOO_LONG`, `OPTION_LENGTH_SPREAD`, `OPTION_INSIDE_ANOTHER`, `ANCHOR_COUNT`, `ANCHOR_NOT_IN_PASSAGE`, `ANCHOR_TOO_LONG`, `FORBIDDEN_LIST_A:<word>`, `FORBIDDEN_SIGN`, `FORBIDDEN_LIST_B:<word>`, `FORBIDDEN_LIST_C:<phrase>`, `FORBIDDEN_PHRASE`.

```json
{"schema": "casalescence/optionb/form_check/v1", "set": "practice",
 "rows": [{"question_id": "V901.p1.LONG_BREAK", "family": "role_step", "passed": true, "reasons": []},
          {"question_id": "V902.p1.GOES_FOR", "family": "role_step", "passed": false, "reasons": ["OPTION_LENGTH_SPREAD", "FORBIDDEN_LIST_C:drawn"]}],
 "counts": {"checked": 2, "passed": 1, "dropped_by_reason": {"OPTION_LENGTH_SPREAD": 1, "FORBIDDEN_LIST_C": 1}}}
```

### 5.2 `checks/anchor_check_<set>.json` (Step 3a)

- **Read by:** `tools/ob_assemble.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/anchor_check/v1`
- One row per role-step question that passed the form check.

| Field | Type | Meaning |
|---|---|---|
| `rows[].question_id` | string | |
| `rows[].passed` | true/false | |
| `rows[].reason` | string or null | `PASSAGE_NOT_ELIGIBLE`, `PASSAGE_BARRED`, `FORM_NOT_OPEN`, `NO_ANCHOR_MATCHES_AGREED_ENTRY` |
| `rows[].matched[]` | list | `anchor`, `noetic`, `agreed_index` (place in `entries.agreed`), `field` (`words_a`, `words_b`, `relative_a`, `relative_b`) |

```json
{"schema": "casalescence/optionb/anchor_check/v1", "set": "practice",
 "rows": [{"question_id": "V901.p1.LONG_BREAK", "passed": true, "reason": null,
           "matched": [{"anchor": "Every weekday for eleven years", "noetic": "^7", "agreed_index": 0, "field": "words_a"}]}],
 "counts": {"checked": 1, "passed": 1, "dropped_by_reason": {}}}
```

### 5.3 `checks/option_check_<set>.json` (Step 3b)

- **Read by:** `tools/ob_assemble.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/option_check/v1`
- One row per role-step question that passed the anchor check.

| Field | Type | Meaning |
|---|---|---|
| `rows[].question_id` | string | |
| `rows[].passed` | true/false | false when `hits` is not empty |
| `rows[].hits[]` | list | `option_index`, `option`, `noetic`, `team` (`a` or `b`), `entry_index`, `field` (`words` or `relative_to`) |

```json
{"schema": "casalescence/optionb/option_check/v1", "set": "practice",
 "rows": [{"question_id": "V903.p1.WHAT_LEFT", "passed": false,
           "hits": [{"option_index": 2, "option": "the worn cylinder", "noetic": "^6", "team": "b", "entry_index": 4, "field": "words"}]}],
 "counts": {"checked": 1, "passed": 0}}
```

### 5.4 `checks/candidates_<set>.json`

- **Read by:** `tools/ob_solve_blind.py`, `tools/ob_select.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/candidates/v1`
- At most one candidate per passage and form, and one plain-fact candidate per passage. It holds no label information.
- Rule: the `p1` question if it passed Steps 2 and 3; else the `p2` question, only if a `p1` question for that form existed, was dropped by Step 2 or 3, and the `p2` question passed Steps 2 and 3. (A plain-fact question has no Step 3.)

| Field | Type |
|---|---|
| `candidates[].question_id`, `.passage_id`, `.family`, `.form`, `.pass` | strings |
| `candidates[].passage` | string, the passage text |
| `candidates[].question`, `.right` | strings |
| `candidates[].wrong`, `.anchors` | lists of strings |
| `counts` | object: `role_step`, `plain_fact`, `spares_used` |

```json
{"schema": "casalescence/optionb/candidates/v1", "set": "practice",
 "candidates": [{"question_id": "V901.p1.LONG_BREAK", "passage_id": "V901", "family": "role_step", "form": "LONG_BREAK", "pass": "p1",
                 "passage": "Every weekday for eleven years …", "question": "…", "right": "stopping the scoop without a glance",
                 "wrong": ["…", "…", "…", "…", "…"], "anchors": ["Every weekday for eleven years"]}],
 "counts": {"role_step": 1, "plain_fact": 0, "spares_used": 0}}
```

---

## 6. Blind solvers (Steps 4 and 5)

**Written by:** `tools/ob_solve_blind.py`. It has these steps: `deepseek` (calls the service), `export` (writes a sheet for a Claude sub-agent), `import` (reads the sub-agent's reply sheet), `decide` (applies the keep rules).

Two modes: `with_passage` (Step 4) and `no_passage` (Step 5). Both run on every candidate.

**What is sent or exported.** With the passage: the passage, the question, the options in shuffled order. Without: the question and the options. Never the key, a label, a note or a real passage id.

**Shuffle.** The options of a question are shuffled with `random.Random('<solver_option_shuffle>|<question id>|<solver>|<mode>')`. Letters A, B, C, … are given in the shown order.

**Item ids.** Sort the question ids, shuffle them with `random.Random('<sheet_item_order>|<set>|<solver>|<mode>|<nn>')`, and number them from 1. Prefixes: `Q` with the passage, `G` without. DeepSeek items use sheet number `00`.

### 6.1 `solve/solver_items_<set>.json` (the private map)

- **Read by:** `tools/ob_solve_blind.py`
- **Schema name:** `casalescence/optionb/solver_items/v1`

| Field | Type | Meaning |
|---|---|---|
| `items[].item_id` | string | |
| `items[].solver` | string | `deepseek-chat` or `claude-sonnet-subagent` |
| `items[].mode` | string | `with_passage` or `no_passage` |
| `items[].sheet` | string | `00` for DeepSeek; `<nn>` for a Claude sheet |
| `items[].question_id` | string | |
| `items[].shown` | list of whole numbers | option indexes in shown order |
| `items[].right_letter` | string | the letter the right option got |

```json
{"schema": "casalescence/optionb/solver_items/v1", "set": "practice",
 "items": [{"item_id": "Q0001", "solver": "claude-sonnet-subagent", "mode": "with_passage", "sheet": "01",
            "question_id": "V901.p1.LONG_BREAK", "shown": [3, 0, 5, 1, 2, 4], "right_letter": "B"}]}
```

### 6.2 `solve/deepseek_calls_<set>.jsonl`

- **Written by:** `tools/ob_solve_blind.py deepseek`. **Read by:** the same tool (to resume), `tools/ob_seal.py`.
- One line per call. Fields: `utc`, `item_id`, `mode`, `question_id`, `model` (the name asked for, `deepseek-chat`), `model_in_reply` (amendment A9), `usage` (object or null; amendment A11), `http_status`, `ok`, `error`, `prompt_sha256`, `reply_sha256`, `prompt`, `reply`.
- A question that already has a readable DeepSeek reply for a mode is not asked again.
- This log is one of the four that carry the DeepSeek token count (section 0). The step stops with `STOPPED_TOKEN_CAP` when a limit is reached.

### 6.3 `solve/claude_sheet_<set>_<mode>_<nn>.txt` (export)

- **Written by:** `tools/ob_solve_blind.py export`. It exports every candidate that has no Claude reply yet for that mode.
- **Read by:** a Claude Sonnet sub-agent that gets this text and nothing else. The `no_passage` sheet goes to a fresh sub-agent.
- Plain text. First the header from `PLAN_CONSTANTS.json` (`solver_sheet_header_with_passage` or `solver_sheet_header_no_passage`) with `<<SHEET_ID>>` filled as `<set>-<mode>-<nn>`. Then one empty line. Then the items, with one empty line between them.

```
SHEET practice-with_passage-01. Each item below holds a passage, a question and lettered options. …
…

=== ITEM Q0001 ===
Passage:
Every weekday for eleven years Oksana had weighed out flour at the same bench before dawn. …

Question: Oksana takes a desk job for two years and never weighs flour. Going only by the passage, which of these has most likely faded when she comes back?
A. hearing the radio on the shelf
B. stopping the scoop without a glance
C. reading numbers on the scale
D. tying her apron at the bench
E. calling out for the trays
F. finding her bench before dawn
=== END Q0001 ===
```

### 6.4 `solve/claude_answers_<set>_<mode>_<nn>.txt` (import)

- **Written by:** the operator saves the sub-agent's reply here, unchanged. **Read by:** `tools/ob_solve_blind.py import`.
- One line per item: the item id, one space, the reply. A reply is one capital letter, `MORE_THAN_ONE` or `NONE` (the last two only with the passage).
- A line that does not fit, a missing item or a repeated item is logged and counts as unreadable.
- **The model name (amendments A3 and A9).** The sub-agent is asked for with the pinned model id, `outside_services.claude_solver.model_id` (`claude-sonnet-5-5`). The operator reads the model name from the sub-agent's transcript and gives it to the `import` step as `--transcript-model <name>`, exactly as the transcript shows it. The step refuses to run without it. Operator decision C3 (2026-10-05, round 3): when the name is not exactly the pinned model id, the step stops with `TRANSCRIPT_MODEL_NOT_THE_PINNED_ID` and stores nothing. Otherwise it stores the name with every answer of that sheet (section 6.5).

```
Q0001 B
Q0002 MORE_THAN_ONE
```

### 6.5 `solve/solver_answers_<set>.json`

- **Read by:** `tools/ob_solve_blind.py decide`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/solver_answers/v1`

| Field | Type | Meaning |
|---|---|---|
| `answers[].item_id`, `.solver`, `.mode`, `.question_id` | strings | |
| `answers[].raw` | string | the reply as given |
| `answers[].readable` | true/false | |
| `answers[].picked_option_index` | whole number or null | 0 means the right option |
| `answers[].flag` | string or null | `MORE_THAN_ONE` or `NONE` |
| `answers[].source_sha256` | string | hash of the reply text or of the answer sheet |
| `answers[].model_in_reply` | string or null | DeepSeek answer: the model name in the reply, as in the call log. Claude answer: the model name the operator read from the sub-agent's transcript (section 6.4). |

### 6.6 `solve/key_check_<set>.json`

- **Read by:** `tools/ob_select.py`, `tools/ob_assemble.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/key_check/v1`

| Field | Type | Meaning |
|---|---|---|
| `rows[].question_id`, `.family` | strings | |
| `rows[].with_passage` | object | per solver: `RIGHT`, `WRONG`, `FLAG_MORE_THAN_ONE`, `FLAG_NONE` or `UNREADABLE` |
| `rows[].key_check_passed` | true/false | true only when both are `RIGHT` |
| `rows[].no_passage` | object | per solver: `RIGHT`, `WRONG` or `UNREADABLE` |
| `rows[].no_passage_passed` | true/false | false only when both are `RIGHT` |
| `rows[].survives` | true/false | both checks passed |
| `counts` | object | `checked`, `key_check_passed`, `no_passage_passed`, `survive`, each split by family |

```json
{"schema": "casalescence/optionb/key_check/v1", "set": "practice",
 "rows": [{"question_id": "V901.p1.LONG_BREAK", "family": "role_step",
           "with_passage": {"deepseek-chat": "RIGHT", "claude-sonnet-subagent": "RIGHT"}, "key_check_passed": true,
           "no_passage": {"deepseek-chat": "WRONG", "claude-sonnet-subagent": "RIGHT"}, "no_passage_passed": true, "survives": true}],
 "counts": {"checked": {"role_step": 1, "plain_fact": 0}, "survive": {"role_step": 1, "plain_fact": 0}}}
```

---

## 7. Selection (Step 6) and the keys as text

### 7.1 `select/selection_<set>.json`

- **Written by:** `tools/ob_select.py`
- **Read by:** `tools/ob_write_questions.py` (practice file only, and only `practice_setting_count` and the block `reserve`, for the reserve rule; amendment A8), `tools/ob_write_ordinary_notes.py` (only the list of passage ids that carry a task), `tools/ob_screen_notes.py`, `tools/ob_assemble.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/selection/v1`
- This file is the key as text: it says which option is right. It is sealed in step 3A (practice) or 3C (final). It holds no letters. Letters are set later (section 12).

| Field | Type | Meaning |
|---|---|---|
| `practice_setting_count` | whole number | 8 to 12 |
| `tasks[].task_id`, `.passage_id`, `.question_id` | strings | |
| `tasks[].family` | string | `role_step` or `plain_fact` |
| `tasks[].type`, `.form` | strings | `FACT` and `FACT` for a plain-fact task |
| `tasks[].question`, `.right` | strings | |
| `tasks[].wrong` | list | five, or three for a plain-fact task, in the writer's order |
| `tasks[].anchors` | list | as written |
| `tasks[].anchors_matched` | list | the anchors that passed the anchor check |
| `tasks[].right_is_single_longest`, `.right_is_single_shortest` | true/false | counted in words over all written options |
| `dropped[]` | list | `question_id`, `reason` |
| `counts` | object | `role_step_tasks`, `plain_fact_tasks`, `passages_with_a_task`, `passages_with_a_role_step_task`, `single_longest` `[part, whole]`, `single_shortest` `[part, whole]` |
| `floor` | object | practice only: `practice_role_step_min` (36), `practice_plain_fact_min` (20), `met` (true when both launch floors are met) |
| `reserve` | object | practice only: `role_step_target` (45), `plain_fact_target` (25), `target_met` (true when both targets are met), `settings_left` (12 minus `practice_setting_count`), `finished` (true when `target_met` is true or `settings_left` is 0) |

**When the practice set is final (review round 1).** This is the one reading; every program follows it.

- The reserve rule looks at `reserve`. While `reserve.finished` is false, the next reserve setting is moved: its questions are written (a new wave, section 4), and the check, the solvers and the selection run again with one more practice setting. The practice files are not sealed yet, so they may be written again.
- **Three tools read this block, in the same way (amendment A8).** `tools/ob_select.py` writes it and says "move the next reserve setting" while `reserve.finished` is false. `tools/ob_write_questions.py` adds the wave of the next reserve setting only when `reserve.finished` is false (section 4). `tools/ob_seal.py` refuses seal step 3A unless `reserve.finished` is true. None of the three reads `floor.met` for the reserve rule. `floor.met` only says "launch or not".
- `tools/ob_seal.py` refuses seal step 3A unless `reserve.finished` is true.
- After seal step 3A no practice file of sections 4 to 7.1 is written again.
- `floor.met` false with `reserve.finished` true means: do not launch. Seal step 3A may still be written, so that the practice questions are kept as evidence. Seal step 3B is then refused (section 7.2).
- The four numbers 36, 20, 45 and 25 come from `PLAN_CONSTANTS.json`: `launch_floor` and `split.reserve_target_…`.

`dropped[].reason`: `NOT_PICKED_BY_PAIR_RULE`, `SAME_RIGHT_THING`, `LAND_RULE`, `LENGTH_BACKSTOP_LONGEST`, `LENGTH_BACKSTOP_SHORTEST`, `PASSAGE_BARRED`.

```json
{"schema": "casalescence/optionb/selection/v1", "set": "practice", "practice_setting_count": 8,
 "tasks": [
  {"task_id": "V901.LONG_BREAK", "passage_id": "V901", "question_id": "V901.p1.LONG_BREAK", "family": "role_step", "type": "HABIT", "form": "LONG_BREAK",
   "question": "…", "right": "stopping the scoop without a glance", "wrong": ["…", "…", "…", "…", "…"],
   "anchors": ["Every weekday for eleven years", "her hands stopped the scoop"], "anchors_matched": ["Every weekday for eleven years"],
   "right_is_single_longest": false, "right_is_single_shortest": false},
  {"task_id": "V901.FACT", "passage_id": "V901", "question_id": "V901.p1.FACT", "family": "plain_fact", "type": "FACT", "form": "FACT",
   "question": "Where was the new radio?", "right": "on the shelf", "wrong": ["on the bench", "beside the scale", "in the tray rack"],
   "anchors": [], "anchors_matched": [], "right_is_single_longest": false, "right_is_single_shortest": false}],
 "dropped": [],
 "counts": {"role_step_tasks": 1, "plain_fact_tasks": 1, "passages_with_a_task": 1, "passages_with_a_role_step_task": 1, "single_longest": [0, 1], "single_shortest": [0, 1]},
 "floor": {"practice_role_step_min": 36, "practice_plain_fact_min": 20, "met": false},
 "reserve": {"role_step_target": 45, "plain_fact_target": 25, "target_met": false, "settings_left": 4, "finished": false}}
```

### 7.2 `select/split_fixed.json`

- **Written by:** `tools/ob_select.py`, once, after seal step 3A, when the reserve rule is finished: both reserve targets are met or all 4 reserve settings are used.
- **Read by:** `tools/ob_write_questions.py`, `tools/ob_check_questions.py`, `tools/ob_solve_blind.py`, `tools/ob_select.py` (all for `final`), `tools/ob_assemble.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/split_fixed/v1`
- No program handles the `final` set before this file exists and seal step 3B is written.

| Field | Type | Meaning |
|---|---|---|
| `practice_setting_count` | whole number | 8 to 12 |
| `practice_settings`, `final_settings` | lists of strings | |
| `history[]` | list | one row per count tried: `practice_setting_count`, `practice_role_step_tasks`, `practice_plain_fact_tasks`, `target_met` (both reserve targets) |
| `reserve_target_met` | true/false | `target_met` of the last row. False is allowed only with 12 settings. |
| `floor_met` | true/false | both practice launch floors are met by the last row (36 role-step and 20 plain-fact tasks). If false: do not launch. |
| `final_writer_passage_ids` | list | the K1 to K5 passages of the final settings |

Rules (review round 1):

- `tools/ob_select.py` refuses to write this file when an earlier row of `history` already has `target_met` true (a setting was moved that the rule did not ask for), or when the last row has `target_met` false and reserve settings are left.
- `tools/ob_seal.py` refuses seal step 3B unless `floor_met` is true.

```json
{"schema": "casalescence/optionb/split_fixed/v1", "practice_setting_count": 9,
 "practice_settings": ["a locksmith's van", "…", "a cheese cellar"], "final_settings": ["a barber shop", "…"],
 "history": [{"practice_setting_count": 8, "practice_role_step_tasks": 41, "practice_plain_fact_tasks": 27, "target_met": false},
             {"practice_setting_count": 9, "practice_role_step_tasks": 47, "practice_plain_fact_tasks": 31, "target_met": true}],
 "reserve_target_met": true, "floor_met": true, "final_writer_passage_ids": ["V904", "…"]}
```

---

## 8. Ordinary notes (Step 7, first half)

**Written by:** `tools/ob_write_ordinary_notes.py`. It runs for a set only after that set's seal step (3A/3B or 3C) exists.

**What is sent.** The request frame with one brief and one passage. Nothing else. One passage per call. Temperature 0.

### 8.1 `notes_ord/ordinary_notes_<set>.json`

- **Read by:** `tools/ob_check_support.py`, `tools/ob_screen_notes.py`, `tools/ob_assemble.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/ordinary_notes/v1`
- One object per passage that carries a task. Six notes per passage: two briefs, three lengths. Every version is kept.

| Field | Type | Meaning |
|---|---|---|
| `writer` | string | `deepseek-chat`: the model name asked for |
| `passages[].passage_id` | string | |
| `passages[].role_size_count`, `.passage_words`, `.passage_size_count` | whole numbers | the three inputs of the word target |
| `passages[].notes` | object | keys `ORD-INFORMED`, `ORD-FREE`; under each, keys `090`, `100`, `110` |
| `….target_words` | whole number | N |
| `….current` | 1 or 2 | the version in use |
| `….versions[]` | list | `version`, `text`, `words`, `size_count`, `prompt_sha256`, `reply_sha256`, `utc` |
| `….not_written` | null or object | A13: null while the note is written or still due. An object when the note was given up: `version` (1 or 2), `replies` (whole number, 2), `errors` (list of the reasons, in call order) |

The note text is the reply with white space removed at both ends and CR LF turned into LF. Nothing else is changed.

**A note the writer can not produce (A13, small faults; plan section 10, Step 7).** The numbers and words are in `PLAN_CONSTANTS.json` under `ordinary_notes.not_written_…`.

- A reply with `http_status` 200 that is empty after cleaning, or whose `finish_reason` is `length`, is not a note. Its call log line has `ok` false and the `error` `REPLY_EMPTY` or `REPLY_CUT_OFF`.
- The tool asks for that note once more, in a later run of the same step. Never in the same run.
- When the call log holds 2 such lines for one note id, the tool asks no more. It sets `not_written` for that note. The passage is dropped for every group (section 9.5: `DROPPED_NOTE_NOT_WRITTEN`).
- Operator decision C6 (2026-10-05, round 3): a call log line with `http_status` 400, 404 or 422 is counted like such a line, because the same call would be refused again, and its reason in `not_written.errors` is `HTTP_400`, `HTTP_404` or `HTTP_422`; a line with `http_status` 429 or 500 to 599 is not counted, and the note is asked for again later.
- A line with another `http_status`, or with no answer, is not counted.
- **The guard.** At most 3 passages of a set are dropped this way: the first ones that meet the rule, in the order of the call log. If one more passage would be dropped, the tool sets no further `not_written` and stops with the status `STOPPED_TOO_MANY_NOTES_NOT_WRITTEN` (exit code 2). Then: stop and report.
- The tool ends with exit code 0 when every note due in the step is written or given up.

```json
{"schema": "casalescence/optionb/ordinary_notes/v1", "set": "practice", "writer": "deepseek-chat",
 "passages": [{"passage_id": "V901", "role_size_count": 78, "passage_words": 45, "passage_size_count": 52,
   "notes": {"ORD-INFORMED": {
               "090": {"target_words": 61, "current": 1, "not_written": null, "versions": [{"version": 1, "text": "Oksana has weighed flour at this bench …", "words": 58, "size_count": 66, "prompt_sha256": "ab…", "reply_sha256": "cd…", "utc": "2026-10-08T09:00:00Z"}]},
               "100": {"target_words": 68, "current": 1, "versions": [{"version": 1, "text": "…", "words": 70, "size_count": 79, "prompt_sha256": "…", "reply_sha256": "…", "utc": "…"}]},
               "110": {"target_words": 74, "current": 2, "versions": [{"version": 1, "text": "…", "words": 77, "size_count": 88, "prompt_sha256": "…", "reply_sha256": "…", "utc": "…"},
                                                                    {"version": 2, "text": "…", "words": 75, "size_count": 85, "prompt_sha256": "…", "reply_sha256": "…", "utc": "…"}]}},
             "ORD-FREE": {"090": {"target_words": 61, "current": 1, "versions": []}, "100": {"target_words": 68, "current": 1, "versions": []}, "110": {"target_words": 74, "current": 1, "versions": []}}}}]}
```

(The empty `versions` lists in the example only keep it short. A real file has at least version 1 everywhere, or `not_written` set. The example shows `not_written` in one slot only; a real file has it in every slot.)

### 8.2 `notes_ord/ordinary_calls_<set>.jsonl`

- **Read by:** `tools/ob_write_ordinary_notes.py` (to resume), `tools/ob_seal.py`.
- One line per call. Fields: `utc`, `note_id`, `frame` (`first` or `rewrite`), `model` (the name asked for, `deepseek-chat`), `model_in_reply` (amendment A9), `usage` (object or null; amendment A11), `http_status`, `ok`, `error`, `prompt_sha256`, `reply_sha256`, `prompt`, `reply`.
- This log is one of the four that carry the DeepSeek token count (section 0). The tool stops with `STOPPED_TOKEN_CAP` when a limit is reached.
- A13: for a reply that is not a note, `ok` is false and `error` is `REPLY_EMPTY` or `REPLY_CUT_OFF` (section 8.1). These lines, and by operator decision C6 the lines with `http_status` 400, 404 or 422, are the count of the rule "a note the writer can not produce".

---

## 9. Support check (Step 7, second half)

**Written by:** `tools/ob_check_support.py`. Steps: `gemini` (calls the service) and `decide`. The steps `export` and `import` are gone (amendment A2).

**Batches.** Sort the passage ids of the set, shuffle them with `random.Random(<support_batch_order>)`, and cut them into groups of 2. A batch holds the six current notes of each of its passages: 12 items. Rewritten notes are checked in a second round, in batches of up to 12 items, in note-id order.

**A passage with a note that was given up (A13).** A round starts only when every note due is written or given up (`not_written` set, section 8.1). A passage that has a note with `not_written` set is put in no batch from then on: none of its notes is sent to the checker any more. Its status is `DROPPED_NOTE_NOT_WRITTEN` (section 9.5).

**What is sent.** For each item: a neutral item id, the passage, the note. Nothing else. The checker is not told the group or the length.

**One checker (amendment A2).** The checker is Gemini `gemini-3.1-flash-lite`, for both sets and both rounds. There is no fallback checker and no Claude checker. The fallback rule of review round 1, its 24-hour clock and its sheets are deleted. If Gemini refuses a call, the build waits: the `gemini` step is run again later, from its checkpoint. In exact terms:

- **Daily-cap refusal.** A call log line with `http_status` 429 whose error text matches `daily_cap_error_regex` (any letter case). Only such a line gets the mark `DAILY_CAP_STOP: ` at the start of its `error` field. The `gemini` step then stops with the status `STOPPED_DAILY_CAP`.
- **Rate refusal.** Any other line with `http_status` 429. It never gets the mark. After the allowed waits the `gemini` step stops with the status `STOPPED_RATE_LIMIT`.
- **After either stop.** The checkpoint is kept. The same step is run again later. No batch ever moves to another checker. A refused call is not counted as an attempt.

The files of 9.1, 9.2 and 9.3 are read by `tools/ob_check_support.py` itself (to resume) and by `tools/ob_seal.py`.

### 9.1 `support/support_state_<set>.json` (the checkpoint)

- **Schema name:** `casalescence/optionb/support_state/v1`
- Fields: `model` (the name asked for), `rounds[]` with `round` (1 or 2) and `batches[]` (`batch`, `item_ids`, `status`: `PENDING`, `DONE` or `UNREADABLE`; `attempts`), `cap_stops_utc` (the times of the daily-cap refusals only), `first_cap_stop_utc` (string or null), `complete`.
- The status `MOVED_TO_FALLBACK` and the object `fallback` of review round 1 are gone (amendment A2).

```json
{"schema": "casalescence/optionb/support_state/v1", "set": "final", "model": "gemini-3.1-flash-lite",
 "rounds": [{"round": 1, "batches": [{"batch": 0, "item_ids": ["N0001", "…"], "status": "DONE", "attempts": 1},
                                     {"batch": 1, "item_ids": ["N0013", "…"], "status": "PENDING", "attempts": 0}]}],
 "cap_stops_utc": ["2026-10-08T10:00:00Z"], "first_cap_stop_utc": "2026-10-08T10:00:00Z",
 "complete": false}
```

### 9.2 `support/support_items_<set>.json` (the private map)

- **Schema name:** `casalescence/optionb/support_items/v1`
- Fields: `items[]` with `item_id` (`N0001` …), `note_id`, `round`, `checker` (always `gemini-3.1-flash-lite`), `sheet` (always `00`).

### 9.3 `support/support_calls_<set>.jsonl`

- One line per Gemini call. Fields: `utc`, `model` (the name asked for), `model_in_reply` (amendment A9), `round`, `batch`, `item_ids`, `attempt`, `http_status`, `ok`, `error`, `prompt_sha256`, `reply_sha256`, `prompt`, `reply`.

### 9.4 (removed by amendment A2)

There is no Claude sheet and no Claude answer file for the support check. The files `support/claude_support_sheet_<set>_<nn>.txt` and `support/claude_support_answers_<set>_<nn>.txt` do not exist. The constant `briefs.support_sheet_header` is deleted. This number stays, so that section 9.5 keeps its number.

### 9.5 `support/support_results_<set>.json`

- **Read by:** `tools/ob_write_ordinary_notes.py` (to know which notes to write again), `tools/ob_screen_notes.py`, `tools/ob_assemble.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/support_results/v1`

| Field | Type | Meaning |
|---|---|---|
| `results[].note_id`, `.item_id`, `.checker` | strings | `checker` is always `gemini-3.1-flash-lite` (amendment A2) |
| `results[].round` | 1 or 2 | |
| `results[].verdict` | string | `PASS`, `FAIL` or `UNREADABLE` |
| `passages[].passage_id` | string | |
| `passages[].status` | string | `ALL_PASS`, `REWRITE_NEEDED`, `DROPPED_SECOND_FAILURE`, `DROPPED_NOTE_NOT_WRITTEN` (A13) or `UNCHECKED` |
| `passages[].rewrite_note_ids` | list | notes whose version 1 failed |
| `counts` | object | notes checked, passed, failed once, failed twice; passages dropped; A13: `passages_dropped_note_not_written` |

An item with no readable verdict is asked once more. If it is still unreadable it counts as `FAIL`.

**`DROPPED_NOTE_NOT_WRITTEN` (A13).** The passage has a note with `not_written` set in `notes_ord/ordinary_notes_<set>.json` (section 8.1). It is dropped for every group, like a passage with `DROPPED_SECOND_FAILURE`. A set is ready for seal step 4 when every passage has the status `ALL_PASS`, `DROPPED_SECOND_FAILURE` or `DROPPED_NOTE_NOT_WRITTEN`.

```json
{"schema": "casalescence/optionb/support_results/v1", "set": "practice",
 "results": [{"note_id": "V901|ORD-INFORMED|110|v1", "item_id": "N0003", "checker": "gemini-3.1-flash-lite", "round": 1, "verdict": "FAIL"},
             {"note_id": "V901|ORD-INFORMED|110|v2", "item_id": "N0101", "checker": "gemini-3.1-flash-lite", "round": 2, "verdict": "PASS"}],
 "passages": [{"passage_id": "V901", "status": "ALL_PASS", "rewrite_note_ids": ["V901|ORD-INFORMED|110|v1"]}],
 "counts": {"notes_checked": 7, "failed_once": 1, "failed_twice": 0, "passages_dropped": 0}}
```

---

## 10. Answer-leak screen

### 10.1 `screen/leak_screen_<set>.json`

- **Written by:** `tools/ob_screen_notes.py`
- **Read by:** `tools/ob_assemble.py`, `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/leak_screen/v1`
- It screens every passage that carries a task and was not dropped by the support check. For each: FILLER, ROLE, MIXED, QUOTES-ONLY (frame text only) and both ordinary groups in all three lengths (current version), against every selected task of that passage.
- A13: "dropped by the support check" means the status `DROPPED_SECOND_FAILURE` or `DROPPED_NOTE_NOT_WRITTEN` in `support/support_results_<set>.json`.
- A13: the frame text of a ROLE or MIXED note holds its sayings lines whole (section 3.1). Rules a to d test them like every other frame word. An option whose whole text stands inside a sayings line, and not in the passage, is a rule c hit.

| Field | Type | Meaning |
|---|---|---|
| `passages[].passage_id` | string | |
| `passages[].hit` | true/false | true drops the passage for every group |
| `passages[].hits[]` | list | `group`, `length` (string or null), `rule` (`a`, `b`, `c` or `d`), `task_id` (string or null), `detail` |
| `counts` | object | `passages_screened`, `passages_hit`, `hits_by_rule` |

```json
{"schema": "casalescence/optionb/leak_screen/v1", "set": "practice",
 "passages": [{"passage_id": "V901", "hit": false, "hits": []},
              {"passage_id": "V905", "hit": true, "hits": [{"group": "ORD-FREE", "length": "110", "rule": "c", "task_id": "V905.GOES_FOR", "detail": "holds the option text: browsing old charts at a stall"}]}],
 "counts": {"passages_screened": 2, "passages_hit": 1, "hits_by_rule": {"a": 0, "b": 0, "c": 1, "d": 0}}}
```

### 10.2 The report-only run (review round 1)

- **Command:** `tools/ob_screen_notes.py --set practice --report-only`. `--report-only` is refused with any other value of `--set`.
- **Needs:** seal steps 1, 2, 3A and 3B, and a finished practice support check: `support/support_results_practice.json` exists and no passage has the status `REWRITE_NEEDED` or `UNCHECKED`. It does not need seal step 4.
- **Does:** the same screen as 10.1, with the same rules a to d, on the practice notes as they then stand.
- **Prints:** `passages_screened`, `passages_hit`, `hits_by_rule`, and the practice role-step and plain-fact tasks that would be left, beside the two practice launch floors.
- **Writes:** nothing. No file, no `.partial` file.
- It is an early look, so that the hit rate is known before any final question is written. The screen of record is the full run of 10.1 after seal step 4. A hit, in either run, never causes a note to be written again.

---

## 11. Removal log

### 11.1 `removal_log.json`

- **Written by:** `tools/ob_assemble.py`, from the files of sections 4 to 10. No other program adds to it.
- **Read by:** `tools/ob_seal.py`, the reviewer, the owner
- **Schema name:** `casalescence/optionb/removal_log/v1`

| Field | Type | Meaning |
|---|---|---|
| `entries[].set` | string | |
| `entries[].step` | string | see the list below |
| `entries[].program` | string | the program whose rule removed it |
| `entries[].object` | string | `question`, `task`, `note` or `passage` |
| `entries[].id` | string | |
| `entries[].rule` | string | a reason code of that step |
| `entries[].detail` | string | |
| `counts_by_step_and_rule` | object | |
| `survival` | object | per set: a list of rows `filter`, `role_step`, `plain_fact`, in filter order |
| `final_counts` | object | `final_role_step_tasks`, `final_plain_fact_tasks`, `final_passages_with_a_role_step_task`, `practice_role_step_tasks`, `practice_plain_fact_tasks` |
| `launch_floor_met` | true/false | |
| `tier` | string | `AS_IT_STANDS`, `EXPLORATORY` or `NO_LAUNCH` |
| `estimated_padding` | object | per group, an estimate from size counts; labeled an estimate; no rule uses it |

`step` values, in order: `STEP_1_WRITER`, `STEP_2_FORM_CHECK`, `STEP_3A_ANCHOR_CHECK`, `STEP_3B_OPTION_CHECK`, `STEP_4_KEY_CHECK`, `STEP_5_NO_PASSAGE_CHECK`, `STEP_6_SELECTION`, `STEP_6_LENGTH_BACKSTOP`, `STEP_7_SUPPORT_CHECK`, `STEP_7_LEAK_SCREEN`.

`survival` filter names, in order: `written for an open form`, `form check`, `anchor check`, `option check`, `key check`, `no-passage check`, `selection`, `length backstop`, `support check`, `answer-leak screen`.

A13: a passage that is dropped because a note could not be written (section 8.1) is logged under the step `STEP_7_SUPPORT_CHECK`, with the program `tools/ob_write_ordinary_notes.py`, the object `passage` and the rule `DROPPED_NOTE_NOT_WRITTEN`. The `survival` row `support check` counts it as removed. No step name and no filter name was added.

```json
{"schema": "casalescence/optionb/removal_log/v1",
 "entries": [{"set": "practice", "step": "STEP_2_FORM_CHECK", "program": "tools/ob_check_questions.py", "object": "question", "id": "V902.p1.GOES_FOR", "rule": "OPTION_LENGTH_SPREAD", "detail": "lengths 4 to 8 words"}],
 "counts_by_step_and_rule": {"STEP_2_FORM_CHECK": {"OPTION_LENGTH_SPREAD": 1}},
 "survival": {"practice": [{"filter": "written for an open form", "role_step": 70, "plain_fact": 58}, {"filter": "form check", "role_step": 61, "plain_fact": 55}]},
 "final_counts": {"final_role_step_tasks": 128, "final_plain_fact_tasks": 119, "final_passages_with_a_role_step_task": 96, "practice_role_step_tasks": 41, "practice_plain_fact_tasks": 30},
 "launch_floor_met": true, "tier": "EXPLORATORY",
 "estimated_padding": {"note": "an estimate from size counts, not from the tokenizer", "ORD-INFORMED": "4.1", "ORD-FREE": "6.3"}}
```

---

## 12. Assembled prompt parts and lettered keys

**Written by:** `tools/ob_assemble.py`. It keeps a passage only if it carries a task, passed the support check and was not hit by the answer-leak screen. (A13: a passage with the status `DROPPED_SECOND_FAILURE` or `DROPPED_NOTE_NOT_WRITTEN` did not pass the support check.) It then sets the letters (rule `selection.letters` in `PLAN_CONSTANTS.json`). The prompt parts are packed as two large files, not one file per passage.

**Right letters (review round 1).** Per set, per task family (`role_step`, `plain_fact`) and per level:

1. For each type of the family, in the order of `types_in_order` (the plain-fact family has the one type `FACT`): sort the tasks of that type by id and shuffle them with `random.Random('<letters>|<set>|<type>|<level>')`.
2. Join the shuffled lists, type after type, into one list.
3. The task at place `i` of the joined list, counted from 0, gets the right letter `letters[i % shown]`. The count does not start again at `A` for a new type. `shown` is 4 at level 1 and 6 at level 2 for a role-step task, and 4 for a plain-fact task (level 1 only).
4. The other shown options fill the other letters in an order drawn with `random.Random('<letters>|<task id>|<level>')`.

Check, in the same tool: for each set, family and level, the counts of right letters differ by at most one between any two shown letters, inside every type and over the whole family. If not, the tool stops with `LETTERS_NOT_BALANCED`.

### 12.1 `prompts/prompt_parts_practice.json` and `prompts/prompt_parts_final.json`

- **Read by:** `job/runner_b1.py` (all commands), `job/analysis_b1.py` (for the word-matching view), `tools/ob_seal.py`
- **Schema name:** `casalescence/optionb/prompt_parts/v1`
- It never says which option is right. (Exception: the practice file's `answer_given` notes, which are the practice-only positive control.)

| Field | Type | Meaning |
|---|---|---|
| `set` | string | |
| `passages[].passage_id`, `.text` | strings | |
| `passages[].notes.FILLER` | string | the filler sentence |
| `passages[].notes.ROLE`, `.MIXED`, `.QUOTES-ONLY` | strings | notes text without padding line |
| `passages[].notes.ORD-INFORMED`, `.ORD-FREE` | objects | keys `090`, `100`, `110`: the current note texts |
| `tasks[].task_id`, `.passage_id`, `.family`, `.question` | strings | |
| `tasks[].options` | object | key `"1"` and, for a role-step task, `"2"`: a list of `{"letter", "text"}` in letter order |
| `tasks[].groups` | list | the must-run groups of this task, in order |
| `answer_given[]` | list | practice file only: `task_id`, `level`, `note` |

```json
{"schema": "casalescence/optionb/prompt_parts/v1", "set": "practice",
 "passages": [{"passage_id": "V901", "text": "Every weekday for eleven years Oksana …",
   "notes": {"FILLER": "No notes are provided for this passage.",
             "ROLE": "<canon line ^1>\n<sayings line ^1>\n<canon line ^7>\n<sayings line ^7>\n- ^7 Rhythm: \"Every weekday for eleven years\". …",
             "MIXED": "<canon line ^1>\n<sayings line ^1>\n<canon line ^4>\n<sayings line ^4>\n- ^4 Vibration: \"Every weekday for eleven years\". …",
             "QUOTES-ONLY": "- \"Oksana\".\n- \"Every weekday for eleven years\". Supporting quote: \"…\"",
             "ORD-INFORMED": {"090": "…", "100": "…", "110": "…"},
             "ORD-FREE": {"090": "…", "100": "…", "110": "…"}}}],
 "tasks": [{"task_id": "V901.LONG_BREAK", "passage_id": "V901", "family": "role_step", "question": "…",
            "options": {"1": [{"letter": "A", "text": "tying her apron at the bench"}, {"letter": "B", "text": "stopping the scoop without a glance"}, {"letter": "C", "text": "calling out for the trays"}, {"letter": "D", "text": "hearing the radio on the shelf"}],
                        "2": [{"letter": "A", "text": "…"}, {"letter": "B", "text": "…"}, {"letter": "C", "text": "…"}, {"letter": "D", "text": "…"}, {"letter": "E", "text": "…"}, {"letter": "F", "text": "…"}]},
            "groups": ["NONE", "FILLER", "ROLE", "MIXED", "ORD-INFORMED", "ORD-FREE", "QUOTES-ONLY"]},
           {"task_id": "V901.FACT", "passage_id": "V901", "family": "plain_fact", "question": "Where was the new radio?",
            "options": {"1": [{"letter": "A", "text": "on the shelf"}, {"letter": "B", "text": "on the bench"}, {"letter": "C", "text": "beside the scale"}, {"letter": "D", "text": "in the tray rack"}]},
            "groups": ["NONE", "FILLER", "ROLE", "MIXED", "ORD-INFORMED", "ORD-FREE"]}],
 "answer_given": [{"task_id": "V901.LONG_BREAK", "level": "1", "note": "The right answer to the question is B."},
                  {"task_id": "V901.LONG_BREAK", "level": "2", "note": "The right answer to the question is E."}]}
```

### 12.2 `keys_practice/keys_practice.json` and `keys_final/keys_final.json`

- **Read by:** `job/gate_b1.py` (practice keys only), `job/analysis_b1.py` (final keys; and practice keys in the self-test), `job/runner_b1.py` in `selftest` and `run-practice` (practice keys only), `tools/ob_seal.py`
- **Never read by:** `job/runner_b1.py run-final`. That command is given the prompt folder only.
- **Schema name:** `casalescence/optionb/keys/v1`
- The final keys sit in their own folder, `keys_final/`.

| Field | Type | Meaning |
|---|---|---|
| `set` | string | |
| `keys` | object | per task id: per level (`"1"`, and `"2"` for a role-step task) the right letter |

```json
{"schema": "casalescence/optionb/keys/v1", "set": "practice",
 "keys": {"V901.LONG_BREAK": {"1": "B", "2": "E"}, "V901.FACT": {"1": "A"}}}
```

### 12.3 `keys_practice/task_meta_practice.json` and `keys_final/task_meta_final.json`

- **Read by:** `job/analysis_b1.py`, `job/gate_b1.py` (practice), `tools/ob_seal.py`. Never by a command that calls model B on final tasks.
- **Schema name:** `casalescence/optionb/task_meta/v1`

| Field | Type | Meaning |
|---|---|---|
| `tasks` | object | per task id, the fields below |
| `.passage_id`, `.family`, `.type`, `.form`, `.kind`, `.setting` | strings | |
| `.right_text` | string | |
| `.anchors_matched` | list | |
| `.type_has_leftover` | true/false | an only-one-team entry on the type's Noetics (sub-view 2); false for a plain-fact task |
| `.passage_any_leftover_2_to_9` | true/false | sub-view 3 |

```json
{"schema": "casalescence/optionb/task_meta/v1", "set": "practice",
 "tasks": {"V901.LONG_BREAK": {"passage_id": "V901", "family": "role_step", "type": "HABIT", "form": "LONG_BREAK", "kind": "K5", "setting": "a swimming pool",
                               "right_text": "stopping the scoop without a glance", "anchors_matched": ["Every weekday for eleven years"],
                               "type_has_leftover": false, "passage_any_leftover_2_to_9": true}}}
```

### 12.4 `review/review_pack.json`

- **Written by:** `tools/ob_assemble.py`. **Read by:** the outside reviewer's tool, the owner.
- **Schema name:** `casalescence/optionb/review_pack/v1`
- All practice tasks, and a seeded 10% of the final tasks: `random.Random(<review_sample>).sample(sorted final task ids, ceil(0.10 × count))`. For each: passage, question, options, right option, type, and the six note texts.

---

## 13. Job programs and the known examples

| File | Written by | Read by |
|---|---|---|
| `job/runner_b1.py` | its builder | the guest; seal step 6 |
| `job/scorer_v0_1_1.py` | its builder | `job/runner_b1.py`, `job/gate_b1.py`, `job/analysis_b1.py` |
| `job/gate_b1.py` | its builder | `job/runner_b1.py` |
| `job/analysis_b1.py` | its builder | `job/runner_b1.py` |
| `job/scorer_examples_v0_1_1.json` | the scorer's builder | `job/runner_b1.py selftest` |

### 13.1 `job/scorer_examples_v0_1_1.json`

- **Schema name:** `casalescence/scorer-known-examples/v0.1.1`
- The same shape as `scorer_examples_v0_1.json`. The 30 old examples are copied unchanged (`S01` … `S30`). Ten are added (`S31` … `S40`), as listed in the plan, section 17.2.

| Field | Type |
|---|---|
| `rules` | string |
| `expected_decided_by` | string |
| `examples[].id` | string |
| `examples[].raw_text` | string |
| `examples[].cut_off` | true/false |
| `examples[].task_answer` | whole number, string or list of strings |
| `examples[].expected` | one of the five categories |

```json
{"schema": "casalescence/scorer-known-examples/v0.1.1", "rules": "03_SCORER_RULES_v0_1.md plus: a repeated key is FORMAT_FAIL",
 "expected_decided_by": "hand, from the written rules",
 "examples": [{"id": "S39", "raw_text": "{\"answer\": \"A\", \"answer\": \"B\"}", "cut_off": false, "task_answer": "B", "expected": "FORMAT_FAIL"}]}
```

### 13.2 What the scorer offers

`scorer_v0_1_1.py` keeps the names of `tools/scorer_v0_1.py`: `CATEGORIES`, `read_answer(raw_text, cut_off)` → `(category or None, value)`, `categorize(raw_text, task_answer, cut_off)`, `primary_score`, `secondary_category`, `tally`. The gate and analysis programs work out "clean" themselves: `read_answer` gave a value, the value is a string, and it is one of the letters shown.

---

## 14. The package the job gets

The package is a folder tree inside `source.zip`. Its files keep the paths they have under `optionb/`, with two exceptions. The plan sits at the package root. `tools/verdict.py` keeps the path it has under `CASALESCENCE_NOETICS_v0_1/`, which is `tools/verdict.py`.

```
08_OPTION_B_PLAN_v1_0.md
PLAN_CONSTANTS.json
FILE_FORMATS.md
SEAL_OPTIONB.jsonl                      (as it stood when source.zip was built: after seal step 6, or after the last 6R line)
tools/verdict.py                        (the frozen source of plan section 3; review round 1)
job/runner_b1.py
job/scorer_v0_1_1.py
job/gate_b1.py
job/analysis_b1.py
job/scorer_examples_v0_1_1.json
prompts/prompt_parts_practice.json
prompts/prompt_parts_final.json
keys_practice/keys_practice.json
keys_practice/task_meta_practice.json
keys_final/keys_final.json
keys_final/task_meta_final.json
```

That is 16 files.

**Why `tools/verdict.py` is in the package (review round 1).** The analysis program needs its function `content()` for three views that the plan says are always printed: `sub_views.word_rule_misses_under_ROLE`, `extra_views.word_matching_rule` and `extra_views.anchor_in_ordinary_note` (section 17.9). The rules:

- Seal step 1 gives the file the `package_path` `tools/verdict.py`. So the self-test check `package_matches_seal` covers it.
- `job/analysis_b1.py` lists it among the package files it needs. It imports `content()` only after the file's sha256 equals `sources.verdict_program.sha256` in `PLAN_CONSTANTS.json`. It never copies or rewrites the function.
- No other file under `tools/` is in the package. The eleven `tools/ob_*.py` programs are sealed with `package_path` null.

The controller's builder adds what the guest needs beside it (the requirements file, the bundle manifest, the contract, the authority record). Those are not part of this list.

The pre-check job and the GPU job get the same package, byte for byte. The pre-check payload holds the six small model files (no `model.safetensors`). The GPU payload holds all seven.

The development test (amendment A10) gets a package of the same layout with made-up content. Section 20 describes it. It is never the package of this section.

---

## 15. The seal file

### 15.1 `SEAL_OPTIONB.jsonl`

- **Written by:** `tools/ob_seal.py`, one line per seal step, only ever added at the end.
- **Read by:** every `tools/ob_*.py` program (it checks the steps it depends on), `job/runner_b1.py selftest` (package hashes match the seal)
- **Schema name of a line:** `casalescence/optionb/seal-step/v1`

| Field | Type | Meaning |
|---|---|---|
| `n` | whole number | 1, 2, 3, … in file order |
| `step` | string | one of the nine steps in the list below, or a repair step (15.2) |
| `utc` | string | |
| `files[]` | list | `path` (relative to `CASALESCENCE_NOETICS_v0_1/`), `package_path` (string, or null when the file is not in the package), `bytes`, `sha256`. A13: one sealed file lies outside that folder, the source of the sayings. Its `path` is `../../docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, counted from the same folder, two steps up. |
| `values` | object | small facts sealed with the step |
| `who_could_open` | string | the custody note for these files |
| `previous_line_sha256` | string or null | sha256 of the bytes of the line before, without its LF; null on line 1 |
| `made_by` | object | program, its sha256, utc |

`tools/ob_seal.py` refuses a step that is out of order. Before adding a line it hashes every sealed file again and refuses if one differs from its values in force (see "The hash in force" in 15.2).

Steps and their files:

| `step` | Files |
|---|---|
| `1_PLAN_AND_SOURCES` | `08_OPTION_B_PLAN_v1_0.md`, `optionb/PLAN_CONSTANTS.json`, `optionb/FILE_FORMATS.md`, the six source files of plan section 3 (A13: they are the six names under `seal.sources_sealed_in_step_1` in `PLAN_CONSTANTS.json`; the sixth is the source of the sayings, `../../docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, with `package_path` null), `optionb/elig/exclusions.json`, `optionb/elig/eligibility.json`, and the eleven tools listed under `seal.tools_sealed_in_step_1` in `PLAN_CONSTANTS.json`. `values`: the practice and reserve settings, the scorer version. |
| `2_ROLE_NOTES` | `optionb/notes_role/role_notes.json`, `optionb/notes_role/owner_sample_20.json` |
| `3A_PRACTICE_QUESTIONS_AND_KEYS` | every `practice` file of sections 4 to 7.1 |
| `3B_PRACTICE_SET_FIXED` | `optionb/select/split_fixed.json` |
| `3C_FINAL_QUESTIONS_AND_KEYS` | every `final` file of sections 4 to 7.1 |
| `4_ORDINARY_NOTES` | every file of sections 8 and 9, both sets |
| `5_PROMPT_PARTS_AND_REMOVAL_LOG` | the files of sections 10.1, 11 and 12 |
| `6_PROGRAMS` | the five files of section 13 |
| `7_PRECHECK` | `optionb/OUTCOME_STATUS_TABLE.json` (section 19; `package_path` null). `values`: the same five as before: `source_zip_sha256`, `selftest_status`, `prompt_list_sha256`, `padding_plan_sha256`, `selftest_json_sha256` |

Rules added in review round 1, and three added by A13. Each is a refusal of `tools/ob_seal.py`; nothing is written.

| Step | Refused unless |
|---|---|
| 1 | Each of the eleven tools is there. `package_path` is null for each of them. `tools/verdict.py` gets the `package_path` `tools/verdict.py`. `made_by.sha256` in `elig/exclusions.json` and in `elig/eligibility.json` equals the sha256 of `tools/ob_eligibility.py` that this step seals. `outside_services.claude_solver.model_id` in `PLAN_CONSTANTS.json` is a string, not null. |
| 1 | A13: each of the six source files is there with the size and sha256 that `sources` gives it. The source of the sayings is one of them. |
| 2 | A13: `canon.sayings_sha256` in `notes_role/role_notes.json` equals `sources.canonical_sayings.sha256`, as `canon.sha256` equals `sources.labeling_guide.sha256`. Both files of the step name the sayings file under `inputs` with that sha256. |
| 3A | `select/selection_practice.json` has `reserve.finished` true (section 7.1). |
| 3B | `select/split_fixed.json` has `floor_met` true: both practice launch floors (section 7.2). |
| 4 | A13: every passage of `support/support_results_practice.json` and of `support/support_results_final.json` has the status `ALL_PASS`, `DROPPED_SECOND_FAILURE` or `DROPPED_NOTE_NOT_WRITTEN` (section 9.5). |
| 7 | As before: the pre-check ended with `SELFTEST_PASS` in `precheck` mode and its check `package_matches_seal` is recorded as passed. New: `optionb/OUTCOME_STATUS_TABLE.json` exists and keeps every limit of `spec_sheet_status.limits` in `PLAN_CONSTANTS.json` (section 19). Added by amendment A8: the four receipt and package checks below. |

**Step 7 reads the receipt of the pre-check job (amendment A8).** The command is `tools/ob_seal.py step 7 --receipt FILE --selftest-json FILE --source-zip FILE`. `--receipt` is the job's `supervisor_receipt.json`, copied unchanged out of its result archive. The step is refused unless all four hold:

1. The receipt's `precheck_kind` is `SEALED_PACKAGE`.
2. The receipt's `status` is `PRECHECK_COMPLETE_SELFTEST_PASS`.
3. The receipt's block `seal_step_7_values` equals the five values the step works out from the given `selftest.json` and `source.zip`: `source_zip_sha256`, `selftest_status`, `prompt_list_sha256`, `padding_plan_sha256`, `selftest_json_sha256`.
4. The given `source.zip` holds the seal file up to its last program line. In exact terms: its member `SEAL_OPTIONB.jsonl` is, byte for byte, the real seal file from its first line to its last program line. A program line is the line `6_PROGRAMS` or a line `6R_PROGRAMS_REPAIRED`. No program line follows it in the real seal file. The step opens the zip with the standard `zipfile` module and reads this one member only.

Why: the pre-check kit builds three kinds of job, `SEALED_PACKAGE`, `REHEARSAL` and `DEVELOPMENT_TEST`. All three return a `selftest.json` in `precheck` mode. A seal step is never written twice. With these checks a rehearsal, or a test on made-up data, can never be sealed as step 7. The receipt of a job that is not of kind `SEALED_PACKAGE` holds no block `seal_step_7_values`. The seal copy inside a made-up package is not the start of the real seal file.

**The tools are sealed files.** After seal step 1 a tool whose bytes differ from its values in force makes every seal check fail with `SEALED_FILE_CHANGED`: in `tools/ob_seal.py` and in the seal check of every other tool. No extra self-check is needed. The way out is a `TR_TOOLS_REPAIRED` line inside its window (15.2), or putting the sealed bytes back.

### 15.2 Repair lines (review round 1; narrowed by amendment A5)

Two more values of `step`. A repair line has the same fields as any line. It is added at the end, like any line. `n` counts every line.

| `step` | Window: may be written only | At most |
|---|---|---|
| `6R_PROGRAMS_REPAIRED` | after `6_PROGRAMS` and before `7_PRECHECK`, and only after a failed pre-check job on the sealed package. So before any call to model B. | 2 lines (`repairs.job_programs.max_repairs`) |
| `TR_TOOLS_REPAIRED` | after line 1 and while no final question exists: no `final` file of sections 4 to 7.1 exists, and the seal file has no line `3C_FINAL_QUESTIONS_AND_KEYS` | no fixed number |

**Outside its window (amendment A5).** `tools/ob_seal.py` writes no repair line and stops with `REPAIR_OUTSIDE_ITS_WINDOW`. A fault in a tool after the first final question exists, or in a job program after seal step 7, means: stop, report, a new reviewed plan version.

**A plan-only run closes the tool window (A13, small faults).** A run of the final question writer with `--max-calls 0` writes `questions/writer_state_final_<pass>.json` and `questions/raw_questions_final_<pass>.json`. They are `final` files of section 4. So such a run closes the window of `TR_TOOLS_REPAIRED`. It is not run before the practice set is fully done (plan section 11.1).

**What a repair never changes (amendment A5).** A repair changes program code only. Neither kind of repair may change the plan, the constants, a brief, a threshold, a key, a task or a note. Each repair needs its own review record (15.3).

**Order rule.** Leave the repair lines out. What is left must be the nine steps in their order, or a start of that order. No step is written twice.

**The hash in force.** For a path that more than one line lists, the latest line gives the size and the sha256 in force. Only a repair line may list a path that an earlier line lists. Every check "no sealed file has changed", in `tools/ob_seal.py`, in every other tool and in the runner's self-test, compares each path with its values in force. The package holds, for each `package_path`, the file in force.

**The repair folder.** `optionb/repairs/<repair id>/`. The repair id is `6R1` or `6R2` for job programs, and `TR1`, `TR2`, … for tools. It holds:

| File | Content |
|---|---|
| `old/<file name>` | the old bytes of each changed file. Its sha256 must equal the value that was in force before the repair. |
| `diff.txt` | a unified diff, old against new, of every changed file. UTF-8, LF. |
| `review.json` | the review record (15.3) |
| `failed_precheck/supervisor_receipt.json` | `6R` only: a copy of the receipt of the failed pre-check |
| `failed_precheck/selftest.json` | `6R` only, and only if one came back |

**`files[]` of a repair line.** Each changed file at its own path, with its new size and sha256 and the `package_path` it had before. Then every file of the repair folder, with `package_path` null. A file that did not change is not listed.

**`values` of a repair line.**

| Field | Type | Meaning |
|---|---|---|
| `repair_id` | string | `6R1`, `TR1`, … |
| `repaired[]` | list | `path`, `old_sha256`, `new_sha256`, `old_copy` (path under the repair folder) |
| `fault` | string | one plain sentence |
| `reviewer` | string | who wrote the review record |
| `review_verdict` | string | must be `REPAIR_ALLOWED` |
| `failed_precheck` | object | `6R` only: `job_id`, `source_zip_sha256`, `receipt_status`, `selftest_status` (string or null) |
| `could_have_changed_a_sealed_output` | false | `TR` only. It must be false. |
| `unsealed_files_deleted[]` | list | `TR` only: `path`, `sha256` of each derived file that was deleted to be derived again; may be empty |

**Refusals for a repair line.** `tools/ob_seal.py` writes no repair line unless all of this holds:

- every changed file is one that the repair kind may change (`repairs.job_programs.files_that_may_change`, or a `tools/ob_*.py` file sealed in step 1);
- at least one such file differs from its values in force, and no other sealed file does;
- each `old/` copy has the sha256 that was in force;
- `review.json` fits 15.3, names this repair id and exactly these files, carries the sha256 of `diff.txt`, and has the verdict `REPAIR_ALLOWED` with its three statements true;
- for `6R`: the line `6_PROGRAMS` exists, `7_PRECHECK` does not, fewer than 2 `6R` lines exist, and no `expected` category in `job/scorer_examples_v0_1_1.json` differs from the old copy;
- for `6R`, added by amendment A5 and narrowed by operator decision C4 (2026-10-05, round 3): the kept receipt `failed_precheck/supervisor_receipt.json` says `precheck_kind` `SEALED_PACKAGE` and the `status` `PRECHECK_COMPLETE_WITH_FINDINGS` or `STOPPED_NO_RETRY`. A receipt with any other status is refused. That holds for `RUNNING` too: such a job never finished. So the repair follows a failed pre-check job on the sealed package. A rehearsal or a development test never opens this window;
- for `6R`, added by operator decision C4: the receipt names another `source_zip_sha256` than the block `failed_precheck` of every earlier `6R_PROGRAMS_REPAIRED` line. So one failed job opens the window once. The receipt of an earlier failed job, copied into a new repair folder, opens no window. Both refusals of operator decision C4 carry the code `REPAIR_OUTSIDE_ITS_WINDOW`;
- for `TR`: no row of `sealed_outputs_checked` in the review record says `could_the_fault_have_changed_it` true;
- for `TR`, added by amendment A5: no `final` file of sections 4 to 7.1 exists under `questions/`, `checks/`, `solve/` or `select/`, and the seal file has no line `3C_FINAL_QUESTIONS_AND_KEYS`. (`select/split_fixed.json` is not a `final` file.)

A repair outside its window is refused with `REPAIR_OUTSIDE_ITS_WINDOW`.

```json
{"schema": "casalescence/optionb/seal-step/v1", "n": 9, "step": "6R_PROGRAMS_REPAIRED", "utc": "2026-10-12T09:00:00Z", "files": [{"path": "optionb/job/gate_b1.py", "package_path": "job/gate_b1.py", "bytes": 33950, "sha256": "aa…"}, {"path": "optionb/repairs/6R1/old/gate_b1.py", "package_path": null, "bytes": 33894, "sha256": "bb…"}, {"path": "optionb/repairs/6R1/diff.txt", "package_path": null, "bytes": 612, "sha256": "cc…"}, {"path": "optionb/repairs/6R1/review.json", "package_path": null, "bytes": 1480, "sha256": "dd…"}, {"path": "optionb/repairs/6R1/failed_precheck/supervisor_receipt.json", "package_path": null, "bytes": 2210, "sha256": "ee…"}, {"path": "optionb/repairs/6R1/failed_precheck/selftest.json", "package_path": null, "bytes": 5120, "sha256": "ff…"}], "values": {"repair_id": "6R1", "repaired": [{"path": "optionb/job/gate_b1.py", "old_sha256": "bb…", "new_sha256": "aa…", "old_copy": "optionb/repairs/6R1/old/gate_b1.py"}], "fault": "The gate program read a field of the padding plan under a wrong name and stopped.", "reviewer": "a reviewer who did not write the change", "review_verdict": "REPAIR_ALLOWED", "failed_precheck": {"job_id": "cas-optionb-b1-precheck-p1", "source_zip_sha256": "11…", "receipt_status": "PRECHECK_COMPLETE_WITH_FINDINGS", "selftest_status": "GATE_STOP_SELFTEST"}}, "who_could_open": "the operator (Claude Code), the owner and the repair reviewer", "previous_line_sha256": "22…", "made_by": {"program": "tools/ob_seal.py", "sha256": "33…", "utc": "2026-10-12T09:00:00Z"}}
```

### 15.3 `repairs/<repair id>/review.json` (review round 1)

- **Written by:** a reviewer who did not write the change. It may be a separate agent or the outside reviewer. **Read by:** `tools/ob_seal.py`, the owner.
- **Schema name:** `casalescence/optionb/repair_review/v1`. This file does not carry `made_by` or `inputs`; no program writes it.

| Field | Type | Meaning |
|---|---|---|
| `repair_id` | string | |
| `kind` | string | `JOB_PROGRAMS` or `TOOLS` |
| `reviewer`, `author_of_change` | strings | they must differ |
| `fault_file` | string | the path of the file that holds the fault |
| `fault` | string | one plain sentence |
| `evidence` | string | `JOB_PROGRAMS`: the failed self-test check and the log line. `TOOLS`: the stop code or the error text, or the sentence of the sealed plan that the code did not follow. |
| `files_changed` | list of strings | every changed path |
| `diff_sha256` | string | sha256 of `diff.txt` |
| `changes_only_the_listed_files` | true/false | |
| `brings_the_code_in_line_with_the_sealed_plan` | true/false | |
| `changes_no_rule_number_or_wording_of_the_plan` | true/false | |
| `sealed_outputs_checked[]` | list | `TOOLS` only. One row per file that is already sealed and that the old tool wrote: `path`, `could_the_fault_have_changed_it` (true/false), `why` |
| `verdict` | string | `REPAIR_ALLOWED` or `REPAIR_REFUSED` |
| `utc` | string | |

`REPAIR_ALLOWED` needs the three true/false statements true. For `TOOLS` it also needs every `could_the_fault_have_changed_it` false. If one is true the verdict is `REPAIR_REFUSED`: no repair on this seal file, no launch, a new plan version.

```json
{"schema": "casalescence/optionb/repair_review/v1", "repair_id": "6R1", "kind": "JOB_PROGRAMS",
 "reviewer": "repair reviewer (a separate agent)", "author_of_change": "the builder of the job programs",
 "fault_file": "optionb/job/gate_b1.py", "fault": "The gate program read a field of the padding plan under a wrong name and stopped.",
 "evidence": "selftest check made_up_sets failed; stage log line: KeyError: 'average_padding'",
 "files_changed": ["optionb/job/gate_b1.py"], "diff_sha256": "cc…",
 "changes_only_the_listed_files": true, "brings_the_code_in_line_with_the_sealed_plan": true, "changes_no_rule_number_or_wording_of_the_plan": true,
 "verdict": "REPAIR_ALLOWED", "utc": "2026-10-12T08:40:00Z"}
```

```json
{"schema": "casalescence/optionb/seal-step/v1", "n": 2, "step": "2_ROLE_NOTES", "utc": "2026-10-06T08:00:00Z", "files": [{"path": "optionb/notes_role/role_notes.json", "package_path": null, "bytes": 310222, "sha256": "ab…"}], "values": {}, "who_could_open": "the operator (Claude Code) and the owner; no outside model; no question writer", "previous_line_sha256": "cd…", "made_by": {"program": "tools/ob_seal.py", "sha256": "ef…", "utc": "2026-10-06T08:00:00Z"}}
```

---

## 16. Inside the job: commands and file rules

The guest runs these five commands in this order, every time. Each command exits with 0 unless it crashes. A stop is written into a file; it is not an exit code.

| Command | Does | Is given |
|---|---|---|
| `runner_b1.py selftest --mode precheck\|gate0` | Gate 0. No model call. | the package folder, the model folder (tokenizer), the output folder; in `gate0` mode also `--expect-prompt-list-sha256` and `--expect-padding-plan-sha256` |
| `runner_b1.py run-practice` | steps P1, P2, P3. Does nothing unless `selftest.json` says `SELFTEST_PASS`. | package folder, model folder, output folder, `--deadline-unix` |
| `runner_b1.py gate` | runs `gate_b1.py`; writes `GATE.json` | package folder, output folder, `--deadline-unix` |
| `runner_b1.py run-final` | the final calls. Does nothing unless `GATE.json` says `"go": true`. | `PLAN_CONSTANTS.json`, the folder `prompts/` only, model folder, output folder, `--deadline-unix`. **No key folder.** |
| `runner_b1.py score` | runs `analysis_b1.py`; writes `RESULT.json` in every case | package folder, output folder, the two model-hash receipts |

The pre-check job runs the first command only.

File rules for everything the runner writes (copied from `PLAN_CONSTANTS.json`, `runner_file_rules`):

1. Write only under one new folder, `work/run_b1/`.
2. Create each output file once. Then only append and flush.
3. Never rename a file. Never delete a file. Never use a temporary file. No write-then-rename.
4. File names use only letters, digits, dot, dash and underscore.
5. Write nothing under the source folder or the authority folder.
6. Load the model from the payload snapshot path with offline settings. No symlinks. No hard links.

---

## 17. Inside the job: the files

All under `work/run_b1/` unless a path says otherwise.

### 17.1 `selftest.json`

- **Written by:** `job/runner_b1.py selftest`, once. **Read by:** `run-practice`, `score`, the guest's result reader (pre-check job), `tools/ob_seal.py` (step 7).
- **Schema name:** `casalescence/optionb/selftest/v1`

| Field | Type | Meaning |
|---|---|---|
| `mode` | string | `precheck` or `gate0` |
| `status` | string | `SELFTEST_PASS`, `GATE_STOP_SELFTEST`, `GATE_STOP_PADDING` or `GPU_REQUIRED` |
| `checks[]` | list | `name`, `passed` (true, false, or null for "not checked"), `detail` |
| `prompt_list_sha256` | string | sha256 of the bytes of `prompt_hashes.jsonl` |
| `padding_plan_sha256` | string | sha256 of the bytes of `padding_plan.json` |
| `planned_calls` | object | `practice`, `final_must_run`, `final_no_passage`, `whole_job`, `cap` |
| `slowest_analysis_seconds_text` | string | |
| `score_time_limit_seconds` | whole number | at least 120 |
| `made_up_sets` | object | per set: `gate_printed`, `gate_expected`, `analysis_printed`, `analysis_expected`, `ok` |

`checks[].name` values, in order: `scorer_known_examples`, `package_matches_seal`, `every_task_has_every_group`, `gpu_present`, `tokenizer_loads`, `padding_plan`, `planned_calls_under_cap`, `made_up_sets`, `score_time`, `precheck_binding`.

```json
{"schema": "casalescence/optionb/selftest/v1", "mode": "precheck", "status": "SELFTEST_PASS",
 "checks": [{"name": "scorer_known_examples", "passed": true, "detail": "40 of 40"}, {"name": "gpu_present", "passed": null, "detail": "not checked in precheck mode"}],
 "prompt_list_sha256": "ab…", "padding_plan_sha256": "cd…",
 "planned_calls": {"practice": 560, "final_must_run": 1610, "final_no_passage": 128, "whole_job": 2298, "cap": 5000},
 "slowest_analysis_seconds_text": "6.20", "score_time_limit_seconds": 120,
 "made_up_sets": {"ALL_RIGHT": {"gate_printed": "GATE_STOP_DIFFICULTY", "gate_expected": "GATE_STOP_DIFFICULTY", "analysis_printed": "UNINFORMATIVE_DIFFICULTY", "analysis_expected": "UNINFORMATIVE_DIFFICULTY", "ok": true}}}
```

### 17.2 `padding_plan.json`

- **Written by:** `job/runner_b1.py selftest`, once. **Read by:** `run-practice`, `run-final`, `gate`, `score`.
- **Schema name:** `casalescence/optionb/padding_plan/v1`
- **No time, no host name, no path of the machine.** Written with `json.dumps(value, indent=1, ensure_ascii=False, sort_keys=True)` plus one LF. So its bytes are the same in the pre-check job and in the GPU job. It does not carry `made_by` or `inputs`.

| Field | Type | Meaning |
|---|---|---|
| `passages[].passage_id`, `.set` | strings | |
| `passages[].ord_length_chosen` | object | per ordinary group: `090`, `100` or `110` |
| `passages[].content_tokens` | object | per group: tokens of the notes text alone; for an ordinary group an object per length |
| `passages[].target_tokens` | whole number | |
| `passages[].blocks` | object | per group with a Notes block: `k`, `block_tokens`, `padding_tokens`, `difference` (block minus target; −1, 0 or 1) |
| `answer_given[]` | list | practice only: `task_id`, `level`, `k`, `block_tokens`, `padding_tokens`, `difference` |
| `average_padding_share` | object | per set, per group: `share`, the exact mean as `[numerator, denominator]`, and `percent_text` |
| `rule` | object | `max_percent` (10), `groups`, `stop` (true/false) |

```json
{"schema": "casalescence/optionb/padding_plan/v1",
 "passages": [{"passage_id": "V901", "set": "practice", "ord_length_chosen": {"ORD-INFORMED": "100", "ORD-FREE": "110"},
   "content_tokens": {"FILLER": 9, "ROLE": 118, "MIXED": 119, "QUOTES-ONLY": 61, "ORD-INFORMED": {"090": 96, "100": 112, "110": 127}, "ORD-FREE": {"090": 90, "100": 104, "110": 116}},
   "target_tokens": 125,
   "blocks": {"FILLER": {"k": 110, "block_tokens": 125, "padding_tokens": 115, "difference": 0}, "ROLE": {"k": 2, "block_tokens": 125, "padding_tokens": 7, "difference": 0},
              "MIXED": {"k": 1, "block_tokens": 125, "padding_tokens": 6, "difference": 0}, "QUOTES-ONLY": {"k": 59, "block_tokens": 125, "padding_tokens": 64, "difference": 0},
              "ORD-INFORMED": {"k": 8, "block_tokens": 125, "padding_tokens": 13, "difference": 0}, "ORD-FREE": {"k": 4, "block_tokens": 125, "padding_tokens": 9, "difference": 0}}}],
 "answer_given": [{"task_id": "V901.LONG_BREAK", "level": "1", "k": 108, "block_tokens": 125, "padding_tokens": 113, "difference": 0}],
 "average_padding_share": {"practice": {"ROLE": {"share": [7, 125], "percent_text": "5.60"}}, "final": {}},
 "rule": {"max_percent": 10, "groups": ["ROLE", "MIXED", "ORD-INFORMED", "ORD-FREE"], "stop": false}}
```

### 17.3 `prompt_hashes.jsonl`

- **Written by:** `job/runner_b1.py selftest`, once. **Read by:** `run-practice`, `run-final` (each prompt it builds must have the hash listed here), `score` (V2).
- One line per prompt that could be sent: every phase, task, group it has, level it has, and each of the three closing wordings. Lines are sorted by `call_id`. No time and no host name. Each line is `json.dumps(value, ensure_ascii=False, sort_keys=True)`.

| Field | Type |
|---|---|
| `call_id` | string |
| `prompt_sha256` | string |
| `prompt_tokens` | whole number |
| `notes_tokens` | whole number, or null when the group has no Notes block |

```json
{"call_id": "final|V950.GOES_FOR|ROLE|L1|W2", "notes_tokens": 125, "prompt_sha256": "ab…", "prompt_tokens": 331}
```

### 17.4 The made-up answer sets

- **Written by:** `job/runner_b1.py selftest`, each once. **Read by:** `gate_b1.py` and `analysis_b1.py` during the self-test only.
- For each set name `<SET>` in `ALL_RIGHT`, `ALL_WRONG`, `DESIGNED`, `RANDOM_LETTERS`, `ALL_MALFORMED`:
  - `trial_<SET>_calls_practice.jsonl` — lines in the format of 17.5, phase `practice`, built from the practice tasks;
  - `trial_<SET>_calls_final.jsonl` — the same practice tasks written as phase `final`, level 1, wording 1;
  - `trial_<SET>_GATE.json` — what the gate program wrote (format 17.7);
  - `trial_<SET>_RESULT.json` — what the analysis program wrote (format 17.9).
- In these lines `prompt` is the empty string and `answer_token_ids` is an empty list. `seconds_text` is `"1.0"`.

### 17.5 `calls_practice.jsonl` and `calls_final.jsonl` (the per-call output lines)

- **Written by:** `job/runner_b1.py run-practice` and `run-final`. One line per model call, written and flushed at once.
- **Read by:** `job/gate_b1.py` (practice), `job/analysis_b1.py` (final), the archive.
- The runner never scores a final reply and never knows a final key.

| Field | Type | Meaning |
|---|---|---|
| `call_id` | string | |
| `n` | whole number | running number over the whole job, from 1 |
| `phase` | string | `practice` or `final` |
| `step` | string | `P1`, `P2`, `P3`, `MUST_RUN` or `NO-PASSAGE` |
| `task_id`, `passage_id`, `family`, `group` | strings | |
| `level` | 1 or 2 | |
| `wording` | 1, 2 or 3 | |
| `ord_length` | string or null | the length used, for an ordinary group |
| `padding_k` | whole number or null | |
| `prompt` | string | the full prompt text after the chat template |
| `prompt_sha256` | string | |
| `prompt_tokens` | whole number | |
| `notes_tokens` | whole number or null | tokens of the Notes block |
| `letters_shown` | list of strings | |
| `raw_answer` | string | |
| `answer_token_ids` | list of whole numbers | |
| `new_tokens` | whole number | |
| `cut_off` | true/false | |
| `seconds_text` | string | seconds for this call |
| `utc` | string | |

```json
{"call_id": "final|V950.GOES_FOR|ROLE|L1|W2", "n": 1532, "phase": "final", "step": "MUST_RUN", "task_id": "V950.GOES_FOR", "passage_id": "V950", "family": "role_step", "group": "ROLE", "level": 1, "wording": 2, "ord_length": null, "padding_k": 2, "prompt": "<|im_start|>system\n…", "prompt_sha256": "ab…", "prompt_tokens": 331, "notes_tokens": 125, "letters_shown": ["A", "B", "C", "D"], "raw_answer": "{\"answer\": \"C\"}", "answer_token_ids": [4913, 9217, 3252, 330, 34, 9207], "new_tokens": 7, "cut_off": false, "seconds_text": "0.41", "utc": "2026-10-10T18:22:05Z"}
```

Order of calls. Practice P3 and the final must-run block: tasks sorted by id, shuffled with `random.Random(<practice_call_order>)` or `random.Random(<final_call_order>)`; for each task its groups back to back, in the order of `PLAN_CONSTANTS.json`. Then, in the final phase, the NO-PASSAGE block in the same task order, if `GATE.json` lists it.

### 17.6 `practice_decisions.jsonl` and `run_status.jsonl`

- **Written by:** `job/runner_b1.py`. **Read by:** `job/gate_b1.py` (it must reach the same decisions and stops if it does not), `job/analysis_b1.py`.
- `practice_decisions.jsonl`: one line after P1 and one after P2.

```json
{"after": "P1", "chosen_wording": 2, "clean_by_wording": {"1": [61, 100], "2": [88, 100], "3": [80, 100]}}
{"after": "P2", "chosen_level": 1, "correct_by_level": {"1": [29, 66], "2": [22, 66]}, "plain_fact_correct": [27, 34], "early_stop": null}
```

`early_stop` is null, `GATE_STOP_DIFFICULTY` or `GATE_STOP_NO_HARM_BASE`. With an early stop, P3 is not run.

- `run_status.jsonl`: one line per event. Fields: `utc`, `command`, `event`, `calls_done`. `event` is `START`, `END`, `SKIPPED_NO_SELFTEST_PASS`, `SKIPPED_NO_GO`, `STOP_CALL_CAP` or `STOP_WORK_CUTOFF`.

```json
{"utc": "2026-10-10T18:40:00Z", "command": "run-final", "event": "END", "calls_done": 2298}
```

### 17.7 `GATE.json`

- **Written by:** `job/gate_b1.py`, once. **Read by:** `job/runner_b1.py run-final`, `job/analysis_b1.py`.
- **Schema name:** `casalescence/optionb/gate/v1`

| Field | Type | Meaning |
|---|---|---|
| `go` | true/false | |
| `stop_code` | string or null | one of the stop codes |
| `first_failing_gate` | string or null | a name from `gates.order` |
| `chosen_wording` | 1, 2, 3 or null | |
| `chosen_level` | 1, 2 or null | |
| `final_blocks` | list | `["MUST_RUN"]` or `["MUST_RUN", "NO-PASSAGE"]`; empty when `go` is false |
| `gates` | object | per gate: its counts as `[part, whole]` pairs and `passed` (true, false, or null for "not reached") |
| `printed_no_rule` | object | `role_vs_ord_informed_differ` `[part, whole]`; `clean_gap_points_text` per ordinary group |
| `seconds_per_call_text` | string | |
| `decided_unix` | whole number | |

**`gates.GATE_4_FORMAT` (review round 1).** Gate 4 counts role-step tasks and plain-fact tasks apart. Its object has this shape, and no other:

| Field | Type | Meaning |
|---|---|---|
| `by_group` | object | one key per must-run group |
| `by_group.<group>.role_step` | object | `clean` `[part, whole]`, `format_fail_plus_cut_off` `[part, whole]`, `passed` |
| `by_group.<group>.plain_fact` | object | the same three fields. Left out for a group that has no plain-fact tasks (QUOTES-ONLY). |
| `by_group.<group>.passed` | true/false | true only when every family the group has passed |
| `no_passage` | object | `clean` and `format_fail_plus_cut_off` of NO-PASSAGE on role-step tasks |
| `no_passage_dropped` | true/false | |
| `passed` | true/false | true only when every must-run group passed |

A family passes when `100 × clean ≥ 75 × whole` and `100 × format_fail_plus_cut_off ≤ 25 × whole`. The counts are over the group's practice calls of that family at the chosen level under the chosen wording. Both practice families hold tasks in a launched job, because the launch floor asks for 36 and 20.

```json
{"schema": "casalescence/optionb/gate/v1", "go": true, "stop_code": null, "first_failing_gate": null,
 "chosen_wording": 2, "chosen_level": 1, "final_blocks": ["MUST_RUN", "NO-PASSAGE"],
 "gates": {"GATE_1_CLOSING_WORDING": {"clean_by_wording": {"1": [61, 100], "2": [88, 100], "3": [80, 100]}, "passed": true},
           "GATE_2_DIFFICULTY": {"correct_by_level": {"1": [29, 66], "2": [22, 66]}, "inside_window": {"1": true, "2": true}, "passed": true},
           "GATE_3_NO_HARM_BASE": {"correct": [27, 34], "passed": true},
           "GATE_4_FORMAT": {"by_group": {"ROLE": {"role_step": {"clean": [63, 66], "format_fail_plus_cut_off": [2, 66], "passed": true},
                                                   "plain_fact": {"clean": [32, 34], "format_fail_plus_cut_off": [1, 34], "passed": true}, "passed": true},
                                          "QUOTES-ONLY": {"role_step": {"clean": [64, 66], "format_fail_plus_cut_off": [1, 66], "passed": true}, "passed": true}},
                             "no_passage": {"clean": [65, 66], "format_fail_plus_cut_off": [0, 66]}, "no_passage_dropped": false, "passed": true},
           "GATE_5_NOTES_ARE_READ": {"clean_replies": 63, "correct_among_clean": 61, "passed": true},
           "GATE_6_PASSAGE_IS_NEEDED": {"correct": [14, 66], "no_passage_minus_none_points_text": "-22.73", "passed": true},
           "GATE_7_TIME": {"must_run_calls": 1610, "no_passage_calls": 128, "seconds_left": 5200, "must_run_fits": true, "no_passage_fits": true, "passed": true}},
 "printed_no_rule": {"role_vs_ord_informed_differ": [17, 66], "clean_gap_points_text": {"ORD-INFORMED": "1.52", "ORD-FREE": "-3.03"}},
 "seconds_per_call_text": "0.41", "decided_unix": 1791657000}
```

### 17.8 The model-hash receipts

- **Written by:** the guest (not by the runner). **Read by:** `job/analysis_b1.py` (rule V2), the archive.
- `controller/MODEL_PRE.json` — before the first stage.
- `controller/MODEL_AFTER_CALLS.json` — after the last model call and before the score stage.
- `controller/MODEL_POST.json` — in the guest's own end routine (the analysis program does not read this one).
- Shape, as the guest's `verify_tree` writes it today:

| Field | Type |
|---|---|
| `status` | string, `EXACT_FILE_MEMBERSHIP_AND_BYTES_VERIFIED` |
| `root_role` | string |
| `files[]` | list of `{"path", "bytes", "sha256"}` |
| `file_count` | whole number (7) |
| `total_bytes` | whole number (999586347) |
| `verified_unix` | number |

V2 holds when both receipts exist, both have that status, their `files` lists are equal, and each file's `bytes` and `sha256` equal `model_b.files` in `PLAN_CONSTANTS.json`. A receipt file is matched to `model_b.files` by the last part of its `path` (the file name). A missing receipt gives `INVALID_RUN` with reason `MODEL_HASH_RECEIPT_MISSING`.

```json
{"status": "EXACT_FILE_MEMBERSHIP_AND_BYTES_VERIFIED", "root_role": "models", "files": [{"path": "models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775/config.json", "bytes": 659, "sha256": "18e1…ff45"}], "file_count": 7, "total_bytes": 999586347, "verified_unix": 1791650000.5}
```

### 17.9 `RESULT.json`

- **Written by:** `job/analysis_b1.py`, once, in every case. **Read by:** the guest's small result reader (it takes only `outcome_code`, and the file's hash and size), the operator, anyone who repeats the scoring.
- **Schema name:** `casalescence/optionb/result/v1`
- Written with `allow_nan=False`. Whole numbers and `_text` strings only.

| Field | Type | Meaning |
|---|---|---|
| `kind` | string | `OUTCOME` or `STOP` |
| `outcome_code` | string | an outcome code (with `_EXPLORATORY` where the tier rule adds it) or a stop code; capital letters and underscores, at most 80 characters |
| `base_code` | string | the code without the ending |
| `exploratory` | true/false | |
| `invalid_reasons` | list of strings | from `validity.reasons`; empty unless `INVALID_RUN` |
| `sizes` | object | `final_role_step_tasks`, `final_plain_fact_tasks`, `final_passages_with_a_role_step_task` |
| `chosen` | object | `wording`, `level` |
| `groups` | object | per group, per family: `tasks`, the five category counts, `clean`, `not_clean`, `near_miss`, `letters` (count per letter chosen) |
| `validity` | object | `V1`, `V2`, `V3` (true/false) and `format_floor` per group and family |
| `readability` | object | `R1`, `R2`, `R3`: `tripped` and the numbers used |
| `tests` | object | per comparison, the fields below |
| `conditions` | object | `C1` … `C5` (true, false, or null when not reached), `better_rival`, `c2_margin_met` |
| `no_harm` | object | `status`, `H1`, `H2`, `by_group`, `sentence` |
| `x_points` | whole number or null | the number X. It is worked out from the standard error of the test of ROLE against the better rival (section 18, rows "Standard error" and "The number X"). |
| `sentences` | list of strings | the fixed report sentences that apply. They are `report_sentences.code_7` and `report_sentences.code_10` in `PLAN_CONSTANTS.json`. (Amendment A7: `code_10` was named `code_9` before the outcome codes were numbered 1 to 11.) |
| `sub_views` | object | four keys: `without_LAND_and_HABIT`, `type_without_leftover`, `passage_without_leftover`, `word_rule_misses_under_ROLE`; each holds `sizes` and `tests` |
| `extra_views` | object | `word_matching_rule`, `anchor_in_ordinary_note`, `no_passage`, `by_type`, `two_by_two_vs_NONE`, `padding_average`, `digit_view` |
| `random_procedure` | object | `used`: the procedure the program ran. `plan_text`: `tests.random_source` of `PLAN_CONSTANTS.json`. Both name the same procedure (section 18). |
| `word_views_note` | string | says whether `content()` was imported from `tools/verdict.py` |
| `view_errors` | list of strings | empty unless a view raised an error. In the self-test a list that is not empty fails that made-up set. |
| `seconds_text` | string | time the analysis took |

**The three word views (review round 1).** `sub_views.word_rule_misses_under_ROLE`, `extra_views.word_matching_rule` and `extra_views.anchor_in_ordinary_note` each carry `available` (true/false). They are worked out inside the job, because `tools/verdict.py` is in the package (section 14). So `available` is true in the job and in the self-test. A package without the file, or with another sha256, fails the self-test check `package_matches_seal` before any model call.

A test object (`tests.<X>_beats_<Y>`):

| Field | Type |
|---|---|
| `x`, `y` | group names |
| `passages`, `tasks` | whole numbers |
| `correct_x`, `correct_y` | whole numbers |
| `sum_d` | whole number |
| `flips`, `flips_at_least` | whole numbers (100000 and the count) |
| `two_sided_flips_at_least` | whole number |
| `holds` | true/false (one-sided) |
| `difference_points_text` | string |
| `range95_points_text` | list of two strings |
| `se_points_text` | string: the bootstrap standard error, in points. It is the standard deviation of the 10000 resampled values. Nothing divides it by a count (amendment A4). |

After a stop (`kind` is `STOP`), only `kind`, `outcome_code`, `base_code`, `exploratory` (false), `stop_details` and `seconds_text` are present.

```json
{"schema": "casalescence/optionb/result/v1", "kind": "OUTCOME",
 "outcome_code": "ROLE_HELP_NOT_ABOVE_ORDINARY_HELP_EXPLORATORY", "base_code": "ROLE_HELP_NOT_ABOVE_ORDINARY_HELP", "exploratory": true,
 "invalid_reasons": [],
 "sizes": {"final_role_step_tasks": 128, "final_plain_fact_tasks": 119, "final_passages_with_a_role_step_task": 96},
 "chosen": {"wording": 2, "level": 1},
 "groups": {"ROLE": {"role_step": {"tasks": 128, "CORRECT": 80, "WRONG": 44, "TYPE_MISMATCH": 0, "FORMAT_FAIL": 3, "CUT_OFF": 1, "clean": 122, "not_clean": 6, "near_miss": 2, "letters": {"A": 33, "B": 30, "C": 31, "D": 28}}}},
 "validity": {"V1": true, "V2": true, "V3": true},
 "readability": {"R1": {"tripped": false, "none_correct": [59, 128]}},
 "tests": {"ROLE_beats_ORD-INFORMED": {"x": "ROLE", "y": "ORD-INFORMED", "passages": 96, "tasks": 128, "correct_x": 80, "correct_y": 74, "sum_d": 6, "flips": 100000, "flips_at_least": 14210, "two_sided_flips_at_least": 28377, "holds": false, "difference_points_text": "4.69", "range95_points_text": ["-3.91", "13.28"], "se_points_text": "4.38"}},
 "conditions": {"C1": true, "C2": false, "C3": true, "C4": null, "C5": null, "better_rival": "ORD-INFORMED", "c2_margin_met": false},
 "no_harm": {"status": "HELD", "sentence": "A loss of up to 7 points cannot be ruled out."},
 "x_points": 11,
 "sentences": ["Role information helped B. An advantage over a strong model's ordinary notes was not shown. A gain under about 11 points could have been missed."],
 "sub_views": {}, "extra_views": {}, "seconds_text": "7.80"}
```

---

## 18. Small rules that two programs must apply the same way

| Rule | Exact form |
|---|---|
| Word count of a question or option | `len(text.split())` |
| Word sequence of a text | lower case, then regex `[A-Za-z0-9']+` |
| "Holds" (one text inside another) | the word sequence of one is an unbroken part of the word sequence of the other |
| Size count | the number of matches of regex `[A-Za-z0-9']+\|[^\sA-Za-z0-9']` |
| Looser match | `lenient_span(a, b)` from `tools/verdict.py` |
| Same reading | `same_span` on the words and `same_field` on each field in `REQUIRED[noetic]` |
| Token count | `len(tokenizer.encode(text, add_special_tokens=False))` |
| Block text | padding line, LF, notes text |
| Clean reply | `read_answer` gave a value; it is a string; it is in `letters_shown` |
| Near miss | a WRONG reply that is not clean, and whose value, after dropping brackets, dots, colons and spaces at both ends, starts with one shown letter followed by nothing or by a non-letter; or whose value equals a shown option's text, any letter case |
| Word-matching rule | for a task and a group: score each shown option by how many of its distinct content words (`content()` from `tools/verdict.py`) are among the content words of the group's notes text; the rule picks an option only when one option alone has the highest score |
| Anchor appears in an ordinary note | at least half of the anchor's content words are among the note's content words; a task counts when one of its `anchors_matched` appears |
| Percent and point rules | whole numbers only, for example `100 * part >= 60 * whole` |
| Chance plus points | with k options: `100 * part * k > (100 + points * k) * whole` means "above chance plus points" |
| Per-passage test value | `d` = right under X minus right under Y, over the passage's final role-step tasks at the chosen level |
| Random source (review round 1) | `random.Random(seed)` of the Python standard library; a fresh one for every test and for every range; no numpy |
| One sign flip | `r = rng.getrandbits(n)` with `n` passages sorted by passage id; bit `j` of `r`, counted from 0, belongs to passage `j`; a set bit flips the sign of that passage's `d`; flipped sum = real sum − 2 × (sum of `d` over the flipped passages) |
| One resample | `rng.choices(passages, k=n)` with the passages in passage-id order; value = `(100 × 1000000 × sum(d)) // sum(tasks)`, a whole number of millionths of a point |
| 95% range | the sorted 10000 values at index 250 and index 9749; the one-sided upper end at index 9499 |
| Standard error (amendment A4) | the standard deviation of the 10000 resampled values. That is the bootstrap standard error. It is used as it stands: it is not divided by the number of resamples, by the number of passages or by any other count. The standard deviation is taken in its plain form: the square root of the average squared distance of the 10000 values from their average. Whole-number arithmetic, the square root rounded down. |
| The number X | the larger of (2.485 × SE) and (5 + 0.84 × SE), rounded up to a whole point. SE is the standard error, as in the row above, of the resampled ROLE-minus-better-rival differences, in points. |
| Right letters | section 12: dealt in turn over the whole task family of a set and level, type after type, never starting again at `A` for a new type |
| Sayings line (A13) | `Sayings: ` and then the sayings cell: group 4 of `role_notes.sayings_row_regex` on that Noetic's table row, character for character |
| Head of a ROLE or MIXED text (A13) | for each Noetic shown, in number order: its canon line, then its sayings line. A head line is frame text and is never blanked. `tools/ob_role_notes.py` builds the head this way; `tools/ob_screen_notes.py` and `tools/ob_assemble.py` check a note's head against the same rule |
| A note that is given up (A13; operator decision C6) | the call log holds 2 counted lines for that note id. A counted line has `http_status` 200 and the `error` `REPLY_EMPTY` or `REPLY_CUT_OFF`, or, by operator decision C6, `http_status` 400, 404 or 422; at most 3 passages of a set (section 8.1) |

---

## 19. The owner's status table (review round 1)

### 19.1 `OUTCOME_STATUS_TABLE.json`

- **Path:** `optionb/OUTCOME_STATUS_TABLE.json`
- **Written by:** the operator, from the owner's own words. The owner decides every word in it. No program writes it. It does not carry `made_by` or `inputs`.
- **Read by:** `tools/ob_seal.py` (seal step 7, and the command `status-word`).
- **Schema name:** `casalescence/optionb/outcome_status_table/v1`
- **When:** it may be written at any time before seal step 7. It is hashed in seal step 7. Without it there is no seal step 7, and so no GPU launch.
- **Why:** the status word of the spec sheet is fixed before model B's results exist (plan section 21).

| Field | Type | Meaning |
|---|---|---|
| `owner_words_verbatim` | string | what the owner wrote or said, unchanged |
| `received_utc`, `channel` | strings | when and how the operator got it |
| `spec_sheet` | object | `path` (`docs/CAS_HARNESS_SPEC_SHEET.md`) and `sha256` of the sheet as it stood then |
| `legend_words` | list of strings | the status words of the sheet's legend (its section 3), copied from the sheet |
| `table` | object | one key per code; the value is one status word |

**Keys of `table`: 28.** Every `code` of `outcome_codes_in_checking_order` (11; they are numbered 1 to 11, each number once, by amendment A7). Every code of `tiers.suffix_applies_to` with the ending `_EXPLORATORY` (7; these are the codes numbered 5 to 11). Every code of `stop_codes` (8). `RESULT_UNREADABLE`. `NO_RESULT_FILE` (the job returned no `RESULT.json`). 11 + 7 + 8 + 2 = 28. A key is the name of a code, not its number.

**Limits.** They are `spec_sheet_status.limits` in `PLAN_CONSTANTS.json`. `tools/ob_seal.py` refuses seal step 7 unless all hold:

1. Every one of the 28 keys stands in `table` once. There is no other key.
2. Every word stands in `legend_words`.
3. `INVALID_RUN`, `UNINFORMATIVE_DIFFICULTY`, `FORMAT_GAP_NOT_READABLE`, `PADDING_HURTS_B_NOT_READABLE`, every stop code, `RESULT_UNREADABLE` and `NO_RESULT_FILE` never get a pass word. The pass words are `spec_sheet_status.pass_words`: `VALIDATED`, `LICENSED`, `PASS`, `SANITY_PASS`, `HOLDS`.
4. A code that ends in `_EXPLORATORY` never gets `VALIDATED` or `LICENSED`.
5. Only `ROLE_HELP_BEATS_STRONGEST_ORDINARY_HELP`, with or without the ending, may get a pass word.

The example shows the shape only. Its words are placeholders. They are not a proposal for the owner.

```json
{"schema": "casalescence/optionb/outcome_status_table/v1",
 "owner_words_verbatim": "<the owner's words>", "received_utc": "2026-10-09T18:00:00Z", "channel": "<how the operator got it>",
 "spec_sheet": {"path": "docs/CAS_HARNESS_SPEC_SHEET.md", "sha256": "ab…"},
 "legend_words": ["<word 1>", "<word 2>", "…"],
 "table": {"INVALID_RUN": "<word>", "UNINFORMATIVE_DIFFICULTY": "<word>", "NO_ROLE_HELP_SHOWN": "<word>", "NO_ROLE_HELP_SHOWN_EXPLORATORY": "<word>",
           "GATE_STOP_SELFTEST": "<word>", "RESULT_UNREADABLE": "<word>", "NO_RESULT_FILE": "<word>", "…": "…"}}
```

### 19.2 The command `status-word`

- `tools/ob_seal.py status-word --result <path of RESULT.json>`
- It needs seal line `7_PRECHECK` and an unchanged table. It reads `outcome_code` from the result file and prints one line: the code, one space, the status word of the table.
- With `--no-result-file` in place of `--result` it prints the word of `NO_RESULT_FILE`. With `--code RESULT_UNREADABLE` it prints that word.
- A code that is not a key of the table can not come from a sound run. The command then prints the code and `NOT_IN_TABLE`, and exits with code 2. Nobody fills the word in by hand.
- It writes no file. The report and the spec sheet quote its line.

---

## 20. The development-test package (amendment A10)

The development test is one CPU-only AWS job of kind `DEVELOPMENT_TEST`, at most two, before seal step 1 (plan section 19.1). It runs `runner_b1.py selftest --mode precheck` once, on the package of this section. Its limits are in `PLAN_CONSTANTS.json` under `aws.development_test_job`: cap 0.50 USD and 45 minutes for each job.

- **Built by:** `dry/build_dev_package.py` (the full path is `optionb/dry/build_dev_package.py`). It runs the real laptop tools `tools/ob_*.py` on a made-up fixture under `optionb/dry/`. Then it runs the real zip and contract builders of the controller folder. So the package has the real layout.
- **Read by:** the pre-check kit (it builds the job folder for kind `DEVELOPMENT_TEST`), and `job/runner_b1.py selftest` inside the job.
- **Layout:** the same 16 paths as in section 14, inside a `source.zip`.

What each path holds:

| Path in the package | Content |
|---|---|
| `prompts/…`, `keys_practice/…`, `keys_final/…` | Written by the real tools from the made-up fixture, in the formats of section 12. Made-up passages, made-up tasks, made-up notes and made-up keys. |
| `SEAL_OPTIONB.jsonl` | A made-up seal file of the dry folder, in the format of section 15. It names the package files with their true sizes and hashes, so that the self-test check `package_matches_seal` can run. It ends with a line `6_PROGRAMS`. It is never the seal file of the study. |
| `job/…`, `tools/verdict.py` | The real files, as they stand that day. |
| `08_OPTION_B_PLAN_v1_0.md`, `PLAN_CONSTANTS.json`, `FILE_FORMATS.md` | The real files, as they stand that day. They are not sealed yet. |

Rules:

- **Made-up only.** The package never holds a real passage, a real question, a real label, a real note or a real key. The only real study text in it is the canon definition lines and, by A13, the canonical sayings lines. The role-note tool copies them from the guide and from the table of Clarification 6, as it always does.
- **The dry mark.** Every JSON file that a tool writes in the dry folder carries the dry mark in `made_by.program`, as the dry fixtures do today.
- **Size.** The made-up set must be large enough for the five made-up answer sets to reach the codes of plan section 17.3. `job/SELFTEST_EXPECTED.json` lists what the set `DESIGNED` needs. The largest need is at least 20 practice role-step tasks, because Gate 5 needs 20 clean ANSWER-GIVEN replies. It also needs at least 1 practice plain-fact task, fewer than 100 practice plain-fact tasks and fewer than 200 practice role-step tasks.
- **No real seal file.** The kit takes a package for kind `DEVELOPMENT_TEST` only while `optionb/SEAL_OPTIONB.jsonl` does not exist. So the test can only run before seal step 1.
- **The receipt.** The job's `supervisor_receipt.json` says `precheck_kind` `DEVELOPMENT_TEST`. It holds its five values under the name `values_never_for_a_seal_file`, never under `seal_step_7_values`. Seal step 7 refuses such a receipt (section 15.1).
- **Job ids.** `cas-optionb-b1-devtest-d1`, then `cas-optionb-b1-devtest-d2`. There is no third.
- **What the result is.** A record of a program test on made-up data. It is never evidence about roles. It is never written to a seal file. It is not one of the 4 pre-check jobs.
