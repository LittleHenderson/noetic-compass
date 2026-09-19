# CASformer v0.2 map, for reuse in the pointer machine

> Produced 2026-09-19 by a read-only $0 sub-agent. READ/MEASURED labels are the agent's.

CASFORMER v0.2 MAP (read-only, $0, standard library only, no torch run)

ROOTS
- WT = C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE
- V2 = WT\research\CAS_CJT_TRANSFORMER_v0_2 (package `cas_cjt`, version 0.2.0)
- V1 = WT\research\CASFORMER_v0_1 (package `casformer`, version 0.1.0; v0.2 depends on it, see neural.py:17-23)
- M2 = WT\research\CAS_META_2_COMPOSITION\cas_meta2
- Scratch: C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner\12c87ae7-c1f0-44b3-9b95-de65d5efbd48\scratchpad\understand
  - I checked `param_count.py` and `check_freeze.py` from the earlier attempt against the source, re-ran them, and they are correct.
  - I added `decompose_equiv.py`.
  - The `dm_*`, `defect/` and `pdf_*` files belong to other tasks and were not used.

## 0. Is the frozen code intact? (MEASURED)
- **V2 manifest:** 50 files, 0 mismatches. Recomputed aggregate hash = declared = 5fad64a52c8aef30d56e46fa22f113c26bc171a3016d326c3c88157425b798f1. Manifest file sha256 = f68b9ba7…e634.
- **V1 manifest:** 26 files, 0 mismatches. Aggregate hash = 324603abfdcba59cb68d7351d822f612c2409dcd396d42e9e91fd3df2bbe091e. Manifest file sha256 = abcc0b77…0460.
  - Both match `SOURCE_FREEZE.json`.
- **Nothing changed since the freeze:** `git diff dec08c81..HEAD` on V1 and V2 shows only the 51 artifact files (4,880 lines added) from b5d52d1f. b5d52d1f is an ancestor of HEAD.
- **Worktree:** V1 and V2 have no uncommitted changes (`git status --short` on both was empty).

## 1. Architecture (READ unless tagged)

### Config fields: `CASformerConfig` (V1 casformer/core.py:322-407, frozen dataclass)
- `d_model` (required, no default)
- `num_heads` (required; must divide `d_model`)
- `num_relations=4`
- `num_layers=1`
- `d_ff=None` (then 4·d_model; core.py:405-407)
- `dropout=0.0` and `attention_dropout=0.0` (any non-zero value is refused; core.py:384-385)
- `minimum_total_resistance=0.1`
- `reference_resistance=1.0`
- `reference_drive=1.0`
- `initial_beta=1.0`
- `beta_max=4.0`
- `initial_cutoff=0.25`
- `initial_saturation=8.0`
- `linear_weight_mode="standard"` (the other allowed value is "differential_conductance")
- `minimum_weight_resistance=0.1`

### d_model used in practice
v0.2 fixes no width.
- CNCM typed learner: 64. The config is built at M2\graph_teaching\real_framework.py:73-76 with d_model=64, num_heads=2, num_relations=4, num_layers=1, initial_cutoff=0.01, initial_saturation=100.0.
- v0.2 demo: 4 (examples/complete_reasoning_transistor.py:32-40).
- tests/test_neural_core.py:78 uses 8.

### The four typed transforms (V2 cas_cjt/neural.py)
Each one maps [..., d] to [..., d]. Every linear layer has no bias term (`_linear`, neural.py:104-112).

| Op | Class (lines) | Math | Registered name | Relation index | Status |
|---|---|---|---|---|---|
| ^6 | `_DecomposeTransform` (115-126) | merge(cat(tanh(left x), tanh(right x))) | decompose | 0 | CANONICAL_ADMITTED |
| ^2 | `_AttractTransform` (129-138) | tanh(direction x)·sigmoid(gate x) | experimental_attract | 1 | EXPERIMENTAL_OPEN_SEMANTICS |
| ^3 | `_AvertTransform` (141-150) | −tanh(direction x)·sigmoid(gate x) | experimental_avert | 2 | EXPERIMENTAL_OPEN_SEMANTICS |
| ^8 | `_TriggerTransform` (153-162) | response(gelu(source x)) | experimental_trigger | 3 | EXPERIMENTAL_CONFLICTED_SEMANTICS |

Registrations are at neural.py:72-101. They are cross-checked against types.py:732-739 (`BUILTIN_OPERATION_IDENTITIES`).

### `RegisteredOperationBank(config)` (neural.py:165-316)
- It is a `ModuleDict` named `modules_by_operation`. Modules are built in this order: ^6, ^2, ^3, ^8 (neural.py:181-188).
- `bank(op_id, x)` runs one transform (270-288).
- The four built-ins run without any contract binding. Only extensions need `bind_contract` first (253-264).
- An extension must be named `experimental_*`, must be non-canonical, and must use an unused relation index. Its output must have the same shape and dtype and be finite (202-242, 275-287).

### `NeuralCJT(config)` (neural.py:330-399)
- It contains `engine` = `CASformerBlock`, `operations` = `RegisteredOperationBank`, and `bias_update_head` = Linear(d,d).
- forward(x [B,S,d], control, operation_id):
  1. Every candidate edge must have `relation_ids == op.relation_index`. Otherwise it raises `NeuralCJTError` (346-356).
  2. It runs the engine but throws away the residual/FFN output (368-374).
  3. effect = op(out_proj(merge_heads(telemetry.cjt_effect))).
  4. `execution_mask` = (cjt_gate>0).any over heads, shape [B,S] (377).
- It returns a `NeuralCJTProposal`:
  - `candidate_effect` [B,S,d]
  - `proposed_bias_delta` [B,S,d]
  - `execution_mask` [B,S] bool
  - `telemetry`
- It has no authority.

### `CASformerBlock` (V1 core.py:967-1039)
- Data path: input LayerNorm → `OhmicMultiheadAttention` → `CJTRegionGate` → effect = tanh(bias_heads + β·gate·head_out) − tanh(bias_heads) (1016-1019) → out_proj → residual → LayerNorm+FFN (GELU) residual.

### Cross-element and graph mechanisms
There is exactly one learned cross-element mechanism:
- **`OhmicMultiheadAttention`** (V1 core.py:481-752). This is self-attention only: `control.validate` is called with key_length = query_length = sequence (585-595).
  - logits = QKᵀ/√hd + route_log, where route_log = log drive − log ref_drive + log readiness + log region + log ref_R − log(total R) (639-646).
  - It is a masked softmax over valid paths. A row with every path closed gives exact zeros (687-700).
  - Per-edge relation ids pick a per-head [hd,hd] operator that is applied to the attended values (704-721). At init, relation 0 is the identity; relation r>0 is identity + 0.025·r·roll (518-534).
  - Hard `topology_mask` and `permission_mask` [B,h,S,S] work as an adjacency matrix.
  - `telemetry.attention` [B,h,S,S] is a proper distribution per row, so it can serve as a pointer.

Everything else here has no learned cross-element part:
- **`casformer.LearnedCASControlAdapter`** (V1 controls.py:47-): learned pairwise fields, each softplus(query_i + key_j) from Linear(d,h) pairs (controls.py:18-44). This is additive and rank-1 per head, not bilinear.
- **`DifferentiableConductanceCircuit`** (V1 circuit.py:21-): no parameters. It solves the graph Laplacian (Bᵀ diag(1/R) B + damping·I) u = drive, with incidence [E,N] or [B,E,N], resistance [E] or [B,E], drive [B,N,C].
- **`CASOhmRouter`** (V2 routing.py:779-780): "Parameter-free CAS-Ohm route evaluator".
- **`NeuralCJTNetwork`** (V2 network.py:39-167): a container of whole `NeuralCJT` cells plus a directed edge table (`edge_permitted`, `select_candidates`). Node selection is deterministic. There is no learned message passing between cells. `parameter_names_for_node` (128-150) gives per-node lists of parameters allowed to learn.

### Parameter counts
Settings: d=64, h=2, relations=4, d_ff=256, standard mode. The arithmetic comes from the source shapes (MEASURED by param_count.py; the module was not instantiated).

| Module | Parameters |
|---|---|
| ^6 | 16,384 (left 64×64, right 64×64, merge 64×128) |
| ^2 | 8,192 |
| ^3 | 8,192 |
| ^8 | 8,192 (source 64×64, response 64×64) |
| Bank total | 40,960 |
| Attention | 24,576 (q, k, v, out = 16,384; relation_operators [4,2,32,32] = 8,192) |
| CJT gate | 146 (raw_beta/cutoff/span 3·h = 6; bias_projection 128; diagnostic_projection 5→2 with bias = 12) |
| `cjt_effect_bias` | 4,096 |
| LayerNorms | 128 each, 2 of them |
| FFN | 33,088 |
| `CASformerBlock` | 62,162 |
| `bias_update_head` | 4,096 |
| **`NeuralCJT` total** | **107,218** |

- At the demo size (d=4), `NeuralCJT` = 478 and ^6 = 64 (MEASURED arithmetic).
- In differential_conductance mode, each weight becomes two tensors, `raw_positive_resistance` and `raw_negative_resistance` (core.py:1152-1261). So ^6 = 32,768 and ^8 = 16,384 (INFERRED).
- INFERRED from code: `NeuralCJT` never uses the FFN plus its LayerNorm (33,216 parameters). They get no gradient from `candidate_effect`.

## 2. Source-freeze rules (READ)
- **What dec08c81 froze:** "the unchanged 50-file v0.2 source set, frozen v0.1 dependency, locked Windows CPU test dependencies, and the committed CNCM regression footprint".
  - 271 files; tree a56fc8b8…; parent 1e58d725.
  - The freeze includes the 26-file V1 and the CNCM regression footprint (cncm/, spec/, schemas/, fixtures/golden) that lets the frozen CNCM regression (181 tests / 403 subtests) run from the freeze commit.
- **What must not change:** every path in V2\SOURCE_MANIFEST.json and V1\SOURCE_MANIFEST.json. That covers all of `cas_cjt/*.py`, the schemas, docs, tests, pyproject, and `casformer/*.py`.
  - This is enforced by V2 tests/test_source_manifest.py (4 tests: 34, 74, 118, 141).
  - BUILD_CONTRACT.md:19-23 pins the V1 aggregate hash.
  - reproduce.ps1 enforces the embedded 50-file manifest.
- **Evidence rule:** the evidence commit must have dec08c81 as its sole parent and must change only the v0.2 artifacts tree (VALIDATION_RECEIPT `evidence_binding.git_binding_rule`).
- **Downstream pins:**
  - M2 typed_teaching/learner.py:29-44 hashes graph_teaching/trainer.py and real_framework.py into the learner profile digest.
  - M2 child_scaffold_v8.py:26-27 pins sha256 of cas_cjt/runtime.py and verifier.py.
  - M2 diagnostic_v8/gpu.py:112-116 checks the installed `casformer` source against the manifest.
- **What a consumer may import** (package-root lazy exports, cas_cjt/__init__.py:134-151; API_CONTRACTS.md:44-80):
  - `NeuralCJT`, `NeuralCJTProposal`, `RegisteredOperationBank`, `OperationRegistration`, `OPERATION_REGISTRATIONS`
  - `DECOMPOSE`, `ATTRACT`, `AVERT`, `TRIGGER`
  - `CJTNodeSpec`, `NeuralCJTNetwork`, `TopologyEdge`
  - `CASOhmRouter`
  - the typed records
  - from casformer: `CASformerConfig`, `CASControl`, `CASformerBlock`, `OhmicMultiheadAttention`, `DifferentialConductanceLinear`, `LearnedCASControlAdapter`, `DifferentiableConductanceCircuit` (V1 casformer/__init__.py)
- **Private names:** `_DecomposeTransform` and `_TriggerTransform` are not exported. The sanctioned route is `bank.modules_by_operation[DECOMPOSE]` or `[TRIGGER]`.
- **Integration limits:**
  - ROADMAP.md:72-74: "Do not import this prototype into CNCM 0.1.0 as hidden authority."
  - CNCM_INTEGRATION_BOUNDARY.md: `NOT_RUNTIME_INTEGRATED`.

## 3. Evidence status words (READ, exact)
- README: `FIRST COMPLETE LOCAL MECHANISM PROTOTYPE`
- BUILD_CONTRACT: `COMPLETE FOR THE v0.2 LOCAL MECHANISM PROTOTYPE`
  - RT-01..RT-15 = COMPLETE
  - D-07 = `COMPLETE AS PROPOSAL-ONLY BOUNDARY`
  - D-09 = `COMPLETE AS ROADMAP ARTIFACT`
  - D-10 = `COMPLETE AS EXTENSION MECHANISM`
- ARCHITECTURE: `IMPLEMENTED LOCAL MECHANISM PROTOTYPE`
- API_CONTRACTS: `IMPLEMENTED AND COVERED BY PUBLIC API TESTS`
- EQUATIONS: `LOCAL MECHANISM PROTOTYPE CONTRACT`
- ROADMAP: `FIRST REASONING-TRANSISTOR MECHANISM MILESTONE REACHED`
- MEMORY_RESEARCH_PLAN: `ACCEPTED AS A POST-v0.2 RESEARCH PLAN; NOT IMPLEMENTED IN v0.2`
- OPERATION_EXPANSION: `FOUR BUILT-INS PLUS TESTED NEURAL-BANK EXTENSION / FULL CANONICAL VOCABULARY OPEN`
- CNCM boundary:
  - `IMPLEMENTED PROPOSAL-ONLY ADAPTER / NOT ADMITTED BY CURRENT CNCM`
  - `NOT_RUNTIME_INTEGRATED`
  - envelope `INERT_PROPOSAL_ONLY_NOT_ADMITTED_BY_CURRENT_CNCM`
- SOURCE_MANIFEST: `LOCAL_NEURAL_CJT_MECHANISM_PROTOTYPE_SOURCE_SET`
- SOURCE_FREEZE.json: `SOURCE_FREEZE_VERIFIED`
- VALIDATION_RECEIPT:
  - status `CASFORMER_V0_2_RELEASE_REPRODUCED`
  - classification `LOCAL_RELEASE_REPRODUCTION_WITH_HASH_BOUND_EVIDENCE`
  - tests: 250 v0.2, 5 manifest, 89 v0.1, 181 CNCM + 403 subtests, all passed, 0 failed
  - demo: 5 accepted effects, 6 traces
  - 7 of 7 required checks passed
  - 46 payload files
  - FINAL_VALIDATION status PASS
  - environment: torch 2.11.0+cpu, CUDA not available
- Audit: `CAS_CJT_TRANSFORMER_V0_2_CODE_AUDIT_PARTIAL` ("ACCEPT AS PARTIAL", audit txt:324). The pre-freeze receipt is `HISTORICAL_ONLY`.
- `claims_not_promoted`: language capability, general reasoning capability, CAS-specific advantage, CNCM brain completion, AGI, production readiness.
- `evidence_boundary`: organizationally_independent false, cryptographically_signed false.
- V1 status (AUTHORITY_MANIFEST.yaml:364-366): `REFERENCE_IMPLEMENTATION / NOT_TRAINED / NOT_KERNEL_INTEGRATED`. `casformer_advantage_established: false` (line 461).
- V1 CLAIMS.md negative results:
  - `SCALAR_ROUTING_REPARAMETERIZATION_ONLY` (:22): Ohmic routing is ordinary attention plus an additive logit bias.
  - `CONDUCTANCE_ONLY_FOR_ROUTING` (:24)
  - `TYPE_RELABELING_IS_NOT_A_CAUSAL_CONTROL` (:28)
  - `SIGNED_PAIR_VALID_BUT_REPARAMETERIZED` (:30)
- Typed learner profile: `WORKER_IMPLEMENTATION_NUMERIC_ACCEPTANCE_PENDING` (learner.py:43).
- Practice study commit 8cdbad81 subject: `NO_TRANSFER_TO_NEW_WORLDS`.

## 4. How the CNCM typed learner gets its ^6 block (READ)
1. **Seed and build.** WT\cncm\typed_course_worker.py:191-197 (and typed_matched_worker.py:43-48) call `torch.manual_seed(seed)`, `cuda.manual_seed_all`, then `build_graph_training_framework(torch, device, seed=seed, encoder={"d_model": 64})`.
   - The builder's `seed` argument does not seed torch (comment at worker:192; confirmation.py:85, 466-469). The bank draws weights from the ambient RNG in the order ^6, ^2, ^3, ^8.
2. **Framework build.** real_framework.py:59-83:
   - imports `casformer.CASformerConfig`, `cas_cjt.neural.{RegisteredOperationBank, DECOMPOSE, OPERATION_REGISTRATIONS}` and `cas_cjt.state.make_operation_contract`;
   - `contract = make_operation_contract("^6")`, which must have `contract_id == "cas.cjt.operation.^6.decompose/0.2"` (constant at :23);
   - `"operation:^6"` must be in `contract.plasticity_groups`. That tuple is `("operation:^6","bias_update_head")` (state.py:187);
   - `bank = RegisteredOperationBank(config)`; `module = bank.modules_by_operation[DECOMPOSE]`, moved to the device.
   - Only this module is kept. The other three are built and then discarded. No `NeuralCJT`, attention, gate or `bias_update_head` is used.
3. **Choosing what may learn.** trainer.py:68-91:
   - `select_target` finds the unique registration with the target `contract_id`.
   - `scope_parameters` gets the allow-list from `framework.resolve_plasticity_groups`. That is every `named_parameter` of the module (real_framework.py:45-49). It sets `requires_grad` and returns {allowed, frozen, contract_id, role}.
   - Note: the trainer docstring (:5, :80) says "operator.^6" but the code constant is "operation:^6".
4. **Learner guards.** learner.py:78-86 requires:
   - scope == {"allowed": ["left.weight","merge.weight","right.weight"], "frozen": [], "contract_id": "cas.cjt.operation.^6.decompose/0.2", "role": "operation:^6"}
   - shapes left (64,64), right (64,64), merge (64,128), float32, `requires_grad`.
   - This implies standard linear mode: differential mode would change the parameter names and fail these guards.
5. **Training and inference.** AdamW over those 3 tensors (107-109).
   - The core call is `self.module(torch.stack(incoming).unsqueeze(0))[0]`, [1,64] → [1,64] (137-144).
   - `recurrence.run_passes(..., depth∈{1,2,4,8})` reapplies the same module with the input re-injected each pass (learner.py:149-150; M2 recurrent_cjt/recurrence.py:182-215).
   - Readout = frozen `readout_rows[indexes] @ vector`, [90,64] (153).

## 5. Modules importable unchanged as learnable parts (constructor calls READ; shapes READ from source)
Common setup:
```python
from casformer import CASformerConfig, CASControl, OhmicMultiheadAttention
from cas_cjt.neural import RegisteredOperationBank, NeuralCJT, DECOMPOSE, TRIGGER
config = CASformerConfig(d_model=64, num_heads=2, num_relations=4, num_layers=1, dropout=0.0,
                         attention_dropout=0.0, initial_cutoff=0.01, initial_saturation=100.0)  # = real_framework.py:73-76
bank = RegisteredOperationBank(config)          # builds all 4 ops, 40,960 params; seed torch first
```

**A. ^6 as a node-update or message function**
- Call: `phi = bank.modules_by_operation[DECOMPOSE]`, or `bank(DECOMPOSE, h)`.
- Shapes: h [..., 64] → [..., 64]. It applies to the last dimension only, so [N,64] or [B,N,64] work with weights shared across nodes.
- Parameters: 16,384; names `left.weight`, `right.weight`, `merge.weight`.
- Contract and plasticity role: "cas.cjt.operation.^6.decompose/0.2", "operation:^6". These are the same as the typed learner's. `trainer.scope_parameters` can be reused if the framework object exposes the same `module`, `contract_for` and `resolve_plasticity_groups`.
- It takes one input vector. Any pairwise message must be reduced to 64 numbers outside the module (for example h_i + h_j, or h_i ⊙ h_j).

**B. ^8 as an association channel**
- Call: `psi = bank.modules_by_operation[TRIGGER]`, or `bank(TRIGGER, h)`.
- Shapes: [..., 64] → [..., 64]; 8,192 parameters (`source.weight`, `response.weight`).
- Contract "cas.cjt.operation.^8.trigger.experimental/0.2"; role "operation:^8".
- Example use: pointer score s_ij = ⟨psi(h_i), h_j⟩, computed outside the module.
- Its status travels with it: `EXPERIMENTAL_CONFLICTED_SEMANTICS`. The default verifier returns `EXPERIMENTAL_OPERATION_NOT_AUTHORITY_ADMITTED` (OPERATION_EXPANSION.md:16-18).

**C. Graph attention and pointer**
- Call: `attn = OhmicMultiheadAttention(config)`.
- Forward: `head_out, tel = attn(x, control)`.
  - x: [B,S,64] float, finite.
  - head_out: [B,h,S,hd], i.e. [B,2,S,32].
  - `attn.merge_heads(head_out)` → [B,S,64].
  - `tel.attention` → [B,h,S,S] pointer distribution.
- `control = CASControl.uniform(x, num_heads=2, relation_id=r)` works for tests. A real graph needs a full `CASControl` (core.py:91-108):
  - drive, the 4 resistances, readiness and region_multiplier: float [B,h,S,S];
  - topology_mask and permission_mask: bool [B,h,S,S];
  - relation_ids: int [B,h,S,S];
  - bias: [B,S,d];
  - summed resistance must be ≥0.1 on every candidate path.
- There is no cross-attention: queries and nodes must share one sequence, masked by `topology_mask`.
- 24,576 parameters.

**D. Whole cell**
- Call: `NeuralCJT(config)(x, control, operation_id=DECOMPOSE)`.
- Returns a proposal with `candidate_effect` [B,S,64].
- All candidate edges must use relation 0 for ^6 (or 3 for ^8).
- The gate is zero below the cutoff. When it is zero, both the effect and its gradient are zero (neural.py:377-388).
- 107,218 parameters, of which 33,216 are unused.

**E. Parameter-free graph step**
- Call: `DifferentiableConductanceCircuit(damping=1e-3, minimum_resistance=0.1)(incidence, resistance, drive)`.
- Returns `node_potential`, `edge_current`, `conductance`, `laplacian`, `solve_residual` (circuit.py:11-16).

**Required baseline for any of these** (by the "register a mechanism-free baseline" rule):
- MEASURED (decompose_equiv.py, d=8, 1,000 random inputs, max abs difference 0.0): `_DecomposeTransform` is exactly W2·tanh(W1·x), with W1 = [left;right] of size 128×64 and W2 = merge of size 64×128. That is an ordinary 2-layer tanh MLP with no bias and hidden width 128.
- INFERRED: PyTorch's default initialization bounds match too: 1/√64 = 0.125 for left/right, 1/√128 = 0.08838834764831843 for merge. So an equal-size generic MLP is the matched control, and the "^6" label adds no mechanism by itself (V1 CLAIMS.md:28).
- ^8 is a 2-layer GELU MLP with hidden width d.
- For attention, compare against `casformer.baselines.compiled_ohmic_attention` (baselines.py:40) or plain masked attention, plus `GenericFullStateController` (baselines.py:161).

## 6. CAS naming rules for this reuse (READ: tksCAS\docs\CAS_FOUNDATIONAL_CLARIFICATIONS.md; V2 docs; types.py)
- **^6 Male (clarifications:22).** "An Idea impregnated with another Idea, the Ideas an Idea is composed of." Colloquialisms (:146): "Unpacking an idea" / "Breaking it down". The v0.2 local name is "decompose". It is the only `CANONICAL_ADMITTED` operation. types.py:813-814 refuses canonical status for anything except ^6.
- **^8 Above/Cause (clarifications:24).** "An Idea that triggers a different Idea than itself to come to Mind."
  - Anti-drift rule (:209): ^8 is associative triggering, NOT analytical or causal reasoning.
  - Deductive causal inference is ^6 + ^9, not ^8.
  - v0.2 matches this: "association channel; not deduction authority" (neural.py:154); "does not prove causation" (OPERATION_EXPANSION.md:15-16).
  - The status word stays `EXPERIMENTAL_CONFLICTED_SEMANTICS` and the name stays `experimental_trigger`.
  - Never relabel ^2, ^3 or ^8 as canonical (ROADMAP.md item 7). "The local names for ^2 and ^3 do not establish canonical CAS meanings" (OPERATION_EXPANSION.md:14-15).
- **New operations** (for example ^9 for landing an answer) go only through `register_operation`:
  - name must be `experimental_*`;
  - status must be non-canonical;
  - relation index must be unused, which needs num_relations ≥5 (the tested ^9 example uses 5);
  - `bind_contract` must succeed before the operation can run.
  - The runtime contract factory is frozen at four operations (OPERATION_EXPANSION.md:92-97).
- **Authority:** neural output, flow or scores never grant truth, proof, commitment, state write or halt (CNCM_INTEGRATION_BOUNDARY.md:67-79).
