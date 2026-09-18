# BINDING_VARIANTS_RESULT — the information is in the slot's name, and the block throws it away

**Round 29. New measurement, and a refutation of round 28's own proposal.**
**$0.00. Pure Python, standard library plus the project's pure modules. No torch, no GPU, no model,
no training, no new run.**

Scripts: `measure_binding_variants.py` (`binding_variants.txt`), `measure_binding_ceiling.py`
(`binding_ceiling.txt`), `measure_read_path_projection.py` (`read_path_projection.txt`).

---

## 0. Frozen-byte gate — the reconstruction is the encoder

Every number below is computed from a pure-Python rebuild of the frozen encoder. It reproduces both
published byte strings exactly, so it is the encoder and not a proxy:

```
projection  shape (3829, 64)   sha256 4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9  MATCH
readout     shape   (90, 64)   sha256 14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667  MATCH
```

`measure_binding_ceiling.py` aborts if either hash fails. Neither did.

## 1. The packet is inert per slot — six runs, run-invariant

`encoder.py:212` is the whole of the slot encoding:

```python
result = normalize((entry["vector"] + query) / math.sqrt(2.0))
```

`learner.py:153` then reads out `readout_rows[indexes] @ vector`, which is **linear**. So the frozen
readout's decision on the encoder's own output is `sign(d · (packet + query))` for
`d = readout[PRESENT] − readout[ABSENT]`, and the packet's contribution `d · packet` is **one
constant per question**.

Measured, identically in all six runs:

| kind | slots | before the block | chance | best constant | after the block | `before == name-alone` |
|---|---|---|---|---|---|---|
| edge_account | 1029 | **51.6035%** | 51.8326% | 59.5724% | 52.3810% – 53.5471% | **100.0000%** |
| parts | 207 | **47.8261%** | 51.2707% | 57.9710% | 70.5314% – 73.9130% | **97.1014%** |
| context | 267 | **49.0637%** | 66.4184% | 78.6517% | 38.5768% – 41.5730% | **100.0000%** |
| role_set | 216 | **53.2407%** | 68.6728% | 80.5556% | 65.7407% – 70.8333% | **94.4444%** |

`before == name-alone` is the fraction of slots where the frozen readout's decision on
`normalize(packet + query)` is **identical** to its decision with the packet term deleted. For
`edge_account` and `context` it is **100.0000%** — the packet does not change one decision in 1,296
slots.

Two further confirmations:

- **The packet term alone, with no slot term, scores exactly the best constant** for `role_set`
  (80.5556% against a best constant of 80.5556%). Its entire contribution is one bit per question.
- **The pre-block numbers are identical in every run.** They must be: `q` depends only on the
  world alias and the slot descriptor, and `p` is inert. This is a property of the architecture, not
  of any training run.

## 2. The proposal from round 28 is refuted — twice over

Round 28 concluded: "give a pair-valued slot a name for the pair itself, not the sum of its two
ends." `measure_binding_variants.py` tested that directly. Ridge LDA on the slot vector `q`,
5-fold by question, `edge_account`, 1,029 slots:

| naming variant of `coordinates` | q: LDA | enc: LDA |
|---|---|---|
| `real` — `["W15/N0", "W15/N1"]` | 62.3033% | 62.9181% |
| `pair_token` — `["W15/N0->N1"]` | **60.2719%** | 60.3998% |
| `pair_token_sorted` — `["W15/N1->W15/N0"]` sorted | 63.3721% | 63.0098% |
| `swapped` — `["W15/N1", "W15/N0"]` | **62.3033%** | **62.9181%** |

**Naming the pair as one token makes it worse**, by 2.03 points. And `swapped` is identical to `real`
to four decimal places in both columns — the binding **discards the coordinate order** at the linear
level.

**And arity is refuted independently.** `context` participants carry one node ref per slot, exactly
like `parts` — the same arity the round-28 proposal was built on — and `context` fails at 40.8240%
against a 78.6517% constant while `parts` succeeds at 70.5314% against a 57.9710% constant.
**Slot arity does not separate success from failure.** The round-28 proposal is withdrawn.

## 3. The finding: the label is recoverable, and the block destroys it

Same probe, same folds, per kind. `lookup` is a pure memoriser keyed on
`(scope alias, coordinates)`, fitted on four fifths of the questions; `block` is the recorded
per-bit accuracy of the trained machine, for reference.

| kind | slots | **q: LDA** | enc: LDA | **lookup** | **block** | best constant |
|---|---|---|---|---|---|---|
| edge_account | 1029 | 62.3033% | 62.9181% | **96.4508%** | **53.5471%** | 59.5724% |
| parts | 207 | **87.1525%** | 86.6700% | 85.4437% | **70.5314%** | 57.9710% |
| context | 267 | **96.3758%** | 94.2490% | **98.5926%** | **40.8240%** | 78.6517% |
| role_set | 216 | 60.6376% | 60.4577% | 68.2540% | 69.4444% | 80.5556% |

### Headroom against the trivial constant

**These are per-bit figures. §4 shows they do not convert into answer-level gains, and the
conversion is the thing that matters.**

| kind | best probe | best constant | headroom |
|---|---|---|---|
| parts | 87.1525% | 57.9710% | **+29.18** |
| context | 96.3758% | 78.6517% | **+17.72** |
| edge_account | 62.3033% | 59.5724% | **+2.73** |
| role_set | 60.6376% | 80.5556% | **−19.92** |

### Headroom of the block against its own input

| kind | best readout of `encoded` | block | lost |
|---|---|---|---|
| context | 96.3758% | 40.8240% | **−55.55** |
| parts | 87.1525% | 70.5314% | **−16.62** |
| edge_account | 62.9181% | 53.5471% | **−9.37** |
| role_set | 60.6376% | 69.4444% | **+8.81** |

## 4. The per-bit gain does NOT become an answer-level gain — measured, and it goes the wrong way

The obvious next step after §3 is to turn per-bit reading into whole answers and project the score.
`measure_read_path_projection.py` did exactly that: fit the lookup on four fifths of the exposed
course, predict **every** slot of the held-out fifth, assemble the answer with the project's own
`slots.assemble_answer`, and compare to the project's own derived truth.

```
           kind     q   recorded     lookup      lift  key coverage
          reach   107   75.7009%   75.7009%  +0.0000%     100.0000%
 correspondence    88   59.0909%       nan%     +nan%          nan%
        context    70    0.0000%    0.0000%  +0.0000%      92.5816%
        analogy    70    0.0000%    0.0000%  +0.0000%      94.2857%
   edge_account    70    0.0000%    0.0000%  +0.0000%      90.4762%
     definition    70    0.0000%    0.0000%  +0.0000%      94.2857%
          parts    53   22.6415%   18.8679%  -3.7736%      71.4976%
       role_set    36    8.3333%    5.5556%  -2.7778%      50.0000%
----------------------------------------------------------------------------
   ONE DECISION   265   50.1887%   45.7627%  -4.4260%
 MANY DECISIONS   299    5.0167%    4.0134%  -1.0033%
----------------------------------------------------------------------------
            ALL   564   26.2411%   19.5378%  -6.7033%
```

**The lookup gains nothing at the answer level and loses 6.7033 points overall.** `context` reads its
bits at 98.5926% under the same fit and scores **0.0000%** on the whole answer.

*(A sixth column, `slot agreement`, was printed by the script and is **not** reproduced above: it
counts how often the lookup's guess equals the machine's recorded `selected`, not the truth, so its
label is wrong and it says nothing about accuracy. Noted rather than silently dropped.)*

**So §3's headroom is per-bit only, and per-bit headroom is not a projection of score.** Three reasons,
in order of size:

1. **Whole-answer accuracy compounds over every field, not just the bit fields.** A `context` answer
   is `setting_ref` (a 64-way alias choice) *and* the participant set. `definition` is `whole` plus
   two 64-way declarations. A lookup that reads the participants at 98.5926% still returns
   `setting_ref` from a sparse table, and one wrong alias field makes the whole answer wrong however
   good the bits are. **This is a finding in its own right: for `context` and `definition`, the
   answer-level bottleneck is the alias-valued field, not the binary slots.**
2. **Key coverage is incomplete.** `parts` 71.4976%, `role_set` 50.0000%, `edge_account` 90.4762%,
   `context` 92.5816%. A question needs *every* one of its keys seen.
3. **Exactness needs every bit right**, and the per-bit errors are correlated within a question
   because they share a world.

**What this does and does not overturn.** It does **not** overturn §1 or §3: the packet is still
inert per slot (`before == name-alone` at 100.0000%, six runs), and a linear probe of `encoded` still
reads `context`'s bits at 96.3758% where the block reads them at 40.8240%. It **does** overturn any
reading of §3 as "the machine could score 96% if it read the bits", and it removes the basis for
quoting a projected score gain from this line of work. **No score projection is offered.**

It also means the `Fix A` bridge in §5 is weaker than it looked: a better linear readout of `encoded`
improves per-bit reading, and per-bit reading is not what the score is made of.

## 5. What this means

**The encoder's binding is not the bottleneck.** Round 27 and round 28 blamed the additive binding
for hiding the packet. The packet *is* inert per slot — §1 proves it — but that turns out not to
matter, because for these four kinds **the answer is a function of the slot's own name**, and the
name carries it: the world alias is part of every slot descriptor, and each world's declarations are
fixed across the whole course. A memoriser keyed on the slot's name reads the bits at **96.4508%**
and **98.5926%** where the trained machine reads them at 53.5471% and 40.8240%.

**So there are two separate losses, and the second is far larger:**

1. **The block cannot synthesise the conjunction** the slot-and-packet binding requires. Measured:
   `before == name-alone` at 94.44%–100.00%, and pre-block accuracy at or below chance on all four
   kinds. This is what rounds 27 and 28 established.
2. **The block actively destroys a linear signal present in its own input.** `context` sits at
   96.3758% under a plain linear readout of `encoded` — the exact quantity the block is handed — and
   at **40.8240%** after the block. That is a **−55.55-point** loss, and it lands *below* the
   78.6517% that a constant answer earns.

**Loss 2 is the bigger prize and the cheaper one, because it needs no new information path.** The
input already contains the answer in a linearly readable form; the machine has to stop destroying it.

### The bridge to `Fix A`

`cncm/analytic_decompose.py::decompose_from_free_readout` exists to make the frozen readout behave
as a **free linear readout** by inverting `R`. The LDA numbers in §3 are therefore exactly the
quantity that construction targets: the best linear readout of the encoder's own output. Fix A's
published result (62.94% direct, 62.06% through the recurrence, on focus identification) and
`context`'s 96.3758% here are the same kind of number.

**And `Fix A` is not available as implemented for this readout**: `decompose_from_free_readout`
requires `nclass == core_width`, and the frozen readout is `[90, 64]`, so it refuses. The construction
would need a rectangular solve. That is an engineering step, not a research one, and it is **not
taken here**.

## 6. Claim status

- **REAL, measured, checksum-gated:** §0's reconstruction. Artifact: the two matching sha256s printed
  by `measure_binding_ceiling.py` and `measure_binding_variants.py`.
- **REAL:** every figure in §1–§3, from recorded artifacts plus the frozen encoder's own bytes.
  Artifacts: `binding_ceiling.txt`, `binding_variants.txt`.
- **WITHDRAWN, this round:** round 28's "name the pair as one thing" proposal. Refuted by
  `pair_token` scoring 2.03 points *worse* than `real`, and by `context` sharing `parts`' arity and
  failing. Artifact: `binding_variants.txt`.
- **WITHDRAWN, this round:** the arity hypothesis as the discriminator between reading and not
  reading.
- **REAL:** the packet is inert in the pre-block per-slot decision — `before == name-alone` at
  100.0000% on 1,296 slots across two kinds, six runs, run-invariant.
- **REAL, and adverse to §3:** the memoriser gains **−6.7033 points** at the answer level
  (26.2411% → 19.5378%) and `context` scores **0.0000%** on whole answers while reading its bits at
  98.5926%. Artifact: `read_path_projection.txt`. **Per-bit headroom is not a score projection, and
  none is offered.**
- **OPEN, and now the leading question:** for `context` and `definition`, the answer-level
  bottleneck is the **alias-valued field** (`setting_ref`, `whole`, `kind_ref`, `function_ref`), not
  the binary slots. Unmeasured which field binds the answer.
- **NOT LICENSED:** that any fix raises the recorded score. §3 identifies where the per-bit headroom is;
  §4 shows it does not convert. Nothing here demonstrates that a change can capture it.
- **OPEN:** why the block destroys a linearly available signal. Unmeasured. The concentration result
  (all six runs converging on `W36`, a direction that is not a training target) remains the best
  lead, and remains unexplained.

## 7. What this does not say

- It does not say a memoriser is the fix. A memoriser is a **lower bound** on a read path: the
  answers are visible fields of the test packet (`focus["contains"]`, `focus["declarations"]`), so a
  machine with a read path needs no exposure at all. Where the memoriser fails for want of coverage,
  a read path still succeeds.
- It does not say the round-28 proposal was unreasonable. It says the data refused it, and that the
  refusal is now on record rather than discovered after a GPU run.
- **It does not establish anything about unseen worlds.** §3's regime is *seen world, unseen
  question*. The `development` panel (59 questions, zero overlap with the exposed course, machine
  score 0/59 at every cursor) cannot be scored here at all: its records are absent from the frozen
  course, so `course.model_packet` raises `TYPED_COURSE_RECORD_UNKNOWN` and its targets cannot be
  derived. That panel stays unmeasured, and it is the panel that matters most.
- It does not authorise a code change. The `PHASE0_RECORD_DRAFT.md` remains unsigned.
