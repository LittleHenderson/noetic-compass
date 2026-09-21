# Helm and the CAS expression space — a grounded review of the owner's proposal

**Date:** 2026-09-20. **Status:** design opinion, not a result. Nothing was run on a GPU, nothing
was changed in Helm, no claim is promoted.
**Method:** four read-only explorers over the repo (the SDG, CCDL/PCBA, the 40/28 in code, Helm's
input doors), then three adversarial critics told to break the proposal, run twice — once on the
first wording, once on the owner's clarification. Seven agents, ~1.2M tokens, $0.
**The proposal, verbatim:** organise Helm's embeddings and weights by the 40 Elements, 28
Foundations and CAS expressions "so each vector would be some kind of CAS notation"; training
inputs "translated into CAS by CAS SDG"; "even CAS PCBA components and boards matched with via
training their weights to match and reflect them."
**The clarification, verbatim:** "It would just be the 40 Elements but the infinite expressions
and notations that CAS consists of."

---

## The one-paragraph answer

**Right instinct, wrong layer.** Organising Helm around the CAS expression language is the
correct direction, and the compositional clarification is what makes it correct — a finite
40-slot scheme would be the lookup table that already memorised. But the language belongs on the
**output** side (a decoder that must round-trip) and in the **registry** (what each weight group
is certified to compute), never in the **inputs** and never as a claim that a float vector *is* a
notation. Put it in the inputs and the compiler becomes the mechanism-free baseline and scores
the ceiling; the certified-gate problem (a no-learning rule at 11 of 18) returns, now perfect.
The SDG cannot do the translation step in the direction the proposal needs. The PCBA idea is the
best part of the whole thing — a board really is a new *kind* of world — but only if Helm gets a
relation-typed door, and not as "weights matching components", which has no mechanism to test.

---

## What the repo actually contains (grounded, with paths)

### The SDG runs the other way

`cas-synthetic/` picks a CAS expression **first**, at random from the grammar, then writes English
from YAML phrase banks to fit it (`generator/v74_baseline.py:46-88`, `generator/base.py`
"Template-first"). Every emitted expression is checked by `api/notation/compiler.py::
compile_expression`. A real record, `data/level2_scaffold/level2_full_10k.jsonl` line 1: English
prompt about a data scientist → `cas_expression "^2^O_{F3}|T"`.

It does **not** read an idea and emit CAS. The only English→CAS lanes are:
- `scripts/generate_stage4b_pilot.py` — asks **Claude Haiku** to propose the expression; the
  compiler checks syntax only. A foreign model's answer.
- `scripts/sfe.py` — says of itself: "It is NOT a full CAS parser — it cannot reconstruct the
  source CAS from English."
- Path D Wave 3 phase-1 `english_to_cas` was found to be **"100% verbatim copy"**
  (`generate_path_d_wave3_v2.py:14-18`); v2 added an anti-copy validator.

So "translate training inputs into CAS with the SDG" would hand back the seed the English was
generated from — the answer, written into the input. The owner-ratified rule already on record:
**"Foreign questions can broaden CAS. Foreign answers cannot define CAS."**

### The compositional language exists in code, and it round-trips — as strings

- A frozen 388-token vocabulary, `cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json`:
  `^0`–`^9`, `^P ^C ^E ^O`, `F1`–`F7`, `|T |A |f |E` and the `|⟨` set opener, all 40 compound
  states as single tokens (ids 213–252), `+ − × ∘ → ← ↔ ∈ ∉ ⊂ ⊆ ∪ ∩ ∖ ∅`, `Θ Ω Λ κ ι η`, 12 named
  Ω targets, meta-logic set names, fractal keywords. `decode(encode(expr)) == expr` is a passing
  test (`cas-native/tests/test_tokenizer.py:20`).
- Fixed operators already in code: composition `(i + j) % 10` (`cas-native/model/composition.py:20`,
  matching `cas-engine/src/ontology/operators.rs:103`); involution pairs; domain order.
- **Nothing decodes a vector back to a compound expression.** Only argmax to one of 40 states
  exists (`compiler.py:1183 _state_key`, `StateValue.dominant_state()`, Rust `from_linear_index`,
  axis-wise argmax heads in `cas-native/model/structured_prediction.py:223-227`).
- **Two coordinate systems for the 40:** tokenizer ids are Noetic-major (`^0^P=213, ^0^C=214…`);
  Rust `linear_index` and `compiler._state_index` are domain-major (`P0=0 … C0=10 … O9=39`).
- **Two definitions of the 28:** 7 Drives × 4 **Domains** (`drives.rs:5`, `CLAUDE.md`, display
  `F2-C`) versus 7 Drives × 4 **Registers** (`docs/reference/tks_28_foundations_translation_key.md:5`,
  `cas-native/belief/tks28_foundations.py`, `F2|A`). No 28-row embedding exists anywhere.
- One existing typed embedding: `StructuredTokenEmbedding` fuses a vocab id with a 25-float axis
  signature (10 + 4 + 7 + 4) per token (`cas-native/tokenizer/structured_token.py:35-66`).

### Helm has three input doors, and none carries a word

`pointer_inputs.read_packet` → `pointer_learner.py`:
1. **Node row, 18 numbers** (`_graph_blocks`, lines 1008-1017): is_declared_whole, is_participant
   rank, is_primary_label, is_whole_argument, is_part_argument, is_focus, is_target, a constant,
   then in-degree and out-degree one-hots. Used **once** by `node_encode` to seed the state; the
   8 rounds then read states only (Helm 2.0). Design rule, `pointer_inputs.py:31-37`:
   **"NODE IDENTITY IS THE REGISTERED RANK, AND NO WORDS."**
2. **`declaration_table`, 1024 × 64.** Not a hash: per reading, per field, the distinct tokens are
   sorted and each takes its **sorted position** as its row — "a position bucket, not a stable
   identity" (lines 1196-1213). A field vector is the **sum** of its token rows. This is the table
   that is 41.5% of Helm 1.0 and memorised: `analogy` 0.42 train, **0.00 held-out**.
3. **Query vector, 21 numbers** (`_query_vector`, 1045-1061): 8 kind one-hot, 9 rule one-hot,
   whole rank, part rank, is_target, world_count.

The frozen encoder (3829 × 64) is carried on the object and **never called**. Every injection
door changes `state_dict` shapes; `restore_checkpoint` is `strict=True`; so any of them is a new
run identity, not a patch.

### A CCDL board is genuinely more than a Helm world

`book/CAS_PCBA_Engineer/Appendix_C_CCDL_Language_Reference.md`: "A CCDL file is a netlist"
(line 19). Connection is by shared node name (line 232). A CJT takes three **typed ports**,
`cause | bias => effect`, and `|` and `=>` are "not interchangeable" (line 269). Four edge kinds:
`->` wire, `=>` produces, `feedback`, `via` (vias must run P→C→E→O, line 582). Nets are typed
state literals `noetic [domain] [_{drive}] [register]` (line 56), so the faithful graph is
**bipartite** (parts and state-nodes) with hyperedges (MUX). Parameter blocks carry the real
design content, and the validator "constrains values, not relationships" (line 927).

The CSB (`Chapter_18`, lines 72-127): 11 typed nodes, 8 CJTs, a Differential, a Fuse, a MUX, a
LowPass, one feedback at β=0.2, 4 probes. Four edges are **loose in the text itself**: `trend` is
never declared as a node; `out -> result` is implied only; the fuse's cut of the green path is
prose, not netlist; `risk_signal` is probed but never wired into the cascade. **No CCDL parser
exists on disk.** Whoever writes one picks the graph — and therefore the answer key.

A component is **not** a CAS expression. The Component Companion's rule 6: "Do not force one
part onto one Noetic. Components implement roles." A component is a typed operator whose *ports*
carry expressions. 15 full datasheets, 30 named types in Appendix B; 40 reserved type names in
Appendix C; 34 component entries in the Companion. Seventeen of 39 CCDL statement leaders have
syntax but no semantics. `cas-synthetic` has **no PCBA generator**.

---

## What the evidence kills

I agree with the critics on all six of these. Each is anchored to a file.

1. **"Each vector IS a CAS expression."** A vector space has no boundary: every sum and every
   scaling of two vectors is another vector. CAS has admissibility (Correction 1 — some operator
   applications are illegal), and the SDG's Rule-4 bucket deliberately emits ~18-20% **invalid**
   expressions so a model can learn where the edge is. A vector can be *decoded to* a notation or
   *initialised from* one. It cannot *be* one. And today nothing decodes a 64-d state to a
   compound expression at all.

2. **"Translated into CAS by the SDG."** The SDG generates in the opposite direction. The only
   translator is a foreign model. Using its output as Helm input breaks the ratified rule.

3. **CAS in the inputs recreates the zero-learning floor at the semantic level — perfectly.**
   If the world is generated from an expression, `parts` and `reach` are sub-expression lookups,
   `analogy` and `correspondence` are parse-tree matches, and the compiler answers all of them
   deterministically. Real record, line 2 of the 10k file:
   `(^3^P_{F2}|f × ^3^P_{F2}|A) = ^3^P|Ω_refusal` with `omega_labels: Omega_refusal` — **the
   label is a substring of the input.** The certified gate already lost 11 of 18 to a one-hop
   rule; this would lose all of it to the parser.

4. **Superposition in 64 floats is the mechanism that already failed.** `declaration_table`'s
   field vector is literally "sum the token rows" — and that memorised. Rough capacity (a
   critic's estimate, not measured): a sum of random-ish rows over a 293-symbol alphabet stays
   decodable to about 5 primitives at width 64, about 11 at width 128. One CSB literal,
   `^3^P_{F7}|⟨A,f,T⟩`, is 6 primitives. The Rule-4 record above is about 12.

5. **"Match component weights to boards"** has no object to match against. Parameters are design
   choices, not measurements (Appendix B line 12). Helm has no numeric port and no parameter
   query among its 8 kinds. The single checkable relation in the book is one hand-stated
   inequality on one board (fuse 0.05 below red sat 0.1). **NOT LICENSED as stated.**

6. **Two 40-orderings and two 28-definitions must be settled by owner decision before a single
   slot is built.** Otherwise the tokenizer and the engine disagree about which state is which.

---

## What survives — and where I part company with the critics

The critics scored the proposal as written. The owner's clarification points at a real design,
and the critics' own "would work if" lists describe it. Here it is, in the order I would build.

### 1. CAS as the *registry* of what each weight group is — not the content of the weights

Helm's reasoning core is **already** this: `left`/`right`/`merge` is registered as
`cas.cjt.operation.^6.decompose/0.2` — the `^6` Male operator, "the Ideas an Idea is composed
of." Extend it. Every head and every query kind gets one compiled CAS expression in a registry
file, checked by `compile_expression` and by a behaviour test. Then "this vector is a CAS
notation" means exactly "this parameter group is certified to implement this compiled
operation." Checkable, never learned, no leakage. This is the traceability rule done properly.

### 2. A CAS *decoder* that must round-trip — the output side is where the language belongs

Axis-wise heads (10 Noetic, 4 Domain, 7 Drive, 4 Register), as `structured_prediction.py`
already does for cas-native, plus an operator/composition decoder. The test is not "does the
vector look right" but: **decode → compile → re-encode → compare, exact match, on held-out
compositions.** This is the "NL front door, CAS spine" architecture already on record and the
5-layer eval's round-trip ≥ 80% gate. It answers `analogy` questions *in CAS*, which is the
traceable output the whole project exists to produce.

### 3. Fix, never learn, everything CAS already fixes

The 40 state ids in Rust domain-major order; composition `(i + j) % 10`; involution pairs;
domain order P ≻ C ≻ E ≻ O. These become **fixed operators inside the model**, not learned ones.
A learned `×` that drifts from CAS semantics is undetectable without a decoder; a fixed one
cannot drift. This is the largest free win in the proposal and the critics named it.

### 4. The $0 experiment that decides the capacity question — before anything touches Helm

A standalone encoder + decoder over the frozen 388-token vocabulary at widths 64 and 128.
Training data: SDG level2 records — compiler-checked expressions exist by construction, so no
labeller is needed and no foreign answer enters. Test: exact-match round-trip *after compile* on
**held-out compositions** (unseen combinations of seen primitives) at depths 1, 2, 3, 4, against
a registered mechanism-free baseline (bag-of-rows sum + nearest neighbour). Report the depth at
which each width fails. Dev on the RTX 4070; a claim-bearing run goes to AWS under the GPU-first
rule. **This is the single experiment that turns "each vector is an expression" from a slogan into
a number.**

### 5. For `analogy` — the actual measured failure — the fix is relational, not typed content

Analogy is "same shape, different names." A CAS type on a world is a name. What generalises
across worlds is structure: a canonical form or WL-style hash of each node's local `contains`
neighbourhood, or explicit sub-graph matching between the two worlds in the pair. The F3 ladder
(`records/typed_pointer_001/ladder/`) already measures this axis; it is where an analogy fix
should be scored.

### 6. PCBA boards — the best part of the proposal, done honestly

A board *is* a new kind of world — bipartite, typed ports, four edge kinds, feedback cycles —
and that is exactly the novel-domain test the audit said Helm never had. To make it real:

- **A relation-typed door.** An edge-kind feature (wire / produces / bias / feedback / via) and
  port roles (cause / bias / effect) consumed **inside** the 8 rounds. New run identity, own
  profile digest.
- **Queries untyped adjacency cannot answer**: "which node is the BIAS of `stage3`", "is `fb_rc`
  low-gain", "does `red_fuse` cut the green path". Register the one-hop rule first and show it
  sits at chance on them; if it does not, the query is not out-of-kind.
- **A frozen CCDL parser with a content digest**, edges derived only from netlist statements
  (`node`, `cjt`, component args, `feedback`, `via`), never from prose; the CSB's four loose
  edges logged as excluded; the 17 syntax-only leaders excluded.
- **Hold out whole board families** — train on three of CSB/COB/CDAB/CMB/CPMB, test on the two
  never seen; report train and held-out side by side.
- **A PCBA generator in `cas-synthetic`** — it has none today — with a distribution deliberately
  unlike the book boards, so the book boards can be the held-out set.
- **A literal-only baseline** (answer from the state literal, no graph). If it beats chance on a
  query, that query reads the answer off the input.

Not "weights matching components." That has nothing to score.

---

## Claim states

| statement | state |
|---|---|
| The SDG generates CAS → English, not English → CAS | **real**, quoted from `v74_baseline.py`, `sfe.py` |
| The frozen 388-token CAS vocabulary round-trips as strings | **real**, passing test |
| No decoder exists from a vector to a compound CAS expression | **real**, searched, absent |
| Two 40-orderings and two 28-definitions coexist in the repo | **real**, quoted |
| A CCDL board is a bipartite typed multigraph with four edge kinds | **real**, Appendix C |
| No CCDL parser and no PCBA generator exist on disk | **real**, searched, absent |
| Vector capacity ~5 primitives at width 64, ~11 at 128 | **estimate**, a critic's arithmetic, **not measured** |
| CAS-in-the-inputs would let the compiler score the ceiling | **argued**, not run; the substring case is real |
| The output-side design (registry + round-trip decoder) is sound | **my opinion**, not tested |
| "Weights matching components" | **NOT LICENSED** — no object, no scorer |

---

## Decisions only the owner can make

1. **Which 28.** 7 Drives × 4 Domains (Rust, `CLAUDE.md`) or 7 Drives × 4 Registers (the TKS
   key, `tks28_foundations.py`). Both live in code. Nothing 28-shaped should be built until one
   is written down.
2. **Which coordinate for the 40.** I would take Rust domain-major (`P0=0 … O9=39`) as canonical
   and add a test pinning tokenizer ids 213-252 to it.
3. **Authorise the $0 round-trip experiment (item 4)** on the 4070 — no Helm change, no AWS.
   It is the one thing that makes the vector-capacity question a number instead of an argument.
4. **Whether the relation-typed door (item 6) is a Helm 3.0.** It invalidates every Helm 2.0
   checkpoint and needs its own row in `BRAIN_LINEAGE.md`.
5. **Whether to extend the SDG with a PCBA generator** — that is the piece of the proposal that
   turns "boards" from a hope into a dataset.
