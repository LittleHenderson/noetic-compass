# Fable: Helm + CAS implementation package, v1.0

## Execute the bounded program
Start with `agent_prompts/F0_FABLE.md`, `DIRECTIVE.md`, and `AGREEMENTS_AND_DIFFERENCES.md`. Then assign `TASKS.json` and execute the relevant `ACCEPTANCE_TESTS.json` vectors. All task/vector states begin PLANNED. This is not a preaccepted implementation.

The decision is explicit: finish the trustworthy Helm baseline while building a standalone CAS Expression Lab from audited engine semantics. Integrate the tested mechanism into an experimental Helm lineage. Extend to typed PCBA only after its parser and behavior contracts are defined. Do not replace Helm with CAS-Native or make Jev/Dream-RSI prerequisites.

## First command for the handoff package
```
python tools/verify_package.py .
python tools/math_sanity_checks.py
```
These check this package and small mathematical examples only. They do not run Helm, inspect the user's repository, validate a CAS ontology, or authorize training.

## First checkout commands for Fable
Use the actual selected repository working directory, not this package folder:
```
git rev-parse --show-toplevel
git status --short
git branch --show-current
git rev-parse HEAD
git worktree list --porcelain
```
Then inspect current owner/repository guidance, resolve the reported local SHAs, and record imports and permissions. The branch may be unpushed. Do not use remote absence as evidence that the local changes do not exist. Exclude unselected agent worktrees from broad content searches, but never delete them automatically.

## Required runnable interface to deliver
Implement a small CLI or an equivalent repository-native interface with these operations:
```
python -m cas_expression_lab discover --output <new-audit-dir>
python -m cas_expression_lab build-data --contract <frozen-contract> --plan <frozen-plan> --output <new-data-dir>
python -m cas_expression_lab train --plan <frozen-plan> --authorization <verified-permission-record> --output <new-run-dir>
python -m cas_expression_lab evaluate --run <run-dir> --evaluator <trusted-evaluator-reference>
python -m cas_expression_lab intervene --run <run-dir> --cohort <frozen-development-cohort> --output <new-intervention-dir>
python -m cas_expression_lab export-rpa --run <run-dir> --output <new-view-dir>
```
**These commands are proposed deliverables, not existing executable commands in this handoff.** Fable may use the repository's established command names instead, but must publish the exact implemented equivalents and test them. Evaluation credentials or protected targets must never be made accessible to the training process. Training must stop with a clear permission error if the resource record is insufficient.

## Execution order
Q0 source/evaluator integrity; Q1 real Helm baseline; Q2 operation contracts; Q3 behavior-paired data and sealed splits; Q4 encoder/decoder/modules; Q5 interventions and matched evaluation; Q6 experimental integration and replayable delivery; Q7 later PCBA extension.

Q2/Q3 preparation can run in parallel with baseline repair. T19 confirmatory benefit testing and T23-T25 PCBA extensions do not block a clearly labeled engineering release when genuinely permission/semantics-blocked. Such a release must not claim those missing results.

## Files
- `DIRECTIVE.md` and `FABLE_HELM_CAS_Implementation_Directive_v1.pdf`: primary directive; PDF also includes the comparison ledger.
- `AGREEMENTS_AND_DIFFERENCES.md`: source-faithful agreement, disagreement, and decision ledger.
- `TASKS.json`: accountable owners, dependencies, outputs, planned acceptance references.
- `ACCEPTANCE_TESTS.json`: planned tests with methods and expected outcomes.
- `agent_prompts/`: seven role-specific instructions.
- `templates/`: permission, experiment, adaptation, handoff, and release templates.
- `schemas/`: proposed operation and training-record envelopes.
- `sources/`: byte-preserved uploaded reports/result, a labeled pasted-message excerpt, source map, and exact hashes.
- `tools/`: offline package and mathematical checks.
- `PACKAGE_MANIFEST.json`: hashes every distributed file except itself.

A package hash detects mismatch, not author authentication. The external evaluator trust boundary must be implemented in the project independently. Package checks are not acceptance of future code.
