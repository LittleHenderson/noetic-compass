# Cold v7 parent and public-loader check

The portable parent and the runtime public loader passed this bounded check.
This is preparation evidence, not a GPU run or a learning result.

## Results

- The parent rebuilt all **9 files byte-for-byte** from the saved diagnostic base.
- The export contained **8 files** and no `test_private.json`.
- A separate fresh Python process loaded the export twice. Both loads agreed.
- Public loading made **0 private-file reads, 0 problem-parser or generator
  calls, 0 parent-code imports, 0 subprocess/Git calls, and 0 network attempts**.
  The loader did not add an import hook or change `sys.path`.
- The bridge suite passed **12 tests and 15 subtests**.
- The separate synthetic exposure suite passed **8 tests and 3 subtests**.
- All **27 watched source files** had the same hashes before and after.
- All four child processes exited 0. No test failed or skipped.
  Total measured wall time was **15.324246099999073 seconds**.

The parent was permitted to read private targets to check the bundle. The
public process was not. Private graph separation and private depth counts in
the public receipt remain externally pinned parent findings; the public
loader does not independently recheck those private facts.

## Exact inputs and identities

This check used only the previously saved **seed 926603** diagnostic bundle.
It copied the existing five base files, appended the exact 256 known prototype
tasks, and generated no new task graph.

| Split | Tasks | Depth counts |
| --- | ---: | --- |
| Train | 352 | 1: 32; 2: 160; 3: 160 |
| Validation | 24 | 1: 8; 2: 8; 3: 8 |
| Test | 9 | 3: 6; 4: 3 |

The original 96 training records remain the prefix. All 256 imported records
and 128 pairs remain intact. Validation and test bytes are unchanged. The
tokenizer was fitted on the 352 training records only.

- Original and rebuilt merged manifest SHA-256:
  `19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29`
- Base manifest SHA-256:
  `36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1`
- Public loader SHA-256:
  `5db831d685b2343a16b93cbc3d3c16e53978ebf0e3cf9da8fefd7d10692708b0`
- `source_pins.json` SHA-256:
  `9d66a81fbdc0e4041cd09d460c821f3cf68e244610ed49831324b5accf74084d`
- Dataset identity:
  `737f37d91a262a4603f02950defbfb8f9360fdc7b72615ff0ad945461e4d530b`
- Final receipt SHA-256:
  `86eac9caece5cecd734579681f570327015c9018a26c5da1790d9b47327168a8`

The source-pins file is the exact canonical `source` object from the
externally pinned original merged manifest. It binds the adapter and 16
frozen files from `acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0`. The public
loader has its separate external pin. The new runtime wrapper and test
files are candidate bytes recorded in the before/after hash maps; this
check does not claim that they already belong to a source-freeze commit.

## Execution and retained records

The command actually run was:

```powershell
& 'C:/Python314/python.exe' -B 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/contrast_v7_bridge_checks_001/run.py'
```

Working directory:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION
```

The runner started four isolated children, using the same command with
`--phase parent`, `--phase public`, `--phase bridge`, and
`--phase exposure`. Exact commands, UTC times, output hashes, environment
identity, and source maps are in `receipt.json`. Each child had a declared
180-second limit. All finished normally; none needed a retry.

This used the existing **Python 3.14.0** installation at
`C:/Python314/python.exe`. It was **not a fresh-environment installation**
and was not a wheel-install check. Python bytecode writes, pytest plugin
autoload, GPU tests, neural imports, and provider imports were disabled.
The parent and public API phases additionally rejected subprocess, shell,
and network use. No Git command was used by this runner.

Files to inspect:

- `run.py`: executable check and traps.
- `plan.json`, `source_pins.json`: externally bound input and source identities.
- `parent_result.json`: merge/export receipts and all output hashes.
- `public_result.json`: both public load receipts and zero trap counters.
- `bridge_tests.json`, `exposure_tests.json`: individual passing test IDs.
- `parent.stdout.txt`, `parent.stderr.txt`, `public.stdout.txt`,
  `public.stderr.txt`, `bridge.stdout.txt`, `bridge.stderr.txt`,
  `exposure.stdout.txt`, `exposure.stderr.txt`: exact child outputs.
- `roundtrip/base_dataset/`: five copied input files.
- `roundtrip/dataset/`: nine byte-identical merged files.
- `roundtrip/trainer_input/`: eight public export files.
- `receipt.json`: final evidence binding.

A short retained temporary directory was used:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_tmp/prototype-v7-bridge-00f4d1036b7b
```

The runner refuses to overwrite an existing plan or receipt. To repeat it,
place unchanged `run.py` in a new empty sibling directory under this
package's `records/`, preserve the referenced saved inputs and source
bytes, and run it there. Do not rerun child stages into this retained record.

## Boundaries

No model, tensor, GPU, provider, paid operation, live v6 data, or registered
seed 2026092601 was used. The exposure tests used synthetic values, not a
completed experiment's data. No accepted model, executor, or production
source was changed by this check.

The older local adapter installs strict pure-process checks and expects its
own import state. The portable parent was therefore checked in one cold
process, and public loading in another. No legacy fixture process was
reused and no source check was weakened. This proves the cold portable API
path on the known diagnostic data; it does not establish AWS launch,
training completion, held-out performance, or a CAS-specific advantage.

