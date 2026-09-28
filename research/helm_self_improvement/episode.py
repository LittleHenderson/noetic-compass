"""One externally authored H1/H2 build/test/reload episode; admitted AWS only."""
import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil

from .admission import ROOT, TrustedHost, contained, file_hash, write_new
from .contracts import (CandidateBuild, FailureObservation, HarnessConfig, ModificationProposal,
                        ParentIdentity, SelfDescription, build_candidate, digest)
from .native_bridge import execute_candidate, run_baseline, verify_run_semantics


@dataclass(frozen=True)
class ExperimentReceipt:
    candidate_id: str
    original_prediction: str | None
    candidate_prediction: str | None
    baseline_checked: bool
    candidate_checked: bool
    actual_operations_changed: bool
    disposition: str
    operation: str
    edit_level: str
    model_calls: int = 0
    attribution: str = "ENGINEERING_ASSISTED"
    benefit_claim: str = "NO_NEURAL_OR_COMPARATIVE_BENEFIT_CLAIM"


def decide(candidate, baseline, result):
    changed = baseline["operations"] != result["operations"]
    retain = (result["mode"] == "active" and result["checked_effect"] and not baseline["checked_effect"] and changed
              and baseline["input_sha256"] == result["input_sha256"]
              and baseline["host_step_limit"] == result["host_step_limit"] == 32)
    return ExperimentReceipt(candidate.candidate_id, baseline["original_prediction"],
                             result["original_prediction"], baseline["checked_effect"],
                             result["checked_effect"], changed,
                             "RETAINED_RESEARCH_ONLY" if retain else "REJECTED_NO_CHECKED_REPAIR",
                             candidate.proposal.operation, candidate.edit_level)


def read_candidate(value):
    if set(value) != {"parent", "proposal", "config", "candidate_id", "edit_level", "build_sequence", "isolation"}:
        raise ValueError("CANDIDATE_FIELDS_CHANGED")
    proposal = dict(value["proposal"])
    proposal["parent"] = ParentIdentity(**proposal["parent"])
    proposal["parameters"] = tuple(proposal["parameters"])
    proposal["alternatives"] = tuple(proposal["alternatives"])
    return CandidateBuild(ParentIdentity(**value["parent"]), ModificationProposal(**proposal),
                          HarnessConfig(**value["config"]), value["candidate_id"],
                          value["edit_level"], value["build_sequence"], value["isolation"])


def read_observation(value):
    data = dict(value)
    data["parent"] = ParentIdentity(**data["parent"])
    return FailureObservation(**data)


def witness(host, destination, *, operation="CHANGE_CONFIG"):
    host.validate_parent(host.parent)
    if host.baseline_config != HarnessConfig(False):
        raise ValueError("INJECTED_FAILURE_WITNESS_REQUIRES_ADMITTED_DISABLED_BASELINE")
    destination = Path(destination).resolve()
    if destination.is_relative_to(ROOT.resolve()) or destination.is_relative_to(host.evidence_root):
        raise ValueError("EPISODE_OUTPUT_MUST_BE_SEPARATE")
    destination.mkdir(parents=True, exist_ok=False)
    description = SelfDescription(host.parent, host.baseline_config)
    baseline, observation = run_baseline(host)
    parameters = {"NO_CHANGE": (), "CHANGE_CONFIG": (True,),
                  "COMPOSE_SUPPORTED_COMPONENTS": ("parent_transform", "prerequisite_acquisition",
                                                    "verification_commit")}[operation]
    proposal = ModificationProposal(host.parent, digest(asdict(observation)), operation, parameters)
    candidate = build_candidate(host, description, observation, proposal)
    write_new(destination / "candidate_build.json", asdict(candidate))
    write_new(destination / "failure_observation.json", asdict(observation))
    result, _ = execute_candidate(host, description, observation, candidate, mode="active")
    receipt = decide(candidate, baseline, result)
    if receipt.disposition == "RETAINED_RESEARCH_ONLY" and result["native_replay"] is None:
        raise ValueError("REPLAY_REQUIRED_FOR_RETENTION")
    for label, summary in (("baseline", baseline), ("candidate", result)):
        shutil.copytree(host.evidence_root / "runs" / summary["run_id"], destination / label)
        verify_run_semantics(host, summary, destination / label)
    inventory = [{"path": p.relative_to(destination).as_posix(), "bytes": p.stat().st_size,
                  "sha256": file_hash(p)} for p in sorted(destination.rglob("*")) if p.is_file()]
    body = {"schema": "helm.si.improvement-episode/2", "parent": asdict(host.parent),
            "host_policy_sha256": host.policy_sha256, "observation_sha256": digest(asdict(observation)),
            "candidate_id": candidate.candidate_id, "receipt": asdict(receipt),
            "baseline": baseline, "candidate": result, "files": inventory,
            "actual_action": {"operation": operation, "edit_level": candidate.edit_level,
                             "before_config": asdict(host.baseline_config), "after_config": asdict(candidate.config)},
            "promotion": "NOT_REQUESTED_RESEARCH_ONLY",
            "authorship": {"observed": "admitted host native run", "proposed": proposal.proposer,
                           "executed": "existing CompoundMachine through source-pinned CAS adapter",
                           "checked": "existing public Effect checker and native replay"},
            "limits": {"host_entries_per_branch_max": 32, "branches": 2, "model_calls": 0,
                       "generated_code": False, "automatic_retries": 0},
            "cost": {"provider_actual_bill_usd": None,
                     "measured_runtime_wall_ns": baseline["runtime_wall_ns"] + result["runtime_wall_ns"],
                     "host_entries": baseline["host_entries"] + result["host_entries"],
                     "complete_compute": None},
            "claim": "H1/H2; EXTERNALLY_AUTHORED; INJECTED_CONFIGURATION_FAILURE; DETERMINISTIC_NATIVE_EXECUTION; RESEARCH_RETENTION_ONLY"}
    episode = {**body, "episode_digest": digest(body)}
    write_new(destination / "episode.json", episode)
    host.record_episode(episode)
    return episode


def reload_episode(host, directory, expected_episode_digest):
    host.validate_parent(host.parent)
    directory = Path(directory).resolve()
    episode = json.loads((directory / "episode.json").read_bytes())
    body = {k: v for k, v in episode.items() if k != "episode_digest"}
    if episode["episode_digest"] != expected_episode_digest or digest(body) != expected_episode_digest:
        raise ValueError("EPISODE_INTEGRITY_FAILED")
    # A newly self-computed digest cannot replace the host's independent retained record.
    host.verify_episode_anchor(episode)
    host.validate_parent(ParentIdentity(**episode["parent"]))
    if episode["schema"] != "helm.si.improvement-episode/2" or episode["host_policy_sha256"] != host.policy_sha256:
        raise ValueError("EPISODE_ADMISSION_MISMATCH")
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
    if actual != {"episode.json"} | {r["path"] for r in episode["files"]}:
        raise ValueError("REPLAY_INVENTORY_CHANGED")
    for row in episode["files"]:
        path = contained(directory, row["path"])
        if path.stat().st_size != row["bytes"] or file_hash(path) != row["sha256"]:
            raise ValueError("REPLAY_FILE_ALTERED_OR_TRUNCATED")
    candidate = read_candidate(json.loads((directory / "candidate_build.json").read_bytes()))
    observation = read_observation(json.loads((directory / "failure_observation.json").read_bytes()))
    description = SelfDescription(host.parent, host.baseline_config)
    host.verify_candidate(description, observation, candidate)
    if (candidate.candidate_id != episode["candidate_id"] or
            digest(asdict(observation)) != episode["observation_sha256"] or
            observation.run_id != episode["baseline"]["run_id"] or
            episode["candidate"]["run_sequence"] <= candidate.build_sequence or
            episode["candidate"]["candidate_id"] != candidate.candidate_id):
        raise ValueError("EPISODE_LOGICAL_ORDER_MISMATCH")
    expected = decide(candidate, episode["baseline"], episode["candidate"])
    if asdict(expected) != episode["receipt"]:
        raise ValueError("REPLAY_DISPOSITION_MISMATCH")
    if episode["actual_action"] != {"operation": candidate.proposal.operation, "edit_level": candidate.edit_level,
                                    "before_config": asdict(host.baseline_config), "after_config": asdict(candidate.config)}:
        raise ValueError("REPLAY_ACTION_MISMATCH")
    verify_run_semantics(host, episode["baseline"], directory / "baseline")
    replay = verify_run_semantics(host, episode["candidate"], directory / "candidate")
    return {"status": "RESEARCH_EPISODE_RELOADED", "candidate_id": candidate.candidate_id,
            "disposition": expected.disposition, "native_replay": replay,
            "promotion": "NOT_REQUESTED_RESEARCH_ONLY", "model_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-admission", required=True, help="Operator-owned policy outside source/candidate tree")
    parser.add_argument("--expected-admission-sha256", required=True, help="Independently retained by the operator")
    parser.add_argument("--host-evidence", required=True, help="Host-owned directory unavailable to typed candidates")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("witness")
    run.add_argument("--output", required=True)
    run.add_argument("--operation", choices=("NO_CHANGE", "CHANGE_CONFIG", "COMPOSE_SUPPORTED_COMPONENTS"), default="CHANGE_CONFIG")
    replay = sub.add_parser("reload")
    replay.add_argument("--directory", required=True)
    replay.add_argument("--expected-episode-digest", required=True)
    args = parser.parse_args()
    host = TrustedHost(args.trusted_admission, args.expected_admission_sha256, args.host_evidence)
    result = witness(host, args.output, operation=args.operation) if args.command == "witness" else reload_episode(host, args.directory, args.expected_episode_digest)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
