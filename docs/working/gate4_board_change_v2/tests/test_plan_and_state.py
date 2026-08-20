import copy
import json
import shutil
from pathlib import Path

import pytest

from core import (
    ContractError,
    ExperimentState,
    PHASE_MOCK_GENERATING,
    REQUIRED_PROTOCOL_FILES,
    SCHEMA_PROTOCOL_LOCK,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    validate_prompt_plan,
    validate_protocol_lock,
)
from helpers import (
    ManualClock,
    RUN_ID,
    frozen_state,
    make_authorization,
    make_plan,
    make_protocol_fixture,
)


def test_prompt_plan_is_exactly_72n_20s_and_92_unique_seeds():
    result = validate_prompt_plan(make_plan())
    assert result["strata"] == {"N": 72, "S": 20}
    assert result["unique_exact_seed_hashes"] == 92
    assert result["unique_normalized_seed_prompts"] == 92
    assert all(counts == {"N": 18, "S": 5, "total": 23}
               for counts in result["generators"].values())


def test_prompt_plan_rejects_normalized_duplicate_and_historical_reuse():
    plan = make_plan()
    plan["conversations"][1]["seed_prompt"] = "  " + plan["conversations"][0][
        "seed_prompt"
    ].upper() + "  "
    from core import sha256_text
    plan["conversations"][1]["seed_prompt_sha256"] = sha256_text(
        plan["conversations"][1]["seed_prompt"]
    )
    with pytest.raises(ContractError, match="normalized seed prompt duplicate"):
        validate_prompt_plan(plan)

    fresh = make_plan()
    blocked = fresh["conversations"][0]["seed_prompt_sha256"]
    with pytest.raises(ContractError, match="historical v1"):
        validate_prompt_plan(fresh, forbidden_seed_hashes=[blocked])


def test_prompt_plan_rejects_wrong_shape_and_nonblind_authoring():
    plan = make_plan()
    plan["conversations"].pop()
    with pytest.raises(ContractError, match="exactly 92"):
        validate_prompt_plan(plan)
    plan = make_plan()
    plan["authoring"]["blind_to_board_rubric"] = False
    with pytest.raises(ContractError, match="blind_to_board_rubric"):
        validate_prompt_plan(plan)


def test_state_machine_requires_exact_one_use_full_authorization(tmp_path):
    plan = make_plan()
    validation = validate_prompt_plan(plan)
    source_root, lock, protocol_sha = make_protocol_fixture(tmp_path, plan)
    state = ExperimentState(tmp_path / "run")
    state.initialize(run_id=RUN_ID, protocol_lock_sha256=protocol_sha,
                     prompt_plan_sha256=validation["plan_sha256"])
    state.freeze_protocol(prompt_plan=plan, protocol_lock=lock, source_root=source_root)
    with pytest.raises(ContractError):
        state.start_generation(authorization_sha256="2" * 64)

    authorization = make_authorization(validation["plan_sha256"], protocol_sha)
    with pytest.raises(ContractError, match="PRODUCTION_AUTHORITY_INTEGRATION_ABSENT"):
        state.authorize_full(authorization)
    _, _, _, _, _, mock_state, _ = frozen_state(tmp_path / "mock")
    assert mock_state.phase == PHASE_MOCK_GENERATING
    assert mock_state.events()[2]["evidence"]["production_authorization_status"] == "NOT_AUTHORIZED"


def test_state_hash_chain_detects_tampering(tmp_path):
    plan = make_plan()
    validation = validate_prompt_plan(plan)
    state = ExperimentState(tmp_path / "run")
    state.initialize(run_id=RUN_ID, protocol_lock_sha256="1" * 64,
                     prompt_plan_sha256=validation["plan_sha256"])
    text = state.path.read_text(encoding="utf-8").replace('"DRAFT"', '"DRAFX"', 1)
    state.path.write_text(text, encoding="utf-8")
    with pytest.raises(ContractError, match="record hash mismatch"):
        state.current()


def test_protocol_lock_binds_every_required_file_and_v1_exclusion_bank(tmp_path):
    source = Path(__file__).resolve().parents[1]
    frozen = tmp_path / "frozen"
    for relative in REQUIRED_PROTOCOL_FILES:
        target = frozen / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
    plan = make_plan()
    plan_path = frozen / "prompt_plan_v2.json"
    plan_path.write_bytes(canonical_json_bytes(plan) + b"\n")
    relative_paths = sorted(REQUIRED_PROTOCOL_FILES | {"prompt_plan_v2.json"})
    files = [
        {"relative_path": relative, "bytes": (frozen / relative).stat().st_size,
         "sha256": sha256_file(frozen / relative)}
        for relative in relative_paths
    ]
    lock = {
        "schema_version": SCHEMA_PROTOCOL_LOCK,
        "protocol_id": "board-change-v2",
        "git_commit_sha": "3" * 40,
        "remote_ref": "refs/heads/frozen-fixture",
        "remote_commit_observed_at_utc": "2026-08-20T08:01:00Z",
        "network_transport_present": False,
        "prompt_plan_relative_path": "prompt_plan_v2.json",
        "prompt_plan_sha256": sha256_bytes(canonical_json_bytes(plan)),
        "v1_seed_fingerprints_relative_path": "v1_seed_fingerprints.json",
        "claim_bearing_files": files,
    }
    result = validate_protocol_lock(lock, source_root=frozen, prompt_plan=plan)
    assert result["valid"] is True
    assert result["locked_file_count"] == len(files)
    assert result["production_lock_status"] == "UNVERIFIED_OFFLINE"
    assert result["production_authorization_available"] is False

    (frozen / "core.py").write_text("tampered", encoding="utf-8")
    with pytest.raises(ContractError, match="bytes/hash mismatch"):
        validate_protocol_lock(lock, source_root=frozen, prompt_plan=plan)
