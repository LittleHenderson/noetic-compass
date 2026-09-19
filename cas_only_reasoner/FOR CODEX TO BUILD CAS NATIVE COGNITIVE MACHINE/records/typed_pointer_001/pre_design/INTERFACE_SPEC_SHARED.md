# INTERFACE_SPEC_SHARED — exact interface contract for the CNCM pointer machine builders

**Status:** read-only extraction from branch `codex/cncm-vision-next`, HEAD `52fea7ed`. No file listed here was modified.
**Purpose:** let a builder write `pointer_contract.py`, `pointer_inputs.py`, `pointer_learner.py`, `cncm/typed_pointer_worker.py`,
`aws/typed_pointer_launch.py`, `records/typed_pointer_001/evaluate_gates.py` and the pointer tests **without reading the whole codebase**.
**Sources of truth:** the source lines cited in every claim below, plus four read-only probes run for this document (pure Python
plus `torch.load(..., weights_only=True)` on a checkpoint file; **no model was built, no tensor op was run on a device**).

## 0. Path correction (read this first)

The task brief gives module paths as `cas_meta2/typed_teaching/...`. **Those paths do not exist under the CNCM root.** The real
package root is `research/CAS_META_2_COMPOSITION/cas_meta2/`, and every module path recorded inside profiles is relative to
`research/CAS_META_2_COMPOSITION/`:

| Brief said | Real path under CNCM root |
|---|---|
| `cas_meta2/typed_teaching/slots.py` | `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/slots.py` |
| `cas_meta2/typed_teaching/learner.py` | `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/learner.py` |
| `cas_meta2/typed_teaching/encoder.py` | `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/encoder.py` |
| `matched_contract.py`, `loss_plan.py`, `tokenization.py`, `source.py` | same folder as above |
| `recurrent_cjt/recurrence.py` | `research/CAS_META_2_COMPOSITION/cas_meta2/recurrent_cjt/recurrence.py` |
| `graph_teaching/trainer.py` | `research/CAS_META_2_COMPOSITION/cas_meta2/graph_teaching/trainer.py` |
| `research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py` | correct as given (this one is right) |

The import setup that every script in this repo uses (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:61-70`):

```python
import sys; from pathlib import Path
CNCM = Path(r"...\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
from cas_meta2.typed_teaching import practice_contract as c
```

`cas_meta2` resolves to `research/CAS_META_2_COMPOSITION/cas_meta2` because only that string is on `sys.path`
(`source.py:22` `PACKAGE_ROOT = Path(__file__).resolve().parents[1]`).

**Precedence rule used in this document:** where the design draft and the source disagree, the source wins, and the disagreement is
called out. One such correction exists — see §D.1 (`model_state_identity` vs the ^6 sub-block).

---

## A. `cas_meta2/typed_teaching/slots.py` (348 lines)

### A.1 Module constants (`slots.py:19-37`)

```python
PLAN_SCHEMA     = "cas.typed-teaching-slot-plan/0.1"          # slots.py:19
DECISION_SCHEMA = "cas.typed-teaching-slot-decisions/0.1"     # slots.py:20
PROFILE_SCHEMA  = "cas.typed-teaching-slot-profile/0.1"       # slots.py:21
SYMBOLS = ("PRESENT", "ABSENT", "DIRECT", "NO_MATCH", "MAPPING") + tuple("N%d" % i for i in range(10)) \
        + tuple("VIA_N%d" % i for i in range(10)) + tuple("W%d" % i for i in range(65))   # slots.py:22-24
MAX_ABS_SCORE = 1000000        # slots.py:25  <- the |score| <= 1e6 bound
MAX_CACHE_ENTRIES = 1024       # slots.py:26
MAX_CACHE_SERIALIZED_BYTES = 256 * 1024 ** 2   # slots.py:27
```
`len(SYMBOLS) == 90` — 5 + 10 + 10 + 65 (probe A: `SYMBOLS length: 90 ('PRESENT', 'ABSENT', 'DIRECT', 'NO_MATCH', 'MAPPING') W64`).
This is exactly the 90 rows of the frozen readout (`learner.py:38` `"readout_rows": 90`; `learner.py:103` `(90, 64)`).

`DECISION_CONTRACT` (`slots.py:28-37`) is a 7-key dict copied verbatim into every plan (`slots.py:117`); keys:
`independent`, `correspondence`, `correspondence_forced`, `candidate_order`, `candidate_ties`, `score_scalar`, `loss_contract`,
`semantic_repair`. `score_scalar` is the written form of the bound:
`"finite exact Python int or float, excluding bool; absolute value <= 1000000"` (`slots.py:34`).

Module aliases at `slots.py:38`:
```python
require, digest, canonical = source.require, source.digest, source.canonical
```
so `slots.require` raises `ValueError`, `slots.digest` / `slots.canonical` are `source.digest` / `source.canonical` (§F).

### A.2 `profile()` — exact hashed files (`slots.py:41-52`)

```python
def profile():                                  # slots.py:41
    raw = Path(__file__).read_bytes()           # slots.py:43  <- ONLY slots.py itself
```
Returns (keys in source order, all confirmed present by probing the real artifact):
`schema`, `symbols` (= `list(SYMBOLS)`), `symbol_count` (90), `world_alias`, `node_alias`, `maximum_slots` (100),
`correspondence_max_nodes` (4), `readout_width_proposed` (64), `decision_contract`, `source_files`, `course_profile`, `status`,
**`profile_digest`** (`slots.py:52` `digest(body)` where `body` is all other keys).

`source_files` is a **one-element** list (`slots.py:49`):
```json
[{"path": "cas_meta2/typed_teaching/slots.py", "bytes": 19341, "sha256": "3d79db262708264dcd77cd7fb0296e7683849b5967b82d72fd3c51ab85f74487"}]
```
(byte count and digest are measured today, probe A.)

It **pulls in `course.profile()`** at `slots.py:50`, and `course.profile()` hashes **15 files** (`course.py:70-76`; the real list,
extracted from the checkpoint artifact, is):
`cas_meta2/complementary_teaching/course.py`, `cas_meta2/graph_teaching/face_corpus.py`,
`cas_meta2/graph_teaching/face_roles.py`, `cas_meta2/graph_teaching/face_schedule.py`, `cas_meta2/graph_teaching/face_tasks.py`,
`cas_meta2/recurrent_cjt/course.py`, `cas_meta2/recurrent_cjt/recurrence.py`, `cas_meta2/rpm_cfc_constructor/diagnosis.py`,
`cas_meta2/typed_teaching/__init__.py`, `cas_meta2/typed_teaching/answers.py`, `cas_meta2/typed_teaching/checker.py`,
`cas_meta2/typed_teaching/course.py`, `cas_meta2/typed_teaching/course_plan.py`, `cas_meta2/typed_teaching/focal.py`,
`cas_meta2/typed_teaching/source.py`.
**So touching `recurrence.py` or `answers.py` changes `slots.profile()` and therefore the learner profile (see GOTCHAS #2).**

Today's values (probe B): `slots.profile()["profile_digest"] == "6cc7b2a630d9c841d43f38d806d777501f6f4095185856f2688fef83150f0a98"`,
`course.profile()["profile_digest"] == "b13a2ad2598dd1494d42714b30cdcd7ba340d1094a2d277f81b6940ff29766dc"`.

`course.profile()` keys: `data_files` (`[]`), `files`, `identity_scope` (`"ON_DISK_SOURCE_NOT_LOADED_WORKER_ATTESTATION"`),
`plan_source_profile`, `profile_digest`, `schema` (`"cas.typed-teaching-course-source-profile/0.1"`).

### A.3 `compile_slots(packet)` — the plan structure (`slots.py:218-220`, compiler `slots.py:63-119`)

```python
def compile_slots(packet):      # slots.py:218
    return _SLOT_CACHE.compile(packet)     # slots.py:220
```

**Top-level plan keys** (real key names, from `slots.py:114-119`; confirmed on a live plan, probe A):
`schema`, `record_id`, `query_id`, `source_digest`, `packet_digest`, `kind`, `profile`, `aliases`, `slots`,
`correspondence_candidates`, `decision_contract`, `forced_candidate_count`, **`plan_digest`**.

Copyable real example of the envelope (real values from the 20260917 practice artifacts):

```python
{"schema": "cas.typed-teaching-slot-plan/0.1",
 "record_id": "typed-input-0245afcca3fe65f5586f723362e44815baab6c982272dc3f1a60487e8da1e53b",
 "query_id": "typed-query-f3bcb04aebded63611d72257aa5b74f6b79f9521eddbb52bf65f39cd7d8100da",
 "source_digest": "<sha256 of the public source, source.public_digest>",
 "packet_digest": "8e1f4ef229d993e909598b929cd6221a660d8102d7fddb3c30418246b20a76b3",
 "kind": "definition",
 "profile": { ...slots.profile()... },
 "aliases": {"worlds": [{"alias": "W0", "world_id": "world-00d90e...", "nodes": [{"alias": "N0", "ref": "world-00d90e.../n0"}, ...]}, ...]},
 "slots": [ ... ],
 "correspondence_candidates": [],
 "decision_contract": { ...8-key dict... },
 "forced_candidate_count": 0,
 "plan_digest": "e849544f2243e93a9c2d7d9059a5b84952a1d504f56e53daf261e57cbf2c7229"}
```

`packet_digest` is `digest(checked)` of the closed learner packet (`slots.py:75`) — i.e. `source.digest` over
`{"source": ..., "record": ...}`. `record_id` / `query_id` / `source_digest` are copied from `record` (`slots.py:114-115`).
`plan_digest = digest(body)` where `body` is every other top-level key (`slots.py:119`).

**Aliases** (`alias_table`, `slots.py:55-60`):
```python
{"worlds": [{"alias": "W%d" % i, "world_id": world["world_id"],
             "nodes": [{"alias": "N%d" % j, "ref": ref}
                       for j, ref in enumerate(sorted(node["ref"] for node in world["nodes"]))]}
            for i, world in enumerate(sorted(public["worlds"], key=lambda row: row["world_id"]))]}
```
`W` index = position in the list of worlds sorted by `world_id`; `N` index = position in `sorted(node["ref"])` **within that
world**. Node aliases are always world-scoped (`slots.py:46`).

**Every key of every slot dict** (`add()`, `slots.py:77-84`) — exactly six keys plus `slot_id`:

| key | value |
|---|---|
| `slot_id` | `"typed-slot-" + digest({"packet_digest": packet_digest, **body})` (`slots.py:84`) |
| `field` | one of `role`, `whole`, `kind_ref`, `function_ref`, `setting_ref`, `participant`, `world_id`, `mode`, `mapping_target`, `node`, `edge`, `reach` (`slots.py:86-107`) |
| `group` | one of `roles`, `whole`, `kind_ref`, `function_ref`, `setting_ref`, `participants`, `world_id`, `correspondence`, `nodes`, `edges`, `reach` (`slots.py:86-107`) |
| `coordinates` | `[]`, `[role]`, `[ref]`, or `[source_ref, target_ref]` — depends on kind (below) |
| `scope_world_id` | the focus world's `world_id`, except correspondence `mapping_target` rows, which use `target` (`slots.py:77-78`, `slots.py:101`) |
| `scope_alias` | `world_alias[scope]`, e.g. `"W40"` |
| `symbols` | an ordered list of symbol strings, all members of `SYMBOLS`, no duplicates (`slots.py:82-83` raises `TYPED_SLOT_SYMBOLS`) |

Real example (definition packet above):
```python
{"slot_id": "typed-slot-688dbf9d8dad9a1f957967f4d95a4aabae182b13b1926b2d96a6bd4f66953f00",
 "field": "whole", "group": "whole", "coordinates": [],
 "scope_world_id": "world-7afc0b967564edb89050f99eeb409560cb401de94fda9bd901d97ee16a5be881",
 "scope_alias": "W40", "symbols": ["N0", "N1", "N2"]}
```

Post-conditions: `0 < len(slots) <= 100` and all `slot_id` distinct, else `TYPED_SLOT_BOUND` (`slots.py:108`).

**Kind → field/group/coordinates/symbols** (`slots.py:85-107`; the counts are the real ones measured on the frozen course):

| `kind` | row(s) added | `field` | `group` | `coordinates` | `symbols` | symbol universe (count) |
|---|---|---|---|---|---|---|
| `role_set` | one per role | `role` | `roles` | `[role]` | `("ABSENT","PRESENT")` | 6 rows, `role` ∈ `ROLE_IDS` `(1..6)` (`answers.py:23`, `147`) |
| `definition` | `whole`, then 2 | `whole` | `whole` | `[]` | node aliases, **node order** (see A.4) | world nodes in packet order: 3 or 4 |
| | | `kind_ref`, `function_ref` | same as field | `[]` | every bank world alias in alias order | **64** (all alias `W0..W63`; `kind_refs`/`function_refs` are 64 long, `answers.py:151-152`) |
| `context` | `setting_ref`, then one per participant | `setting_ref` | `setting_ref` | `[]` | every bank world alias in alias order | **64** |
| | | `participant` | `participants` | `[ref]` | `("ABSENT","PRESENT")` | one row per focus-world node: 3 or 4 |
| `analogy` | one | `world_id` | `world_id` | `[]` | `["NO_MATCH", *world aliases of inv["world_ids"]]` | **65** = `NO_MATCH` + 64 (`slots.py:95`) |
| `correspondence` | `mode`, then one per source node | `mode` | `correspondence` | `[]` | `("NO_MATCH","MAPPING")` | 2 |
| | | `mapping_target` | `correspondence` | `[source_ref]` | aliases of `sorted(inv["target_nodes"])` | target-world node count: **3 or 4** (`MAX_PERMUTATION_NODES = 4`, `answers.py:22`) |
| `parts` | one per node | `node` | `nodes` | `[ref]` | `("ABSENT","PRESENT")` | 3 or 4 rows |
| `edge_account` | one per ordered pair incl. self-pairs | `edge` | `edges` | `[a, b]` | `("ABSENT","PRESENT")` | `n*n` rows: 9 or 16 (`answers.py:165`; 16 seen in probe A) |
| `reach` | one | `reach` | `reach` | `[]` | `["ABSENT","DIRECT", *("VIA_"+alias for ref in inv["via_refs"])]` | `2 + n` = 5 or 6 (probe A saw `['ABSENT','DIRECT','VIA_N0','VIA_N1','VIA_N2','VIA_N3']`, n=4) |

`inv` is `answers.answer_space(public, query)["inventory"]` (`slots.py:68`, built `answers.py:135-171`). `whole_refs`,
`participant_refs`, `node_refs`, `via_refs` are `_nodes(world)` = `[node["ref"] for node in world["nodes"]]` — **packet order**
(`answers.py:74-75`, `143`).
`setting_ref` `add()` uses **all** world aliases (`slots.py:92`), not `inv["setting_refs"]`, even though `answers.answer_space`
also computes `setting_refs` (`answers.py:154`).

Today's real per-kind counts for the one representative record of each kind (probe A): `role_set` 6, `definition` 3,
`context` 4, `analogy` 1, `correspondence` 4, `parts` 4, `edge_account` 16, `reach` 1.
(These track world size: 52 course worlds have 4 nodes, 12 have 3 — so `context`/`parts` are 4 or 3, `edge_account` 16 or 9.)

### A.4 The ordering rule for `slot["symbols"]`, and the `whole` special case

Two different orderings are used, and they are **not** the same code path:

1. **Alias order** (`slots.py:90`, `92`, `95`, `101`): the symbol list is built from `alias_table` output, i.e. worlds sorted by
   `world_id`, nodes sorted by `ref`. This covers `kind_ref`, `function_ref`, `setting_ref`, `world_id`, and `mapping_target`.
2. **Node order** (`slots.py:88`): `add("whole", "whole", [], [node_alias[ref] for ref in inv["whole_refs"]])` — the symbol list is
   driven by `inv["whole_refs"]`, which is `_nodes(world)` in the packet's own node order (`answers.py:74-75`, `143`). No sorting.

**Measured reality (important, and it contradicts the way DG6 phrases it):** for the frozen bank, packet node order and alias order
produce the **same list**. `source._facts()` sorts labels (`source.py:207` `"labels": sorted(labels)`), `_world()` assigns
`node_refs = {label: world_id + "/n%d" % index for index, label in enumerate(material["labels"])}` (`source.py:214`) and emits
nodes in that same order (`source.py:219`); `_validate_world` re-derives and compares byte-for-byte (`source.py:253-254`), so the
course builder cannot violate it. Probe B: **0 of 64 bank worlds** have `declared order != sorted(ref) order`, and **0 of 70**
`definition` records have `whole["symbols"] != [alias_of[ref] for ref in declared node order]`.
**Builder rule:** derive `whole` symbols from `inv["whole_refs"]` (or the packet's node order), never from an assumption, but do not
expect a difference today. Record both facts in the pointer tests.

### A.5 `score_decisions`, `assemble_answer`, score bounds

```python
def score_decisions(packet, scores):    # slots.py:283
def assemble_answer(packet, decisions): # slots.py:299
def candidate_scores(packet, scores):   # slots.py:276
def validate_plan(packet, plan):        # slots.py:231
```

`_check_scores(plan, scores)` (`slots.py:243-249`) — the **score bound** is at `slots.py:248`:
```python
require(type(scores) is dict and set(scores) == {slot["slot_id"] for slot in plan["slots"]}, "TYPED_SLOT_SCORE_FIELDS")
for slot in plan["slots"]:
    row = scores[slot["slot_id"]]
    require(type(row) is dict and set(row) == set(slot["symbols"]), "TYPED_SLOT_SCORE_SYMBOLS")
    require(all(type(value) in (int, float) and abs(value) <= MAX_ABS_SCORE and math.isfinite(value)
                for value in row.values()), "TYPED_SLOT_SCORE_SCALAR")
```
So: `scores` must have **exactly** one key per `slot_id`; each row **exactly** the slot's symbol set; each value a non-bool
`int`/`float`, finite, `abs(value) <= 1000000`. `bool` fails `type(value) in (int, float)` because `type(True) is bool`.

`score_decisions` returns `_decision(plan, selected, candidate)` (`slots.py:238-240`):
```python
{"schema": "cas.typed-teaching-slot-decisions/0.1", "record_id": plan["record_id"], "query_id": plan["query_id"],
 "plan_digest": plan["plan_digest"], "selected": selected, "correspondence_candidate_id": candidate}
```
- Non-correspondence: `selected = {slot_id: max(slot["symbols"], key=lambda s: scores[slot_id][s])}` — **argmax over the declared
  symbol order, first wins exact ties** (`slots.py:29`, `slots.py:293-294`); `correspondence_candidate_id` is `None`.
- Correspondence: `selected = {}` and `correspondence_candidate_id` = the winner of `_candidate_scores`
  (`slots.py:295-296`). `_candidate_scores` (`slots.py:259-273`) raises `TYPED_SLOT_CANDIDATE_SCORE_KIND` if the plan is not
  correspondence, normalizes `NO_MATCH` against `logsoftmax(mode)` and each mapping against `logsoftmax` of the sums of the
  selected node logits (the exact formula is the `correspondence` value of `DECISION_CONTRACT`, `slots.py:30`), and can raise
  `TYPED_SLOT_NONFINITE_SCORE_RESULT` (`slots.py:255`, `269`, `272`).

`assemble_answer(packet, decisions)` (`slots.py:299-348`) raise-conditions, in order:
`TYPED_SLOT_DECISION_FIELDS` (exact 6-key dict, `slots.py:304`), `TYPED_SLOT_DECISION_BINDING` (schema/record/query/plan_digest
all equal the freshly compiled plan's, `slots.py:305-307` — note it **recompiles** the plan, so a cached `plan_digest` must still
match), `TYPED_SLOT_SELECTION_TYPE`, then either `TYPED_SLOT_MAPPING_SELECTION` + `TYPED_SLOT_UNKNOWN_CANDIDATE`
(correspondence, `slots.py:311-314`) or `TYPED_SLOT_SELECTION_COVERAGE` + `TYPED_SLOT_SELECTION_SYMBOL` (every other kind,
`slots.py:317-320`). It finishes with `answers.make_answer(...)` (`slots.py:348`), which adds its own
`AnswerContractError` conditions (`answers.py:245-253`).

Real assembled answer for the definition record (from the real prediction file):
```json
{"schema": "cas.typed-teaching-answer/0.1",
 "query_id": "typed-query-f3bcb04aebded63611d72257aa5b74f6b79f9521eddbb52bf65f39cd7d8100da",
 "kind": "definition",
 "value": {"function_ref": "world-1a109d6d943a45a61bb843eb96dece5ed665a1f62372d618d5af1182a6440767/decl/function",
           "kind_ref": "world-edc0fc8d4beea14212e3909cd309786eefd8653b60cd306874a060783780c9ba/decl/kind",
           "whole": "world-7afc0b967564edb89050f99eeb409560cb401de94fda9bd901d97ee16a5be881/n0"}}
```

Correspondence extras: `correspondence_candidates` (`slots.py:110-113`) is `[{"candidate_id": "typed-candidate-" + digest({"query_id":..., "value":...}), "value": value}]`,
where `value` comes from `answers.correspondence_candidates` (`answers.py:285-304`): element 0 is always
`{"status": "NO_MATCH", "pairs": []}`, then one `{"status": "MAPPING", "pairs": [{"source": a, "target": b} for a, b in zip(left, row)]}`
per permutation of the sorted target refs against the sorted source refs. `forced_candidate_count` is `1` only when the list has
exactly one entry (`slots.py:118`). Real measured case: 7 candidates, `forced_candidate_count == 0`.

### A.6 The slot cache (`slots.py:148-228`)

`_SlotCache.__init__(self, *, max_entries=MAX_CACHE_ENTRIES, max_serialized_bytes=MAX_CACHE_SERIALIZED_BYTES)`
raises `TYPED_SLOT_CACHE_ENTRY_BOUND` / `TYPED_SLOT_CACHE_BYTE_BOUND` (`slots.py:156-160`). `compile()` pre-checks the packet tree
with `_packet_bytes` (`slots.py:122-145`): `TYPED_SLOT_CACHE_TREE_BOUND` (≤250 000 nodes, depth ≤32), `TYPED_SLOT_CACHE_JSON_TYPE`
(`dict/list/str/int/bool/None` only — tuples are rejected), `TYPED_SLOT_CACHE_CYCLE`, `TYPED_SLOT_CACHE_JSON_KEY`,
`TYPED_SLOT_CACHE_STRING_BOUND` (8 MiB/str), `TYPED_SLOT_CACHE_PACKET_BOUND` (8 MiB total).
Then `TYPED_SLOT_CACHE_COLLISION` (same key, different bytes, `slots.py:175`) and
`TYPED_SLOT_CACHE_CONTEXT_CHANGED` (the profile changed mid-compile, `slots.py:184-186`). `compile_slots` returns a
`deepcopy`, so a caller cannot mutate the cache. Public counters: `slots.slot_cache_info()` / `slots.clear_slot_cache()`
(`slots.py:223-228`).

---

## B. `cas_meta2/typed_teaching/loss_plan.py` (161 lines)

### B.1 `validate_prediction(packet, prediction)` — the exact required field set (`loss_plan.py:35-55`)

```python
PREDICTION_SCHEMA = "cas.typed-teaching-prediction/0.1"      # loss_plan.py:17
def validate_prediction(packet, prediction):                 # loss_plan.py:35
```

The **exact** required key set is the 12 names at `loss_plan.py:37-38`, and the set equality is enforced
(`loss_plan.py:39`, `TYPED_LOSS_PREDICTION_FIELDS`):

| field | required type / value | source |
|---|---|---|
| `schema` | exactly `"cas.typed-teaching-prediction/0.1"` | `loss_plan.py:39` |
| `prediction_id` | `"typed-prediction-" + digest({k: v for k, v in prediction.items() if k != "prediction_id"})` | `loss_plan.py:53` |
| `record_id` | equals `plan["record_id"]` | `loss_plan.py:47` |
| `packet_digest` | equals `plan["packet_digest"]` | `loss_plan.py:47` |
| `slot_plan_digest` | equals `plan["plan_digest"]` | `loss_plan.py:48` |
| `depth` | `int`, one of `(1, 2, 4, 8)` | `loss_plan.py:41` |
| `model_revision` | `int`, `>= 0` | `loss_plan.py:42` |
| `run_context_digest` | `str`, `re.fullmatch("[0-9a-f]{64}", ...)` | `loss_plan.py:44-45` |
| `encoder_identity_digest` | `str`, `re.fullmatch("[0-9a-f]{64}", ...)` | `loss_plan.py:44-45` |
| `scores` | exactly the slot/symbol shape `slots._check_scores` demands | `loss_plan.py:49` |
| `decisions` | `canonical(prediction["decisions"]) == canonical(slots.score_decisions(packet, scores))` | `loss_plan.py:49-51` |
| `answer` | `canonical(prediction["answer"]) == canonical(slots.assemble_answer(packet, decision))` | `loss_plan.py:50-52` |

Both digests are **64 lowercase hex characters** (`TYPED_LOSS_PREDICTION_IDENTITIES`, `loss_plan.py:45`). They are produced by
`digest(...)` (SHA-256 over canonical JSON, §F), so a builder must pass `learner.run_identity_digest` for
`run_context_digest` and `digest(encoder.identity)` for `encoder_identity_digest` — exactly what `learner.py:161-162` does.
**Note the `depth` set is `{1, 2, 4, 8}` — the only depth constraint found in this module**; there is no other depth rule here
(DG1's "K=8" is a study decision, not enforced by `validate_prediction`).

There is a second, stricter entry point: `_sealed(packet, raw, expected_sha256)` (`loss_plan.py:58-67`) requires the bytes be
non-empty, ≤2 MiB, hash-matched (`TYPED_LOSS_SEAL_BYTES`), valid UTF-8 JSON (`TYPED_LOSS_SEAL_JSON`) and **byte-identical to
`canonical(prediction) + "\n"`** (`TYPED_LOSS_SEAL_NONCANONICAL`, `loss_plan.py:66`). That is the exact form the worker writes as a
batch seal (`learner.py:191`).

**Complete minimal valid example dict** (shape taken from a real sealed prediction in
`records/typed_practice_001/receipt_20260917/checkpoints/course_p00_predictions.json`, trimmed to a 3-symbol `whole` slot):

```python
prediction = {
    "schema": "cas.typed-teaching-prediction/0.1",
    "prediction_id": "typed-prediction-b4caa5194193eef4f8f7e47811cb79f66da7f4d594e77327f6e97526bf889e1b",
    "record_id": "typed-input-0245afcca3fe65f5586f723362e44815baab6c982272dc3f1a60487e8da1e53b",
    "packet_digest": "8e1f4ef229d993e909598b929cd6221a660d8102d7fddb3c30418246b20a76b3",
    "slot_plan_digest": "e849544f2243e93a9c2d7d9059a5b84952a1d504f56e53daf261e57cbf2c7229",
    "depth": 8,
    "model_revision": 0,
    "run_context_digest": "145374ac99e3bc6f0e306ee612e9c7a88b7f4c6d410d0dafff601d72a557afff",
    "encoder_identity_digest": "15d67197fda16cb438c6b6400e78d57ea6963a5909580e1339febeddfcb49fad",
    "scores": {
        "typed-slot-688dbf9d8dad9a1f957967f4d95a4aabae182b13b1926b2d96a6bd4f66953f00":
            {"N0": 0.05617135763168335, "N1": -0.019019706174731255, "N2": -0.0701385885477066},
        # ... one more entry per slot, each with exactly that slot's symbol set
    },
    "decisions": {"schema": "cas.typed-teaching-slot-decisions/0.1",
                  "record_id": "...", "query_id": "...", "plan_digest": "e849544f...",
                  "selected": {"typed-slot-688dbf9d...": "N0", "...": "W4", "...": "W61"},
                  "correspondence_candidate_id": None},
    "answer": {"schema": "cas.typed-teaching-answer/0.1", "query_id": "...", "kind": "definition",
               "value": {"whole": ".../n0", "kind_ref": ".../decl/kind", "function_ref": ".../decl/function"}},
}
```
`validate_prediction` was **run on this real record** during the probes and returned it unchanged (deep copy) — so the example
above is exact-shape, not a paraphrase. Note that a builder cannot reuse this literal: `prediction_id`, the digests and the
`selected` values must be recomputed for the builder's own packet.

### B.2 Other public entry points in this module

- `compile_loss_plan(packet, target_receipt, *, sealed_prediction_bytes, expected_prediction_sha256)` (`loss_plan.py:92`).
  Validates the seal first, **then** imports the private checker (`loss_plan.py:95`, comment at `:94`), then builds the field list.
  Raise codes: `TYPED_LOSS_JOINT_VALID_SET` (`:103`), `TYPED_LOSS_FIELD_SHAPE` (`:112`),
  `TYPED_LOSS_CORRELATED_MEMBERSHIP_TARGETS_UNSUPPORTED` (`:115`), `TYPED_LOSS_FIELD_UNSUPPORTED` (`:86`, a plain `ValueError`),
  `TYPED_LOSS_TARGET_SYMBOL` (`:87`). Returns a plan whose keys are listed at `loss_plan.py:121-128`
  (`schema`, `record_id`, `query_id`, `packet_digest`, `slot_plan_digest`, `prediction_id`, `prediction_sha256`, `target_digest`,
  `checker_profile_digest`, `admissible_answer_count`, `fields`, `policy`, `profile`, `forced_fields`, `authority`,
  `loss_plan_digest`). Each entry in `fields` has keys
  `field`, `kind` (`"joint_correspondence"` | `"membership"` | `"categorical"`), `slot_ids`, `valid_candidate_ids`, `targets`,
  `public_alphabet_size`.
- `validate_loss_plan(packet, target_receipt, plan, *, sealed_prediction_bytes, expected_prediction_sha256)` (`loss_plan.py:131`) —
  raises `TYPED_LOSS_PLAN_RECONSTRUCTION`.
- `scalar_report(packet, plan, scores)` (`loss_plan.py:139`) — pure-Python audit; raises `TYPED_LOSS_REPORT_PLAN_BINDING`,
  `TYPED_LOSS_NONFINITE_REPORT`. Returns `{"fields": [...], "raw_task_loss", "normalized_task_loss", "training_uses": "raw_task_loss",
  "numeric_model_executed": False}`. **This is the function `train_sealed_batch` compares its tensor loss against, tolerance
  `rel_tol=2e-5, abs_tol=2e-5` (`learner.py:261`).**
- `profile()` (`loss_plan.py:27-32`) — hashes **only `loss_plan.py`** (`loss_plan.py:28`) plus `slots.profile()`; keys
  `schema`, `policy`, `source_sha256`, `slots_profile`, `status`, `profile_digest`.

---

## C. `cas_meta2/typed_teaching/learner.py` (364 lines)

### C.1 `TypedCourseLearner.__init__` — exact scope/shape/limit checks (`learner.py:73-118`)

```python
def __init__(self, torch, framework, encoder, *, optimizer_config, run_context, limits, device):   # learner.py:73
```

Module constants (`learner.py:25-26`):
```python
PARAMETERS = ("left.weight", "merge.weight", "right.weight")
PARAMETER_SHAPES = {"left.weight": (64, 64), "right.weight": (64, 64), "merge.weight": (64, 128)}
```

In order:

| line | condition | error code |
|---|---|---|
| 77 | `re.fullmatch(r"cuda(?::[0-9]+)?", str(device))` and `torch.cuda.is_available()` | `TYPED_LEARNER_CUDA_REQUIRED` |
| 82-83 | `self.scope == {"allowed": list(PARAMETERS), "frozen": [], "contract_id": "cas.cjt.operation.^6.decompose/0.2", "role": "operation:^6"}` where `self.scope = scope_parameters(framework, self.module)` (line 81) | `TYPED_LEARNER_REGISTERED_SCOPE` |
| 85-86 | `set(named_parameters()) == set(PARAMETERS)` **and** every one matches `PARAMETER_SHAPES[name]`, `p.device == self.device`, `p.dtype == torch.float32`, `p.requires_grad` | `TYPED_LEARNER_PARAMETER_SHAPE` |
| 87 | `set(optimizer_config) == {"learning_rate", "weight_decay", "betas", "eps"}` | `TYPED_OPTIMIZER_FIELDS` |
| 88 | `type(betas) is list and len(betas) == 2` | `TYPED_OPTIMIZER_BETAS` |
| 90-92 | all finite; `0 < lr <= 1`; `0 <= wd <= 1`; `0 < eps <= 1`; `0 <= beta < 1` each | `TYPED_OPTIMIZER_RANGE` |
| 93-96 | `set(limits) == {"max_updates","max_core_calls","max_wall_seconds"}`; `int` and `0 < max_updates <= 176`; `int` and `0 < max_core_calls <= 1000000`; `int/float` and `0 < max_wall_seconds <= 3600` | `TYPED_LEARNER_LIMITS` |
| 97-101 | `set(run_context) == {"run_id","course_sha256","condition","source_seed"}`; `run_id` matches `[A-Za-z0-9_-]{1,128}`; `course_sha256` matches `[0-9a-f]{64}`; `condition in ("ALT_COMPONENT_WHOLE","MIXED_SAME_ITEMS","ORDINARY_DEPENDENCY_GRAPH")`; `source_seed in (101, 202, 303)` | `TYPED_LEARNER_RUN_CONTEXT` |
| 102 | `encoder.verify_frozen()` (its own codes, §E) | — |
| 103-105 | `tuple(encoder.readout_rows.shape) == (90, 64)`, right device/dtype, `not requires_grad`, and `encoder.symbol_to_index == {s: i for i, s in enumerate(slots.SYMBOLS)}` | `TYPED_LEARNER_READOUT` |

The **176 updates / 3 600 s ceilings live here** and are the reason the practice study needed a subclass
(`practice_learner.py:22-24, 51-53`: it clips to the registered ceilings, calls `super().__init__`, then re-installs the practice
limits `2048 / 14 400` and re-derives `run_identity_digest`).

Constructed state (`learner.py:79-118`): `self.torch`, `self.framework`, `self.module = framework.module`, `self.encoder`,
`self.device = torch.device("cuda", torch.cuda.current_device())` when `str(device) == "cuda"`, `self.scope`,
`self.optimizer_config`, `self.limits`, `self.optimizer = torch.optim.AdamW([parameters[name] for name in PARAMETERS], ...,
foreach=False, fused=False, capturable=False)` (`learner.py:107-109` — **only the three `PARAMETERS`, in that order**),
`self.run_identity`, `self.run_identity_digest`, `self.cursor = self.model_revision = 0`, `self.counters`,
`self._pending = None`, `self.failed = False`, `self._started`, `self._elapsed_before`.

`self.run_identity` keys (`learner.py:110-112`): `context`, `learner_profile`, `encoder_identity`,
`initial_model_identity`, `scope`, `optimizer_config`, `limits`.
`self.run_identity_digest = digest(self.run_identity)` (`learner.py:113`).
`self.counters` keys (`learner.py:115-116`): `core_forward_attempts`, `core_forward_calls`, `sample_core_passes`,
`slot_forwards`, `prediction_calls`, `staged_batches`, `backward_attempts`, `backward_calls`, `optimizer_step_attempts`,
`optimizer_updates`, `private_loss_plan_calls` — all `int`, all zero-initialised.

### C.2 `_tensor_loss` — exact signature and every `self.*` it touches (`learner.py:197-235`)

```python
def _tensor_loss(self, plan, loss, tensors):    # learner.py:197
```
It is a plain method with **no `@staticmethod`/`@classmethod`**, and it never touches `self.module`, `self.encoder`,
`self.optimizer`, `self.counters`, `self.limits`, `self.device`, `self.scope` or `self._pending`. The complete list of `self.*`
attributes it reads:

- `self.torch` (`learner.py:198` `torch = self.torch`, then `torch.log_softmax` `:203`, `torch.stack` `:216-217`, `torch.cat` `:218`,
  `torch.logsumexp` `:218/220/226`, `torch.isfinite` `:228`) — **the only attribute.**

Its arguments: `plan` is a slot plan from `slots.compile_slots`; `loss` is a loss plan from `loss_plan.compile_loss_plan`;
`tensors` is `{slot_id: logits_tensor}` in `slot["symbols"]` order (built at `learner.py:155`).
Returns a 2-tuple `(task_tensor, report)` where the report keys are
`fields` (list of `{"field","raw_loss","normalized_loss","public_alphabet_size","slot_count","forced"}`), `raw_task_loss`,
`normalized_task_loss` (`learner.py:230-235`). Raise code: `TYPED_LEARNER_LOSS_DETACHED_OR_NONFINITE` (`learner.py:228`).

**Answer to the builder's question: yes.** A new class can call
`TypedCourseLearner._tensor_loss(self, plan, loss, tensors)` — or simply `self._tensor_loss(...)` from any subclass — with only
`self.torch` present. Everything else it needs comes from its arguments. `plan["slots"]`, `plan["aliases"]` and
`plan["correspondence_candidates"]` must exist (they do, for any plan produced by `slots.compile_slots`).

### C.3 The other methods — signatures, returns, raise codes

**`predict(self, packet, depth)` → prediction dict** (`learner.py:167-172`). Requires `self._pending is None`
(`TYPED_LEARNER_PENDING_BATCH`, `:169`), sets `self.module.eval()`, runs `self._forward` under `torch.no_grad()` and returns only
the prediction dict. `_forward(self, packet, depth)` (`learner.py:125-165`) returns `(prediction, plan, tensors)` and is where the
forward internals live; its raise codes: `TYPED_LEARNER_FAILED_OR_WALL_BUDGET` (`:123`), `TYPED_LEARNER_DEPTH` (`:128`, depth must
be `int` in `(1,2,4,8)`), `TYPED_LEARNER_FORWARD_BUDGET` (`:130`), `TYPED_LEARNER_DETACHED_RECURRENCE` (`:134`, raised when any
value fed to `rms` is not a tensor), `TYPED_LEARNER_CORE_OUTPUT` (`:143`, must be shape `(64,)` and finite),
`TYPED_LEARNER_ENCODED_SLOT` (`:148`, `(64,)`, right device/dtype, no grad, finite), `TYPED_LEARNER_LOGITS_NONFINITE` (`:154`).

**`stage_batch(self, packets, depth, *, cursor, occurrence_ids)` → `{"public": dict, "bytes": bytes, "sha256": str}`**
(`learner.py:174-195`). Raise codes: `TYPED_LEARNER_BATCH_CURSOR_OR_BUDGET` (`:178`: `_pending is None`, `type(cursor) is int`,
`cursor == self.cursor`, `optimizer_updates < max_updates`), `TYPED_LEARNER_BATCH_SHAPE` (`:181`: `packets` a list of 1..8, ids a
list of the same length, unique, each matching `typed-occurrence-[0-9a-f]{64}`). It **zeroes gradients with
`set_to_none=True`** at `learner.py:185` before each forward. `"bytes"` is `(canonical(public) + "\n").encode()` (`:191`).

**`train_sealed_batch(self, path, *, expected_sha256, target_receipts)` → update dict** (`learner.py:237-292`). Raise codes:
`TYPED_LEARNER_NO_PENDING_BATCH` (`:240`), `TYPED_LEARNER_SEAL_PATH` (`:242`), `TYPED_LEARNER_SEAL_MISMATCH` (`:245`, hash **and**
byte equality with the retained `raw`), `TYPED_LEARNER_MODEL_CHANGED_AFTER_PREDICTION` (`:246`), `TYPED_LEARNER_TARGET_COUNT`
(`:250`), then `_tensor_loss`'s own code, then the scalar/tensor agreement `TYPED_LEARNER_SCALAR_TENSOR_LOSS_MISMATCH` (`:261`,
`rel_tol=abs_tol=2e-5`), then **`TYPED_LEARNER_GRADIENTS` at `learner.py:271`** — `all(p.grad is not None and finite for p in
module.named_parameters())` — then `TYPED_LEARNER_GRADIENT_NORM_NONFINITE` (`:273`), then
`TYPED_LEARNER_PARAMETERS_NONFINITE` (`:278`). On **any** exception it sets `self.failed = True`, clears `self._pending` and
re-raises (`learner.py:289-292`). On success it increments `self.cursor` and `self.model_revision` (`:280`) and returns
(`learner.py:281-286`):
```python
{"schema": "cas.typed-teaching-update/0.1", "batch_id": <public batch_id>, "public_seal_sha256": expected_sha256,
 "cursor_committed": self.cursor, "model_revision": self.model_revision, "tasks": reports,
 "raw_batch_loss": ..., "normalized_batch_loss": ..., "training_uses": "raw_batch_loss",
 "gradient_squared_norm": gradient_squared, "loss_plan_digests": loss_ids, "counters": deepcopy(self.counters)}
```
`STATUS: WORKER_ONLY` — `TYPED_LEARNER_GRADIENTS` is RK1 and is the single most likely run-killer for a multi-head container.

**`export_checkpoint(self, path)` → receipt dict** (`learner.py:294-316`). Requires `_pending is None and not failed`
(`TYPED_CHECKPOINT_UNCOMMITTED_OR_FAILED`, `:295`), parent dir exists (`TYPED_CHECKPOINT_PARENT`, `:311`), and writes with
`destination.open("xb")` (`:312` — **create-only**: a second export to the same path raises `FileExistsError`). Returns
(`learner.py:315-316`):
```python
{"path": str(destination.resolve()), "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
 "run_identity_digest": self.run_identity_digest, "metadata": metadata}
```
The `.pt` payload is `{"schema": CHECKPOINT_SCHEMA, "metadata", "model_state", "optimizer_state", "encoder_state", "rng_state"}`
(`learner.py:308-309`), and `metadata` has exactly 11 keys (`learner.py:303-307`): `run_identity`, `run_identity_digest`,
`model_revision`, `cursor`, `counters`, `elapsed_seconds`, `training_mode`, `model_state_identity`, `optimizer_state_identity`,
`encoder_state_identity`, `rng_state_identity`. `model_state` is `_cpu(torch, dict(self.module.state_dict()))` (`learner.py:298`)
— **only `self.module`**, which is why a container must be `self.module` itself.

**`restore_checkpoint(cls, torch, framework, *, path, expected_sha256, expected_run_identity_digest, device)`** — a
`@classmethod` (`learner.py:318-364`). Raise codes in order: `TYPED_LEARNER_CUDA_REQUIRED` (`:322`), `TYPED_CHECKPOINT_FILE_BOUND`
(`:324`, existing regular non-symlink file, `0 < size <= 256 MiB`), `TYPED_CHECKPOINT_SHA` (`:326`), `TYPED_CHECKPOINT_FIELDS`
(`:329-330`), `TYPED_CHECKPOINT_METADATA` (`:332-333`), `TYPED_CHECKPOINT_RUN_IDENTITY` (`:335-336`),
`TYPED_CHECKPOINT_STATE_DIGEST:<field>` for `field in ("model","optimizer","encoder","rng")` (`:337-338`),
then the encoder restore and `framework.module.load_state_dict(payload["model_state"], strict=True)` (`:341`), then
`TYPED_CHECKPOINT_RESTORED_VALUES` (`:344-345`), `TYPED_CHECKPOINT_CURSOR` (`:346-347`), `TYPED_CHECKPOINT_COUNTERS` (`:348-350`),
`TYPED_CHECKPOINT_RUNTIME_METADATA` (`:351-353`), `TYPED_CHECKPOINT_RNG_FIELDS` (`:359`), `TYPED_CHECKPOINT_RNG_VALUES` (`:362`).
Also `torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)` (`:328`).

**Exactly which recorded values must equal today's values:**

1. `digest(identity) == metadata["run_identity_digest"] == expected_run_identity_digest` (`learner.py:335`), where
   `identity = metadata["run_identity"]`.
2. **`canonical(identity["learner_profile"]) == canonical(profile())`** — the **module-level** `profile()`, not a method and not a
   subclass override (`learner.py:336`). This is the whole of the "profile list" requirement, and it is the reason
   `records/typed_practice_001/...` restores fail on any byte change to the **six** files at `learner.py:30-34` **plus**
   `slots.profile()`'s chain: `learner.py`, `loss_plan.py`, `recurrent_cjt/recurrence.py`, `graph_teaching/trainer.py`,
   `graph_teaching/real_framework.py`, `teaching_cycle/gpu_adapter.py`, and — transitively through `slots.profile()` —
   `slots.py` and `course.profile()`'s **15 files** (§A.2).
3. **The encoder identity list:** `restore_frozen_typed_encoder(torch, payload["encoder_state"], expected_identity=identity["encoder_identity"], device=device)`
   (`learner.py:339-340`), which re-derives `encoder.expected_identity(tokenizer, seed, d_model)` from today's code and requires
   `canonical(payload["identity"]) == canonical(wanted)` (`encoder.py:257-258`, codes `TYPED_ENCODER_STATE_FIELDS` /
   `TYPED_ENCODER_STATE_IDENTITY`) and byte-exact rows (`TYPED_ENCODER_ACTUAL_ROW_BYTES`, `encoder.py:88-89`). So the today-values
   that must match are: the full `expected_identity` object (which contains `profile` → `binding.profile()` → every file hash in
   §E.4, plus the tokenizer's file hashes), the tokenizer's exact `digest`, and the exact float32 projection/readout bytes.
4. `identity["optimizer_config"]`, `identity["context"]`, `identity["limits"]` are fed straight into `cls(...)` (`learner.py:342`),
   so an old checkpoint is only ever restored through the **registered** ceilings check — the practice subclass then re-checks its
   own (`practice_learner.py:62-67`, `PRACTICE_CHECKPOINT_PROFILE`).

Measured today (probe B): `canonical(run_identity["learner_profile"]) == canonical(learner.profile())` is `True`, and
`digest(run_identity) == run_identity_digest` is `True` for
`records/typed_practice_001/receipt_20260917/checkpoints/initial_checkpoint.json`.

**RNG overwrite behaviour near line 360** (`learner.py:358-362`):
```python
rng = payload["rng_state"]
require(type(rng) is dict and set(rng) == {"torch_cpu", "torch_cuda", "python"}, "TYPED_CHECKPOINT_RNG_FIELDS")   # :359
torch.set_rng_state(rng["torch_cpu"]); torch.cuda.set_rng_state_all(rng["torch_cuda"]); random.setstate(rng["python"])  # :360
current_rng = {"torch_cpu": torch.get_rng_state(), "torch_cuda": torch.cuda.get_rng_state_all(), "python": random.getstate()}  # :361
require(state_identity(torch, current_rng) == metadata["rng_state_identity"], "TYPED_CHECKPOINT_RNG_VALUES")   # :362
```
Restoring **overwrites all three global RNG streams** (torch CPU, all CUDA devices, Python `random`) and then verifies the overwrite
by re-reading them. Nothing saves the previous state. Combined with `matched._framework`'s own `torch.manual_seed` /
`torch.cuda.manual_seed_all` / `random.seed` (`cncm/typed_matched_worker.py:44-46`), **phase A of the pointer worker must finish
before the pointer model is seeded** (DG4/M3). Also note the restored object becomes `training_mode` from the file
(`learner.py:357`) and `_elapsed_before = metadata["elapsed_seconds"]` (`:356`).

**`profile()`** (`learner.py:29-44`) and **`state_identity(torch, value)`** (`learner.py:47-61`):
```python
def profile():                              # learner.py:29
def state_identity(torch, value):           # learner.py:47  -> 64-hex string via digest(walk(value))
```
`profile()` hashes the six files at `learner.py:30-34` (paths relative to `Path(__file__).parents[2]`, i.e. to
`research/CAS_META_2_COMPOSITION/`, formatted `.as_posix()`) plus `slots.profile()` (`:38`); other keys: `schema`,
`core_width` (64), `readout_rows` (90), `recurrence`, `readout`, `training_loss`, `identity_boundary`, `status`, `profile_digest`.
`state_identity` walks tensors (`TYPED_STATE_SPARSE`, `TYPED_STATE_KEY`, `TYPED_STATE_SCALAR`) into
`{"type": "tensor", "dtype": str(node.dtype), "shape": list(node.shape), "sha256": sha256(raw).hexdigest()}` — **device is
ignored** (`.cpu()` at `:52`), dtype and shape are part of the digest.

### C.4 Attributes the worker reads off a learner instance

Observed in the practice/matched workers (`cncm/typed_matched_worker.py`, `cncm/typed_practice_worker.py`,
`cncm/typed_course_worker.py`) — the full list a new `PointerCourseLearner` must expose with the same meanings:

| attribute | type | who reads it |
|---|---|---|
| `torch` | the module object passed in | `base._state` (`typed_course_worker.py:207`), `_rng` (`:201`) |
| `module` | `nn.Module`; **the one container holding every learned weight** (`framework.module` today) | `base._state` (`:207`), `learner.export_checkpoint` (`:298`) |
| `encoder` | the frozen typed encoder object (§E) | `base._state` (`:210`), `_state`→`export_state()`, `_check_state` (`:213-216`) |
| `optimizer` | `torch.optim.AdamW` | `base._state` (`:208`), restore (`:343`) |
| `counters` | `dict[str, int]`, 11 keys (§C.1) | `counter_delta` (`:55-59`), `_evaluate` (`:139`, `:157`) |
| `cursor` | `int` | `_stage_and_train` (`typed_practice_worker.py:110`), update records |
| `model_revision` | `int` | prediction dicts (`learner.py:161`), `_sum_deltas` |
| `failed` | `bool` | `export_checkpoint` gate (`learner.py:295`) |
| `run_identity_digest` | 64-hex `str` | `stage_batch` public body (`learner.py:188`), predictions (`:162`) |
| `limits` | `dict` with `max_updates`, `max_core_calls`, `max_wall_seconds` | `_budget` (`:123`), restore checks |
| `device`, `scope`, `framework` | as constructed | `learner.__init__`, `scope_parameters` |
| `_pending`, `_elapsed_before`, `_started` | internal but read by `restore_checkpoint` (`:355-356`) | restore |

`base._state(torch, learner)` (`cncm/typed_course_worker.py:205-210`) returns exactly
`{"model_state_identity", "optimizer_state_identity", "rng_state_identity", "encoder_state_identity"}`, and `base._check_state`
(`:213-216`) requires all four to equal `checkpoint["metadata"][k]` else `RESTORED_STATE_MISMATCH`. A pointer learner therefore
**must** keep a frozen typed encoder alive on `self.encoder` even if it never encodes a packet — the handoff says exactly this
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:255-256`).

### C.5 `scope_parameters` in `graph_teaching/trainer.py` — what it freezes (`trainer.py:79-91`)

```python
def scope_parameters(framework, model):     # trainer.py:79
    _registration, contract = select_target(framework)                     # :81
    allowed = set(framework.resolve_plasticity_groups(model, TARGET_PLASTICITY_ROLE, contract))   # :82-83
    require(allowed, "PLASTICITY_ALLOWLIST_EMPTY")                         # :84
    names = []
    for name, parameter in model.named_parameters():                       # :86
        parameter.requires_grad_(name in allowed)                          # :87
        names.append(name)
    frozen = [name for name in names if name not in allowed]               # :89
    return {"allowed": sorted(allowed), "frozen": sorted(frozen),
            "contract_id": TARGET_CONTRACT_ID, "role": TARGET_PLASTICITY_ROLE}
```
It sets `requires_grad_(False)` on **every** parameter whose name is not in the resolved allowlist. For a real framework,
`GraphTrainingFramework.resolve_plasticity_groups` returns **all** of the module's parameter names
(`real_framework.py:45-49`, requiring `role == TARGET_PLASTICITY_ROLE` else `PLASTICITY_ROLE_OUTSIDE_RUN_SCOPE`), so calling it on
a container that holds non-^6 heads **freezes every head**. Never call it on the pointer container (RK2).
`select_target` (`trainer.py:68-76`) raises `TARGET_CONTRACT_NOT_UNIQUE` / `TARGET_PLASTICITY_ROLE_NOT_ADMITTED`.

---

## D. The registered ^6 block and framework

### D.1 `matched._framework(torch, device, seed)` — and the correction to the draft

The function is `_framework(torch, device, seed)` in **`cncm/typed_matched_worker.py:43-48`** (the worker, not the contract module;
`typed_practice_worker.py:285,404,425` call it as `matched._framework(...)`):

```python
def _framework(torch, device, seed):        # cncm/typed_matched_worker.py:43
    torch.manual_seed(seed)                 # :44
    torch.cuda.manual_seed_all(seed)        # :45
    random.seed(seed)                       # :46
    from cas_meta2.graph_teaching.real_framework import build_graph_training_framework
    return build_graph_training_framework(torch, device, seed=seed, encoder={"d_model": 64})   # :47-48
```
`typed_course_worker._fresh_framework` is the same three seeds then the same call (`cncm/typed_course_worker.py:191-197`,
with the comment at `:192`: *"The inherited builder's seed argument does not initialize torch's RNG."*).

**Returned object type:** `cas_meta2.graph_teaching.real_framework.GraphTrainingFramework`
(`real_framework.py:32-56`), a `@dataclass` with fields `torch`, `device`, `module`, `contract`, `operation_registrations`,
`encoder`, and methods `contract_for(contract_id)`, `resolve_plasticity_groups(model, role, contract)`,
`tensor_bytes(parameter)`, `build_decompose_model(seed)`.

**How the ^6 weights are drawn — CONFIRMED, with the mechanism spelled out.** `build_graph_training_framework`
(`real_framework.py:59-83`) does not re-seed; it relies on the caller's seeding and then:
- `config = CASformerConfig(d_model=encoder["d_model"], num_heads=2, num_relations=4, num_layers=1, dropout=0.0, attention_dropout=0.0, initial_cutoff=0.01, initial_saturation=100.0)` (`real_framework.py:73-76`),
- `bank = RegisteredOperationBank(config)` (`:77`),
- `module = bank.modules_by_operation[DECOMPOSE]` (`:78`), `module.to(device)` (`:79`).

`RegisteredOperationBank.__init__` builds its `nn.ModuleDict` **in this exact order** (`cas_cjt/neural.py:181-188`):
`DECOMPOSE` → `ATTRACT` → `AVERT` → `TRIGGER`. So `_DecomposeTransform(config)` is constructed **first**, and every weight it
creates is drawn from the freshly seeded global RNG before any other operation module exists. `DECOMPOSE = "^6"`
(`neural.py:29`), and `_linear` returns `nn.Linear(..., bias=False)` because `linear_weight_mode` defaults to `"standard"`
(`neural.py:104-112`; `CASformerConfig.linear_weight_mode: str = "standard"`, `research/CASFORMER_v0_1/casformer/core.py:338`).
`registered_learner_bank` also requires `num_relations >= len(OPERATION_REGISTRATIONS)` (4) and re-checks the built-in identities
(`neural.py:176-199`).

So the draft's statement stands: **for the same seed, the ^6 block starts from exactly the same weights as any other run using
this builder** — the bank draws the ^6 weights first from the RNG seeded at `typed_matched_worker.py:44-46`.

**Getting the two things a builder needs:**

(i) **The ^6 sub-block state dict** is simply the whole of the framework module's state dict, because the module *is* the ^6 block:
```python
framework = matched._framework(torch, device, seed)   # cncm/typed_matched_worker.py:43
sub_block = dict(framework.module.state_dict())       # keys exactly {'left.weight','merge.weight','right.weight'}
```
Verified from a real checkpoint (probe D): `model_state` keys are exactly `['left.weight', 'merge.weight', 'right.weight']` with
shapes `{'left.weight': (64, 64), 'right.weight': (64, 64), 'merge.weight': (64, 128)}` — identical to `learner.PARAMETERS` and
`learner.PARAMETER_SHAPES` (`learner.py:25-26`). A container must therefore load these under the same three parameter names
(apparent from `restore_checkpoint`'s `load_state_dict(..., strict=True)`, `learner.py:341`).

(ii) **`model_state_identity`** is computed as
```python
learner.state_identity(torch, dict(module.state_dict()))     # learner.py:111 and learner.py:306
```
i.e. the 64-hex `digest` of the canonical walk over the state dict, where each tensor becomes
`{"type": "tensor", "dtype": ..., "shape": [...], "sha256": sha256(tensor.detach().contiguous().reshape(-1).view(torch.uint8).cpu().tolist())}`
(`learner.py:47-61`). Getting it from an artifact (probe verified on the 20260917 `initial_checkpoint.json`):
```python
pin = json.loads(Path("records/typed_practice_001/receipt_20260917/checkpoints/initial_checkpoint.json").read_bytes())
pin["metadata"]["model_state_identity"]     # '82d2037ca88593233f1176913b91f54d419ebacd23f5abc4e12bd71795feb794'
pin["metadata"]["run_identity"]["initial_model_identity"]   # identical value
```
`model_state_identity` and `run_identity["initial_model_identity"]` are equal by construction (`learner.py:111` vs `:306`, same
input, same function); I recomputed both from the real `initial.pt` and both matched (probe D).

**Correction to the draft (DG4a wording).** `pre_design/DESIGN_DRAFT_v0.1.md:143` (and the review at
`DESIGN_REVIEW_PIPELINE_LENS.md:143`) says the *"^6 sub-block identity must equal the matched study's `initial_checkpoint`
`model_state_identity`"*. That is only true if the two runs' **whole modules** hold the same parameter set. Since
`model_state_identity` digests **`framework.module.state_dict()`**, and the new container module holds more than the three ^6
weights, a pointer run's `module.state_dict()` identity will **not** equal the practice study's `model_state_identity`.
The correct in-job check is: build `matched._framework(torch, device, seed)`, digest **only its three ^6 tensors** with
`state_identity(torch, {"left.weight": ..., "right.weight": ..., "merge.weight": ...})` (i.e. a dict with exactly those keys),
and compare against the practice value above; or equivalently load the practice `.pt`'s `model_state` (itself only those three keys)
and compare. Record which of the two forms was used in `measurements.json` — they are not the same number.
The three real practice-start values are (probe B): seed 20260917 `82d2037ca88593233f1176913b91f54d419ebacd23f5abc4e12bd71795feb794`,
20260918 `bc906a0bdd9f0b31e58653bd47ff70dfa2e40b0fbc35f36cc693c97ac3f0d753`,
20260919 `d437bbeb1b13a4fd31f1a158d17485821ba52da4a29f1de7b00d8ccd583598f0` (read fresh from each
`receipt_<seed>/checkpoints/initial_checkpoint.json`).

> **CORRECTED 2026-09-19.** The 20260918 and 20260919 values above are **WRONG** and must not be used. They do not
> appear in `receipt_<seed>/checkpoints/initial_checkpoint.json`. Read from two independent authoritative sources in
> each receipt — `checkpoints/worker_report.json` `initial_model_identity` and
> `checkpoints/initial_checkpoint.json` `metadata.model_state_identity` — which agree with each other exactly:
>
> | Seed | `model_state_identity` of `checkpoints/initial.pt` |
> |---|---|
> | 20260917 | `82d2037ca88593233f1176913b91f54d419ebacd23f5abc4e12bd71795feb794` |
> | 20260918 | `35081019e8b56f0c0c14aa8168262c23dab4c662c385ddcf26edc794a179b706` |
> | 20260919 | `91279389cfc22df46415dd56a26b1285fb3ef1ecd59e3aaccef553564528c12e` |
>
> Only the seed-20260917 value was correct above. The seed-20260919 value is independently confirmed a third way:
> `measurements/framework_probe/FINDINGS.md` recomputed `state_identity` over that checkpoint's own `model_state` and
> got `91279389...12e` back, matching its recorded metadata. The same table, generated straight from the nine
> sidecar files, is `pre_design/contract_pins/checkpoint_pins.json` under `model_state_identity` — **use that file,
> not this paragraph**, and note it lists all nine checkpoints (initial / pass_01 / final per seed), not just the
> starts.

### D.2 `_DecomposeTransform` (`research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py:115-126`)

```python
class _DecomposeTransform(nn.Module):                                   # neural.py:115
    """Two learned views merged into one typed ^6 candidate channel."""

    def __init__(self, config: CASformerConfig) -> None:                # neural.py:118
        super().__init__()
        self.left  = _linear(config, config.d_model, config.d_model)     # neural.py:120
        self.right = _linear(config, config.d_model, config.d_model)     # neural.py:121
        self.merge = _linear(config, 2 * config.d_model, config.d_model) # neural.py:122

    def forward(self, value: Tensor) -> Tensor:                         # neural.py:124
        parts = torch.cat((torch.tanh(self.left(value)), torch.tanh(self.right(value))), dim=-1)
        return self.merge(parts)
```
- Parameter **names**: `left`, `right`, `merge` (each an `nn.Linear` **without bias**); the `state_dict()` names are therefore
  `left.weight`, `right.weight`, `merge.weight` (`_linear` at `neural.py:104-112`).
- Parameter **shapes** at `d_model = 64`: `left.weight (64, 64)`, `right.weight (64, 64)`, `merge.weight (64, 128)`.
- **Registered contract id:** `cas.cjt.operation.^6.decompose/0.2` — declared twice: in the registration table
  (`neural.py:78`, under `operation_id=DECOMPOSE`) and as `TARGET_CONTRACT_ID` in `real_framework.py:23`; the builder requires
  `contract.contract_id == TARGET_CONTRACT_ID` (`real_framework.py:70`, else `DECOMPOSE_CONTRACT_ID_CHANGED`) and
  `TARGET_PLASTICITY_ROLE in contract.plasticity_groups` (`:71-72`, else `DECOMPOSE_PLASTICITY_ROLE_NOT_ADMITTED`).
  `TARGET_PLASTICITY_ROLE = "operation:^6"` (`real_framework.py:24`); `make_operation_contract("^6")` sets
  `plasticity_groups=("operation:^6", "bias_update_head")` (`cas_cjt/state.py:154-189`, groups at `:187`).
- `forward` is called on a **2-D** tensor in the learner path: `learner.py:140-141`
  `self.module(torch.stack(list(incoming)).unsqueeze(0))[0]`, then the result is checked to be shape `(64,)` and finite
  (`TYPED_LEARNER_CORE_OUTPUT`, `learner.py:143`). So the block is a drop-in `core` callable for `recurrence.run_passes`.

### D.3 `recurrent_cjt/recurrence.py` — `run_passes` and the `rms` / `cast` / `zeros` helpers

```python
def rms(values):                                                         # recurrence.py:96
def feedback(state, encoded, *, lambda_=LAMBDA, epsilon=EPSILON, rms_fn=rms, cast=float)   # recurrence.py:105
def reinjected(encoded, state, *, lambda_=LAMBDA, epsilon=EPSILON, rms_fn=rms, cast=float) # recurrence.py:126
def run_passes(encoded, core, *, depth, state=None, accounting=None,
               lambda_=LAMBDA, epsilon=EPSILON, rms_fn=rms, cast=float,
               zeros=None, reset_each_pass=False)                        # recurrence.py:182
```
Module constants: `DEPTHS = (1, 2, 4, 8)`, `PRIMARY_DEPTH = 8`, `LAMBDA = 0.5`, `EPSILON = 1e-6` (`recurrence.py:47-53`).

`run_passes` semantics (`recurrence.py:196-215`):
```python
require(depth in DEPTHS, "DEPTH_NOT_DECLARED:" + str(depth))             # :197
width = len(encoded)                                                     # :198
allocate = zeros or (lambda count: [0.0] * count)                        # :199
shortcut = depth == 1 and state is None                                  # :204
current = list(allocate(width)) if state is None else list(state)        # :205
require(len(current) == width, "STATE_WIDTH_MISMATCH")                   # :206
for _ in range(depth):                                                   # :207
    incoming = (list(encoded) if (reset_each_pass or shortcut)
                else reinjected(encoded, current, lambda_=lambda_, epsilon=epsilon,
                                rms_fn=rms_fn, cast=cast))               # :208-210
    current = list(core(incoming))                                       # :211
    require(len(current) == width, "CORE_WIDTH_CHANGED")                 # :212
if accounting is not None: accounting.charge(depth=depth, samples=1)     # :213-214
return current                                                           # :215
```
`reinjected` = `[cast(base) + extra for base, extra in zip(encoded, carried)]` (`:131`), and `feedback` =
`[scale * cast(value) for value in state]` with `scale = lambda_ * input_rms / (input_rms**2 + state_rms**2 + epsilon**2)**0.5`
(`:118-123`; `FEEDBACK_SHAPE_MISMATCH` if `len(state) != len(encoded)`).

**Reproducing the old forward bit-for-bit (M4).** The old forward passes to `run_passes` (`learner.py:149-150`):
```python
final = recurrence.run_passes(encoded, core, depth=depth, state=None, rms_fn=rms, cast=lambda x: x,
    zeros=lambda count: torch.zeros(count, dtype=encoded.dtype, device=encoded.device))
```
where `rms` is the **tensor** rms defined locally at `learner.py:133-136`:
```python
def rms(values):
    require(all(torch.is_tensor(v) for v in values), "TYPED_LEARNER_DETACHED_RECURRENCE")
    vector = torch.stack(list(values))
    return torch.sqrt(torch.mean(vector * vector))
```
and `core(incoming)` (`learner.py:137-144`) is
```python
result = self.module(torch.stack(list(incoming)).unsqueeze(0))[0]
```
plus counter bookkeeping. A new class can import `recurrent_cjt.recurrence` and pass its own `rms_fn`, `cast` and `zeros` with the
same bodies; the module default `rms` (`recurrence.py:96-102`, plain floats) and default `cast=float` are the **reference** path and
must not be used in a torch path (the docstring at `recurrence.py:113-117` explains that `float()` detaches).
`select_best_depth(*_args, **_kwargs)` always raises `DEPTH_SELECTION_BY_CHECKER_IS_NOT_A_SUPPORTED_PATH` (`recurrence.py:218-225`).

---

## E. `encoder.py` and `tokenization.py`

### E.1 `export_state()` on the frozen encoder (`encoder.py:228-232`)

```python
def export_state(self):                     # encoder.py:228
    self.verify_frozen()
    return {"schema": STATE_SCHEMA, "identity": self.identity, "tokenizer": frozen_tokenizer.to_dict(),
            "projection": projection.detach().to(device="cpu").clone(),
            "readout": readout.detach().to(device="cpu").clone()}
```
`STATE_SCHEMA = "cas.typed-teaching-frozen-encoder-state/0.1"` (`encoder.py:22`). Exact keys:
`schema`, `identity`, `tokenizer`, `projection` (tensor `(3829, 64)` float32 on CPU), `readout` (tensor `(90, 64)` float32 on CPU).
`identity` is the same object as `encoder.identity` (`encoder.py:176-178`, a `deepcopy` of the frozen identity); the other public
properties are `readout_rows` (`:179-182`, triggers `fast_guard()`) and `symbol_to_index` (`:183-185`).

**For a token cache**, the projection rows a builder needs are `encoder.export_state()["projection"]` — but note the cheaper and
already-public route used by the old forward: `encoder.readout_rows` and, per slot,
`self.encoder.encode_slot(packet, plan, slot)` (`learner.py:146`; body `encoder.py:189-215`). The projection column count equals
`len(tokenizer.vocabulary)` = **3829** today, and a single token's row is
`binding.row_bytes(["token", token], seed=seed, d_model=64)` (`binding.py:198-208`) = 64 float32 values, each exactly `+1/8` or
`-1/8` (`binding.py:202`, `binding.py:68`). `restore_frozen_typed_encoder(torch, payload, *, expected_identity, device)` is the
inverse (`encoder.py:248-264`, codes `TYPED_ENCODER_STATE_FIELDS`, `TYPED_ENCODER_STATE_IDENTITY`, plus `_check_tensor`'s codes).
`build_frozen_typed_encoder(torch, tokenizer, *, seed, d_model=64, device)` is the fresh-construction path (`encoder.py:236-245`).
Encoded vectors are unit L2 with zero/nonfinite rejected: `TYPED_ENCODER_ZERO_OR_NONFINITE_NORM` (`encoder.py:113-116`).

### E.2 `FrameTokenizer.encode_text` — signature, why it is slow, and the correct fix

```python
def encode_text(self, text):                # tokenization.py:148
    """Return text IDs only; no truncation and no unknown replacement."""
    _text(text)                                                                        # :150
    lookup = {_unword(t): i for i, t in enumerate(self.vocabulary[WORD_START:], WORD_START)}   # :151  <-- SLOW LINE
    result = []
    for match in _UNIT.finditer(text):                                                 # :153
        unit = match.group()
        remaining = self.max_tokens - len(result) - 2
        if unit in lookup:
            _require(remaining >= 1, "TYPED_TOKEN_OVERFLOW_NO_TRUNCATION")             # :157
            result.append(lookup[unit])
        else:
            _require(len(unit) <= remaining, "TYPED_TOKEN_OVERFLOW_NO_TRUNCATION")     # :162
            encoded = _text(unit)
            _require(len(encoded) <= remaining, "TYPED_TOKEN_OVERFLOW_NO_TRUNCATION")  # :164
            result.extend(BYTE_START + b for b in encoded)                             # :165
    return result
```
`FrameTokenizer` is a `@dataclass(frozen=True)` (`tokenization.py:96-101`) with fields `vocabulary: tuple[str, ...]`,
`training_frame_digests: tuple[str, ...]`, `max_tokens: int`, `source_profile: dict`; `digest` is a property
(`tokenization.py:144-146`) = `source.digest(self.to_dict())`.

**Why line 151 is slow:** it rebuilds a **3 571-entry** `dict` on **every call** by running `_unword` (a hex decode + re-encode
round-trip check, `tokenization.py:56-67`) over **every** word token in the vocabulary. Measured in the pipeline review:
**0.0111 s per call** (`DESIGN_REVIEW_PIPELINE_LENS.md:47`), and world-choice slots list 64–65 symbols each
(`DESIGN_REVIEW_PIPELINE_LENS.md:48`). Facts measured today (probe C):
`len(vocabulary) == 3829`, `WORD_START == 258`, `FIXED` length `258` = `("[FRAME]", "[END]") + 256 byte tokens`
(`tokenization.py:23-25`), so the word tokens number `3829 - 258 = 3571`, and the reusable lookup has 3571 entries.

**The correct way to build the lookup once** (semantics identical to line 151):
```python
from cas_meta2.typed_teaching import tokenization
WORD_START = tokenization.WORD_START               # 258
_LU = {tokenization._unword(t): i for i, t in enumerate(tokenizer.vocabulary[WORD_START:], WORD_START)}
# then per text: [ _LU[u] if u in _LU else ... ] over tokenization._UNIT.finditer(text)
```
For the pointer machine the cheaper path is to avoid `encode_text` entirely for fixed strings: tokenize each of the 230 distinct
labels / 244 nodes and each declaration text **once**, pin the digest of that cache, and reuse it (RK3 resolution,
`DESIGN_REVIEW_PIPELINE_LENS.md:50`). Note `_WORD`/`_UNIT` are private (`tokenization._unword`, `tokenization._UNIT`) but unused
by any test-only contract; if you prefer not to reach for privates, re-implement the identical decode:
`bytes.fromhex(token[6:-1]).decode("utf-8")` with the `token.startswith("[UNIT:")` guard.
`encode_frame(self, frame)` (`tokenization.py:196-201`) wraps `[START, *ids, END]` and returns
`{"schema": SEQUENCE_SCHEMA, "frame_digest", "tokenizer_digest", "ids", "sequence_digest"}`;
`decode_text(self, ids)` (`:168-194`) is the inverse; `fit_train(frames, *, max_tokens)` (`:216-234`) builds a tokenizer.

### E.3 The exact encoder identity digest, and which files it covers

```python
def expected_identity(tokenizer, *, seed, d_model=64):     # encoder.py:49
    binding.validate_config(seed, d_model)                 # :51  (TYPED_BINDING_SEED / TYPED_BINDING_DIMENSION)
    projection = binding.projection_bytes(tokenizer, seed=seed, d_model=d_model)   # :52
    readout    = binding.readout_bytes(seed=seed, d_model=d_model)                 # :53
    body = {"schema": IDENTITY_SCHEMA, "profile": profile(), "tokenizer_digest": tokenizer.digest,
            "seed": seed, "d_model": d_model,
            "projection": _row_receipt(projection, len(tokenizer.vocabulary)),
            "readout": _row_receipt(readout, 90),
            "row_authority": "DETERMINISTIC_EXPECTED_BYTES_ACTUAL_DEVICE_ROWS_REQUIRE_VERIFICATION"}
    return {**body, "identity_digest": _digest(body)}      # :59
```
`IDENTITY_SCHEMA = "cas.typed-teaching-frozen-encoder-identity/0.1"` (`encoder.py:21`).
`_row_receipt(raw, rows)` (`encoder.py:45-46`) = `{"dtype": "float32LE", "shape": [rows, 64], "bytes": len(raw), "sha256": ...}`.

**The digest the prediction carries** is **not** `identity["identity_digest"]`. Both are 64-hex, both come from the same object,
but they are different computations:
- `encoder.identity["identity_digest"]` = `digest(body)` = digest of the inner identity dict (`encoder.py:59`);
- the value written into a prediction as `encoder_identity_digest` = `source.digest(encoder.identity)` = digest of the **whole**
  identity object including `identity_digest` inside it (`learner.py:162`), which is also exactly what `run_identity["encoder_identity"]`
  digests to (`learner.py:110` + `:113`).
Probe D proves both from the real artifacts:
```
digest(encoder_identity as recorded in run_identity) = 15d67197fda16cb438c6b6400e78d57ea6963a5909580e1339febeddfcb49fad
encoder_identity["identity_digest"]                  = a00930c51a06adc88ad0194b0439c076a2ddd7096eb8329be5ffc4d4935fc68b
prediction["encoder_identity_digest"]                = 15d67197fda16cb438c6b6400e78d57ea6963a5909580e1339febeddfcb49fad
```
**Builder rule:** `encoder_identity_digest = digest(encoder.identity)` — never `encoder.identity["identity_digest"]`.

**Files covered by the identity (all transitive).** `profile()` (`encoder.py:30-42`) hashes only
`cas_meta2/typed_teaching/encoder.py` (`encoder.py:33`) and embeds `binding.profile()`. `binding.profile()`
(`binding.py:57-71`) hashes only `cas_meta2/typed_teaching/binding.py` (`:60`) and embeds `tokenization.profile()` and
`slots.profile()`. `tokenization.profile()` (`tokenization.py:69-79`) hashes only `cas_meta2/typed_teaching/tokenization.py`
(`:73-74`) and embeds `input_frames.profile()`. `input_frames.profile()` (`input_frames.py:98-119`) hashes **four** files:
`cas_meta2/typed_teaching/__init__.py`, `cas_meta2/typed_teaching/answers.py`, `cas_meta2/typed_teaching/input_frames.py`,
`cas_meta2/typed_teaching/source.py` (`input_frames.py:102-105`). Then `slots.profile()` adds `slots.py` + `course.profile()`'s
15 files (§A.2). So the identity covers, in total: `encoder.py`, `binding.py`, `tokenization.py`, `input_frames.py`,
`__init__.py`, `answers.py`, `source.py`, `slots.py`, and the 15 course-profile files — **22 files**. Today's digests (probe C/A):
`tokenizer.digest = 5ce5aa8b26334eb517c820ebae66216fe20439d1f91ede0ada6e64cc03edf798`,
`binding.profile().profile_digest = 4aa5a2989fe5e401787c02fdd9f1c26301b637696fc2dd2e3d774f2ac21897ab`,
`slots.profile().profile_digest = 6cc7b2a630d9c841d43f38d806d777501f6f4095185856f2688fef83150f0a98`.

---

## F. Small helpers

### F.1 `source.digest(...)`, `source.canonical(...)`, `source.require(...)` (`source.py:46-57`)

```python
def require(value, reason):                 # source.py:46
    if not value:
        raise ValueError(reason)            # source.py:48

def canonical(value):                       # source.py:51
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)     # source.py:52-53

def digest(value):                          # source.py:56
    return sha256(canonical(value).encode()).hexdigest()      # source.py:57
```
- `require(value, reason)` → raises **`ValueError(reason)`** (not `AssertionError`, so `python -O` does not strip it).
- `canonical(value)` → a **`str`** (not bytes), **sorted keys**, compact separators, `ensure_ascii=True`, `allow_nan=False`.
  It will raise `TypeError`/`ValueError` for non-JSON types or NaN. Note the `ensure_ascii=True` detail: non-ASCII characters are
  `\uXXXX`-escaped, so a byte-for-byte comparison against a Node/other-language canonical form will differ.
- `digest(value)` → 64-hex **str** = SHA-256 of `canonical(value).encode()`.
`source._bounded(value, *, allow_tuples=False)` (`source.py:64-87`) is the tree guard used by `validate_plan` / `assemble_answer`:
`TYPED_SOURCE_TREE_BOUND` (≤100 000 nodes, depth ≤20), `TYPED_SOURCE_JSON_TYPE`, `TYPED_SOURCE_CYCLE`, `TYPED_SOURCE_JSON_KEY`,
`TYPED_SOURCE_TEXT_BOUND` (≤4096/str), `TYPED_SOURCE_BYTE_BOUND` (≤4 MiB).

**Three different `canonical` in the tree — do not mix them:**

| function | file:line | returns | notes |
|---|---|---|---|
| `source.canonical` | `source.py:51-53` | `str` | sort_keys, compact, **no trailing newline** |
| `worker_contract.canonical` | `worker_contract.py:67-69` | **`bytes`** | same JSON **plus `+ "\n"`**, `ensure_ascii=False` |
| `real_framework`/`recurrent_cjt.recurrence.canonical` | `recurrence.py:83-85` | `bytes` | compact + `"\n"`, `ensure_ascii=True` |
`matched_contract.canonical = baseline.canonical` (`matched_contract.py:33`) → that is the **bytes** version;
`practice_contract.canonical = matched.canonical` (`practice_contract.py:71`) likewise. Every seal written by the worker is
`canonical(public) + "\n"` from `learner.py:191`, which uses `source.canonical` internally; the contract helper adds the newline
itself. Use the one the target function expects.

### F.2 `matched.require(...)`

There is no `require` defined in `matched_contract.py` by hand — it is imported at the top of the module as
`from . import course_plan, source, worker_contract as baseline` (`matched_contract.py:16`) and then defined at
`matched_contract.py:58-60`:
```python
def require(value, reason):                 # matched_contract.py:58
    if not value:
        raise ValueError("TYPED_MATCHED:" + reason)     # :60
```
So **`matched.require` is `source.require` with a `"TYPED_MATCHED:"` prefix on the reason**, and `matched.canonical` is
`worker_contract.canonical` (the bytes-with-newline form, `matched_contract.py:33`). `practice_contract.require` is the same
object (`practice_contract.py:71`), so a pointer worker reusing the practice helpers gets `TYPED_MATCHED:<CODE>` in its messages.
`worker_contract.require(value, reason)` raises `ValueError("TYPED_WORKER:" + reason)` (`worker_contract.py:62-64`).

---

## G. `cas_meta2/typed_teaching/matched_contract.py` (234 lines)

### G.1 Frozen constants (`matched_contract.py:18-32`)

```python
CANDIDATE = "CNCM_TYPED_MATCHED_LEARNING_001"                       # :18
CONFIG_SCHEMA = "cncm.typed-matched-worker-config/0.1"              # :19
JOB_PATTERN = r"cas-meta2-tmat-\d{14}-([a-f0-9]{8})-(a|m)-(20260917|20260918|20260919)"   # :20
CONDITIONS = (course_plan.ALT, course_plan.MIXED)                   # :21
MODEL_SEEDS = (20260917, 20260918, 20260919)                        # :22
ENCODER_SEED, SOURCE_SEED = 20260916, 101                           # :23
MAX_WALL_SECONDS = 3300                                             # :24
DEVELOPMENT_PATH = "records/typed_matched_001/development_001/compact_development.json"   # :25
DEVELOPMENT_PIN = {"bytes": 685549, "sha256": "5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4"}   # :27
COURSE_PATH, TOKENIZER_PATH = baseline.COURSE_PATH, baseline.TOKENIZER_PATH            # :28
TOKENIZER_DIGEST = baseline.TOKENIZER_DIGEST                        # :29
WHEEL_PREFIX, WHEELS = baseline.WHEEL_PREFIX, baseline.WHEELS       # :30
MAX_MEMBER_BYTES = baseline.MAX_MEMBER_BYTES                        # :31
MATERIAL = {**deepcopy(baseline.MATERIAL), DEVELOPMENT_PATH: deepcopy(DEVELOPMENT_PIN)}   # :32
canonical = baseline.canonical                                      # :33
```
Resolved values (from `worker_contract.py:20-35`):
```python
COURSE_PATH    = "records/typed_course_001/checks_002/public_course.json"
TOKENIZER_PATH = "records/typed_interface_001/checks_002/training_tokenizer.json"
TOKENIZER_DIGEST = "5ce5aa8b26334eb517c820ebae66216fe20439d1f91ede0ada6e64cc03edf798"
MAX_MEMBER_BYTES = 4 * 1024 ** 2                                    # worker_contract.py:20
WHEEL_PREFIX = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"     # :31
WHEELS = {"casformer_reference-0.1.0-py3-none-any.whl": "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee",
          "cas_neural_cjt-0.2.0-py3-none-any.whl": "6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9"}   # :32-35
```
`matched.DESIGN` (`matched_contract.py:35-55`) is `baseline.DESIGN` plus the matched-study keys and **pops**
`condition` and `model_seed` (`:54-55`), so those two are re-added per job. `practice_contract.DESIGN`
(`practice_contract.py:196-218`) inherits the 18 `_INHERITED` keys and **also carries two fields the pointer study must not reuse**:
`"registered_learner_unchanged": True` (`practice_contract.py:213`) and an update/slot-count schedule — see DG10.

### G.2 `MATERIAL` — one real row, all keys

`MATERIAL` is `{relative_path: {"bytes": int, "sha256": str}}`. Real content today (`worker_contract.py:26-29` +
`matched_contract.py:32`), three rows:

```python
{"records/typed_course_001/checks_002/public_course.json":
     {"bytes": 4165195, "sha256": "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987"},
 "records/typed_interface_001/checks_002/training_tokenizer.json":
     {"bytes": 447140, "sha256": "bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c"},
 "records/typed_matched_001/development_001/compact_development.json":
     {"bytes": 685549, "sha256": "5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4"}}
```
Row keys are exactly **`bytes`** and **`sha256`** — nothing else (`worker_contract.py:27-28`, `matched_contract.py:27`).
`DEVELOPMENT_PIN` was also verified on disk: the file exists and is exactly 685 549 bytes.

### G.3 `input_inventory(root)` and `material_inputs(...)`

```python
def material_inputs(root):                  # matched_contract.py:167
    require(type(DEVELOPMENT_PIN) is dict, "DEVELOPMENT_PIN_NOT_FROZEN")                     # :168
    baseline.read_pinned(root, DEVELOPMENT_PATH, DEVELOPMENT_PIN)                            # :169
    return [{"path": name, **deepcopy(pin)} for name, pin in sorted({**baseline.MATERIAL, DEVELOPMENT_PATH: DEVELOPMENT_PIN}.items())]   # :170

def input_inventory(root):                  # matched_contract.py:173
    rows = baseline.input_inventory(root)                                                    # :174
    development = next(row for row in material_inputs(root) if row["path"] == DEVELOPMENT_PATH)   # :175
    result = sorted([*rows, development], key=lambda r: r["path"])                           # :176
    require(len(result) <= 2000 and sum(r["bytes"] for r in result) <= 96 * 1024 ** 2, "INPUT_TOTAL_BOUND")   # :177
    return result
```
`baseline.input_inventory(root)` (`worker_contract.py:135-156`) returns rows of **exactly**
`{"path": str, "bytes": int, "sha256": str}` (`worker_contract.py:149`), sorted by path, covering `MATERIAL` keys,
the two wheels, and **every `.py` file** under `cncm/` and `research/CAS_META_2_COMPOSITION/cas_meta2`
(`worker_contract.py:138-143`). Its codes: `SOURCE_PACKAGE_MISSING:<prefix>`, `SOURCE_PATH`, `INPUT_MEMBER_BOUND:<name>`,
`INPUT_MATERIAL_PIN`, `INPUT_WHEEL_PIN`, `INPUT_TOTAL_BOUND`. `read_pinned(root, name, expected)` (`:72-79`) returns the raw
bytes and raises `MATERIAL_PATH`, `MATERIAL_SIZE:<name>`, `MATERIAL_BYTES:<name>`.

### G.4 `load_material(root)`, `public_packets(frozen)`, `development_packets`, `retention_packets`

```python
def load_material(root):        # matched_contract.py:181
    from .development import expand_development
    frozen, tokenizer, _ = baseline.load_material(root)                          # :183
    material_inputs(root)                                                        # :184
    development = expand_development(json.loads(baseline.read_pinned(root, DEVELOPMENT_PATH, DEVELOPMENT_PIN)))   # :185
    require(development["tokenizer_digest"] == tokenizer.digest
            and development["main_targets_constructed"] == 0
            and development["final_questions_constructed"] == 0, "DEVELOPMENT_BOUNDARY")    # :186-187
    return frozen, tokenizer, development                                        # :188
```
`baseline.load_material(root)` returns `(frozen, tokenizer, schedule)` (`worker_contract.py:118-124`) and raises
`TOKENIZER_IDENTITY` if the tokenizer digest differs or `max_tokens != 32768` (`:123`); it calls `validate_schedule`
(`:82-115`, codes `COURSE_IDENTITY`, `COURSE_COUNTS`, `REGISTRY_IDENTITY`, `BATCH_FIELDS`, `BATCH_CURSOR`, `BATCH_DEPTH`,
`BATCH_ROUND`, `BATCH_SHAPE`, `BATCH_UNKNOWN_RECORD`, `PRESENTATION_JOIN`, `PRESENTATION_ORDER`, `COMPLETE_COVERAGE`,
`KIND_COUNTS`). Measured from the frozen course (probe A/B): 564 registry records, 160 batches, 1152 presentations,
64 bank worlds (52 with 4 nodes, 12 with 3), 3829-token vocabulary.

`public_packets(frozen)` is a **generator** of `(record_id, packet)` (`matched_contract.py:128-129` delegating to
`baseline.public_packets`, `worker_contract.py:127-132`), where `packet = course.model_packet(frozen, record_id)`
(`course.py:285-292`). No teacher is called on this path (`worker_contract.py:129-130`).

`development_packets(development)` (`matched_contract.py:191-204`) returns a **dict** `record_id -> validated packet` and raises
`DEVELOPMENT_BOUNDARY` (`:195`) or `DEVELOPMENT_PACKET` (`:201`); it requires exactly **59** packets (`:203`) whose kind is
`parts` or `reach` with empty supports.

`retention_packets(frozen)` (`matched_contract.py:132-149`) is a **generator of `(record_id, packet)`**, built from `parts` and
`reach` registry rows with `supports = []`, re-keyed as `"typed-input-" + source.digest({...})` (`:141`); codes
`RETENTION_ID_COLLISION` (`:145`), `RETENTION_EMPTY` (`:147`).

### G.5 `schedule(frozen, condition)` and `_slot_counts(frozen)`

```python
def schedule(frozen, condition):            # matched_contract.py:90  -> (batches, planned_stats)
def _slot_counts(frozen):                   # matched_contract.py:78
```
`_slot_counts` returns `{record_id: int}` using the per-kind formula at `matched_contract.py:83-84`:
```python
values = {"role_set": 6, "definition": 3, "context": 1 + count, "analogy": 1,
          "correspondence": 1 + count, "parts": count, "edge_account": count * count, "reach": 1}
```
where `count = len(world["nodes"])` for the record's source world (`:79`, `:82`); unknown kind raises `SLOT_KIND` (`:85`).
This matches §A.3 exactly (`context` = 1 setting row + `count` participant rows; `correspondence` = 1 mode + `count` rows).
**Caveat for the pointer design:** every slot in a packet needs a logit, but `role_set`'s 6 rows come from `ROLE_IDS`, not from
the world, which is why the formula has no `count` for it.

`schedule` verifies the frozen course bytes against the `COURSE_PATH` pin (`_frozen`, `:70-75`, codes `COURSE_BYTES`, plus
`baseline.validate_schedule`), then rebuilds all three plans and asserts a long list of invariants: `CONDITION`, `OCCURRENCE_COVERAGE`
(1152), `OCCURRENCE_LINEAGE_CHANGED`, `ALT_BATCHES_CHANGED`, `DAG_ALT_AUDIT`, `CONTRAST_NOT_DISTINCT`, `PACKET_DEPTH_MULTISET`,
`NONSUPPLEMENT_CHANGED`, and finally `MATCHED_MAIN_WORK` (`:117-118`) which pins
`len(batches) == 160`, total presentations `1152`, `work == 17178` (`slot_count × depth` sum, using CURRENT untouched-label slot counts)
and `slot_calls == 4613`. It returns `(deepcopy(batches), stats)` where `stats` keys (`:119-124`) are:
`condition`, `source_seed`, `groups`, `presentations`, `unique_packets`, `presentation_slots`, `planned_slot_core_passes`,
`packet_depth_multiset_digest`, `source_plan_digest`, `batches_digest`, `occurrence_lineage_digest`, `ordinary_graph_equals_alt`,
`contrast_distinct`, `actual_compute_measured`.

**This is the hard constraint on the pointer study's planned-work formula:** `17178` and `4613` are functions of the CURRENT
per-kind slot counts. A pointer machine that changes the per-slot reading (for example, one forward per packet instead of one per
slot) must compute its own formula and **must not** reuse `matched.schedule`'s numbers as its own work estimate (DG10).

### G.6 `make_config` / `validate_config` (for reference; the pointer contract replaces these)

`make_config(root, *, source_sha, job, bucket, condition, model_seed)` (`matched_contract.py:207-225`) requires a 40-hex
`source_sha` (`SOURCE_SHA`), a known `condition` (`CONDITION`), a known `model_seed` (`MODEL_SEED`), a job whose parsed tuple and
first-8 sha fragment agree (`JOB_PARAMETERS`), and a bucket matching `[a-z0-9][a-z0-9-]{1,61}[a-z0-9]` (`BUCKET`, ≤63 chars — RK4).
It returns `{"schema": CONFIG_SCHEMA, "source_sha", "job", "bucket", "design", "inputs", "inputs_sha256"}` (`:224-225`).
`validate_config(config, root)` (`:228-234`) requires the exact 7-key shape (`CONFIG_FIELDS`) and byte equality with a rebuild
(`CONFIG_IDENTITY`).

---

## H. The practice receipt artifacts — real on-disk shapes

Receipt root: `records/typed_practice_001/receipt_<seed>/`, seeds `20260917`, `20260918`, `20260919`
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:46`).

### H.1 `checkpoints/initial_checkpoint.json` — every key and its type

This file is the **`export_checkpoint` return value** (`learner.py:315-316`), not the `.pt`. It is one line, canonical JSON.

Top level — **5 keys**:

| key | type | value for `receipt_20260917/checkpoints/initial_checkpoint.json` |
|---|---|---|
| `path` | `str` | `"/opt/cas-graph6curr/package/results/artifacts/initial.pt"` (the AWS path, not a local path) |
| `sha256` | `str` (64 hex) | `"0c1af5abb80cec2f67373fbf51c49d6e02f2edb4dc957de7bc8b9b494df98e7f"` |
| `bytes` | `int` | `1583505` |
| `run_identity_digest` | `str` (64 hex) | `"145374ac99e3bc6f0e306ee612e9c7a88b7f4c6d410d0dafff601d72a557afff"` |
| `metadata` | `object` | see below |

`metadata` — **11 keys** (`learner.py:303-307`; exact set re-checked at `:332-333`):

| key | type | value (seed 20260917, `initial`) |
|---|---|---|
| `counters` | object, 11 int keys (all `0` at cursor 0) | `{"backward_attempts":0,"backward_calls":0,"core_forward_attempts":0,"core_forward_calls":0,"optimizer_step_attempts":0,"optimizer_updates":0,"prediction_calls":0,"private_loss_plan_calls":0,"sample_core_passes":0,"slot_forwards":0,"staged_batches":0}` |
| `cursor` | `int` | `0` (and `147` at `pass_01`, `1470` at `final`) |
| `elapsed_seconds` | `float` | `0.02948368800002754` |
| `encoder_state_identity` | `str` (64 hex) | `"15d3ba3557aa8fb6142e0497d7978de798fef775dffb41080fc87798e139eae4"` |
| `model_revision` | `int` | `0` |
| `model_state_identity` | `str` (64 hex) | `"82d2037ca88593233f1176913b91f54d419ebacd23f5abc4e12bd71795feb794"` |
| `optimizer_state_identity` | `str` (64 hex) | `"3b86fdad3243758538a08d269266772dd513695d678a69a56724c3c5d8fe22a6"` |
| `rng_state_identity` | `str` (64 hex) | `"e82f30755f7fd03bced49d6eb43e80134ba76af76289e7d334c391ccff5b1b7b"` |
| `run_identity` | object, 8 keys | `{context, encoder_identity, initial_model_identity, learner_profile, limits, optimizer_config, practice_learner_profile, scope}` |
| `run_identity_digest` | `str` (64 hex) | same as the top-level value: `"145374ac..."` |
| `training_mode` | `bool` | `true` |

Inside `metadata.run_identity` — the values the task asks for:

```json
"initial_model_identity": "82d2037ca88593233f1176913b91f54d419ebacd23f5abc4e12bd71795feb794"
```
(identical to `metadata.model_state_identity` — verified equal on this file and both recomputed from `initial.pt`, probe D)

```json
"encoder_identity": {
  "schema": "cas.typed-teaching-frozen-encoder-identity/0.1",
  "d_model": 64, "seed": 20260916,
  "identity_digest": "a00930c51a06adc88ad0194b0439c076a2ddd7096eb8329be5ffc4d4935fc68b",
  "tokenizer_digest": "5ce5aa8b26334eb517c820ebae66216fe20439d1f91ede0ada6e64cc03edf798",
  "row_authority": "DETERMINISTIC_EXPECTED_BYTES_ACTUAL_DEVICE_ROWS_REQUIRE_VERIFICATION",
  "projection": {"dtype": "float32LE", "shape": [3829, 64], "bytes": 980224,
                 "sha256": "4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9"},
  "readout":    {"dtype": "float32LE", "shape": [90, 64],   "bytes": 23040,
                 "sha256": "14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667"},
  "profile": {"schema": "cas.typed-teaching-frozen-encoder-profile/0.1", "dtype": "float32LE", "d_model": 64,
              "readout_symbols": [ ...90 symbols... ],
              "binding_profile": {"profile_digest": "4aa5a2989fe5e401787c02fdd9f1c26301b637696fc2dd2e3d774f2ac21897ab", ...},
              "source": {"path": "cas_meta2/typed_teaching/encoder.py", "bytes": 15266, "sha256": "a5dcc50a4cfde6fed16f952b40bb98f2e87d24f3d40e117f8ef96507c57434ef"},
              "loaded_source_and_wheel_attestation": "REQUIRED_FROM_WORKER_NOT_ESTABLISHED_BY_THIS_PROFILE",
              "numeric_acceptance": false, "profile_digest": "..."}}
```
**Note: `digest(encoder_identity) == "15d67197fda16cb438c6b6400e78d57ea6963a5909580e1339febeddfcb49fad"`, while
`encoder_identity["identity_digest"] == "a00930c5..."` (probe D). These are two different numbers; see §E.3.**

```json
"run_identity_digest": "145374ac99e3bc6f0e306ee612e9c7a88b7f4c6d410d0dafff601d72a557afff"
```
(the same string in three places: top level, `metadata.run_identity_digest`, and every prediction's `run_context_digest`)

Other `run_identity` members (all quoted verbatim from the real file):
```json
"context": {"condition": "MIXED_SAME_ITEMS",
            "course_sha256": "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987",
            "run_id": "cas-meta2-tprac-20260918234544-daeb6497-m-20260917", "source_seed": 101},
"scope": {"allowed": ["left.weight", "merge.weight", "right.weight"],
          "contract_id": "cas.cjt.operation.^6.decompose/0.2", "frozen": [], "role": "operation:^6"},
"optimizer_config": {"learning_rate": 0.003, "weight_decay": 0.01, "betas": [0.9, 0.999], "eps": 1e-08},
"limits": {"max_updates": 1486, "max_core_calls": 600000, "max_wall_seconds": 12300},
"learner_profile": {"schema": "cas.typed-teaching-learner-profile/0.1", "profile_digest": "844fb57116bc774a01d1af89e0cfa5c66bf654aa2286ea9a8e3de8d57872a994",
                    "core_width": 64, "readout_rows": 90, "status": "WORKER_IMPLEMENTATION_NUMERIC_ACCEPTANCE_PENDING",
                    "identity_boundary": "ON_DISK_BYTES; LOADED_SOURCE_WHEEL_AND_PROVIDER_ATTESTATION_REQUIRED_FROM_WORKER",
                    "slots_profile": {"profile_digest": "6cc7b2a630d9c841d43f38d806d777501f6f4095185856f2688fef83150f0a98", ...},
                    "files": [ {"path": "cas_meta2/typed_teaching/learner.py",            "bytes": 26674, "sha256": "d87b49caed6d59e1d9715066ef030f55e09228a474c3a67e2535a3c54b3619ca"},
                               {"path": "cas_meta2/typed_teaching/loss_plan.py",          "bytes": 10441, "sha256": "df950e3dadd86de136c5f6fc5a2d4dcfdc033550ee92061a9f073e3b17c722ce"},
                               {"path": "cas_meta2/recurrent_cjt/recurrence.py",          "bytes": 18437, "sha256": "45278c0455b042e5515a73eb629a0ae90c31d41ae373ad3527e11a9cae49d17c"},
                               {"path": "cas_meta2/graph_teaching/trainer.py",            "bytes": 13502, "sha256": "e3302b90030dd9da048d6aacdc1c806967455f8a51435665eae3489d25066bd4"},
                               {"path": "cas_meta2/graph_teaching/real_framework.py",     "bytes": 20252, "sha256": "82c177e8f70e6931d90a79b65defe9fe6848cce6ab690c67f890b12c4799cd3c"},
                               {"path": "cas_meta2/teaching_cycle/gpu_adapter.py",        "bytes": 18872, "sha256": "d1b01b62c9236d8deb6ee53d9fc409fffac204f34dc5937071ab0544a718bea2"}]},
"practice_learner_profile": {"schema": "cas.typed-practice-learner-profile/0.1", "profile_digest": "ac2aede6a3ef0907cadc49ee3e0613e404e8f1eac29ac6ce1306ca1db03c2939",
                             "max_updates_ceiling": 2048, "max_wall_seconds_ceiling": 14400, "changes": "UPDATE_AND_WALL_CEILINGS_ONLY",
                             "file": {"path": "cas_meta2/typed_teaching/practice_learner.py", "bytes": 3924,
                                      "sha256": "a0557d3495ed22758e2b3b67718506785a1c9e1fa19b599af2df1530b9cc34d"}}
```
The `learner_profile.files` sha256 values above are the **exact strings the restore check compares** — a builder whose new files sit
in a *new* profile must not expect these to match (`learner.py:336` compares only `learner_profile`, so a new learner needs its own
`profile()` and its own pinned list).

The `.pt` file itself (`initial.pt`, 1 583 505 bytes) has payload keys exactly
`['encoder_state', 'metadata', 'model_state', 'optimizer_state', 'rng_state', 'schema']`; `model_state` keys exactly
`['left.weight', 'merge.weight', 'right.weight']` with shapes `(64,64)`, `(64,64)`, `(64,128)`; `optimizer_state` keys
`['param_groups', 'state']`; `encoder_state` keys `['identity', 'projection', 'readout', 'schema', 'tokenizer']`;
`rng_state` keys `['python', 'torch_cpu', 'torch_cuda']` (probe D, read with `weights_only=True`).

### H.2 The sealed prediction files — exact JSON structure

The sealed prediction files are `checkpoints/<phase>_predictions.json`, written by
`cncm/typed_practice_worker._seal_predictions` (`cncm/typed_practice_worker.py:93-96`, which is
`base._sealed_predictions` with the create-only publisher) — **3 top-level keys**:

```json
{"schema": "cncm.typed-course-prediction-seal/0.1", "phase": "course_p00", "predictions": [ ... ]}
```
Real example: `records/typed_practice_001/receipt_20260917/checkpoints/course_p00_predictions.json`,
564 predictions, `phase = "course_p00"`. Phases in play: `course_p00|p01|p10`, `heldback_p02|p04|p06|p08`,
`development_p00|p01|p02|p04|p06|p08|p10`, `retention_before|retention_after`, `replay_1|replay_2`, and the three
`initial|final|retained` reload files (`cncm/typed_practice_worker.py:47-48`).

One prediction record — **exactly the 12 keys `loss_plan.validate_prediction` demands**, real values:

```json
{"answer": {"kind": "definition",
            "query_id": "typed-query-f3bcb04aebded63611d72257aa5b74f6b79f9521eddbb52bf65f39cd7d8100da",
            "schema": "cas.typed-teaching-answer/0.1",
            "value": {"function_ref": "world-1a109d6d943a45a61bb843eb96dece5ed665a1f62372d618d5af1182a6440767/decl/function",
                      "kind_ref": "world-edc0fc8d4beea14212e3909cd309786eefd8653b60cd306874a060783780c9ba/decl/kind",
                      "whole": "world-7afc0b967564edb89050f99eeb409560cb401de94fda9bd901d97ee16a5be881/n0"}},
 "decisions": {"correspondence_candidate_id": null,
               "plan_digest": "e849544f2243e93a9c2d7d9059a5b84952a1d504f56e53daf261e57cbf2c7229",
               "query_id": "typed-query-f3bcb04aebded63611d72257aa5b74f6b79f9521eddbb52bf65f39cd7d8100da",
               "record_id": "typed-input-0245afcca3fe65f5586f723362e44815baab6c982272dc3f1a60487e8da1e53b",
               "schema": "cas.typed-teaching-slot-decisions/0.1",
               "selected": {"typed-slot-688dbf9d8dad9a1f957967f4d95a4aabae182b13b1926b2d96a6bd4f66953f00": "N0",
                            "typed-slot-767ac3ad39ce77f9aa4f19b3a32d018e17945c11f72e3ad2d743639782e134df": "W4",
                            "typed-slot-f1c8ae3b1b6d04d7840f9c5486fe200ea71f2c80eb470492dfb963dbe99344d5": "W61"}},
 "depth": 8,
 "encoder_identity_digest": "15d67197fda16cb438c6b6400e78d57ea6963a5909580e1339febeddfcb49fad",
 "model_revision": 0,
 "packet_digest": "8e1f4ef229d993e909598b929cd6221a660d8102d7fddb3c30418246b20a76b3",
 "prediction_id": "typed-prediction-b4caa5194193eef4f8f7e47811cb79f66da7f4d594e77327f6e97526bf889e1b",
 "record_id": "typed-input-0245afcca3fe65f5586f723362e44815baab6c982272dc3f1a60487e8da1e53b",
 "run_context_digest": "145374ac99e3bc6f0e306ee612e9c7a88b7f4c6d410d0dafff601d72a557afff",
 "schema": "cas.typed-teaching-prediction/0.1",
 "scores": {"typed-slot-688dbf9d8dad9a1f957967f4d95a4aabae182b13b1926b2d96a6bd4f66953f00":
                {"N0": 0.05617135763168335, "N1": -0.019019706174731255, "N2": -0.0701385885477066},
            "typed-slot-767ac3ad39ce77f9aa4f19b3a32d018e17945c11f72e3ad2d743639782e134df":
                {"W0": -0.027152933180332184, "W1": -0.03189811855554581, "W10": -0.01926041953265667,
                 "W11": -0.030172929167747498, "W12": 0.0006491942331194878, "W13": 0.01408427581191063,
                 "...": 0.0, "...": 0.0, "...": 0.0, "...": 0.0, "...": 0.0, "...": 0.0, "...": 0.0},
            "typed-slot-f1c8ae3b1b6d04d7840f9c5486fe200ea71f2c80eb470492dfb963dbe99344d5":
                {"W0": 0.0, "...": 0.0}},
 "slot_plan_digest": "e849544f2243e93a9c2d7d9059a5b84952a1d504f56e53daf261e57cbf2c7229"}
```
Detail the builder must replicate:
- `scores` is `{slot_id: {symbol: float}}` — for the definition record above the three slots hold 3, 64 and 64 entries, i.e. the
  world-choice rows carry **all 64** `W0..W63` logits, keyed `W0`, `W1`, `W10`, `W11`, ... The dict ordering inside `scores` is
  the learner's natural Python order and does not matter, because the file is written with `canonical()` (sorted keys)
  (`learner.py:191`, `cncm/typed_practice_worker.py:95-96`).
- `depth` is `8` for every evaluation by construction (`cncm/typed_practice_worker.py:145`, `learner.predict(packet, 8)`).
- `run_context_digest` and `encoder_identity_digest` are **the same for every prediction of a run**
  (`145374ac...` and `15d67197...` above).
- `prediction_id` must equal `"typed-prediction-" + digest(record without prediction_id)` — recomputed and asserted by the
  readers (`learner.py:165`, `loss_plan.py:53`, `matched_analysis.py:81-82`).
- The file is **create-only and byte-exact**: `_seal_predictions` → `_publish` → `<name>.partial` + `os.replace`
  (`cncm/typed_practice_worker.py:65-96`), and `_score_seal` re-reads and checks `bytes` + `sha256` before any target is read
  (`cncm/typed_course_worker.py:148-153`, code `SCORING_SEAL_CHANGED`).
- `initial_reload_predictions.json` (8 predictions, phase `initial_reload`) is the same 3-key seal shape; the reload phases exist
  for `initial`, `final`, `retained` only (`cncm/typed_practice_worker.py:54`).
- The per-update training seals are the same dict **without** the outer seal wrapper: `stage_batch` returns `bytes` that are
  `canonical({"schema": "cas.typed-teaching-staged-batch/0.1", "cursor", "model_revision", "run_identity_digest",
  "occurrence_ids", "predictions"}) + "\n"` plus `"batch_id"` (`learner.py:187-195`), appended one JSON line at a time to
  `pass_NN_batches.jsonl` (`cncm/typed_practice_worker.py:99-104`, `:125-133`).

---

## GOTCHAS

Every item is a trap with a `file:line` source. Ordered roughly by how likely it is to cost a paid run.

1. **`TYPED_LEARNER_GRADIENTS` kills the first batch that omits a kind (`learner.py:271`).** With
   `self.optimizer.zero_grad(set_to_none=True)` at `learner.py:185`, a head that took part in no field of a batch has `grad is
   None`, and line 271 requires **every** parameter of `self.module` to have a finite gradient. `learner.py:271` is
   `all(p.grad is not None and ...)`. A container with per-kind heads will die here. A pointer `train_sealed_batch` must require
   finite gradients only where `p.grad is not None`, require at least one non-None gradient overall, and **record** whether AdamW
   with `set_to_none=True` skips weight decay for those parameters (it does: a `None` grad means no update and no decay
   term for that parameter this step) — log per-update which parameters received gradients.

2. **`restore_checkpoint` compares the module-level `profile()`, and that profile covers 22 files
   (`learner.py:336`, `learner.py:30-38`, `slots.py:50`, `course.py:76`).** Any byte change to `learner.py`, `loss_plan.py`,
   `recurrent_cjt/recurrence.py`, `graph_teaching/trainer.py`, `graph_teaching/real_framework.py`,
   `teaching_cycle/gpu_adapter.py`, `slots.py`, or any of the 15 course-profile files breaks the practice-checkpoint restore with
   `TYPED_CHECKPOINT_RUN_IDENTITY` — including files a pointer builder might think are unrelated (`answers.py`, `checker.py`,
   `focal.py`, `face_tasks.py`, ...). A new learner must ship its **own** `profile()` and pin its own file list; it must not call
   `learner.profile()` and expect the practice values.

3. **`matched._framework` seeds the global RNG; `restore_checkpoint` overwrites it** (`cncm/typed_matched_worker.py:44-46`,
   `learner.py:358-362`). Both act on process-global state (`torch`, all CUDA devices, Python `random`) with no save/restore.
   Ordering is therefore load-bearing: run phase A's three restores **before** seeding and building the pointer model, or the
   pointer model's start weights will not be reproducible (`DESIGN_REVIEW_PIPELINE_LENS.md:188`, DG4d/S5).

4. **`model_state_identity` covers the whole `module` state dict, not the ^6 sub-block** (`learner.py:111`, `:306`). The pointer
   container's identity will not equal the practice study's value even when the ^6 weights are identical. Compare the ^6 *sub-dict*
   on its own (§D.1). Do not write a check that compares the two whole-module numbers and expect it to pass.

5. **Two different "encoder identity digest" values exist** (`encoder.py:59` vs `learner.py:162`). The prediction field
   `encoder_identity_digest` is `digest(encoder.identity)` (the digest of the **whole** identity object), **not**
   `encoder.identity["identity_digest"]` (the digest of the inner body). Both are 64-hex strings that look equally plausible, so
   nothing fails loudly at the point of the mistake: a reader that recomputes the value
   (`matched_analysis.py:82-87` recomputes `prediction_id`; any gate reader that rebuilds the prediction will recompute the
   digest chain) will simply reject the record, and `loss_plan._sealed` will reject the seal with `TYPED_LOSS_SEAL_NONCANONICAL`
   or a hash mismatch. The two real values are quoted in §E.3.

6. **The `whole` slot's symbols follow the packet's node order, not the alias table** (`slots.py:88` via `answers.py:74-75`,
   `143`). Today they coincide (0 of 64 worlds differ — probe B), so a builder that hardcodes "N0, N1, N2, N3" will pass today and
   be wrong the moment the bank changes. Derive from `inv["whole_refs"]`.

7. **`slots.compile_slots` is cached globally but `assemble_answer` recompiles (`slots.py:215`, `:301`).** If anything changes
   `slots.profile()` mid-run — including a file under `course.profile()` — a cached plan's `plan_digest` stops matching and
   `assemble_answer` raises `TYPED_SLOT_DECISION_BINDING`, while `compile_slots` raises `TYPED_SLOT_CACHE_CONTEXT_CHANGED`
   (`slots.py:184-186`).

8. **Score bounds are enforced twice in two languages** (`slots.py:248` `abs(value) <= 1000000` and finite;
   `loss_plan.py:152` / `slots.py:255` `TYPED_SLOT_NONFINITE_SCORE_RESULT`). A pointer score that is a raw dot product of
   unnormalized vectors can exceed 1e6 and fail `TYPED_SLOT_SCORE_SCALAR` **after** the forward pass is done (DG7). RMS-normalize
   each round (`recurrence.reinjected`'s feedback does bounded scaling, `recurrence.py:105-123`).

9. **`TYPED_LEARNER_SCALAR_TENSOR_LOSS_MISMATCH`, tolerance `2e-5`** (`learner.py:261`). The tensor loss and the pure-Python
   `loss_plan.scalar_report` must agree to `rel_tol=2e-5, abs_tol=2e-5` per batch, on every batch, all run. Reproduce the loss
   arithmetic exactly as `_tensor_loss` does (`learner.py:197-235`) — field mean, then task mean, then batch mean
   (`slots.py:35`, `loss_plan.py:18-23`) — or this fires.

10. **`set_to_none=True` semantics** (`learner.py:185`): after the call, `p.grad` is `None`, not zero. Any code that reads
    `p.grad` before the next `backward()` must handle `None`; and any code that (like item 1) checks "every parameter has a
    gradient" will see `None` for parameters that no field of the batch touched.

11. **The evidence publisher is create-only** (`DESIGN_REVIEW_PIPELINE_LENS.md:114`; `cncm/typed_practice_worker.py:65-96`,
    `:99-104`). Every file under `results/` must be complete before its final name exists: write `<name>.partial` (skipped by the
    publisher, `cncm/typed_practice_worker.py:198-199`), fsync, then `os.replace`; grow JSONL logs in a **staging directory outside
    `results/`** and move them in whole (`_move_in`, `:83-90`). A file that grows after its first upload fails the final upload with
    `EVIDENCE_DIGEST_CONFLICT`. `export_checkpoint` itself is create-only (`open("xb")`, `learner.py:312`) and raises
    `TYPED_CHECKPOINT_PARENT` if the directory is missing.

12. **Windows CRLF breaks the AWS package build.** The repo is `eol=lf` (`.gitattributes:1-2`) and the launcher compares
    working-copy bytes to committed blobs, so a CRLF `.py` fails with `INPUT_NOT_COMMITTED`
    (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:110-112`). Write with the Write/Edit tools or `write_bytes`; never
    "renormalize" the old files that are committed with CRLF. Note also the repo deliberately marks some trees `-text`
    (`.gitattributes`), so byte equality, not normalization, is the contract.

13. **Any new `.py` under `cncm/` or `cas_meta2/` between authority and launch blocks jobs 2 and 3** (RK9;
    `worker_contract.py:138-143` re-globs those two trees into the inventory, and the launcher re-validates at execute time,
    `DESIGN_REVIEW_PIPELINE_LENS.md:83-88`). Keep gate readers and analysis scripts under `records/`.

14. **Bucket names are capped at 63 characters** (`matched_contract.py:212`, `worker_contract.py:162`; bucket = job +
    `-807562639912`). The study token after `cas-meta2-` must be ≤5 characters: `tpntr` → **63** (exactly at the
    limit; **corrected 2026-09-19** — this line said 62 and was wrong by one character), `tpoint` → 64 (fails)
    (`DESIGN_REVIEW_PIPELINE_LENS.md:52-55`). Add a length test for all three seeds.

15. **`scope_parameters` freezes everything outside the ^6 allowlist** (`trainer.py:86-88`) and
    `require(self.scope == {...three names...}, "TYPED_LEARNER_REGISTERED_SCOPE")` fails for any other scope
    (`learner.py:82-83`). Two independent reasons a pointer container cannot be hosted by `TypedCourseLearner`, plus
    `TYPED_LEARNER_PARAMETER_SHAPE` (`learner.py:85-86`) and the AdamW list restricted to the three names (`learner.py:107`).

16. **`encode_text` rebuilds a 3 571-entry lookup per call** (`tokenization.py:151`), measured 0.0111 s
    (`DESIGN_REVIEW_PIPELINE_LENS.md:47`). 64 world-choice symbols per packet × thousands of packets exceeds the 12 300 s
    `WORKER_DEADLINE_SECONDS` (`practice_contract.py:64`). Build the lookup once from
    `(tokenization._unword(t), i) for i, t in enumerate(vocabulary[258:], 258)` and cache label/declaration encodings, pinning the
    cache digest (RK3).

17. **`references` ordering:** `scores` must contain **all** world aliases for world-choice slots (`W0..W63`) and exactly the
    slot's declared symbols elsewhere (`slots.py:247`), so a pointer head that only emits a chosen symbol fails
    `TYPED_SLOT_SCORE_SYMBOLS` before any loss is computed.

18. **`ASSERT`-free spend paths:** `source.require` raises `ValueError` (`source.py:46-48`), `worker_contract.require` raises
    `ValueError("TYPED_WORKER:" + reason)` (`worker_contract.py:62-64`), `matched.require` raises
    `ValueError("TYPED_MATCHED:" + reason)` (`matched_contract.py:58-60`). Never use `assert` in a spend path
    (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:374`: `python -O` strips it).

19. **Three different `canonical()`s** (§F.1) — one returns `str` without a newline, two return `bytes` **with** a newline. The
    seal format is `canonical_json + "\n"` (`learner.py:191`, `loss_plan.py:66`) — a seal written without the trailing newline is
    rejected with `TYPED_LOSS_SEAL_NONCANONICAL`.

20. **`matched.schedule` pins the old machine's work counts** (`matched_contract.py:117-118`: `work == 17178`,
    `slot_calls == 4613`), and `design.schedule` numbers are old-machine counts (DG10). A new DESIGN must carry its own planned-work
    formula and be tested against real counters (test P11), and it must **not** inherit
    `"registered_learner_unchanged": True` (`practice_contract.py:213`).

21. **`int`/`bool` traps:** `type(value) in (int, float)` is used for scores (`slots.py:248`) and `bool` is rejected even though
    `isinstance(True, int)` is true; `type(x) is int` (not `isinstance`) is used for limits and seeds
    (`learner.py:94-101`, `matched_contract.py:210`), so a `numpy.int64` seed fails `MODEL_SEED`.

22. **Phase A/B custody (FP3):** the checker must not be imported and no `derive_target` may run before the first pointer seal.
    The registered order is `base._write_bytes(seal)` → read back → `from cas_meta2.typed_teaching import checker` →
    `derive_target` (`cncm/typed_practice_worker.py:107-121`, `cncm/typed_course_worker.py:180-183`). Probing held-world answers
    "first" would read held-back correct answers before training.

23. **`restore_checkpoint` also restores `training_mode` and the elapsed clock** (`learner.py:356-357`) and re-checks
    `metadata["counters"]["optimizer_updates"] == metadata["cursor"]` (`learner.py:350`), so a restored learner's
    `_elapsed_before` is the old run's wall time — budget checks (`learner.py:122-123`) compare against
    `limits["max_wall_seconds"]`, not against the new job's clock.

24. **`state_identity` ignores device but not dtype or shape** (`learner.py:47-61`). A pointer head stored as float64, or a
    transposed view with the same values, changes `model_state_identity` and breaks
    `TYPED_CHECKPOINT_RESTORED_VALUES` (`learner.py:344`).

25. **`_packet_bytes` rejects tuples** (`slots.py:131` `type(value) in (dict, list, str, int, bool, type(None))`). A packet built
    with tuples raises `TYPED_SLOT_CACHE_JSON_TYPE` before compilation.

---

## UNCERTAIN (explicitly not determined from the source)

UNCERTAIN: `matched._framework`'s claim that the ^6 weights are drawn **first** is established from source order
(`cas_cjt/neural.py:181-188` builds the `nn.ModuleDict` with `DECOMPOSE` first, and `real_framework.py:77` constructs the bank
without any prior parameter creation) — but it was **not** executed, so I cannot report a measured equality between a freshly
built `_framework(torch, device, seed=20260917).module.state_dict()` and the practice `initial.pt` `model_state` tensors. The
three recorded `model_state_identity` values per seed are quoted from the artifacts (§D.1) and are the correct comparison targets.

UNCERTAIN: the exact number of parameters in a whole `GraphTrainingFramework` module state dict beyond the documented three.
`real_framework.py` aliases `bank.modules_by_operation[DECOMPOSE]` (`:78`) and `resolve_plasticity_groups` returns
`model.named_parameters()` for that module (`:47-49`), and every observed checkpoint has exactly three keys — but I did not
instantiate the class to count them, because that requires `casformer`/`cas_cjt` wheels and would run torch for a model build
outside this task's budget.

UNCERTAIN: whether `course_plan.compile_plan(SOURCE_SEED, course_plan.DAG)` (`matched_contract.py:97`) and
`course_plan.DAG` (`:104`) are usable as-is by a pointer worker. `DAG` is only used as an audit comparator inside `schedule`, and
`matched_contract.parse_job` maps only `a`/`m` (`:67`); I did not read `course_plan.py` to check for other exported plan names.

UNCERTAIN: the pointer study's own bucketed-length test values, job pattern and MATERIAL rows do not exist yet (no
`pointer_contract.py` on disk), so §G documents the practice/matched constants they must be derived from; the `≤5-character`
study token rule (`tpntr`) is taken from `DESIGN_REVIEW_PIPELINE_LENS.md:52-55` measured arithmetic, not from a source constant.

UNCERTAIN: I could not confirm an on-disk owner-signed per-job record format for the pointer study (DG9); the practice study's
`owner.json` shape was not read here, and `records/typed_pointer_001/` currently holds only `pre_design/`.
