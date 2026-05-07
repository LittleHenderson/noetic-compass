"""Tests for the Path D Wave 2C variant generator.

Four guard rails (per the kickoff memo's "tests" section):

1. **Smoke** — variant types are all represented in a small smoke run.
2. **Base-preservation** — random sample of variants preserves state
   literals + Ω names + Θ wrappers + fractal sequences from the source
   seed.
3. **Compiler-validation rate** — at least 95% of attempted variants
   round-trip through `api/notation/compiler.py`.
4. **Oversample** — rpm_chain and inversion lanes hit their oversample
   ratios (≥3× and ≥5× respectively), counted against productive seeds
   for inversion (axis-W shapes have no fiber to vary; spec allows
   skipping rather than violating base preservation).
"""

from __future__ import annotations

import importlib.util
import json
import random
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = (
    _REPO_ROOT
    / "cas-synthetic"
    / "scripts"
    / "generate_path_d_variants.py"
)
_SEEDS_PATH = (
    _REPO_ROOT
    / "cas-synthetic"
    / "data"
    / "path_d"
    / "seeds.jsonl"
)


def _load_module():
    name = "path_d_variant_generator_under_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _read_seeds(path: Path) -> list[dict]:
    out: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


REQUIRED_VARIANT_FIELDS = (
    "variant_id",
    "source_seed_id",
    "variant_type",
    "preserved_axes",
    "varied_axes",
    "expression",
    "compiler_validated",
    "axes",
    "n_state_literals",
    "uses_named_omega",
    "uses_theta_recipe",
    "uses_meta_logic",
    "uses_fractal",
    "delta_from_seed",
)


REQUIRED_VARIANT_TYPES = ("drive_intensity", "register", "operation", "order")


@pytest.fixture(scope="module")
def smoke_run():
    """Run the variant generator over the full seed enumeration once
    for the smoke + base-preservation + oversample tests. The seed file
    is the Wave 1B output (5802 compiler-validated seeds)."""
    if not _SEEDS_PATH.exists():
        pytest.skip(
            f"seeds.jsonl missing at {_SEEDS_PATH} — Wave 1B not yet run"
        )
    seeds = _read_seeds(_SEEDS_PATH)
    mod = _load_module()
    gen = mod.VariantGenerator(seed=4242)
    gen.run(seeds)
    return mod, gen, seeds


def test_all_variant_types_represented(smoke_run):
    """Every variant_type from the kickoff memo's four-type taxonomy
    appears in the smoke run. This is the regression guard for a
    transform family silently dying."""
    _mod, gen, _seeds = smoke_run
    seen_types = {v.variant_type for v in gen.accepted}
    missing = set(REQUIRED_VARIANT_TYPES) - seen_types
    assert not missing, (
        f"missing variant types: {missing}; saw {sorted(seen_types)}"
    )


def test_per_variant_schema(smoke_run):
    """Every accepted variant carries all required fields with non-empty
    values where required. This is the schema-load-bearing contract the
    Wave 4 corpus aggregator (deliverable G) consumes downstream."""
    _mod, gen, _seeds = smoke_run
    assert gen.accepted, "no accepted variants produced"
    # Sample 200 across the run.
    rng = random.Random(0)
    sample = rng.sample(
        gen.accepted, min(200, len(gen.accepted))
    )
    for v in sample:
        record = v.to_record()
        missing = [f for f in REQUIRED_VARIANT_FIELDS if f not in record]
        assert not missing, f"variant {v.variant_id} missing: {missing}"
        assert record["variant_id"].startswith("var_"), (
            f"variant_id format unexpected: {record['variant_id']}"
        )
        assert record["source_seed_id"], "empty source_seed_id"
        assert record["variant_type"] in REQUIRED_VARIANT_TYPES, (
            f"unexpected variant_type: {record['variant_type']}"
        )
        assert record["expression"], "empty expression"
        assert record["compiler_validated"] is True
        # axes is a populated dict.
        assert isinstance(record["axes"], dict)
        for k in ("noetics_used", "domains_used", "drives_used",
                  "registers_used", "operators_used"):
            assert k in record["axes"], (
                f"variant {v.variant_id} axes missing {k}"
            )
        # Boolean flags are bools.
        for flag in ("uses_named_omega", "uses_theta_recipe",
                     "uses_meta_logic", "uses_fractal"):
            assert isinstance(record[flag], bool), (
                f"flag {flag} not bool on {record['variant_id']}"
            )


def test_base_preservation_random_sample(smoke_run):
    """Random sample of variants preserves the load-bearing base of
    their source seed: state literals (multiset), Ω target names,
    Θ-wrapper presence, fractal head+sequence pairs.

    This is THE load-bearing rule of Wave 2C — variants that drift the
    base defeat the contrastive supervision design (Path D §7). The
    multiset comparison on state_cores is intentional: order-type
    variants permute occurrence order, but the SAME state literals must
    appear with the SAME multiplicity."""
    mod, gen, seeds = smoke_run
    seeds_by_id = {s["seed_id"]: s for s in seeds}

    rng = random.Random(7)
    sample = rng.sample(
        gen.accepted, min(500, len(gen.accepted))
    )
    failures: list[str] = []
    for v in sample:
        seed = seeds_by_id.get(v.source_seed_id)
        if seed is None:
            failures.append(
                f"variant {v.variant_id} references unknown seed "
                f"{v.source_seed_id}"
            )
            continue
        ok, reason = mod._bases_equal(seed["expression"], v.expression)
        if not ok:
            failures.append(
                f"variant {v.variant_id} ({v.variant_type}) breaks base: "
                f"{reason} | seed={seed['expression']!r} | "
                f"variant={v.expression!r}"
            )
    assert not failures, (
        f"{len(failures)} base-preservation failures (sample size "
        f"{len(sample)}); first 3:\n  - "
        + "\n  - ".join(failures[:3])
    )


def test_compiler_validation_rate_above_95_percent(smoke_run):
    """The script's compiler-in-the-loop validation should reject very
    few attempts. Anything above 5% rejection signals the transforms
    are producing structurally-malformed candidates and must be
    investigated."""
    _mod, gen, _seeds = smoke_run
    accepted = len(gen.accepted)
    rejected = len(gen.rejected)
    total_attempted = accepted + rejected
    assert total_attempted > 0
    rate = accepted / total_attempted
    assert rate >= 0.95, (
        f"compiler-validation acceptance rate {rate:.2%} below 95% "
        f"threshold (accepted={accepted} rejected={rejected})"
    )


def test_oversample_rpm_chain(smoke_run):
    """rpm_chain seeds get ≥3 variants on average (the "thin lane"
    oversample rule from the Wave 2C kickoff memo)."""
    _mod, gen, seeds = smoke_run
    rpm_seed_ids = {
        s["seed_id"] for s in seeds if s.get("grammar_category") == "rpm_chain"
    }
    rpm_variants = [
        v for v in gen.accepted if v.source_seed_id in rpm_seed_ids
    ]
    assert rpm_seed_ids, "no rpm_chain seeds present (test setup error)"
    ratio = len(rpm_variants) / len(rpm_seed_ids)
    assert ratio >= 3.0, (
        f"rpm_chain oversample ratio {ratio:.2f} below ≥3.0 target "
        f"(seeds={len(rpm_seed_ids)} variants={len(rpm_variants)})"
    )


def test_oversample_inversion_productive_shapes(smoke_run):
    """Inversion seeds with at least one variable fiber/marginal
    (productive shapes — axes A, E, F, N, P, S) get ≥5 variants on
    average per the kickoff memo's "thin lane" rule. Axis-W shapes
    (`^N^Da -> ^N^Db`) have no fiber to vary while preserving the base
    (no drives, no registers, single arrow with mandatory domain
    descent), so per the kickoff memo we skip rather than fabricate a
    base-changing variant. The productive-shape ratio is the metric the
    kickoff memo's oversample target measures."""
    _mod, gen, seeds = smoke_run
    inversion_seeds = [
        s for s in seeds if s.get("grammar_category") == "inversion"
    ]
    productive_seed_ids = {
        s["seed_id"]
        for s in inversion_seeds
        if s.get("metadata", {}).get("axis") != "W"
    }
    inv_variants = [
        v for v in gen.accepted if v.source_seed_id in productive_seed_ids
    ]
    assert productive_seed_ids, "no productive inversion seeds (test error)"
    ratio = len(inv_variants) / len(productive_seed_ids)
    assert ratio >= 5.0, (
        f"productive inversion oversample ratio {ratio:.2f} below ≥5.0 "
        f"target (productive seeds={len(productive_seed_ids)} "
        f"variants={len(inv_variants)})"
    )


def test_variant_ids_are_unique(smoke_run):
    """Variant IDs are globally unique across the run so downstream
    provenance tracking (Wave 4 corpus aggregator G) can join across
    files."""
    _mod, gen, _seeds = smoke_run
    ids = [v.variant_id for v in gen.accepted]
    assert len(ids) == len(set(ids)), (
        f"duplicate variant_ids: {len(ids)} ids, {len(set(ids))} unique"
    )


def test_variants_round_trip_through_compiler(smoke_run):
    """Re-compile a sample of accepted variants. The script already
    validates each before accepting; this re-runs validation
    independently to catch any stale-cache or stateful bug in the
    compiler loader."""
    mod, gen, _seeds = smoke_run
    compiler_module = mod._load_compiler()
    rng = random.Random(11)
    sample = rng.sample(
        gen.accepted, min(50, len(gen.accepted))
    )
    for v in sample:
        artifact = compiler_module.compile_expression(v.expression)
        assert getattr(artifact, "valid", False), (
            f"variant {v.variant_id} fails second-pass compile: "
            f"{v.expression!r} | "
            f"err={getattr(artifact, 'error', '') or ''}"
        )


def test_variant_differs_from_seed(smoke_run):
    """Every variant must differ from its source seed (no-op transforms
    are filtered)."""
    _mod, gen, seeds = smoke_run
    seeds_by_id = {s["seed_id"]: s for s in seeds}
    for v in gen.accepted:
        seed = seeds_by_id.get(v.source_seed_id)
        if seed is None:
            continue
        assert v.expression.strip() != seed["expression"].strip(), (
            f"variant {v.variant_id} identical to seed expression"
        )


def test_drive_intensity_changes_only_drives(smoke_run):
    """Targeted property check on drive_intensity variants: they should
    have a different drive multiset from the seed (or at least one
    different drive index), and identical state-literal multiset."""
    mod, gen, seeds = smoke_run
    seeds_by_id = {s["seed_id"]: s for s in seeds}
    di_variants = [v for v in gen.accepted if v.variant_type == "drive_intensity"]
    if not di_variants:
        pytest.skip("no drive_intensity variants present")
    rng = random.Random(13)
    sample = rng.sample(di_variants, min(60, len(di_variants)))
    for v in sample:
        seed = seeds_by_id[v.source_seed_id]
        seed_drives = sorted(
            int(d) for d in mod._RE_DRIVE_SUB.findall(seed["expression"])
        )
        var_drives = sorted(
            int(d) for d in mod._RE_DRIVE_SUB.findall(v.expression)
        )
        assert seed_drives != var_drives, (
            f"drive_intensity variant {v.variant_id} did not change F_k: "
            f"seed_drives={seed_drives} var_drives={var_drives}"
        )
        # State cores (multiset) must be identical.
        assert sorted(mod._state_cores(seed["expression"])) == sorted(
            mod._state_cores(v.expression)
        ), (
            f"drive_intensity variant {v.variant_id} altered state cores"
        )


def test_register_changes_only_registers(smoke_run):
    """Targeted property check on register variants: register set from
    the variant differs from the seed, state cores (multiset) preserved."""
    mod, gen, seeds = smoke_run
    seeds_by_id = {s["seed_id"]: s for s in seeds}
    reg_variants = [v for v in gen.accepted if v.variant_type == "register"]
    if not reg_variants:
        pytest.skip("no register variants present")
    rng = random.Random(17)
    sample = rng.sample(reg_variants, min(60, len(reg_variants)))
    for v in sample:
        seed = seeds_by_id[v.source_seed_id]
        seed_regs = sorted(set(
            mod._RE_REGISTER_SINGLE.findall(seed["expression"])
        ))
        var_regs = sorted(set(
            mod._RE_REGISTER_SINGLE.findall(v.expression)
        ))
        # Either single-register set differs, or the multi-register set
        # group differs — either way the surface-form register content
        # must change.
        seed_set_match = mod._RE_REGISTER_SET.search(seed["expression"])
        var_set_match = mod._RE_REGISTER_SET.search(v.expression)
        if seed_set_match is not None or var_set_match is not None:
            seed_set_inner = seed_set_match.group(1) if seed_set_match else ""
            var_set_inner = var_set_match.group(1) if var_set_match else ""
            assert (seed_regs != var_regs) or (
                seed_set_inner != var_set_inner
            ), (
                f"register variant {v.variant_id} did not change |R or "
                f"|⟨...⟩"
            )
        else:
            assert seed_regs != var_regs, (
                f"register variant {v.variant_id} did not change |R: "
                f"seed_regs={seed_regs} var_regs={var_regs}"
            )
        # State cores preserved.
        assert sorted(mod._state_cores(seed["expression"])) == sorted(
            mod._state_cores(v.expression)
        ), (
            f"register variant {v.variant_id} altered state cores"
        )


def test_operation_changes_only_operator(smoke_run):
    """Operation variants change the binary operator while preserving
    the operand state literals."""
    mod, gen, seeds = smoke_run
    seeds_by_id = {s["seed_id"]: s for s in seeds}
    op_variants = [v for v in gen.accepted if v.variant_type == "operation"]
    if not op_variants:
        pytest.skip("no operation variants present")
    rng = random.Random(19)
    sample = rng.sample(op_variants, min(40, len(op_variants)))
    for v in sample:
        seed = seeds_by_id[v.source_seed_id]
        # Operands (state cores) preserved as multiset.
        assert sorted(mod._state_cores(seed["expression"])) == sorted(
            mod._state_cores(v.expression)
        )
        # The variant uses a different operator glyph (one of +, ×, ∘)
        # than the seed.
        for op in ("+", "×", "∘"):
            seed_has = op in seed["expression"]
            var_has = op in v.expression
            if seed_has != var_has:
                break
        else:
            # No glyph difference found.
            pytest.fail(
                f"operation variant {v.variant_id} has no operator "
                f"glyph difference from seed"
            )


def test_order_preserves_state_core_multiset(smoke_run):
    """Order variants permute operand order while preserving state
    literal multiset (and thus the load-bearing base)."""
    mod, gen, seeds = smoke_run
    seeds_by_id = {s["seed_id"]: s for s in seeds}
    order_variants = [v for v in gen.accepted if v.variant_type == "order"]
    if not order_variants:
        pytest.skip("no order variants present")
    rng = random.Random(23)
    sample = rng.sample(order_variants, min(60, len(order_variants)))
    for v in sample:
        seed = seeds_by_id[v.source_seed_id]
        seed_cores = sorted(mod._state_cores(seed["expression"]))
        var_cores = sorted(mod._state_cores(v.expression))
        assert seed_cores == var_cores, (
            f"order variant {v.variant_id} altered state-core multiset: "
            f"seed={seed_cores} variant={var_cores}"
        )
