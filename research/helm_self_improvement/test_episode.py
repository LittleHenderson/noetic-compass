"""Actual native witness, disabled/shadow parity and fresh-process reload in AWS."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from .admission import ROOT
from .contracts import COMPONENTS, HarnessConfig, ModificationProposal, SelfDescription, build_candidate, digest
from .conftest import host_for
from .episode import reload_episode, witness
from .native_bridge import _runtime, execute_candidate, run_baseline


@pytest.fixture(scope="module", params=["CHANGE_CONFIG", "COMPOSE_SUPPORTED_COMPONENTS", "NO_CHANGE"])
def completed_episode(request, tmp_path_factory):
    root = tmp_path_factory.mktemp(request.param.lower())
    host = host_for(root / "authority")
    directory = root / "episode"
    result = witness(host, directory, operation=request.param)
    return host, directory, result, request.param


def test_actual_h1_h2_or_no_change_is_recorded_and_persisted(completed_episode):
    host, directory, episode, operation = completed_episode
    expected = "REJECTED_NO_CHECKED_REPAIR" if operation == "NO_CHANGE" else "RETAINED_RESEARCH_ONLY"
    assert episode["receipt"]["disposition"] == expected
    assert episode["receipt"]["operation"] == operation
    assert episode["receipt"]["edit_level"] == ("H2" if operation == "COMPOSE_SUPPORTED_COMPONENTS" else "H1")
    assert episode["baseline"]["checked_effect"] is False
    assert episode["candidate"]["checked_effect"] is (operation != "NO_CHANGE")
    if operation != "NO_CHANGE":
        assert "PUSH_PRIMITIVE_ACQUISITION" in episode["candidate"]["operations"]
        assert episode["candidate"]["operations"] != episode["baseline"]["operations"]
    for name in ("baseline", "candidate"):
        assert json.loads((directory / name / "summary.json").read_bytes()) == episode[name]
        assert episode[name] == host.verified_run(episode[name]["run_id"])
        assert episode[name]["host_entries"] <= 32
    assert episode["baseline"]["run_sequence"] < episode["candidate"]["run_sequence"]


def test_witness_reloads_in_a_fresh_process_with_same_host_admission(completed_episode):
    host, directory, episode, _ = completed_episode
    command = [sys.executable, "-B", "-m", "research.helm_self_improvement.episode",
               "--trusted-admission", str(host.policy_path), "--expected-admission-sha256", host.policy_sha256,
               "--host-evidence", str(host.evidence_root), "reload", "--directory", str(directory),
               "--expected-episode-digest", episode["episode_digest"]]
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120, check=True)
    result = json.loads(process.stdout)
    assert result["status"] == "RESEARCH_EPISODE_RELOADED"
    assert result["disposition"] == episode["receipt"]["disposition"]
    assert result["native_replay"] == episode["candidate"]["native_replay"]
    assert result["promotion"] == "NOT_REQUESTED_RESEARCH_ONLY"


@pytest.mark.parametrize("baseline_enabled", [False, True], ids=['case_00', 'case_01'])
def test_disabled_shadow_preserve_admitted_parent_and_record_measured_overhead(tmp_path, baseline_enabled):
    host = host_for(tmp_path / "authority", baseline=baseline_enabled)
    baseline, observation = run_baseline(host)
    description = SelfDescription(host.parent, host.baseline_config)
    proposal = ModificationProposal(host.parent, digest(asdict(observation)), "CHANGE_CONFIG", (not baseline_enabled,))
    candidate = build_candidate(host, description, observation, proposal)
    for mode in ("disabled", "shadow"):
        result, _ = execute_candidate(host, description, observation, candidate, mode=mode)
        assert result["mode"] == mode
        assert result["deterministic_parity"] == baseline["deterministic_parity"]
        assert result["config_consumed"] == asdict(host.baseline_config)
        assert result["mode_validation_ns"] >= 0 and result["host_setup_ns"] >= 0
        assert result["runtime_wall_ns"] > 0 and result["verification_and_persistence_ns"] >= 0
        assert "wall" not in result["deterministic_parity"]
        # Wall-dependent receipt/bundle hashes are deliberately not compared as deterministic parity.
        assert result["receipt_identity_includes_wall_fields"] is True
        assert json.loads((host.evidence_root / "runs" / result["run_id"] / "summary.json").read_bytes()) == result


@pytest.mark.parametrize("file", ["candidate_build.json", "candidate/events.jsonl", "baseline/journal.json", "candidate/summary.json"], ids=['case_00', 'case_01', 'case_02', 'case_03'])
def test_replay_rejects_changed_public_copy_even_without_changing_semantics(tmp_path, completed_episode, file):
    import shutil
    host, original, episode, _ = completed_episode
    directory = tmp_path / "copy"
    shutil.copytree(original, directory)
    with (directory / file).open("ab") as out:
        out.write(b" ")
    with pytest.raises(ValueError, match="REPLAY_FILE_ALTERED"):
        reload_episode(host, directory, episode["episode_digest"])


def test_self_recomputed_episode_digest_does_not_authenticate_new_disposition(tmp_path, completed_episode):
    import shutil
    host, original, episode, _ = completed_episode
    directory = tmp_path / "copy"
    shutil.copytree(original, directory)
    altered = json.loads((directory / "episode.json").read_bytes())
    altered["receipt"]["disposition"] = "PROMOTED"
    altered["episode_digest"] = digest({k: v for k, v in altered.items() if k != "episode_digest"})
    (directory / "episode.json").write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError, match="EPISODE_NOT_HOST_RECORDED"):
        reload_episode(host, directory, altered["episode_digest"])


def test_fabricated_summary_and_inventory_cannot_replace_host_run(tmp_path, completed_episode):
    import shutil
    host, original, _, _ = completed_episode
    directory = tmp_path / "copy"
    shutil.copytree(original, directory)
    altered = json.loads((directory / "candidate/summary.json").read_bytes())
    altered["original_prediction"] = "fabricated public output"
    with pytest.raises(ValueError, match="PERSISTED_SUMMARY_DIFFERS"):
        from .native_bridge import verify_run_semantics
        verify_run_semantics(host, altered, directory / "candidate")


def test_failure_preserves_native_work_and_has_no_retry(tmp_path, monkeypatch):
    host = host_for(tmp_path / "authority")
    _, _, native, _ = _runtime(host)
    calls = []

    def fail_after_one_step(machine, **options):
        calls.append(1)
        native.controlled_step(machine, allow_acquisition=options["allow_acquisition"])
        raise RuntimeError("INJECTED_AFTER_NATIVE_WORK")

    monkeypatch.setattr(native, "run_episode", fail_after_one_step)
    with pytest.raises(RuntimeError, match="INJECTED_AFTER_NATIVE_WORK"):
        run_baseline(host)
    failures = [e for e in host.events() if e["kind"] == "RUN_FAILED"]
    assert len(failures) == 1 and len(calls) == 1
    path = host.evidence_root / "runs" / failures[0]["body"]["run_id"]
    failure = json.loads((path / "failure.json").read_bytes())
    assert failure["status"] == "FAILED_NOT_RETRIED" and failure["work_refunded"] is False
    assert json.loads((path / "partial_journal.json").read_bytes())["episodes"][0]["trace"]
