"""The twelve-step mathematical acceptance ladder
(MATH_ACCEPTANCE_LAW_v0.1.md). The examiner never changes; the
teacher's eloquence grants nothing; every episode seals with
provenance, the checker-source digest, and a rollback pointer."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, List, Optional, Tuple

from . import ohm_profile
from .graph import missing_prerequisites, skill_info
from .mathir import canonical, parse_expr
from .packets import validate_packet
from .sdg import (DEV_SEED, PROTECTED_SEED, RETENTION_SEED,
                  attack_equation, generate, verify_identity)
from .student import SkillStore, Student, _digest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LANE = os.path.dirname(os.path.dirname(_HERE))

DEV_COUNT, HELD_OUT_COUNT, RETENTION_COUNT = 8, 6, 4


def checker_digest() -> str:
    """The sealed identity of the validity authority: the CCB-M1
    exact engine plus this board's student. A repair that touches
    these is visible in every episode."""
    sources = [
        os.path.join(_LANE, "CCB_M1_v0.1", "cas_math", "expr.py"),
        os.path.join(_LANE, "CCB_M1_v0.1", "cas_math", "checker.py"),
        os.path.join(_HERE, "student.py"),
        os.path.join(_HERE, "sdg.py"),
    ]
    blob = b"".join(open(p, "rb").read() for p in sources)
    return hashlib.sha256(blob).hexdigest()[:16]


def grade(exercise: Dict, result: Dict) -> Dict:
    """The examiner's grade: exact match against the SDG answer key
    (never the student's own path)."""
    if result.get("status") != "SOLVED":
        return {"passed": False, "result": result,
                "exercise_id": exercise["exercise_id"]}
    kind = exercise["kind"]
    if kind in ("expand", "rewrite"):
        expected = canonical(parse_expr(exercise["expected_equal_to"]))
        got = canonical(parse_expr(result["answer_expr"]))
        original = canonical(parse_expr(exercise["expr"]))
        passed = (got == expected and got == original
                  and result.get("canonical_equal_to_input") is True)
    elif kind == "derivative":
        from .advanced import derivative_canonical
        expected = canonical(parse_expr(exercise["expected_equal_to"]))
        got = canonical(parse_expr(result["answer_expr"]))
        independent = derivative_canonical(
            parse_expr(exercise["expr"]),
            exercise.get("variable", "x"))
        passed = got == expected == independent
    elif kind == "prove":
        from .advanced import examiner_verify_proof
        passed = (result.get("answer") == "proved"
                  and examiner_verify_proof(exercise["lhs_text"],
                                            exercise["rhs_text"],
                                            result.get("steps", [])))
    elif kind == "discovery_round":
        from .advanced import examiner_verify_discovery
        ok, detail = examiner_verify_discovery(
            result, result.get("library_used", []),
            int(exercise["min_proved"]),
            int(exercise["min_refuted"]))
        passed = ok and result.get("answer") == "discovery_verified"
        return {"passed": passed, "result": {
                    "status": result.get("status"),
                    "answer": result.get("answer"),
                    "examiner_detail": detail,
                    "proved": len(result.get("proved", [])),
                    "refuted": len(result.get("refuted", [])),
                    "conjectures": len(result.get("conjectures",
                                                  []))},
                "exercise_id": exercise["exercise_id"]}
    else:
        passed = result.get("answer") == exercise["expected"]
    return {"passed": passed, "result": result,
            "exercise_id": exercise["exercise_id"]}


def _run_set(student: Student, exercises: List[Dict]) -> Tuple[
        bool, List[Dict]]:
    grades = [grade(e, student.solve(e)) for e in exercises]
    return all(g["passed"] for g in grades), grades


def _first_failure(grades: List[Dict]) -> Dict:
    for g in grades:
        if not g["passed"]:
            return g
    return {}


def _candidate_record(packet: Dict) -> Dict:
    info = skill_info(packet["skill_id"])
    formal: Dict = {}
    if info["kind"] == "rewrite_rule":
        lhs, rhs = packet["formal_rule"].split("=")
        formal = {"lhs": lhs.strip(), "rhs": rhs.strip()}
    elif info["kind"] == "equation_solving":
        formal = {"method": list(packet["method"])}
    else:
        formal = {"definition_examples":
                  list(packet["worked_examples"])}
    return {"skill_id": packet["skill_id"], "kind": info["kind"],
            "level": info["level"], "formal": formal,
            "packet_digest": _digest(packet)}


def teach(packet: Dict, store_path: str) -> Dict:
    """One MathLessonPacket through all twelve steps. Returns the
    sealed episode. The ONLY write path into the skill store."""
    stages: List[Dict] = []

    def stage(name: str, passed: bool, detail: str) -> bool:
        stages.append({"stage": name, "passed": passed,
                       "detail": detail})
        return passed

    store = SkillStore.load(store_path)
    parent_json = store.to_json()

    def seal(verdict: str) -> Dict:
        episode = {
            "lesson_id": packet.get("lesson_id"),
            "skill_id": packet.get("skill_id"),
            "teacher_identity": packet.get("teacher_model"),
            "teacher_revision": packet.get("teacher_revision"),
            "teacher_role": packet.get("teacher_role", "lecturer"),
            "examiner_identity": "cas_math_exact_examiner",
            "checker_digest": checker_digest(),
            "provenance": packet.get("provenance"),
            "rollback_pointer": {
                "parent_revision": parent_json["revision"],
                "parent_digest": parent_json.get("store_digest")},
            "stages": stages,
            "verdict": verdict,
        }
        episode["episode_digest"] = _digest(episode)
        return episode

    skill_id = packet.get("skill_id")

    # 1. RPM prerequisite check
    if skill_id and skill_id in store.skills:
        stage("RPM_PREREQUISITES", False,
              f"{skill_id} is already promoted - no gain")
        return seal("QUARANTINED_ALREADY_PROMOTED")
    try:
        missing = missing_prerequisites(skill_id,
                                        store.promoted_ids())
    except Exception as exc:
        stage("RPM_PREREQUISITES", False, str(exc))
        return seal("REJECTED_MALFORMED_PACKET")
    if not stage("RPM_PREREQUISITES", not missing,
                 f"first missing prerequisite: {missing[0]}"
                 if missing else "prerequisite path clear"):
        return seal("REJECTED_PREREQUISITE_MISSING")

    # 2+3. packet schema + formal parse into CAS-Math IR
    defects = validate_packet(packet)
    if not stage("PACKET_VALID", not defects,
                 "; ".join(defects) or "typed packet complete; "
                 "formal channel parsed into CAS-Math IR"):
        return seal("REJECTED_MALFORMED_PACKET")
    info = skill_info(skill_id)

    # 4. every worked example checked EXACTLY (identities by
    # canonical equality; equation examples by SUBSTITUTION of the
    # given solution into the given equation)
    failures = []
    for example in packet["worked_examples"]:
        if info["kind"] == "equation_solving":
            from fractions import Fraction

            from .mathir import eval_at, parse_equation, parse_expr
            lhs, rhs = parse_equation(example["equation"])
            from .mathir import eval_at as _ev
            solution_value = _ev(
                parse_expr(str(example["solution"])), {})
            point = {example["variable"]: solution_value}
            try:
                if eval_at(lhs, point) != eval_at(rhs, point):
                    failures.append(
                        f"{example['equation']!r} is NOT satisfied "
                        f"by {example['variable']} = "
                        f"{example['solution']}")
            except Exception as exc:
                failures.append(f"{example!r}: {exc}")
        else:
            holds, witness = verify_identity(example)
            if not holds:
                failures.append(f"{example!r} is FALSE (witness: "
                                f"{witness})")
    if not stage("EXAMPLES_EXACT", not failures,
                 "; ".join(failures)
                 or f"{len(packet['worked_examples'])} examples "
                    f"verified by the exact engine"):
        return seal("REJECTED_EXAMPLE")

    # 5. the counterexample ATTACK
    if info["kind"] == "rewrite_rule":
        holds, witness = verify_identity(packet["formal_rule"])
        if not stage("RULE_SURVIVES_ATTACK", holds,
                     f"counterexample: {witness}" if not holds
                     else "canonical schema equality holds - the "
                          "rule is sound for this class"):
            return seal("REJECTED_RULE_COUNTEREXAMPLE")
    mistake_witness = attack_equation(packet["common_mistake"])
    if not stage("MISTAKE_IS_A_MISTAKE",
                 mistake_witness is not None
                 and "error" not in mistake_witness,
                 f"refutation witness: {mistake_witness}"
                 if mistake_witness else
                 "the declared 'common mistake' is actually TRUE - "
                 "teaching it as an error would corrupt the "
                 "student"):
        return seal("REJECTED_MISTAKE_NOT_A_MISTAKE")

    candidate = _candidate_record(packet)
    student = Student(store, candidate=candidate)

    # CAS-Ohm learning profile: capability BEFORE (compute-only)
    held_out = generate(skill_id, info["kind"], PROTECTED_SEED,
                        HELD_OUT_COUNT)
    profile = ohm_profile.before(Student(store), held_out)

    # 6+7. SDG development variations, solved with the candidate
    dev = generate(skill_id, info["kind"], DEV_SEED, DEV_COUNT)
    ok, grades = _run_set(student, dev)
    if not stage("DEV_EXERCISES", ok,
                 f"first failure: {_first_failure(grades)}"
                 if not ok else f"{len(dev)} independent variations "
                                f"solved"):
        return seal("REJECTED_DEV_EXERCISES")

    # 8. PROTECTED held-out (examiner's channel; bar is 100%)
    ok, grades = _run_set(student, held_out)
    if not stage("PROTECTED_HELD_OUT", ok,
                 f"first failure: {_first_failure(grades)}"
                 if not ok else f"{len(held_out)} protected "
                                f"exercises solved (100% exact)"):
        return seal("REJECTED_HELD_OUT")

    # 9. regression over every mastered skill's guards
    failures = []
    for prior_id in store.promoted_ids():
        guards = store.get(prior_id).get("regression_guard", [])
        ok, grades = _run_set(student, guards)
        if not ok:
            failures.append(f"regression on {prior_id}: "
                            f"{_first_failure(grades)}")
    if not stage("PRIOR_SKILLS_REGRESSION", not failures,
                 "; ".join(failures)
                 or "every mastered skill still solves its guards"):
        return seal("REJECTED_REGRESSION")

    # 11(commit). the coordinator writes, ATOMICALLY via full-file
    # save; parent JSON retained above as the rollback body
    candidate["regression_guard"] = held_out[:3]
    store._commit_skill(
        candidate,
        provenance=f"lesson:{packet['lesson_id']}"
                   f"|teacher:{packet['teacher_model']}")
    store.save(store_path)
    stage("PROMOTED_PROVISIONALLY", True,
          f"committed at revision {store.revision}")

    # 10. delayed retention: FRESH reload from disk, unseen set
    fresh = Student(SkillStore.load(store_path))
    retention = generate(skill_id, info["kind"], RETENTION_SEED,
                         RETENTION_COUNT)
    ok, grades = _run_set(fresh, retention)
    if not ok:
        # rollback: restore the parent store file
        with open(store_path, "w", encoding="utf-8") as fh:
            json.dump(parent_json, fh, indent=1, sort_keys=True)
        stage("DELAYED_RETENTION", False,
              f"first failure: {_first_failure(grades)}; store "
              f"ROLLED BACK to revision {parent_json['revision']}")
        return seal("RETENTION_FAILED_ROLLED_BACK")
    stage("DELAYED_RETENTION", True,
          f"{len(retention)} unseen exercises after a fresh reload")

    # CAS-Ohm learning profile: capability AFTER
    episode_profile = ohm_profile.after(profile, fresh, held_out)
    stages.append({"stage": "CAS_OHM_PROFILE", "passed": True,
                   "detail": json.dumps(episode_profile,
                                        sort_keys=True)})
    return seal("PROMOTED")
