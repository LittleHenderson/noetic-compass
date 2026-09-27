"""Exercise the real CAS runtime and a fresh replay process on admitted AWS."""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

from .contracts import HarnessConfig, ModificationProposal, SelfDescription, build_candidate, digest
from .episode import reload_episode, witness
from .native_bridge import ROOT, _runtime, execute_candidate, parent_identity, run_branch


@pytest.mark.parametrize("operation", ["CHANGE_CONFIG", "COMPOSE_SUPPORTED_COMPONENTS"])
def test_real_candidate_changes_native_calls_and_reloads_in_fresh_process(tmp_path, operation):
    directory = tmp_path / "episode"
    episode = witness(directory, operation=operation)
    assert episode["receipt"]["disposition"] == "RETAINED_RESEARCH_ONLY"
    assert episode["baseline"]["checked_effect"] is False
    assert episode["candidate"]["checked_effect"] is True
    assert episode["baseline"]["operations"] != episode["candidate"]["operations"]
    assert "PUSH_PRIMITIVE_ACQUISITION" in episode["candidate"]["operations"]
    assert episode["baseline"]["input_sha256"] == episode["candidate"]["input_sha256"]
    assert episode["baseline"]["host_entries"] <= 32 and episode["candidate"]["host_entries"] <= 32
    command = [sys.executable, "-B", "-m", "research.helm_self_improvement.episode", "reload",
               "--directory", str(directory), "--expected-episode-digest", episode["episode_digest"]]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120, check=True)
    reloaded = json.loads(result.stdout)
    assert reloaded["native_replay"] == episode["candidate"]["native_replay"]
    assert reloaded["model_calls"] == 0


def test_no_change_is_preserved_as_rejected_episode(tmp_path):
    episode = witness(tmp_path / "no-change", operation="NO_CHANGE")
    assert episode["receipt"]["disposition"] == "REJECTED_NO_CHECKED_REPAIR"
    assert episode["receipt"]["original_prediction"] == episode["receipt"]["candidate_prediction"]
    assert reload_episode(tmp_path / "no-change", episode["episode_digest"])["native_replay"] is None


def test_disabled_and_shadow_preserve_real_authoritative_state():
    parent = parent_identity()
    d = SelfDescription(parent, HarnessConfig(False))
    baseline, o = run_branch(parent, d.config)
    p = ModificationProposal(parent, digest(asdict(o)), "CHANGE_CONFIG", (True,), "Codex fixture",
                             "acquisition", ("NO_CHANGE",))
    c = build_candidate(d, o, p)
    for mode in ("disabled", "shadow"):
        result, _ = execute_candidate(d, o, c, mode=mode)
        for key in ("state_hash", "original_prediction", "operations", "trace_sha256", "host_entries"):
            assert result[key] == baseline[key]


@pytest.mark.parametrize("file", ["candidate_build.json", "candidate/events.jsonl", "baseline/journal.json"])
def test_replay_rejects_altered_retained_files(tmp_path, file):
    directory = tmp_path / "episode"
    episode = witness(directory)
    with (directory / file).open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ValueError, match="REPLAY_FILE_ALTERED"):
        reload_episode(directory, episode["episode_digest"])


def test_candidate_cannot_recompute_caller_acceptance_anchor(tmp_path):
    directory = tmp_path / "episode"
    episode = witness(directory, operation="NO_CHANGE")
    expected = episode["episode_digest"]
    episode["receipt"]["disposition"] = "RETAINED_RESEARCH_ONLY"
    episode["episode_digest"] = digest({k: v for k, v in episode.items() if k != "episode_digest"})
    (directory / "episode.json").write_text(json.dumps(episode))
    with pytest.raises(ValueError, match="EPISODE_INTEGRITY_FAILED"):
        reload_episode(directory, expected)


def test_native_failure_preserves_partial_journal_without_retry(tmp_path, monkeypatch):
    parent = parent_identity()
    _, _, native, _ = _runtime(parent)
    calls = []

    def fail_after_one_step(machine, **options):
        calls.append(1)
        native.controlled_step(machine, allow_acquisition=options["allow_acquisition"])
        raise RuntimeError("INJECTED_AFTER_NATIVE_WORK")

    monkeypatch.setattr(native, "run_episode", fail_after_one_step)
    destination = tmp_path / "failed"
    with pytest.raises(RuntimeError, match="INJECTED_AFTER_NATIVE_WORK"):
        run_branch(parent, HarnessConfig(True), destination=destination)
    failure = json.loads((destination / "failure.json").read_bytes())
    partial = json.loads((destination / "partial_journal.json").read_bytes())
    assert failure["status"] == "FAILED_NOT_RETRIED" and failure["work_refunded"] is False
    assert len(calls) == 1 and partial["episodes"][0]["trace"]
