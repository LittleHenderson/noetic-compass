# Path D Wave 1A — Tokenizer v2 Coverage Report

**Date:** 2026-05-07
**Deliverable:** Path D Wave 1A — tokenizer expansion (`docs/working/path_D_corpus_pipeline_design_2026_05_07.md` §7)
**Artifact:** `cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json`
**Manifest:** `cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07_manifest.json`
**Test:** `cas-native/tests/tokenizer/test_path_d_vocab_coverage.py` (119 tests, all passing)

## 1. Outcome

109 of 110 enumerated CAS surface-form constructs now encode as a single
token id under the v2 vocab. The single non-single-token entry — `→ Ω`
— is correctly multi-token by CAS grammar (whitespace separates the
recipe arrow `→` from the production target `Ω`); each piece individually
encodes as one token.

The closes the v0 meta_logic 14-token vocab gap (memory
`project_v76_metalogic_two_failure_modes_2026_05_04.md`) and the
forgotten-Cognitive-Fractal-keywords gap (`feedback_cas_token_enum_must_include_metalogic_and_fractals.md`).

| Vocab axis            | Before | After |
|-----------------------|-------:|------:|
| SPECIAL_TOKENS        |     15 |    15 |
| CAS_RESERVED_TOKENS   |    198 |   253 |
| char tokens (default) |    120 |   120 |
| **Total**             |  **333** | **388** |
| Tokens added          |      — |    55 |

ID stability: every v1 token's id is preserved verbatim in v2 (verified
in `test_v1_token_ids_preserved_in_v2_vocab`). The 55 added tokens are
appended at the END of the reserved-token list, so all v1 IDs in the
range 0..332 are unchanged.

## 2. Per-category coverage

### Category 1 — State literals (54/54)

- 10 single-Noetic atoms `^0`..`^9` — already present (v1).
- 4 standalone domain markers `^P`, `^C`, `^E`, `^O` — already present (v1).
- **40 compound state literals `^N^D` (the patent-named 40 Cognitive
  States)** — ADDED. Order: `^0^P, ^0^C, ^0^E, ^0^O, ^1^P, ...` (Noetic
  varies fastest). Activation requires the v2-aware dynamic-regex hook
  (see §5).

### Category 2 — Drive subscripts (21/21)

- 7 bare drives `F1`..`F7` — already present (v1).
- 7 underscore-prefixed `F_1`..`F_7` (CAS v7.5 notation) — already
  present (v1).
- **7 wrapped subscript forms `_{F1}`..`_{F7}`** — ADDED. The
  longest-prefix reserved-token matcher claims the 5-char wrapper over
  the 2-char `_{` prefix.

### Category 3 — Register tags (6/6)

- 4 single-register suffixes `|T`, `|A`, `|f`, `|E` — already present (v1).
- Register-set closer `⟩` — already present (v1).
- **Register-set opener `|⟨`** for CAS v7.7 `|⟨T,A,f⟩` — ADDED.

### Category 4 — Operators (7/7)

All present in v1: `+`, `×`, `→`, `∘`, `=`, `Ω`, `Ω_`.

### Category 5 — Production-recipe markers (1/2 single-token; both pieces single)

- `Θ` — already present (v1).
- `→ Ω` — TWO TOKENS BY DESIGN. The CAS grammar uses whitespace to
  separate the arrow from the production target; `→` and `Ω`
  individually encode as single tokens. No vocab change required.

### Category 6 — Meta-logic constructors (14/14)

All present in v1: `NoeticCluster`, `StateSet`, `RelationCluster`,
`Tuple`, `Coordinate`, `Product`, `CoverOf`, `PartitionOf`, `∪`, `∩`,
`∖`, `∈`, `⊆`, `let`. The audit confirms the v1 vocab DOES include the
14 meta-logic constructors that memory `project_v76_metalogic_two_failure_modes_2026_05_04.md`
flagged. The v0 evaluation failure on the meta_relations bucket was
NOT due to the constructor tokens being absent — it was due to the
state-literal / register-set / drive-subscript fragmentation cascade
that surrounded the constructors in compound expressions. v2 closes
that surrounding fragmentation.

### Category 7 — Cognitive Fractal operators (6/6)

- Angle brackets `⟨`, `⟩` — already present (v1; shared with cat 3).
- Colon `:` (fractal-sequence delimiter) — already present (v1).
- Greek `Φ` and ASCII alias `Phi` — already present (v1).
- **`FractalClass` keyword** — ADDED. Plus the four IFS-stability
  discriminants `Stabilizing`, `Amplifying`, `Oscillatory`, `Neutral`,
  plus `FractalConvergence`, `CognitiveFractal` from
  `cas-native/inference/ood_gate.py`.

## 3. Summary of tokens added (55 total)

| Category | Count | Surfaces |
|---|---:|---|
| 1 — compound state literals | 40 | `^0^P` … `^9^O` |
| 2 — drive-subscript wrappers | 7 | `_{F1}` … `_{F7}` |
| 3 — register-set opener | 1 | `\|⟨` |
| 7 — fractal class keywords | 7 | `FractalClass`, `FractalConvergence`, `CognitiveFractal`, `Stabilizing`, `Amplifying`, `Oscillatory`, `Neutral` |

ID range of added tokens: 333–387. All v1 IDs (0..332) preserved.

## 4. Compound-expression tightness

Path D-relevant CAS expressions tokenize tightly under v2:

| Expression | v1 tokens | v2 tokens |
|---|---:|---:|
| `^2^P_{F2}\|A` | 6 | **3** |
| `(^3^P\|A × ^3^P\|f) = ^3^P\|Ω_refusal` | 18 | **15** |
| `^3^P\|⟨A,f,T⟩` | 10 | **8** |
| `FractalClass.Stabilizing` | 24 | **3** |

The `^N^D` collapse from 2 tokens to 1 is the largest gain — every
state literal in the 40-state grammar drops one token, so a typical
20-state expression saves ~20 tokens of context budget in addition to
removing the silhouette-without-content tokenization risk that drove
v0's evaluation fragility.

## 5. Implementation: v2-aware dynamic regex

The v1 dynamic regex (`_DYNAMIC_CAS_PATTERNS`) matches `\^\d+`
greedily, claiming `^2` from `^2^P` before the longer reserved token
`^2^P` can be considered. The v2 patch prepends a
`\^\d+\^[PCEO]` pattern, but ONLY when the corresponding v2 tokens
are in vocab:

```python
patterns: list[str] = []
if "^0^P" in self.word2id:
    patterns.append(_DYNAMIC_CAS_PATTERNS_V2_COMPOUND_STATE)
if "_{F1}" in self.word2id:
    patterns.append(_DYNAMIC_CAS_PATTERNS_V2_DRIVE_SUBSCRIPT)
patterns.extend(_DYNAMIC_CAS_PATTERNS)
self._dynamic_re = re.compile("|".join(f"(?:{p})" for p in patterns))
```

Backward compatibility: existing v1 tokenizer.json files on disk (e.g.
`tmp/native_nl_b3_smoke_50k_20260507/tokenizer.json`) load without
`^0^P` in vocab, so the v2 patterns are NOT prepended; the dynamic
regex is bit-identical to v1. Verified by
`test_v1_only_vocab_load_preserves_v1_tokenization`.

## 6. Audit findings flagged for follow-up

1. **Parametric `Ω_NAME` emergents fragment to char tokens under
   frozen mode.** The dynamic regex `Ω_[A-Za-z][A-Za-z0-9_]*` matches
   `Ω_safe_judgment` but the full string isn't in vocab → frozen mode
   falls through to char tokens. The `Ω_` prefix morpheme IS in vocab,
   but the current tokenizer logic doesn't fall back to a shorter
   prefix when the dynamic match isn't in vocab. Path D corpus
   generation should pre-register the specific `Ω_NAME` strings that
   appear in the corpus before freezing the tokenizer for that run.
   Alternatively, a future tokenizer logic change (Wave 2+) could
   implement prefix-fallback decoding.

2. **Cognitive Fractal index digits inside `⟨3:8:5:2⟩` tokenize as
   char tokens.** The 7-category spec did not list digits 0-9, and
   compiler grammar treats them as `TokenKind.NUMBER` integer literals
   (multi-digit). Adding bare 0-9 as single tokens would conflict with
   word-regex `[A-Za-z0-9_]+` greedy matching in the tokenize loop.
   Defer to a Wave 2 audit if the Path D corpus shows fractal-index
   accuracy regressions.

3. **`→ Ω` is whitespace-separated by CAS grammar.** Treated as 2
   tokens. No vocab change needed; documented for future agents who
   may misread the spec as requiring a fused token.

4. **Meta-logic constructors (`NoeticCluster` et al.) were already in
   v1 vocab.** Memory `project_v76_metalogic_two_failure_modes_2026_05_04.md`
   flagged a 53.6% failure on meta_relations — that failure was
   ALMOST CERTAINLY the surrounding-state fragmentation, not the
   constructor tokens themselves. The v2 patch closes the surrounding
   fragmentation. Wave 4 corpus eval (deliverable H) should re-measure
   the meta_relations bucket on a v2-tokenized corpus to validate.

## 7. References

- Sprint kickoff: `docs/working/path_D_corpus_pipeline_design_2026_05_07.md`
- Path D runbook: `docs/working/path_D_compiler_fluency_curriculum_2026_05_07.md`
- 7-category coverage rule: memory `feedback_cas_token_enum_must_include_metalogic_and_fractals.md`
- v0 failure record: memory `project_v76_metalogic_two_failure_modes_2026_05_04.md`
- Authoritative grammar: `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`
- Tokenizer module: `noetic-compass-scaffold/noetic-compass/cas-native/training/tokenizer.py`
- v1 reference artifact: `tmp/native_nl_b3_smoke_50k_20260507/tokenizer.json`
- English BPE companion (unchanged): `cas-synthetic/data/native_nl/english_bpe_50k_20260507.json`
