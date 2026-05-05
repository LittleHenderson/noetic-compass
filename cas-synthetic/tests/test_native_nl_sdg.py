"""Tests for the Native NL SDG v1 seed script.

These tests exercise the deterministic Tier 1 path, the schema fields,
the validator, the manifest writer, and the cost-cap / API-key fallback
behavior. Tier 2 is exercised through the dry-run synthesis path so the
test suite never touches the Anthropic API.
"""

from __future__ import annotations

import importlib.util as _importlib_util
import json
import sys
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest


# Load the script as a module without going through the `cas_synthetic`
# package init (which requires an editable install).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = (
    _REPO_ROOT
    / "cas-synthetic"
    / "scripts"
    / "generate_native_nl_sdg_v1.py"
)


def _load_sdg_module():
    mod_name = "generate_native_nl_sdg_v1_module"
    spec = _importlib_util.spec_from_file_location(mod_name, _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = _importlib_util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


sdg = _load_sdg_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQUIRED_RECORD_FIELDS = (
    "id",
    "schema_version",
    "trace_id",
    "tier",
    "parent_ids",
    "source",
    "source_template_id",
    "generator_model",
    "generation_timestamp",
    "cas_expression",
    "noetic",
    "domain",
    "drive",
    "register",
    "prompt",
    "reply",
    "demographic_profile",
    "demographic_profile_code",
    "tone",
    "tone_code",
    "validator_pass",
    "validator_reasons",
    "generation_version",
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_record_schema_all_required_fields_present():
    """Tier 1 records carry every load-bearing traceability field."""
    trace_id = str(uuid.uuid4())
    records = sdg.generate_tier1(target=20, seed=42, trace_id=trace_id)
    assert len(records) == 20
    for rec in records:
        missing = [k for k in REQUIRED_RECORD_FIELDS if k not in rec]
        assert not missing, f"missing fields in record: {missing}"
        assert rec["schema_version"] == "native_nl.v1"
        assert rec["tier"] == "tier1"
        assert rec["trace_id"] == trace_id
        assert rec["parent_ids"] == []
        assert rec["generator_model"] == "deterministic"
        assert isinstance(rec["validator_reasons"], list)
        # ISO 8601 UTC parse must succeed.
        parsed = datetime.fromisoformat(rec["generation_timestamp"])
        assert parsed.tzinfo is not None


def test_axis_coverage_visits_all_four_axes():
    """A 1,120-record run covers every (Noetic, Domain, Drive, Register)."""
    records = sdg.generate_tier1(target=1_120, seed=7, trace_id="t")
    cells = {(r["noetic"], r["domain"], r["drive"], r["register"]) for r in records}
    # 10 * 4 * 7 * 4 = 1120 unique cells. Visiting all 1,120 records once
    # should cover the full grid (the iter is shuffled but exhaustive).
    assert len(cells) == 1_120, (
        f"expected 1120 unique cells, got {len(cells)} "
        f"(some axis combinations missing)"
    )
    noetics = {c[0] for c in cells}
    domains = {c[1] for c in cells}
    drives = {c[2] for c in cells}
    registers = {c[3] for c in cells}
    assert noetics == set(sdg.NOETICS.keys())
    assert domains == set(sdg.DOMAINS.keys())
    assert drives == set(sdg.DRIVES.keys())
    assert registers == set(sdg.REGISTERS.keys())


def test_deterministic_id_same_inputs_same_id():
    """deterministic_id is stable across calls with identical inputs."""
    a = sdg.deterministic_id("alpha", "beta", "gamma")
    b = sdg.deterministic_id("alpha", "beta", "gamma")
    assert a == b
    assert len(a) == 32  # 32 hex chars = 128 bits of sha256
    # Different input -> different ID.
    c = sdg.deterministic_id("alpha", "beta", "delta")
    assert c != a


def test_deterministic_id_prefix_does_not_collide():
    a = sdg.deterministic_id("x", prefix="tpl_")
    b = sdg.deterministic_id("x")
    assert a.startswith("tpl_")
    assert a[len("tpl_"):] == b


def test_idempotent_rerun_with_same_seed_and_trace_id():
    """Re-running Tier 1 with same seed AND trace_id reproduces the same
    cells, prompts, replies, and template IDs deterministically (the
    timestamp-derived IDs differ because timestamps advance)."""
    a = sdg.generate_tier1(target=50, seed=99, trace_id="trace-X")
    b = sdg.generate_tier1(target=50, seed=99, trace_id="trace-X")
    # Cells must align positionally — same cell shuffle.
    for r1, r2 in zip(a, b):
        assert (r1["noetic"], r1["domain"], r1["drive"], r1["register"]) == (
            r2["noetic"], r2["domain"], r2["drive"], r2["register"]
        )
        assert r1["cas_expression"] == r2["cas_expression"]
        assert r1["prompt"] == r2["prompt"]
        assert r1["reply"] == r2["reply"]
        assert r1["source_template_id"] == r2["source_template_id"]


def test_validator_accepts_clean_reply():
    ok, reasons = sdg.validate_reply(
        "I will not sign off on a plan that puts the line workers at risk."
    )
    assert ok, f"expected clean reply to pass; reasons={reasons}"
    assert reasons == []


def test_validator_rejects_jargon_and_template_openers():
    ok1, r1 = sdg.validate_reply("This Noetic of mine is principled.")
    assert not ok1
    assert any("noetic" in s.lower() for s in r1)

    ok2, r2 = sdg.validate_reply("Reading this as a structural concern.")
    assert not ok2
    assert "template_opener" in r2

    ok3, r3 = sdg.validate_reply(
        "I would set the dial to F2 and then look at the |A register."
    )
    assert not ok3
    # F2 jargon, |A register jargon, etc.
    assert any("F[1-7]" in s or "register" in s.lower() or "|" in s for s in r3)


def test_validator_rejects_too_short_too_long_low_density():
    ok, r = sdg.validate_reply("hi")
    assert not ok and "too_short" in r

    ok, r = sdg.validate_reply("a" * 700)
    # 700 a's is over length, but also passes letter density.
    assert not ok
    assert "too_long" in r

    ok, r = sdg.validate_reply("############# *(*&" * 5)
    assert not ok
    assert "low_letter_density" in r


def test_cas_expression_format_is_v75_register_specified():
    """CAS expression is rendered as ``^n^D_{F_k}|R``."""
    expr = sdg.build_cas_expression("^3", "P", "F2", "A")
    assert expr == "^3^P_{F2}|A"


def test_manifest_completeness(tmp_path):
    """Manifest must capture distributions, costs, traceability, notes."""
    out_path = tmp_path / "out.jsonl"
    manifest_path = tmp_path / "manifest.json"
    rc = sdg.run(
        tier1_target=40,
        tier2_target=0,
        out_path=out_path,
        manifest_path=manifest_path,
        seed=11,
        concurrency=2,
        cost_cap_usd=0.0,
        primary_model="claude-sonnet-4-6",
        fallback_model="claude-3-5-sonnet-20241022",
        env_file=tmp_path / "nonexistent.env",
        tier1_only=True,
        dry_run=False,
    )
    assert rc == 0
    assert out_path.exists()
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for k in (
        "schema_version",
        "trace_id",
        "tier1_records",
        "tier2_records",
        "total_records",
        "validator_pass_count",
        "validator_pass_rate",
        "distributions",
        "total_cost_usd",
        "api_calls",
        "hard_cost_cap_usd",
        "cost_aborted",
        "failure_counts",
        "generation_started",
        "generation_completed",
        "round_trip_validator",
        "notes",
    ):
        assert k in manifest, f"missing manifest key: {k}"
    assert manifest["tier1_records"] == 40
    assert manifest["tier2_records"] == 0
    assert manifest["total_records"] == 40
    assert "noetic" in manifest["distributions"]
    assert "domain" in manifest["distributions"]
    assert "drive" in manifest["distributions"]
    assert "register" in manifest["distributions"]


def test_api_key_missing_falls_back_to_tier1_only(tmp_path):
    """No API key in env or env file -> Tier 1 only, manifest documents the gap."""
    out_path = tmp_path / "out.jsonl"
    manifest_path = tmp_path / "manifest.json"
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("# empty\n", encoding="utf-8")

    # Ensure NC_ANTHROPIC_API_KEY is not in process env for this test.
    import os
    saved = os.environ.pop("NC_ANTHROPIC_API_KEY", None)
    try:
        rc = sdg.run(
            tier1_target=10,
            tier2_target=10,  # would normally call API
            out_path=out_path,
            manifest_path=manifest_path,
            seed=17,
            concurrency=1,
            cost_cap_usd=10.0,
            primary_model="claude-sonnet-4-6",
            fallback_model="claude-3-5-sonnet-20241022",
            env_file=empty_env,
            tier1_only=False,  # not forced; falls through to True after key check
            dry_run=False,
        )
    finally:
        if saved is not None:
            os.environ["NC_ANTHROPIC_API_KEY"] = saved

    assert rc == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["api_key_status"] == "missing"
    assert manifest["tier1_records"] == 10
    assert manifest["tier2_records"] == 0
    assert manifest["total_cost_usd"] == 0.0
    assert manifest["api_calls"] == 0
    assert any("API key" in note for note in manifest["notes"])


def test_dry_run_tier2_synthesizes_placeholders_without_api(tmp_path):
    """Dry-run Tier 2 produces parent-linked placeholder records."""
    out_path = tmp_path / "out.jsonl"
    manifest_path = tmp_path / "manifest.json"
    rc = sdg.run(
        tier1_target=20,
        tier2_target=20,
        out_path=out_path,
        manifest_path=manifest_path,
        seed=23,
        concurrency=2,
        cost_cap_usd=10.0,
        primary_model="claude-sonnet-4-6",
        fallback_model="claude-3-5-sonnet-20241022",
        env_file=tmp_path / "nonexistent.env",
        tier1_only=False,
        dry_run=True,
    )
    assert rc == 0

    records = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines() if line]
    tier1 = [r for r in records if r["tier"] == "tier1"]
    tier2 = [r for r in records if r["tier"] == "tier2"]
    assert len(tier1) == 20
    assert len(tier2) == 20
    # Every Tier 2 must point at a Tier 1 parent.
    tier1_ids = {r["id"] for r in tier1}
    for r in tier2:
        assert r["parent_ids"], "tier2 record must have parent_ids"
        for pid in r["parent_ids"]:
            assert pid in tier1_ids, f"tier2 parent {pid} not in tier1"
    # Dry-run must not record any API spend.
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["api_calls"] == 0
    assert manifest["total_cost_usd"] == 0.0
    assert manifest["api_key_status"] == "dry-run"


def test_cost_cap_enforced():
    """CostTracker aborts when adding tokens crosses the cap."""
    import asyncio
    tracker = sdg.CostTracker(hard_cap_usd=0.001)  # $0.001 cap
    # Each input token at $3/M => $3 / 1_000_000. 1 token = $0.000003.
    # 1000 input tokens = $0.003 > $0.001. Should abort.
    async def _go():
        return await tracker.add(1000, 0)
    ok = asyncio.run(_go())
    assert ok is False
    assert tracker.aborted is True


def test_tier2_jobs_carry_parent_lineage():
    """Tier 2 job builder pairs parents with stratified (profile, tone) cells."""
    trace_id = str(uuid.uuid4())
    tier1_records = sdg.generate_tier1(target=200, seed=31, trace_id=trace_id)
    jobs = sdg.build_tier2_jobs(tier1_records, target=50, seed=32, k_per_parent=5)
    assert len(jobs) == 50
    parent_ids = {job.parent_id for job in jobs}
    assert all(pid in {r["id"] for r in tier1_records} for pid in parent_ids)
    # Each job carries a (profile, tone) drawn from the canonical taxonomy.
    valid_profiles = {p.code for p in sdg.PROFILES}
    valid_tones = {t.code for t in sdg.TONES}
    for job in jobs:
        assert job.profile_code in valid_profiles
        assert job.tone_code in valid_tones
        assert "Voice spec" in job.user_message
        assert "{topic}" not in job.user_message  # template fully formatted


def test_tier1_records_pass_validator_at_high_rate():
    """Tier 1 templates are designed clean — validator pass rate >= 95%."""
    records = sdg.generate_tier1(target=500, seed=51, trace_id="t")
    pass_rate = sum(1 for r in records if r["validator_pass"]) / len(records)
    assert pass_rate >= 0.95, (
        f"tier1 validator pass rate too low: {pass_rate:.3f} "
        f"(template hygiene regressed)"
    )


def test_anti_drift_3_uses_visceral_vocabulary():
    """^3 templates must use visceral aversion vocabulary, not analytical
    audit/scrutinize/find-flaws vocabulary (anti-drift annotation)."""
    visceral_markers = (
        "stomach",
        "rubs me the wrong way",
        "ten-foot pole",
        "recoils",
        "knot in my gut",
        "wrong with me",
        "won't compromise",
        "hard line",
        "won't endorse",
    )
    analytical_markers = (
        "audit",
        "scrutinize",
        "find the flaw",
        "stress-test",
    )
    for register in sdg.REGISTERS:
        templates = sdg.NOETIC_REGISTER_TEMPLATES[("^3", register)]
        for tpl in templates:
            assert not any(m in tpl.lower() for m in analytical_markers), (
                f"^3 template uses analytical vocabulary (should be ^6): {tpl!r}"
            )
        joined = " ".join(t.lower() for t in templates)
        assert any(m in joined for m in visceral_markers), (
            f"^3 register {register} templates missing visceral vocabulary: "
            f"{templates}"
        )


def test_anti_drift_8_uses_associative_vocabulary():
    """^8 templates must use associative-trigger vocabulary, not deductive
    'therefore'-style reasoning vocabulary (anti-drift annotation)."""
    associative_markers = (
        "reminds me",
        "leading to another",
        "triggers",
        "brings to mind",
        "kicked off",
        "made me think",
        "brought up",
        "hit a smell-memory",
        "brings to",
        "flagging",
    )
    deductive_markers = (
        "therefore",
        "hence",
        "it follows that",
        "we can conclude",
    )
    for register in sdg.REGISTERS:
        templates = sdg.NOETIC_REGISTER_TEMPLATES[("^8", register)]
        for tpl in templates:
            assert not any(m in tpl.lower() for m in deductive_markers), (
                f"^8 template uses deductive vocabulary "
                f"(should be ^6+^9 compound): {tpl!r}"
            )
        joined = " ".join(t.lower() for t in templates)
        assert any(m in joined for m in associative_markers), (
            f"^8 register {register} templates missing associative vocabulary: "
            f"{templates}"
        )
