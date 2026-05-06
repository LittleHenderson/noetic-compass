# Path B Tier 3 Dialogue SDG - Codex status (2026-05-06)

## Scope

This is B-1 from `docs/working/path_B_kickoff_codex_2026_05_06.md`.
The live classifier smoke on the pod was not touched.

## Files added

- `cas-synthetic/scripts/generate_tier3_dialogue_v1.py`
- `cas-synthetic/tests/test_tier3_dialogue_sdg.py`
- `cas-synthetic/scripts/reformat_lever3_paired_to_native_nl.py`
- `cas-synthetic/tests/test_lever3_reformat.py`

## Files modified

- `.gitignore` now ignores `manual_tmp_test/codex_tier3_dialogue/`, a local
  test scratch directory used because this Windows session denies access to
  the default pytest temp directory.

## What the generator does

- Samples the CAS state locally for each dialogue turn.
- Sends Claude only the job of writing natural-language user prompts and
  natural-language replies for those pre-sampled states.
- Writes one JSONL row per turn with:
  - `conversation_id`
  - `turn_index`
  - `prompt_text` / `prompt`
  - `cas_expression`
  - `reply_text` / `reply`
  - demographic profile and tone fields
  - object trace fields: `id`, `created_at`, `schema_version`,
    `parent_ids`, `source`, `trace_id`
- Preserves the existing native-NL schema version: `native_nl.v1`.
- Adds `generation_version = native_nl_tier3_dialogue_v1`.
- Shards output as `<out-prefix>_0000.jsonl`, `<out-prefix>_0001.jsonl`,
  etc.
- Resumes by reading existing shard files and skipping already-written
  records.
- API mode now top-ups accepted records inside the same invocation if the
  validator drops a conversation before the target is reached.
- Enforces the existing no-jargon reply validator from
  `generate_native_nl_sdg_v1.py`.
- Keeps `round_trip_validator = deferred`.

## Coverage in the 500-record proof dry run

Artifact paths:

- `cas-synthetic/data/native_nl/v1_dialogue_proof_dryrun_20260506_0000.jsonl`
- `cas-synthetic/data/native_nl/v1_dialogue_proof_dryrun_20260506_manifest.json`

Manifest headline:

- 500 total records
- 95 conversations
- 500/500 validator pass
- 0 API calls
- $0 spend
- expression families:
  - base: 390
  - register_set: 45
  - copresence: 27
  - omega_emergent: 21
  - recipe: 17

Important: this dry-run shard is a structural proof only. Its replies are
deterministic placeholders, not training-quality fluent data. Use it to inspect
schema, sharding, resume, and coverage. Do not treat it as final training data.

## Paid 500-record proof result

Artifact paths:

- `cas-synthetic/data/native_nl/v1_dialogue_proof_claude_20260506_0000.jsonl`
- `cas-synthetic/data/native_nl/v1_dialogue_proof_claude_20260506_manifest.json`

Command run:

```powershell
python cas-synthetic\scripts\generate_tier3_dialogue_v1.py `
  --target-records 500 `
  --out-prefix cas-synthetic\data\native_nl\v1_dialogue_proof_claude_20260506 `
  --manifest cas-synthetic\data\native_nl\v1_dialogue_proof_claude_20260506_manifest.json `
  --records-per-shard 5000 `
  --seed 20260506 `
  --concurrency 5 `
  --cost-cap 25
```

Result:

- 477 accepted records
- 91 accepted conversations
- 477/477 validator pass
- $1.53 actual spend
- 106 API calls
- 4 conversations dropped by validator because the reply leaked the word
  `register`
- cost cap was not approached

Post-run patch: the generator now supports same-invocation top-up rounds and
has a stricter prompt line forbidding the literal words `register`, `noetic`,
`domain`, `drive`, and `CAS` in `reply_text`. The paid proof above was produced
before that top-up patch, so it remains at 477 accepted rows.

## Lever 3 paired-data audit

The pasted 2026-05-06 note about existing paired data was checked against the
actual files:

- `cas-synthetic/data/level2_scaffold/lever3_paired_dt_K4.jsonl`
  - 19,652 rows
- `cas-synthetic/data/level2_scaffold/lever3_paired_freeform_5k_2026_05_04.jsonl`
  - 4,913 rows

The files are real, but their `assistant_response` field is usually not a
fluent conversational reply. It is usually CAS-explanation text, for example
`The precise notation is ...` or `Read it as ... noetic ... domain ...`.

Added bridge tool:

- `cas-synthetic/scripts/reformat_lever3_paired_to_native_nl.py`

It has two lanes:

- strict default lane: only emits rows safe for `conversational_lm`
- `--include-explanatory`: emits rows as `cas_explanation_auxiliary` with
  `use_for_conversational_lm=false`

Actual audit command:

```powershell
python cas-synthetic\scripts\reformat_lever3_paired_to_native_nl.py `
  --out cas-synthetic\data\native_nl\v1_dialogue_lever3_strict_audit_v2_20260506.jsonl `
  --manifest cas-synthetic\data\native_nl\v1_dialogue_lever3_strict_audit_v2_20260506_manifest.json
```

Result:

- 0 conversational rows accepted
- 24,565 rows rejected by the strict dialogue gate
- top rejection causes:
  - 10,360 noetic jargon
  - 8,355 register jargon
  - 2,045 CAS jargon
  - 1,820 too long
  - 1,140 symbolic `^N` notation
  - 425 `F1`-`F7` notation
  - 160 explanation-style `notation` false positives caught by the v2 gate

Auxiliary smoke command:

```powershell
python cas-synthetic\scripts\reformat_lever3_paired_to_native_nl.py `
  --include-explanatory `
  --limit 1000 `
  --out cas-synthetic\data\native_nl\v1_dialogue_lever3_auxiliary_smoke_v2_1k_20260506.jsonl `
  --manifest cas-synthetic\data\native_nl\v1_dialogue_lever3_auxiliary_smoke_v2_1k_20260506_manifest.json
```

Result:

- 1,000 auxiliary explanation rows emitted
- 0 rows marked usable for conversational LM

Conclusion: do not count Lever 3 paired data as 25K ready conversational
dialogue rows. It is useful as a separate CAS-explanation auxiliary task, or
as source material for a paid rewrite pass that generates missing fluent
assistant replies.

## Verification run

Passed:

```powershell
python -m py_compile cas-synthetic\scripts\generate_tier3_dialogue_v1.py cas-synthetic\tests\test_tier3_dialogue_sdg.py
python -m pytest cas-synthetic\tests\test_tier3_dialogue_sdg.py -q
python -m py_compile cas-synthetic\scripts\reformat_lever3_paired_to_native_nl.py cas-synthetic\tests\test_lever3_reformat.py
python -m pytest cas-synthetic\tests\test_lever3_reformat.py cas-synthetic\tests\test_tier3_dialogue_sdg.py -q
```

Result:

- 7 tests passed in 0.60s after the top-up patch.
- 11 combined Tier 3 + Lever 3 reformat tests passed in 0.67s.

Attempted broader regression:

```powershell
python -m pytest cas-synthetic\tests\test_native_nl_sdg.py cas-synthetic\tests\test_tier3_dialogue_sdg.py -q
```

Result:

- 21 passed.
- 3 errored before test body because this Windows session cannot create the
  default pytest temp directory under
  `C:\Users\wakil\AppData\Local\Temp\pytest-of-wakil`.
- This is an environment temp-dir permission issue in existing tests using
  `tmp_path`, not a Tier 3 code failure.

## Fresh paid 500-record proof command

Run this only after confirming the Anthropic key is present in
`noetic-compass-scaffold/noetic-compass/.env` as `NC_ANTHROPIC_API_KEY`.
Use a low proof cap first; the script still supports the full $500 cap later.
This uses a new prefix so the manifest captures the full run cost after the
top-up patch.

```powershell
python cas-synthetic\scripts\generate_tier3_dialogue_v1.py `
  --target-records 500 `
  --out-prefix cas-synthetic\data\native_nl\v1_dialogue_proof_claude_v2_20260506 `
  --manifest cas-synthetic\data\native_nl\v1_dialogue_proof_claude_v2_20260506_manifest.json `
  --records-per-shard 5000 `
  --seed 20260506 `
  --concurrency 5 `
  --cost-cap 25
```

Expected preflight estimate for 500 records is low. The cap above is a hard
stop: if real token use exceeds it, the run aborts cleanly.

## Sample-review command after paid proof

```powershell
python -c "import json; rows=[json.loads(l) for l in open('cas-synthetic/data/native_nl/v1_dialogue_proof_claude_20260506_0000.jsonl', encoding='utf-8')]; seen=[]; [seen.append(r['conversation_id']) for r in rows if r['conversation_id'] not in seen]; 
for cid in seen[:5]:
    print('---', cid)
    for r in [x for x in rows if x['conversation_id']==cid]:
        print(r['turn_index'], r['cas_expression'])
        print('USER:', r['prompt_text'])
        print('REPLY:', r['reply_text'])
"
```

Review questions:

- Does `reply_text` sound like normal English, not framework talk?
- Does the reply avoid CAS jargon and symbolic notation?
- Does the reply match the hidden state well enough for training?
- Are multi-turn conversations coherent, or are turns isolated?
- Are compound cases readable without leaking notation?

## Next decision

If the paid 500-record proof looks good:

1. Scale to 5,000 records with `--cost-cap 75`.
2. Review distributions and 20 random conversations.
3. Scale to 50,000 records with the full monitoring cadence and hard cap.

If the proof looks bad:

1. Tighten `TIER3_SYSTEM_PROMPT` and `render_tier3_user_message`.
2. Keep the schema unchanged.
3. Rerun only a 100-500 record paid proof before scaling.
