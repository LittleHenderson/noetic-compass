# Split grouping and protected evaluation — FROZEN law

## Anti-leakage grouping (the registered defense)

Splits are separated on BOTH axes that caused the historical template-prefix
memorization failure (a 97-percentage-point swing in an earlier lane):

| Split | Template families | Vocabulary bundle | Materialized in Gate 1A? |
|---|---|---|---|
| train | A, B | T | yes — `data/candidate/train.jsonl` |
| validation | C | V | yes — `data/candidate/val.jsonl` |
| protected | D | P | **NO** |

Bundles T, V, P are DISJOINT sets of minds, ideas, and part nouns (frozen inside the
generator). A protected passage therefore shares neither surface syntax family nor
content vocabulary with anything trained on.

## Protected-evaluation law

- The protected split is **never materialized, read, or inspected in Gate 1A**. The
  generator produces it in-memory with the frozen seed, round-trip-checks it, and
  records ONLY: its passage count, its per-class/question-type balance counts, and
  the SHA-256 digest of its canonical JSONL content. Those pre-registered values
  live in `DATASET_MANIFEST_CANDIDATE.json`.
- At Gate 1B, the AWS job regenerates the protected split from the same seed,
  verifies the digest matches the pre-registration (else `DATASET_INTEGRITY_FAILURE`
  and abort), and evaluates each arm on it EXACTLY ONCE, after all training of all
  arms and seeds is complete (exactly 3000 updates each; NO early stopping) and the
  layer choice L* is frozen in the receipt. The mandated S0/seed-11 duplicate run
  performs NO protected read (its determinism tolerance is measured on validation).
- **Honest limit (review finding, recorded):** the protected split is a pure
  function of the committed generator and public seed, so its secrecy is
  procedural, not technical — anyone running the public generator can reconstruct
  it. The pre-registered digest guarantees INTEGRITY (Gate 1B cannot substitute a
  different set), not secrecy. Registered mitigation: the complete Gate 1B
  training/evaluation code must be committed and digest-pinned BEFORE the protected
  step executes, and the independent audit verifies that ordering from git history.
  Strengthening options (owner decision, recorded in the freeze return): an
  owner-held salt folded into the protected generation seed (gains secrecy, loses
  the public pre-registered digest) versus the status quo.
- **Burned-split law:** the protected split is burned after ONE campaign. Any v2
  experiment must register a NEW protected derivation (new seed or salt) — reusing
  a read protected split is prohibited outright.
- No metric, threshold, arm, or analysis choice may be made after any protected
  number is seen. The deterministic status program (THRESHOLDS_AND_STATUS_LAW.yaml)
  reads the protected results and emits the status; prose does not.

## Validation use

The validation split is the ONLY tuning surface: layer selection (S0-only law),
learning-curve monitoring, and sanity checks. It licenses no claim.

## Amendments

Any change to splits, sizes, families, or bundles after this freeze requires an
entry in AMENDMENT_LOG.md BEFORE Gate 1B execution; amendments after any protected
read are prohibited outright.
