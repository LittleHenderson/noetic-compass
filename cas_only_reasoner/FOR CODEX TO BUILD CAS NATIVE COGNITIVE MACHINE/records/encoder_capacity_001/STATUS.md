# Frozen-encoder capacity: why six of eight question kinds never learn

Status: **MEASURED ON REAL FROZEN PACKETS — $0, standard library and the project's
own pure modules only. No torch, no GPU, no checkpoint, no provider, no spend.**

Reproduce:
`python -B measure_real_packets.py` (real frames) and
`python -B verify_encoder_capacity.py` (the synthetic model it replaces).

## The question

Every completed experiment shows the same pattern: of the eight question kinds
only `correspondence` and `reach` move off chance, while `context`, `definition`
and `edge_account` stay at exactly 0 in every run, every seed and both teaching
arms. The matched study reproduced this independently. This record asks whether
the frozen encoder can carry the information those questions need.

## Method, and why the numbers are trustworthy

The frozen token projection and symbol readout are built by one pure function in
`cas_meta2/typed_teaching/binding.py`. Reconstructing it reproduces both matrices
byte for byte, validated against the SHA-256 the GPU worker recorded:

| matrix | bytes | reconstructed | recorded | exact |
| --- | ---: | --- | --- | --- |
| readout (90 symbols) | 23040 | `14da2c58…0ac667` | `14da2c58…0ac667` | **yes** |
| projection (3829 tokens) | 980224 | `4481b1d2…9fefdd9` | `4481b1d2…9fefdd9` | **yes** |

The real measurements then load the frozen course and tokenizer through the
project's own `worker_contract.load_material`, build real model packets through
`course.model_packet`, compile real frames through `input_frames.compile_packet`,
and rebuild each line's row vector exactly as `binding.py` specifies (signed
permutation per token position, then unit-normalize each row, then sum). Every
figure below is computed from those real objects.

## Finding 1 — the readout and the projection are NOT the bottleneck

A plausible hypothesis was that the 65 world rows are too alike for a
64-dimensional readout to separate.

False. 90 symbol rows, mean `|cos|` **0.098408**, max `|cos|` **0.468750**, zero
duplicates; 65 world rows mean `|cos|` **0.101412**. The projection has **zero
duplicate rows across 3829 tokens**. Both are well-spread random frames.

## Finding 2 — the real packet is 76 rows and ~27,600 tokens

| scope family | rows |
| --- | ---: |
| `WORLD` | **64** |
| `SUPPORT` | 3 |
| `START`, `FORMAT`, `BINDINGS`, `ALIASES`, `POLICY`, `SOURCE`, `RECORD`, `QUERY`, `END` | 1 each |

Every packet carries **all 64 worlds**. The focus world is one of them. The
course's own record states the shared bank is 219,105 of 225,368 bytes of every
packet — 97.2%.

Comparing two different questions on the same world: **all 76 row scopes are
identical at every ordinal.** The difference between two questions is entirely
*inside* rows, not between them.

## Finding 3 — measured on real packets, the question signal is below the readout's own interference

`1−cos` between two real packets about the same world, against the readout
cross-talk floor of `0.098408`:

| packet construction | same kind | different kind |
| --- | ---: | ---: |
| **all 76 rows (what the course uses)** | **0.008374 — 12× low** | **0.024554 — 4× low** |
| no other 63 worlds | 0.048536 — 2× low | 0.140158 — OK |
| question rows only (`QUERY`+`RECORD`+`SUPPORT`) | 0.089208 — 1× low | 0.297050 — OK |
| focus world row only | 0.000000 | 0.000000 |
| focus world + question rows | 0.054148 — 2× low | 0.157531 — OK |

Reading the table:

- **The current encoding is 12× below the floor on the hardest and most
  diagnostic case**: two questions of the *same kind* on the *same world*, which
  are what `context` (0/70 in every run) actually consists of.
- **Dropping the 63 irrelevant world rows improves same-kind discrimination 5.8×**
  and pushes different-kind above the floor.
- **The question does not live in the world row.** `focus world row only` gives
  `1−cos = 0` — the world's own content is identical no matter which question is
  asked about it, so a focus-only packet erases the question entirely.
- **The question lives in the `QUERY`, `RECORD` and `SUPPORT` rows**, and that
  variant is the best of all on both columns.
- But the world row is *needed to answer* `context`, `definition` and
  `edge_account`: those answers are the focus world's own declarations. So the
  measured tension is real — **the evidence you need to answer dilutes the
  question that asks for it**, because both are summed into one vector.

*Caveat on the "floor" comparison.* It is a heuristic, not a theorem. It compares
the packet difference between two questions against the mean `|cos|` between
unrelated answer symbols. A difference smaller than that interference does not
make learning impossible — it makes the model resolve a signal beneath its own
cross-talk, which is what the eight-kind history shows happening.

## Finding 4 — the synthetic model, and what it got wrong

`verify_encoder_capacity.py` models the packet as a mean of random token rows and
predicts `1−cos ≈ k/n` for k differing rows of n. It gave **0.000085** at 27,718
tokens for a 16-row query, and a sweep suggesting the packet must stay under about
128 rows.

Against real packets that model is **directionally right and quantitatively
wrong in both directions**. Real cross-kind differences (0.008–0.050) match the
`k/n` estimate for 1–4 differing rows of 76, so the mechanism is confirmed. But
real same-world same-kind differences are `1.5e-04`, far below any whole-row
estimate, because the difference is *sub-row*. And the "make the packet shorter"
remedy is wrong: **the fix is not fewer rows, it is not summing evidence and
question into one vector.** The synthetic record is retained as the model; this
record supersedes its recommendation.

## The architectural conclusion

The encoder mean-pools a question, its worked supports, and a 64-world bank into a
single 64-dimensional unit vector. Because the bank is identical in every packet,
it forms a large common component; the question is a small perturbation on top.
The learner then has to pick among 90 answer symbols whose mutual interference
(`0.098408`) exceeds the perturbation by 4× to 12×.

This is consistent with everything the project has measured: kinds whose answer is
fixed by the *query's own scope* (`correspondence`, `reach`) learn, because the
slot query is a separate short vector; kinds requiring *content retrieval* from the
frame (`context`, `definition`, `edge_account`) stay at exactly 0, and `world_id`
sat at normalized loss 0.47 from update 0 without moving. **More seeds and more
updates cannot repair it: the signal is gone before the trainable block sees it.**

The fix that follows from the ablation is architectural, not a schedule change:

1. **Do not sum the question and the evidence into one vector.** Keep a question
   channel and an evidence channel, or let the question *select* its evidence
   (attention or keyed lookup over rows) instead of being averaged with it. The
   ablation shows both halves are individually adequate (`question rows only` and
   `no other 63 worlds` each clear the floor on cross-kind) and that summing them
   is what loses the signal.
2. **Drop the irrelevant worlds.** The 63 worlds that are not the focus contribute
   nothing to the answer and cost 5.8× on same-kind discrimination.
3. Either change makes a **cheap decisive test possible without new data**: rebuild
   the packet from the focus world's row plus the question rows, keep the learner
   and course unchanged, and check whether `context`, `definition` and
   `edge_account` leave 0.

## Finding 5 — a falsification test the diagnosis partly passes

The obvious test of any diagnosis is whether it predicts the outcome it was
invented to explain. Joining the recorded answer alphabets (from the per-update
loss records), the declared slot counts, and the observed exact-answer accuracy
across the whole matched study (both arms, three seeds, 1,692 rows per phase):

| kind | slots | answer alphabet | after | outcome |
| --- | --- | ---: | ---: | --- |
| correspondence | 1+nodes | 7, **25** | 94.51% | learned |
| reach | 1 | 5, **6** | 76.48% | learned |
| parts | nodes | 2 | 29.25% | learned |
| analogy | 1 | **65** | 16.19% | weak |
| role_set | 6 | 2 | 10.19% | weak |
| definition | 3 | 3, 4, **64** | 0.00% | failed |
| context | 1+nodes | 2, **64** | 0.00% | failed |
| edge_account | nodes^2 | 2 | 0.00% | failed |

**Factor one, and it holds without exception: every kind whose answer requires
naming one of the 64/65 world symbols fails or is weak** (definition 0.00%,
context 0.00%, analogy 16.19%; mean 5.40%). Every kind whose answer is a small
structural choice does better (correspondence 94.51%, reach 76.48%, parts 29.25%;
the group mean is 42.08% but that includes edge_account — see below).

This is exactly what the dilution predicts. A world name is a 64-way choice, and
to make it the model must discriminate two packets at `1−cos ≈ 1.5e-04` against a
readout whose unrelated symbols interfere at `0.098408`. A reach rule is a 5- or
6-way choice and survives the same dilution.

**Factor two, and the diagnosis alone does not explain it: `edge_account` has a
binary alphabet and still scores exactly 0.00%.** The reason is conjunction
length. `edge_account` declares `nodes²` slots — up to 16 independent binary
decisions for a 4-node world — and exact-answer scoring requires all of them
correct. `parts` declares `nodes` slots and reaches 29.25%; `role_set` declares 6
and reaches 10.19%. Exact accuracy over a conjunction falls geometrically in the
slot count, so an identical per-slot weakness produces 29% on a five-slot kind and
0% on a sixteen-slot one.

So the honest statement is a two-factor account, not one:

1. **Answers needing a 64-way world symbol cannot be made** from a mean-pooled
   packet — the discrimination they need is 4× to 12× below the readout's own
   interference.
2. **Exact-answer scoring over many-slot conjunctions compounds any per-slot
   weakness geometrically**, so multi-slot kinds fail even when their alphabet is
   small.

Neither factor is repairable by training, seeds or schedule. Both are encoder
properties. The two fixes in the architectural conclusion address factor one
directly and factor two indirectly, by raising per-slot accuracy.

Note on the test: this is a retrospective check against outcomes the diagnosis was
built to explain, so it is corroboration and not independent confirmation. The
kind with the cleanest falsifying power, `edge_account`, is the one the single
factor failed on, and that is recorded above rather than smoothed over.

## What this record does NOT claim

- It does not test the trainable block. It shows the encoder cannot deliver the
  signal; it does not show the block could not use it if delivered.
- It makes no learning, capability or readiness claim.
- The "12× below floor" figure is a comparison against a heuristic interference
  level, not a proof that learning is impossible at that ratio.
- The `1−cos = 0` for focus-only is a real measurement of identical vectors, not a
  rounding artefact; the two packets genuinely share the same focus-world row.
- The split of the eight kinds into scope-fixed and content-retrieval remains a
  reading of the evidence, offered as a hypothesis.

## Evidence

| artifact | SHA-256 |
| --- | --- |
| frozen readout (recorded by the GPU worker) | `14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667` |
| frozen projection (recorded by the GPU worker) | `4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9` |

Sources: `cas_meta2/typed_teaching/binding.py` lines 106–216 (row algorithm and
binding), `cas_meta2/typed_teaching/input_frames.py` (frame construction),
`cas_meta2/typed_teaching/worker_contract.py` (frozen-course loader),
`cas_meta2/recurrent_cjt/recurrence.py` lines 182–215 (the recurrence).

Scripts in this directory: `measure_real_packets.py` (real frames, the authority
for Findings 2–4) and `verify_encoder_capacity.py` (the synthetic model).
