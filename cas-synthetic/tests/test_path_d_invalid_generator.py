"""Tests for the Path D Wave 2D invalid-CAS generator.

Four guard rails (per the deliverable spec):

1. **Smoke per error_class** — each of the six error classes (parse,
   admissibility, rpm, recipe, meta_logic, fractal) produces at least 10
   valid invalid samples on a small smoke run.
2. **Compiler-rejection rate ≥99%** — samples that COMPILE are bugs in
   the mutator (every sample must be rejected by the compiler).
3. **Schema-conformance** — every accepted record has every required
   field, and `compiler_error_message` is captured non-empty.
4. **Repair-target preservation** — `corrected_form` is identical to the
   source seed expression for the seeded mutators (the constructor-style
   mutators that synthesize fresh expressions still set
   `corrected_form` to the source seed expression).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = (
    _REPO_ROOT
    / "cas-synthetic"
    / "scripts"
    / "generate_path_d_invalids.py"
)
_SEEDS = (
    _REPO_ROOT
    / "cas-synthetic"
    / "data"
    / "path_d"
    / "seeds.jsonl"
)


def _load_module():
    name = "path_d_invalid_generator_under_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


REQUIRED_FIELDS = (
    "invalid_id",
    "source_seed_id",
    "mutation_type",
    "error_class",
    "expression",
    "corrected_form",
    "compiler_validated",
    "compiler_error_message",
    "compiler_error_type",
    "axes_in_corrected_form",
)

REQUIRED_AXIS_KEYS = (
    "noetics_used",
    "domains_used",
    "drives_used",
    "registers_used",
    "operators_used",
)

REQUIRED_ERROR_CLASSES = (
    "parse",
    "admissibility",
    "rpm",
    "recipe",
    "meta_logic",
    "fractal",
)


def _read_seeds(path: Path):
    seeds = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                seeds.append(json.loads(line))
    return seeds


@pytest.fixture(scope="module")
def smoke_run():
    """Run the generator at target=1500 against the full seed file once
    for the schema + class-coverage tests. 1500 produces ~250 samples
    per error class, comfortably above the 10-per-class smoke threshold
    while keeping the test fast."""
    mod = _load_module()
    if not _SEEDS.exists():
        pytest.skip(f"path D seeds.jsonl not generated at {_SEEDS}")
    seeds = _read_seeds(_SEEDS)
    gen = mod.InvalidGenerator(seeds=seeds, target_total=1500, seed=4242)
    gen.run()
    return gen


def test_each_error_class_produces_at_least_ten(smoke_run):
    """Per deliverable spec: each error_class produces at least 10 valid
    invalid samples on a small smoke run."""
    counts = {cls: 0 for cls in REQUIRED_ERROR_CLASSES}
    for r in smoke_run.accepted:
        counts[r.error_class] = counts.get(r.error_class, 0) + 1
    for cls in REQUIRED_ERROR_CLASSES:
        assert counts[cls] >= 10, (
            f"error_class {cls!r} only produced {counts[cls]} samples "
            f"(threshold: 10). Other classes: {counts}"
        )


def test_compiler_rejection_rate_above_99_percent(smoke_run):
    """Per deliverable spec: compiler-rejection rate ≥99%. Samples that
    compile are mutator bugs — they get logged into
    `unexpected_compile` but are NOT emitted into `accepted`. The rate
    measured here is the fraction of attempted-mutate-and-compile cycles
    that produced a real invalid (rejected by the compiler).
    """
    accepted = len(smoke_run.accepted)
    unexpected = len(smoke_run.unexpected_compile)
    total = accepted + unexpected
    assert total > 0
    rate = accepted / total
    assert rate >= 0.99, (
        f"compiler-rejection rate {rate:.4%} below 99% "
        f"threshold (accepted={accepted} unexpected_compiles={unexpected}). "
        f"Tighten the mutators that leaked: "
        f"{[u['mutation_type'] for u in smoke_run.unexpected_compile[:10]]}"
    )


def test_schema_conformance(smoke_run):
    """Every accepted record has every required field, with
    `compiler_error_message` captured non-empty and `compiler_validated`
    being literally False."""
    assert smoke_run.accepted, "no invalid samples emitted"
    for record_obj in smoke_run.accepted:
        record = record_obj.to_record()
        for field_name in REQUIRED_FIELDS:
            assert field_name in record, (
                f"record missing field {field_name!r}: {record}"
            )
        # Boolean field must be literally False (NOT 0, None, or "false").
        assert record["compiler_validated"] is False, (
            f"compiler_validated must be False, got "
            f"{record['compiler_validated']!r}"
        )
        # Compiler error message must be non-empty (we captured the verbatim
        # error from the compiler).
        assert record["compiler_error_message"], (
            f"compiler_error_message is empty on {record['invalid_id']}"
        )
        # Axes dict must have all five required keys.
        axes = record["axes_in_corrected_form"]
        assert isinstance(axes, dict), (
            f"axes_in_corrected_form not a dict on {record['invalid_id']}"
        )
        for key in REQUIRED_AXIS_KEYS:
            assert key in axes, (
                f"axes missing key {key!r} on {record['invalid_id']}"
            )
        # error_class must be one of the six required classes.
        assert record["error_class"] in REQUIRED_ERROR_CLASSES, (
            f"unknown error_class {record['error_class']!r} on "
            f"{record['invalid_id']}"
        )


def test_invalid_ids_are_unique(smoke_run):
    """Each invalid sample has a unique invalid_id so downstream
    provenance tracking can join across files (Path D Wave 4 corpus
    aggregator G consumer)."""
    ids = [r.invalid_id for r in smoke_run.accepted]
    assert len(ids) == len(set(ids)), (
        f"duplicate invalid_ids: {len(ids)} ids, {len(set(ids))} unique"
    )


def test_repair_target_preservation(smoke_run):
    """Per deliverable spec: `corrected_form` is identical to the source
    seed expression. This is load-bearing — the repair-track training
    target IS this exact form."""
    mod = _load_module()
    seeds = _read_seeds(_SEEDS)
    seed_by_id = {s["seed_id"]: s for s in seeds}
    for record in smoke_run.accepted:
        seed = seed_by_id.get(record.source_seed_id)
        assert seed is not None, (
            f"source_seed_id {record.source_seed_id!r} not in seeds.jsonl"
        )
        assert record.corrected_form == seed["expression"], (
            f"corrected_form != source seed expression on "
            f"{record.invalid_id}: got {record.corrected_form!r}, "
            f"expected {seed['expression']!r}"
        )


def test_expression_differs_from_corrected_form(smoke_run):
    """The mutated expression must be DIFFERENT from the corrected form —
    otherwise no mutation actually happened."""
    for record in smoke_run.accepted:
        assert record.expression != record.corrected_form, (
            f"mutation produced identical expression on "
            f"{record.invalid_id}: {record.expression!r}"
        )


def test_compiler_module_loads():
    """Pre-flight: the compiler is reachable from the script's loader.
    Without this, every mutation would short-circuit to None."""
    mod = _load_module()
    compiler_module = mod._load_compiler()
    assert hasattr(compiler_module, "compile_expression")
    # Sanity check: a known-valid baseline compiles.
    artifact = compiler_module.compile_expression("^0^P")
    assert getattr(artifact, "valid", False), (
        f"compiler baseline failed: {getattr(artifact, 'error', '')}"
    )


def test_every_invalid_actually_fails_compiler():
    """Round-trip a sample of the emitted invalids back through the
    compiler at test time and confirm every one is actually rejected.
    This is the strongest possible compile-rejection check — it
    re-validates the artifact independently of the generator's own
    `unexpected_compile` bucket."""
    mod = _load_module()
    if not _SEEDS.exists():
        pytest.skip(f"path D seeds.jsonl not generated at {_SEEDS}")
    seeds = _read_seeds(_SEEDS)
    gen = mod.InvalidGenerator(seeds=seeds, target_total=600, seed=99)
    gen.run()
    assert gen.accepted, "no invalid samples emitted by smoke run"
    compiler = mod._load_compiler()
    re_validated = 0
    for record in gen.accepted:
        artifact = compiler.compile_expression(record.expression)
        assert not getattr(artifact, "valid", True), (
            f"sample re-compiled cleanly on round-trip: "
            f"{record.invalid_id} class={record.error_class} "
            f"mutation={record.mutation_type} expr={record.expression!r}"
        )
        re_validated += 1
    assert re_validated >= 100, (
        f"too few samples re-validated: {re_validated}"
    )


def test_each_error_class_has_diverse_mutations(smoke_run):
    """Each error_class should exercise multiple mutation_types — not
    just one. A class collapsed to a single mutation_type signals
    silent skip-condition triggers across all the others."""
    by_class_mutations = {}
    for r in smoke_run.accepted:
        by_class_mutations.setdefault(r.error_class, set()).add(
            r.mutation_type
        )
    for cls in REQUIRED_ERROR_CLASSES:
        muts = by_class_mutations.get(cls, set())
        assert len(muts) >= 2, (
            f"error_class {cls!r} only exercised {len(muts)} mutation_type(s) "
            f"({muts}) — expected at least 2"
        )
