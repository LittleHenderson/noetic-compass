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
- **Honest limit (recorded; language law):** under the default public-seed
  derivation the protected split is a pure function of the committed generator
  and public seed — anyone can reconstruct it, and it is NEVER called secret.
  The pre-registered digest guarantees INTEGRITY (Gate 1B cannot substitute a
  different set), not secrecy. Mitigation (STRENGTHENED at Gate 1A.1): the
  complete Gate 1B implementation is already committed and digest-pinned in
  `GATE1B_CODE_MANIFEST.json`, and the owner-signed approval binds it BEFORE any
  signature exists.
- **Commit-and-reveal salt option (owner decision, formalized per audit section
  9):** (1) the owner generates a random secret salt offline; (2) only
  `sha256(salt)` is committed pre-execution (the signed approval carries
  `protected_derivation_commitment: SALT_SHA256:<digest>`); (3) the generator
  derives the protected stream from
  `"CONSTRUCTION_GOLD_PROTECTED|20260831|<salt>"` (`--protected-salt-hex`,
  implemented); (4) the salt stays outside Claude's environment until the
  protected step of the sealed campaign; (5) after sealing, the owner reveals the
  salt for public reproduction. This keeps preregistration (the commitment),
  real secrecy during development, an integrity digest (recorded at owner-side
  generation), and eventual reproducibility. Default remains the public seed
  until the owner chooses.
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
