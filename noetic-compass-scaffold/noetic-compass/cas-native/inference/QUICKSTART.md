# CAS-Native CLI — Quickstart Runbook

How to start, run, and demo CAS-Native through the unified `cas` dispatcher.

---

## 0. What you're running

The **CAS-Native v0** is a structured-prediction model that takes natural-language input and produces a CAS v7.7 expression — predicting Noetic, Domain, Drive, Register, and structural flags simultaneously.

**Active checkpoint:** `K=9 baseline` (commit `3232f05`, run dir `structured-token-recoverable-paraphrase-v77fix-...`).

**Held-out performance:** 93.2% canonical-exact on a 1K rigorously overlap-filtered eval.

**Known limitation:** the model was trained on the recoverable Level 3 surface distribution. Plain colloquial English is out-of-distribution and the model collapses to its most-populated prior. The CLI mitigates this with a rule-based rewrite shim, but you'll see ~50% of free-form prompts route to `meta_logic`. This is the **modality mismatch**, not a bug. Use `/menu` or `/sample` to demo the model's actual capability.

---

## 1. Prerequisites

| Requirement | Verify |
|---|---|
| Python 3.10+ | `python --version` |
| `torch` (CPU is fine) | `python -c "import torch; print(torch.__version__)"` |
| `rich` library | `python -c "import rich; print(rich.__version__)"` |
| Repo at `C:\Users\wakil\OneDrive\Desktop\tksCAS` | `cd C:\Users\wakil\OneDrive\Desktop\tksCAS && dir cas.bat` |

If `torch` or `rich` is missing:
```
pip install torch rich
```

---

## 2. Smoke-check the dispatcher

```
cd C:\Users\wakil\OneDrive\Desktop\tksCAS
python noetic-compass-scaffold\noetic-compass\cas-native\inference\cas_cli.py --test
```

Expected: prints version block, then the 21-prompt demo table, then runs one prediction. Exits with `rc=0`. **If this fails, stop and fix before proceeding** — none of the user-facing commands will work.

---

## 3. The five subcommands

### `cas help` (and bare `cas`)
Banner with all subcommands. Start here when showing the CLI to someone new.

### `cas chat`
The interactive REPL. The headline demo.

```
cas chat
```

Inside the REPL:

| Command | What it does |
|---|---|
| (any free-form text) | Detects CAS signal via the rewrite shim; if signal is found, rewrites to training-surface format then predicts; otherwise predicts directly with an out-of-distribution warning |
| `/menu` or `/m` | Numbered list of all 21 curated demo prompts grouped by bucket — pick by number |
| `/sample` or `/s` | Random demo prompt + prediction |
| `/raw` | Toggle showing the raw 12-key prediction dict alongside English |
| `/help` | Re-show the banner |
| `/exit`, `/quit`, `/q` | Leave |

### `cas demo`
Print the 21 curated starter prompts (no prediction). Use this as a printable cheat sheet — handy when handing the CLI to someone unfamiliar.

```
cas demo
```

### `cas predict "<text>"`
One-shot. Loads model, predicts, renders, exits. For scripting / piping.

```
cas predict "I keep practicing the same scale every day"
cas predict "I can't stand it when people interrupt me" --raw
```

### `cas notation "<expr>"`
Pass-through to the existing CAS compiler at `api/notation/cli.py`. Compiles a CAS expression to JSON, lex output, parse tree, or check result.

```
cas notation "^3^E_{F2}|A"
cas notation "^3^E_{F2}|A" --mode check
cas notation --grammar
cas notation --repl
```

### `cas version`
Project version, checkpoint, training-time metric, build date.

---

## 4. Demoing to someone new — the recommended script

1. **Open a clean shell**, `cd` into the repo.
2. `cas help` — show them the surface.
3. `cas demo` — show them the 21 starter prompts grouped by bucket.
4. `cas chat`, then `/menu`, pick a number from each bucket. The first impression should be: *the model gets the structured CAS expression right, in English.*
5. **Then, and only then,** invite them to type free-form English. Lead with: *"This is where the model is still learning — if it routes to `meta_logic`, that's the documented modality limitation."* Honesty up front avoids surprise.
6. If they ask "what's the next step?" — direct to `docs/working/cas_native_conversational_broadening_proposal_2026_05_04.md`.

---

## 5. Reading a chat turn

```
INPUT            <what the user typed>
DETECTED SIGNAL  Noetic ^3 (1.00), domain E (0.83), drive F4 (0.50), register |f (0.92)
REWRITTEN        As a notation exercise, map this structure into CAS: families: state expression; ...
CAS PREDICTION   ^3^E_{F4}|f
ENGLISH          Reading this as `^3^E_{F4}|f` — a felt aversion (^3 Negative on the
                 Evaluative domain, expressed in Affective register), driven by F4
                 Connection. Did I get that right?
```

- **DETECTED SIGNAL** appears only when the rewrite shim detected enough axes to rewrite. Confidence floats are `[0.0, 1.0]`.
- **REWRITTEN** appears only when the rewrite shim transformed the input. If the input is already in training-surface format (e.g., from `/menu`), this row is skipped.
- **RAW** appears only when `/raw` is toggled on. Shows the 12-key prediction dict.

---

## 6. Common issues

### `ImportError: No module named 'torch'`
You're on a Python install that doesn't have torch. Run `pip install torch`. ~700 MB.

### `ModuleNotFoundError: No module named 'rich'`
`pip install rich`. The CLI has a plain-text fallback path but the demo aesthetic depends on rich.

### Free-form English collapses to `meta_logic`
This is the **modality mismatch** — the K=9 baseline was trained on a narrow surface distribution. The rewrite shim mitigates ~85-90% of canonical colloquialisms (e.g., *"can't stand"* → ^3 Negative) but won't catch every phrasing. Use `/menu` for the strongest demo. The fix is **Lever 3** (continued fine-tune on Claude-rewritten paired data) — see the conversational-broadening proposal for the plan.

### `cas` is not recognized as a command
`cas.bat` lives at `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas.bat`. From any directory inside the repo it should resolve. From outside the repo, either `cd` in or fully-qualify the path. (It's intentionally not on global `PATH` to avoid name collisions with system `cas` binaries.)

### `cas notation` — `|` and `^` get eaten by cmd.exe
Cmd.exe parses `|` as a pipe and `^` as an escape. Use PowerShell or escape them: `cas notation "^^3^^E_{F2}^|A"`. The dispatcher itself is fine — it's a shell-quoting issue, not a CLI bug.

### Anything inside `cas-native/inference/` looks broken
The `cas_native` package is a runtime shim (cas-native with hyphen → cas_native with underscore). The shim is installed at the top of every entry-point file in this directory. If you're running a script directly, the shim works. If you're running via `python -m cas_native.inference.X`, the module-form import fails because the shim runs after `-m` resolves the module path. **Always invoke with the full path or via `cas.bat`**, not `python -m`.

---

## 7. Files in play (for editors)

```
cas-native/inference/
├── chat.py            # Interactive REPL (rich-styled)
├── cas_cli.py         # Top-level dispatcher
├── predict_cas.py     # Inference wrapper — text → prediction dict
├── cas_renderer.py    # CAS expression → English (authoritative defs verbatim)
├── rewrite_shim.py    # Free-form English → training-surface
├── demo_prompts.py    # 21 curated starter prompts (frozen data)
├── QUICKSTART.md      # This file
└── (existing files)   # generate_samples.py, semantic_reranker.py, etc.

cas.bat                # Repo-root Windows wrapper
```

---

## 8. Where to go next

- **Add a starter prompt:** edit `demo_prompts.py`. Selection criteria: `all_heads_exact == True` on the K=9 baseline, structurally interesting, < 200 chars when possible. Re-test with `cas demo` after editing.
- **Tighten the rewrite shim:** edit `rewrite_shim.py`. Add new colloquialism patterns to the keyword dicts at the top. Re-test with `python rewrite_shim.py`.
- **Extend the renderer:** edit `cas_renderer.py`. Authoritative definitions live in `noetic-compass-scaffold/noetic-compass/CLAUDE.md` — preserve them verbatim. Apply the anti-drift rules (^3 visceral, ^8 associative).
- **Improve the model:** read `docs/working/cas_native_conversational_broadening_proposal_2026_05_04.md`. Recommendation is Lever 3 (continued fine-tune on Claude-rewritten paired data, 5-7 days, ~$25).
- **Improve the eval:** see the held-out 1K eval at `cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl`.

---

## 9. The honest framing for outsiders

The CLI demos a real CAS-Native model that gets 93.2% on a structured prediction task on its training distribution. It does not yet handle arbitrary free-form English — that's the next lever. What's working today is exactly what the project promised at this phase: **CAS structure recovery from prompts the model has seen the surface distribution of**. The conversational layer is v0; the language broadening is v1.
