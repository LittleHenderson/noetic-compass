# Native NL Tokenizer Extension — Spec (2026-05-04)

Author: Tokenizer Extension Agent (Opus 4.7)
Status: Implementation landed alongside this doc.
Companion code: `cas-native/training/english_bpe_extension.py`
Companion tests: `cas-native/tests/training/test_english_bpe_extension.py`

## §1 Goal

The CAS-Native English generation head (Version B, Phase 4 — NL Generation
Head) needs an English vocabulary that the existing `HybridCASTokenizer` does
not provide. The hybrid tokenizer was designed to keep CAS structural symbols
exact and to fall back to per-character `<CHAR:HEX>` tokens for everything
else. That works for a structured-prediction classifier whose outputs are CAS
labels, but it is too coarse for an English decoder: an autoregressive head
that must emit words one BPE piece at a time will fragment every English word
into single characters and burn its sequence-length budget on byte-level
fluff.

The fix is an **English BPE extension**: a byte-level BPE vocabulary trained
**from scratch** on the project's own SDG corpus
(`cas-synthetic/data/native_nl/v1_seed_5k.jsonl`, produced by the parallel
SDG agent), composed on top of the existing CAS reserved vocabulary so that:

1. CAS structural tokens (vocab14 reserved + 12-head structured-prediction
   tokens) keep priority and stable low IDs.
2. English text gets compact BPE pieces instead of character fallback.
3. No foreign pretrained tokenizer is loaded. Ever. Per user-ratified rule
   from 2026-05-04: "CAS gets the glory or the project doesn't ship."
4. Every tokenizer artifact is fully traceable: corpus hash, vocab version,
   merge count, training timestamp.

This document specifies the extension; the implementation is in
`english_bpe_extension.py` and the tests are in
`tests/training/test_english_bpe_extension.py`.

## §2 Vocab partition strategy

The combined vocabulary is layered, not merged:

```
ID range        | Source                          | Priority | Mutability
0 ..  N_CAS-1   | CAS reserved (existing tokenizer) | High   | Frozen forever
N_CAS .. N_TOTAL-1 | English BPE pieces             | Low     | Versioned
```

`N_CAS` is read live from `HybridCASTokenizer.vocab_size` at compose time. As
of this writing, the base hybrid tokenizer ships with ~250 reserved tokens
(15 specials + ~200 CAS structural + character fallback). The English BPE
extension adds 16K-32K pieces on top.

**Why CAS gets the low IDs:** stability across vocab updates. If a
downstream embedding table is keyed on token IDs, retraining English BPE
must never renumber CAS tokens. The compose function asserts that every CAS
token-to-ID mapping in the base tokenizer survives unchanged into the
extended tokenizer.

**Why we don't merge into a single BPE pass:** byte-level BPE applied over a
mixed CAS+English corpus would split CAS literals like `^3^P|A` into garbage
pieces (`^3`, `^`, `P`, `|A`) whose interpretation depends on which merges
fired. Since CAS structural tokens are load-bearing for the model's
classifier head, we keep them as atomic reserved tokens and only run BPE
over the English remainder.

**Tokenization order:** at encode time, the extended tokenizer runs the
existing reserved-token-prefix matcher first (so `^3^P|A` is recognized as
a single token), then byte-level BPE on whatever runs of text fall between
reserved tokens. Decoded output is the concatenation of reserved-token
surfaces and BPE-decoded byte spans.

## §3 BPE training procedure

We use a stdlib + numpy implementation of byte-level BPE. The algorithm is
the classic Sennrich/Wang one — repeatedly find the most frequent adjacent
pair of pieces in the training corpus and merge it into a new piece — but
operating on raw UTF-8 bytes (not Unicode code points) so we sidestep NFC
normalization entirely.

**Inputs:**
- `corpus_path` — path to a JSONL file with `prompt` + `reply` (or
  equivalents) on each line. The training script reads
  `record.get("prompt") or record.get("user_prompt")` and similarly for the
  reply, concatenated with a separator.
- `vocab_size` — target English vocab size (default 24,000).
- `min_frequency` — minimum count for a merge to be admitted (default 2).
- `output_path` — JSON file to write the trained merges + provenance to.

**Algorithm:**

1. Read corpus, extract `prompt + reply` text per record.
2. Compute SHA-256 of the canonical JSONL bytes — this is
   `trained_from_corpus_hash`.
3. Encode every word to UTF-8 bytes, then split into per-byte symbols.
   Initial vocabulary: 256 byte symbols + a small set of specials
   (`<bpe_pad>`, `<bpe_unk>`, `<bpe_bow>`, `<bpe_eow>`).
4. Count adjacent-pair frequencies across the whole corpus.
5. Greedily pick the most frequent pair (with deterministic tie-break on
   the lexicographic ordering of the pair), record the merge, apply it to
   the corpus, and recount.
6. Stop when `vocab_size` is reached or no pair has count >= `min_frequency`.

**Determinism:** the merge selection uses a strict
`(-count, pair_lex_order)` sort key, so identical input corpora produce
byte-identical merge sequences. A test
(`test_same_corpus_produces_same_merges`) hashes the merge list and locks
this contract.

**No foreign pretrained merges:** the entire merge list is computed inside
the function from the supplied corpus. There is no `from_pretrained()`,
no HuggingFace download, no sentencepiece model file. The implementation
imports only `hashlib`, `json`, `re`, `collections`, `pathlib`, `time`, and
the existing `cas_native.training.tokenizer` module. (Numpy is allowed but
the reference implementation uses only stdlib because BPE training on 5K
records is fast in pure Python.)

**Hyperparameters used for v1 SDG seed run (5K records):**
- `vocab_size = 24000` (target; final size will be smaller because rare
  pairs get filtered by `min_frequency`).
- `min_frequency = 2`.
- Special tokens preserved at fixed positions: `<bpe_pad>`, `<bpe_unk>`,
  `<bpe_bow>`, `<bpe_eow>`. These are NOT BPE-merged; they exist in the
  English vocab table only as IDs that BPE never produces from input
  (the encoder skips them, the decoder elides them when not requested).

## §4 Object traceability fields

The output JSON artifact carries these fields. Every field is required:

| Field | Type | Meaning |
|---|---|---|
| `vocab_version` | str | semver, currently `"english_bpe.v1.0"` |
| `trained_from_corpus_hash` | str | SHA-256 hex of the input JSONL bytes |
| `trained_from_corpus_path` | str | absolute path of the input file |
| `trained_at_timestamp` | str | ISO8601 UTC at training start |
| `bpe_merge_count` | int | number of merges learned |
| `english_vocab_size` | int | total English vocab including bytes + specials + merges |
| `cas_reserved_token_count` | int | for the composed extended tokenizer, the number of CAS reserved IDs that prefix the English vocab |
| `min_frequency` | int | training hyperparameter |
| `target_vocab_size` | int | training hyperparameter |
| `merges` | list[list[str, str]] | ordered merge pairs |
| `byte_to_id` | dict[str, int] | base byte alphabet (256 entries) |
| `merge_to_id` | dict[str, int] | merged-piece-to-ID mapping (just IDs) |
| `special_to_id` | dict[str, int] | BPE-side specials |

**Provenance flow into tokenization:** every call to
`tokenize_with_provenance(text, tokenizer)` returns a dict with the
tokenization output plus a `vocab_version` field copied from the
tokenizer's metadata. This is the architectural-spine traceability rule
(per `HONEST_STATUS.md`'s "★ Architectural spine: TRACEABILITY" section):
no tokenization ever travels through the system without its vocab version
attached.

## §5 Integration points

The extended tokenizer is exposed via two surfaces:

### `ExtendedHybridCASTokenizer`

A thin wrapper around `HybridCASTokenizer` that owns:
- The base `HybridCASTokenizer` instance (frozen).
- A loaded English BPE artifact (vocab + merges + provenance).
- A composed `id_to_token` table where IDs `0..N_CAS-1` come from the base
  hybrid tokenizer and IDs `N_CAS..N_TOTAL-1` come from the English BPE
  vocab (offset by `N_CAS`).

The extended tokenizer exposes `encode(text)`, `decode(ids)`, and
`tokenize(text)` with the same signatures as the base class. Backward-
compatible: any caller that has a `HybridCASTokenizer` reference can be
replaced with an `ExtendedHybridCASTokenizer` without code change.

### `tokenizer.py` modifications

Minimal. We add an opt-in path: if the caller passes
`english_bpe_path=...` to a new `HybridCASTokenizer.with_english_bpe(path)`
classmethod, the returned object is an `ExtendedHybridCASTokenizer`.
Existing callers (training, eval, predict_cas) are unchanged because they
never pass that argument.

The `cas-native/tokenizer/__init__.py` re-exports
`ExtendedHybridCASTokenizer` from
`cas_native.training.english_bpe_extension` so notebooks can import it
from a single canonical location.

## §6 Testing strategy

12+ tests in `cas-native/tests/training/test_english_bpe_extension.py`.

Test categories:

1. **Roundtrip identity** — `decode(encode(x)) == x` for ASCII, multi-byte
   UTF-8, and CAS-mixed text.
2. **Reserved-token preservation** — every CAS reserved token in the base
   tokenizer keeps its ID after composition; the extended tokenizer's
   `id_to_token[id]` for `id < N_CAS` matches the base tokenizer's
   mapping exactly.
3. **Determinism** — training the same corpus twice produces byte-identical
   merge lists. Hash of the merges is asserted constant.
4. **Different corpus produces different merges** — sanity check that BPE
   isn't ignoring its input.
5. **Vocab cap** — `english_vocab_size <= target_vocab_size` always.
6. **Min-frequency** — merges with count below threshold are dropped.
7. **Provenance fields populated** — all 6 required fields present and
   well-typed in the output JSON.
8. **Tokenization output carries `vocab_version`** — end-to-end provenance
   on every encode call.
9. **Backward compatibility** — `HybridCASTokenizer` callers that don't
   touch the extension still work.
10. **Corpus hash detection** — re-running with a corpus modified by one
    byte produces a different `trained_from_corpus_hash`.
11. **Merge order stability** — the i-th merge in the saved JSON is
    reproducibly the i-th merge selected during training.
12. **End-to-end** — train BPE from a fixed mini-corpus, save artifact,
    load it, compose with the base hybrid tokenizer, encode + decode a
    sample CAS+English string, verify both CAS literals and English
    BPE pieces survive the roundtrip.

The tests use a synthetic mini-corpus of ~50 lines so they run in <2s on
CPU and don't depend on the SDG agent's output.

---

## Open assumptions worth flagging

- **Word boundary handling:** v1 uses simple whitespace + punctuation
  splitting before BPE. A future v2 could introduce GPT-2-style
  byte-pair-encoding-with-spaces, but for an English corpus of CAS-themed
  text the simple variant should produce reasonable pieces; we'll measure
  on the SDG corpus and revise if the average pieces-per-word is too high.
- **Vocab size 24K:** chosen to be in the same ballpark as small modern
  encoder-decoders (BERT 30K, GPT-2 50K). A 5K-record SDG corpus probably
  won't actually produce 24K useful merges; the cap is a ceiling, not a
  target. We'll report the actual size in the manifest.
- **Multi-corpus future:** when the SDG corpus scales from 5K to 100K+
  the BPE should be retrained from scratch on the larger corpus. The
  `vocab_version` field will bump (`v1.0` -> `v1.1`) and the corpus hash
  field will change accordingly. Models trained against v1.0 must be
  finetuned (or have their embedding table extended) to consume v1.1.
