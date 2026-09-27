"""Source-bound SI1 -> H1/H2 engineering episode; run only in admitted AWS.

The host owns observations, checks, retention and replay. Candidates are immutable
data values, never programs or paths. There is no system/model promotion API here.
"""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from .contracts import (CandidateBuild, FailureObservation, HarnessConfig, ModificationProposal,
                        ParentIdentity, SelfDescription, build_candidate, digest)
from .native_bridge import execute_candidate, parent_identity, replay_native, run_branch


@dataclass(frozen=True)
class ExperimentReceipt:
    candidate_id: str
    original_prediction: str | None
    candidate_prediction: str | None
    baseline_checked: bool
    candidate_checked: bool
    actual_operations_changed: bool
    disposition: str
    model_calls: int = 0
    attribution: str = "ENGINEERING_ASSISTED"
    benefit_claim: str = "NO_NEURAL_OR_COMPARATIVE_BENEFIT_CLAIM"


def decide(candidate, baseline, result):
    changed = baseline["operations"] != result["operations"]
    retain = (result["checked_effect"] and not baseline["checked_effect"] and changed
              and baseline["input_sha256"] == result["input_sha256"]
              and baseline["host_step_limit"] == result["host_step_limit"])
    return ExperimentReceipt(candidate.candidate_id, baseline["original_prediction"],
                             result["original_prediction"], baseline["checked_effect"],
                             result["checked_effect"], changed,
                             "RETAINED_RESEARCH_ONLY" if retain else "REJECTED_NO_CHECKED_REPAIR")


def _write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def _read_candidate(value):
    if set(value) != {"parent", "proposal", "config", "candidate_id", "edit_level", "isolation"}:
        raise ValueError("CANDIDATE_FIELDS_CHANGED")
    proposal = dict(value["proposal"])
    proposal["parent"] = ParentIdentity(**proposal["parent"])
    proposal["parameters"] = tuple(proposal["parameters"])
    proposal["alternatives"] = tuple(proposal["alternatives"])
    return CandidateBuild(ParentIdentity(**value["parent"]), ModificationProposal(**proposal),
                          HarnessConfig(**value["config"]), value["candidate_id"],
                          value["edit_level"], value["isolation"])


def witness(destination, *, operation="CHANGE_CONFIG"):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    parent = parent_identity()
    description = SelfDescription(parent, HarnessConfig(False))
    baseline, observation = run_branch(parent, description.config, destination=destination / "baseline")
    parameters = {"NO_CHANGE": (), "CHANGE_CONFIG": (True,),
                  "COMPOSE_SUPPORTED_COMPONENTS": ("parent_transform", "prerequisite_acquisition",
                                                    "verification_commit")}[operation]
    proposal = ModificationProposal(parent, digest(asdict(observation)), operation, parameters,
                                    "Codex externally authored fixture",
                                    "Permit the existing bounded prerequisite acquisition path.",
                                    ("NO_CHANGE", "Reject if checks or replay fail"))
    candidate = build_candidate(description, observation, proposal)
    _write(destination / "candidate_build.json", asdict(candidate))
    _write(destination / "failure_observation.json", asdict(observation))
    result, _ = execute_candidate(description, observation, candidate, mode="active",
                                   destination=destination / "candidate")
    receipt = decide(candidate, baseline, result)
    # A retained result requires the unchanged native verifier and exact replay.
    if receipt.disposition == "RETAINED_RESEARCH_ONLY" and result["native_replay"] is None:
        raise ValueError("REPLAY_REQUIRED_FOR_RETENTION")
    inventory = []
    for path in sorted(destination.rglob("*")):
        if path.is_file():
            raw = path.read_bytes()
            inventory.append({"path": path.relative_to(destination).as_posix(), "bytes": len(raw),
                              "sha256": hashlib.sha256(raw).hexdigest()})
    body = {"schema": "helm.si.improvement-episode/1", "parent": asdict(parent),
            "observation_sha256": digest(asdict(observation)), "candidate_id": candidate.candidate_id,
            "receipt": asdict(receipt), "baseline": baseline, "candidate": result,
            "files": inventory, "promotion": "NOT_REQUESTED_RESEARCH_ONLY",
            "authorship": {"observed": "native runtime", "proposed": proposal.proposer,
                           "executed": "existing CompoundMachine through source-pinned CAS adapter",
                           "checked": "existing public Effect checker and native replay"},
            "limits": {"host_entries_per_branch_max": 32, "branches": 2, "model_calls": 0,
                       "generated_code": False, "automatic_retries": 0},
            "cost": {"provider_actual_bill_usd": None,
                     "wall_ns": baseline["wall_ns"] + result["wall_ns"],
                     "host_entries": baseline["host_entries"] + result["host_entries"],
                     "complete_compute": None},
            "claim": "ENGINEERING_ASSISTED; SYMBOLIC_NATIVE_CAS_INTERFACE; NEURAL_HELM_NOT_RUN"}
    episode = {**body, "episode_digest": digest(body)}
    _write(destination / "episode.json", episode)
    return episode


def reload_episode(directory, expected_episode_digest):
    directory = Path(directory)
    episode = json.loads((directory / "episode.json").read_bytes())
    body = {k: v for k, v in episode.items() if k != "episode_digest"}
    if episode["episode_digest"] != expected_episode_digest or digest(body) != expected_episode_digest:
        raise ValueError("EPISODE_INTEGRITY_FAILED")
    if ParentIdentity(**episode["parent"]) != parent_identity():
        raise ValueError("STALE_OR_FOREIGN_REPLAY_PARENT")
    for row in episode["files"]:
        rel = Path(row["path"])
        path = directory / rel
        if rel.is_absolute() or ".." in rel.parts or path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError("REPLAY_PATH_ESCAPE")
        raw = path.read_bytes()
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("REPLAY_FILE_ALTERED_OR_TRUNCATED")
    candidate = _read_candidate(json.loads((directory / "candidate_build.json").read_bytes()))
    obs = json.loads((directory / "failure_observation.json").read_bytes())
    obs["parent"] = ParentIdentity(**obs["parent"])
    observation = FailureObservation(**obs)
    rebuilt = build_candidate(SelfDescription(candidate.parent, HarnessConfig(False)), observation, candidate.proposal)
    if rebuilt != candidate or candidate.candidate_id != episode["candidate_id"]:
        raise ValueError("REPLAY_CANDIDATE_MISMATCH")
    expected = decide(candidate, episode["baseline"], episode["candidate"])
    if asdict(expected) != episode["receipt"]:
        raise ValueError("REPLAY_DISPOSITION_MISMATCH")
    replay = None
    if expected.disposition == "RETAINED_RESEARCH_ONLY":
        replay = replay_native(candidate.parent, directory / "candidate", episode["candidate"]["bundle_digest"])
        if replay != episode["candidate"]["native_replay"]:
            raise ValueError("REPLAY_STATE_MISMATCH")
    return {"status": "RESEARCH_EPISODE_RELOADED", "candidate_id": candidate.candidate_id,
            "disposition": expected.disposition, "native_replay": replay,
            "promotion": "NOT_REQUESTED_RESEARCH_ONLY", "model_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("witness")
    run.add_argument("--output", required=True)
    run.add_argument("--operation", choices=("NO_CHANGE", "CHANGE_CONFIG", "COMPOSE_SUPPORTED_COMPONENTS"), default="CHANGE_CONFIG")
    replay = sub.add_parser("reload")
    replay.add_argument("--directory", required=True)
    replay.add_argument("--expected-episode-digest", required=True)
    args = parser.parse_args()
    if args.command == "witness":
        result = witness(args.output, operation=args.operation)
    else:
        result = reload_episode(args.directory, args.expected_episode_digest)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
