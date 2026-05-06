"""Tests for the Tier 3 native-NL dialogue SDG script.

The suite uses --dry-run style paths only. It never calls the Anthropic API
and never spends money.
"""

from __future__ import annotations

import importlib.util as _importlib_util
import json
import sys
from contextlib import contextmanager
from collections import defaultdict
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = (
    _REPO_ROOT
    / "cas-synthetic"
    / "scripts"
    / "generate_tier3_dialogue_v1.py"
)


def _load_tier3_module():
    mod_name = "generate_tier3_dialogue_v1_module"
    spec = _importlib_util.spec_from_file_location(mod_name, _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = _importlib_util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


tier3 = _load_tier3_module()

_TMP_ROOT = (
    _REPO_ROOT
    / "manual_tmp_test"
    / "codex_tier3_dialogue"
)


@contextmanager
def _fresh_paths(name: str):
    _TMP_ROOT.mkdir(parents=True, exist_ok=True)

    def _clean() -> None:
        for path in _TMP_ROOT.glob(f"{name}*"):
            if path.is_file():
                path.unlink()

    _clean()
    out_prefix = _TMP_ROOT / name
    manifest_path = _TMP_ROOT / f"{name}_manifest.json"
    env_file = _TMP_ROOT / f"{name}.env"
    try:
        yield out_prefix, manifest_path, env_file
    finally:
        _clean()


REQUIRED_FIELDS = (
    "id",
    "created_at",
    "schema_version",
    "trace_id",
    "tier",
    "parent_ids",
    "source",
    "source_template_id",
    "generator_model",
    "generation_timestamp",
    "conversation_id",
    "turn_index",
    "turn_count",
    "cas_expression",
    "expression_family",
    "noetic",
    "domain",
    "drive",
    "register",
    "register_set",
    "prompt",
    "prompt_text",
    "reply",
    "reply_text",
    "demographic_profile",
    "demographic_profile_code",
    "tone",
    "tone_code",
    "validator_pass",
    "validator_reasons",
    "round_trip_validator",
    "generation_version",
)


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_build_dialogue_jobs_exact_turn_count_and_3_to_7_turns():
    jobs = tier3.build_dialogue_jobs(target_records=50, seed_value=42)
    assert sum(len(job.turn_specs) for job in jobs) == 50
    assert all(3 <= len(job.turn_specs) <= 7 for job in jobs)
    assert len({job.conversation_id for job in jobs}) == len(jobs)


def test_dry_run_writes_shards_manifest_and_schema():
    with _fresh_paths("dialogue_schema") as (out_prefix, manifest_path, env_file):
        rc = tier3.run(
            target_records=12,
            out_prefix=out_prefix,
            manifest_path=manifest_path,
            records_per_shard=5,
            seed_value=20260506,
            concurrency=2,
            cost_cap_usd=500.0,
            primary_model=tier3.PRIMARY_MODEL,
            fallback_model=tier3.FALLBACK_MODEL,
            env_file=env_file,
            dry_run=True,
            resume=True,
        )
        assert rc == 0

        shards = tier3.iter_shard_paths(out_prefix)
        assert [p.name for p in shards] == [
            "dialogue_schema_0000.jsonl",
            "dialogue_schema_0001.jsonl",
            "dialogue_schema_0002.jsonl",
        ]
        records = []
        for shard in shards:
            records.extend(_read_jsonl(shard))
        assert len(records) == 12

        for rec in records:
            missing = [field for field in REQUIRED_FIELDS if field not in rec]
            assert not missing, f"missing fields: {missing}"
            assert rec["schema_version"] == "native_nl.v1"
            assert rec["tier"] == "tier3"
            assert rec["source"] == "dry-run"
            assert rec["generator_model"] == "dry-run"
            assert rec["parent_ids"] == []
            assert rec["round_trip_validator"] == "deferred"
            assert rec["prompt"] == rec["prompt_text"]
            assert rec["reply"] == rec["reply_text"]
            assert rec["validator_pass"] is True

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["total_records"] == 12
        assert manifest["tier3_records"] == 12
        assert manifest["dry_run"] is True
        assert manifest["api_calls"] == 0
        assert manifest["total_cost_usd"] == 0.0
        assert manifest["records_per_shard"] == 5
        assert len(manifest["shard_paths"]) == 3
        assert "expression_family" in manifest["distributions"]


def test_conversation_turn_indices_are_sequential():
    with _fresh_paths("dialogue_turns") as (out_prefix, manifest_path, env_file):
        tier3.run(
            target_records=25,
            out_prefix=out_prefix,
            manifest_path=manifest_path,
            records_per_shard=50,
            seed_value=7,
            concurrency=2,
            cost_cap_usd=500.0,
            primary_model=tier3.PRIMARY_MODEL,
            fallback_model=tier3.FALLBACK_MODEL,
            env_file=env_file,
            dry_run=True,
            resume=True,
        )
        records = _read_jsonl(tier3.shard_path(out_prefix, 0))
        by_conv: dict[str, list[dict]] = defaultdict(list)
        for rec in records:
            by_conv[rec["conversation_id"]].append(rec)

        for conv_records in by_conv.values():
            conv_records.sort(key=lambda r: r["turn_index"])
            assert [r["turn_index"] for r in conv_records] == list(range(len(conv_records)))
            assert all(r["turn_count"] == len(conv_records) for r in conv_records)


def test_resume_skips_existing_records():
    with _fresh_paths("dialogue_resume") as (out_prefix, manifest_path, env_file):
        kwargs = dict(
            target_records=10,
            out_prefix=out_prefix,
            manifest_path=manifest_path,
            records_per_shard=50,
            seed_value=77,
            concurrency=2,
            cost_cap_usd=500.0,
            primary_model=tier3.PRIMARY_MODEL,
            fallback_model=tier3.FALLBACK_MODEL,
            env_file=env_file,
            dry_run=True,
            resume=True,
        )
        assert tier3.run(**kwargs) == 0
        first_records = _read_jsonl(tier3.shard_path(out_prefix, 0))
        assert len(first_records) == 10

        assert tier3.run(**kwargs) == 0
        second_records = _read_jsonl(tier3.shard_path(out_prefix, 0))
        assert len(second_records) == 10
        assert [r["id"] for r in second_records] == [r["id"] for r in first_records]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["resumed_records"] == 10


def test_dry_run_replies_pass_existing_no_jargon_validator():
    jobs = tier3.build_dialogue_jobs(target_records=20, seed_value=5)
    for job in jobs:
        for payload in tier3.render_dry_turns(job):
            ok, reasons = tier3.seed.validate_reply(payload["reply_text"])
            assert ok, f"dry-run reply failed validator: {reasons}"


def test_compound_expression_families_appear_in_proof_scale_jobs():
    jobs = tier3.build_dialogue_jobs(target_records=120, seed_value=9)
    families = {
        spec.expression_family
        for job in jobs
        for spec in job.turn_specs
    }
    assert "base" in families
    assert "register_set" in families
    assert "copresence" in families
    assert "omega_emergent" in families
    assert "recipe" in families


def test_cost_estimate_keeps_500_record_proof_under_default_cap():
    assert tier3.estimate_cost_usd(500) < tier3.DEFAULT_COST_CAP_USD
