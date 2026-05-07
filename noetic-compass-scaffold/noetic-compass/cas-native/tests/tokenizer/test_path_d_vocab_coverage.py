"""Path D Wave 1A — tokenizer vocab coverage tests.

These tests pin down the seven-category surface-form coverage rule
(see ``docs/working/path_D_corpus_pipeline_design_2026_05_07.md`` and
memory ``feedback_cas_token_enum_must_include_metalogic_and_fractals.md``).
Every token in each of the seven categories must encode as a SINGLE
token id under the v2 hybrid CAS tokenizer.

The tests also pin down v1 backward compatibility: existing v1 vocabs
(without the v2 compound-state-literal and drive-subscript-wrapper
tokens) must continue to tokenize identically to before the patch.

Coverage report and provenance manifest:
  - cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json
  - cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07_manifest.json
  - docs/working/path_D_tokenizer_v2_coverage_2026_05_07.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cas_native.training.tokenizer import (
    CAS_RESERVED_TOKENS,
    HybridCASTokenizer,
    SPECIAL_TOKENS,
)


# ---------------------------------------------------------------------------
# Category enumerations — exact surface forms the v2 vocab promises to
# encode as single tokens. These lists are the contract.
# ---------------------------------------------------------------------------

# Category 1: State literals.
#   * 10 single-Noetic atoms `^0`..`^9`
#   * 4 standalone domain markers `^P`, `^C`, `^E`, `^O`
#   * 40 compound state literals `^N^D` (N in 0..9, D in {P,C,E,O})
CATEGORY_1_STATE_LITERALS: list[str] = (
    [f"^{i}" for i in range(10)]
    + [f"^{d}" for d in "PCEO"]
    + [f"^{n}^{d}" for n in range(10) for d in "PCEO"]
)

# Category 2: Drive subscripts.
#   * 7 bare drive primitives `F1`..`F7`
#   * 7 underscore-prefixed primitives `F_1`..`F_7` (CAS v7.5 notation)
#   * 7 wrapped subscript forms `_{F1}`..`_{F7}` (in-state notation)
CATEGORY_2_DRIVE_SUBSCRIPTS: list[str] = (
    [f"F{i}" for i in range(1, 8)]
    + [f"F_{i}" for i in range(1, 8)]
    + [f"_{{F{i}}}" for i in range(1, 8)]
)

# Category 3: Register tags.
#   * 4 single-register suffixes `|T`, `|A`, `|f`, `|E`
#   * Register-set opener `|⟨` and closer `⟩` for `|⟨T,A,f⟩` notation.
CATEGORY_3_REGISTER_TAGS: list[str] = ["|T", "|A", "|f", "|E", "|⟨", "⟩"]

# Category 4: Operators.
CATEGORY_4_OPERATORS: list[str] = ["+", "×", "→", "∘", "=", "Ω", "Ω_"]

# Category 5: Production-recipe markers.
#   The recipe arrow `→ Ω` is a TWO-token sequence by CAS grammar
#   (whitespace separates `→` from `Ω`); each piece must individually
#   be a single token, but the joint `→ Ω` is not in the contract.
CATEGORY_5_PRODUCTION_MARKERS: list[str] = ["Θ", "→", "Ω"]

# Category 6: Meta-logic constructors and operators.
CATEGORY_6_METALOGIC: list[str] = [
    "NoeticCluster",
    "StateSet",
    "RelationCluster",
    "Tuple",
    "Coordinate",
    "Product",
    "CoverOf",
    "PartitionOf",
    "∪",
    "∩",
    "∖",
    "∈",
    "⊆",
    "let",
]

# Category 7: Cognitive Fractal operators / keywords.
CATEGORY_7_FRACTALS: list[str] = [
    "⟨",
    "⟩",
    ":",
    "FractalClass",
    "Φ",
    "Phi",
]

ALL_CATEGORIES: dict[str, list[str]] = {
    "1_state_literals": CATEGORY_1_STATE_LITERALS,
    "2_drive_subscripts": CATEGORY_2_DRIVE_SUBSCRIPTS,
    "3_register_tags": CATEGORY_3_REGISTER_TAGS,
    "4_operators": CATEGORY_4_OPERATORS,
    "5_production_markers": CATEGORY_5_PRODUCTION_MARKERS,
    "6_metalogic": CATEGORY_6_METALOGIC,
    "7_fractals": CATEGORY_7_FRACTALS,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def v2_tokenizer() -> HybridCASTokenizer:
    """The v2 hybrid CAS tokenizer (default-built, frozen)."""
    tok = HybridCASTokenizer()
    tok.freeze()
    return tok


def _repo_root() -> Path:
    """Resolve the tksCAS repo root from this test file's location.

    test_path_d_vocab_coverage.py lives at:
      tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/tests/tokenizer/
    so parents[5] is the repo root.
    """
    return Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def v2_artifact_path() -> Path:
    return _repo_root() / "cas-synthetic" / "data" / "native_nl" / "cas_hybrid_tokenizer_v2_2026_05_07.json"


@pytest.fixture(scope="module")
def v2_manifest_path() -> Path:
    return _repo_root() / "cas-synthetic" / "data" / "native_nl" / "cas_hybrid_tokenizer_v2_2026_05_07_manifest.json"


# ---------------------------------------------------------------------------
# Per-category single-token tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("category", "surface"),
    [(cat, s) for cat, surfaces in ALL_CATEGORIES.items() for s in surfaces],
    ids=[f"{cat}__{s}" for cat, surfaces in ALL_CATEGORIES.items() for s in surfaces],
)
def test_each_category_token_encodes_as_single_token(
    v2_tokenizer: HybridCASTokenizer, category: str, surface: str
) -> None:
    """Every category-7 surface form must encode to exactly one token id.

    This is the core Path D Wave 1A contract: every CAS surface-form
    construct is representable as a single token, so v0's silent
    multi-token fragmentation (which caused the v76_metalogic 53.6%
    failure on meta_relations) cannot recur on the Path D corpus.
    """
    ids = v2_tokenizer.encode(surface, add_special=False)
    assert v2_tokenizer.UNK_ID not in ids, (
        f"category={category!r} surface={surface!r} produced UNK"
    )
    assert len(ids) == 1, (
        f"category={category!r} surface={surface!r} expected 1 token id, "
        f"got {len(ids)}: ids={ids} pieces={v2_tokenizer.token_ids_to_tokens(ids)}"
    )
    assert surface in v2_tokenizer.word2id, (
        f"category={category!r} surface={surface!r} missing from vocab"
    )


# ---------------------------------------------------------------------------
# Compound-expression tests — Path D-relevant compositions tokenize tightly.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("expr", "expected_token_count"),
    [
        # Compound state with drive and register: 3 tokens (^N^D, _{Fk}, |R)
        ("^2^P_{F2}|A", 3),
        # Multi-state co-presence: 15 tokens including spaces
        ("(^3^P|A × ^3^P|f) = ^3^P|Ω_refusal", 15),
        # Register-set occupancy
        ("^3^P|⟨A,f,T⟩", 8),
    ],
)
def test_compound_expressions_tokenize_tightly(
    v2_tokenizer: HybridCASTokenizer, expr: str, expected_token_count: int
) -> None:
    """Verify Path D-relevant compound expressions reach the v2 tightness."""
    ids = v2_tokenizer.encode(expr, add_special=False)
    assert v2_tokenizer.UNK_ID not in ids, f"expr={expr!r} produced UNK"
    assert len(ids) == expected_token_count, (
        f"expr={expr!r} expected {expected_token_count} tokens, got {len(ids)}: "
        f"{v2_tokenizer.token_ids_to_tokens(ids)}"
    )


# ---------------------------------------------------------------------------
# v1 ID-stability test — every v1 token's ID is preserved in v2.
# ---------------------------------------------------------------------------

V2_ADDED_TOKENS: frozenset[str] = frozenset(
    [f"^{n}^{d}" for n in range(10) for d in "PCEO"]
    + [f"_{{F{i}}}" for i in range(1, 8)]
    + ["|⟨"]
    + [
        "FractalClass",
        "FractalConvergence",
        "CognitiveFractal",
        "Stabilizing",
        "Amplifying",
        "Oscillatory",
        "Neutral",
    ]
)


def test_v1_token_ids_preserved_in_v2_vocab(v2_tokenizer: HybridCASTokenizer) -> None:
    """Reconstruct the v1 reserved-token ordering and verify ID stability.

    This is the load-bearing constraint from the Path D Wave 1A spec:
    "preserve all existing tokens and IDs." If a v1 token's ID shifted,
    every existing v1-trained checkpoint would silently mis-tokenize.
    """
    # Re-derive the v1 reserved-token list by removing the v2 additions.
    v1_only_reserved = [t for t in CAS_RESERVED_TOKENS if t not in V2_ADDED_TOKENS]

    # The v1 reserved list, plus SPECIAL_TOKENS, is what the v1 tokenizer
    # added in order. We compare expected v1-IDs to v2 vocab IDs.
    expected_id = 0
    for tok in SPECIAL_TOKENS:
        assert v2_tokenizer.word2id[tok] == expected_id, (
            f"Special token {tok!r} ID shifted: expected {expected_id}, "
            f"got {v2_tokenizer.word2id[tok]}"
        )
        expected_id += 1
    for tok in v1_only_reserved:
        assert v2_tokenizer.word2id[tok] == expected_id, (
            f"v1 reserved token {tok!r} ID shifted: expected {expected_id}, "
            f"got {v2_tokenizer.word2id[tok]}"
        )
        expected_id += 1


def test_v1_only_vocab_load_preserves_v1_tokenization() -> None:
    """A v1-shaped vocab (no v2 tokens) tokenizes identically to v1.

    This is the backward-compat guarantee: existing v1 tokenizer.json
    artifacts on disk (e.g. tmp/native_nl_b3_smoke_50k_20260507/) must
    not behave differently after this patch. The dynamic regex includes
    the compound `^N^D` pattern only when the corresponding v2 tokens
    are present in vocab.
    """
    # Build a v1-equivalent vocab by stripping the v2 additions.
    full = HybridCASTokenizer()
    full.freeze()
    v1_token_to_id = {
        tok: idx for tok, idx in full.word2id.items() if tok not in V2_ADDED_TOKENS
    }
    v1_sim = HybridCASTokenizer(token_to_id=v1_token_to_id, frozen=True)

    # Under v1 semantics, `^2^P_{F2}|A` decomposes to 6 tokens (the v1
    # baseline). Under v2, it would be 3.
    ids_v1 = v1_sim.encode("^2^P_{F2}|A", add_special=False)
    pieces_v1 = v1_sim.token_ids_to_tokens(ids_v1)
    assert pieces_v1 == ["^2", "^P", "_{", "F2", "}", "|A"], (
        f"v1-equivalent vocab tokenization changed: got {pieces_v1}"
    )


# ---------------------------------------------------------------------------
# Artifact + manifest existence tests
# ---------------------------------------------------------------------------

def test_v2_artifact_exists_and_loads(v2_artifact_path: Path) -> None:
    """The Path D Wave 1A artifact is on disk and reloadable."""
    assert v2_artifact_path.exists(), (
        f"v2 artifact missing at {v2_artifact_path}; "
        f"run tmp/path_d_build_v2_artifact.py to regenerate."
    )
    loaded = HybridCASTokenizer.load(v2_artifact_path)
    assert loaded.frozen, "v2 artifact should load frozen"
    # Sanity: v2-specific tokens are present in the loaded vocab.
    assert "^0^P" in loaded.word2id
    assert "_{F1}" in loaded.word2id
    assert "|⟨" in loaded.word2id
    assert "FractalClass" in loaded.word2id


def test_v2_manifest_exists_and_records_added_tokens(v2_manifest_path: Path) -> None:
    """The manifest records every added token and its ID."""
    import json

    assert v2_manifest_path.exists(), f"v2 manifest missing at {v2_manifest_path}"
    manifest = json.loads(v2_manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "cas_hybrid_tokenizer_manifest.v1"
    added = manifest["added_tokens"]
    surfaces = {entry["surface"] for entry in added}
    # Spot-check the four token shapes that were the gap in v0.
    assert "^0^P" in surfaces
    assert "_{F1}" in surfaces
    assert "|⟨" in surfaces
    assert "FractalClass" in surfaces
    assert manifest["vocab_sizes"]["before_total"] == 333
    assert manifest["vocab_sizes"]["after_total"] == 388
    assert manifest["id_stability"]["all_v1_token_ids_preserved"] is True


# ---------------------------------------------------------------------------
# Smoke: the compiler-validated meta_logic shape that hit v0 with 53.6% fails.
# ---------------------------------------------------------------------------

def test_meta_logic_shape_no_longer_fragments(
    v2_tokenizer: HybridCASTokenizer,
) -> None:
    """``NoeticCluster{^2, ^7} ⊆ Noetics`` tokenizes without char fallback.

    Per memory ``project_v76_metalogic_two_failure_modes_2026_05_04``,
    the v0 vocab gap on meta_logic constructors and operators caused
    53.6% failure on the meta_relations bucket. The Path D tokenizer
    must remove that failure mode.
    """
    expr = "NoeticCluster{^2, ^7} ⊆ Noetics"
    ids = v2_tokenizer.encode(expr, add_special=False)
    pieces = v2_tokenizer.token_ids_to_tokens(ids)
    assert v2_tokenizer.UNK_ID not in ids
    # No <CHAR:...> fallback tokens — every piece is a real reserved token
    # or whitespace special.
    char_pieces = [p for p in pieces if p.startswith("<CHAR:")]
    assert not char_pieces, f"meta_logic shape fragmented to chars: {pieces}"
    # The four load-bearing meta_logic surfaces must appear as their own
    # tokens.
    for required in ("NoeticCluster", "^2", "^7", "⊆", "Noetics"):
        assert required in pieces, f"expected {required!r} in pieces, got {pieces}"
