# How to reproduce everything

Every command below was run by the author on 2026-09-21/22 and the stated output is what was observed. If your
output differs, that is a finding — report it with both.

## Environment

- Windows 11. Python **3.14.0** at `C:/Python314/python.exe`.
- No third-party packages are needed for the CAS-Ohm module or the compiler. `pytest` is needed for the test
  suites (version observed: 9.1.1).
- Set `PYTHONIOENCODING=utf-8` or output containing CAS symbols (`^`, `∘`, `∈`) will fail to print on a
  cp1252 console. This is a display problem, not a code problem, but it will stop you mid-check.

## Two repositories, not one — read this before you get confused

This machine holds **two separate git repositories** that both push to the same remote:

| | path | git dir | note |
|---|---|---|---|
| **lab** | `…/_worktrees/helm3-lab` | `…/_worktrees/vision-next/.git` | the branch under audit, `research/helm-3.0-cas-lab` |
| **main** | `C:/Users/wakil/OneDrive/Desktop/tksCAS` | its own `.git` | on another agent's branch `codex/casformer-v0.2-release` |

A commit in one is **not** visible in the other. This is why the book canon exists as two commits with
identical content (`d50abbbc` in lab, `eb3c9b1e` in main): the main repository carried two of another agent's
unpushed commits, so pushing it would have published their unfinished work.

Also: the main repository's working tree stores some files **CRLF**; the lab worktree stores **LF**. Take all
digests over LF-normalised bytes:

```python
hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
```

---

## 1. The CAS-Ohm module — the clearest single check

From `…/_worktrees/helm3-lab/noetic-compass-scaffold/noetic-compass`:

```bash
python api/cas_ohm/test_quantifiers.py
```

**Observed:** `PASSED 48/48`

Before the change, from a scratch copy of `git show 078d00ed:…/api/cas_ohm/{quantifiers,test_quantifiers,__init__}.py`:

**Observed:** `PASSED 39/39`

### The defect itself

Run this against the **before** code and the **after** code:

```python
from api.cas_ohm import i_pred, r_total
inf, nan = float("inf"), float("nan")
i_pred(nan, 4.0); i_pred(8.0, nan); i_pred(8.0, inf); i_pred(inf, 4.0)
r_total(1e308, 1e308, 1.0, 1.0)
```

| call | before (observed) | after (observed) |
|---|---|---|
| `i_pred(nan, 4.0)` | `nan` | refused, `ValueError` containing "finite" |
| `i_pred(8.0, nan)` | `nan` | refused |
| `i_pred(8.0, inf)` | **`0.0`** | refused |
| `i_pred(inf, 4.0)` | `inf` | refused |
| `r_total(1e308, 1e308, 1.0, 1.0)` | `inf` | refused |

And unchanged in both: `i_pred(8.0, 4.0) == 2.0`, `y_hat(8.0, 4.0) == 2.0`, `r_total(1,2,3,4) == 10.0`,
`r_hidden(v=8.0, i_obs=2.0, r_known=2.0)` → magnitude `2.0`, `r_apparent` `4.0`; resistance `0.0` and `-2.0`
still refused.

---

## 2. The compiler test suites

From `…/_worktrees/helm3-lab/noetic-compass-scaffold/noetic-compass`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest --noconftest -o addopts= \
  tests/test_notation_compiler.py tests/test_notation_compiler_nesting_and_defects.py \
  tests/test_notation_compiler_continuation.py tests/test_offline_help_text_canon.py \
  tests/test_full_demo_program.py -q -p no:cacheprovider
```

**Observed:** `458 passed`

The 99 pre-existing tests in `tests/test_notation_compiler.py` were **not modified** by this work. Check:

```bash
git diff c3855275 HEAD -- noetic-compass-scaffold/noetic-compass/tests/test_notation_compiler.py
```

**Observed:** empty.

---

## 3. The lab test suites

**This one has a trap.** The Q4 key fixtures refuse to run if the temporary directory is inside the repository
under test. Point `TEMP` and `TMP` somewhere outside it, or you will get setup errors that look like failures.

From `…/_worktrees/helm3-lab/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/helm_cas_expression_lab`:

```bash
export TEMP=/some/dir/outside/the/repo TMP=$TEMP
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -o addopts= \
  test_compiler_nesting_facts.py test_foundations28.py test_operation_contracts.py \
  test_q3_behaviour_records.py test_q3_load_and_export.py test_q3_load_boundary.py \
  test_q3_load_errors.py test_learner_q4.py test_q4_followup.py -q -p no:cacheprovider
```

**Observed:** `348 passed in 200.42s`. Takes about three and a half minutes.

---

## 4. The book canon

The canon pin is `d50abbbc`. To see only the content change, diff it against the pre-edit tree:

```bash
git diff dbb388ee d50abbbc -- book/CAS_PCBA_Engineer/
```

**Observed:** 8 files, 202 insertions, 95 deletions. (Commit `0fc6bb30` alone shows 1765/1658 — that is the
line-ending mistake described in `04_WHAT_I_GOT_WRONG.md` item 2, fixed by `d50abbbc`.)

Line endings:

```bash
git ls-files --eol -- book/CAS_PCBA_Engineer/*.md
```

**Observed:** all 39 files `i/lf  w/lf`.

The two repositories hold identical book content — see `02_MANIFEST.json`, key
`canon_pin_cross_repository_check`, which reports `canon_pin_all_identical: true` over all eight changed files.

### The claim that the edits fix a real defect

The disputed sentence, before and after:

```bash
git show dbb388ee:book/CAS_PCBA_Engineer/Chapter_10_Special_Purpose_Components.md | sed -n '96p;98p;104p;111p'
git show d50abbbc:book/CAS_PCBA_Engineer/Chapter_10_Special_Purpose_Components.md | sed -n '93p;99p;105p;113p'
```

**The claim to test:** the committed text calls `XOR` a "dissonance detector — both `^2` and `^3` firing →
conflict flag". XOR fires when inputs *differ*, so it does not fire when both are active. Judge for yourself
whether "plainly wrong" is fair or overstated.

### My self-correction — check this hard

```bash
git show dbb388ee:book/CAS_PCBA_Engineer/Chapter_10_Special_Purpose_Components.md | grep -n "^[[:space:]]*gate [a-z_]*:"
git show dbb388ee:book/CAS_PCBA_Engineer/Appendix_E_Exercise_Answers.md | sed -n '327p'
```

**Observed:** `278:    gate dissonance: XOR< attract, averse >;` and `327:    xor dissonance: XOR< attract, averse >;`
— the chapter and its own answer key use different prefixes for the same declaration. This is what makes my
original published claim false and the correction `f46d34cb` necessary.

### The listing count

```python
import pathlib, re
blocks, names = 0, set()
for f in sorted(pathlib.Path("book/CAS_PCBA_Engineer").glob("*.md")):
    for m in re.finditer(r"^\s*(circuit|board)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", f.read_text(encoding="utf-8"), re.M):
        blocks += 1; names.add(m.group(2))
```

**Observed:** 58 blocks, 42 distinct names. (An earlier investigator reported 60; a designer said 58; I
re-counted and got 58.)

---

## 5. The compiler comparison that decided the merge

Load both compiler texts side by side from a scratch folder:

```bash
git show 7f32129d:noetic-compass-scaffold/noetic-compass/api/notation/compiler.py   # mine
git show 04547c55:noetic-compass-scaffold/noetic-compass/api/notation/compiler.py   # theirs
```

Digests over LF-normalised bytes: mine `f1a44678438a65c3…`, theirs `61ed5a45970459e4…`.

Then test each of the five points:

| expression | mine (observed) | theirs (observed) |
|---|---|---|
| `let X = ^8^C_{F2\|A} ∘ ^3^C; let Q = {X}; Q` | `['Phi<^8^C_{F2}:^3^C>']` — drops `\|A` | `['Phi<^8^C_{F2\|A}:^3^C>']` |
| `fn h(s) = s ∘ ^3^O; h(^8^C)` | no warning | cross-Domain warning |
| `fractal(^8^C, ^3^O)` | no warning | cross-Domain warning |
| `let P1_count = ^2^C; P1_count` | **refused** | accepted |
| `let F2_total = ^2^C; F2_total` | **refused** | accepted |
| `compile_file("docs/CAS_FULL_DEMO_APP.cas")` | invalid | valid |
| `compile_file("docs/CAS_FULL_DEMO_LIB.cas")` | invalid | valid |

**I had an interest in this comparison being tidy, since it decided whose work survived. Re-run it.**

---

## 6. No model was run

```bash
grep -n "import torch" …/research/helm_cas_expression_lab/learner_q4_neural.py
```

**Observed:** the import is inside `build_model`, not at module level, and `build_model` raises
`GPU_REQUIRED` unless given an explicit `cuda:N` device that exists. Nothing in this work calls it.

---

## 7. The other agent's work, which I verified before merging

From `…/_worktrees/codex-helm-data`, their own record is
`cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/continuation_20260921/VERIFICATION.md`.
It lists their commands. I re-ran all of them and observed: **458, 304, 92, 27, 2 passed**; Q3 v0.5 versus v0.7
all 24 row files identical; scaffold source, offline folder and ZIP carrying one compiler.
