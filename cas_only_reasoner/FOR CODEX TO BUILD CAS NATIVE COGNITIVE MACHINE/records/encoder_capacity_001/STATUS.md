# Frozen-encoder capacity: why six of eight question kinds never learn

> # CORRECTION — Findings 3 to 10 are built on a WRONG PREMISE and their conclusion is FALSE
>
> **The encoder is not the bottleneck. The frozen random-code READOUT is.**
>
> Findings 3–10 measured the *packet vector* and concluded the encoder averages the
> question away before the learner sees it. **The learner never receives the packet
> vector.** `encoder.encode_slot` line 212 gives it
>
> ```
> normalize( (packet_vector + slot_query_row) / sqrt(2) )
> ```
>
> and the **slot query row alone carries the focus world at 63.65% linear
> decodability — 40.7× chance** — on the encoding the current encoder already
> produces. The measured "0.18%" was an artefact of probing an object the learner
> does not consume.
>
> **Consequences, all measured:**
>
> | what was measured | value | meaning |
> | --- | ---: | --- |
> | packet vector, current (Findings 3–9) | 0.18% | an object the learner never sees |
> | **actual slot encoding, current** | **63.65%** | **the focus IS available to the learner** |
> | actual slot encoding, my proposed change | 62.94% | my change achieves **nothing** |
> | **actual slot encoding + the learner's FROZEN readout** | **1.24%** | **below chance** |
> | actual slot encoding + a LEARNED linear readout | 63.65% | the information is present |
>
> The information is in the representation and the **frozen readout cannot extract
> it**. A learned 64×64 linear map reaches 63.65%; argmax over the learner's 90
> frozen Rademacher readout rows reaches 1.24%, *below* the 1.5625% chance level.
>
> **The change spec is WITHDRAWN in full.** It proposed an encoder change to fix a
> defect that does not exist. The corrected diagnosis is in Finding 11.
>
> The wrong findings are kept below rather than deleted. Four self-corrections are
> now recorded in this record, and each one was caught by measuring the thing the
> previous round had only assumed.

Status: **CORRECTED — the encoder is not the bottleneck; the frozen readout is.**

Reproduce:
`python -B measure_real_slot_encoding.py` (the decisive measurement) and
`verify_encoder_capacity.py` (the synthetic model it replaces).

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

> **Superseded in part. The two remedies first written here were tested in
> Finding 5 and both failed. The diagnosis below stands; the remedies do not.
> Read Finding 5 before acting on anything in this section.**

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

The two remedies originally proposed here, and their measured fate:

1. ~~Do not sum the question and the evidence into one vector; let the question
   *select* its evidence by a keyed read.~~ **Failed.** Tested as a fixed
   query-to-world-row dot product: 6.25% focus recovery against 1.56% chance. Not
   a usable read. The rows must be *learned over*, not addressed by a fixed
   function.
2. ~~Drop the 63 irrelevant worlds.~~ **Failed, and unsafe.** It removes the
   distractors that make a 64-way answer meaningful, so `correspondence` and
   `analogy` answers become identifiable by elimination. The measured
   discrimination gain comes from deleting the answer space.

**The remedy that survives, and the only one the measurements support:** stop
collapsing the 76-row structure into one vector *before* the learner sees it.
Expose the rows — or a bounded selected subset — with a learned addressing
mechanism over them, instead of pre-averaging. The evidence that this is where the
problem lies is the contrast in Finding 5: the mean-pooled packet recovers the
focus world 0 times in 160, while an untrained read over the raw rows recovers it
4× more often than chance. The information is in the rows and gone from the mean.

## Finding 5 — my own proposed fix was tested and FAILED, and the reason matters

The architectural conclusion below originally recommended two things. Both were
tested against the real rows, and **both are wrong.** Recording that here rather
than editing it away.

**Recommendation tested: an addressed read.** The proposal was to replace
`packet = unit_l2(sum of all row vectors)` with a read addressed by the query:
score each world's row by `⟨query, world_row⟩` and take the argmax. This keeps
every world present, so the answer space is unchanged and nothing leaks.

Measured on 160 real packets (`measure_addressed_read.py`), chance = 1/64 = 1.56%
(expected 2.5 hits by chance):

| read | focus recovered | vs chance |
| --- | ---: | --- |
| query rows only | 10/160 = **6.25%** | 4.0× chance (binomial p < 0.001) |
| query + record + support rows | 8/160 = **5.00%** | 3.2× chance (p < 0.01) |
| **mean-pooled packet (what the course uses)** | **0/160 = 0.00%** | below chance; expected 2.5 |

**This is the sharpest result in the record, and it is two findings at once:**

1. **The mean-pooled packet recovers the focus world never — 0 out of 160.** The
   quantity the learner most needs, which world the question is about, is not
   merely diluted; at this resolution it is *gone*.
2. **The information is nevertheless present in the rows.** An untrained linear
   read over the query rows alone recovers it 4× more often than chance. The
   signal exists in the representation and is destroyed by the pooling, not absent
   from it.

So the addressed read is **not a fix** — 6.25% is useless as a read. But it is
evidence for where the problem is, which is worth more than the fix would have
been: **the rows carry the focus; the mean does not.**

**Recommendation tested: drop the 63 irrelevant worlds.** This is worse than
ineffective, it is unsafe. The worlds that are not the focus are the *distractors*
that make a 64-way answer meaningful. For `correspondence` and `analogy` the answer
names a different world; removing the other worlds makes the answer identifiable
by elimination. The ablation in Finding 3 measured a real discrimination gain, but
that gain comes from deleting the answer space, not from cleaning the signal.

**So the corrected conclusion is different, and stronger:**

> The defect is not that the encoder uses the wrong read. It is that the encoder
> **collapses a 76-row structure into a single 64-dimensional vector before any
> learning happens.** Once collapsed, the structure that a learned read would need
> is gone, and no fixed function recovers it.

That reframes the fix as: **expose the row structure to the learner instead of
pre-averaging it.** The current learner receives one 64-dim vector per slot
(`learner.py`: a fixed slot plan feeding a `^6` block). It would instead receive
the rows — 76 × 64, or a bounded selected subset — with a learned addressing
mechanism over them. That is a genuine architectural change, and it is the one the
measurements support.

The negative results are load-bearing and are kept: they rule out the two cheap
fixes and leave the expensive one as the only survivor.

## Finding 6 — a falsification test the diagnosis partly passes

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

## Finding 7 — the decisive test: the mean-pooled packet carries ZERO linearly decodable focus, and decodability falls monotonically as rows are summed

Findings 3–6 measure how far apart packets are. This one asks the question that
actually matters: **can a trained read recover the focus world from what the
learner is given?**

Method: build real row vectors for 200 packets, then fit a closed-form ridge probe
(64 classes, one output per world alias) with 5-fold cross-validation. Chance is
1/64 = 1.5625%. Pure Python, no torch, no GPU. Script `linear_probe.py`.

| features given to the probe | dims | CV accuracy | vs chance |
| --- | ---: | ---: | ---: |
| **mean-pooled packet (what the course uses)** | 64 | **0.00%** | **0.0×** |
| query row only | 64 | **11.00%** | **7.0×** |
| query + record + support rows | 64 | 3.50% | 2.2× |
| mean + query concatenated | 128 | 8.50% | 5.4× |

**Two results, and together they are the argument for the architectural change:**

1. **The mean-pooled packet decodes the focus world 0 times in 200.** Not "poorly"
   — at this resolution a trained linear read finds *nothing* about which world the
   question concerns. That is the single quantity `context`, `definition` and
   `analogy` all require.
2. **Decodability falls monotonically as rows are summed.** Query row alone: 11.0%.
   Sum the query with 3 more rows: 3.5%. Sum it with all 76: 0.0%. Concatenating
   instead of summing recovers 8.5%. **The act of pooling is what destroys the
   information**, and it destroys it in proportion to how much is pooled.

This is the cleanest evidence in the record for the corrected conclusion. The
information is present in the representation — a probe finds it at 7× chance — and
the mean removes it. Nothing about training, seeds or schedule can recover what the
encoder has already averaged away.

Limits, stated plainly:

- 200 packets and 64 classes is a small probe. The absolute numbers are indicative,
  not precise, and a linear probe is a lower bound on what a learned nonlinear read
  could extract. The **contrast** between the rows and the mean is the finding, not
  the absolute decodability.
- The mean-pooled figure of 0.00% means "no linearly decodable information at this
  sample size and regularisation", not a proof of zero mutual information.
- The probe is trained on the same 564-question course it is evaluated on, so it is
  a decodability test, not a generalisation result.

## Finding 8 — three compounding defects, and the third is nameable in one line

`measure_mean_defects.py`, 10 real packets. The packet is
`unit_l2( sum of unit row vectors )`, so **every row carries weight `1/75` no
matter how many tokens it holds.** Measured weight against content:

| scope family | rows/pkt | weight | tokens/pkt | token share | mismatch |
| --- | ---: | ---: | ---: | ---: | ---: |
| WORLD | 64.00 | 85.22% | 18,846 | 68.84% | 0.8× |
| **ALIASES** | **1.00** | **1.33%** | **6,852** | **25.03%** | **18.8×** |
| SUPPORT | 2.10 | 2.80% | 594 | 2.17% | 0.8× |
| SOURCE | 1.00 | 1.33% | 509 | 1.86% | 1.4× |
| RECORD | 1.00 | 1.33% | 239 | 0.87% | 0.7× |
| POLICY | 1.00 | 1.33% | 144 | 0.53% | 0.4× |
| QUERY | 1.00 | 1.33% | 88 | 0.32% | 0.2× |
| BINDINGS | 1.00 | 1.33% | 76 | 0.28% | 0.2× |
| FORMAT | 1.00 | 1.33% | 26 | 0.09% | 0.1× |
| START | 1.00 | 1.33% | **1** | 0.004% | 0.0× |
| END | 1.00 | 1.33% | 1 | 0.004% | 0.0× |
| **total** | **75.10** | 100% | **27,376** | 100% | |

**Defect 1 — within-row mean.** Each row is `unit_l2(sum of its own tokens)`, so a
token is diluted by its row's length before any row pooling begins: one part in
~88 for a `QUERY` row, ~298 for a `WORLD` row.

**Defect 2 — unweighted row mean.** A **single-token `START` marker and the entire
6,852-token alias table receive identical influence, `1/75 = 1.33%`.** The alias
table is a quarter of the packet by content and contributes 1.33% of its signal —
an 18.8× mismatch. The question itself is 88 tokens, 0.32% of the packet.

**Defect 3 — no content addressing.** The aggregation is a fixed unweighted sum,
identical in form for every question. Nothing in it depends on what is being asked,
so **no amount of training can make it selective.** This is the one-line statement
of the architectural defect:

> The encoder aggregates 75 rows with fixed uniform weights before any learning
> happens, so a question is averaged into its own evidence.

All three compound. None is repairable by seeds, schedule or more updates. The
change that follows is specified in `ARCHITECTURE_CHANGE_SPEC_v0.1.md`.

## Finding 9 — the full-sample probe and the learning curve: the information is there and the mean destroys it

Finding 7 used 200 packets. Rebuilt at the full 564, and swept against sample size
(`falsify_prediction_1.py`; ridge probe solved in the dual, 5-fold CV, chance
1/64 = 1.5625%).

**Full sample, all 564 packets:**

| features | dims | CV accuracy | vs chance |
| --- | ---: | ---: | ---: |
| **mean-pooled packet (the current profile)** | 64 | **0.18%** | **0.1×** |
| query row only | 64 | 39.89% | 25.5× |
| query + support rows | 256 | 25.53% | 16.3× |
| **head rows (no world rows)** | 576 | **70.92%** | **45.4×** |
| the 64 world rows | 4096 | 0.89% | 0.6× |
| all rows concatenated | 4864 | 64.89% | 41.5× |

**Learning curve — the row features are sample-limited; the mean is not:**

| n samples | mean (64d) | query (64d) | head (576d) |
| ---: | ---: | ---: | ---: |
| 50 | 0.00% | 0.00% | 0.00% |
| 100 | 1.00% | 5.00% | 3.00% |
| 200 | 2.50% | 12.00% | 9.00% |
| 300 | 2.67% | 20.33% | 29.00% |
| 400 | 1.00% | 28.25% | 44.50% |
| 500 | 0.20% | 38.60% | **64.60%** |

Four conclusions, and the fourth is a correction to Finding 7:

1. **The current profile decodes the focus world 1 time in 564** (0.18%, against
   8.8 expected by chance). The row structure decodes it **400 times in 564**
   (70.92%). The defect is confirmed and quantified.
2. **The row features climb steeply with data and are still rising at the full
   sample.** Finding 7's 11.00% was a **sample limitation, not an information
   limitation.** The spec that was withdrawn on that basis is restored.
3. **Adding the world rows to a read HURTS: 70.92% → 64.89%.** The 4,096
   question-invariant world-row dimensions dilute the signal even at the read. This
   is the dilution effect measured directly, and it says identification should
   address the head rows while the world rows supply content.
4. **The 64 world rows decode at 0.89%, below chance.** They are identical in every
   packet, so they cannot identify the focus at all — only help answer once it is
   known.

**Silent failure avoided:** `falsify_prediction_1.py` originally solved ridge in the
primal, which needs a 4,864 × 4,864 inverse for the concatenated features and will
not finish in pure Python. It was rewritten in the dual (an n × n inverse, n = 564).
Any future probe on concatenated features must use the dual form.

## Finding 11 — the corrected diagnosis: a frozen random-code readout that cannot be read

The decisive measurement, all 564 packets, primal ridge for the learned case
(`measure_real_slot_encoding.py`), chance 1/64 = 1.5625%:

| feature | read | CV accuracy | vs chance |
| --- | --- | ---: | ---: |
| packet vector, current encoder | learned linear | 0.18% | 0.1× |
| packet vector, query row only | learned linear | 39.89% | 25.5× |
| **actual slot encoding, current encoder** | **learned linear** | **63.65%** | **40.7×** |
| actual slot encoding, proposed change | learned linear | 62.94% | 40.3× |
| **actual slot encoding, current encoder** | **the learner's FROZEN readout** | **1.24%** | **0.8× — below chance** |

**The information the learner needs is already in what it receives.** A learned
linear map recovers the focus world from the current slot encoding 40.7× better than
chance. The learner's own readout does worse than guessing.

### What the frozen readout demands

The readout is 90 fixed Rademacher rows, each 64 entries of ±0.125 chosen by a hash
(`binding.row_bytes`, validated byte for byte in Finding 1). To emit the correct
world symbol, the hidden state must align with that world's particular random
direction. Nothing about those directions is related to the question or to the
content — they are a random codebook.

So the trainable `^6` block has to learn a re-alignment that carries the encoded
focus onto 64 arbitrary Rademacher directions. A free 64×64 linear map does it
(63.65%). The learner's block — `merge(cat(tanh(left(x)), tanh(right(x))))`, 16,384
parameters, applied recurrently, trained for 160 updates — does not, and the readout
it feeds is at 1.24%.

**That is a statement about architecture, not about schedule.** It implies the
project's decision to freeze *both* the projection and the readout — taken for
reproducibility and for hash-verifiable rows — is what caps learning, and that no
amount of teaching-order variation can move the three zero-score kinds.

### Why three kinds are zero and two are not, under this diagnosis

The kinds that work need fewer, coarser distinctions from the frozen codebook:
`reach` is a 5–6-way choice and `correspondence` a 7–25-way one, both far from
needing 64 arbitrary directions separated. The zero kinds — `context` (0/70) and
`definition` (0/70) — must emit a **world symbol**, a 64-way choice through the
frozen codebook. `edge_account` additionally compounds 16 exact slots (Finding 6).

This is one coherent account of all eight kinds and it needs no encoder change.

### The open question this raises, and its answer

Finding 12 answers it: **every one of the 65 world symbols is selectable.**

## Finding 12 — the codebook is capable, so the failure is in training, not architecture

`measure_codebook_vertices.py`, exact arithmetic on the reconstructed rows.

To emit world symbol `W_t` the hidden state must beat every other world row:
`<h, r_t> > <h, r_s>`. That is possible exactly when `r_t` is a **vertex of the
convex hull** of the world rows. If a row lay inside the hull of the others, no
hidden state whatsoever could select it and that symbol would be **unreachable for
any model, however trained**.

Result — solved for each of the 65 rows by margin maximisation:

| | count |
| --- | ---: |
| **selectable** | **65 of 65** |
| **not selectable** | **0 of 65** |
| margin (normalised by ‖h‖) | min **0.7573**, median 0.8418, max 0.9014 |

With `h` set exactly to a world's own row, the worst runner-up margin is **0.5312**
between `W2` and `W20`. The codebook is not degenerate, not collapsed, and not
missing any symbol.

### The diagnosis, now complete and consistent

| layer | measured state | verdict |
| --- | --- | --- |
| encoder output (actual slot encoding) | focus decodable at **63.65%**, 40.7× chance | **adequate** |
| frozen readout codebook | **65 of 65 symbols selectable**, margin ≥ 0.757 | **adequate** |
| a learned 64×64 linear map into the frozen codebook | **63.65%** | the fix is representable |
| the `^6` block actually trained, 160 updates | **1.24%**, below chance | **the failure** |

**Nothing in the representation or the codebook is blocking. The learner simply
fails to find a rotation that a free 64×64 linear map finds easily.**

That also means the `^6` block is *capable in principle*: one pass of a linear core
is exactly `h = W·e`, the same object the probe learns; and `tanh` is ≈ identity
for small inputs, so `merge(cat(left(x), right(x)))` can express a linear map. The
block is not structurally forbidden from doing it.

### The quantified suspicion, and why it is about budget rather than shape

The probe needed the **full 564 packets** to reach 63.65%; at 200 packets it reached
only ~9% (Finding 9's curve). Fitting a 64×64 map is ~4,096 parameters. The learner
receives **160 gradient steps on batches of 8** — about 1,280 presentations for a
16,384-parameter model, roughly **0.08 presentations per parameter**, applied to a
re-alignment whose own probe needed hundreds of samples to emerge.

**The honest reading: this looks like an under-training result, not an architectural
one.** That is the opposite of where this record started, and it follows from the
measurements rather than from a preference.

**But the comparison is not apples-to-apples, and that limit must be stated.** The
probe's 63.65% comes from a **closed-form ridge solve** on 564 samples; the learner
reaches its 1.24% by **stochastic gradient descent in 160 steps**. So this record
establishes **representability** — a linear map into the frozen codebook exists and
is easy to find in closed form — and it does **not** establish that SGD in 160 steps
could find it. The under-training reading is a well-motivated hypothesis, not a
measured fact.

What *is* measured and does carry the argument:

- the encoder delivers the focus at 40.7× chance before any learning;
- the codebook can express all 65 symbols with margin ≥ 0.757;
- a 64×64 map into that codebook reaches 40.7× chance in closed form;
- the trained block reaches 0.8× chance, below guessing.

So the gap is between "a map exists" and "this optimiser found it in this budget",
and that gap is where the next question lives — not in the encoder, which is what
five rounds of this record wrongly blamed.

It is cheap to distinguish, though not at $0: a longer-training or
learning-rate/warmup run on the **unchanged** architecture would test it, and so
would a short diagnostic that reports the training loss curve and the achieved
focus decodability at each checkpoint. **No such run is proposed here or
authorized.**

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
