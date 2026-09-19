# HANDOFF — CNCM pointer machine: build it, review it, dry-run it, launch it on AWS

**Written 2026-09-19 by the outgoing agent. Branch `codex/cncm-vision-next`. Nothing is running on AWS. $0.00 spent since the
practice study. The pointer machine is DESIGNED and REVIEWED ONCE; not one line of it is built yet.**

You are picking up the CAS Native Cognitive Machine (CNCM) campaign. The owner has approved the next experiment: **"pointer
answers plus the checkpoint check"**. Your job: build it, get it reviewed twice, dry-run it for $0, record the owner's approval
as signed per-job records, then launch 3 AWS jobs and read the result with a deterministic gate program.

Read §0 and §1 first. §6 is the build plan. §9 is the launch procedure. §12 lists what the owner must do.

---

## 0. The whole situation in ten lines

1. The machine (frozen hash encoder → one trainable 16,384-weight `^6` block → frozen answer table) was trained for ten passes
   on AWS on 2026-09-18. It learned the questions it practised (13 → 85 of 189) and **nothing** about five worlds it never
   practised (2–3 → 2–5 of 45). Label: `NO_TRANSFER_TO_NEW_WORLDS`. Commit `8cdbad81`.
2. On 2026-09-19 we measured WHY, for $0 (§3): each question's input is one 64-number blend of all 64 worlds (almost identical
   for every question), plus a scrambled code of the answer slot's NAME. A never-seen name gets a random-looking code. So a
   world the machine never practised is unreadable **by construction**. The old 96.3758% "the answer is in the input" figure
   came only from recalling exact names already seen.
3. The owner then ordered option 1: a **pointer machine** — the machine reads ONE world as a small graph and answers by
   POINTING at that world's own parts ("this node here"), so the skill is the same for every world.
4. A design draft exists (`records/typed_pointer_001/pre_design/DESIGN_DRAFT_v0.1.md`). One adversarial review (pipeline /
   run-killers lens) is done and found 10 run-killers, 3 false-positive risks, 10 design gaps (§5). Two more review lenses
   (leaks/shortcuts; can-it-learn) were started but their results were NOT captured — **re-run them** (§5.3).
5. Your next concrete step: write design v0.2 folding in §5, freeze the protocol doc, then build per §6.

---

## 1. Where everything is — full paths

**Git worktree root (commit and push from here):**
```
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next
```
**CNCM project folder (call it CNCM below; all relative paths are from here):**
```
<worktree root>\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE
```
Branch `codex/cncm-vision-next`, pushed to origin. HEAD at hand-off: see `git log -1` (this handoff's commit).

| What | Path (under CNCM unless absolute) |
|---|---|
| Practice study (the run that just finished) | `records/typed_practice_001/` — `PRACTICE_STUDY_RESULT.md`, `evaluate_gates.py`, `prepare_study.py`, `execute_study.py`, `preflight_dry_run.py`, `holdout_audit.py`, receipts `receipt_2026091{7,8,9}/` |
| Practice protocol (frozen) | `docs/CNCM_TYPED_PRACTICE_STUDY_v0.1.md` |
| Practice code (copy its patterns) | `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/practice_contract.py`, `practice_learner.py`; `cncm/typed_practice_worker.py`; `research/CAS_META_2_COMPOSITION/aws/typed_practice_launch.py`; `tests/test_typed_practice_study.py` (24 tests, ~128 s) |
| Old learner (do NOT edit) | `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/learner.py` |
| Slot plan / answer assembly (reuse unchanged) | `.../typed_teaching/slots.py`, `answers.py`; checker `checker.py`; loss plan `loss_plan.py` |
| Frozen encoder (keep as `.encoder`) | `.../typed_teaching/encoder.py`, `binding.py`, `tokenization.py`, `input_frames.py` |
| ^6 block source (frozen, do NOT edit) | `research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py` (`_DecomposeTransform`) |
| Machine status record | `records/MACHINE_STATE_001/STATUS.md` (§6 has the owner ruling and the practice result) |
| **This hand-off's pre-design material** | `records/typed_pointer_001/pre_design/` — `DESIGN_DRAFT_v0.1.md`, `DESIGN_REVIEW_PIPELINE_LENS.md`, `INPUT_DEFECT_MEASUREMENT.md`, `CASFORMER_V0_2_MAP.md`, `PDF_ASSESSMENT.md`, `measurements/input_defect/*`, `measurements/pipeline_review/r1..r5*.py` |
| Living master record (update in the SAME commit as any result) | `<worktree root>\docs\CAS_HARNESS_SPEC_SHEET.md` |
| Changelog (update every unit of work) | `<worktree root>\CHANGELOG.md` |
| Budget ledger (read it; do not hand-edit) | `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\research\CAS_META_2_COMPOSITION\records\budget\campaign_ledger.json` (the launcher's `CANONICAL_LEDGER`) |
| Receipt backups | `D:\tksCAS-archive\cncm_typed_practice_001_20260918` (1,795 files, verified) |
| Owner's PDF | `C:\Users\wakil\Downloads\CAS-RPA × TypeSafe AI × CAS PCBA_ JEV Integration Deep Dive.pdf` — assessed in `pre_design/PDF_ASSESSMENT.md` |

Python import setup used everywhere:
```python
import sys; from pathlib import Path
CNCM = Path(r"...\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
from cas_meta2.typed_teaching import practice_contract as c
frozen, tokenizer, development = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)            # record-id lists: 127 / 358 / 79
packets = dict(c.public_packets(frozen))             # record_id -> {"source": ..., "record": ...}
```

---

## 2. Owner orders and standing rules (verbatim where it matters)

**Approval for THIS study, 2026-09-19, verbatim from chat:**
> "do option 1, pointer answers plus the checkpoint check BUT EXAMINE THIS TO SEE IF AND HOW IT OR ANYTHING IN HERE CAN HELP:      "C:\Users\wakil\Downloads\CAS-RPA × TypeSafe AI × CAS PCBA_ JEV Integration Deep Dive.pdf""

**Option 1 as it was offered to the owner (verbatim), which is what was approved:**
> "Pointer answers + checkpoint check (my recommendation). Today the machine answers by choosing from a fixed list of 90 labels,
> like "node 3" or "world 46". A pointer version answers by pointing at a part of the question's own input: "this node here."
> That pointing skill is the same for any world, including new ones. It's the standard fix for "works on things it has seen,
> fails on new ones." Whether it actually works here is what the run would test. I'd build and dry-run it for $0 first. The paid
> run would be about the same size as this one (about $13, with $45 reserved). The checkpoint check from option 3 runs on the
> same machine at no extra cost."

**Two corrections the owner must be told (do not bury them):**
- "At no extra cost" was wrong. The in-job checkpoint check costs about 9–15 minutes per job, about **$0.38–$0.63 per job**
  (pipeline review M2).
- "Pointer answers" alone cannot work: the INPUT must change too (one world as a graph, the question expressed by pointing at
  its nodes, not by a hashed name). This is inside the spirit of option 1 but it is a bigger change than "the answer format".

**Standing owner goal (earlier, verbatim excerpt):** "IT MUST BE LEARNING LEARNING AT THE NEURON LEVEL THE ARCHITECTURE SHOULD
BE SERVING THIS PURPOSE ... CONTINUE ON WITH AI AGENTS RESEARCH AND DEVELOPMENT UNTIL THE ULTIMATE VISION OF THIS PROJECT IS
FULLY FULFILLED MEANING WE HAVE A WORKING CASFORMER LLM/CNCM". Owner ruling 2026-09-18: rule-layer gains never count as machine
progress.

**Standing rules you must follow (CLAUDE.md + memory):**
- **Plain English in every reply to the owner**, every time; short sentences; exact numbers; claim states separated. Owner
  action items go LAST in a separate block. Mark results ✅🟩🟨🟧🟥⬜🔧🔒.
- **You are NOT the research governor.** Do not pick a replacement hypothesis after a failed gate; a failed hard gate is a
  FAILURE, never "PASS with caveats"; the claim status is what the frozen gate program prints; owner approval must be an
  executable signed record (one `owner.json` per job, as the practice study did).
- **GPU-first.** No neural work on local CPU. Local RTX 4070 = smoke/dev only. Every claim-bearing run on AWS GPU (not Bedrock).
- **Never write to `CAS_RRK_v0.1`.** Never delete a negative result. Numbers exact, never rounded.
- **Every result** → `CHANGELOG.md` + a dated spec-sheet change-log row with an artifact path, in the same commit. Run pytest
  before committing code. Commit and push after every unit of work. Back up successful run receipts to `D:\tksCAS-archive\`.
- **Register a mechanism-free baseline** in every bench; a win is uninterpretable until it beats the cheapest method without
  the mechanism. Relabelling/shuffle controls over a permutation-symmetric machine are VACUOUS.
- **Windows line endings:** Python `Path.write_text` writes CRLF on Windows. The repo is `eol=lf` and the AWS package compares
  working-copy bytes to committed blobs → a CRLF `.py` breaks the build (`INPUT_NOT_COMMITTED`). Use `write_bytes` or the
  Write/Edit tools. Some OLD files are committed WITH CRLF — never "renormalize" them; check each equals `git show HEAD:path`.
- **The evidence publisher is create-only.** Any file under `results/` that grows or is rewritten fails the final upload
  (`EVIDENCE_DIGEST_CONFLICT`). Write `<name>.partial` then rename; grow logs in a staging dir outside `results/`.
- **Read the console before re-spending** when an AWS job fails (free `get_console_output`), never guess-and-relaunch.

---

## 3. What was measured this session ($0, pure Python) — the input defect

Full report: `pre_design/INPUT_DEFECT_MEASUREMENT.md`; scripts/outputs `pre_design/measurements/input_defect/`.
Encoder rebuild verified byte-exact (projection sha256 `4481b1d2...fdd9`, readout sha256 `14da2c58...c667`).

- Every packet holds all 64 bank worlds. A 67-line block (FORMAT, ALIASES, POLICY, 64 WORLD lines) is byte-identical in all 564
  packets — including the 5 held worlds' own lines. Question-specific lines are 2 or 5 per packet (median 0.065789 of rows).
- Packet vectors: nearest trained packet to a held packet has cosine median 0.999065. Norm of the course-mean packet 0.983943.
- The only part of the slot input that changes from slot to slot is the query code: exactly 0.500000 of its squared norm, a
  SHA-256 hash of the slot name. Held slots whose name occurs in training: 0 of 617. Max cosine of a held query to any trained
  query: median 0.375 — the same as random vectors (control median 0.375).
- **Cross-world linear probe** (fit on trained-world slots, test on held-world slots) — the $0 half of the checkpoint check:

| kind | train acc (λ=1) | held acc (λ=1) | held majority |
|---|---|---|---|
| parts | 94.1520 | 58.3333 | 52.7778 |
| context | 96.7949 | 60.2941 | 75.0000 |
| role_set | 80.5556 | 83.3333 | 83.3333 |
| edge_account | 82.0155 | 73.8971 | 80.1471 |

  Every held accuracy sits inside a random-query null (P from 0.1633 to 0.9833). Leaving out 5 TRAINED worlds fails the same
  way, so any unseen world fails. The published 96.3758% (context) is exact-name recall: seen names 96.8627–100.0000, unseen
  names 50.0000.
- **Verdict — claim state corrected 2026-09-19 by the incoming agent, after re-reading `INPUT_DEFECT_MEASUREMENT.md`.**
  MEASURED: no transfer to a never-practised world **for the four per-bit kinds probed** (`parts`, `context`, `role_set`,
  `edge_account`), and any never-seen slot name gets chance whether it sits in a new world or a practised one. INFERRED,
  **not** measured: "impossible for ANY learner, ALL kinds" — that follows from the hash construction
  (`binding.py:198-202`) plus the q-blind ceiling, and `INPUT_DEFECT_MEASUREMENT.md` line 168 already marks it INFERRED.
  The four choice kinds (`definition`, `analogy`, `correspondence`, `reach`) were never probed, and three of them are in the
  new RELATIONAL tier, so the distinction is load-bearing for the pointer gate. Record this as a REAL negative about the OLD
  machine's input for the four probed kinds (the spec-sheet row of this hand-off's commit is already worded correctly).
- **Independently reproduced 2026-09-19.** `build2.pkl` was never committed, so none of the above could be re-checked from
  the repo. It was rebuilt and the whole chain re-run: gate digests matched, 2,598 slots, 2,442 distinct rows, both analysis
  stdouts identical after stripping wall-clock timings, summary JSON canonically identical. Rebuild takes about 900 s.
  Record: `pre_design/measurements/input_defect/RERUN_VERIFICATION_20260919.md`.
- **Checkpoint files: 30 exist on disk, 18 are shipped.** `initial`, `pass_01`, `final`, `prelast` and `retained` exist for
  each of the 3 seeds; only the first three are in the checkpoint-check ship list (§5.1). `prelast` and `retained` stay
  unshipped so the check costs what the owner was told (~$0.38–0.63 per job, M2).

Other facts found this session:
- **Data model.** Course worlds have 3 or 4 nodes (52 with 4, 12 with 3), each node `{ref, label, kind:"idea"}`; 3–4 directed
  `contains` edges `{ref, source(parent), target(child)}`; `declared_whole`; declarations `{domain, function, kind,
  participants (3 refs), primary_labels, setting, participants_basis}`; `branch_order`. Eight kinds: role_set, definition,
  context, analogy, correspondence, parts, edge_account, reach. Answer rules are in `checker.py` (`_derive_values`, `_reach`,
  `_bfs`, isomorphism via permutations).
- **Reach breaks ties by alphabetical node order** (`checker.py:115-151`, BFS over sorted neighbours) and has TWO rules:
  `bfs_immediate_predecessor_lexical_v1` (all 59 course reach records) and `first_direct_constituent_lexical_v1`.
- **The ten-node development panel** (59 questions: 53 reach + 6 parts) uses `first_direct_constituent_lexical_v1` for all 53
  reach questions — a rule the course NEVER teaches. Report it as "unpractised rule"; never gate on it.
- **PDF:** see `pre_design/PDF_ASSESSMENT.md`. Its cited commits `83322e8f`, `9597840c`, `b6f42eb8` are real. Adopted: held-out
  ladder labelling, ablation ("disable the learned part → benefit drops"), per-tier reporting, evidence-class wording. Rejected:
  using the outside TypeSafe/Jev model (not neuron learning; its contract forbids training on its outputs; foreign-model rule).
- **CASformer v0.2** (`pre_design/CASFORMER_V0_2_MAP.md`): source-frozen (dec08c81; 50+26 files, manifests intact). Public
  imports allowed (`RegisteredOperationBank`, `DECOMPOSE`, `OhmicMultiheadAttention`, ...). The typed learner gets its ^6 block
  via `cncm.typed_matched_worker._framework(torch, device, seed)` → `build_graph_training_framework(...)`; the bank draws ^6
  weights FIRST from the seeded RNG, so **for the same seed the ^6 block starts from exactly the practice study's weights**.
  `OhmicMultiheadAttention` (self-attention with hard topology/permission masks as adjacency) is a candidate message-passing
  layer for a LATER version; v0.1 should use plain dense adjacency matmuls (deterministic, simple).

---

## 4. The design so far (draft v0.1 — superseded in parts by §5)

Full text: `pre_design/DESIGN_DRAFT_v0.1.md`. Core idea:

- **Keep** the interface: the new learner outputs, for every slot of the EXISTING slot plan (`slots.compile_slots(packet)`),
  one logit per declared symbol, in `slot["symbols"]` order. Then `slots.score_decisions`, `slots.assemble_answer`, the private
  checker, `TypedCourseLearner._tensor_loss` (incl. joint correspondence), seal-before-targets, the holdout split, the schedule
  and the scoring all stay unchanged.
- **Input reading** (pure, public-only, deterministic): the focus world (+ correspondence target world; + every world a
  world-choice slot lists) as a graph. Per node ONLY its own raw facts: flags {declared whole, participant (+rank), primary label
  (+rank)}; question flags {is the `whole` argument, is the `part` argument}. Directed `contains` adjacency goes ONLY into
  message passing, never into a readout head. Per world: domain text vector; flags {is focus, is target}. Query: kind (+ rule,
  see §5). Supports, worked answers, instruction and cue are never read.
- **Network** (~45K weights): node embedding → K rounds of message passing with shared weights, update
  `h ← h + ^6(W_self h + W_down Σparents + W_up Σchildren)` using the registered ^6 block unchanged → pointer heads: yes/no per
  node (parts, context participants), per edge pair (edge_account), per role (role_set); node-choice by `<W q, h_v>` (definition
  whole, reach VIA, correspondence targets) with learned option vectors (ABSENT, DIRECT, NO_MATCH, mode); world-choice by
  `<W [q; g_focus], g_w>`.
- **Study:** same course, same frozen holdout (5 twin-free worlds, 127 held records / 50 questions; 79 excluded; 358 trained),
  same schedule (10 passes × 147 updates = 1,470 main + 16 interference + 2 replay), same evaluation points, seeds
  20260917/18/19, AWS g7.2xlarge, $15 reserved per job, sequential.

**Outgoing agent's own recommendation, not yet reviewed:** drop node LABEL words from the input entirely (no rule uses them; they
only add a memorisation channel and a tokenizer-time cost, RK3). Keep only each world's domain word (analogy is cross-domain).

---

## 5. Review findings you must fold into design v0.2

### 5.1 Pipeline / run-killer lens — DONE (`pre_design/DESIGN_REVIEW_PIPELINE_LENS.md`, read it whole)

Headline items and the recommended resolution:

| ID | Problem | Resolution to adopt |
|---|---|---|
| RK1 | `learner.py:271` demands a gradient on EVERY weight; most batches lack most kinds, so per-kind heads get none → `TYPED_LEARNER_GRADIENTS` | Own `train_sealed_batch`: require finite grads on weights that took part, ≥1 grad overall; with `zero_grad(set_to_none=True)` AdamW skips params whose grad is None (no decay step) — register that behaviour; log which params got grads per update |
| RK2 | `TypedCourseLearner.__init__`/`restore_checkpoint` hard-wire the ^6-only scope, 176 updates, 3,600 s, module-level `profile()` | New class `PointerCourseLearner`: ONE container `module` holding every learned weight (^6 block included); own `__init__`, `predict`, `stage_batch`, `train_sealed_batch`, `export_checkpoint`, `restore_checkpoint`, `profile`; borrow `_tensor_loss` by calling it. Never call `scope_parameters` on the container (it freezes non-^6 weights) |
| RK3 | Tokenizing labels per packet costs 0.0111 s/call → blows the 12,300 s deadline | Precompute once, pin its digest (or drop labels, §4) |
| RK4 | Bucket = job + "-807562639912" must be ≤ 63 chars | Study token after `cas-meta2-` ≤ 5 chars (e.g. `tpntr`); add a length test |
| RK5 | Practice launcher hard-codes practice job pattern, authority, task_scope, failure statuses, package members | Override `_user_data`, `bind_authority`, `reservation_plan`, `failure_statuses`, `git_package_bytes` (or copy the provider); keep `_probe()` |
| RK6 | A "reported" check that fails still fails the job (missing artifact; a failed import poisons `attestor.snapshot()`) | Always write the check's artifact with status COMPLETE/FAILED inside; import everything at start-up, outside any try |
| RK7 | `torch.use_deterministic_algorithms(True)` may reject scatter/index/embedding-backward/linalg | Dense adjacency matmuls, one-hot matmuls instead of embedding lookups, closed-form ridge; prove with smoke S1 |
| RK8 | Reusing the practice gate reader → VOID (I1 names the practice worker; I3 compares to matched-study weights) | New `records/typed_pointer_001/evaluate_gates.py` |
| RK9 | Any new `.py` under `cncm/` or `cas_meta2/` between authority and launch blocks later jobs | Keep analysis scripts under `records/`; freeze the tree from authority to job 3 |
| RK10 | The checkpoint check's restore breaks on any byte change to ~15 shared files | Turn `measurements/pipeline_review/r2_restore_identity.py` into a pytest; measured today: all 9 checkpoints match |
| FP1 | **Flag copying alone passes the old gate**: definition 5 + context 5 held questions, b=10, c=0, p=0.0009765625 | **LEARNS_NEW_WORLDS must require the RELATIONAL-tier test** (correspondence 5, edge_account 5, reach 9, analogy 5, parts 5 = 29 eligible, 5 worlds); all-kinds G_LEARN becomes a reported flag; add a test that a flag-copy-only outcome gets no label |
| FP2 | The relational tier is not flag-free: "parts(whole) = participants − whole" solves 3 of 5 eligible held parts questions | Freeze a per-question flag-rule baseline before the run; remove flag-solved questions from the gate population |
| FP3 | Probing first would read held-back answers before training (custody breach) | Phase A first = restore old checkpoints, extract and seal PUBLIC vectors only; Phase B last = derive answers and fit probes after all pointer evaluations/reloads/replays |
| DG1 | Batches use depth 1/2/4/8 (380/370/340/380 updates) | Fixed K=8 rounds; batch depth recorded only |
| DG2 | Reach rule is not an input; swapping it changes 11 answers | Add a rule embedding to the query |
| DG3 | Some reach answers depend on alphabetical node order (5/26 held, 11/71 trained; 2 of 9 eligible held reach questions) | EITHER give each node its rank among the world's sorted refs (world-independent) AND register a rank-only no-learning baseline, removing questions it solves; OR remove the order-dependent questions before the run. Outgoing agent leans: include rank + register the rank baseline |
| DG4 | "I3 re-derives from seed" cannot be computed by a pure-Python reader | In-job: build `matched._framework(torch, device, seed)` FIRST and check its ^6 identity equals the matched study's initial `model_state_identity`; build the whole model twice → identical; three seeds pairwise different; identical start with/without the check |
| DG5 | Held worlds pass through the encoder as wrong world-choice candidates in 1,340 of 8,180 training presentations | Declare it: "never the focus of a trained question", not "never seen" |
| DG6 | Prediction schema must match `loss_plan.validate_prediction` exactly; the `whole` slot follows node order not alias order | Build predictions with the same field set; test it |
| DG7 | |score| ≤ 1e6 and tensor/scalar loss agreement ≤ 2e-5 can break mid-run | RMS-normalize each round; smoke S8 |
| DG8 | Ablations unspecified | Run on restored copies after reload/replay; reset one component to `initial.pt` weights; in EXPECTED_ARTIFACTS; create-only |
| DG9 | New machine → 3 new owner-signed per-job records; the $15/4 h envelope is unmeasured | Measure one pass + one evaluation in a smoke; if a job projects > ~11,000 s, go back to the owner before reserving more |
| DG10 | `practice_contract.DESIGN` carries false fields ("registered_learner_unchanged", old per-slot work counts) | New DESIGN and a new planned-work formula, tested against real counters |

Also: V1–V3 (vacuous checks to replace), M1–M4 (checkpoint duplicates; true cost of the check; RNG overwrite on restore — Phase A
must finish before the pointer model is seeded; the old forward does not expose the post-block vector — copy
`encode_slot` + `recurrence.run_passes` and prove equality by rebuilding logits bit-for-bit against `restored.predict`).

**Checkpoint files to ship** (one package serves all 3 jobs): for each seed, `records/typed_practice_001/receipt_<seed>/checkpoints/
{initial,pass_01,final}.pt` and `{...}_checkpoint.json` — 18 files, 15,259,777 bytes raw, ~5.8 MB compressed, under all limits.
Add them to the new contract's MATERIAL and inventory with pinned sha256 and `run_identity_digest`.

### 5.2 My additions (outgoing agent)

- Tiers, fixed before the run: DIRECT_READ = definition, context; RELATIONAL = parts, edge_account, reach, correspondence,
  analogy; TEXT = role_set. Primary label keyed on RELATIONAL (FP1). Report every tier and every kind.
- Gate arithmetic reminder: with c = 0, the smallest passing b per seed at p ≤ 0.01 is 7 (2^-7 = 0.0078125). Compute the final
  relational population (29 minus flag-solved minus rank/tie removals) and state the minimum passing b in the protocol.
- Reuse the practice study's `split`, `practice_schedule`, `interference_batches`, `retention_packets`, `development_packets`,
  `held_back_questions` UNCHANGED (import them). The holdout digests must equal the practice study's (test P1).
- Keep the frozen typed encoder object as `learner.encoder` so `base._state` / `_check_state` / `export_state` work, even though
  the pointer machine does not use its packet vectors.

### 5.3 Two review lenses NOT captured — re-run them before you write v0.2

The session started two more adversarial reviewers on `DESIGN_DRAFT_v0.1.md`; the hand-off was written before they returned.
Re-run both (read-only, $0, pure Python), giving each the draft plus §5.1:
1. **Leaks / built-in answers / shortcuts / vacuity:** does anything in the proposed input carry a held answer (check the
   role_set `focal_excerpt` text, analogy/correspondence candidate lists); which answers a single input flag gives with no
   learning (per kind, held and trained); new pointer-space shortcuts ("point at the argument", "point at the focus world",
   "PRESENT for all non-argument nodes") and their held accuracy; permutation vacuity.
2. **Can it learn each kind:** per-kind expressivity with the proposed inputs; 1-WL limits for analogy/correspondence (are any two
   non-isomorphic course worlds indistinguishable by mean-pooled message passing with these flags?); stability of 8 shared
   rounds; whether label words only enable memorisation; optimiser adequacy (AdamW, 1,470 updates, batch ≤ 8); whether the input
   reading works on the ten-node development worlds.

Then run a SECOND full review of the BUILT code before any spend (the practice study's second review found three leaks the first
redesign created).

---

## 6. Build plan — new files only, zero edits to shared modules

| # | File (under CNCM) | Content |
|---|---|---|
| 1 | `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_contract.py` | Pure. Imports the practice split/schedule/etc. New `CANDIDATE` (e.g. `CNCM_TYPED_POINTER_LEARNING_001`), `CONFIG_SCHEMA`, `JOB_PATTERN` with a ≤5-char token (`cas-meta2-tpntr-\d{14}-([a-f0-9]{8})-m-(20260917\|20260918\|20260919)`), MATERIAL incl. the 18 checkpoint files with pinned sha256, `input_inventory` wrapper, new DESIGN, deadlines, planned-work formula, tier lists, frozen flag-rule / rank-rule baselines and the gate population, `make_config` / `validate_config` |
| 2 | `.../typed_teaching/pointer_inputs.py` | Pure, deterministic public reader with a digest: per-world node flags, rank (if adopted), adjacency, domain-word ids, query kind/rule/argument marks, excerpt word ids with world refs replaced by placeholders. Never reads supports, cue, instruction, labels (if dropped), node alias positions beyond the registered rank |
| 3 | `.../typed_teaching/pointer_learner.py` | Torch only when called. `PointerCourseLearner` per RK2; container module with the ^6 block from `matched._framework` built FIRST; dense-matmul message passing, K=8, RMS norm; pointer heads; outputs the exact prediction schema |
| 4 | `cncm/typed_pointer_worker.py` | Adapted from `typed_practice_worker.py` (reuse `_publish`, `_move_in`, `_append`, `_train_logged`, `_evaluate`, `_split_score`, `base._ProgressWriter/_state/_check_state/_partial_checkpoint/_score_seal`). Phases: preflight → packets → **checkpoint check phase A** → seed + double build (DG4) → 10 passes with evaluations → retention/interference → reloads/replays → **phase B probes** → ablations → source verification → deliver. Own `EXPECTED_ARTIFACTS` (< 500 files), own expected-work check |
| 5 | `research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py` | Subclass/copy of the practice provider with the RK5 overrides; `bootstrap_source().replace("typed_matched_worker", "typed_pointer_worker")` keeping the count check; reservation "15.00" |
| 6 | `records/typed_pointer_001/evaluate_gates.py` | Copy of the practice reader with new I1, DG4 I3, RELATIONAL primary label, reported all-kinds G_LEARN, per-tier/per-kind tables. Labels: `LEARNS_NEW_WORLDS` / `NO_TRANSFER_TO_NEW_WORLDS` / `VOID` (plus a registered relational flag) |
| 7 | `records/typed_pointer_001/{prepare_study.py, execute_study.py, preflight_dry_run.py, holdout_audit.py}` | Adapted from the practice versions; owner text verbatim (§2) in every job's `owner.json` |
| 8 | `docs/CNCM_TYPED_POINTER_STUDY_v0.1.md` | The frozen protocol (sha pinned in `study.json`) |
| 9 | `tests/test_typed_pointer_study.py` | §7 tests; self-contained `sys.path` block at the top (other tests rely on side effects) |

---

## 7. Tests required before any paid launch

Pure ($0, pytest): P1 holdout/schedule identical to the practice study (held digest `668e6ce7...`, excluded `b82108e1...`,
batches `daf95831...`, 45 eligible / 5 shortcut); P2 bucket length ≤ 63; P3 inventory has the 18 pinned checkpoint rows within
bounds; P4 restore-identity freeze test for all 9 checkpoints; P5 package dry run (archive ≤ 24 MiB; rendered worker is
`typed_pointer_worker`); P6 launcher overrides; P7 EXPECTED_ARTIFACTS unique, < 500, `required_count` = len + 3; P8 worker refuses
Windows before any numeric import and delivers a FAILED result; P9 input reader purity, determinism, bounded per-packet time; P10
inputs exclude supports/cue/instruction and include the reach rule; P11 planned-work formula; P12 gate reader: flag-copy-only gets
no label, exact arithmetic, new I3; P13 frozen flag-rule/rank-rule baselines and removal lists; P14 custody: checker imported and
targets derived only after the first pointer seal (except phase B).

GPU smoke (NOT claim-bearing): S1 all 8 kinds forward+backward under deterministic mode, bit-identical twice; S2 train on a batch
missing most kinds and on an interference batch; S3 export → restore → predict identical, replay from prelast equals final; S4
evaluation leaves state unchanged; S5 identical start with the check on/off and ^6 identity equals the matched start; S6 phase A
restores all 3 checkpoints and rebuilt logits equal `restored.predict` bit-for-bit, and a forced failure still writes the
artifact; S7 time one pass + one evaluation → projected job time; S8 score bounds and loss agreement; S9 node-relabelling
equivariance (engineering only); S10 the worker's `run()` end-to-end on a shrunken schedule.

**Where smoke can run:** `execution_guard()` requires Linux + `CAS_META2_RUN_TEACHING_CYCLE=1`, and the worker requires torch
`2.11.0+cu128` and an "RTX PRO 4500" GPU. So: S1, S2, S7 (module-level), S8, S9 can run on the local RTX 4070 by driving the
network module directly (venv `~/venvs/cas-gpu`, dev only); WSL2 Ubuntu exists (stopped) if you want the guarded class locally;
**S10 needs a short AWS smoke job** on the real instance (a few minutes, well under $1) — ask the owner first (§12).

---

## 8. Checkpoint check (owner-approved part), precise spec

- **$0 half — DONE** (§3 table). Keep it as the recorded "pre-block" result; it need not be recomputed on the GPU (pipeline
  review V2: the pre-block vectors are identical at every checkpoint because the encoder is frozen).
- **GPU half, inside each job, in two phases:**
  - Phase A (first, cheap, no answers): restore that seed's practice checkpoints `initial`, `pass_01`, `final` with
    `PracticeCourseLearner.restore_checkpoint` (framework from `matched._framework`); for every slot of all 564 records compute
    the post-block vector by copying the forward internals; verify by rebuilding logits bit-for-bit against `restored.predict`;
    seal the vectors create-only. Must finish BEFORE the pointer model is seeded (restore overwrites RNG state).
  - Phase B (last, after all pointer work): derive answers, fit the trained-world → held-world ridge probe per kind on the
    post-block vectors at each checkpoint; do the same on the pointer machine's node states at initial / pass_01 / final.
    Report only; always write the artifact with a status field.
- Cost: about 9–15 minutes per job (tell the owner, §2).

---

## 9. Freeze, review, dry-run, launch — the procedure

1. Write design v0.2 (fold §5), write `docs/CNCM_TYPED_POINTER_STUDY_v0.1.md`, build §6, write §7 tests; `pytest` green.
2. Adversarial pre-flight review of the BUILT code, twice (fix, then review again). Record both as
   `records/typed_pointer_001/PREFLIGHT_REVIEW.md` with findings files.
3. Stand-in dry run (`preflight_dry_run.py`, pattern of the practice one): real everything except the learner; create-only
   publisher simulation; write-audit hook. Must print `PREFLIGHT_PASS` for all three seeds.
4. GPU smoke per §7; S10 on AWS only after owner OK.
5. Commit everything (the package is built from git HEAD blobs; any uncommitted `.py` fails `INPUT_NOT_COMMITTED`), push.
6. `python records/typed_pointer_001/prepare_study.py` → `admission_001/{study.json, 2026091X/{request,authority,owner}.json,
   rehearsal}`; commit + push that freeze BEFORE the first launch (the practice freeze commit was `c4f7c321`).
7. Launch sequentially, in the background, logging to a file:
   `python records/typed_pointer_001/execute_study.py --execute records/typed_pointer_001/admission_001/study.json <sha256>`
   It stops on the first failure (explicit `stop_unless`, never `assert`). One job at a time (us-west-2 GPU quota is 8 vCPU).
   Do NOT change any `.py` under `cncm/` or `cas_meta2/` until all 3 jobs have launched (each re-validates the inventory).
8. The gate program's printed label IS the claim status. Write `records/typed_pointer_001/POINTER_STUDY_RESULT.md`, update
   `records/MACHINE_STATE_001/STATUS.md`, `CHANGELOG.md`, the spec sheet row (with artifact paths), back up receipts to
   `D:\tksCAS-archive\cncm_typed_pointer_001_<date>` with sha256 checks, commit + push, then report to the owner in plain English.

**AWS facts:** account 807562639912, region us-west-2, instance g7.2xlarge (RTX PRO 4500), observed $2.52/hour; bucket = job +
"-807562639912"; credentials are local (`~/.aws/`), never print or copy them. Lifecycle modules:
`research/CAS_META_2_COMPOSITION/aws/typed_matched_launch.py`, `graph_training_candidate_launch.py`,
`graph_training_curriculum_launch.py`. The practice jobs took 6,064 / 6,082 / 6,025 s of instance time (~$12.72 total).

---

## 10. Claim status right now

- 🟥 REAL (negative): the old machine does not transfer to never-practised worlds (`8cdbad81`).
- 🟥 REAL (negative, measured $0): the old machine's input makes such transfer impossible by construction (§3).
- ⬜ OPEN: whether a pointer machine's neurons learn a skill that transfers. Nothing built, nothing run.
- NOT LICENSED: any claim about the pointer machine, CASformer attention, or the architecture family.

---

## 11. Traps already hit (do not repeat)

- Hold-outs in this course leak six ways (rule twins, worked supports, same-world priors, look-alike worlds, analogy answers
  naming worlds, supports reaching worlds through arguments) — the current split already closes them; do not re-derive a split.
- Identical numbers across a sweep = your knob was imported by value; you are setting the wrong module.
- A "reported, not gating" phase can still kill a job (RK6).
- `python -O` strips `assert`: every stop in a spend path must be an explicit check.
- Bash heredocs with quotes break easily on this machine: write scripts to the scratchpad and run them.
- **The worktree lives under OneDrive, and files can transiently vanish from a directory listing.** On 2026-09-19
  `pointer_inputs.py` was present at 25,627 bytes, then absent from both `Test-Path` and `Get-ChildItem`, then present
  again **with the same size and the same modification timestamp**. It was never deleted: OneDrive had placed it as a
  cloud-only placeholder. Two consequences. (a) **Do not conclude a file is lost from one failed listing** — re-check,
  and compare size and mtime before reacting; the module's compiled bytecode in `__pycache__/` is further evidence it
  existed and imported. (b) **Snapshot every new file with a commit the moment it first appears.** An uncommitted
  hour of work is one sync glitch from being unrecoverable, and committing an in-flight file cannot disturb the agent
  writing it — the agent's later edits simply show as modifications.

---

## 12. 🔒 Owner action items (the next agent must put these LAST in its report)

**Items 1–3 were ANSWERED by the owner on 2026-09-19, in the session that picked up this hand-off. Do not re-ask them.**

1. **Two corrections — ✅ ACCEPTED, both.** (a) The in-job checkpoint check costs about $0.38–$0.63 per job, not "no extra
   cost". (b) Pointer answers alone cannot work: the INPUT must change too, so the machine reads one world as a small graph
   instead of a blend of all 64 worlds. Owner answer verbatim: *"Accept both, carry on."*
2. **Short AWS smoke job for the end-to-end worker test S10 — ✅ APPROVED.** Well under $1. It doubles as the timing
   measurement for S7/DG9 and must run before the paid launch. Owner selected the option labelled verbatim
   *"Approve the smoke job (Recommended)"*. Cost model and shrunken schedule:
   `pre_design/AWS_SMOKE_S10_PLAN.md` — the measured non-worker overhead is 598.2 s (boot, install, delivery) costing
   $0.42 on its own, so the approved $1 leaves the smoke a worker clock of at most about 830 s.
3. **Gate change — ✅ CONFIRMED.** `LEARNS_NEW_WORLDS` will require gains on the RELATIONAL kinds (parts, edge_account,
   reach, correspondence, analogy), because copying one input flag otherwise passes the old gate (FP1: b=10, c=0,
   p=0.0009765625). Owner answer verbatim: *"Yes — require the relational kinds."* The all-kinds result is reported
   alongside as a flag, not as the label.

**Still open:**

4. **Budget, conditional.** If the smoke timing projects a job above ~11,000 s, a larger per-job reservation needs a new
   approval. The approved envelope is ~$13 expected, $45 reserved in total. Nothing has been re-asked yet.
5. Vercel MCP server needs authorisation in an interactive `claude` session (`/mcp`) — unrelated to this work, untouched.
