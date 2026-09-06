# Audit-runner input correction

The first clean-source attempt at `246f490d7d0dad2c18cc14a125b07e296ed74a3c`
stopped before the canonical validator started. The runner incorrectly required
`records/contrast_v7_exclusions_001/inventory.json`. That file was only a default
future output name in the exclusion builder, not an existing input.

The one-line correction uses the real, already committed prior inventory at
`records/contrast_v6_exclusions_001/inventory.json`. No production code, tests,
closed-package input, or protected file changed.

The failed attempt remains unchanged at `../run_001/receipt.json`:

```text
SHA256 cc51bb4ffa2697c4ebbfd3218ed23de1d3fc44b89ffa87fda4aae9dec67314ca
```

Its detached worktree `prototype-v7-audit-246f490d` is also retained. This failure
is an audit-runner input-list error, not a failed model, guard, or package test.

An independent fresh pure Python preflight checked every actual closed source,
protected file, retained helper, and known test input against its Git blob:
602 closed inputs, 316 protected files, 618 distinct verified files, zero missing
or changed files. These counts overlap and must not be added. Only the corrected
runner is deliberately excluded from equality with the old source commit.

`execution.json` preserves the exact inline command and captured output.
`check.py` preserves its source text for inspection. It did not import or run the
audit runner, create a worktree, start tests, generate tasks, or use models/GPU/AWS.
The full clean proof must wait for the corrected runner's new source commit.
