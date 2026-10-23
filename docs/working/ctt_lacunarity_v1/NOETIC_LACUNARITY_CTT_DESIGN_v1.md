# Noetic lacunarity for CTT training — design note v1 (2026-10-23)

Status: **design note plus one measured reading.** Nothing trained, nothing scored. Claim status of the reading:
`REAL`; of the design: `PROPOSED`; of any gain: `NOT CLAIMED`. Not claim-bearing (local analysis of existing files).

## 1. Two different objects, one shared algebra

The numerical measure used so far and the CAS measure in the books are not the same thing, but they are the same
family. Stating the relationship exactly is what makes them usable together.

**CAS state lacunarity** (manuscript, *Lacunarity: The Geometry of Cognitive Gaps*, lines 1758–1794):

```
Λ(p) = Var(p) / Mean(p)²
```
over the activation vector `p` of the 40-state matrix. Bands given in the text: `< 0.5` uniform, `0.5–1.5` moderate,
`1.5–3.0` concentrated, `> 3.0` extreme ("critical blind spots; dangerously narrow"). Four further metrics are named:
fractal `1 − unique Noetics/10`, domain `1 − active domains/4`, drive `1 − active drives/7`, RPM resolution
`1 − mechanisms used/4`.

**Numerical (gliding-box) lacunarity**, used in E1:

```
L(b) = 1 + Var(N_b) / E[N_b]²
```

**The bridge, exactly.** For one box covering the whole vector, `N_b` is the total mass, so
`L = 1 + Var/Mean² = Λ + 1`. CAS state lacunarity *is* the gliding-box statistic at the coarsest possible scale,
applied to a semantic vector instead of a positional one. What each adds:

| | CAS / Noetic lacunarity | Gliding-box lacunarity |
|---|---|---|
| Field | the 40-state vector (named cells) | per-token errors (positions) |
| Scale | one box: the whole architecture | a family of boxes `b` |
| Says | **which cell** is empty | **where in the sequence** error clusters |
| Blind to | position inside a sequence | the identity of the missing capability |

Neither subsumes the other. Together they give a coordinate: cell × position.

**Two more things the books add that a variance number cannot.**

1. **The lacunarity of silence** (manuscript lines 741–748): some Noetics *should* be quiet for a task. A surgeon
   needs `^8` and `^5` silent. Absence is a defect only when it is persistent and non-contextual, i.e. absent where
   the task requires it. Any use on CTT must therefore carry an **expected-state table** per task.
2. **Never-written versus faded** (CAS PCBA Engineer, Chapter 21, CMB): the board reports cells below a charge
   threshold (~0.05), but a zero reading has two causes: *never charged* (a true lacuna — needs exposure) or
   *charged and leaked* (a faded memory — needs rehearsal). Confusing them "leads to the wrong intervention". The
   glossary fixes the vocabulary: lacunarity = absent; leakage = present but producing the wrong output; inversion =
   present with reversed polarity.

## 2. First measured reading on the real corpus (today)

The mouth rows carry a conditioning state token, the tone tag `^n`. Counted over the frozen data:

| Split | Rows | `^1` Mind | every other Noetic |
|---|---|---|---|
| `mouth_train.jsonl` | 11,530 | **11,530** | 0 |
| `mouth_dev.jsonl` | 2,097 | **2,097** | 0 |

Exposure vector `[11530, 0, 0, 0, 0, 0, 0, 0, 0, 0]`:

```
Λ_exposure = Var/Mean² = 9.000000
```

That is three times the top of the "extreme" band in the book (`> 3.0`). Nine of the ten Noetic cells have **zero
charge in the tone tag** of this corpus. Per-state error lacunarity is degenerate (`0.000000`) for the same reason:
there is only one state to compare.

**Read this carefully, because the obvious interpretation is too strong.** The tone tag is the *conditioning* state
the trainer hands the model, not the full cognitive address of the reply. The content may exercise other Noetics
implicitly. What is measured here is narrow and exact: **the mouth has been taught one tone state and nine empty
ones.** The token-loss lacunarity of E1 cannot see this at all — it sees positions, not cells. That gap between the
two views is the reason to build the Noetic layer.

## 3. What a Noetic layer would compute for CTT

For every example, extract its address from the gold CAS material: noetic `^n`, domain `P/C/E/O`, drive `F1–F7`,
register `|T/|A/|f/|E`. Then, per checkpoint:

| Quantity | Definition | Source |
|---|---|---|
| Charge `E_s` | number of training rows whose address contains cell `s` | training data |
| Error `Err_s` | mean row NLL (or `1 − exact match`) on held-out rows addressing `s` | existing scoring |
| Gap class | **never-written** (`E_s` below floor), **faded** (`E_s` above floor, `Err_s` rising across checkpoints), **failing** (`E_s` high, `Err_s` high), **appropriately silent** (`E_s ≈ 0` and not required) | joins above |
| State lacunarity `Λ(p)` | `Var/Mean²` over the per-cell error or charge vector | CAS formula |
| Limiting reagent | from the v7.6 recipe view: `Θ(Ω) = Σ a_s·s`, the cell with the smallest `x_s / a_s` | production semantics |

The recipe view is the natural join. The CMB's tip-of-the-tongue example is exactly a limiting-reagent diagnosis:
addressing is fine, stored charge is the bottleneck, so rehearse rather than sharpen the cue. For CTT the same
question becomes: is the failing reply a *coverage* lacuna (never taught that cell), a *retention* lacuna (taught,
then degraded), or a *wrong-product* leakage (the cell fires, but composes the wrong reply)?

## 4. The experiment ladder, cheapest first

| Step | What | Cost | Decision it supports |
|---|---|---|---|
| N1 | Build the address table; per-cell charge and error at the checkpoints already produced | 0 USD, offline | which cells are empty, failing, or faded |
| N2 | Predictive test: does `Err_s` at checkpoint `t` predict held-out `Err_s` at `t + Δ`, controlling for `E_s`? Across the 3 seeds now running | 0 USD | whether a gap score is a *signal* rather than a description |
| N3 | One intervention: targeted replay of examples whose address contains the top gap cells, against random replay at equal compute | one short run | whether acting on the diagnosis helps |
| N4 | Only if N2 and N3 succeed: bounded per-cell weighting or learning-rate scaling | one run | whether it beats plain training |

Preregistered decision for N3 (proposal): targeted replay must beat random replay by at least **0.05** held-out NLL
on the cells it targets, in at least 2 of 3 seeds, with no degradation of more than 0.02 on the cells it does not
target. Otherwise: no gain.

## 5. Guardrails

1. **A Noetic label is a hypothesis, not a diagnosis.** The address comes from gold structure or an audited parser;
   an inference from error position alone is not a label.
2. **Silence needs a task table.** Per task, name the required cells. Absence outside that table is not a gap.
3. **The tone tag is a conditioning signal, not the content address.** Section 2's `Λ = 9.0` measures the tag, not
   the reply; a full reading needs the parsed target address.
4. **Coverage is a property of the data.** Fixing an empty cell is data work (examples), not optimisation.
5. **No label may change weights without a controlled trial.** The controller stays outside; the diagnosis proposes,
   the experiment decides.
6. **Keep the two measures separate in the record.** Numerical lacunarity is `L(b)` on token positions. Noetic
   lacunarity is `Λ` on the 40-cell vector. Reporting one as the other is the error the outside critique warned
   about, and it would be ours to make.

## 6. What would count as success, honestly stated

The thesis worth testing is narrow: *a Noetic gap score predicts later held-out failure better than exposure alone,
and a cheap intervention aimed at the gap improves held-out quality per unit of compute.* If that fails, the layer
still has value as a diagnostic map of what a corpus never taught, but it must not be described as accelerating
training.

## 7. Claim status

| Statement | Status |
|---|---|
| Mouth corpus tone tags use only `^1`: 11,530/11,530 train, 2,097/2,097 dev | `REAL` (counted today) |
| Exposure lacunarity of the tone tag is 9.000000, above the book's 3.0 extreme band | `REAL` for the tag, `PROPOSED` as a claim about the model |
| `Λ_CAS = L(b) − 1` when the box covers the whole vector | `DERIVED` (algebra) |
| Noetic gap score predicts later held-out failure | `NOT TESTED` |
| Targeted replay on gap cells improves held-out quality | `NOT TESTED` |
| Any training speed-up from the Noetic layer | `NOT CLAIMED` |
