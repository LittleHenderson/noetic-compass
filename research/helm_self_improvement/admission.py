"""Trusted host admission and append-only public evidence.

Only the host process opens this API. Candidates are typed data and receive no
paths, environment, file handles or Python execution. The operator supplies the
policy and its independently retained digest OUTSIDE the candidate/source tree.
The policy digest is integrity, not authority: authority is that access boundary
and the admitted source inventory. Arbitrary Python running as this host is
outside this fixture's threat model. No OS sandbox claim is made.
"""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess

from .contracts import (CandidateBuild, FailureObservation, HarnessConfig, ModificationProposal, ParentIdentity,
                        SelfDescription, candidate_configuration, digest, public_observation)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = "7bbf1e0f7bae635126c05b3203cca706ea8654dc"
RUNTIME_SHA = "8182ad52b4468f18f140837dffee0e7debcfe786"
MANIFEST_SHA = "e59767f232c0c6eec3918ab653ffd6c564d25506fd45663307527ceab56d6d6c"
BRANCH = "codex/helm-si-three-lead-20260927"
HARNESS_FILES = ("__init__.py", "contracts.py", "admission.py", "native_bridge.py", "episode.py")
OBSERVATION_FIELDS = ("run_id", "run_sequence", "input_sha256", "trace_sha256",
                      "journal_digest", "original_prediction", "checked_effect", "feedback")


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as out:
        out.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
        out.flush()
        os.fsync(out.fileno())


def contained(root, relative):
    rel = Path(relative)
    target = root / rel
    if rel.is_absolute() or ".." in rel.parts or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("EVIDENCE_PATH_ESCAPE")
    if any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError("SYMLINK_NOT_ADMITTED")
    return target


class TrustedHost:
    def __init__(self, policy_path, expected_policy_sha256, evidence_root):
        self.policy_path = Path(policy_path).resolve()
        self.evidence_root = Path(evidence_root).resolve()
        if (self.policy_path.is_relative_to(ROOT.resolve()) or
                self.evidence_root.is_relative_to(ROOT.resolve())):
            raise ValueError("HOST_AUTHORITY_MUST_BE_OUTSIDE_SOURCE_EXPORT")
        raw = self.policy_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_policy_sha256:
            raise ValueError("HOST_POLICY_ANCHOR_MISMATCH")
        self.policy_sha256 = expected_policy_sha256
        self.policy = json.loads(raw)
        p = self.policy
        if (set(p) != {"schema", "source_sha", "runtime_sha", "manifest_sha256", "branch",
                       "checkpoint_sha256", "harness_files", "baseline_config",
                       "source_anchor_kind", "source_anchor_ref", "host_step_limit", "candidate_access"} or
                p["schema"] != "helm.si.host-admission/1" or p["source_sha"] != SOURCE_SHA or
                p["runtime_sha"] != RUNTIME_SHA or p["manifest_sha256"] != MANIFEST_SHA or
                p["branch"] != BRANCH or p["checkpoint_sha256"] is not None or
                p["host_step_limit"] != 32 or type(p["host_step_limit"]) is not int or
                p["candidate_access"] != "TYPED_PUBLIC_DATA_ONLY_NO_FILES_OR_EXECUTION" or
                p["source_anchor_kind"] != "OPERATOR_VERIFIED_ALLOWLISTED_ORIGINAL_GIT_BYTES" or
                p["source_anchor_ref"] != SOURCE_SHA):
            raise ValueError("UNSUPPORTED_HOST_ADMISSION")
        self.baseline_config = HarnessConfig(**p["baseline_config"])
        self.parent = ParentIdentity(SOURCE_SHA, RUNTIME_SHA, BRANCH, MANIFEST_SHA,
                                     digest(p["harness_files"]))
        self.validate_parent(self.parent)
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        (self.evidence_root / "ledger").mkdir(exist_ok=True)
        (self.evidence_root / "runs").mkdir(exist_ok=True)
        if not self.events():
            self.append("ADMITTED", {"parent": asdict(self.parent), "baseline_config": asdict(self.baseline_config)})
        elif self.events()[0]["body"] != {"parent": asdict(self.parent), "baseline_config": asdict(self.baseline_config)}:
            raise ValueError("FOREIGN_HOST_EVIDENCE_ROOT")

    def validate_parent(self, parent):
        if type(parent) is not ParentIdentity:
            raise ValueError("TYPED_PARENT_REQUIRED")
        ParentIdentity(**asdict(parent))
        if parent != self.parent:
            raise ValueError("PARENT_NOT_ADMITTED_CURRENT")
        if file_hash(self.policy_path) != self.policy_sha256:
            raise ValueError("HOST_POLICY_CHANGED")
        manifest_path = ROOT / "PUBLIC_SOURCE_MANIFEST.json"
        if file_hash(manifest_path) != MANIFEST_SHA:
            raise ValueError("SOURCE_MANIFEST_CHANGED")
        m = json.loads(manifest_path.read_bytes())
        if m["source_commit"] != SOURCE_SHA or m["runtime_commit"] != RUNTIME_SHA:
            raise ValueError("RUNTIME_SOURCE_MISMATCH")
        paths = set()
        for row in m["files"]:
            if row["path"] in paths:
                raise ValueError("DUPLICATE_SOURCE_PATH")
            paths.add(row["path"])
            target = contained(ROOT, row["path"])
            if target.stat().st_size != row["bytes"] or file_hash(target) != row["sha256"]:
                raise ValueError("PINNED_CAS_SOURCE_CHANGED")
        hashes = self.policy["harness_files"]
        if set(hashes) != set(HARNESS_FILES):
            raise ValueError("INCOMPLETE_HARNESS_ADMISSION")
        for name, expected in hashes.items():
            if file_hash(Path(__file__).parent / name) != expected:
                raise ValueError("HARNESS_IMPLEMENTATION_CHANGED")
        # A history-free AWS export uses the externally admitted branch context.
        # When Git exists, it must agree too; no bootstrap/fetch is attempted.
        if (ROOT / ".git").exists():
            actual = subprocess.check_output(["git", "-C", str(ROOT), "symbolic-ref", "--short", "HEAD"], text=True).strip()
            if actual != BRANCH:
                raise ValueError("WRONG_DEPLOYED_BRANCH_CONTEXT")

    def validate_description(self, description):
        if type(description) is not SelfDescription:
            raise ValueError("TYPED_DESCRIPTION_REQUIRED")
        SelfDescription(**(asdict(description) | {"parent": description.parent, "config": description.config}))
        self.validate_parent(description.parent)
        if description.config != self.baseline_config:
            raise ValueError("BASELINE_NOT_HOST_ADMITTED")

    def events(self):
        events, previous = [], None
        for index, path in enumerate(sorted((self.evidence_root / "ledger").glob("*.json")), 1):
            value = json.loads(path.read_bytes())
            body = {k: v for k, v in value.items() if k != "digest"}
            if (path.name != f"{index:06}.json" or value["sequence"] != index or
                    value["previous"] != previous or value["policy_sha256"] != self.policy_sha256 or
                    digest(body) != value["digest"]):
                raise ValueError("HOST_LEDGER_INTEGRITY_FAILED")
            events.append(value)
            previous = value["digest"]
        return events

    def next_sequence(self):
        return len(self.events()) + 1

    def append(self, kind, body):
        events = self.events()
        value = {"sequence": len(events) + 1, "previous": events[-1]["digest"] if events else None,
                 "policy_sha256": self.policy_sha256, "kind": kind, "body": body}
        event = {**value, "digest": digest(value)}
        write_new(self.evidence_root / "ledger" / f"{value['sequence']:06}.json", event)
        return event

    def begin_run(self, config, mode, candidate_id=None):
        self.validate_parent(self.parent)
        sequence = self.next_sequence()
        run_id = f"run_{sequence:06}"
        self.append("RUN_STARTED", {"run_id": run_id, "config": asdict(config), "mode": mode, "candidate_id": candidate_id})
        directory = self.evidence_root / "runs" / run_id
        directory.mkdir(exist_ok=False)
        return run_id, directory

    def finish_run(self, run_id, summary):
        directory = self.evidence_root / "runs" / run_id
        summary = {**summary, "run_id": run_id, "run_sequence": self.next_sequence()}
        write_new(directory / "summary.json", summary)
        files = {p.name: file_hash(p) for p in sorted(directory.iterdir()) if p.is_file()}
        event = self.append("RUN_FINISHED", {"run_id": run_id, "files": files})
        if event["sequence"] != summary["run_sequence"]:
            raise ValueError("HOST_ORDER_RACE")
        return summary

    def verified_run(self, run_id):
        finished = [e for e in self.events() if e["kind"] == "RUN_FINISHED" and e["body"]["run_id"] == run_id]
        started = [e for e in self.events() if e["kind"] == "RUN_STARTED" and e["body"]["run_id"] == run_id]
        if len(finished) != 1 or len(started) != 1 or started[0]["sequence"] >= finished[0]["sequence"]:
            raise ValueError("RUN_NOT_HOST_RECORDED")
        event = finished[0]
        directory = contained(self.evidence_root / "runs", run_id)
        for name, expected in event["body"]["files"].items():
            if file_hash(contained(directory, name)) != expected:
                raise ValueError("HOST_RUN_EVIDENCE_CHANGED")
        summary = json.loads((directory / "summary.json").read_bytes())
        journal = json.loads((directory / "journal.json").read_bytes())
        bundle = json.loads((directory / "bundle.json").read_bytes())
        if (summary["run_sequence"] != event["sequence"] or summary["run_id"] != run_id or
                summary["trace_sha256"] != digest(journal) or summary["journal_digest"] != journal["journal_digest"] or
                summary["input_sha256"] != digest(bundle["trusted_genesis"]) or
                summary["mode"] != started[0]["body"]["mode"] or
                summary["candidate_id"] != started[0]["body"]["candidate_id"] or
                summary["config_consumed"] != started[0]["body"]["config"]):
            raise ValueError("RUN_EVIDENCE_BINDING_FAILED")
        return summary

    def verify_observation(self, observation):
        if type(observation) is not FailureObservation:
            raise ValueError("TYPED_OBSERVATION_REQUIRED")
        FailureObservation(**(asdict(observation) | {"parent": observation.parent}))
        self.validate_parent(observation.parent)
        summary = self.verified_run(observation.run_id)
        if summary["mode"] != "baseline" or summary["config_consumed"] != asdict(self.baseline_config):
            raise ValueError("OBSERVATION_NOT_ADMITTED_BASELINE")
        expected = public_observation(self.parent, {k: summary[k] for k in OBSERVATION_FIELDS})
        if observation != expected:
            raise ValueError("OBSERVATION_NOT_HOST_EVIDENCE")

    def record_build(self, candidate, observation):
        self.verify_observation(observation)
        if observation.run_sequence >= candidate.build_sequence or candidate.build_sequence != self.next_sequence():
            raise ValueError("OBSERVATION_NOT_BEFORE_BUILD")
        self.append("BUILD", {"candidate": asdict(candidate), "observation": asdict(observation)})

    def verify_candidate(self, description, observation, candidate):
        self.validate_description(description)
        self.verify_observation(observation)
        if type(candidate) is not CandidateBuild:
            raise ValueError("TYPED_CANDIDATE_REQUIRED")
        ModificationProposal(**(asdict(candidate.proposal) | {"parent": candidate.proposal.parent}))
        self.validate_parent(candidate.parent)
        self.validate_parent(candidate.proposal.parent)
        config, level = candidate_configuration(description, candidate.proposal)
        body = {"parent": asdict(self.parent), "proposal": asdict(candidate.proposal),
                "config": asdict(config), "edit_level": level, "build_sequence": candidate.build_sequence}
        expected = CandidateBuild(self.parent, candidate.proposal, config, digest(body), level, candidate.build_sequence)
        if candidate != expected or candidate.proposal.observation_sha256 != digest(asdict(observation)):
            raise ValueError("CANDIDATE_BUILD_ALTERED")
        matches = [e for e in self.events() if e["kind"] == "BUILD" and e["sequence"] == candidate.build_sequence]
        # JSON normalizes tuples: compare the canonical digest of both records.
        if (len(matches) != 1 or observation.run_sequence >= candidate.build_sequence or
                digest(matches[0]["body"]) != digest({"candidate": asdict(candidate), "observation": asdict(observation)})):
            raise ValueError("BUILD_NOT_HOST_RECORDED")

    def record_episode(self, episode):
        self.append("EPISODE", {"episode_digest": episode["episode_digest"], "candidate_id": episode["candidate_id"]})

    def verify_episode_anchor(self, episode):
        if not any(e["kind"] == "EPISODE" and e["body"] == {
                "episode_digest": episode["episode_digest"], "candidate_id": episode["candidate_id"]} for e in self.events()):
            raise ValueError("EPISODE_NOT_HOST_RECORDED")
