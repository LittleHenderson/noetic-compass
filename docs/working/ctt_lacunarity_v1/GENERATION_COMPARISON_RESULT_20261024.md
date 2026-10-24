# Generation-level result — the early-stopping hypothesis fails (2026-10-24)

> **CORRECTION (2026-10-24, after independent verification; see `LAC-00_EVIDENCE_LEDGER.md` §3).**
> A second deviation was found: the preregistration defines each rate over **all 1,517 items** (non-fact replies
> count as round-trip passes), but the implementation used the **800 fact rows**. Under the prereg-literal
> denominators the composites are A4-s1 0.197192 → 0.267512, A4-s2 0.216385 → 0.277804, A4-s3 0.216260 → 0.289607
> (early → final). The decision is unchanged — the final checkpoint still wins by more than 0.02 in 3 of 3 — but the
> numbers below are not the preregistered metric.

Status: **diagnostic, not claim-bearing** (local GPU; the AWS rule reserves claim-bearing neural runs for AWS).
Numbers `REAL`. Preregistration: `PREREGISTRATION_GENERATION_COMPARISON_20261024.md`.

## 1. What was run

Six models: three seeds (A4-s1, A4-s2, A4-s3) at step 1,000 and step 6,000, each answering the same 1,517 exam
inputs with the frozen mouth decoding path — top-p 0.9, whole-word lock, per-item seed from input text and situation.
Every attempted reply is counted; nothing is dropped.

Scoring, exactly as preregistered except one documented deviation:

| Component | Definition |
|---|---|
| Guard | `mouth_task.check` on the reply against its situation, input and reading |
| Fact exactness | reply passes the guard and contains no word outside the function words plus the words of the input |
| Read-back | **one fixed listener** (the ear before mouth training, seed A4-s1) reads a fact reply back; the reading must match the fact the reply was asked about. A fact reply that failed the guard is a read-back failure, not an omission |
| Composite | guard rate × fact-exact rate × read-back rate, each over its own denominator |

**Documented deviation:** the frozen protocol uses three ear copies with a unanimous vote. The three pre-training
copies disagreed (two produced empty readings), so a single fixed listener was used for all six models. A fixed
listener is the fair choice for a comparison, but it is not the frozen rule and is recorded as a deviation.

## 2. Results (all three seeds, 1,517 replies each, 800 fact replies each)

| Model | Guard | Fact exact | Read-back | Composite |
|---|---|---|---|---|
| A4-s1 step 1,000 | 0.761371 | 0.715000 | 0.406250 | **0.221155** |
| A4-s1 step 6,000 | 0.845748 | 0.817500 | 0.495000 | **0.342243** |
| A4-s2 step 1,000 | 0.802900 | 0.730000 | 0.431250 | **0.252763** |
| A4-s2 step 6,000 | 0.864865 | 0.825000 | 0.503750 | **0.359432** |
| A4-s3 step 1,000 | 0.793672 | 0.723750 | 0.457500 | **0.262797** |
| A4-s3 step 6,000 | 0.875412 | 0.836250 | 0.526250 | **0.385248** |

| Seed | Early | Final | Difference (final − early) |
|---|---|---|---|
| A4-s1 | 0.221155 | 0.342243 | **+0.121088** |
| A4-s2 | 0.252763 | 0.359432 | **+0.106669** |
| A4-s3 | 0.262797 | 0.385248 | **+0.122451** |

**Decision: the early-stopping hypothesis FAILS, in the opposite direction.** The preregistered rule required the
early checkpoint to beat the final one by at least 0.02 in at least 2 of 3 seeds. The final checkpoint beats the early
one by 0.107 to 0.122 in **3 of 3 seeds**, and it wins on every component in every seed. This is a `FAILED` result
for the early-stopping hypothesis and it stays in the record as such.

## 3. What this means

**Prediction loss was a misleading proxy here.** On held-out next-token loss the early checkpoint looked better in
all three seeds (−0.45 to −0.49). On the task the mouth actually performs — writing a guarded, fact-exact,
read-back-consistent reply — the later checkpoint is clearly better. Choosing a checkpoint on next-token loss would
have selected the worse writer.

**This is exactly the distinction the experiment was built to test,** and the answer is unambiguous at this
evaluation. It also means no protocol change is proposed: the frozen "train to 6,000 and score the final" rule is
vindicated for this configuration.

**What it does not say.** It does not say more training always helps (one configuration, one model, 6,000 steps), and
it does not identify *what* the extra 5,000 steps improved. The components suggest better task compliance rather than
better fit to the training mix, but that is a hypothesis for the next analysis, not a result.

**One caution about the listener.** The single-listener deviation affects the absolute read-back numbers. Because the
same listener scores all six models, the comparison stands, but the absolute rate would change under the frozen
three-vote rule.

## 4. Claim status

| Statement | Status |
|---|---|
| Final checkpoint beats early on the composite in 3 of 3 seeds: +0.121088, +0.106669, +0.122451 | `REAL` |
| Final wins every component in every seed | `REAL` |
| The preregistered early-stopping hypothesis fails | `REAL` decision, kept as a failure |
| Prediction loss was a misleading checkpoint signal for generation | `PROPOSED` — true for this configuration; needs a second model family |
| What the extra 5,000 steps improved | `NOT MEASURED` — N1's question |
| Claim-bearing status | **NONE** (local GPU diagnostic) |

## 5. Artifacts

- Generation files: `cs_aws/generation/gen_<seed>_<checkpoint>.jsonl`, 1,517 rows each.
- Scored files: `cs_aws/scored/*.scored.jsonl`, with per-reply guard, fact and read-back fields.
- Runners: `lacunarity_e1/gen_one.py`, `rt_score.py`, `composite.py`.
- Checkpoints: `cs_aws/results/out/<seed>/` (18 files, sha256 recorded in each `WEIGHTS_MANIFEST.json`).
- Cost: generation and scoring local, **0 USD**; the AWS training that produced the checkpoints cost about 1.2 USD,
  total 2.4 USD as approved.
