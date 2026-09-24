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
against the fixtures. Revision 1 adds the coordinator's claim-status ruling to the table (see "Scope ruling" there).

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

These are the v0.1 hashes (commit `785c9bd1`). Revision 1 changed three files; see its file table.

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

**Superseded by Revision 1 below.** The check order, check a, the input list, the time limit handling and the
exit codes all changed. This section is kept as the record of v0.1.

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

**Corrected in Revision 1 (review F4).** No correct/incorrect field is written in checks b and d. But the earlier
sentence here ("only 'graded, no error' and the checker's receipt digest are written") was wrong. Right/wrong CAN be
recomputed from what is written: `answer_sha256` is the sha256 of the canonical answer, and the public fixture file
holds every correct value; `check_digest` is a digest over a receipt body that contains `correct`. Check b also
writes `logit_bits` and `admissible_answer_count`. These are public plumbing fixtures, so this is acceptable. This
recording scheme must never be used for sealed items.

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

---

# Revision 1 (2026-09-23): the changes the review asked for

- **Label: CLAUDE_BUILT_CLAUDE_CHECKED.** Written by the temporary Claude builder. Codex is away until 2026-09-28.
  Custody is not independent: Claude built the path, reviewed it, and revised it.
- Review: `REVIEW_LARGER_QUESTION_PATH_785c9bd1.md` (commit `cc68d8b3`). Verdict: CHANGES_REQUIRED.
- Parent commit: `cc68d8b3`. This revision is the commit that adds this section.
- **Status: BUILT, and checked statically on the laptop. The AWS T4 checks are still NOT_RUN.** Nothing ran with
  torch. No AWS call was made.
- Only `eval_paths/` and this report changed. No protected file was edited. The 12 source pins still hold.

## What changed, finding by finding

| Finding | Coordinator decision | What changed | Where |
|---|---|---|---|
| F1 (MAJOR) time limit | 1. order d, c, b, a; write each row as it completes | The checks always run d, c, b, a, whatever order is typed. Every finished row goes to a create-only rows file at once, flushed and fsynced | `t4_larger_question_checks.py`: `CHECK_ORDER` (line 78), `RowWriter` (304), `_publish` (323), `main` (801) |
| F1 | 3. timing preflight | About 20 timed forward passes project the total; above 3,600 s the run refuses before the main work | `planned_work` (453), `project_total` (472), `preflight` (486) |
| F2 history | 2. compare with the T4 item-1 digests | Check a now compares each checkpoint's overall digest with the digest the T4 job recorded | `T4_REFERENCE` (161), `T4_REFERENCE_OVERALL_DIGEST` (185), `check_a` (766) |
| F3 inputs | 4. `REQUIRED_INPUTS` and `--list-inputs` | Every input file is named with bytes and sha256, and checked before torch is imported | `REQUIRED_INPUTS` (112), `list_inputs` (238), `verify_inputs` (258) |
| F4 wording | 5. fix the wording | The script docstring, `BOUNDARY`, check b's note and this report now say right/wrong is recomputable | docstring; this report, end of "What must run on AWS" |
| F5 pins | 6. D-1 anchors inside `grade()` | `grade()` and `target()` check the route's checker pins on every call | `larger_question_scope.py`: `verify_grader_pins` (200), `grade` (288), `target` (313) |
| F6 scope | 7. write the ruling into the table | Two new columns in `KIND_SCOPE` | `larger_question_scope.py` (lines 101-168) |
| F7 raw inputs | 8. disclose | Disclosed below; check b now records the raw positions per fixture | `check_b` (709) |
| F8 switch | 8. disclose; add switch OFF to d if cheap | Check d now also runs a switch-OFF learner pair, on a subset | `_build_pair` (547), `_learner_pair` (569), `check_d` (642) |
| F9 exposure | note | Recorded in the exposure section below | this report |
| F10 wording | note | Answered below | this report |

Line numbers are those of the revised files in this commit.

## 1. Check order, and rows written as they finish (F1)

- **Order.** `CHECK_ORDER = ("d", "c", "b", "a")`. `--checks` only picks a subset. It cannot change the order.
  So check d (the subclass against the original learner) runs first and cannot be the check a wall stop cuts.
- **Rows file.** `<out>.rows.jsonl`, opened with exclusive create (`open(..., "x")`). One JSON line per finished
  unit: one line per model in check a, one per fixture and container in check b, one per refusal in check c, and in
  check d one per learner pair, per fixture and per refusal, plus the F20 and training-refusal lines. Each line is
  flushed and fsynced before the next unit starts.
- **Summary file.** `<out>`, written once: at the end, or at a stop. It is written to `<out>.partial` with
  exclusive create, then hard-linked to `<out>` (a hard link refuses to replace an existing file). The summary
  records the rows file's sha256 and the row count per check.
- **Create-only.** The run refuses at start (exit 4, `OUTPUT_EXISTS`) if `<out>`, `<out>.partial` or the rows file
  already exists.
- **At the wall limit.** The running check is marked `NOT_COMPLETE` with the number of rows it wrote; later checks
  are `NOT_RUN`; the verdict is `WALL_LIMIT_REACHED` (exit 3). Every finished row is already on disk.

## 2. Check a compares with the recorded T4 history (F2)

**Compared field.** `results[i].overall_digest` in the T4 item-1 job's files, for the row whose `checkpoint` is
`records/typed_pointer_001/receipt_<seed>/checkpoints/<phase>.pt` and whose `checkpoint_sha256` equals the pin. It
is compared with the `overall_digest` that check a computes from `predict_packet` on the same checkpoint.

**Source of the reference.** Commit `41071a3f1dd86ffbb00dbf07233c32dcea5e8a1b` on
`origin/research/helm-integration-20260923` (fetched explicitly; `FETCH_HEAD` was `91968e5d`). Folder
`records/helm_eval_design_20260923/analogy_repair_t4_job/results/`. Read with `git show` and `git cat-file`.

| File | sha256 |
|---|---|
| `preservation_OFF_T4_seed20260917.json` | `27f856d9f7d1d48bf220321d33e589910822850e4efedb6b5f5cb9f159d58890` |
| `preservation_OFF_T4_seed20260918.json` | `f36e44ead4d6759b11b0766fd3bf04d6ef58d6c75bf72c03d55ef9caa3482efa` |
| `preservation_OFF_T4_seed20260919.json` | `abc1ece79e195280bbaf4c597a72eb87b97f196974aa250b22153e75f72801cd` |
| `preservation_control_20208c92_T4_seed20260917.json` | `8ffa0ac95c21a16cdbd1c71ec8f68bb18b82dfbaa8ec340efef578231e841749` |
| `preservation_control_20208c92_T4_seed20260918.json` | `fff9e352b13c8120a8bf264e06169aab264cc86d175d5d53cd17f04dd96c18c2` |
| `preservation_control_20208c92_T4_seed20260919.json` | `24b006a5e711878ea5fb036a0a8c820d9e8ac510226840bb076ef5c89884890d` |

| Checkpoint | Recorded `overall_digest` (OFF file = control file) |
|---|---|
| seed 20260917, initial | `1aaa01da42a8f754470696a6b35b08ac876cead7f36e29e939ae0e720972ba0a` |
| seed 20260917, final | `949b371973745a0686537f9c9031451c9d3558a35e0b23c94b79ef5a23155806` |
| seed 20260918, initial | `47e4cfb267aec4f959388aa4c8a4d37d2d52b8c60d7b8d3afb33b8aca3ebd365` |
| seed 20260918, final | `5cede80f347b84b05a402e698417153076f3edd053daa32e008ce38f37a050a7` |
| seed 20260919, initial | `fc2412f665a98884399209c0d0d9b7fa28c56ed0a98786ab2eb196f0467be858` |
| seed 20260919, final | `62c188861902422664fcf59535d6b8011b34d7db5bcdb377ab95ce21fc00375a` |

- The OFF files come from the current source with the switch OFF. The control files come from the unchanged Helm
  2.0 source (`20208c92`). Their digests are equal for all six checkpoints. So the reference is also Helm 2.0's own
  T4 history.

**Why it is the same quantity.** I read the reference tool, `analogy_wiring_probe/preservation_digest.py` at
`41071a3f` (LF sha256 `21bf01e5411d3d959bd8106f8f6a7ca6ca158d97f4000c0b060d57e99176292e`, equal to the
`tool_sha256_lf` in all six files). Point by point:

1. Per question: sha256 of compact, sorted-key JSON `{slot_id: ["%08x" float32 bit patterns]}` of the head logits
   (tool lines 98-100). `larger_question_learner.logit_bits_digest` writes the same bytes.
2. Overall: sha256 of the newline-joined `"record_id digest"` lines over the sorted 564 record ids (tool line 101).
   `_overall_digest` in the script does the same.
3. Same logits: the tool runs `GraphForward(torch, model, reading, device).head_logits(plan, indicators)` with the
   plan from the frozen `slots.compile_slots`, the reading from `pointer_inputs.read_packet` and the same role
   indicators. On the old route, `predict_packet` calls exactly these.
4. Same container: `_build_container(torch, _framework(torch, device, seed), device,
   analogy_focus_comparison=False)` (the job's `--container-kwargs` for the OFF files), strict `load_state_dict` of
   `torch.load(..., weights_only=True)["model_state"]`, eval mode.
5. Same source: the OFF files record the LF sha256 of five files, and all five equal today's files (tested). They
   are `pointer_learner.py`, `pointer_inputs.py`, `pointer_contract.py`, `slots.py` (the same values as the scope
   module's pins) and `cncm/typed_matched_worker.py`
   (`51afa5e5ca908356c53381c30767b65ae9057c388aa2cc0b231fbb5be4dd6522`). Full values:
   `T4_REFERENCE_SOURCE_LF_SHA256`.
6. Same course (course digest `272c26e1391c65607d40ff7ae67522402f6a2af553478d32ea6daa0e8e706dbb`) and the same
   determinism settings (`CUBLAS_WORKSPACE_CONFIG=:4096:8`, deterministic algorithms, cuDNN deterministic).
7. Same torch build and GPU class. The reference ran torch `2.11.0+cu128` on a `g4dn.2xlarge` (Tesla T4). Bits can
   differ on other hardware or builds. So if check a is requested, the script refuses before any GPU work unless
   torch is `2.11.0+cu128` and the GPU name contains `T4` (`SETUP_REFUSED:T4_REFERENCE_ENVIRONMENT_DIFFERS`). It also
   refuses if one of the five source files differs (`T4_REFERENCE_SOURCE_DIFFERS`) or the course digest differs.

So it is the same quantity. The coordinator's fallback (a paired comparison on 2 checkpoints) is not needed, and
the paired old-versus-new comparison is gone. That halves check a (6,768 to 3,384 forward passes).

**What check a no longer shows, and where that is covered.** It no longer compares scores, decisions and answers of
two code paths side by side. On the old route those are fixed functions (the frozen `slots.score_decisions` and
`assemble_answer`) of the logits, which check a now pins to history. And check d compares full predictions (scores,
decisions, answer, prediction id) of the original learner and the subclass on all 564 questions.

**Locating a mismatch.** Check a writes all 564 per-question digests of each model to the rows file. They can be
compared line by line with the `per_record` maps in the committed reference files.

## 3. Preflight and expected wall time (F1)

**What the preflight does** (after setup, before any check):

- builds one fresh switch-OFF container, and runs 2 warm-up calls (not timed);
- times 16 course questions, each doing check a's work (`predict_packet` plus the logit digest);
- times 4 fixtures (F20, H01, F17, F24), each doing check b's work (`predict_packet`, the scope plan, answer
  validation, checker v2 grade, logit digest);
- if check d can run (Linux and the environment guard): builds the frozen encoder (kept for check d), builds one
  learner, runs 1 warm-up and times 3 learner predictions.

That is 20 timed container calls and 3 timed learner calls.

**The projection:** elapsed seconds so far + 1.15 x (the planned calls of every requested check x their measured
time per call, plus container and learner builds x their measured build time). Fixture calls by a learner are
estimated as the fixture time plus the learner's extra time. If the projection is above `WALL_SECONDS = 3600`, the
run stops with `PREFLIGHT_OVER_WALL_LIMIT` (exit 5). The preflight row, with every timing, is written first.

**Planned forward passes** (down from 8,122):

| Check | Calls |
|---|---|
| d | 1,270 learner calls on course questions (564 x 2 with the switch ON, 71 x 2 with it OFF), plus 74 on fixtures (37 x 2) |
| c | 4 informational old-path calls; the 8 refusals cost 0 |
| b | 185 (37 fixtures x 5 containers) |
| a | 3,384 (564 x 6 checkpoints) |
| total | 4,917, plus 26 in the preflight |

**Expected wall time: about 2,300 to 2,800 s (about 38 to 47 minutes), against a limit of 3,600 s. This is an
ESTIMATE, not a measurement.** Where the number comes from:

- The T4 item-1 job (the committed files above): each preservation job ran 1,692 forward passes in 820.13 to
  826.53 s, of which 168.51 to 169.98 s was loading the course. That is 0.384 to 0.389 s per forward pass. It was
  measured while three such jobs shared one T4 (`job.sh.template` starts them together), so a solo run may be faster.
- This script also re-reads, re-decodes and re-assembles each question (the reviewer measured about 0.06 s per call
  of this work on the laptop). So I assumed 0.39 to 0.49 s per course question, 0.05 s more per learner call,
  0.2 s more per fixture (grading), about 40 s of builds, and about 230 s of setup and preflight.
- Total: 230 + 4,917 x t + 160 s. That is about 2,307 s at t = 0.39 s and about 2,799 s at t = 0.49 s.
- **Break-even:** with the same ratios, the preflight refuses when a course question takes more than about 0.56 s.
  The real total at that speed would be about 3,160 s. So the 1.15 margin errs toward refusing early rather than
  being cut late.

## 4. The inputs the run needs (F3)

`python -B t4_larger_question_checks.py --list-inputs` prints this list as JSON. It reads no file, and imports no
torch and no project code (tested in a subprocess with torch blocked). Paths are relative to
`cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/`. All are committed git blobs; the three JSON
data files contain no CR byte. The material and wheel rows equal `worker_contract.MATERIAL`,
`matched_contract.DEVELOPMENT_PIN` and `worker_contract.WHEELS` (tested). Every row equals its git blob (tested by
streaming the blob through sha256; the checkpoints were hashed, never loaded).

| Path | Bytes | sha256 |
|---|---|---|
| `records/typed_course_001/checks_002/public_course.json` | 4,165,195 | `cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987` |
| `records/typed_interface_001/checks_002/training_tokenizer.json` | 447,140 | `bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c` |
| `records/typed_matched_001/development_001/compact_development.json` | 685,549 | `5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4` |
| `research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/casformer_reference-0.1.0-py3-none-any.whl` | 36,501 | `0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee` |
| `research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/cas_neural_cjt-0.2.0-py3-none-any.whl` | 221,994 | `6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9` |
| `records/typed_pointer_001/receipt_20260917/checkpoints/initial.pt` | 2,235,079 | `59dd46877bd7bf97dbb4059975051cc6102b374d5c387d3a183884048b71b004` |
| `records/typed_pointer_001/receipt_20260917/checkpoints/final.pt` | 3,670,007 | `c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb` |
| `records/typed_pointer_001/receipt_20260918/checkpoints/initial.pt` | 2,235,079 | `d3c6292f2c0d09e29952bfe353d47fff058741d42c0a8e8dbe7a80eaad8fd645` |
| `records/typed_pointer_001/receipt_20260918/checkpoints/final.pt` | 3,670,007 | `a6e72caac1fccbd994433a46684846f5a3de48683dcc6b5def5946b85ef20658` |
| `records/typed_pointer_001/receipt_20260919/checkpoints/initial.pt` | 2,235,079 | `93b84558c0123673eabcc462f68afe8ecb1537b598e297ee16f7a7458787ee9f` |
| `records/typed_pointer_001/receipt_20260919/checkpoints/final.pt` | 3,670,007 | `c83e0123643a2433e1650bd4898dc28865204fd3d03fbedd22910632caf7dec8` |
| `research/CAS_META_2_COMPOSITION/eval_paths/fixtures/larger_question_fixtures_v0_1.json` | 190,466 | `7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3` |

Also required, and named in the list:

- **Source trees**, shipped whole (`*.py`), as the training launcher ships them: `cncm` and
  `research/CAS_META_2_COMPOSITION/cas_meta2`. The protected files inside are pinned by the scope module, and the
  five reference files above are pinned for check a. The record keeps each tree's file count and digest.
- **The code under test**: `eval_paths/__init__.py`, `larger_question_scope.py`, `larger_question_learner.py`,
  `larger_question_fixtures.py`, `t4_larger_question_checks.py`. Not pinned (a file cannot pin itself); their LF
  sha256 goes into the record. `colour_refinement_census.py` is not needed on the T4.
- **Installed wheels**: modules `casformer` and `cas_cjt` must be importable, from distributions
  `casformer_reference 0.1.0` and `cas_neural_cjt 0.2.0` (the T4 item-1 job installed them with `pip --no-deps`).
- **torch** with CUDA; check a needs `2.11.0+cu128` on a T4. **Environment**: `CAS_META2_RUN_TEACHING_CYCLE=1` and
  Linux for check d.

**When the check happens.** First thing after the arguments, before `import torch`. A missing file is
`SETUP_REFUSED:INPUT_MISSING:<path>`; a wrong size or hash is `SETUP_REFUSED:INPUT_MISMATCH:<path>`; a missing tree
or wheel has its own name. All exit 4, with the summary written.

**New exit code.** 5 = `PREFLIGHT_OVER_WALL_LIMIT`. The others are unchanged: 0 all four PASS; 1 a check failed or
was not run; 2 `GPU_REQUIRED`; 3 `WALL_LIMIT_REACHED`; 4 `SETUP_REFUSED`.

## 5. What is written (F4)

- No correct/incorrect field is written anywhere.
- **But right/wrong can be recomputed.** `answer_sha256` is the sha256 of the canonical answer, and the public
  fixture file holds each question's correct values. `check_digest` is the checker's digest over a receipt body
  that contains `correct` (`checker_v2.py:292-299`). Check b also writes `logit_bits` and `admissible_answer_count`.
- These are public plumbing fixtures, so this is acceptable here. **This recording scheme must never be used for
  sealed items.** The same words are now in the script's docstring, in `BOUNDARY` and in check b's note.

## 6. Pins checked inside the grader (F5)

- New `verify_grader_pins(route)`. On the new route it checks the three D-1 ACCEPTED anchors (`checker_v2.py`,
  `answers_v2.py`, `slots_v2.py`). On the old route it checks the frozen `checker.py` pin.
- `grade()` and `target()` call it on every call, after the route and before the checker runs. A drifted file gives
  `LARGER_PATH_REFUSED:SOURCE_DRIFT:D1_ANCHOR:<file>` (or `LARGER_PATH_REFUSED:SOURCE_DRIFT:checker.py`).
- `grade()` now also returns `grader_pins_checked`.
- Cost: three small file hashes per call. Not measured on its own.

## 7. Scope ruling (F6)

The coordinator's ruling of 2026-09-23 is now in `KIND_SCOPE`, as two columns. I recorded it; I did not decide it.

| Kind | Claim status at 5 nodes | Claim status at 6 nodes |
|---|---|---|
| `role_set` | `OUT_OF_SCOPE` | `OUT_OF_SCOPE` |
| `definition` | `OUT_OF_SCOPE` | `OUT_OF_SCOPE` |
| `context` | `OUT_OF_SCOPE` | `OUT_OF_SCOPE` |
| `analogy` | `CHECKER_V2_D1_ACCEPTED` | `CHECKER_V2_D1_ACCEPTED` |
| `correspondence` | `CHECKER_V2_D1_ACCEPTED` | `CHECKER_V2_D1_ACCEPTED` |
| `parts` | `NOT_RULED_D1_X_COVERED_3_TO_5` | `DIAGNOSTIC_ONLY` |
| `edge_account` | `NOT_RULED_D1_X_COVERED_3_TO_5` | `DIAGNOSTIC_ONLY` |
| `reach` | `NOT_RULED_D1_X_COVERED_3_TO_5` | `CLAIM_BEARING_IN_HSET2_REACH_GOLD_CROSS_CHECKED_BY_INDEPENDENT_RULES` |

- 6-node reach is claim-bearing in HSET-2, because the HSET-2 build cross-checks every reach gold with independent
  rules. 6-node parts and edge account stay diagnostic only. Definition, context and role are out of scope.
- Analogy and correspondence: the ruling did not restate them. The table says what D-1 licensed: checker v2 for
  these kinds at 5 and 6 nodes.
- Parts, edge account and reach at 5 nodes: **no ruling was given.** The table says so, and says that D-1's extra
  check X covered 3 to 5 nodes. See open question 1.

## 8. Disclosures (F7, F8)

**Raw inputs past the trained range (F7).**

- `_query_vector` feeds the `whole` and `part` node positions to Helm as raw numbers
  (`pointer_learner.py:1102-1103`). Course focus worlds have at most 4 nodes, so the course only ever shows 0 to 3.
  A 5-node focus can show 4. A 6-node focus can show 5. Helm has never seen those values.
- Check b now records, per fixture, `query_whole`, `query_part` and `past_trained_query_range`, and lists the
  fixtures that pass the range. The count is measured on the T4, not here: the position comes from the reader's own
  node order, and computing it needs `pointer_inputs`, which loads the course.
- **One correction to the review.** The review says node rank is also a raw input when `node_rank_feature` is on
  (`:1056`). In the pinned design it is off: `pointer_contract.DESIGN["node_rank_feature"]` is `False`
  (`pointer_contract.py:896`). So in these containers only `whole` and `part` are raw positions.
- Already disclosed in v0.1: the world count is read as `min(count, 64) / 64`, so 64 and 65 worlds look the same.
- Any later larger-question result is shaped by this. It is not a defect of the path.

**Check d and the switch (F8).**

- v0.1 checked the subclass with the switch ON only. `PointerCourseLearner` always builds its container with the
  default, which is ON, and takes no argument to change it.
- Revision 1 adds a switch-OFF learner pair. For the two constructor calls only, the script replaces the module-level
  `pointer_learner._build_container` with a wrapper that passes `analogy_focus_comparison=False`. It restores the
  original in a `finally` block. No file is edited. Both learners' `module.analogy_focus_comparison` is read back
  and must be `False`. A torch-free test with fake learners checks both the switch and the restore.
- **The OFF pair is a subset:** every 8th sorted course question (71 of 564), all 37 fixtures, the 4 refusals, the
  F20 refusal and the training refusals. The ON pair still covers all 564. Why a subset: the full OFF pair would add
  about 1,128 learner calls (about 450 to 600 s) and push the estimate to about 2,900 to 3,400 s. The subset adds
  about 180 calls (about 80 to 100 s).
- What the OFF pair adds: the only switch-dependent code is inside `GraphForward` (the analogy step,
  `pointer_learner.py:1553`). The route and `_graph_larger` do not read the switch.

## 9. Small wording items (F10)

- "The old learner answered 7- to 10-node questions silently" was shown on the laptop only at the slot compiler and
  checker (fixture R01). Check c's informational rows will show it through the forward pass.
- The reviewer's hand count closes my caveat about isolated nodes: at most 24 self-maps (for example one edge and 4
  isolated nodes). I did not re-derive it. Open question 4 names one case the count may not cover.
- The stale comment at `pointer_learner.py:54-57` and `:207-210` stays unedited (protected file).

## 10. What I checked on the laptop (static only; no torch)

| Check | Result |
|---|---|
| `python -B -m pytest -q -p no:cacheprovider eval_paths/tests/test_larger_question_path_static.py` | **36 passed in 76.60 s** (an earlier run, before one last preflight edit: 36 passed in 99.80 s) |
| Same tests by plain `python -B eval_paths/tests/test_larger_question_path_static.py` | **36 passed, 0 failed** (on the final files) |
| `python -B t4_larger_question_checks.py --list-inputs` | prints the list; exit 0; no torch and no project module imported |
| Syntax of the three changed files (`compile`, no bytecode written) | all pass; all LF |
| In-memory mutation check (scratchpad script; nothing on disk changed) | **8 of 8 caught**: order a,b,c,d; `grade` skipping the anchors; one wrong reference digest; margin 1.0; OFF stride 4; one wrong checkpoint pin in the input list; 6-node parts made claim-bearing; a switch substitute that is not restored |

New tests (10), and one rewritten:

- `test_t4_script_fails_closed_without_cuda_before_any_work` (rewritten): the order in `main` is list-inputs,
  create-only check, rows file, input check, `import torch`, both `GPU_REQUIRED` exits, the reference environment
  check, `Context`, preflight, preflight refusal, then the checks.
- `test_t4_runs_the_checks_in_the_order_d_c_b_a`.
- `test_t4_outputs_are_create_only_and_flushed_row_by_row` (real files in a temporary folder: rows are readable
  before close; a second writer and a second publish both refuse).
- `test_t4_required_inputs_name_every_file_with_its_pin`.
- `test_t4_list_inputs_needs_no_torch_and_no_project_code`.
- `test_t4_verify_inputs_refuses_a_missing_or_changed_file_by_name`.
- `test_t4_preflight_plan_and_projection`.
- `test_t4_check_d_switch_off_pair_uses_a_scoped_restored_substitute`.
- `test_t4_reference_digests_equal_the_committed_t4_item1_job` (re-reads the six files and the tool from commit
  `41071a3f`; checks every sha256, OFF = control, the digest formats, and today's source against the reference).
- `test_grade_and_target_check_the_grader_pins_on_every_call`.
- `test_kind_scope_records_the_coordinator_claim_ruling`.

**Not checked locally, by rule:** anything with torch. The T4 script's `main`, `Context`, the preflight and the
four checks were read and reviewed by eye, never executed.

## 11. Files after Revision 1 (all LF)

Under `research/CAS_META_2_COMPOSITION/eval_paths/`:

| File | Bytes | sha256 | Changed? |
|---|---|---|---|
| `__init__.py` | 393 | `38a1d4f57995cd43b5a0ed1616b2e941726327abed0919f3d8ce7a793f1e0ae4` | no |
| `larger_question_scope.py` | 18,619 | `409095a536c7eaaf31573e5a2ac4354f5e109ac5ac3c8d828ed3532cc73b3ee9` | yes |
| `larger_question_learner.py` | 7,852 | `82e963a4b30b2aab8a8cb7371faaca32b66c011a90bece59d1f9106a7bd7d35d` | no |
| `larger_question_fixtures.py` | 32,130 | `567331464043e7fdb4edffc1dc056f266c75141c312fecdca43d10dff3c3e86d` | no |
| `fixtures/larger_question_fixtures_v0_1.json` | 190,466 | `7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3` | no |
| `colour_refinement_census.py` | 5,295 | `dbf9d01f41946349bf853ec51b9d3a279b8194a0914758075212337ffe4cbb5f` | no |
| `t4_larger_question_checks.py` | 54,273 | `4d2bdbbf5907860e65696853513430bf0a4516dc46250533e94f2a28e77d72f7` | yes |
| `tests/test_larger_question_path_static.py` | 41,492 | `8da93c3d5de5c820214c28d92164dc64383c6afd8b09ecdd84ea7a6a55027164` | yes |

## 12. Command for the T4 (not run)

```text
python -B research/CAS_META_2_COMPOSITION/eval_paths/t4_larger_question_checks.py --list-inputs
CAS_META2_RUN_TEACHING_CYCLE=1 python -B research/CAS_META_2_COMPOSITION/eval_paths/t4_larger_question_checks.py --out larger_path_result.json
```

Outputs: `larger_path_result.json` (the summary) and `larger_path_result.json.rows.jsonl` (the rows). The program
writes `INTEGRATION_CHECKS_PASS` only when all four checks ran and passed.

## 13. Claim status of this revision

- **REAL (measured on the laptop, torch-free):** 36 of 36 tests pass; 8 of 8 mutations caught; `--list-inputs` runs
  without torch; the six T4 reference files re-read from git objects, with OFF = control on all six checkpoints;
  every required input equals its git blob.
- **ESTIMATED, not measured:** the T4 wall time (about 2,300 to 2,800 s).
- **NOT_RUN:** all four T4 checks and the preflight.
- **NOT LICENSED:** any statement about Helm's accuracy on larger questions.

## 14. Open questions for the coordinator (not decided by the builder)

1. **5-node parts, edge account and reach.** The ruling covered 6 nodes. The table says `NOT_RULED` at 5 nodes.
   Should they follow D-1's extra check X (claim-bearing), or stay diagnostic?
2. **The launcher is not written.** The T4 image must have torch `2.11.0+cu128` for check a, and both wheels
   installed with `--no-deps`. Otherwise check a refuses (by design), and the run must drop it with `--checks d,c,b`.
3. **Size of the switch-OFF pair in check d.** 71 course questions. If the coordinator wants all 564, set
   `D_OFF_COURSE_STRIDE` to 1 and expect about 450 to 600 s more; the preflight then decides whether it fits.
4. **A world with no edges.** The world validator (`source.py:232-255`) does not visibly require an edge. If a 5- or
   6-node world with no edges is legal, it has 120 or 720 self-maps, above checker v2's 64-answer cap. Grading
   would then refuse by name (`GRADER_OUT_OF_SCOPE:TYPED_CHECKER_TARGET_SET_BOUND`). Not tested. The HSET-2
   generator should state whether it can emit such a world.
5. **Preflight margin.** 1.15. It can refuse a run that would have fitted (see the break-even above). The
   coordinator may change it.
6. **F9 exposure items of the v0.1 build** (below) need the coordinator's confirmation against that build's brief.

## EXPOSURE (Revision 1): every file outside my working copy that I opened, and what else I saw

My working copy is `D:/tksCAS-worktrees/helm-builder`.

**Loaded by the tool before I started (not opened by me).** The owner's global `CLAUDE.md`, the project `CLAUDE.md`
at `C:/Users/wakil/OneDrive/Desktop/tksCAS/CLAUDE.md`, and the auto-memory index `MEMORY.md`. The index names the
sealed-test archive folder and states sealed-build totals (for example "HSET-1A reach W=2"). It holds no TEST world,
record id, shape or answer.

**Read through git objects of commit `41071a3f` on `origin/research/helm-integration-20260923`** (fetched explicitly,
as instructed), not working files:

- the six files `records/helm_eval_design_20260923/analogy_repair_t4_job/results/preservation_OFF_T4_seed<seed>.json`
  and `.../preservation_control_20208c92_T4_seed<seed>.json` (as instructed). Through a Python filter I printed
  their top-level fields, GPU admission fields, wall and load seconds, source pins, and each model's label,
  checkpoint, checkpoint sha256, overall digest and record count. The per-record maps were parsed; I printed only
  their size and 3 sample record ids (public course ids). The new test re-reads these six files;
- `records/helm_eval_design_20260923/analogy_wiring_probe/preservation_digest.py` (whole file; the reference tool);
- `records/helm_eval_design_20260923/analogy_repair_t4_job/job.sh.template` (`grep`s for the preservation,
  container-kwargs, pip and wheel lines) and `launch.py` (a `grep` for the torch version, the instance type and the
  package names);
- file names only: `git show --stat` and `--name-only` of `41071a3f`, and `git ls-tree` of `analogy_repair_t4_job/`
  and `analogy_wiring_probe/`, with `results/` names filtered out of the second listing. The first listing named
  every file in `analogy_repair_t4_job/results/` (logs, `STATUS`, probe JSONs, `results.tar.gz`). I opened only the
  six preservation files.

**Read through git objects of this branch, outside the sparse checkout:** the course, tokenizer and development
files, the two wheels and the six Helm 2.0 checkpoints, hashed only (`git cat-file -p ... | sha256sum`), plus a CR
and LF byte count of the three JSON files. Contents were not interpreted. The new tests stream the same blobs
through sha256.

**Read in the working copy (protected source, unedited):** `pointer_learner.py` (lines 636-660, 700-760, 1040-1060,
1092-1110, 1751-1990, plus `grep`s), `worker_contract.py` (lines 20-60 and 100-160), `pointer_contract.py`,
`practice_contract.py` and `matched_contract.py` (`grep`s for material and inventory lines), `pointer_inputs.py`
(lines 301-321, 339-345, 398-420), `encoder.py` (lines 216-230), `teaching_cycle/gpu_adapter.py` (lines 30-45),
`graph_teaching/real_framework.py` (lines 40-80), `source.py` (lines 95-125 and 225-262), `course.py` (lines 70-82),
`cncm/typed_matched_worker.py` (lines 43-49), and the import lines of `course_plan.py`. One `grep -rn` for
`real_framework` over the `.py` files of `cncm/` and `cas_meta2/`, and a names-only `find` for non-Python files
there (5 names printed). A names-only `find` showed that no file under those two trees has "sealed" in its name and
none is an `*_eval.jsonl`.

**Written outside the working copy:** the session scratchpad only: a copy of the reference tool
(`preservation_digest_41071a3f.py`), the mutation script (`mutation_check_rev1.py`) and this section's draft. The
tests wrote and deleted temporary files in the system temp folder.

**Local machine, not project data:** `python` 3.14.0 and pytest 9.0.2; `git sparse-checkout list`;
`git config core.autocrlf` (false).

**F9: exposure items of the v0.1 build, recorded as the review asks.** The v0.1 builder ran a repo-wide
`git grep -l` for the training bank digest, and a second long `git grep` whose output the tool saved to a file. A
repo-wide `git grep` reads the contents of every tracked file, including any `*sealed*`, `*_eval.jsonl` or `hset1a`
path, unless pathspecs exclude them. The v0.1 report does not say they were excluded. Only file names came back.
The v0.1 builder also read three files under `records/helm_eval_design_20260923/hset1a/`, and saw file names under
`hset1a_aws_job/results_attempt1/`. I cannot tell whether that build's brief allowed these; the coordinator should
confirm. I did not repeat any of it.

**Not opened:** `D:/tksCAS-archive/`, any `*SEALED*` or `*sealed*` file, any `*_eval.jsonl`, any path containing
`hset1a` or `hset1b`, any salt, S3 or AWS, the meta1 ledger, other worktrees' files, and Claude transcripts. No torch
import, no GPU, no training.

---

# Revision 2 (2026-09-23): two notes from the verification of e21472a8

- **Label: CLAUDE_BUILT_CLAUDE_CHECKED.** Written by the temporary Claude builder. Custody is not independent:
  Claude built, reviewed, verified and revised this path.
- Parent commit: `0cdd1a7b` (the verification, verdict APPROVE_FOR_T4_CHECKS, notes V1-V5).
- Asked for: V1 (a code fix) and V4 (the coordinator's ruling, written into the table). V2 needs no change (the
  preflight measures the real speed). V3 (thread settings) and V5 (the launcher) belong to the AWS job folder
  `larger_question_t4_job/` on `research/helm-integration-20260923`, not to this branch.
- Only `larger_question_scope.py`, the torch-free test file and this report changed. `t4_larger_question_checks.py`
  did not change. No protected file changed. The 12 source pins still hold.
- **Status: BUILT, checked statically on the laptop. The AWS T4 checks are still NOT_RUN.** Nothing ran with
  torch. No AWS call was made from this branch.

## R2-1. V1: the grader now pins the four helper files too

In plain words: both checkers run code from four more files while grading. Before, `grade()` checked only the
checker's own files. Now it checks all of them, on every call.

- New `SHARED_GRADER_FILES = ("answers.py", "focal.py", "source.py", "course.py")` in `larger_question_scope.py`.
  Their pins are read from `PROTECTED_SOURCE_LF_SHA256` at call time. An import-time guard refuses the module if a
  name is missing from that table or overlaps the D-1 anchors (`LARGER_PATH_GRADER_PIN_TABLE`).
- `verify_grader_pins(route)` checks, in this order: the route's checker files (the three D-1 anchors on LARGER;
  the frozen `checker.py` on ORIGINAL), then the four shared files, **on both routes**. Why both: `checker.py` and
  `checker_v2.py` both import `answers`, `focal` and `source`, and `grade()` calls `course.validate_model_packet`
  on both routes.
- Refusal names: a drifted D-1 anchor is `SOURCE_DRIFT:D1_ANCHOR:<file>` (unchanged). A drifted shared file is
  `SOURCE_DRIFT:<file>`, for example `LARGER_PATH_REFUSED:SOURCE_DRIFT:focal.py`.
- `grade()` now returns 7 names in `grader_pins_checked` on LARGER and 5 on ORIGINAL.
- Cost: four more small file hashes per `grade()` or `target()` call. Not measured on its own.
- **Not covered, recorded as a note:** `course.py` imports `course_plan.py` at module load. `course_plan.py` is not
  in `PROTECTED_SOURCE_LF_SHA256`, so it is not pinned here. `validate_model_packet` does not call it (I read lines
  295-330 of `course.py`). The T4 run still ships and records the whole source tree's digest. See open question R2-A.

## R2-2. V4: the 5-node ruling, and the claim words are local labels

In plain words: the coordinator ruled that at 5 nodes, parts, edge account and reach are diagnostic only. I wrote
that into the table, with the reason. I also wrote into the table that its claim words are its own labels, not the
spec sheet's.

| Kind | Claim status at 5 nodes | Claim status at 6 nodes | Changed? |
|---|---|---|---|
| `role_set`, `definition`, `context` | `OUT_OF_SCOPE` | `OUT_OF_SCOPE` | no |
| `analogy`, `correspondence` | `CHECKER_V2_D1_ACCEPTED` | `CHECKER_V2_D1_ACCEPTED` | no |
| `parts` | `DIAGNOSTIC_ONLY` (was `NOT_RULED_D1_X_COVERED_3_TO_5`) | `DIAGNOSTIC_ONLY` | 5 nodes |
| `edge_account` | `DIAGNOSTIC_ONLY` (was `NOT_RULED_D1_X_COVERED_3_TO_5`) | `DIAGNOSTIC_ONLY` | 5 nodes |
| `reach` | `DIAGNOSTIC_ONLY` (was `NOT_RULED_D1_X_COVERED_3_TO_5`) | `CLAIM_BEARING_IN_HSET2_REACH_GOLD_CROSS_CHECKED_BY_INDEPENDENT_RULES` | 5 nodes |

- **The reason, as the coordinator gave it** (recorded, not re-derived by me): HSET-1A measured reach W = 2 on
  TEST_NEW_5, and the parts and edge-account bars read the answer off the input. I did not open any HSET-1A file to
  check this.
- The `d1_acceptance_coverage` column still says `X_HSET1A_AT_3_TO_5_NODES_ONLY` for these three kinds. That column
  is about the CHECKER. The claim-status columns are about what a Helm score may claim. The comment above the table
  now says this.
- Every row has two new keys:
  - `claim_status_basis`: which ruling set the row, in words (F6, V4, or the D-1 scope for analogy and
    correspondence);
  - `claim_status_vocabulary`: `LOCAL_LABELS_NOT_THE_SPEC_SHEET_LEGEND`.
- The comment above the table says the words `OUT_OF_SCOPE`, `DIAGNOSTIC_ONLY`, `CHECKER_V2_D1_ACCEPTED` and
  `CLAIM_BEARING_IN_HSET2_...` are local labels. They are **not** the claim-status legend of
  `docs/CAS_HARNESS_SPEC_SHEET.md` (REAL / VALIDATED / LICENSED / NOT LICENSED / GREY / VACUOUS / WITHDRAWN /
  ENGINEERED-NOT-VALIDATED / FLAG_FOR_HUMAN_REVIEW). A person must map them to that legend before any of them
  enters the spec sheet.
- This answers open question 1 of Revision 1.

## R2-3. What I checked on the laptop (static only; no torch)

| Check | Result |
|---|---|
| `python -B -m pytest -q -p no:cacheprovider eval_paths/tests/test_larger_question_path_static.py` (from `research/CAS_META_2_COMPOSITION`) | **37 passed in 50.82 s** on the final files (an earlier run, before one docstring edit: 37 passed in 49.32 s) |
| `python -B t4_larger_question_checks.py --list-inputs` | exit 0 (file unchanged) |
| Syntax of the changed files; line endings | both parse; both LF only; no new line over 120 characters |
| In-memory mutation check (scratchpad script `mutate_r2.py`; nothing on disk changed) | **7 of 7 caught**: shared files not checked; shared files checked on LARGER only; 5-node reach left `NOT_RULED`; 5-node parts made claim-bearing; a spec-sheet legend word (`LICENSED`) used; the vocabulary note dropped; a basis without the V4 reason |

Tests changed or added (36 -> 37):

- `test_grade_and_target_check_the_grader_pins_on_every_call` (updated): LARGER returns the 3 anchors plus the 4
  shared files; ORIGINAL returns `checker.py` plus the 4 shared files.
- `test_grader_pins_also_cover_the_files_both_checkers_run` (new): reads each checker's relative imports with
  `ast` and requires every imported project file (and `course.py`, and the checker itself) to be pinned for its
  route; then makes each shared pin wrong in turn and requires `SOURCE_DRIFT:<file>` from `grade` and `target` on
  both routes; then grades once with the true pins. The four names are written in the test independently of the
  module.
- `test_kind_scope_records_the_coordinator_claim_ruling` (updated): the new 5-node words; no `NOT_RULED` left; the
  V4 reason in the three rows; `claim_status_vocabulary` on every row; no claim word equal to a spec-sheet legend
  word; the "local labels" comment present.

## R2-4. Files after Revision 2 (all LF)

Under `research/CAS_META_2_COMPOSITION/eval_paths/`:

| File | Bytes | sha256 | Changed? |
|---|---|---|---|
| `__init__.py` | 393 | `38a1d4f57995cd43b5a0ed1616b2e941726327abed0919f3d8ce7a793f1e0ae4` | no |
| `larger_question_scope.py` | 22,424 | `a09a172510b2f5ad1dd2ba2bc56d6cd46f354b619264bac90d18aa06748f9f32` | yes |
| `larger_question_learner.py` | 7,852 | `82e963a4b30b2aab8a8cb7371faaca32b66c011a90bece59d1f9106a7bd7d35d` | no |
| `larger_question_fixtures.py` | 32,130 | `567331464043e7fdb4edffc1dc056f266c75141c312fecdca43d10dff3c3e86d` | no |
| `fixtures/larger_question_fixtures_v0_1.json` | 190,466 | `7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3` | no |
| `colour_refinement_census.py` | 5,295 | `dbf9d01f41946349bf853ec51b9d3a279b8194a0914758075212337ffe4cbb5f` | no |
| `t4_larger_question_checks.py` | 54,273 | `4d2bdbbf5907860e65696853513430bf0a4516dc46250533e94f2a28e77d72f7` | no |
| `tests/test_larger_question_path_static.py` | 45,405 | `9f0be6d35e11a65623ef12ae035e73ce2630903a0a93421018cd43668f449c97` | yes |

## R2-5. Claim status of this revision

- **REAL (measured on the laptop, torch-free):** 37 of 37 tests pass; 7 of 7 mutations caught; `--list-inputs`
  exit 0.
- **NOT_RUN:** all four T4 checks and the preflight.
- **NOT LICENSED:** any statement about Helm's accuracy on larger questions.

## R2-6. Open questions for the coordinator (not decided by the builder)

- **R2-A. `course_plan.py`.** Imported by `course.py`, not pinned by this path, not called by grading. Pin it too
  (it would need adding to `PROTECTED_SOURCE_LF_SHA256`, which widens `verify_source_pins`), or leave it?
- Revision 1 questions 2 to 6 stay open as written. Question 2 (the launcher) is being answered by the job folder
  `larger_question_t4_job/` on `research/helm-integration-20260923`, which is written but not reviewed or run.

## EXPOSURE (Revision 2): every file outside my working copy that I opened, and what else I saw

My working copy is `D:/tksCAS-worktrees/helm-builder`.

**Loaded by the tool before I started (not opened by me).** The owner's global `CLAUDE.md`, the project `CLAUDE.md`
at `C:/Users/wakil/OneDrive/Desktop/tksCAS/CLAUDE.md`, and the auto-memory index `MEMORY.md`. The index names the
sealed-test archive folder and states sealed-build totals (for example "HSET-1A reach W=2"). It holds no TEST world,
record id, shape or answer.

**Read in the working copy:** the verification section of the review (through `git show 0cdd1a7b`), this report's
Revision 1 section, `larger_question_scope.py` (whole), the test file (parts), `grep`s of
`t4_larger_question_checks.py`. Protected source, unedited: the import lines of `checker.py`, `checker_v2.py`,
`answers_v2.py`, `slots_v2.py`, `course.py`, `answers.py`, `focal.py`, `source.py`; `course.py` lines 295-330 and a
`grep` for `course_plan.`.

**Written outside the working copy:** the session scratchpad only: `patch_scope.py` (a text patch of the table),
`mutate_r2.py` (the in-memory mutation check) and this section's draft.

**Not opened:** `D:/tksCAS-archive/`, any `*SEALED*` or `*sealed*` file, any `*_eval.jsonl`, any path containing
`hset1a` or `hset1b`, any `results/` folder by me (the existing test re-reads six committed T4 preservation files
from git objects of `41071a3f`, as in Revision 1; nothing from them was printed), any salt, S3 or AWS, the meta1
ledger, and Claude transcripts. No torch import, no GPU, no training.
