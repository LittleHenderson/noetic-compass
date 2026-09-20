"""The registered typed learner with the owner-approved practice ceiling. Importing performs no numeric work.

`learner.TypedCourseLearner` caps a run at 176 updates and 3,600 seconds. The practice study
(owner-approved 2026-09-18: "Practice test", ten passes over the course) needs about 1,600 updates and
a few hours. This subclass changes ONLY those two ceilings. The forward pass, the recurrence, the frozen
encoder and readout, the loss, the optimizer and the plastic scope are the registered learner's own
code, unchanged and still identity-pinned by `learner.profile()`.

The practice ceilings are recorded in the run identity (`limits`, `practice_learner_profile`), so a
checkpoint from this learner cannot be restored as a registered-learner checkpoint or vice versa.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from . import source
from .learner import TypedCourseLearner

require, digest, canonical = source.require, source.digest, source.canonical
PRACTICE_MAX_UPDATES = 2048
PRACTICE_MAX_WALL_SECONDS = 14400
REGISTERED_MAX_UPDATES, REGISTERED_MAX_WALL_SECONDS = 176, 3600


def practice_profile():
    path = Path(__file__)
    body = {"schema": "cas.typed-practice-learner-profile/0.1",
            "file": {"path": path.relative_to(Path(__file__).parents[2]).as_posix(),
                     "sha256": sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size},
            "max_updates_ceiling": PRACTICE_MAX_UPDATES, "max_wall_seconds_ceiling": PRACTICE_MAX_WALL_SECONDS,
            "changes": "UPDATE_AND_WALL_CEILINGS_ONLY"}
    return {**body, "profile_digest": digest(body)}


def validate_practice_limits(limits):
    require(type(limits) is dict and set(limits) == {"max_updates", "max_core_calls", "max_wall_seconds"}
            and type(limits["max_updates"]) is int and 0 < limits["max_updates"] <= PRACTICE_MAX_UPDATES
            and type(limits["max_core_calls"]) is int and 0 < limits["max_core_calls"] <= 1000000
            and type(limits["max_wall_seconds"]) in (int, float)
            and 0 < limits["max_wall_seconds"] <= PRACTICE_MAX_WALL_SECONDS, "PRACTICE_LEARNER_LIMITS")
    return deepcopy(limits)


class PracticeCourseLearner(TypedCourseLearner):
    def __init__(self, torch, framework, encoder, *, optimizer_config, run_context, limits, device):
        limits = validate_practice_limits(limits)
        # The registered constructor validates everything else against its own ceilings; hand it the
        # clipped limits, then install the practice limits and re-derive the identity that pins them.
        registered = {"max_updates": min(limits["max_updates"], REGISTERED_MAX_UPDATES),
                      "max_core_calls": limits["max_core_calls"],
                      "max_wall_seconds": min(limits["max_wall_seconds"], REGISTERED_MAX_WALL_SECONDS)}
        super().__init__(torch, framework, encoder, optimizer_config=optimizer_config, run_context=run_context,
                         limits=registered, device=device)
        self.limits = limits
        self.run_identity["limits"] = deepcopy(limits)
        self.run_identity["practice_learner_profile"] = practice_profile()
        self.run_identity_digest = digest(self.run_identity)

    @classmethod
    def restore_checkpoint(cls, torch, framework, *, path, expected_sha256, expected_run_identity_digest, device):
        restored = super().restore_checkpoint(torch, framework, path=path, expected_sha256=expected_sha256,
                                              expected_run_identity_digest=expected_run_identity_digest, device=device)
        require(canonical(restored.run_identity.get("practice_learner_profile")) == canonical(practice_profile())
                and canonical(restored.limits) == canonical(restored.run_identity["limits"]),
                "PRACTICE_CHECKPOINT_PROFILE")
        return restored
