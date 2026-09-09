# Graph-first candidate + targeted ^6 trainer — RESULTS (adapter milestone complete)

## Status

The real graph→^6 adapter chain is implemented and pure-tested; the finished
runnable package is built. **No GPU run, no reservation, no learning result
has been produced.** The AWS run awaits the owner's signed authorization.

## This milestone (per the review's mandate)

- **Real adapter** (`cas_meta2/graph_teaching/adapter.py` +
  `real_framework.py`): exact input (graph + question tokens), exact module
  (candidate `^6` decompose copy — never the accepted model), frozen
  dot-product readout, checker-derived scoring per op, AdamW over
  `operation:^6` parameters only, digest-verified containment. Full chain in
  `ADAPTER_SPEC.md`.
- **Real contract role**: `operation:^6` from
  `cas_cjt.state.make_operation_contract("^6")` (admits `operation:^6`,
  `bias_update_head`; the run uses only the former).
- **Conditions labeled accurately**: `prompt_framing_only` — not the
  CASformer-vs-generic comparison.
- **Budget resolved**: 64 steps / 600 s per condition; totals 128 / 1200 s in
  ONE job with ONE `$4.00` reservation.
- **Lesson exposure**: per-op record and update counts reported; an optimizer
  step is explicitly not a teaching cycle.
- **Prediction seal**: sealed-split predictions recorded before answers are
  consulted; prediction inputs are answer-free.
- **AWS launcher** (`aws/graph_training_launch.py`): plan-only default; full
  lifecycle with every binding-fit execution fix; worker runs both conditions
  and preserves original inner errors.

## Finished package (byte-fixed; NOT launched)

| Field | Value |
|---|---|
| source_sha | `ce1a3882c57400bb72a810c056c4baf978b72db6` |
| archive_sha256 | `52151c8bb00b45e5e442fd52246d15515c98fe6b2bc745237a4c08992206f580` |
| manifest_sha256 | `0b2801752dcf4dd46e858485584dd52130b76fdc951c33a597f60c294831d2b4` |
| archive bytes / members | 356,470 / 30 |

Package receipt: `package_001/receipt.json`.

## Test evidence (byte-verifiable)

Full suite: **137 passed, 24 subtests passed** — `checks_002/pytest_output.txt`,
sha256 `9a2ab5ac1eedb7b6cbda7c2cf95fe565da6c265face53fbe883b61767f8e3449`.

## FULL LOCAL PATH TO THESE RESULTS

`C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\research\CAS_META_2_COMPOSITION\records\teaching_cycle_001\graph_first_candidate_001\training_mode_001\RESULTS.md`

Companion records in the same directory: `ADAPTER_SPEC.md`,
`AUTHORIZATION_REQUEST_AWS.md` (precise request, NOT launched, NOT reserved),
`MODE_README.md`; package in `package_001\`; checks in `checks_001\` and
`checks_002\`.

## Next step

Owner-signed authorization record binding the package identities above; then —
and only then — one launch with one new `$4.00` reservation. No automatic
launch, no automatic reservation.
