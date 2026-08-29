"""CCB-A1: the Cognitive Apprenticeship and Teaching Board v0.1.

The domain-general teaching pipeline. The teacher may propose
knowledge and skill; the CNCM decides what becomes part of itself.

This board:
  - seals every lesson as a TeachingEpisode with identity, evidence,
    pre/post capability, provenance, and a rollback pointer;
  - enforces the NEVER-AUTONOMOUS list (constitutional targets accept
    suggestions, never promotion);
  - enforces the faculty-committee rule for high-impact lessons (the
    proposer may not be the only examiner);
  - routes each domain to its own frozen verifier channel (grammar ->
    the CCB-L1 ladder; math -> the CCB-M1 exact checker; strategies
    -> the RLP acceptance law; knowledge -> the source-verification
    protocol in knowledge.py);
  - computes the teaching metrics.
"""

from __future__ import annotations

import hashlib
import json
from typing import Callable, Dict, List, Optional

# Structures that accept suggestions but NEVER autonomous promotion.
NEVER_AUTONOMOUS = (
    "authority_contract", "sole_writer_rule", "proof_checker",
    "trace_verifier", "protected_benchmarks", "constitutional_values",
    "deployment_permissions", "rollback_machinery",
    "definition_of_improvement",
)

# Domains whose lessons demand a second, distinct examiner identity.
HIGH_IMPACT_DOMAINS = ("world_knowledge", "research_method",
                       "board_design", "self_improvement",
                       "behavioral_norms")

TEACHER_ROLES = ("lecturer", "demonstrator", "socratic_tutor",
                 "curriculum_designer", "adversary", "critic",
                 "research_mentor")


class TeachingError(Exception):
    pass


class NeverAutonomous(TeachingError):
    """The lesson targets a constitutionally protected structure."""


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class ApprenticeshipBoard:
    def __init__(self) -> None:
        self.episodes: List[Dict] = []

    # ------------------------------------------------------------------
    def teach(self, lesson: Dict,
              verifier_channel: Callable[[Dict], Dict],
              pre_capability: Optional[float] = None,
              post_capability: Optional[float] = None) -> Dict:
        """One lesson through the board. verifier_channel is the
        domain's FROZEN examiner (never authored by the proposing
        teacher); it returns {"verdict": ..., "evidence": ...}."""
        domain = lesson.get("domain", "unknown")
        target = lesson.get("target", "")

        # THE NEVER-AUTONOMOUS GUARD - before anything else runs
        if target in NEVER_AUTONOMOUS:
            episode = self._seal(lesson, {
                "verdict": "REJECTED_NEVER_AUTONOMOUS",
                "evidence": f"'{target}' accepts suggestions, never "
                            f"promotion: a model can explain why a "
                            f"constitution might change; it cannot "
                            f"vote itself the power to change it"},
                pre_capability, post_capability)
            raise NeverAutonomous(episode["outcome"]["evidence"])

        # THE FACULTY-COMMITTEE RULE for high-impact domains
        if domain in HIGH_IMPACT_DOMAINS:
            proposer = lesson.get("teacher_model")
            examiner = lesson.get("examiner_identity")
            if not examiner or examiner == proposer:
                return self._seal(lesson, {
                    "verdict": "REJECTED_SINGLE_EXAMINER",
                    "evidence": "high-impact lessons require a second "
                                "distinct examiner identity - the "
                                "proposer may not be the only examiner "
                                "(the student must never confuse the "
                                "teacher's consistency with "
                                "correctness)"},
                    pre_capability, post_capability)

        # THE FACULTY-COMMITTEE RECORD: when a lesson carries a
        # committee, the board VALIDATES it - at least two DISTINCT
        # model identities, an explicit vote from every member, and
        # any reject vote blocks promotion typed. Committee approval
        # grants NOTHING by itself: the domain's frozen examiner still
        # runs and still decides.
        committee = lesson.get("committee")
        if committee is not None:
            identities = {member.get("model") for member in committee}
            if len(committee) < 2 or len(identities) < 2:
                return self._seal(lesson, {
                    "verdict": "REJECTED_COMMITTEE_COMPOSITION",
                    "evidence": "a faculty committee needs at least "
                                "two DISTINCT model identities"},
                    pre_capability, post_capability)
            unvoted = [member for member in committee
                       if member.get("vote") not in ("approve",
                                                     "reject")]
            if unvoted:
                return self._seal(lesson, {
                    "verdict": "REJECTED_COMMITTEE_COMPOSITION",
                    "evidence": "every committee member must record "
                                "an explicit approve/reject vote"},
                    pre_capability, post_capability)
            rejects = [member for member in committee
                       if member["vote"] == "reject"]
            if rejects:
                return self._seal(lesson, {
                    "verdict": "REJECTED_BY_COMMITTEE",
                    "evidence": [{"model": member.get("model"),
                                  "reasons": member.get("reasons")}
                                 for member in rejects]},
                    pre_capability, post_capability)

        outcome = verifier_channel(lesson)
        return self._seal(lesson, outcome, pre_capability,
                          post_capability)

    # ------------------------------------------------------------------
    def _seal(self, lesson: Dict, outcome: Dict,
              pre_capability, post_capability) -> Dict:
        episode = {
            "lesson_id": lesson.get("lesson_id"),
            "domain": lesson.get("domain"),
            "target": lesson.get("target"),
            "teacher_identity": lesson.get("teacher_model"),
            "teacher_revision": lesson.get("teacher_revision"),
            "teacher_role": lesson.get("teacher_role"),
            "examiner_identity": lesson.get("examiner_identity"),
            "outcome": outcome,
            "pre_learning_capability": pre_capability,
            "post_learning_capability": post_capability,
            "provenance": lesson.get("provenance"),
            "rollback_pointer": lesson.get("rollback_pointer"),
        }
        episode["episode_digest"] = _digest(episode)
        self.episodes.append(episode)
        return episode

    # ------------------------------------------------------------------
    def metrics(self, teacher_assisted: int, total_tasks: int,
                held_out_successes: int, held_out_total: int,
                teacher_compute_cost: float = 1.0,
                delayed_capability: Optional[float] = None) -> Dict:
        """The teaching metrics over this board's sealed episodes."""
        gains = [e["post_learning_capability"]
                 - e["pre_learning_capability"]
                 for e in self.episodes
                 if e["pre_learning_capability"] is not None
                 and e["post_learning_capability"] is not None]
        promoted = [e for e in self.episodes
                    if str(e["outcome"].get("verdict", ""))
                    .startswith("PROMOTED")]
        rejected = [e for e in self.episodes
                    if str(e["outcome"].get("verdict", ""))
                    .startswith("REJECTED")]
        learning_gain = round(sum(gains), 4) if gains else None
        result = {
            "episodes": len(self.episodes),
            "promoted": len(promoted),
            "rejected": len(rejected),
            "false_lesson_rate": round(
                len(rejected) / len(self.episodes), 4)
            if self.episodes else None,
            "learning_gain": learning_gain,
            "transfer_rate": round(held_out_successes / held_out_total,
                                   4) if held_out_total else None,
            "teaching_efficiency": round(
                learning_gain / teacher_compute_cost, 4)
            if learning_gain is not None and teacher_compute_cost
            else None,
            "teacher_dependence": round(
                teacher_assisted / total_tasks, 4)
            if total_tasks else None,
        }
        if delayed_capability is not None and gains:
            immediate = self.episodes[-1]["post_learning_capability"]
            result["retention"] = round(
                delayed_capability / immediate, 4) if immediate else None
        return result
