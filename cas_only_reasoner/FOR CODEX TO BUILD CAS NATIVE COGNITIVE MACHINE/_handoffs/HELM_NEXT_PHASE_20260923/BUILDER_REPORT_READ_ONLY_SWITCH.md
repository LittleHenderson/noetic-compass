# Builder report: read-only analogy switch (2026-09-23)

Written by the temporary Claude builder. Codex is away. Label: `CLAUDE_BUILT_CLAUDE_CHECKED` once the
coordinator's checks run. Until then the change is **built and statically checked only**.

- **Status of the new tests: NOT_RUN.** Nothing was run with torch on the laptop (owner's AWS rule).
- Branch: `claude/helm-builder-continuation-20260923`.
- Parent: `a19eb7352eb666bc1f222e158f0f0c725395cf34` (coordinator records). Source parent: Codex `96644503`.
- Code commit: `098a3bdcc81ef3d31cb02f01299506d342cb2b6e`. This report is in the commit after it.

## What changed, in one paragraph

Before, the container stored the switch as two plain attributes. Anyone could overwrite them. Now the two
values are served by read-only "properties" on the container's class. A property is a small getter function
that Python calls when you read `model.analogy_focus_comparison`. It returns the argument `_build_container` was
called with, which is already checked to be a real `bool` (line 714). Two small guards make any assignment or
deletion of those two names raise `AttributeError`. No tensor, no random number and no saved key was added.

## Exact diff

File: `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py`

| | Old (`96644503`) | New (`098a3bdc`) |
|---|---|---|
| git blob | `caaff9dcfbae0ee2e271e354758eb48861ef8ba6` | `baa3608894e8a928f3f30af7a492f5d47ba3344e` |
| raw sha256 | `320024b4bc0c5930369934eabf06e6b9bd48163a819f81eda2063f040310c5bf` | `a94084f76553f6ee88989c34d6ea65af3fb7758e73625bbdbf680a867a7c56ea` |
| LF sha256 (CRLF→LF) | `b6b8a252b0d9ad0a695f97182d371f11c026020243ab6a33e6a8cac57780076c` | `08198047a91b2ae32d04d87ac94ce1d4577557983c5303b620247de54ad90768` |
| bytes | 157,534 | 159,216 |
| lines | 2,308 | 2,336 |
| CRLF lines | 2,241 | 2,241 |
| LF-only lines | 67 | 95 |

- The old raw sha256 `320024b4...` equals `source_sha256` in
  `records/helm_integrated_repairs_20260923/analogy_tensor_inventory.json`, so that inventory describes the old source exactly.
- **Inserted:** 30 lines, placed before old line 729 (new lines 729-758). All 30 use **LF** endings.
  - Why LF: the lines being replaced (old 729-732, added by `60e382b0`) are LF. Lines 727-728 above are CRLF.
  - Content: 8 comment lines, a class attribute
    `_READ_ONLY_SWITCH = ("analogy_focus_comparison", "analogy_seed")`, two getter-only `@property` methods, and
    `__setattr__` / `__delattr__` guards, plus blank separator lines.
- **Deleted:** old lines 731-732 (both LF):
  `self.analogy_focus_comparison = analogy_focus_comparison` and
  `self.analogy_seed = analogy_seed if analogy_focus_comparison else None`.
- `git diff --numstat`: `30 2`.

### Byte-level comparison (old blob from `git show 96644503:<path>` vs the new file)

- `difflib.SequenceMatcher` on lines **with their endings** finds exactly two changes:
  1. insert of new lines 729-758;
  2. delete of old lines 731-732.
- 2,306 lines are equal, byte for byte, endings included.
- The first 50,026 bytes are identical, up to the insertion point.
- The last 107,297 bytes are identical, from old line 733 to the end of the file.
- The CRLF count is unchanged at 2,241. No other line ending moved.
- `.gitattributes` gives this file `text: unset`, so git stores it as-is. `git show HEAD:<path>` equals the file on disk.

### Line-number shift for later readers

Every line after the insertion moves down by 28. Old 832 → new 860 (`if analogy_focus_comparison:`); old 836 → 864;
old 1524 → 1552 (`_world_scores` branch); old 1748 → 1776 and old 2160 → 2188 (the two default-ON builds).

## Why each invariant holds

1. **OFF behaviour unchanged; ON keeps its five tensors.**
   - The deleted lines only put two plain Python values into the instance `__dict__`. They were never parameters,
     buffers or state-dict entries.
   - Every line that builds a tensor is byte-identical: new 761-868 equal old 733-840.
   - The `state_dict` and `load_state_dict` overrides are byte-identical (new 879-895).
   - So the key order, shapes, initial values and random-number use cannot change.
   - The ON head is still built at new 860-867 under `fork_rng(devices=[])`, seeded from the same argument.
2. **No new tensor, buffer, Parameter, `_extra_state` or state-dict key; no new random draw.**
   - The inserted code makes no torch call.
   - It adds one tuple of two strings (a class attribute), two properties and two methods.
   - `get_extra_state` is not overridden. torch 2.11 writes an `_extra_state` key only when it is
     (`torch/nn/modules/module.py:2167-2170`).
3. **Default stays `True`; learner, checkpoint format, `restore_checkpoint` and scoring untouched.**
   - Line 703 is unchanged.
   - Everything after old line 733 is byte-identical, including new 1776, 2188 and 1552.
   - The checkpoint fingerprint reads `container.state_dict()` only (new 2194).
4. **`getattr(model, "analogy_focus_comparison")` returns a real `bool` equal to the argument.**
   - The getter returns the enclosing argument itself. Line 714 already requires `type(...) is bool`.
   - `json.loads('{"analogy_focus_comparison": false}')` yields Python `False`, which passes line 714.
   - `analogy_seed` returns `analogy_seed if analogy_focus_comparison else None`, the same expression as the old line 732.
5. **Assign and delete raise; `__dict__` writes change nothing.**
   - The `__setattr__` and `__delattr__` guards (new 749-757) raise
     `AttributeError("POINTER_ANALOGY_SWITCH_READ_ONLY:<name>")` for either name, whatever the value.
   - `object.__setattr__` and `object.__delattr__` bypass the guards. They then hit the property, which has no
     setter and no deleter, so they also raise `AttributeError`.
   - A class property is a "data descriptor". Python checks it before the instance `__dict__`. So a value written
     into `model.__dict__` is never returned, and `_world_scores` (new 1552) still takes the branch the argument chose.

### Checks (a)-(c) from the brief

- **(a) The build-time branch still reads the function's own `bool`.**
  - Proof by bytecode (compiled only, never executed).
  - `_build_container.co_cellvars` holds both names. `__init__` loads them with `LOAD_DEREF` (closure cells) at
    new lines 860 and 864.
  - The class body only binds the properties (`STORE_NAME`). It never reads the names as values. Its
    `LOAD_FAST_BORROW` entries pass the closure cells to the methods (Python 3.14 bytecode).
  - No container method reads or writes `self.analogy_*` (no `LOAD_ATTR` / `STORE_ATTR` on those names).
  - The same scoping was shown with a pure-Python analogue under Python 3.14.0.
- **(b) torch really raises: read from torch 2.11.0+cu128 source.** This is the same version as the T4 image.
  - `Module.__setattr__` (`module.py:1972-2075`). For a bool, int, None, str or plain tensor it ends at
    `super().__setattr__` (line 2075), so a getter-only property raises `AttributeError`.
  - **The property alone was not enough.** A `Module` value is registered as a new child with no check (line 2018).
    That would add state-dict keys. A `Parameter` or `Buffer` value raises `KeyError`, not `AttributeError`
    (`register_parameter` line 620, `register_buffer` line 574).
  - That is why the two guards were added. They refuse both names for every value type, before torch's code runs.
  - `Module.__init__` sets its own internals with `object.__setattr__` directly (lines 506-522), so the guard never
    sees them. `train()` sets `self.training` (line 2903); that name passes straight through.
  - `Module.__delattr__` (lines 2077-2086) falls to `object.__delattr__`. The guard also covers the case where
    someone planted the name in `_parameters`, `_buffers` or `_modules`.
  - No torch code tests whether `__setattr__` is overridden: a grep of `torch/nn`, `torch/optim` and
    `torch/utils/checkpoint.py` found nothing.
- **(c) Nothing else reads or writes these attributes.**
  - `git grep` over the whole committed tree at HEAD, including folders outside the sparse checkout, finds readers
    only at `pointer_learner.py` (703, 714-715, 832, 836, 1524 old numbering) and the existing test's constructor
    call. Other matches are records and handoff prose.
  - No code in `typed_teaching/` assigns any attribute onto the container, and none uses `__dict__`, `vars()`,
    `torch.compile` or `functional_call` on it.
  - The other callers of `_build_container` are frozen historical copies under `records/` (old signature) and
    `records/typed_pointer_001/rounds_iterate_check.py:67`, which reads no switch attribute.

## New test file

`tests/test_helm_analogy_switch_read_only.py`: blob `f592bd63f05217b164a78d272eb510aff44c68e4`, sha256
`1ce84d1f08b298cf4e3b67cf330db7edc925255246402844e0226049cbdde340` (LF-only, so raw = LF), 340 lines.

- It copies `container`, `reading`, `forward` and the `legacy_scores` fixture from the existing test. The fixture
  reads `records/helm_failure_research_20260922/agents/A2/source_copies/helm2/pointer_learner.py`.
- The existing `tests/test_helm_analogy_focus_comparison.py` is **not** edited.
- 10 test functions. With parametrization that is 25 cases: 24 on CPU and 1 on CUDA, which is skipped when CUDA is absent.

| Brief item | Test function | Cases |
|---|---|---|
| (1) bool equal to the argument, for default / True / False / `json.loads` false and true; seed 20260923 ON, None OFF | `test_switch_reads_back_as_the_requested_bool` | 5 |
| (1) extra: a non-bool switch (`0`, `1`, `None`, `"false"`, `0.0`) is refused at build with `POINTER_ANALOGY_SWITCH` | `test_non_bool_switch_is_refused_at_construction` | 5 |
| (2) structure: getter-only class properties, no instance, parameter, buffer or module entry, no `get_extra_state`; other attributes and `train()` still work | `test_switch_is_served_by_getter_only_class_properties` | 1 |
| (2) assignment (11 value types, including Parameter, Buffer and Module), `del`, `object.__setattr__` and `object.__delattr__` all raise `AttributeError`; value and layout unchanged; ON and OFF, both names | `test_assignment_and_deletion_raise_and_leave_the_value_unchanged` | 4 |
| (3) `model.__dict__` writes change neither getattr nor the branch; forward hooks show which head ran; OFF equals legacy | `test_instance_dict_writes_change_neither_value_nor_scoring_branch` | 2 |
| (4) `hasattr(analogy_head)`; OFF keys = ON keys minus the 5; the 5 shapes; 174303 / 203424 parameters; no buffers; no `_extra_state` or switch-named key | `test_layout_head_presence_and_parameter_counts` | 1 |
| (5) OFF and ON key/shape lists equal the inventory rows (read from the JSON); `new_tensors`, element counts, totals and `analogy_seed` agree | `test_layout_matches_the_committed_tensor_inventory` | 1 |
| (6) after 8 refused change attempts: ON analogy scores come from `analogy_head` (hook count and output match); OFF equals legacy; definition and context stay legacy; `head_logits` dispatch; seeds 730-732; examples chain, star, domain 2 | `test_scoring_branch_survives_attempted_changes` | 3 |
| (7) CPU RNG state equal after ON vs OFF construction, in both orders; shared tensors equal; reading and refused writes draw nothing; ON head depends only on the analogy seed | `test_cpu_rng_state_and_shared_tensors_equal_after_on_and_off_construction` | 2 |
| (8) CUDA: `torch.cuda.get_rng_state_all()` and CPU state equal after ON vs OFF; all shared tensors equal on cuda; switch still read-only | `test_cuda_rng_state_and_shared_tensors_equal_after_on_and_off_construction` | 1 (skipif) |

Static checks done locally: `py_compile` passes; `ast` parse passes; LF only, no tabs. Every `P.<name>` the test
uses exists at module level in `pointer_learner.py` (checked with `ast`, not by importing).

## What I could NOT verify locally

- **No test was run.** All 25 new cases are NOT_RUN, and the existing 11 cases are NOT_RUN against the new source.
- The torch behaviour in (b) comes from reading the torch 2.11 source plus a pure-Python analogue. It was not executed with torch.
- That OFF and ON scores, tensors and RNG states are unchanged is argued from byte-identity of every tensor-building
  and scoring line. The T4 job is what measures it.
- The CUDA case, test timing ("seconds"), and whether `picked(...)` indexing matches `_world_scores` exactly all
  need the run.

## Known limits, stated plainly

- Replacing the property on the class itself, for example `type(model).analogy_focus_comparison = ...`, would
  still change the value. Each `_build_container` call makes its own class, so it would affect only that one model.
  The contract does not ask for protection against this, and I did not add any.
- `profile()` hashes raw source bytes, so the learner profile digest changes with this commit. This is by design.
  Records that pin `320024b4...` describe the old source.
- I did not edit `CHANGELOG.md`, the spec sheet or `CLAUDE_CONTINUATION_LOG.md`. The brief limits me to these three files.
- Not addressed (out of scope, already recorded by the coordinator): `preflight_dry_run.py` lists 48 container
  names, while the default container has 53.

## EXPOSURE: files outside my working copy that I opened

- **torch source, read only, never imported**, in `C:/Users/wakil/venvs/cas-gpu/Lib/site-packages/torch/`:
  - `nn/modules/module.py`: lines 480-530 (grep), 555-594, 1955-2089 and 2886-2905 (grep), plus a grep for
    `get_extra_state` / `state_dict`;
  - `version.py` (first 5 lines);
  - greps only: `nn/parameter.py` (`class Buffer`), `nn/__init__.py`, `cuda/random.py` (`get_rng_state_all`),
    `random.py` (`fork_rng`), and a grep of `nn/`, `optim/` and `utils/checkpoint.py` for `__setattr__` fast paths.
- **Existence checks only:** `C:/Python314/Lib/site-packages/torch/nn/modules/module.py` (not present); the
  directory listing of `C:/Users/wakil/venvs`.
- **My own scratch files** in the session scratchpad: a copy of the old blob, and two `.pyc` outputs from `py_compile`.
- **Repository objects outside the sparse checkout, through `git grep` over HEAD** (matching lines only, not whole
  files): root `CHANGELOG.md:1612`, `records/typed_pointer_001/*`,
  `records/helm_failure_research_20260922/agents/A4/SOURCE_EXCERPTS.md`, and copies under `records/typed_pointer_001/admission_*`.
  No matched path contained `hset1a` or `SEALED`.
- **Preloaded by the Claude Code harness, not opened by me:** the user's global `C:/Users/wakil/.claude/CLAUDE.md`,
  the main checkout's `CLAUDE.md`, and the auto-memory index `MEMORY.md` under `C:/Users/wakil/.claude/projects/`.
  These are instruction and index text, not session transcripts. They contain no sealed material.
- **Not opened:** `D:/tksCAS-archive/`, any `*SEALED*` file, any `hset1a` path, `D:/tksCAS-worktrees/helm-integration/`,
  other worktrees, AWS or S3, and any session log or transcript.
- **Other actions:** one read-only local process listing (checking no study run was in flight). No AWS call.
