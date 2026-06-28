# Noetic Compass — CAS CLI

A command-line surface around the CAS-Native v0 model. Type natural-language
input; get back a CAS v7.7 structured-prediction expression and a one-sentence
English reading.

Tags: `AI Psychology Assessment` | `CAS v7.7` | `Structured Prediction` | `CLI Demo`

This README is the quickstart for the **CLI surface** that shipped in PR #32.
It is not a paper, not full project documentation, and not marketing copy. If
you want depth, jump to the
[internal runbook](noetic-compass-scaffold/noetic-compass/cas-native/inference/QUICKSTART.md).

---

## 1. Quickstart (3 minutes)

```bash
git clone https://github.com/LittleHenderson/noetic-compass.git
cd noetic-compass
pip install torch rich
cas chat
```

The `cas` entry point is the file `cas.bat` at the repo root. From any
directory inside the cloned repo it resolves on Windows. From outside the
repo, either `cd` in or invoke `cas.bat` by full path. The wrapper is
intentionally not on global `PATH` to avoid name collisions with system
binaries called `cas`.

### macOS / Linux

There is no shipping shell wrapper yet. Drop this two-line script as `cas`
on your `PATH` (or alongside the repo root) and `chmod +x` it:

```bash
#!/usr/bin/env bash
exec python "$(dirname "$0")/noetic-compass-scaffold/noetic-compass/cas-native/inference/cas_cli.py" "$@"
```

(Adjust the path if you saved the script outside the repo root.)

### First smoke check

Before opening the REPL, verify the dispatcher loads:

```bash
python noetic-compass-scaffold/noetic-compass/cas-native/inference/cas_cli.py --test
```

Expected: prints version block, the 21-prompt demo table, and one prediction.
Exits `rc=0`. If it fails, fix the environment before continuing — none of
the user-facing commands will work.

---

## 2. The five subcommands

| Command | Purpose |
|---|---|
| `cas chat` | Interactive REPL with rich-styled output. The headline demo. |
| `cas demo` | Print the 21 curated starter prompts grouped by bucket. |
| `cas predict TEXT` | One-shot prediction. For scripting / piping. |
| `cas notation EXPR` | Pass-through to the existing CAS compiler at `api/notation/cli.py`. |
| `cas version` | Project version, checkpoint name, training-time metric, build date. |
| `cas help` | Banner with all subcommands. Bare `cas` does the same. |

Inside `cas chat`:

| Slash command | What it does |
|---|---|
| (any free-form text) | Detects CAS signal via the rewrite shim; if signal is found, rewrites to training-surface format then predicts; otherwise predicts directly with an out-of-distribution warning. |
| `/menu` or `/m` | Numbered list of all 21 curated demo prompts grouped by bucket — pick by number. |
| `/sample` or `/s` | Random demo prompt + prediction. |
| `/raw` | Toggle showing the raw 12-key prediction dict alongside English. |
| `/help` | Re-show the banner. |
| `/exit`, `/quit`, `/q` | Leave. |

---

## 3. What you'll see

### `cas help` banner

```
NOETIC COMPASS — CAS CLI
v0.1.0-dev | K=9 baseline | 93.2% canonical exact

Commands:
  cas chat              Launch the interactive REPL (CAS-Native predictions)
  cas notation EXPR     Compile a CAS expression to JSON / lex / parse / check
  cas predict TEXT      One-shot prediction on a text input
  cas demo              Show 21 curated starter prompts
  cas version           Show version and metric info
  cas help              Show this banner
```

### A `/menu`-driven turn (model gets the structured CAS right)

The user types a number from `/menu`. The CLI shows the training-surface
prompt verbatim, predicts, and renders.

```
INPUT            As a notation exercise, map this structure into CAS:
                 families: state expression; states: Noetic ^2; domain C
                 (cognitive); drive F2; register |A (analytical).
CAS PREDICTION   ^2^C_{F2}|A
ENGLISH          Reading this as `^2^C_{F2}|A` — an attraction toward an
                 Idea (^2 Positive on the Cognitive domain, expressed in
                 Analytical register), driven by F2 Wisdom.
```

### A free-form English turn (rewrite shim active)

The user types a colloquialism. The shim detects CAS axes, rewrites to the
training surface, then predicts.

```
INPUT            I can't stand it when people interrupt me
DETECTED SIGNAL  Noetic ^3 (1.00), domain E (0.83), drive F4 (0.50),
                 register |f (0.92)
REWRITTEN        As a notation exercise, map this structure into CAS:
                 families: state expression; states: Noetic ^3; domain E
                 (evaluative); drive F4; register |f (felt).
CAS PREDICTION   ^3^E_{F4}|f
ENGLISH          Reading this as `^3^E_{F4}|f` — a felt aversion (^3 Negative
                 on the Evaluative domain, expressed in Affective register),
                 driven by F4 Connection. Did I get that right?
```

### A free-form English turn (modality mismatch)

When the rewrite shim cannot detect enough axes, the prediction is unreliable.
The CLI surfaces this rather than hiding it.

```
INPUT            Tell me a story about a fox
NOTE             Out-of-distribution — the rewrite shim found no clear CAS
                 signal. The model may collapse to its training prior
                 (`meta_logic`).
CAS PREDICTION   meta_logic
ENGLISH          (no clean reading; try /menu for a curated example).
```

---

## 4. The 21 starter prompts

All 21 prompts pass `all_heads_exact == True` on the K=9 baseline. They are
hand-curated to cover six bucket types and structural features.

### `v74_baseline` — bare 40-state CAS (no register), 4 prompts

| # | Feature | Ground truth |
|---|---|---|
| 1 | simple state expression | `^1^E_{F1}` |
| 2 | composition of two states | `^8^C_{F6} * ^5^C_{F6}` |
| 3 | directed transition between states | `^5^C_{F1} -> ^6^E_{F1}` |
| 4 | evaluative-to-operational transition | `^4^E_{F3} -> ^8^O_{F3}` |

### `v75_register` — single state or co-presence with registers, 4 prompts

| # | Feature | Ground truth |
|---|---|---|
| 1 | single state with `|E` embodied register | `^0^O_{F3}|E` |
| 2 | single state with `|A` analytical register | `^2^C_{F2}|A` |
| 3 | domain-omitted state with `|A` register | `^9^P|A` |
| 4 | register co-presence with `+` | `^4^O_{F6}|A + ^4^E_{F7}|f` |

### `v77_rule_four` — same-state co-presence across registers, 3 prompts

| # | Feature | Ground truth |
|---|---|---|
| 1 | 2-register Rule-4 co-presence | `^1^E_{F7}|E + ^1^E_{F5}|f` |
| 2 | 3-register Rule-4 co-presence (A,T,f) | `^7^C_{F5}|A + ^7^C_{F3}|T + ^7^C_{F1}|f` |
| 3 | full 4-register Rule-4 (all registers, same state) | `^5^O_{F4}|A + ^5^O_{F4}|f + ^5^O_{F4}|E + ^5^O_{F4}|T` |

### `v77_omega` — cross-register integration into named emergent, 3 prompts

| # | Feature | Ground truth |
|---|---|---|
| 1 | cross-register integration into omega bind | `(^1_{F3}|E × ^1_{F5}|A) = ^1|Ω_presence` |
| 2 | 3-register omega with domain (witness) | `(^1^E_{F3}|T × ^1^E_{F7}|A × ^1^E_{F6}|E) = ^1^E|Ω_witness` |
| 3 | 3-register omega bind (cadence) | `(^7^O_{F2}|E × ^7^O_{F5}|A × ^7^O_{F6}|f) = ^7^O|Ω_cadence` |

### `v76_production` — weighted recipe with arrow, 3 prompts

| # | Feature | Ground truth |
|---|---|---|
| 1 | production recipe with weighted ingredients | `Θ(Ω_focused_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A + 1.04*^1^P_{F1}|A → Ω_focused_refusal` |
| 2 | recipe with leakage (Lambda) side-product | `Θ(Ω_grounded_creative_insight) = 1.52*^6^C_{F2}|A + 0.83*^8^C_{F3}|A + 0.98*^4^E_{F4}|f → Ω_grounded_creative_insight + 0.1*Λ·Ω_aversion_overflow` |
| 3 | cross-domain recipe with favoritism leakage | `Θ(Ω_mentored_skill_transfer) = 1.26*^5^O_{F5}|E + 1.87*^7^P_{F7}|T + 1.06*^5^C_{F5}|A → Ω_mentored_skill_transfer + 0.1*Λ·Ω_favoritism` |

### `meta_logic` — typed clusters, relations, set ops, products, 4 prompts

| # | Feature | Ground truth |
|---|---|---|
| 1 | typed Noetic cluster (set of Noetics) | `NoeticCluster{^4, ^1, ^3, ^2}` |
| 2 | relation cluster across P-C-E-O domain descent | `RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E, ^5^E -> ^5^O}` |
| 3 | state cluster set-difference | `StateCluster{^8^C, ^1^C, ^0^P} ∖ StateCluster{^0^P, ^8^C}` |
| 4 | Cartesian product of carriers | `Product(Noetics, Registers)` |

Total: 21 curated prompts across 6 buckets. See
`noetic-compass-scaffold/noetic-compass/cas-native/inference/demo_prompts.py`
for the source-of-truth.

---

## 5. Honest framing

A few things to be straight about before showing this to anyone:

- The active checkpoint is `K=9 baseline`, scoring **93.2% canonical-exact**
  on a rigorously overlap-filtered held-out 1K eval. That number is
  **on training-distribution prompts only** — i.e. the formal
  "families: state expression; ..." surface that the model was trained on.
- On free-form colloquial English, the model collapses to its
  most-populated training prior (`meta_logic`). This is the documented
  modality mismatch, not a bug in the CLI.
- The rewrite shim mitigates an estimated **~85-90%** of canonical
  colloquialisms by mapping them to training-surface format before
  prediction. It will not catch every phrasing.
- The fix — Lever 3, continued fine-tune on Claude-rewritten paired data —
  is in progress. See
  [`docs/working/cas_native_conversational_broadening_proposal_2026_05_04.md`](docs/working/cas_native_conversational_broadening_proposal_2026_05_04.md).

When demoing the CLI, lead with `/menu` or `/sample` (the model's
strongest surface) before inviting free-form English. State the limitation
out loud once before the user types something free-form. Honesty up front
beats apology after.

---

## 6. Architecture in five sentences

The CLI is a thin dispatcher; all real work lives in
`noetic-compass-scaffold/noetic-compass/cas-native/inference/`.

A turn flows as: natural-language input → (rewrite shim, if free-form
colloquial) → tokenize → K=9 structured-prediction model (12 prediction
heads: turn type, expression family, transition kind, Noetic, Domain,
Drive, register mode, registers, authority, has-omega, has-meta-logic,
meta-relations) → emit a CAS expression string and an English reading via
the renderer. The renderer uses the authoritative Noetic definitions
(Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm,
Above/Cause, Below/Effect) verbatim from
[`noetic-compass-scaffold/noetic-compass/CLAUDE.md`](noetic-compass-scaffold/noetic-compass/CLAUDE.md).
For the full CAS framework — operators, domains, drives, registers,
production semantics, register multiplicity — see that file.

---

## 7. Where to go next

| For... | Go to |
|---|---|
| Deeper runbook (smoke checks, troubleshooting, file map) | [`noetic-compass-scaffold/noetic-compass/cas-native/inference/QUICKSTART.md`](noetic-compass-scaffold/noetic-compass/cas-native/inference/QUICKSTART.md) |
| Full CAS v7.7 framework reference | [`noetic-compass-scaffold/noetic-compass/CLAUDE.md`](noetic-compass-scaffold/noetic-compass/CLAUDE.md) |
| Authoritative Noetic definitions, anti-drift rules, colloquialism map | [`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`](docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md) |
| CLI source — dispatcher, REPL, predictor, renderer, rewrite shim | [`noetic-compass-scaffold/noetic-compass/cas-native/inference/`](noetic-compass-scaffold/noetic-compass/cas-native/inference/) |
| The plan for free-form English (Lever 3, continued fine-tune) | [`docs/working/cas_native_conversational_broadening_proposal_2026_05_04.md`](docs/working/cas_native_conversational_broadening_proposal_2026_05_04.md) |
| Edit a starter prompt | `cas-native/inference/demo_prompts.py` (selection criterion: `all_heads_exact == True` on the K=9 baseline) |
| Add a colloquialism pattern | `cas-native/inference/rewrite_shim.py` (keyword dicts at the top) |

---

## 8. Status and roadmap

### Working today (2026-05-04)

- The five `cas` subcommands listed in section 2.
- `cas chat` interactive REPL with rich-styled output.
- 21 hand-curated starter prompts (every one canonical-exact at training time).
- Rule-based rewrite shim covering the canonical colloquialism map.
- Plain-text fallback when `rich` is not installed.
- Smoke test (`cas_cli.py --test`).

### Coming

- **v1, free-form English (~2026-05-15):** Lever 3 — continued fine-tune
  on Claude-rewritten paired data. Target: free-form English drops the
  `meta_logic` collapse.
- **v2, dialectic (2026 H2):** three-instance dialectic mode. Year 2 work.

These dates are honest commitments under the current plan; they slip if
training data preparation or compute slips.

---

## 9. Citation and contact

- **Project owner:** Little Henderson (a.k.a. Wakil, a.k.a. Prof. Hermes M. Thoth)
- **Repo:** https://github.com/LittleHenderson/noetic-compass
- **Provisional patent:** USPTO #64/037,173

The 10 Noetic names and definitions used throughout the project are
authoritative and verbatim from the Tootra Math Handbook. They are not
subject to alternative naming. See `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`
Clarification 1 for the canonical text.

---

*Last updated: 2026-05-04. CLI surface from PR #32. Checkpoint:
`structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045`
(commit 3232f05).*
