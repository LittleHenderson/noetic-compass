# A3 first report — teaching data and transfer

Immutable first submission, 2026-09-22. No peer first reports were read.

The held-world result tests reuse of familiar structures under different world identifiers. It does not establish transfer to new graph structures. All five held graphs have counterparts among actually trained focus worlds, even when the mapping must preserve the declared whole and participant-rank flags. The separate development set does introduce larger graphs, but also changes the answer balance sharply. These facts limit the transfer claim; they do not by themselves explain Helm 2.0's failed historical gate or prove a model limitation.

## Subject and evidence custody

- Helm 1.0: `af0970cfa6d54a85aeb16e5a99a84d791ace59c0`.
- Helm 2.0-experimental: `20208c923d41c24614504d4ecc2b289ecb66eda8`.
- Both versions: seeds `20260917`, `20260918`, `20260919`.
- Writing worktree: `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-failure-a3`; branch `codex/helm-failure-a3-20260922`; initial HEAD `59b1dd57e57648ab68c1cc26fbae95a957c20cd3`.
- Inputs were read only at the common manifest's q4-live receipt paths. Six config files, six source ZIPs, and six first-pass batch logs were checked against manifest SHA256 values. No checkpoint was opened or loaded.
- All six ZIPs contain byte-identical course, tokenizer, and compact development data. Their identities are below. This makes the data checks applicable to all six runs; it is one shared dataset, not six independent datasets.

| ZIP member | SHA256 |
| --- | --- |
| `records/typed_course_001/checks_002/public_course.json` | `cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987` |
| `records/typed_interface_001/checks_002/training_tokenizer.json` | `bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c` |
| `records/typed_matched_001/development_001/compact_development.json` | `5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4` |

`PROBE_RESULTS.json` contains exact paths, hashes, source excerpts with line numbers, class counts, and explicit graph mappings. `audit_teaching_transfer.py` reproduces the checks with Python's standard library and no project imports. The historical labels are unchanged.

## What was established

### 1. Identifiers are held apart; underlying structures are repeated

The public bank has 64 worlds: 12 with three nodes and 52 with four. Exhaustive enumeration of at most 24 node permutations per world gives only six directed graph shapes. Keeping the declared-whole flag and ordered participant ranks also gives six shapes. The trained registry uses 19 focus worlds; the held registry uses five.

| Held world prefix | Trained focus worlds with the same directed shape | Same count preserving whole/participant flags |
| --- | ---: | ---: |
| `world-22704554` | 2 | 2 |
| `world-28f61f2d` | 1 | 1 |
| `world-4090ec49` | 3 | 3 |
| `world-6e1fcbda` | 1 | 1 |
| `world-98c6352d` | 3 | 3 |

Concrete witness: held `world-22704554ac881d9846c94b37c5aabc5790edf38f7810692028f0b5e8ce8e4952` has edges `(n1,n3),(n2,n3),(n1,n0)`. Trained `world-00d90ef065fa389a45d42961c0d0d95403221772d942d64a61baadc61d92c3a2` has `(n2,n3),(n1,n3),(n2,n0)`. Renaming held nodes `n0->n0,n1->n2,n2->n1,n3->n3` preserves every edge. All five witnesses are in the raw result.

These are exact graph matches, not approximate degree signatures. They are not full model-input collisions: declaration text and world identifiers differ, and query marks were not included in this graph-only comparison. No contradictory-label or whole-model impossibility claim follows.

### 2. Held focus questions are excluded, but held graphs remain available as bank candidates

The split is 358 trained records, 127 held records, and 79 excluded records. These represent 189, 50, and 60 distinct query IDs respectively; excluded query IDs can overlap trained ones, so these query counts must not be added as disjoint sets. The full registry has 564 records but 244 unique queries. The stored base course has 1,152 presentations.

No trained record text refers to a held world. No held or excluded record appears in any inspected first-pass training log. This supports the focus-question exclusion.

However, `course._public` supplies all 64 worlds (course.py:86-87). The active reader keeps all worlds for `definition`, `context`, and `analogy` (pointer_inputs.py:384-392). `GraphForward` constructs blocks for every retained world (Helm 2 pointer_learner.py:1251, `_graph_blocks`:979-1042; Helm 1 call:1143, builder:883 onward).

There are 113 trained world-choice records: definition 36, context 41, analogy 36. Each inspected first pass presents world-choice tasks 441 times. On that code path, every one of the five held graphs is available as part of the bank. This contradicts a literal claim that the machine never read these worlds. It does not prove that their held-focus answers were used as targets, or that candidate exposure caused the observed result.

The registry contains 384 packets with three worked supports and 180 with none. No top-level main-answer/target field was found. The active pointer reader deliberately ignores `supports`, `cue`, and `instruction` and takes the query and public source. Worked supports should therefore not be counted as direct answer leakage into this reader merely because they appear in the packet. The split's removal of referring support records is still real.

### 3. Active batches are balanced by task kind, but repeat the same small question set

Every one of the six saved first-pass logs contains 147 batches and 1,176 presentations. Every batch has one record from each of the eight kinds. All six record orders match exactly, with canonical sequence SHA256 `037a5d63b59807db0ee95f9c10c2f795aa6681cf42d7e96157654bc8e51896ef`.

Each pass uses all 358 trained records and 189 distinct questions. A record occurs two to five times; a distinct query occurs two to eighteen times. Therefore task-kind starvation in an older unbalanced order is not an explanation of these first-pass runs. Equal kind counts do not imply equal losses, equal target classes, equal graph diversity, or retention; those require other evidence. This report verifies first-pass logs only. The six configurations each specify ten passes; subsequent pass logs were not replayed by A3.

### 4. The development set changes size and target balance together

The compact artifact contains **59** packets: 6 parts and 53 reach, over six new focus-world IDs. Five worlds have ten nodes and one has nine. It should not be described as six ten-node worlds or 60 questions. It has no focus-ID overlap with the 64-world bank; the node-count difference alone proves the focus graphs are not isomorphic to the three/four-node training graphs.

Independently derived reach labels, counted once per unique query:

| Population | ABSENT | DIRECT | VIA | Total |
| --- | ---: | ---: | ---: | ---: |
| Trained | 1 | 25 | 24 | 50 |
| Held | 1 | 5 | 8 | 14 |
| Development | 42 | 8 | 3 | 53 |

The implementation follows the source's direct-edge precedence and sorted-neighbor path rules (checker.py:129-153). This uses no learned outputs. The constant answer `{state: ABSENT, via: null}` agrees with 42/53 derived development reach answers. This is a computed label baseline, not a newly executed official learner comparison. State-only VIA accuracy is not exact-answer accuracy because the `via` node also matters.

All 19 unique trained correspondence questions and all five held correspondence questions have a valid mapping. These panels supply no NO_MATCH negative question. Training analogy queries each admit six or nine different-domain matching bank worlds; held analogy queries also admit six or nine. This is consistent with the checker accepting all exact directed isomorphisms, not one authored name pairing (checker.py:96-112,200-240).

Definition and context answers read declared facts; parts uses one outgoing adjacency row; edge_account copies the complete edge set (checker.py:169-195). Success on those tasks alone is not evidence of multi-step path learning. Those facts are available legitimately under the task definition; calling them hidden-label leakage would be incorrect.

## Interpretation, alternatives, and disproof

The strongest supported interpretation in A3's scope is narrow: the held panel reuses a small set of structures, and the larger development panel mixes size transfer with a substantial answer-distribution shift. Thus the stored evaluations do not isolate unseen-structure reasoning from familiar-structure reuse or answer-class effects.

The strongest alternative is that Helm learned a genuine transferable graph rule despite these easy repeated structures, and its misses instead arise from model updates, numerical behavior, answer selection, or the frozen gate's retention requirement. The data facts do not refute that alternative. They also cannot assign the exact historical failure cause; A3 did not reconstruct the gate.

A wrong mapping witness or a source/config mismatch would disprove the established overlap/exposure facts. Stable exact performance on prospective, size-matched but genuinely new structures with balanced labels would contradict the hypothesis that familiar structures or class balance explain most of the apparent transfer. No such fresh result is present in A3's evidence.

No concrete impossible labeling task or conflicting-label collision was proved. The raw public graph contains the facts needed for the checked parts, edge, reach, and matching semantics. Whether the neural representation loses a needed distinction remains open. Removing the explicit rank feature does not remove list order or lexical tie rules; all six configs have `node_rank_feature: false`, so an explanation relying on an active explicit rank feature would use the wrong configuration.

## Smallest useful next check

**Permitted, not run by A3:** join each saved initial/final development prediction to the 53 independently derived reach labels; report exact correctness separately for the 42 ABSENT, 8 DIRECT, and 3 VIA cases, for every seed/version. Freeze the two predictions first: (a) apparent strength mainly comes from class balance, so the aggregate tracks ABSENT and weakens sharply on the 11 positive-path cases; (b) transferable graph reasoning contributes, so exact DIRECT/VIA answers also improve over initialization. This diagnostic can distinguish interpretations of the saved development scores without loading a model. It cannot establish a training cause.

**If a later authorized model test is needed:** hold graph size and label balance fixed while comparing familiar versus genuinely new structures, include node renamings and valid NO_MATCH correspondence negatives, and keep the prospective set outside development. A matched result would separate shape reuse from structure transfer more cleanly than adding another seed on this same course. This is a proposal, not an executed or authorized neural job.

## Execution, limits, and independence

- Python `C:/Python314/python.exe -B`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONIOENCODING=utf-8`; PowerShell 7 with login disabled and explicit workdir on every shell call.
- One stdlib diagnostic program, two actual executions, both exit 0, both under two seconds of measured program time. No formal test functions; no pytest/cargo/model/inference/training/GPU/cloud/API/install job. The second execution corrected a hardcoded count label from 60 to the actual `len(DEV['records'])=59`; calculated first-run results already said 59. The initial receipt remains preserved.
- Cases per execution: 64 bank graph cases; five held-overlap witnesses; 564 course records/244 distinct queries; 59 development packets; six source ZIP/config identities; six first-pass logs with 147 rows each. Repeated checks on identical data are not independent experiments.
- Read-only inspection output was occasionally truncated by tool limits; narrower reads recovered the required fields. No missing required data was encountered in this selected scope. Dollar cost and the remaining agent allowance were not measured by A3; this is not a claim of free agent work.
- Prior exposure: the common directive states earlier lineage opinions about repeated structures, shortcuts, and the failed retention gate. Historical source docstrings in practice_contract.py and pointer_contract.py also discuss these opinions. I read those while locating the actual split and input path. I did not read peer first reports, new peer findings, or lineage discussion files. The canonical graph check and label derivation are independent stdlib implementations, not copied historical audit results.
- Complete commands/inspection chronology are summarized in COMMANDS.md. Exact source excerpts and full evidence fingerprints are in PROBE_RESULTS.json. Raw source copies in `tmp/` are local inspection scratch and are not part of the report commit.
