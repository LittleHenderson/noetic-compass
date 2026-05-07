"""Tests for the Path D Wave 1B seed enumerator.

Three guard rails:

1. **Smoke** — small enumeration (target=200) produces seeds across all 7
   grammar categories the Path D pipeline §4 names as load-bearing
   (state_literal, binary_composition, cross_register_omega, recipe,
   meta_logic_relation, fractal_sequence, plus at least one of let_binding/
   diagram_export/rpm_chain/inversion to exercise the curated lanes).
2. **Compiler validation rate** — at least 95% of attempted enumerations
   compile cleanly (the script's `_try` helper round-trips every candidate
   through `api/notation/compiler.py`).
3. **Schema conformance** — every accepted seed carries the required
   fields with non-empty `expression` and a populated `axes` dict.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = (
    _REPO_ROOT
    / "cas-synthetic"
    / "scripts"
    / "generate_path_d_seeds.py"
)


def _load_module():
    name = "path_d_seed_enumerator_under_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


REQUIRED_SEED_FIELDS = (
    "seed_id",
    "task_slot",
    "grammar_category",
    "expression",
    "compiler_validated",
    "axes",
    "n_state_literals",
    "n_operators",
    "uses_named_omega",
    "uses_theta_recipe",
    "uses_meta_logic",
    "uses_fractal",
    "metadata",
)

REQUIRED_AXIS_KEYS = (
    "noetics_used",
    "domains_used",
    "drives_used",
    "registers_used",
    "operators_used",
)

REQUIRED_GRAMMAR_CATEGORIES = (
    "state_literal",
    "binary_composition",
    "cross_register_omega",
    "recipe",
    "meta_logic_relation",
    "fractal_sequence",
)

VALID_TASK_SLOTS = (
    "cas_to_english",
    "english_to_cas",
    "invalid_to_explanation",
    "invalid_to_corrected",
    "operation_to_outcome",
    "expression_to_trace",
)


@pytest.fixture(scope="module")
def smoke_run():
    """Run the enumerator at target=200 once for the smoke + schema tests."""
    mod = _load_module()
    enum = mod.PathDSeedEnumerator(seed=4242, target_total=200)
    enum.run()
    return enum


def test_all_required_grammar_categories_present(smoke_run):
    """Every load-bearing grammar category from the Path D pipeline §4
    seven-category rule appears in a small (target=200) smoke
    enumeration. This is the test that catches a regression where a
    category emitter silently fails — its seeds would never reach the
    accepted bucket."""
    seen_categories = {s.grammar_category for s in smoke_run.accepted}
    missing = set(REQUIRED_GRAMMAR_CATEGORIES) - seen_categories
    assert not missing, (
        f"missing required grammar categories: {missing}; "
        f"saw {sorted(seen_categories)}"
    )
    # At least one of the curated extra lanes (let / diagram / rpm /
    # inversion) should also be present — the curated lanes carry the
    # `metadata.source = curated` and structural-edge cases the design
    # memo flags as required.
    extra_lanes = {"let_binding", "diagram_export", "rpm_chain", "inversion"}
    assert seen_categories & extra_lanes, (
        "no curated-lane seeds present (let/diagram/rpm/inversion)"
    )


def test_compiler_validation_rate_above_95_percent(smoke_run):
    """The script's compiler-in-the-loop validation should reject very
    few attempts — anything above 5% rejection is a sign the generator
    is producing structurally-malformed candidates and should be
    investigated."""
    accepted = len(smoke_run.accepted)
    rejected = len(smoke_run.rejected)
    total_attempted = accepted + rejected
    assert total_attempted > 0
    rate = accepted / total_attempted
    assert rate >= 0.95, (
        f"compiler-validation acceptance rate {rate:.2%} below 95% "
        f"threshold (accepted={accepted} rejected={rejected})"
    )


def test_schema_conformance(smoke_run):
    """Every accepted seed has all required fields and a populated axes
    dict. This is the schema-load-bearing contract the Path D corpus
    aggregator (Wave 4 deliverable G) consumes downstream."""
    assert smoke_run.accepted, "no accepted seeds produced"
    for seed in smoke_run.accepted:
        record = seed.to_record()
        missing_fields = [f for f in REQUIRED_SEED_FIELDS if f not in record]
        assert not missing_fields, (
            f"seed {seed.seed_id} missing fields: {missing_fields}"
        )
        # Required field non-emptiness checks.
        assert record["seed_id"], f"empty seed_id on {record}"
        assert record["task_slot"] in VALID_TASK_SLOTS, (
            f"invalid task_slot {record['task_slot']}"
        )
        assert record["grammar_category"], (
            f"empty grammar_category on {record['seed_id']}"
        )
        assert record["expression"], (
            f"empty expression on {record['seed_id']}"
        )
        assert record["compiler_validated"] is True, (
            f"non-validated seed reached accepted bucket: {record}"
        )
        # Axes dict has every required key.
        axes = record["axes"]
        assert isinstance(axes, dict), f"axes not a dict on {record['seed_id']}"
        missing_axes = [k for k in REQUIRED_AXIS_KEYS if k not in axes]
        assert not missing_axes, (
            f"seed {record['seed_id']} missing axes keys: {missing_axes}"
        )
        # n_state_literals / n_operators are non-negative ints.
        assert isinstance(record["n_state_literals"], int)
        assert record["n_state_literals"] >= 0
        assert isinstance(record["n_operators"], int)
        assert record["n_operators"] >= 0
        # Boolean flags are bools (not 0/1 or None).
        for flag in ("uses_named_omega", "uses_theta_recipe",
                     "uses_meta_logic", "uses_fractal"):
            assert isinstance(record[flag], bool), (
                f"flag {flag} not bool on {record['seed_id']}"
            )
        # Metadata is a dict with the seed_for_task_slot key.
        meta = record["metadata"]
        assert isinstance(meta, dict)
        assert meta.get("seed_for_task_slot") == record["task_slot"], (
            f"metadata.seed_for_task_slot mismatch on {record['seed_id']}"
        )


def test_seed_ids_are_unique(smoke_run):
    """Seed IDs must be globally unique so downstream provenance
    tracking (Wave 4 corpus aggregator G) can join across files."""
    ids = [s.seed_id for s in smoke_run.accepted]
    assert len(ids) == len(set(ids)), (
        f"duplicate seed_ids detected: {len(ids)} ids, {len(set(ids))} unique"
    )


def test_compiler_module_loads():
    """The compiler is reachable from the script's loader. This is a
    pre-flight check — without the compiler the validation step would
    silently no-op and the seeds would never round-trip."""
    mod = _load_module()
    compiler_module = mod._load_compiler()
    assert compiler_module is not None
    assert hasattr(compiler_module, "compile_expression")
    artifact = compiler_module.compile_expression("^2^P")
    assert getattr(artifact, "valid", False)


def test_expressions_round_trip_through_compiler(smoke_run):
    """Sanity check — re-compile a sample of accepted seeds (the script
    already validates each before accepting; this re-runs the validation
    independently to catch any stale-cache or stateful bug)."""
    mod = _load_module()
    compiler_module = mod._load_compiler()
    # Sample 50 seeds across categories — re-compile each and confirm.
    sampled = smoke_run.accepted[:: max(1, len(smoke_run.accepted) // 50)]
    for seed in sampled:
        artifact = compiler_module.compile_expression(seed.expression)
        assert getattr(artifact, "valid", False), (
            f"seed {seed.seed_id} fails second-pass compile: "
            f"{seed.expression!r} | "
            f"err={getattr(artifact, 'error', '') or ''}"
        )
