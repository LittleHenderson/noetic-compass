# Learned-candidate reuse execution gate — GPU run pending

The new code prepares and executes a bounded reuse experiment. Local validation
passed, but no real learned candidate has yet run through this new GPU gate.
This does not close V05/V06/V15 memory, qualification or portable-skill goals.

## What is implemented

`cas_meta3/learned_linker.py` retrieves a candidate with fresh external evidence
checks and embeds its complete program under a new parent. It renames every
procedure and CALL consistently without inlining or changing instructions.
One to four calls receive the same observation reference. The parent returns
an explicitly selected call's Effect, including an earlier call after later
calls execute. Permission, source-size, procedure-count, depth and expanded-run
limits remain those of the unchanged IR and codec. No existing limit is raised.
An extra parent requires a spare procedure name; otherwise linking is rejected.

`cas_meta3/learned_reuse.py` provides an AWS/Linux-only execution entrypoint:

```text
run_reuse_suite(job, store_path, expected_digest, trust_inputs, source_public,
                public_cases, output, native_output, call_count=2, return_call=0)
```

All arguments are keyword-only. A JSON request contains these fields. In a
separately budgeted AWS child process, the CLI is:

```text
python -B -m cas_meta3.learned_reuse --request <request.json> --request-sha256 <raw-file-SHA256>
```

It requires the existing explicit META3/META2 AWS job flags and actual CUDA
through the frozen hardware check. T4 is refused. The launcher must independently
bind those flags to the real instance, source archive, budget and termination
deadline. Setting an environment flag alone is not provider evidence.

Before neural execution, the entrypoint retrieves and checks the actual stored
candidate; verifies original public observations against its learning proof;
and requires new selected input values at the exact float32 byte level. Merely
changing wording, an unselected observation, or sub-float32 rounding does not
count as a new input. Values remain inside [-1, 1]. No local curriculum is drawn.

For each of one to four supplied new-input cases, it then:

1. Uses the unchanged private direct native interpreter to obtain reference
   outputs and checks its runtime identity against externally trusted compatibility.
2. Executes the retrieved, linked program through the unchanged meta-runtime.
3. Uses the unchanged native verifier to compare every actual output, dependency,
   input binding and recorded call tree, not just the final trace hash.
4. Checks distinct runtime call IDs and Effect IDs and the selected root return.
5. Preserves result files, source and link identities, total native runs and a
   final receipt, or a failure record if execution raises an ordinary exception.

The gate allows at most 96 reference-plus-candidate native runs and 1,200 execution
seconds. It refuses to replace an existing process alarm. The native-output
byte ceiling is checked after each completed case; each individual frozen native
execution also applies its existing case-size limit. This is not a preallocation
guarantee against transient output growth before a check.

This is deterministic reuse of a known learned program on new numeric inputs,
not model inference on a new natural-language problem. The direct interpreter
is an independent execution path, not an independent demonstration of the
program's usefulness outside its original checked task. All outcomes remain
`UNQUALIFIED`; no promotion, learning, learned retrieval, retention or rollback
is asserted. The old fixed-B native demonstration remains unchanged.

## Pure verification

The final full META3 suite passed **611 tests**, with zero failures/errors/skips,
52.66 pytest seconds and 54.1999225 runner seconds. All 32 tested source/config
files and all 316 protected baseline files were unchanged. Neural and provider
imports were blocked. The only warning is the intentional duplicate-ZIP test.

```powershell
C:/Python314/python.exe -B tools/validate_local.py --output records/local_learned_reuse_002
```

Run this from the META3 directory and choose a new record-directory name when
rerunning. The record contains exact commands, environment, source hashes,
before/after protected checks, raw output and XML.

- Receipt SHA-256: `3f972c5982bd6b22bb6de2a30c75b82cd434588103e4e761129615dd8ffc854b`
- Stdout SHA-256: `bce182b0469e34f3ba557f659142f414128614a8b345dc12448177e0a252035f`
- XML SHA-256: `d6b06ac2ae60fc03bdfa4e648cba4152116f2d74117ff99a1fb68176a81aa08f`

The tests include real pure retrieval/linking with synthetic learning receipts,
exact float32-newness checks, and explicit mocked-native success/failure protocol
tests. A mocked `NATIVE_REUSE_EXECUTED` receipt is only a test fixture and cannot
prove GPU execution. Earlier 582- and 606-test records remain for history.

## Gates still open

- Complete v3 learning and its frozen full-packet and stored-semantic audits.
- Obtain a real correct learned action with positive held-out learning evidence.
- Build a source-bound launcher/request package and verify writer exit before
  starting a fresh reader process; this entrypoint does not attest to writer exit.
- Execute the real AWS reuse gate, then independently inspect the complete packet,
  published trace schemas, stored semantics and provider cleanup.
- Test retention, behavioral rollback and suspended-caller continuity before any
  skill qualification. Keep CAS and generic-control learning identities separate.

No extra AWS job or spending reservation was made for this code. The active
training source and both frozen evaluators were not changed.
