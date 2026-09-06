# V7 saved-rejection diagnosis

All 59 trained CAS rejections ended in a grammar state with no legal continuation.
None was caused by a saved illegal token or the 256-token limit. In 54 of these
59 outputs, the existing two-check diagnostic detects an earlier locally allowed
`PROC` choice that cannot produce a fully reachable program. The other five
also finish with `UNREACHABLE_PROCEDURE`, but neither early check identifies a
witness. This does not explain why the neural model chose those tokens.

The existing analyzer was run unchanged. Its full measured output is
[diagnosis.json](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_rejection_diagnosis_001/run_001/diagnosis.json>),
SHA256 `6221afb137ed5a35654d5c9bdde71569c271825c9530b31a5ca7a8061a1d41d4`.
It contains every saved rejected row, full token streams, exact token indices,
state snapshots, hashes, and counts by depth and held-out condition.
[Representative witnesses](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_rejection_diagnosis_001/WITNESSES.md>) explain four distinct cases.

## Measured rejection counts

Each arm had 72 scheduled cases. This table counts only rejected actions.
The non-rejected execution outcomes remain in the frozen V7 report.

| Saved arm | Rejected | Grammar dead end | Complete-action native admission rejection | Earlier PROC witness | No early witness |
| --- | ---: | ---: | ---: | ---: | ---: |
| CAS untrained | 72 | 72 | 0 | 72 | 0 |
| CAS trained | 59 | 59 | 0 | 54 | 5 |
| Generic untrained | 72 | 72 | 0 | 72 | 0 |
| Generic trained | 53 | 52 | 1 | 47 | 6 |
| Total | 256 | 255 | 1 | 245 | 11 |

The generic no-witness count includes five replayed grammar dead ends and one
complete action whose emitted tokens were not recorded. Thus there are
**10 replayed streams without an early witness**, not 11 failed early replays.

Every one of the **255 available saved token streams** obeys each actual
`grammar_v3` token mask. Counts across these streams:

- Malformed IDs or disallowed emitted tokens: **0/255**.
- Length exhaustion or final-EOS reservation: **0/255**.
- Stopped incomplete with a legal continuation still available: **0/255**.
- Noncompletable terminal grammar state: **255/255**.

The native rejection has no saved token stream. The analyzer does not invent one
by serializing its completed action. The receipt's
`saved_reason_matches_replay = 256` means 255 matching generator-rejection
replays plus one matching native-admission classification, not 256 token replays.

### First empty mask and terminal reason

| Saved arm | procedure_or_eos: no declaration or valid completion | call_target: no legal child target | No recorded token stream |
| --- | ---: | ---: | ---: |
| CAS untrained | 32 | 40 | 0 |
| CAS trained | 59 | 0 | 0 |
| Generic untrained | 28 | 44 | 0 |
| Generic trained | 52 | 0 | 1 |
| Total | 171 | 84 | 1 |

All 171 `procedure_or_eos` endings have
`terminal_completion_error = UNREACHABLE_PROCEDURE`. All 84
`call_target` endings have `PROGRAM_PREFIX_INCOMPLETE`.
Both the actual terminal allowed set and the raw set without the token budget
are empty. The saved stream lengths are 32–116 for each untrained arm,
80–138 for trained CAS, and 64–138 for trained generic. The bound is 256.

The generator labels all 255 streams `GENERATION_GRAMMAR_DEAD_END`.
The evaluator's later `ACTION_FIELDS_INVALID` describes its rejection wrapper;
it is not proof that a malformed token was emitted.
The one complete-action rejection is trained generic case 34,
`NATIVE_TOPOLOGY_MISMATCH`.

### First detected impossibility versus repeated occurrences

The first detected impossibility is `PROC_WITH_NO_PENDING_FORWARD_CALL` in
245 streams: 72 CAS untrained, 54 CAS trained, 72 generic untrained, and 47
generic trained. No stream has `CALL_WITH_NO_LEGAL_TARGET` as its first
detected impossibility; 84 untrained streams encounter that check later.

Across full streams the checks find 425 PROC occurrences and 84 CALL
occurrences. These are repeated token events, not 509 tasks. They do not
identify the earliest causal model error, nor necessarily the earliest
noncompletable prefix.

Trained CAS rejections by depth: 38/48 scheduled depth-3 cases, with 35 early
PROC witnesses; 21/24 scheduled depth-4 cases, with 19 early PROC witnesses.
The five without either early witness are cases **26, 45, 52, 60, and 70**.
The receipt also preserves same-depth, wording-shift, and deeper-call counts.

## Exact execution and retained records

Recorded shell working directory:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION
```

Recorded outer commands:

```powershell
C:/Python314/python.exe -I -S -B records/prototype_v7_rejection_diagnosis_001/capture.py checks_003 tests
C:/Python314/python.exe -I -S -B records/prototype_v7_rejection_diagnosis_001/capture.py execution_001 diagnose run_001
```

These names are already occupied. For a new local rerun, use fresh direct-child
output names; the capture refuses overwrites.

- [Finisher pure-test receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_rejection_diagnosis_001/checks_003/execution_receipt.json>):
  SHA256 `bb1843ac0f01a89e6f4e461708b11a5e08172c0c658256a55474f741dc2a7015`;
  child 74008, exit 0; 16 test methods, including six malformed-ID subcases.
- [Test raw stderr](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_rejection_diagnosis_001/checks_003/stderr.txt>) contains the complete unittest
  output; stdout is empty. Prior checks_002 also passed the same 16 tests.
  Repeating them does not establish 32 distinct tests.
- [Actual diagnosis execution receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_rejection_diagnosis_001/execution_001/execution_receipt.json>):
  SHA256 `b81c6c6a5ada7622dbbd19d6257f6ee5046c233f85da4f5ea6ec71bffb396035`;
  child 16144, exit 0, 39.890376799998194 seconds;
  2026-09-06T12:21:59.104451+00:00 to 12:22:38.994985+00:00.
- [Diagnosis raw stdout](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_rejection_diagnosis_001/execution_001/stdout.txt>) is 1,157 bytes,
  SHA256 `14e51c7c8f88f34a3a8f2917898f25419d48339d5d5fcd7fdf1d024efe949dde`.
  Raw stderr is empty.
- checks_001 retains two empty streams without an execution receipt.
  Its outcome is unproven; it is not labeled a failed or successful test run.
  No prior records were removed or rewritten.

Analyzer source identities, unchanged during both commands:

| File | SHA256 |
| --- | --- |
| analyze.py | 247a0d6484e856f331e83ea4d8b01bfaa6a2953930f3ec19eb2b4fa94d0a416f |
| capture.py | 9acf33a3617304807fc630d3f40f296b4206b3ff77c3a90e681017104f5586a2 |
| test_analyze.py | 4178eb51ce738b93ee55a37ad128e32f541747e22ae607598fa9e9b4268ea927 |

## Evidence boundaries

The analyzer binds the source to
`42f9164754312f12850d9b8789c062fa7fb8069f`, verifies all 603 source files
against the archive and Git, verifies the 316 protected baseline files, and
checks source bytes again at the end. It verifies every extracted packet file
against the pinned archive before replay and again afterward. Checkpoints and
SQLite files are only byte-hashed, never loaded as models or opened as databases.

The pure replay imports the actual v3 grammar and the two already-existing v4
viability checks. It does not run the v4 decoder, generate a repaired sequence,
replace a token, consult a gold program, execute a native program, load a model,
train, or call AWS. It does not change source, decoder, scoring, baseline,
budget, or V7 task results. CAS remains **0/72 correct**.

A completion filter would need separate development tests and a prospective
registered comparison. This replay does not show what an alternative decoder
would emit or whether any emitted replacement would answer the task correctly.
In the earlier v4 fixed-checkpoint decoder comparison, CAS remained 0/72 under
both decoders; those opened tasks and older checkpoints are separate evidence.
