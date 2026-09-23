# CNCM Codex Homebase

## AWS execution preference — owner instruction, 2026-09-23

The owner said: "use aws as there is only 354 mb of 16 gbs locally" and asked
that all future agents be told. Use AWS for tests, builds, benchmarks, model
execution, training, and other memory-intensive or sustained compute. Keep
this laptop to lightweight editing, inspection, orchestration, and result download.
Do not silently fall back to local heavy execution if AWS is unavailable.
The 354 MB free out of 16 GB is the owner's reported snapshot, not a live measurement.
Record each cloud job's source, purpose, instance, resource/time/cost limits,
and cleanup. This instruction selects AWS for the current work; preserve
historical job records and their original device identities.


## This implementation branch: current user scope, 2026-09-23

The completed research checkpoint remains preserved. The current user requests
historical rescorer repair, an evaluation design before tuning, and the missing
focus-to-candidate analogy comparison. Read
records/helm_integrated_repairs_20260923/EVALUATION_DESIGN.md for selected checks
and limits. No new broad team, cloud spending or expanded agent allowance is selected.
The earlier report-only scope remains part of the historical investigation; it
does not prohibit these newly requested repairs in this separate worktree.

## Current run authorization — user instruction 2026-09-22

Read `docs/OWNER_RUN_AUTHORIZATION_20260922.md`. The user explicitly authorized
this project and future AI/LLM research runs in the live conversation. Do not
repeat the superseded per-run approval/signature request for ordinary in-scope
work. Preserve each job's source identity, explicit resource limits, actual
results and failures. An agent transcription is not an owner signature.

## Write boundary

All CNCM implementation work, tests, generated artifacts, documentation, and
playground changes must be created inside this directory:

`C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE`

The controlling build charter is:

`C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\cas_reasoner.txt`

Read the current charter before changing behavior or making a completeness
claim. Reconcile every claimed feature against executable code and tests.

## Protected sibling

Do not edit, move, delete, format, generate files in, or run write-producing
commands against:

`C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\CAS_RRK_v0.1`

That directory belongs to the separate DeepSeek workstream.

## External references

Files outside this homebase may be inspected when they are needed to recover
authoritative CAS/TKS definitions or understand existing compiler/runtime work.
Treat them as read-only inputs. Copy or derive implementation artifacts only
into this homebase, and record source identity and conflicts explicitly.

## Project separation

Do not import CAS Harness production trackers, model-audit backlogs, Pythia
evidence, Evidence Packet launch work, or unrelated deployment tasks into this
CNCM build. CAS Harness and the CAS Native Cognitive Machine are separate
projects.

## NEVER EDIT SOURCE WHILE A RUN IS IN FLIGHT

**This has already destroyed two runs.** Do not be the third.

`cncm/typed_pointer_worker.py:1516`, `_final_source_verification`, runs at the **very end** of a run and
requires the **live working tree** to still match the frozen input rows:

```python
require(canonical(contract.input_inventory(ctx["root"])) == canonical(ctx["config"]["inputs"]),
        "SOURCES_CHANGED")
```

So a single edit made at any point during a run does not fail fast. It fails **at the finish line, after
all the compute is spent**, and the whole run is discarded.

**The files you must not touch while a run is in flight** are the 258 rows of
`contract.input_inventory(root)`:

- anything under `cncm/`
- anything under `research/`
- the four pin sets under `records/typed_course_001`, `records/typed_interface_001`,
  `records/typed_matched_001`, `records/typed_practice_001`

**Safe to edit at any time:** root-level documents such as `AGENTS.md`, `BRAIN_LINEAGE.md`,
`AUDIT_PACK.md`, the worktree `CHANGELOG.md`, and anything under `records/typed_pointer_001/`. None of
these are in the inventory, which is why they can be written while training runs.

**Before starting any run, check whether one is already in flight:**

```powershell
Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
  Where-Object { $_.CommandLine -like '*preflight*' -or $_.CommandLine -like '*execute_study*' } |
  Select-Object ProcessId, CommandLine
```

**The two losses, so this is not abstract:** a study driver killed between its first and second job by
an interrupted tool call, taking a fully successful 1,470-update run's certificate with it; and a dry
run killed about nine minutes in by a concurrent edit to `pointer_learner.py`.

**The fix belongs in the code, not in discipline.** A check that discards a finished run should compare
the sources the worker actually **loaded** (`loaded_sources.json`, already produced) against the frozen
rows, rather than re-reading a live tree that the run did not consume.

## The learning brain — read this before touching the pointer work

The part of this machine that learns is named **Helm** and it is versioned. Before you run
anything that trains it, before you report anything about it, and before you pass this work on,
read and update:

`BRAIN_LINEAGE.md`

It is the single source of truth for the brain's name and version, how many learned numbers it
has, which worlds it was taught on, which worlds it was tested on and never shown, what it scored
before and after, whether a grader officially certified it, and the exact folder holding the proof.

Three rules that file will repeat and that are not negotiable:

- **A number is only a result if a grader printed it.** Run the grader and quote what it printed.
- **Never call an uncertified run a pass**, however good its numbers look. Write "measured, not
  certified" and give both numbers.
- **Never write or edit a certificate, a lifecycle record, or a ledger reservation by hand.** If a
  run's certificate is missing, that run is lost. Say so and run it again.

If you are here to **audit, verify, or independently test** this work rather than extend it, start
at `AUDIT_PACK.md` instead. It gives the exact commands, the exact frozen numbers, the file hashes,
the traps that have already fooled people, and eight attempts to break the claim that you are
expected to actually run and report on.

## Completion rule

Do not use a passing narrow test, a visible interface, a schema, or a document
as proof that the complete cognitive machine exists. Report each requirement as
implemented, partial, blocked by an unresolved authority decision, or absent,
with exact evidence.
