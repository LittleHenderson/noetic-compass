"""Tests for the pilot's launcher binding.

Plan-only and validation paths plus a package build with injected git access: no
provider client, no reservation, no network, no launch.
"""
import io
import json
import shutil
import subprocess
import uuid
import zipfile

import pytest

from aws import graph_training_candidate_launch as cl
from aws import graph_training_curriculum_launch as curriculum

SOURCE_SHA = "a" * 40
ARCHIVE_SHA = "b" * 64
MANIFEST_SHA = "c" * 64
OWNER_SHA = "d" * 64
JOB = "cas-meta2-graph6cand-20260910120000-a1b2c3d4"


def _request(**overrides):
    body = {"schema": cl.REQUEST_SCHEMA, "job": JOB, "source_sha": SOURCE_SHA,
            "archive_sha256": ARCHIVE_SHA, "manifest_sha256": MANIFEST_SHA,
            "launch_authorized": False}
    body.update(overrides)
    return body


def _authority(**overrides):
    body = {"schema": cl.AUTHORITY_SCHEMA, "job": JOB, "source_sha": SOURCE_SHA,
            "archive_sha256": ARCHIVE_SHA, "manifest_sha256": MANIFEST_SHA,
            "owner_authorization_sha256": OWNER_SHA,
            "conditions": list(cl.FROZEN_CONDITIONS),
            "updates_per_condition": cl.FROZEN_UPDATES_PER_CONDITION,
            "total_optimizer_steps": cl.FROZEN_TOTAL_UPDATES,
            "seed": cl.FROZEN_SEED, "encoder_seed": cl.FROZEN_ENCODER_SEED,
            "ordering_mode": cl.FROZEN_ORDERING_MODE,
            "probe_questions": cl.FROZEN_PROBE_QUESTIONS,
            "checkpoints": list(cl.FROZEN_CHECKPOINTS),
            "learning_rate": cl.FROZEN_LEARNING_RATE,
            "max_wall_seconds_per_condition": cl.FROZEN_MAX_WALL_SECONDS,
            "reservation_usd": cl.RESERVATION_USD}
    body.update(overrides)
    return body


def test_plan_only_is_inert_and_binds_this_experiment():
    plan = cl.plan_only()
    assert plan["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert plan["provider_calls"] == 0
    assert plan["reservation_created"] is False
    assert plan["experiment"]["entrypoint"] == \
        "cas_meta2.graph_teaching.candidate_experiment.launch"
    assert plan["design"]["conditions"] == ["checked_component_teaching",
                                            "final_answer_only"]
    assert plan["design"]["updates_per_condition"] == 64
    assert plan["design"]["total_optimizer_steps"] == 128
    assert plan["design"]["seed"] == 20260909
    assert plan["design"]["probe_questions"] == 44
    assert plan["design"]["reservation_usd"] == "7.00"
    assert plan["design"]["launch_enabled"] is False
    assert plan["resource_plan"] == curriculum.scope()
    assert plan["job_pattern"] == cl.JOB_PATTERN


def test_the_client_set_covers_every_name_the_reused_provider_asks_for():
    """Regression guard: the first launch attempt failed with KeyError: 'sts'.

    The reused lifecycle asks for five clients; creating three of them is enough
    to fail at preflight, before any reservation. This test reads the reused
    source and requires CLIENT_NAMES to cover every name it requests.
    """
    import inspect
    import re as _re

    source = inspect.getsource(curriculum)
    asked = set(_re.findall(r'self\.clients\["([a-z0-9]+)"\]', source))
    asked |= {name for group in _re.findall(
        r'\(self\.clients\[name\] for name in \(([^)]*)\)\)', source)
        for name in _re.findall(r'"([a-z0-9]+)"', group)}
    assert asked, "the reused provider must ask for at least one client"
    assert asked <= set(cl.CLIENT_NAMES), sorted(asked - set(cl.CLIENT_NAMES))
    assert set(cl.CLIENT_NAMES) == {"ec2", "s3", "iam", "sts", "pricing"}
def test_the_curriculum_profile_is_preserved_not_overwritten():
    assert curriculum.RESERVATION_USD == cl.RESERVATION_USD
    assert curriculum.JOB_PATTERN != cl.JOB_PATTERN
    assert curriculum.SCHEMA != cl.SCHEMA
    assert curriculum.RESULT_SCHEMA != cl.RESULT_SCHEMA
    assert curriculum.WORKER_NAME != cl.WORKER_NAME
    assert cl.RESERVATION_USD == "7.00"
    plan = curriculum.plan_only()
    assert plan["experiment"]["profile"] == "graph_training_curriculum_comparison"


@pytest.mark.parametrize("overrides,code", [
    ({"schema": "wrong"}, "CANDIDATE_REQUEST_SCHEMA"),
    ({"job": "cas-meta2-graph6curr-20260910120000-a1b2c3d4"}, "CANDIDATE_REQUEST_JOB"),
    ({"source_sha": "short"}, "CANDIDATE_REQUEST_SOURCE_SHA"),
    ({"archive_sha256": "nothex"}, "CANDIDATE_REQUEST_HASH:archive_sha256"),
    ({"launch_authorized": True}, "CANDIDATE_REQUEST_INERT"),
])
def test_request_validation_fails_closed(overrides, code):
    with pytest.raises(ValueError) as error:
        cl.validate_request(_request(**overrides))
    assert str(error.value).startswith(code)


def test_request_field_set_is_exact():
    with pytest.raises(ValueError) as error:
        cl.validate_request({**_request(), "extra": 1})
    assert str(error.value).startswith("CANDIDATE_REQUEST_FIELDS")


@pytest.mark.parametrize("overrides,code", [
    ({"conditions": ["control", "varied"]},
     "CANDIDATE_AUTHORITY_CONDITIONS_FROZEN"),
    ({"updates_per_condition": 256}, "CANDIDATE_AUTHORITY_UPDATES_FROZEN"),
    ({"total_optimizer_steps": 1536}, "CANDIDATE_AUTHORITY_TOTAL_STEPS_FROZEN"),
    ({"seed": 1}, "CANDIDATE_AUTHORITY_SEED_FROZEN"),
    ({"probe_questions": 43}, "CANDIDATE_AUTHORITY_PROBE_FROZEN"),
    ({"ordering_mode": "authored_fixture"}, "CANDIDATE_AUTHORITY_ORDERING_FROZEN"),
    ({"reservation_usd": "4.00"}, "CANDIDATE_AUTHORITY_RESERVATION"),
    ({"learning_rate": 0.01}, "CANDIDATE_AUTHORITY_BUDGET:learning_rate"),
])
def test_authority_validation_freezes_the_design(overrides, code):
    with pytest.raises(ValueError) as error:
        cl.validate_authority(_authority(**overrides))
    assert str(error.value).startswith(code)


def test_authority_accepts_the_declared_design():
    assert cl.validate_authority(_authority())["updates_per_condition"] == 64
    assert cl.validate_request(_request())["launch_authorized"] is False
    plan = cl.plan_only(_request(), _authority())
    assert plan["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert plan["provider_calls"] == 0


def test_the_worker_connects_the_pilot_entrypoint_and_delivers_last():
    worker = cl.render_worker()
    compile(worker, cl.WORKER_NAME, "exec")
    assert "import candidate_experiment as ce" in worker
    assert "ce.launch(" in worker
    assert "build_graph_training_framework" in worker
    assert "GraphLearner" in worker
    assert "gpu_adapter._cuda()" in worker
    assert "weights_only=True" in worker
    assert "condition_order" in worker
    assert "result_partial.json" in worker
    assert "WORKER_FAILED" in worker
    assert worker.index("results/manifest.json") < worker.index("results/result.json")
    assert "REMOTE_FINISHED" in worker


def test_provider_reuses_the_lifecycle_and_binds_the_candidate_config():
    provider = cl.CandidateProvider(
        job=JOB, source_sha=SOURCE_SHA, archive_sha256=ARCHIVE_SHA,
        manifest_sha256=MANIFEST_SHA, ledger_path=curriculum.LEDGER_PATH,
        clients={})
    assert isinstance(provider, curriculum.CurriculumProvider)
    assert provider.worker_name == cl.WORKER_NAME
    assert provider.result_schema == cl.RESULT_SCHEMA
    with pytest.raises(ValueError) as error:
        provider._worker_config("bucket-name")
    assert str(error.value).startswith("CANDIDATE_PROVIDER_AUTHORITY_HASH")
    provider.set_authority_sha256(OWNER_SHA)
    config = provider._worker_config("bucket-name")
    assert config["schema"] == "cas-graph-training-candidate-worker-config/1"
    assert config["conditions"] == ["checked_component_teaching",
                                    "final_answer_only"]
    assert config["updates_per_condition"] == 64
    assert config["probe_questions"] == 44
    assert config["authority_sha256"] == OWNER_SHA
    assert config["ordering_mode"] == "declared"
    assert "pair_seeds" not in config and "panel_seed" not in config


def test_package_builds_from_committed_objects_with_the_candidate_worker():
    """The package is built through the existing builder, with this worker inside.

    The builder refuses any output outside ``records/``, so this test uses a
    scratch directory there and removes it afterwards. Frozen wheels are read from
    the real commit (the builder verifies their digests); source members are
    placeholders, because only the worker script is this test's subject.
    """
    member = curriculum.SOURCE_DIRS[0] + "/candidate_experiment.py"
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                     cwd=str(curriculum.ROOT)).decode().strip()

    def git_bytes(root, commit_sha, name):
        if name in curriculum.WHEELS:
            return curriculum.git_bytes(root, commit_sha, name)
        return ("# placeholder for " + name + "\n").encode("utf-8")

    def git_paths(root, commit_sha, directory):
        return [member] if directory == curriculum.SOURCE_DIRS[0] else []

    output = curriculum.ROOT / "records" / ("candidate_package_test_"
                                            + uuid.uuid4().hex[:12])
    try:
        receipt = cl.build_candidate_package(
            output, source_sha=commit, git_bytes_fn=git_bytes,
            git_paths_fn=git_paths)
        assert receipt["status"] == "SOURCE_ONLY_NO_LAUNCH"
        assert receipt["source_sha"] == commit
        assert receipt["manifest"]["worker_script"] == cl.WORKER_NAME
        assert receipt["manifest"]["experiment"]["profile"] == \
            "graph_training_candidate_component_pilot"
        assert receipt["manifest"]["conditions"] == ["checked_component_teaching",
                                                     "final_answer_only"]
        assert receipt["manifest"]["updates_per_condition"] == 64
        assert receipt["manifest"]["probe_questions"] == 44
        assert receipt["manifest"]["launch_enabled"] is False
        assert receipt["manifest"]["reservation_usd"] == "7.00"
        with zipfile.ZipFile(io.BytesIO((output / "source.zip").read_bytes())) as zipped:
            names = zipped.namelist()
            assert cl.WORKER_NAME in names
            assert member in names
            assert b"ce.launch(" in zipped.read(cl.WORKER_NAME)
        saved = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
        assert saved["archive_sha256"] == receipt["archive_sha256"]
    finally:
        shutil.rmtree(output, ignore_errors=True)
    assert not output.exists()
