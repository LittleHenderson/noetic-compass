# Where the saved generated programs differ

The unchanged-checkpoint comparison did not solve any complete CAS task.
This additional, pure-JSON analysis locates literal structural differences
between saved generated programs and the already-exposed targets. It does
not run the model, repair predictions, or replace the task verifier.

Run from `research/CAS_META_2_COMPOSITION`:

```powershell
& C:/Python314/python.exe -B records/ablation_program_errors_v4_001/run.py
```

The script checks the complete packet SHA-256 before and after analysis,
records the three input-file hashes and its own hash, and passes seven
small structural-comparison assertions. The output is exclusive-create:
use a separate record directory for a rerun rather than overwrite evidence.

The corrected decoder produced 36 CAS programs; none matched the target.
Among those 36, overlapping difference categories include:

- 17 with missing procedures;
- 30 with different return values and 30 with different step inputs;
- 29 with different CJT choices, 28 with different child-call targets,
  23 with different step counts and 17 with different step kinds.

Another 36 CAS generations still ended at a grammar dead end. The original
decoder produced 19 programs and had 53 grammar dead ends. The exact
per-case differences are retained in `receipt.json`.

This points to several learned-content problems, not only stopping syntax.
The next candidate should be tested on procedure coverage, child-call
selection, input connections and returns, then on complete native outcomes.
These counts do not prove the causal reason the model learned poorly.

This is literal JSON comparison, not semantic equivalence. For example, the
generic model has 11 exact target-program matches but 12 recorded correct
task outcomes. Do not substitute exact-match counts for task correctness.
The stored native outcome audit remains a separate check.
