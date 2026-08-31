"""campaign_state.py -- the ONE typed campaign lifecycle (GATE 1A.2 section 1).

Eighteen states, one linear claim-bearing path, explicit failure edges. Every
transition is an append-only, digest-chained record that binds the campaign id,
the package commit, the authorizing approval or receipt, and its input/output
digests. Skipped states, repeated states, and records for a different campaign
are refused. No standalone component may self-authorize a transition: the ONLY
writer is CampaignStateMachine.transition(), and the driver holds the machine.

Chain law: transition k carries prev_transition_sha256 = sha256 of transition
k-1's canonical bytes (record with its own sha field empty); the first carries
64 zeros. Replaying a synthetic campaign reproduces the chain digest exactly
(synthetic mode pins utc="SYNTHETIC").
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

STATES = (
    "CREATED", "DESIGN_VERIFIED", "CONTAINER_PREP_AUTHORIZED",
    "IDENTITIES_RESOLVED", "EXECUTION_AUTHORIZED", "AWS_IDENTITY_VERIFIED",
    "DATA_VERIFIED", "MODEL_VERIFIED", "ACTIVATIONS_CACHED", "LAYER_FROZEN",
    "TRAINING_COMPLETE", "PROTECTED_UNOPENED", "PROTECTED_RUNNING",
    "PROTECTED_BURNED", "RESULTS_SEALED", "STATUS_EMITTED",
    "SHUTDOWN_REQUESTED", "TERMINATED")

# the one claim-bearing forward path
_FORWARD = {STATES[i]: STATES[i + 1] for i in range(len(STATES) - 1)}

# explicit failure edges: any non-terminal, non-protected state may fail to
# SHUTDOWN_REQUESTED; a failure INSIDE the protected phase must burn first.
_FAILURE_TARGETS = {
    s: ("PROTECTED_BURNED" if s == "PROTECTED_RUNNING" else "SHUTDOWN_REQUESTED")
    for s in STATES if s not in ("SHUTDOWN_REQUESTED", "TERMINATED")}


class CampaignStateError(RuntimeError):
    pass


def canonical_transition_bytes(record: dict) -> bytes:
    unsealed = dict(record)
    unsealed["transition_sha256"] = ""
    return json.dumps(unsealed, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")).encode("utf-8")


class CampaignStateMachine:
    """Append-only, digest-chained lifecycle for exactly one campaign."""

    def __init__(self, campaign_id: str, package_commit_sha: str,
                 manifest_path: Path, utc_source=None):
        if not campaign_id or not isinstance(campaign_id, str):
            raise CampaignStateError("campaign_id required")
        self.campaign_id = campaign_id
        self.package_commit_sha = package_commit_sha
        self.manifest_path = Path(manifest_path)
        # adversarial-review fix: the DEFAULT clock is the REAL clock; the
        # synthetic replay clock must be passed explicitly (the driver passes
        # lambda: "SYNTHETIC" only in SYNTHETIC_CONFORMANCE mode)
        if utc_source is None:
            from datetime import datetime, timezone
            utc_source = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731
        self._utc_source = utc_source
        self.state = "CREATED"
        self.index = 0
        self.prev_sha = "0" * 64
        self.transitions = []
        self._visited = {"CREATED"}
        self._burned_by_failure = False

    def transition(self, to_state: str, *, binding_kind: str, binding_sha256: str,
                   input_digests: dict = None, output_digests: dict = None,
                   reason: str = "FORWARD") -> dict:
        if to_state not in STATES:
            raise CampaignStateError(f"unknown state {to_state!r}")
        if self.state == "TERMINATED":
            raise CampaignStateError("campaign already TERMINATED; append-only "
                                     "history admits no further transition")
        forward_ok = _FORWARD.get(self.state) == to_state and reason == "FORWARD"
        failure_ok = (reason == "FAILURE"
                      and _FAILURE_TARGETS.get(self.state) == to_state)
        # after a failure burn, the only continuations are the shutdown tail
        tail_ok = (reason == "FAILURE" and self.state == "PROTECTED_BURNED"
                   and to_state == "SHUTDOWN_REQUESTED")
        if not (forward_ok or failure_ok or tail_ok):
            raise CampaignStateError(
                f"REFUSED transition {self.state} -> {to_state} ({reason}): "
                f"states may not be skipped, repeated, or entered out of order")
        # adversarial-review fix: after a FAILURE burn, forward sealing is
        # forbidden -- a failed protected pass can never yield sealed results
        if forward_ok and self.state == "PROTECTED_BURNED" \
                and self._burned_by_failure:
            raise CampaignStateError(
                "REFUSED: the protected pass was burned by FAILURE; results "
                "may not be sealed -- only the shutdown tail remains")
        if to_state in self._visited:
            raise CampaignStateError(
                f"REFUSED: state {to_state} already visited (one-use lifecycle)")
        if not isinstance(binding_sha256, str) or len(binding_sha256) != 64:
            raise CampaignStateError(
                f"transition {self.state} -> {to_state} requires a 64-hex "
                f"approval/receipt binding, got {binding_sha256!r}")
        record = {
            "campaign_id": self.campaign_id,
            "index": self.index,
            "from_state": self.state,
            "to_state": to_state,
            "reason": reason,
            "package_commit_sha": self.package_commit_sha,
            "binding_kind": binding_kind,
            "binding_sha256": binding_sha256,
            "input_digests": dict(input_digests or {}),
            "output_digests": dict(output_digests or {}),
            "prev_transition_sha256": self.prev_sha,
            "utc": self._utc_source(),
            "transition_sha256": "",
        }
        record["transition_sha256"] = hashlib.sha256(
            canonical_transition_bytes(record)).hexdigest()
        self._append(record)
        self.transitions.append(record)
        self.prev_sha = record["transition_sha256"]
        self.state = to_state
        self._visited.add(to_state)
        self.index += 1
        if to_state == "PROTECTED_BURNED" and reason == "FAILURE":
            self._burned_by_failure = True
        return record

    def _append(self, record: dict) -> None:
        line = json.dumps(record, sort_keys=True, ensure_ascii=True,
                          separators=(",", ":"))
        if "\r" in line:
            raise CampaignStateError("CANONICAL_BYTE_VIOLATION in transition record")
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with self.manifest_path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(line + "\n")

    def chain_digest(self) -> str:
        return self.prev_sha if self.transitions else "0" * 64

    def require_state(self, expected: str) -> None:
        if self.state != expected:
            raise CampaignStateError(
                f"REFUSED: operation requires state {expected}, campaign is in "
                f"{self.state}")


def verify_transition_chain(manifest_path: Path, campaign_id: str,
                            package_commit_sha: str) -> dict:
    """Independent re-verification of a persisted transition chain: campaign
    binding, index continuity, digest chaining, legal edges, no repeats.
    Returns {states, chain_digest} or raises CampaignStateError."""
    prev_sha, index, state, visited, last = "0" * 64, 0, "CREATED", {"CREATED"}, None
    burned_by_failure = False
    for n, line in enumerate(
            Path(manifest_path).read_text(encoding="utf-8").splitlines()):
        rec = json.loads(line)
        if rec["campaign_id"] != campaign_id:
            raise CampaignStateError(f"line {n + 1}: WRONG campaign id")
        if rec["package_commit_sha"] != package_commit_sha:
            raise CampaignStateError(f"line {n + 1}: WRONG package commit")
        if rec["index"] != index:
            raise CampaignStateError(f"line {n + 1}: index gap")
        if rec["prev_transition_sha256"] != prev_sha:
            raise CampaignStateError(f"line {n + 1}: digest chain broken")
        expect = hashlib.sha256(canonical_transition_bytes(rec)).hexdigest()
        if rec["transition_sha256"] != expect:
            raise CampaignStateError(f"line {n + 1}: transition digest forged")
        if rec["from_state"] != state:
            raise CampaignStateError(f"line {n + 1}: from_state mismatch")
        ok = (_FORWARD.get(state) == rec["to_state"] and rec["reason"] == "FORWARD") \
            or (rec["reason"] == "FAILURE"
                and (_FAILURE_TARGETS.get(state) == rec["to_state"]
                     or (state == "PROTECTED_BURNED"
                         and rec["to_state"] == "SHUTDOWN_REQUESTED")))
        if not ok:
            raise CampaignStateError(f"line {n + 1}: illegal edge "
                                     f"{state} -> {rec['to_state']}")
        if state == "PROTECTED_BURNED" and burned_by_failure \
                and rec["reason"] == "FORWARD":
            raise CampaignStateError(
                f"line {n + 1}: results sealed after a FAILURE burn")
        if rec["to_state"] == "PROTECTED_BURNED" and rec["reason"] == "FAILURE":
            burned_by_failure = True
        if rec["to_state"] in visited:
            raise CampaignStateError(f"line {n + 1}: repeated state")
        visited.add(rec["to_state"])
        state = rec["to_state"]
        prev_sha = rec["transition_sha256"]
        index += 1
        last = rec
    return {"final_state": state, "transitions": index,
            "chain_digest": prev_sha if last else "0" * 64}
