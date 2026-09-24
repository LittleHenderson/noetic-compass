# Builder report: larger-question path v0.1 (HELM-LARGER-QUESTION-PATH-1), 2026-09-23

Written by the temporary Claude builder. Codex is away until 2026-09-28.

- **Status: BUILT, and checked statically on the laptop. The AWS checks are NOT_RUN.** Nothing ran with torch.
- Branch: `claude/helm-builder-continuation-20260923`. Parent: `ec80730cf5aef72f28b3db76ba56f2819330878c`.
- Code commit: `785c9bd10f1416deb95f9c30aacb43124134fe45`. This report is in the commit after it.
- No protected file was edited. Every new file is in `research/CAS_META_2_COMPOSITION/eval_paths/`.

## In one paragraph

Helm can now be asked 5- and 6-node questions of every kind, through its real forward pass, if the caller opts in.
A small router looks at every world in the question. If every world has 4 nodes or fewer, the question takes the
old path, unchanged. If the largest world has 5 or 6 nodes, the question takes the new path: the accepted slot
compiler v2 builds the answer slots, and the accepted checker v2 grades the answer. If any world has 7 or more
nodes, or any node has more than 4 arrows in or out, the question is refused with a named reason before any
work is done. Grading is kept separate from answering. The path never trains.

## What was already true, and what this adds

This matters for reading any later result, so it comes first.

- **The old learner already answered most 5- and 6-node questions.** For parts, reach, edge account, definition,
  context, role and analogy questions, the old slot compiler has no node limit. Slot compiler v2 hands these
  questions straight to the old compiler, so the answer slots are byte-identical on both paths (tested).
- **What the old learner could not do.** It refused every correspondence question with a world above 4 nodes
  (`TYPED_PERMUTATION_BOUND`). And the old checker refused to grade analogy and correspondence above 4 nodes
  (`TYPED_CHECKER_ISOMORPHISM_BOUND`).
- **What the old learner did silently.** It answered 7- to 10-node parts, reach and edge questions without any
  warning (tested on the 7-node fixture `R01`). The new path refuses them by name.

So the new path adds three things: correspondence at 5 and 6 nodes, grading with checker v2, and explicit refusal.

## Design

### The route

| Largest world in the question's source | Max arrows in or out of any node | Route | Slot compiler | Grader |
|---|---|---|---|---|
| 4 nodes or fewer | (always 3 or fewer) | `ORIGINAL_PATH` | frozen `slots.py` | frozen `checker.py` (scorer of record) |
| 5 or 6 nodes | 4 or fewer | `LARGER_PATH` | accepted `slots_v2.py` | accepted `checker_v2.py` |
| 7 or more nodes | any | refused: `LARGER_PATH_REFUSED:WORLD_ABOVE_SIX_NODES` | none | none |
| 5 or 6 nodes | 5 or more | refused: `LARGER_PATH_REFUSED:DEGREE_ABOVE_READER_EXACT_RANGE` | none | none |

- **Every world counts, not only the focus.** A 7-node world anywhere in the bank refuses the question. This is
  stricter than the checker needs for parts or reach. It keeps any 7-node shape out until a separate, tested change.
- **Why the degree limit.** Helm's degree features have 5 buckets, 0 to 4, where 4 means "4 or more"
  (`pointer_learner.py:211`, `:1016-1017`). A node with 5 arrows would look like one with 4. The D-1 spec, section S5,
  already requires HSET worlds to keep every degree at 4 or less.
- **A malformed question goes to the old path**, so the old validators refuse it with their own error codes.
- **Every historical course question takes the old path.** Course questions carry the frozen 64-world training bank
  (`course.py:86-87`, `:156-163`). Measured: its largest world has 4 nodes and its largest degree is 3.

### Two ways in, both opt-in, both inference-only

1. `larger_question_learner.predict_packet(torch, model, packet, device, *, tagger)`. It works on a bare pointer
   container. Use it for the Helm 2.0 checkpoints (switch OFF, loaded as `preservation_digest.py` loads them) and
   for a fresh switch-ON container. It runs the same steps in the same order as `PointerCourseLearner._graph`
   (`pointer_learner.py:1918-1951`): compile slots, read the packet, run `GraphForward`, take the head logits,
   decode, build the answer. Only the slot compiler changes, and only on the new route. It refuses a non-CUDA
   device (`GPU_REQUIRED`) and a model not in eval mode.
2. `LargerQuestionPointerLearner`, a subclass of `PointerCourseLearner`.
   - On the old route its `_graph` calls `super()._graph(packet)`: the original, untouched.
   - On the new route it runs `_graph_larger`: a line-for-line copy of `_graph` in which `from . import slots` is
     replaced by slots v2. A test compares the two function bodies by syntax tree. Exactly one statement differs.
   - `stage_batch` and `train_sealed_batch` raise `LARGER_PATH_REFUSED:INFERENCE_ONLY`.
   - `restore_checkpoint` builds `cls(...)`, so a future switch-ON checkpoint (schema 0.2) restores into this class.

### Fail-closed source pins

`larger_question_scope.verify_source_pins()` checks the LF sha256 of 12 protected files it relies on. The three v2
files must equal the D-1 ACCEPTED anchors. The learner half runs this check at import. If any of these files
changes, the path refuses (`LARGER_PATH_REFUSED:SOURCE_DRIFT`) until someone reviews it again.

| File | LF sha256 |
|---|---|
| `pointer_learner.py` | `2ebb1b086953002272d18e75d397bb233b75f62442d073487ebade2e93487781` |
| `pointer_inputs.py` | `ba920d9e65e20b96dd0614a7131a80b9b87dd9918cb07d94ec5ebb4b628d0ecd` |
| `pointer_contract.py` | `70be7ae7b7b3dbefd6a5d168b04ab7394718d7456a264614236d31b0c9c09b3d` |
| `slots.py` | `3d79db262708264dcd77cd7fb0296e7683849b5967b82d72fd3c51ab85f74487` |
| `slots_v2.py` (D-1 anchor) | `7b9c2c3a0aca938acf0979aa7d74f1fea422726333926f079a5f8e06f5e7d2fb` |
| `answers.py` | `4d4cf21b65914c5b6878b58a52ab3cfe2f8864b319a3bb5ad1b95c6780686e5c` |
| `answers_v2.py` (D-1 anchor) | `b0bdabfcfac656e4071f192d9bda8ff7dec8b88baf077f29131d8f94497d1bb5` |
| `checker.py` | `57ac0a9f78c46999fac444fc974d3c1b718435b583cbc48701be74c56efa971e` |
| `checker_v2.py` (D-1 anchor) | `d24d8276955bacbe626ebe6293efe7b64c2cf36544100b60175f6d0ab80e6258` |
| `source.py` | `13c265e576dd027362611ca0956ac9f1e6285945cb7e626cef9270c2d08a9337` |
| `course.py` | `cbb1b5aea97567f21cb15ca2def5332ea3175abd10e8a6a48b9e3edd9e0e41e6` |
| `focal.py` | `cd2761b5c5dced4af5e4acc0a6b55a384555b2cb9bb3b90442f8673d1754e70a` |

## Kind-by-kind scope at 5 and 6 nodes

"Same code as frozen" means: checker v2 differs from the frozen checker only in its profile name and its
isomorphism bound (4 raised to 6), shown by `diff checker.py checker_v2.py`. For these kinds that bound is never
used, and the static test confirms equal answers and evidence from both checkers on the fixtures.

| Kind (rules) | Old slot compiler at 5-6 | Old checker at 5-6 | Checker v2 at 5-6 | D-1 acceptance tested it? | Answer slots Helm fills |
|---|---|---|---|---|---|
| `role_set` (`focal_excerpt_roles_v1`) | compiles | grades | grades; same code as frozen | no | 6 role slots, ABSENT/PRESENT; node count does not matter |
| `definition` (`declared_kind_and_function_v1`) | compiles | grades | grades; same code | no | whole: one of N0..N(n-1); kind and function: one of W0..W64 |
| `context` (`declared_setting_and_participants_v1`) | compiles | grades | grades; same code | no | setting: one of W0..W64; one ABSENT/PRESENT slot per node (3 primary labels) |
| `analogy` (`cross_domain_full_graph_isomorphism_v1`) | compiles | **refuses** | grades if the focus and every bank world have 6 nodes or fewer | **yes** (A3, A5, A6) | NO_MATCH or one bank world alias (64 bank worlds at most) |
| `correspondence` (`full_directed_graph_bijection_v1`) | **refuses** | **refuses** | grades if 64 or fewer valid maps | **yes** (A3) | mode NO_MATCH/MAPPING plus one target slot per focus node; the decoder scores all 121 (5 nodes) or 721 (6 nodes) complete maps |
| `parts` (`direct_contains_v1`) | compiles | grades | grades; same code | only at 3-5 nodes (X, HSET-1A) | one ABSENT/PRESENT slot per node |
| `edge_account` (`complete_edge_set_lexical_serialization_v1`) | compiles | grades | grades; same code | only at 3-5 nodes (X) | one slot per ordered node pair: 25 at 5 nodes, 36 at 6 (limit 100) |
| `reach` (`first_direct_constituent_lexical_v1`, `bfs_immediate_predecessor_lexical_v1`) | compiles | grades | grades; same code | only at 3-5 nodes (X) | one slot: ABSENT, DIRECT or VIA_N0..VIA_N(n-1) |

The same table is `larger_question_scope.KIND_SCOPE`, and a test checks every "compiles / refuses / grades" word
against the fixtures.

### Can Helm's heads hold every correct answer?

- **Yes, for every kind at 5 and 6 nodes.** Checked by decoding: for each of the 37 answerable fixtures, scores
  that favour one correct answer were fed to the route's decoder. The decoded answer equalled the checker's answer
  every time, and checker v2 graded it correct. This proves the answer space can hold the answer. It says nothing
  about whether a trained Helm will find it.
- **Ranges.** Node answers use N0..N9 and VIA_N0..VIA_N9 (up to 10 nodes). World answers use W0..W64 (up to 65
  worlds). Participants carry ranks 1 to 3, one per primary label. None of these limits binds at 5 or 6 nodes.
- **The answer cap never binds on an allowed shape.** Across all connected 5- and 6-node shapes with every degree
  at 4 or less, the most self-maps any shape has is 24 at 5 nodes and 48 at 6 nodes. Checker v2 refuses only above 64.
  (Shapes with isolated nodes were not counted. If one ever exceeds 64, grading refuses by name:
  `LARGER_PATH_REFUSED:GRADER_OUT_OF_SCOPE:TYPED_CHECKER_TARGET_SET_BOUND`.)

### Can Helm's input tell same-count shapes apart? (a necessary condition only)

The owner wants "different wiring with the same simple counts". Helm passes messages from parents and children, so
it can only separate two such shapes if directed colour refinement can. `colour_refinement_census.py` counted this:

| Nodes | Connected shapes | With every degree at most 4 | Shapes that share a degree list with another | Same-degree pairs | Pairs colour refinement cannot separate |
|---|---|---|---|---|---|
| 5 | 267 | 267 | 105 | 116 | 0 |
| 6 | 5,647 | 5,074 | 3,996 | 12,588 | 0 |

- The totals 267 and 5,647 match the known counts of connected DAG shapes. The 105 matches D-1's own count.
- **This does not show that Helm can separate them.** Helm also rescales each summed message to unit size
  (`pointer_learner.py:1185-1186`), which hides how many identical neighbours were added. Not measured.
- One code comment is now out of date for larger worlds: `pointer_learner.py:54-57` and `:207-210` say the degree
  list is a complete shape fingerprint "on this corpus". That was true at 3-4 nodes. It is false at 5 and 6 nodes.
  I did not edit the file.

## Inventory check: the new folder is outside what training ships

The training launcher's input list is built by this chain. Every link was read, and a test re-reads it:

1. `research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py:39` imports `pointer_contract as contract`.
2. `typed_pointer_launch.py:303` `_committed_rows`, line `:321`: `rows = contract.input_inventory(...)`.
3. `cas_meta2/typed_teaching/pointer_contract.py:422`, line `:429`: `practice.input_inventory(root)` plus 18 checkpoint rows.
4. `cas_meta2/typed_teaching/practice_contract.py:74`: `input_inventory = matched.input_inventory`.
5. `cas_meta2/typed_teaching/matched_contract.py:173-174`: `baseline.input_inventory(root)` plus one development file.
6. `cas_meta2/typed_teaching/worker_contract.py:135-156`, lines `:138-139`: only `*.py` under `cncm` and
   `research/CAS_META_2_COMPOSITION/cas_meta2`, plus the pinned material and wheels.

`research/CAS_META_2_COMPOSITION/eval_paths/` is under neither prefix. The learner's own identity file list is fixed
(`pointer_learner.py:469-478`) and does not name it. No protected file mentions `eval_paths` (tested). So the
controlled repaired-versus-unchanged training comparison ships the same source as before.

## Public fixtures

- File: `eval_paths/fixtures/larger_question_fixtures_v0_1.json`, 190,466 bytes, sha256
  `7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3`, fixture-set digest
  `049b92bb657831ba4df5a50f2135801510b464fa202384e4ec52ebe814ed75f2`.
- `python -B larger_question_fixtures.py --check` rebuilds it byte for byte.
- **Construction.** The public HSET construction (`hset_worlds.world_from_spec` and `build_packet`, read from the
  integration branch). Words come only from the 4 training domains. 0 supports. No salt, no TEST material.
- **Expected answers are computed without the checker** (brute-force matching; the two reach rules re-implemented).
  A test compares them with checker v2 on every fixture. They agree on all 37.
- **Banks.** `MAIN`: 10 hand-made worlds of 4, 5 and 6 nodes. `FROZEN_TRAINING`: the course's own 64-world bank
  plus a new focus, 65 worlds, as HSET builds them; it is rebuilt on load and pinned by its bank digest
  `0f563762a70e67513ca3e6996d988afd4421dd90fe63e1a04942a31a79e9c388`. `REFUSE_SEVEN` and `REFUSE_DEGREE`: refusal only.

### Shapes (node 0 is the declared whole; edges over node numbers)

| Shape | Nodes | Edges | Role |
|---|---|---|---|
| S4 | 4 | 0→1, 0→2, 2→3 | a 4-node focus inside a larger bank |
| S5A | 5 | 0→1, 0→2, 1→3, 3→4 | main 5-node shape |
| S5B | 5 | 0→1, 0→2, 1→3, 2→4 | **same degree list as S5A, different wiring** |
| S5C | 5 | 0→1, 0→2, 3→2, 3→4 | two roots: node 4 has **no path** from node 0 |
| S6A | 6 | 0→1, 0→2, 1→3, 2→3, 3→4, 4→5 | main 6-node shape (2 self-maps) |
| S6B | 6 | 0→1, 0→3, 1→2, 2→3, 3→4, 4→5 | **same degree list as S6A, different wiring** |
| S6D | 6 | 0→1, 0→3, 1→2, 4→3, 4→5 | two roots: node 5 has **no path** from node 0 |
| S7 | 7 | 0→1, 0→2, 1→3, 2→4, 3→5, 4→6 | refusal only |
| S6STAR | 6 | 0→1 .. 0→5 | refusal only (out-degree 5) |

Canonical forms are in the file. **Their format is this builder's own** (smallest sorted edge list over all
relabellings), not `oracle_isomorphism.canonical_form`. A custodian should re-derive from the edge lists.

### The 41 fixtures and their identities (packet sha256)

Nodes = the largest world in the question's source. Worlds = worlds in the source.

| Id | Kind | Rule | Nodes | Worlds | What it tests | Packet sha256 |
|---|---|---|---|---|---|---|
| F01 | role_set | | 6 | 10 | 5-node focus; one analogy clause | `09e5404bf74f4d5fe274cac4e20e2329250fe3a8f52257211d93eaa57b4f4ae6` |
| F02 | definition | | 6 | 10 | 5-node focus | `b39e2b61fea84d86009e7b353cb27ad65c738fe1e368cac89914d37deb48acfa` |
| F03 | context | | 6 | 10 | 5-node focus | `2cf3951c40a146b1fed9e4f87e421d1536e65775e857fc53656079a524704957` |
| F04 | analogy | | 6 | 10 | 5 nodes; genuine match; same-degree decoy in bank | `02805d3c239af5040e8951cb9e31a5cbd6c1b74ad05b7d31d67a38b4ba67e280` |
| F05 | analogy | | 6 | 10 | 5 nodes; **genuine no-match** (only same-degree decoys) | `27a22cd5f69091c32fd8177b6df43340499bdaee260c7e620a7e539b9b086914` |
| F06 | correspondence | | 6 | 10 | 5 nodes; MAPPING | `72dafb3f3850db57ae1cad1d2fe8116b9f4c4bf751198c28935175ffaabe8ae9` |
| F07 | correspondence | | 6 | 10 | 5 nodes; **genuine no-match**, same degrees, 121 candidates | `82be550c5c41c40b5146f7b4f824f6f3bd836ccd50e09fddc220343eab5c1e76` |
| F08 | parts | | 6 | 10 | 5-node focus | `9cff201600a4cfb86e6d0a9a1623be131a1d1bd1a0b2adeae53d35ef1e397684` |
| F09 | edge_account | | 6 | 10 | 5-node focus | `657e36b0145fce0f052ae171f2591128e30e74e512eddfe23663b8f1e3a9d98a` |
| F10 | reach | first_direct | 6 | 10 | VIA, 3 steps | `2db6c1d75faa4e01aa7232c25a4354eda214ae96afee02ab3c6fbbb64a5ec875` |
| F11 | reach | bfs | 6 | 10 | VIA; the two rules name different nodes | `479ca227f87d728dddfdf2298109caaf10fc47a245138512328e7b1ac2dd92e8` |
| F12 | reach | first_direct | 6 | 10 | **genuine no-path** (part under another root) | `893b1007bebfc7f3fb10d73ad5c005167b6b9a3a4cc07350a999d96199d34320` |
| F13 | reach | bfs | 6 | 10 | DIRECT | `a8dc0351877a36884be087c2b3d2be5e21ea8eaa65e1a88a24ea5b8a2b019ebb` |
| F14 | role_set | | 6 | 10 | 6 nodes; definition + account clauses | `1ce4c36cf9dd33d4e49b784a92e2ffdb9ef7e264e6d2dfebfd924eee5177e484` |
| F15 | definition | | 6 | 10 | 6 nodes | `6579573737e619a3678805887cbadc83e2aa195bea5a143082c1f6ced8f4077a` |
| F16 | context | | 6 | 10 | 6 nodes | `9b28c62397551859600da99e46ebf718e9218488099edb56c2fb93f72609df14` |
| F17 | analogy | | 6 | 10 | 6 nodes; genuine match; 2 same-degree decoys | `51c9fb47e73fc7c9cd7f6f537d6b261577c94cadea60f2068952ef77be6e5b8e` |
| F18 | analogy | | 6 | 10 | 6 nodes; **genuine no-match**: the only twin shares the domain | `3a51542f89086429b3849e66954c4aa6f13aff4437db0f2573ea5a29c886d6c0` |
| F19 | correspondence | | 6 | 10 | 6 nodes; MAPPING, 2 valid maps | `6faa93539dff3112c0a6c0768f3024e12bb085de9af4bce99850b418c4d7d06c` |
| F20 | correspondence | | 6 | 10 | 6 nodes; **genuine no-match**, same degrees, 721 candidates | `ea1bb23b024127b41b4bf91063fceb11eeb09362195eccfe9e267e7833371419` |
| F21 | parts | | 6 | 10 | 6 nodes | `e4d37101b6f65679347796ccceeb4bda276e0bd7c7d0a982c82d888636513bb0` |
| F22 | edge_account | | 6 | 10 | 6 nodes | `91605d971c9b23caaea84533f482da5a3c3040bb45bdcc4f5a49c6952037688b` |
| F23 | reach | first_direct | 6 | 10 | VIA; which child is named depends on node rank (a tie) | `5976b4126307d7c8246b763b3ad2dd7b28b7dfcaf0b3c54fdb3e155ad8499855` |
| F24 | reach | bfs | 6 | 10 | VIA, 4 steps | `15591de80c81244c7e50447bd15ce3356d42a5e0d2f6facc6a4b16d17982dde3` |
| F25 | reach | bfs | 6 | 10 | **genuine no-path** | `99027c453ad60a1752601921f04bb259085143bcfd92c84fd9e9dc565afcc550` |
| F26 | reach | first_direct | 6 | 10 | DIRECT | `bd659a083086069f59b4a054e91d6b380ab41bca96f5e9502a06c6c99d2432d7` |
| F27 | correspondence | | 6 | 10 | 6 nodes; MAPPING within one domain | `bac6437ccbd883731d2bbc654b02cd0fe0e6c50465ae0111bb3d8e32733fc680` |
| F28 | parts | | 6 | 10 | 4-node focus in a larger bank: takes the new route | `ed00b26e364d98978ea1a489abcfd112dc559ee4507d7ae9f202a0c518d212a4` |
| F29 | correspondence | | 6 | 10 | 5 to 6 nodes: forced NO_MATCH, 1 candidate | `f73bd2138bb9e9e5b196acbd0b7435af5170ef34c7539d795cad58060e2e454b` |
| F30 | correspondence | | 6 | 10 | 4 to 5 nodes: forced NO_MATCH; old compiler refuses | `5478430e8c1b89e2eb812808be1f94b53427d8981fa0707b04a8c1d252583dcf` |
| F31 | reach | first_direct | 6 | 10 | VIA, 2 steps | `2ebe344dc5cefd047605516636fd0cf4d15575e29cd318a29455fd6e73e1120d` |
| H01 | definition | | 6 | 65 | training bank + 6-node focus: aliases W0..W64 | `efd72c1a10b90dc59c575399d891c3fe15bce509f2a339ac9e4dd51e1728fb85` |
| H02 | analogy | | 6 | 65 | NO_MATCH by size only | `22a85eb9fb9d17be2c02068ad9c89cf74d8ead691e445d7e7aa91e589636fd1b` |
| H03 | reach | bfs | 6 | 65 | VIA | `0f848a83ebcbc263485ecff22669d6e55bda8e39813e66b3b848054d7847a510` |
| H04 | correspondence | | 6 | 65 | forced NO_MATCH to a 4-node training world | `1008c2165f7108031e398d6308281e98e8b20220cd79fd71ee02b13f4b7f328e` |
| H05 | context | | 5 | 65 | 5-node focus | `053d41da9eb3b37f1ed1626dd69dfb6b7a853ce646341f5d5a0b7f4d5d4fb812` |
| H06 | parts | | 5 | 65 | parts of the second root | `6b5fc441d767610b6ad4462d9b8c862ef538e742791eb3c7e7679c8eea24aa75` |
| R01 | parts | | 7 | 2 | refuse: 7-node focus | `0d6f835f32581e93f17003c31a27009530403ef6333f7ea193af422ce8b88356` |
| R02 | analogy | | 7 | 2 | refuse: 5-node focus, 7-node world in bank | `21811c7d7a81708347118a8b4f3a8b9cb1e6e7bf2b17b2a2df95c1d7e326c3a7` |
| R03 | parts | | 6 | 2 | refuse: a node with out-degree 5 | `cfb6f1e06290768907a1e6c58b198a1dcaa9485380c9ea86c15a6befec6b3089` |
| R04 | definition | | 6 | 2 | refuse: degree-5 world in bank | `481c9ba1a3a5ea353722a11b6fb4fa88851cc2e471fa4cd1e1b21dba603e9856` |

Every kind is covered with a 5-node focus and with a 6-node focus. Both reach rules are covered.

## Files (all LF line endings)

All paths are under `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/eval_paths/`.

| File | Bytes | sha256 | What it is |
|---|---|---|---|
| `__init__.py` | 393 | `38a1d4f57995cd43b5a0ed1616b2e941726327abed0919f3d8ce7a793f1e0ae4` | package marker; says why the folder is outside the inventory |
| `larger_question_scope.py` | 15,446 | `4da36a48ba0c9938e8df80f9380449186074ea6e5a9e2c57c487277598852b67` | pure: route, refusals, decode, grade, pins, kind table |
| `larger_question_learner.py` | 7,852 | `82e963a4b30b2aab8a8cb7371faaca32b66c011a90bece59d1f9106a7bd7d35d` | torch half: `predict_packet`, the subclass |
| `larger_question_fixtures.py` | 32,130 | `567331464043e7fdb4edffc1dc056f266c75141c312fecdca43d10dff3c3e86d` | fixture builder, checker, loader |
| `fixtures/larger_question_fixtures_v0_1.json` | 190,466 | `7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3` | the 41 fixtures |
| `colour_refinement_census.py` | 5,295 | `dbf9d01f41946349bf853ec51b9d3a279b8194a0914758075212337ffe4cbb5f` | the same-degree census above |
| `t4_larger_question_checks.py` | 25,588 | `3f02c9e88371386db8e84aff281d089e52652e7429e90ce716751ba454af2884` | AWS T4 checks a-d |
| `tests/test_larger_question_path_static.py` | 25,002 | `b74ba3e073a6fc8911a7893679c3ab77aab5c37a5befc34aa21778e27ac142f5` | 26 torch-free tests |

## What I checked on the laptop (static only; no torch)

| Check | Result |
|---|---|
| `python -B -m pytest -q -p no:cacheprovider eval_paths/tests/test_larger_question_path_static.py` | **26 passed in 88.90 s** |
| Same tests by plain `python -B` (before the census test was added) | 25 passed, 0 failed |
| Fixture file rebuilt in memory | byte-identical (`FIXTURES_REPRODUCE`) |
| Syntax of all 7 `.py` files (`compile`, no bytecode written) | all pass; all LF |
| Protected-file pins (12 files), including the 3 D-1 anchors | all equal |
| Committed blobs versus files on disk (8 files) | all equal |
| `torch`, `pointer_learner`, `pointer_contract`, `pointer_inputs` imported by the tests | none |
| Mutation check (scratch copies, not committed): one changed statement in the copied `_graph`; one false word in the kind table; one wrong expected reach answer; the node bound raised to 7 | **4 of 4 caught** |

What the 26 tests cover, in short: the pins; the inventory chain; fixture identity and reproduction; coverage of
every kind at 5 and 6 nodes; routes and refusals on every entry point; that every course question takes the old
route; malformed questions; that the old compiler refuses exactly the larger correspondence questions and matches
v2 byte for byte on everything else; the kind table; checker v2 gold versus the independent answers; the genuine
no-match and no-path cases; the same-degree pairs; the census numbers; decoding every correct answer from the slot
plan; decoding arbitrary scores into gradable answers; the syntax-tree comparison of `_graph` and `_graph_larger`;
the names the copy needs; the subclass's dispatch and training refusal; the step order of `predict_packet`; and that
the T4 script checks for CUDA before any work.

**Not checked locally, by rule:** anything with torch. `larger_question_learner.py` and `t4_larger_question_checks.py`
were never imported here: importing them loads the frozen course and torch.

## What must run on AWS (a T4 is enough)

```text
CAS_META2_RUN_TEACHING_CYCLE=1 python -B research/CAS_META_2_COMPOSITION/eval_paths/t4_larger_question_checks.py --out larger_path_result.json
```

- Forward passes only, under `torch.no_grad()`. No optimizer step. No checkpoint written. Wall limit 3,600 s.
- About 8,100 forward passes in total: a = 6,768; b = 185; d = 1,165 (plus 4 informational ones in c).
- It needs, in the bundle: the `eval_paths/` folder; the six checkpoints
  `records/typed_pointer_001/receipt_{20260917,20260918,20260919}/checkpoints/{initial,final}.pt` (pinned by size
  and sha256 inside the script); the pinned course, tokenizer and development files; `cncm/`; `cas_meta2/`.
- The environment variable is the learner's own guard (`teaching_cycle/gpu_adapter.py:37-39`). Check d needs it
  and Linux. The script never sets it.
- Exit codes: 0 all pass; 1 a check failed or was not run; 2 `GPU_REQUIRED` (no torch or no CUDA; no CPU fallback);
  3 wall limit; 4 `SETUP_REFUSED`.

| Check | Passes only if |
|---|---|
| a `OLD_PACKET_PRESERVATION` | For all 6 Helm 2.0 checkpoints in a switch-OFF container, all 564 course questions take the old route, and the old steps and the new path give identical slot plans, identical float32 logit bits, and identical scores, decisions and answers (3,384 comparisons). It also writes each model's overall logit digest in `preservation_digest.py`'s format |
| b `FIXTURES_THROUGH_LEARNER` | All 37 answerable fixtures go read → forward → decode → checker v2 grade with no error, on 5 containers: the 3 trained Helm 2.0 finals (OFF), a fresh OFF and a fresh ON container |
| c `SEVEN_NODE_REFUSAL` | All 4 refusal fixtures raise their named refusal on a fresh OFF and a fresh ON container, and `GraphForward` is called 0 times |
| d `FULL_LEARNER_SUBCLASS` | Two fresh learners from seed 20260917, the original and the subclass, start identical and give byte-identical predictions on all 564 course questions with equal counters; the subclass answers all 37 fixtures; the original refuses F20 with `TYPED_PERMUTATION_BOUND`; the subclass refuses R01-R04 without moving a counter; both training calls are refused |

The program writes `INTEGRATION_CHECKS_PASS` only when all four checks ran and passed.

**Correct/incorrect flags are not written** in checks b and d. Only "graded, no error" and the checker's receipt
digest are written. These are plumbing checks, and a public fixture shape might coincide with a sealed TEST shape.

## Open questions and flags for the coordinator (not decided by the builder)

1. **Refusal reaches the whole bank.** A 7-node or degree-5 world anywhere in the source refuses the question, even
   a parts question about a 5-node focus. The checker would grade some of those. Keep this strict rule?
2. **Scope words for the "same code" kinds.** D-1 acceptance tested analogy and correspondence at 5-6 nodes, and
   reach, parts and edge account at 3-5 nodes only. It did not exercise definition, context or role questions at 5-6
   nodes, nor reach, parts or edge account at 6. Checker v2's code for these is the frozen checker's. Whether that
   counts as "within the accepted checker's scope" is the coordinator's call.
3. **The fixture shapes are now public.** Before check b runs, the custodian should compare S4, S5A, S5B, S5C, S6A,
   S6B and S6D with the sealed TEST shapes (HSET-1A `TEST_NEW_5`, and any HSET-2 TEST), and keep them out of HSET-2
   TEST. I cannot do this: I may not open sealed files.
4. **The pins include `pointer_contract.py`.** Any later edit to it, or to the other 11 files, stops this path until
   it is reviewed again. That is deliberate. It may surprise someone.
5. **Degree limit at 6 nodes.** HSET-2's generator must keep every degree at 4 or less, or those questions are
   refused. This follows D-1 spec S5.
6. **World-count input saturates.** Helm reads the world count as `min(count, 64) / 64` (`pointer_learner.py:1105`),
   so 64 and 65 worlds look the same. Harmless for answers. Recorded only.
7. **HSET-1A comparability.** For HSET-1A-style questions (5-node reach, parts, edge account), the new path gives the
   same slot plan as the old path. Results through either path are comparable.
8. **`CHANGELOG.md` and the CAS Harness spec sheet were not touched.** This follows the other builder commits in this
   takeover. The continuation log is the coordinator's.

## EXPOSURE: what I saw outside this worktree's own working files

**Loaded by the tool before I started (not opened by me).** The owner's global `CLAUDE.md`, the project `CLAUDE.md`
at `C:/Users/wakil/OneDrive/Desktop/tksCAS/CLAUDE.md`, and the auto-memory index `MEMORY.md`. The index names the
sealed-test archive folder and states sealed-build totals (for example "HSET-1A reach W=2"). It holds no TEST world,
record id, shape or answer.

**Read through git objects of `research/helm-integration-20260923` (`git show FETCH_HEAD:<path>`), not working files:**
- `_handoffs/HELM_NEXT_PHASE_20260923/OWNER_DIRECTION_20260924.md` (as instructed);
- `records/helm_eval_design_20260923/analogy_wiring_probe/preservation_digest.py` (as instructed);
- `records/helm_eval_design_20260923/hset1a/hset_worlds.py`, `BUILD_SPEC_v0_1.md`, `BUILD_SPEC_HSET1B_v0_1.md`
  (allowed). The two specs contain salt sha256 values (not salts) and TEST totals only. I did not read
  `hset1a_build.py` or `hset1b_build.py`;
- **outside the named list:** `records/helm_eval_design_20260923/d1_acceptance/D1_ACCEPTANCE_RESULT.md` (the D-1
  verdict, needed for "accepted scope"; it reports sealed items as counts only), and a `grep` for "S5"/"degree"
  lines of `_handoffs/HELM_NEXT_PHASE_20260923/D1_CHECKER_V2_SPEC_AND_ACCEPTANCE.md`;
- **file names only** (`git ls-tree`) of `records/helm_eval_design_20260923/` and of
  `_handoffs/HELM_NEXT_PHASE_20260923/`. That name list includes names under `hset1a_aws_job/results_attempt1/`.
  I opened none of them.

**Read through git objects of this branch, outside the sparse checkout:**
`records/typed_pointer_001/receipt_20260917/artifact_manifest.json` (file names, sizes, sha256), and the six
Helm 2.0 checkpoint blobs, hashed only (`git show ... | sha256sum`), never loaded. A `git grep -l` for the training
bank digest returned 5 file names; I opened none of them.

**Local machine, not project data.** `C:/Python314/python.exe` (3.14.0) with pytest 9.0.2; a lookup that found torch
installed in the user site-packages (not imported); the name of `~/venvs/cas-gpu`; free memory (about 337 MB of
16 GB). The tool saved one long `git grep` output to a file under `C:/Users/wakil/.claude/projects/.../tool-results/`;
I did not open it. Mutation-check scratch copies were written to the session scratchpad only.

**Not opened:** `D:/tksCAS-archive/`, any `*SEALED*` or `*sealed*` file, any `*_eval.jsonl`, any TEST output, any
`results/` folder, S3 or AWS, the meta1 ledger, other worktrees' files, and Claude transcripts.
