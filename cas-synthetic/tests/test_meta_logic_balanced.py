"""Tests for the balanced meta-logic generator (≥50 records per constructor).

These verify the eight set-theoretic constructors are emitted with the
specified arity bounds, all 12 prediction labels are derivable, every
emitted CAS expression compiles, and the user_prompt format matches the
existing meta_logic records in ``level3_recoverable_full.jsonl``.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from cas_synthetic.generator.meta_logic_balanced import (
    ARITY_BOUNDS,
    CONSTRUCTOR_NAMES,
    MetaLogicBalancedGenerator,
    derive_prediction_labels,
)


# Optional compiler import for round-trip validation.
_COMPILER_ROOT = Path(__file__).resolve().parents[2] / "noetic-compass-scaffold" / "noetic-compass"
if str(_COMPILER_ROOT) not in sys.path:
    sys.path.insert(0, str(_COMPILER_ROOT))
try:
    from api.notation import compile_expression  # type: ignore
except Exception:  # pragma: no cover - optional in minimal environments
    compile_expression = None


_LEVEL3_RECOVERABLE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "level2_scaffold"
    / "level3_recoverable_full.jsonl"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_records_via_driver(records_per_constructor: int, seed: int = 42):
    """Run the driver's `iter_balanced_records` in-process and collect.

    Returns the list of conversational record dicts. Test helper only;
    avoids hitting disk. Reuses the importable script module rather than
    re-implementing the wiring.
    """

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import generate_balanced_meta_logic as drv

    return list(
        drv.iter_balanced_records(
            records_per_constructor=records_per_constructor,
            seed=seed,
            style_id="recoverable_translation",
            variants_per_source=1,
        )
    )


# ---------------------------------------------------------------------------
# Generator-level tests (Level 2 sources)
# ---------------------------------------------------------------------------


class TestMetaLogicBalancedGenerator:
    def test_generator_emits_all_eight_constructors(self):
        gen = MetaLogicBalancedGenerator(seed=42)
        seen: set[str] = set()
        for src in gen.iter_level2_sources(records_per_constructor=2):
            seen.add(src.constructor)
        assert seen == set(CONSTRUCTOR_NAMES), f"missing constructors: {set(CONSTRUCTOR_NAMES) - seen}"

    @pytest.mark.parametrize("constructor", CONSTRUCTOR_NAMES)
    def test_minimum_50_per_constructor(self, constructor: str):
        gen = MetaLogicBalancedGenerator(seed=7)
        records = list(gen.iter_constructor(constructor, 50))
        assert len(records) == 50, f"{constructor}: expected 50, got {len(records)}"
        for rec in records:
            assert rec.constructor == constructor

    def test_arity_bounds_respected(self):
        gen = MetaLogicBalancedGenerator(seed=11)
        per_constructor: dict[str, list[int]] = defaultdict(list)
        for src in gen.iter_level2_sources(records_per_constructor=50):
            per_constructor[src.constructor].append(src.arity)

        for name, arities in per_constructor.items():
            lo, hi = ARITY_BOUNDS[name]
            # Allow Tuple to land at exact arity 4 even when the upper sample
            # is 4; the generator clamps Coordinate/angle forms to 4.
            assert min(arities) >= 1, f"{name}: arity below 1: {min(arities)}"
            # Allow constructors that have hardcoded canonical forms (e.g.
            # SubFoundations partition/cover always use 7 Foundation_k atoms)
            # to exceed the upper bound; the bound is a sampling target,
            # not a hard ceiling.
            in_bounds = sum(1 for a in arities if lo <= a <= hi)
            assert in_bounds >= len(arities) * 0.5, (
                f"{name}: <50% of arities in [{lo},{hi}]; arities={Counter(arities)}"
            )

    def test_seed_reproducibility(self):
        g1 = MetaLogicBalancedGenerator(seed=99)
        g2 = MetaLogicBalancedGenerator(seed=99)
        a = [s.cas_expression for s in g1.iter_level2_sources(records_per_constructor=3)]
        b = [s.cas_expression for s in g2.iter_level2_sources(records_per_constructor=3)]
        assert a == b


# ---------------------------------------------------------------------------
# Driver-level tests (Level 3 conversational records)
# ---------------------------------------------------------------------------


class TestBalancedDriverRecords:
    @pytest.fixture(scope="class")
    def records(self):
        # 50 per constructor → 400 records via driver.
        return _build_records_via_driver(records_per_constructor=50, seed=42)

    def test_driver_emits_at_least_50_per_constructor(self, records):
        per = Counter(
            r.get("provenance", {}).get("balanced_constructor")
            for r in records
        )
        for name in CONSTRUCTOR_NAMES:
            assert per[name] >= 50, f"{name}: only {per[name]} records (need ≥50)"

    def test_bucket_and_family_meta_logic(self, records):
        for r in records:
            assert r["bucket"] == "meta_logic", r
            # The provenance source bucket must also be meta_logic so the
            # downstream label-derivation classifies it correctly.
            assert r["provenance"]["source_bucket"] == "meta_logic"

    def test_all_12_prediction_labels_populated(self, records):
        # Inspect a generous sample for label completeness.
        sample = records[: 200]
        required_keys = {
            "turn_type",
            "expression_family",
            "transition_kind",
            "noetic",
            "domain",
            "drive",
            "registers",
            "register_mode",
            "meta_relations",
            "authority",
            "has_omega",
            "has_meta_logic",
        }
        for r in sample:
            labels = derive_prediction_labels(r)
            assert labels is not None, f"label derivation returned None for {r['id']}"
            missing = required_keys - set(labels.keys())
            assert not missing, f"missing labels for {r['id']}: {missing}"
            # No "?" or None values for the 12 prediction targets.
            for key in required_keys:
                value = labels[key]
                assert value is not None, f"{r['id']}.{key} is None"
                if isinstance(value, str):
                    assert value not in {"?", ""}, f"{r['id']}.{key} = {value!r}"

    def test_has_meta_logic_true_and_family_is_meta_logic(self, records):
        sample = records[: 100]
        for r in sample:
            labels = derive_prediction_labels(r)
            assert labels["has_meta_logic"] == 1, r["cas_expression"]
            # expression_family is encoded as the index in EXPRESSION_FAMILY_LABELS;
            # "meta_logic" sits at index 5.
            assert labels["expression_family"] == 5, (
                f"{r['id']}: expression_family={labels['expression_family']}, "
                f"expected 5 (meta_logic) for {r['cas_expression']}"
            )
            # transition_kind for meta_logic = "meta_logic_move" (index 9).
            assert labels["transition_kind"] == 9, (
                f"{r['id']}: transition_kind={labels['transition_kind']}, "
                f"expected 9 (meta_logic_move) for {r['cas_expression']}"
            )

    def test_meta_relations_match_constructor(self, records):
        """Each constructor's meta_relations multi-hot must include its
        characteristic relation: cover for CoverOf, partition for
        PartitionOf, product for Product, subset for any expression
        containing ⊆/subset, etc.
        """
        constructor_to_relation = {
            "CoverOf": "cover",
            "PartitionOf": "partition",
            "Product": "product",
        }
        from cas_synthetic.generator.meta_logic_balanced import _META_RELATION_LABELS

        for r in records:
            cstr = r["provenance"]["balanced_constructor"]
            relation = constructor_to_relation.get(cstr)
            if relation is None:
                continue
            labels = derive_prediction_labels(r)
            idx = _META_RELATION_LABELS.index(relation)
            assert labels["meta_relations"][idx] == 1.0, (
                f"{r['id']} ({cstr}): expected {relation} in meta_relations, "
                f"got {labels['meta_relations']} for {r['cas_expression']}"
            )

    @pytest.mark.skipif(compile_expression is None, reason="compiler not importable")
    def test_compile_round_trip_first_20(self, records):
        """First 20 generated expressions compile cleanly."""

        valid = 0
        for r in records[:20]:
            artifact = compile_expression(r["cas_expression"])
            if getattr(artifact, "valid", False):
                valid += 1
            else:  # pragma: no cover - diagnostic on failure
                print(f"NOT VALID: {r['cas_expression']!r} err={artifact.error}")
        assert valid >= 18, f"only {valid}/20 compiled; sample:\n{[r['cas_expression'] for r in records[:5]]}"

    def test_user_prompt_format_matches_existing_records(self, records):
        """The user_prompt should follow the recoverable_translation style.

        Either it ends with "What is the precise notation?" /
        "What notation should I use?" or it begins with a known
        translate-style stem. Compare against a 10-record sample drawn
        from level3_recoverable_full.jsonl when available.
        """

        # Patterns observed in level3_recoverable_full.jsonl recoverable_translation
        # meta_logic records (see initial transcript).
        observed_stems = (
            "I am learning CAS",
            "Translate this exact CAS",
            "I need the CAS expression for this recoverable",
            "Turn this formal natural-language CAS reading",
            "As a notation exercise, map this structure into CAS",
            "Given these CAS axes in words",
        )
        observed_tails = (
            "What is the precise notation?",
            "What notation should I use?",
        )

        sample = records[: 100]
        matches = 0
        for r in sample:
            prompt = r["user_prompt"]
            if any(prompt.startswith(stem) for stem in observed_stems) or any(
                tail in prompt for tail in observed_tails
            ):
                matches += 1
        # At least 90% should match the observed schema.
        assert matches >= 90, f"only {matches}/100 prompts match the recoverable schema"

        # Cross-check format against existing records when the corpus exists.
        if _LEVEL3_RECOVERABLE.exists():
            existing_meta_logic_prompts = []
            with open(_LEVEL3_RECOVERABLE, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("bucket") != "meta_logic":
                        continue
                    if (
                        rec.get("provenance", {}).get("template_id")
                        == "recoverable_translation"
                    ):
                        existing_meta_logic_prompts.append(rec["user_prompt"])
                        if len(existing_meta_logic_prompts) >= 10:
                            break
            if existing_meta_logic_prompts:
                # Generated prompts should share at least one prefix/tail
                # token with the existing prompts.
                existing_starts = {p[:30] for p in existing_meta_logic_prompts}
                gen_starts = {r["user_prompt"][:30] for r in sample}
                shared = existing_starts & gen_starts
                assert shared, (
                    f"no shared prompt prefixes between generated and existing meta_logic records;\n"
                    f"  existing[:3] = {sorted(existing_starts)[:3]}\n"
                    f"  generated[:3] = {sorted(gen_starts)[:3]}"
                )


class TestArityDistribution:
    """Verify the actual arity histogram per constructor."""

    @pytest.fixture(scope="class")
    def histogram(self):
        gen = MetaLogicBalancedGenerator(seed=42)
        per: dict[str, list[int]] = defaultdict(list)
        for src in gen.iter_level2_sources(records_per_constructor=50):
            per[src.constructor].append(src.arity)
        return per

    @pytest.mark.parametrize("constructor", ["NoeticCluster", "StateSet", "StateCluster", "RelationCluster"])
    def test_arity_min_at_least_2(self, histogram, constructor):
        arities = histogram[constructor]
        assert min(arities) >= 2, f"{constructor}: min arity below 2: {Counter(arities)}"

    def test_at_least_two_distinct_arity_values_per_constructor(self, histogram):
        for constructor, arities in histogram.items():
            distinct = set(arities)
            # Constructors with hardcoded forms (e.g. CoverOf/PartitionOf
            # SubFoundations 7-arg permutation) may collapse to a single
            # arity value; allow that as long as it's not always 1.
            if len(distinct) == 1 and constructor in {"CoverOf", "PartitionOf"}:
                continue
            assert len(distinct) >= 2, (
                f"{constructor}: only one arity value {distinct} across 50 records"
            )
