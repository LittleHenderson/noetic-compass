# Candidate grammar correction — no learning result yet

The failed ec9 v3 run is preserved in evidence commit `608b59a5`. Its retained
verdicts report CAS 0/72 correct tasks, generic trained 12/72 and rule 72/72.
This candidate does not rewrite those outputs or change that result.

`cas_meta2/grammar_viability_v4.py` wraps the unchanged v3 prefix grammar. It
consults generated tokens only, never the problem, expected program, answer,
native result or model scores. It removes two choices:

1. `PROC` after all declared procedures are closed and no forward call awaits a
   declaration. Existing closed procedures cannot gain another call, so any new
   procedure would be unreachable from main.
2. `CALL` when the original grammar admits no call target. No next token could
   complete that instruction.

All other token choices, IR limits, scopes and vocabulary remain unchanged.
In particular, a helper may still be declared before a pending later caller;
forward and backward calls remain legal. This is not a complete solver for
whether every prefix can finish. Other dead ends remain explicit rejections.

The change is not wired into the frozen v3 policy, checkpoint or evaluator.
It has not run neural inference on AWS. Before a new learning claim, register
a separate comparison using the same correction for CAS and generic models,
trained and untrained. Do not treat a mask-only improvement as a training gain.
Do not repair recorded predictions or silently reuse exposed test tasks as new
held-out examples. Preserve the accepted executor and baseline weights.

The test suite checks the two rejected choices, constructor/from-ID enforcement,
branch isolation, and reuses the existing synthetic valid-language corpus for
nested and backward calls, all sixteen procedures, scope orders, repeated calls,
earlier returns and random acyclic graphs. These are pure language checks, not
model performance or native execution evidence.

## Local validation

`records/local_grammar_viability_v4_001/receipt.json` records 1,148 passed test
functions and 178 passed subtests, zero failures/errors and seven skipped GPU
modules. The run took 232.1689695 seconds. All 99 source/config files and all
316 protected baseline files were unchanged during validation. Neural and
provider-client imports were blocked. No GPU inference or training was performed.

Run from META2 using a new record directory:

```powershell
C:/Python314/python.exe -B tools/validate_local_v3.py --output records/local_grammar_viability_v4_002
```
