# MASTER HANDOFF — noetic-compass / HELM Cognitive Machine Stack
**Target Agent:** Claude / Any Incoming Autonomous Agent  
**Date:** 2026-10-18 (Updated 14:25 PDT)  
**Governing Rule:** Open and inspect every referenced artifact before asserting anything. Never guess.

---

## 0. EXECUTIVE SUMMARY & CURRENT WORKING STATE

Everything Claude needs to immediately take over, execute, audit, and extend this codebase without missing any context, lost files, or broken conventions.

### Where the Stack Sits Right Now:
- **Option 1 (Conversational HELM + Unified Cube Store)** is **DELIVERED & VERIFIED ON TRUNK** (PR #343, commit `05210ae3`).
- **Option 3 (RB-OH1 Substitution Recipe Head)** is **BUILT & VERIFIED** in `C:\Users\wakil\Documents\Codex\2026-10-15\rb_oh1\` (16/16 tests pass).
- **L4 Open-English Baseline & Anti-Circular Guard** is **MEASURED & SEALED** on trunk (commit `ec780a34`). The 439 headline SDG English sentences were tabulated; 197 unparseables partitioned into 98 held-out and 99 dev rows with mathematically proven zero overlap and sealed SHA-256 hashes.
- **End-to-End Pipeline Harness & Ordering Fix** is **WIRED & VERIFIED LIVE** on trunk (commit `7eb3511a` and `a7dcc6b6`). The ordering defect where `G-ABSENT` clamped reads is resolved: store reads/declarations bypass reagent clamps, while recipe execution is strictly gated by the Phase 3 Meta Valve Controller (`tks_meta_valve_controller.py`). All 6 live probes pass on the public signature; 11/11 tests green.
- **Trunk Integrity**: 100% green. Branch `claude/project-thread-pmbzd6` contains all 9 canonical packages (308 tests), the conversational HELM, the end-to-end harness, and sealed baseline datasets. 0 test failures.
- **Immediate Next Task**: **Option 2 (AWS Cloud Compute)** — Training the Level L4 CAS-Native Open-English Proposer on AWS GPU under the Dual Scorecard Mandate.

---

## 1. ESSENTIAL ADDRESSES, REPOSITORY & ENVIRONMENT

### 1.1 Repositories and Branches
| Resource | Address / Path | Notes |
|---|---|---|
| **Git Remote** | `https://github.com/LittleHenderson/noetic-compass.git` | Primary remote `origin` |
| **Canonical Branch** | `claude/project-thread-pmbzd6` | **NEVER COMMIT DIRECTLY TO `master`**. Always branch or commit to `claude/project-thread-pmbzd6` |
| **Active Worktree** | `D:\tksCAS-worktrees\repair-performer-20261017` | Local git worktree currently tracking `origin/claude/project-thread-pmbzd6` (branch `verify-consolidated`) |
| **Secondary Workspace** | `C:\Users\wakil\OneDrive\Desktop\tksCAS` | Local workspace directory |
| **External Codex Archive** | `C:\Users\wakil\Documents\Codex\` | Read-only historical & dependency archives (see §6) |
| **Council Records** | `C:\Users\wakil\Documents\Codex\2026-10-16\noetic_loop\` | Outside repo; mirrors handoffs and council decisions |

### 1.2 Execution Environment & Runtime Constraints
- **Python Executable**: `C:\Python314\python.exe`
- **Mandatory Python Flags**: Always run with `-X utf8 -B` (ensures UTF-8 encoding across Windows LF/CRLF and prevents `__pycache__` clutter).
- **Git Commit Identity**:
  ```bash
  git commit -c user.name="Little Henderson" -c user.email="little.henderson@noetic-compass.dev"
  ```
- **Local Memory Constraint (CRITICAL)**:
  The owner reported a snapshot of only **354 MB free out of 16 GB locally**.
  - **Rule**: Keep laptop work to lightweight editing, inspection, orchestration, and local fast tests (< 30s runtime, < 100 MB RAM, $0 spend).
  - **Rule**: All heavy training, neural fits, and sustained GPU runs must execute on **AWS GPU**. Never fall back to local heavy neural training.

---

## 2. OWNER ORDERS, STANDING INVARIANTS & CLAIM CEILINGS

### 2.1 The Core Purpose
> *"Remember we are trying to replace and do better than the traditional transformer that is currently the brain of HELM."*
A 97-trained-parameter transformer is replaced by 68 learned values (32 requirements $a$, 32 ceilings $h$, 4 bindings $\beta$).
> *"A brain that computes exactly, knows what it does not know, and can prove both."*

### 2.2 First Principles & Architectural Invariants
1. **Language is a Skin, Not the Brain**:
   $$\text{Facts} \in \{\text{CubeStore Receipts}, \text{Stoichiometric CES Proofs}, \text{User Declarations}\}$$
   No fact originates from the language layer. Free English is parsed into structured CASContent; structured CASContent is rendered deterministically back to English; ungrounded or non-derivable claims trigger typed `CLARIFY` or `GATE_REFUSE` with **zero cubes written**.
2. **Proposal vs Authority**:
   > *"Randomness may only propose; the verifier, the receipts and the RPM Gate always decide."*
   Neural components (like Level L4 Proposer) have zero authority to assert facts. They only propose candidates, which must satisfy $\text{parse}(\text{render}(\hat{C})) \equiv \hat{C}$ and receive user confirmation before entering memory.
3. **Phase 3 Meta Valve Controller Invariant (CRITICAL MANDATORY MEMORY)**:
   > **`MUST REMEMBER: Add, train, and test the VALVE SYSTEM (tks_meta_valve_controller) in Phase 3. This is CRITICAL.`**
   The valve sits at the execution boundary. Store reads (`LIST_PARTS`) and declarations consume nothing and bypass reagent clamps. Physical batch execution (`run`/`bake`) is strictly gated by `tks_meta_valve_controller`: missing essential reagents (`Flour`, `Water`) trigger an immediate `G-ABSENT` clamp.
4. **Verbatim Claim Ceiling**:
   Whenever writing documentation, READMEs, or reports, maintain this exact claim ceiling:
   > `MECHANISM ONLY. KNOWLEDGE IS STORED AS CUBES; ANSWERS COME FROM THREE OPERATIONS OVER THAT STORE. AN UNKNOWN FACE IS REPORTED AS UNKNOWN AND IS NEVER FILLED. NO UNDERSTANDING OF THE REQUEST IS CLAIMED.`

---

## 3. CANONICAL CODEBASE MAP & FULL LOCAL PATHS

### 3.1 The Nine Canonical Packages in `docs/working/noetic_council/`
All paths relative to `D:\tksCAS-worktrees\repair-performer-20261017\docs\working\noetic_council\`:

| Package Directory | Test Suite | Test Count | Description / Role |
|---|---|---|---|
| `cube_store/` | `test_all.py` | **19** | **Unified Cube Store**: 6-faced CubeNodes, 16-char SHA-256 receipts, orthogonal `assertion` / `valence` split, `LIST_PARTS` read queries, cold honest bedside manner. |
| `prereq_planner/` | `test_all.py` | **11** | **Topological Prerequisite Planner**: Kahn acyclicity verification, HORIZON=12 bounds, cycle refusal, mid-plan repair interlock. |
| `continuity_build_v4/` | `test_all.py` | **50** | **Continuity & S0 Anchor**: S0 anchored to the real Atlas model, ASOM readout gauge, seam detection. |
| `dwp_engine_v2/` | `test_all.py` | **33** | **D/W/P Engine**: Definition 27.2 functors, HORIZON=12, desire bound=12, retraction & lacunarity. |
| `the_loop_v3/` | `test_all.py` | **35** | **The Loop & Real RPM Gate**: 5 stages, strictly checked `GateRequest` (no label field), `RpmCause`. |
| `return_address/` | `test_all.py` | **27** | **Atlas Return Stack**: Exact Atlas addresses, dirty-child invalidation, snapshot digest certification. |
| `faculties_v2/` | `test_all.py` | **49** | **Faculties & Unity Eye**: Wondering, pondering, imagination, self-notice, `restart_fallback`, real `rb_c4` fitter. |
| `language_v3/` | `test_lm_t1*.py` | **68** | **Language Translator**: CCE v0.1/v0.1b/v0.1c, deterministic parser and renderer, alias-wide reader, 15 real English examples. |
| `repair_performer/` | `test_all.py` | **16** | **Repair Performer Actor**: Opens child repair goals when parent gate returns `REPAIR`, glues results back. |

**Total Canonical Package Tests**: **308 tests — 0 failures**.

### 3.2 Conversational & Pipeline Integration Modules
Located in root of repo / worktree:
- [`helm_end_to_end_loop.py`](file:///D:/tksCAS-worktrees/repair-performer-20261017/helm_end_to_end_loop.py): Complete pipeline harness connecting User Dialogue $\rightarrow$ CCE Round-Trip Gate $\rightarrow$ Phase 3 Meta Valve Controller $\rightarrow$ Station S0 22x40 Recipe Brain $\rightarrow$ Unified Cube Store. Handles both Path A (store reads/writes) and Path B (physical recipe execution).
- [`test_helm_end_to_end_loop.py`](file:///D:/tksCAS-worktrees/repair-performer-20261017/test_helm_end_to_end_loop.py): 11 tests verifying end-to-end turns, G-ABSENT clamping on execution, read query pass-through, and top-level public convenience keys (`11/11 PASS in 0.11s`).
- [`helm_chat.py`](file:///D:/tksCAS-worktrees/repair-performer-20261017/helm_chat.py): Conversational layer with dialogue act disambiguation, honest affective responses, and personal fact memory.
- [`helm_memory.py`](file:///D:/tksCAS-worktrees/repair-performer-20261017/helm_memory.py): Working memory context, user narrative facts, preferences, and multi-turn inventory store.
- [`test_helm_chat_nuance.py`](file:///D:/tksCAS-worktrees/repair-performer-20261017/test_helm_chat_nuance.py): 10 tests verifying 5 sequences and 5 probes (`10/10 PASS`).
- [`tks_meta_valve_controller.py`](file:///D:/tksCAS-worktrees/repair-performer-20261017/tks_meta_valve_controller.py): Phase 3 Meta Valve Controller evaluating stoichiometric balance, 80/20 invariant/nuance ratio, and pressure clamping.
- [`helm_brain_22x40.py`](file:///D:/tksCAS-worktrees/repair-performer-20261017/helm_brain_22x40.py): Station S0 22x40 Recipe Brain computing 40-digit software Decimal CES law and limiting reagents.
- [`helm_creativity_dial.py`](file:///D:/tksCAS-worktrees/repair-performer-20261017/helm_creativity_dial.py): Bounded creativity dial controlling exploratory aperture.

### 3.3 Option 3 Substitution Recipe Head (RB-OH1)
Located at: `C:\Users\wakil\Documents\Codex\2026-10-15\rb_oh1\`
- `sub_oh1.py`: 40-digit software `Decimal` CES law $Y_\rho(\Omega \mid S) = (\sum_i c_i x_i^\rho)^{1/\rho}$ over the 11-rung exponent ladder $\{1, 1/2, 1/3, 1/4, 0, -1/4, -1/3, -1/2, -1, -2, -4\}$.
- `routing_oh1.py`: Stage-boundary router implementing routing keys $R_0..R_6$ and RPM Gate rules (`G-ABSENT`, `G-LIMIT`).
- `test_rboh1.py`: Acceptance test suite (**16/16 tests pass in 2.95s**).
- `FROZEN.json` & `SOURCE_MANIFEST.json`: Cryptographically frozen specifications.

---

## 4. BASELINE DATASETS, HASHES & ANTI-CIRCULAR GUARD

### 4.1 Tabulation of the 439 SDG Real English Sentences
- Script: [`tabulate_439_sdg_baseline.py`](file:///D:/tksCAS-worktrees/repair-performer-20261017/tabulate_439_sdg_baseline.py)
- Record: [`docs/working/SDG_439_HEADLINE_TABULATION_20261018.json`](file:///D:/tksCAS-worktrees/repair-performer-20261018/docs/working/SDG_439_HEADLINE_TABULATION_20261018.json)
- Results:
  - Baseline Bridge v2: 118 MATCH, 321 UNPARSEABLE, 42 MISMATCH (on 481 accepted rows).
  - Alias-Wide Grammar: 265 MATCH, 199 UNPARSEABLE, 17 MISMATCH (on 481 accepted rows).
  - Net Gain: **+147 matches** (or **+115** on the 439 headline subset), **−59.5% reduction in misreads** (42 $\rightarrow$ 17).
  - Unparseable Failure Taxonomy: 148 `NO_STATE` (75.1%), 56 `NO_DOMAIN` (28.4%), 27 `AMB_STATE` (13.7%), 16 `PARSE_FRAME_ERR` (8.1%).

### 4.2 The Sealed Evaluation Partitions
Located in: `cas-synthetic/data/l4_split/` (relative to repo/worktree):
1. **`real_heldout_unparseables_98.jsonl`**:
   - 98 sentences | SHA-256: `e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe`
   - **STRICTLY HELD OUT**. Zero training exposure permitted. Never include in training prompts, fine-tuning, or few-shot examples.
2. **`real_dev_unparseables_99.jsonl`**:
   - 99 sentences | SHA-256: `17cd198321d242bd74ff789a4b7f8032d499a7ff8534e5b07545b6221930fde0`
   - Development & error taxonomy analysis only.
3. **Disjointness Proof**:
   - Mathematically verified 0 overlapping sentences across the two files across `english`, `seed_id`, and `(file, line)`.

### 4.3 The Dual Scorecard Mandate for Option 2 (AWS Run)
To prevent the circular-data trap where a model learns synthetic generator quirks instead of open language:
$$\text{Scorecard} = \left[ \text{Acc}_{\text{synthetic\_test}}, \quad \text{Acc}_{\text{real\_heldout\_98}} \right]$$
Both scores must be published side-by-side in any AWS training report.

---

## 5. EXACT COMMANDS TO RUN AND VERIFY EVERYTHING

### 5.1 Canonical 7 Packages in `noetic_council`
```powershell
cd "D:\tksCAS-worktrees\repair-performer-20261017"
git fetch origin claude/project-thread-pmbzd6
git status

# 1. Test 6 core packages:
foreach ($p in @("continuity_build_v4","dwp_engine_v2","the_loop_v3","return_address",
                 "faculties_v2","repair_performer")) {
  Push-Location "docs\working\noetic_council\$p"
  & "C:\Python314\python.exe" -X utf8 -B test_all.py 2>&1 | Select-String "TOTAL|RESULT"
  Pop-Location
}

# 2. Test Unified Cube Store (19 tests):
& "C:\Python314\python.exe" -X utf8 -B docs\working\noetic_council\cube_store\test_all.py

# 3. Test Prerequisite Planner (11 tests):
& "C:\Python314\python.exe" -X utf8 -B docs\working\noetic_council\prereq_planner\test_all.py
```

### 5.2 Language v3 Tests (Requires External Dependencies in PYTHONPATH)
```powershell
$env:PYTHONPATH = "C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011;" +
                  "C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1"
Push-Location "docs\working\noetic_council\language_v3"
& "C:\Python314\python.exe" -X utf8 -B test_lm_t1.py      # 26 tests
& "C:\Python314\python.exe" -X utf8 -B test_lm_t1b.py     # 11 tests
& "C:\Python314\python.exe" -X utf8 -B test_lm_t1c.py     #  5 tests
& "C:\Python314\python.exe" -X utf8 -B test_lm_t1v3.py    # 26 tests
& "C:\Python314\python.exe" -X utf8 -B how_it_talks.py    # 15 English examples
Pop-Location
```

### 5.3 Conversational HELM Nuance & End-to-End Pipeline Harness
```powershell
cd "D:\tksCAS-worktrees\repair-performer-20261017"
# 10 tests (Sequences A & B, DeepSeek 7-turn, Epistemic study, 5 Probes):
& "C:\Python314\python.exe" -X utf8 -B test_helm_chat_nuance.py

# 11 tests (End-to-end loop, ordering fix, public signature keys):
& "C:\Python314\python.exe" -X utf8 -B test_helm_end_to_end_loop.py
```

### 5.4 RB-OH1 Substitution Recipe Head (16 tests)
```powershell
$env:PYTHONPATH = "C:\Users\wakil\Documents\Codex\2026-10-14;" +
                  "C:\Users\wakil\Documents\Codex\2026-10-15;" +
                  "C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1;" +
                  "C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011"
cd "C:\Users\wakil\Documents\Codex\2026-10-15\rb_oh1"
& "C:\Python314\python.exe" -X utf8 -B -m unittest test_rboh1.py
```

---

## 6. EXTERNAL DEPENDENCIES & READ-ONLY REFERENCE PACKAGES

The following folders outside the repository are read-only dependencies and must **never be deleted or modified**:
- `C:\Users\wakil\Documents\Codex\2026-10-14\rb_c4\`: Real fitter (`fitg.py`, `taskb.py`). Used by `faculties_v2/real_fit.py` and `repair_performer`.
- `C:\Users\wakil\Documents\Codex\2026-10-14\lsr_t1` through `lsr_t7`: Family data and engines imported by `rb_c4` and `rb_oh1`.
- `C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011\sdg_bridge_v2\`: Used by `language_v3/aliaswide.py`.
- `C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1\`: Used by `language_v3/coverage.py`.
- `C:\Users\wakil\Documents\Codex\2026-10-15\lm_t6\`: Cascade 4 verification.

---

## 7. NEXT ACTION PLAN: OPTION 2 (AWS CLOUD COMPUTE FOR LEVEL L4 PROPOSER)

With Options 1 and 3 complete, Option 2 is next. The exact execution plan is specified in [`LEVEL_L4_OPEN_ENGLISH_PROPOSER_SPECIFICATION_20261018.md`](file:///D:/tksCAS-worktrees/repair-performer-20261017/docs/working/LEVEL_L4_OPEN_ENGLISH_PROPOSER_SPECIFICATION_20261018.md):

### Step 2A: Generate Synthetic Training Data (Local Stdlib, $0 spend)
1. Sample 20,000–50,000 valid `CASContent` combinations from the 21 mapped fundamentals (8 Noetic verb frames + 13 cross-cutting structures).
2. Render each record under ALIAS and CANON wording variations using `cce.render(C, w)`.
3. Target the 148 `NO_STATE` and 56 `NO_DOMAIN` structural gaps discovered in the baseline audit.
4. **Zero-Bleed Exclusion**: Mechanically filter the generator against the 98 sealed held-out sentences in `cas-synthetic/data/l4_split/real_heldout_unparseables_98.jsonl`.

### Step 2B: Build & Freeze AWS GPU Job Package (`helm_l4_aws_training/`)
1. Model: CAS-Native Sequence-to-Sequence / DAG Transformer ($\le 35\text{M}$ parameters, zero foreign weights).
2. Evaluator: Implement the Dual Scorecard $[\text{Acc}_{\text{synthetic\_test}}, \text{Acc}_{\text{real\_heldout\_98}}]$.
3. Gate: Interlock proposed outputs behind Phase 3 `tks_meta_valve_controller` ($\varepsilon \circ \eta = \text{id}$).
4. Spec: Define `JOB_SPEC.json` with strict limits: instance `g4dn.xlarge` / `g5.xlarge`, cost limit $<\$1.00$, timeout 900s.

### Step 2C: Launch & Train on AWS GPU
1. Trigger job using AWS CLI / runner script.
2. Stream training loss, validation metrics, and receipts to local log.
3. Download trained weights (`l4_proposer_weights.pt`) and evaluation summary.
4. Re-evaluate pipeline harness with trained proposer and record measured improvement on the 98 held-out rows.

---

## 8. POWERSHELL & SHELL TRAPS (DO NOT REPEAT THESE MISTAKES)

1. **PowerShell Quote & Semicolon Mangling**:
   - Running `gh pr create --body "..."` with semicolons or double quotes in the string will get mangled by PowerShell. **Always write the PR body to a temporary markdown file and pass `--body-file`**.
   - Heredocs piped directly into Python on Windows PowerShell get mangled. Write a temporary `.py` script and run it.
2. **Git CRLF vs LF Normalization**:
   - The repository uses LF endings. On Windows checkouts, run Python with `-X utf8 -B`. Do not convert file line endings to CRLF.
3. **Always Check Git Ancestry Before Pushing**:
   - Before pushing to `origin/claude/project-thread-pmbzd6`, run `git merge-base --is-ancestor origin/claude/project-thread-pmbzd6 HEAD` to verify no commits were overwritten.

---

## 9. MANDATORY RESPONSE FORMAT FOR WAKIL

The owner requires every update to conclude with these exact three headings in order:
```markdown
🎉WHAT IS CURRENTLY HAPPENING: (EITHER MENTION NOTHING OR WHATEVER IS HAPPENING LIKE A RUN, TESTING, BUILD etc.)

🎁FOR WAKIL TO DO: (MENTION WHATEVER IT IS YOU NEED ME TO DO OR NOTHING YET)

🚀NEXT: (MENTION WHAT'S NEXT IN THE PROJECT PROCESS)
```
Do not leave any of these blank.
