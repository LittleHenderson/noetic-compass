from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "services"
    / "cas_harness_pythia160m_research_lock.py"
)
SPEC = importlib.util.spec_from_file_location("pythia160m_lock_validator", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_prior_v1_lock_fails_closed_after_successor_executor_exists() -> None:
    before = set(sys.modules)
    with pytest.raises(
        MODULE.PythiaResearchLockError,
        match="not bound by a successor lock",
    ):
        MODULE.validate_repository(ROOT)
    after = set(sys.modules)
    assert not (MODULE.FORBIDDEN_FRAMEWORK_MODULES & (after - before))


def test_gpt2_cannot_be_substituted_into_family_lock() -> None:
    lock = MODULE.load_json(ROOT / MODULE.LOCK_RELATIVE_PATH)
    mutated = copy.deepcopy(lock)
    mutated["family_scope"]["included"]["model_id"] = "gpt2"
    with pytest.raises(MODULE.PythiaResearchLockError, match="Wrong model family"):
        MODULE.validate_repository(ROOT, mutated)


def test_live_receipt_and_executor_status_fail_closed() -> None:
    lock = MODULE.load_json(ROOT / MODULE.LOCK_RELATIVE_PATH)
    mutated = copy.deepcopy(lock)
    mutated["current_prohibitions"]["live_receipt_exists"] = True
    with pytest.raises(MODULE.PythiaResearchLockError, match="Live receipt"):
        MODULE.validate_repository(ROOT, mutated)
    mutated = copy.deepcopy(lock)
    mutated["executor_contract"]["status"] = "READY"
    with pytest.raises(MODULE.PythiaResearchLockError, match="must not imply"):
        MODULE.validate_repository(ROOT, mutated)


def test_compute_and_control_drift_fail_closed() -> None:
    lock = MODULE.load_json(ROOT / MODULE.LOCK_RELATIVE_PATH)
    mutated = copy.deepcopy(lock)
    mutated["compute_cap"]["network_allowed"] = True
    with pytest.raises(MODULE.PythiaResearchLockError, match="network_allowed"):
        MODULE.validate_repository(ROOT, mutated)
    mutated = copy.deepcopy(lock)
    mutated["experiment"]["controls"].remove("patch_back")
    with pytest.raises(MODULE.PythiaResearchLockError, match="Control set drift"):
        MODULE.validate_repository(ROOT, mutated)


def test_prompt_overlap_and_non_unit_direction_fail_closed() -> None:
    split = MODULE.load_json(
        ROOT
        / "docs"
        / "working"
        / "research_intervention_pythia160m_v1"
        / "PYTHIA160M_PROMPT_SPLIT_V1.json"
    )
    mutated_split = copy.deepcopy(split)
    mutated_split["heldout"]["^0|C"][0] = mutated_split["calibration"]["^0|C"][0]
    with pytest.raises(MODULE.PythiaResearchLockError):
        MODULE._validate_prompt_split(mutated_split)

    intervention = MODULE.load_json(
        ROOT
        / "docs"
        / "working"
        / "research_intervention_pythia160m_v1"
        / "PYTHIA160M_INTERVENTION_MAP_V1.json"
    )
    mutated_intervention = copy.deepcopy(intervention)
    mutated_intervention["target"]["unit_values"][0] = 0.0
    with pytest.raises(MODULE.PythiaResearchLockError, match="unit L2"):
        MODULE._validate_intervention_map(mutated_intervention)
