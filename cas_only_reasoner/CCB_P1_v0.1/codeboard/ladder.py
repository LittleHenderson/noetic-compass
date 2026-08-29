"""CCB-P1: the programming acceptance law.

A procedure becomes durable only when: the spec is typed AND the
program compiles AND public examples pass AND negative and boundary
tests pass AND protected held-out passes AND property checks pass
AND prior skills do not regress AND forbidden effects stay blocked
AND deterministic replay passes AND delayed retention passes AND the
teacher did not alter the examiner. A compiling bug is still a bug
wearing a clean shirt."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Callable, Dict, List, Optional, Tuple

from . import repair as repair_mod
from . import sandbox
from .packets import validate_packet
from .spec import (DEV_SEED, PROTECTED_SEED, RETENTION_SEED, SKILLS,
                   SPECS, TRACE_PROGRAMS, TRANSFER_SPECS, REFERENCES,
                   boundary_inputs, exam_inputs,
                   missing_prerequisites, property_checks,
                   validate_spec)
from .student import CodeStudent, ProcedureStore, _digest

_HERE = os.path.dirname(os.path.abspath(__file__))


def examiner_digest() -> str:
    """The sealed identity of the examiner: sandbox, tracer, repair,
    spec registry, this ladder. Any change is visible in every
    episode - the teacher cannot alter the examiner unseen."""
    sources = [os.path.join(_HERE, name)
               for name in ("sandbox.py", "tracer.py", "repair.py",
                            "spec.py", "ladder.py")]
    blob = b"".join(open(p, "rb").read() for p in sources)
    return hashlib.sha256(blob).hexdigest()[:16]


# ------------------------------------------------- the code battery
def run_code(code: str, fname: str, args: List) -> Tuple[bool, object]:
    outcome = sandbox.run(code, fname, args)
    return outcome["status"] == "OK", outcome.get("value")


def algorithm_battery(skill_id: str, code: str, spec: Dict,
                      seeds: Tuple[int, ...] = (DEV_SEED,
                                                PROTECTED_SEED),
                      per_seed: int = 6) -> Tuple[bool, Dict]:
    """The FULL battery for one implementation against one spec:
    public + boundary + negative (wrong arity raises) + seeded
    channels (answers from the examiner's REFERENCE) + properties."""
    fname = spec["function_name"]
    reference = REFERENCES[skill_id]

    for example in spec["public_examples"]:
        ok, value = run_code(code, fname, example["args"])
        if not ok or value != example["expected"]:
            return False, {"stage": "public",
                           "args": example["args"],
                           "expected": example["expected"],
                           "got": value if ok else "ERROR"}
    for args in boundary_inputs(skill_id):
        ok, value = run_code(code, fname, args)
        expected = reference(*args)
        if not ok or value != expected:
            return False, {"stage": "boundary", "args": args,
                           "expected": expected,
                           "got": value if ok else "ERROR"}
    wrong_arity = sandbox.run(code, fname, [])
    if wrong_arity["status"] == "OK" and spec["params"]:
        return False, {"stage": "negative",
                       "detail": "a wrong-arity call must fail, "
                                 "not return a value"}
    for seed in seeds:
        for args in exam_inputs(skill_id, seed, per_seed):
            ok, value = run_code(code, fname, args)
            expected = reference(*args)
            if not ok or value != expected:
                return False, {"stage": f"seeded:{seed}",
                               "args": args, "expected": expected,
                               "got": value if ok else "ERROR"}
    failures = property_checks(
        skill_id, lambda args: run_code(code, fname, args))
    if failures:
        return False, {"stage": "property", "detail": failures[0]}
    return True, {"stage": "all", "detail": "battery green"}


def make_mutants(skill_id: str, code: str,
                 count: int = 4) -> List[str]:
    """Seeded single-edit mutants that BREAK the battery - the
    examiner's defect factory for testing/repair exams."""
    spec = SPECS[skill_id]
    mutants = []
    for candidate in repair_mod.candidate_patches(code):
        ok, _ = algorithm_battery(skill_id, candidate, spec,
                                  seeds=(DEV_SEED,), per_seed=3)
        if not ok:
            mutants.append(candidate)
        if len(mutants) >= count:
            break
    return mutants


# ------------------------------------------------------ exam per kind
def _exam_tracing(student: CodeStudent, seed: int) -> Tuple[bool, Dict]:
    index_offset = seed % 2
    for program in TRACE_PROGRAMS:
        inputs = program["inputs"][index_offset:] \
            + program["inputs"][:index_offset]
        for args in inputs:
            truth = sandbox.run(program["code"], program["fname"],
                                args)
            result = student.trace_predict(program["code"],
                                           program["fname"], args)
            if result.get("status") != "SOLVED" \
                    or result.get("prediction") != truth.get("value"):
                return False, {"program": program["fname"],
                               "args": args, "result": result,
                               "truth": truth.get("value")}
    return True, {"detail": "all traces predicted exactly"}


def _exam_algorithm(student: CodeStudent, skill_id: str,
                    seed: int) -> Tuple[bool, Dict]:
    spec = SPECS[skill_id]
    implementation = student.implement(skill_id, spec)
    if implementation.get("status") != "SOLVED":
        return False, {"stage": "implement",
                       "result": implementation}
    ok, detail = algorithm_battery(skill_id,
                                   implementation["code"], spec,
                                   seeds=(seed,), per_seed=6)
    if not ok:
        return False, detail
    # STRUCTURAL TRANSFER: the renamed specification
    transfer_spec = TRANSFER_SPECS[skill_id]
    adapted = student.implement(skill_id, transfer_spec)
    if adapted.get("status") != "SOLVED":
        return False, {"stage": "transfer_implement",
                       "result": adapted}
    ok, detail = algorithm_battery(skill_id, adapted["code"],
                                   transfer_spec, seeds=(seed,),
                                   per_seed=4)
    if not ok:
        return False, {"stage": "transfer", "detail": detail}
    return True, {"detail": "battery + structural transfer green"}


def _exam_testing(student: CodeStudent,
                  seed: int) -> Tuple[bool, Dict]:
    for skill_id in ("sum_list", "reverse_string"):
        spec = SPECS[skill_id]
        reference_record = student.store.get(skill_id)
        if reference_record is None:
            return False, {"stage": "prereq",
                           "detail": f"{skill_id} not promoted"}
        code = reference_record["formal"]["code"]
        fname = reference_record["formal"]["function_name"]
        generated = student.generate_tests(skill_id, spec)
        if generated.get("status") != "SOLVED":
            return False, {"stage": "generate", "result": generated}
        suite = generated["suite"]
        reference = REFERENCES[skill_id]
        for test in suite:
            if test.get("expect_error"):
                outcome = sandbox.run(code, fname, test["args"])
                if outcome["status"] == "OK" and spec["params"]:
                    return False, {"stage": "negative_test",
                                   "detail": "expected an error"}
                continue
            ok, value = run_code(code, fname, test["args"])
            if not ok or value != reference(*test["args"]):
                return False, {"stage": "suite_vs_reference",
                               "args": test["args"]}
        # the suite must KILL mutants that public examples alone miss
        mutants = make_mutants(skill_id, code, count=3)
        for mutant in mutants:
            public_pass = all(
                run_code(mutant, fname, ex["args"])
                == (True, ex["expected"])
                for ex in spec["public_examples"])
            killed = any(
                (run_code(mutant, fname, t["args"])
                 != (True, reference(*t["args"])))
                for t in suite if not t.get("expect_error"))
            if public_pass and not killed:
                return False, {"stage": "mutant_survived",
                               "skill": skill_id,
                               "detail": "one passing example does "
                                         "not establish correctness "
                                         "- and this suite proved "
                                         "no stronger"}
    return True, {"detail": "suites verify references and kill "
                            "mutants"}


def _exam_repair(student: CodeStudent,
                 seed: int) -> Tuple[bool, Dict]:
    for skill_id in ("sum_list", "count_matching"):
        record = student.store.get(skill_id)
        if record is None:
            return False, {"stage": "prereq",
                           "detail": f"{skill_id} not promoted"}
        code = record["formal"]["code"]
        spec = SPECS[skill_id]
        mutants = make_mutants(skill_id, code, count=2)
        if not mutants:
            return False, {"stage": "mutant_factory",
                           "detail": "no mutants produced"}
        for mutant in mutants:
            failing_args = None
            reference = REFERENCES[skill_id]
            fname = spec["function_name"]
            for args in (boundary_inputs(skill_id)
                         + exam_inputs(skill_id, seed, 6)):
                ok, value = run_code(mutant, fname, args)
                if not ok or value != reference(*args):
                    failing_args = args
                    break
            if failing_args is None:
                continue

            def battery(candidate: str,
                        _sid=skill_id, _spec=spec):
                return algorithm_battery(_sid, candidate, _spec,
                                         seeds=(seed,), per_seed=4)

            result = student.diagnose_and_repair(
                skill_id, mutant, failing_args, battery)
            if result.get("status") != "SOLVED":
                return False, {"stage": "repair", "skill": skill_id,
                               "result": {k: result.get(k)
                                          for k in ("status",
                                                    "detail",
                                                    "diagnosis")}}
            ok, detail = algorithm_battery(skill_id,
                                           result["patched_code"],
                                           spec)
            if not ok:
                return False, {"stage": "examiner_recheck",
                               "detail": detail}
            if len(result["changed_lines"]) > 1:
                return False, {"stage": "minimality",
                               "detail": f"patch touched "
                                         f"{result['changed_lines']}"}
            if result.get("diagnosis") is None:
                return False, {"stage": "diagnosis",
                               "detail": "no first-bad-state was "
                                         "produced"}
    return True, {"detail": "faults localized, minimal patches, "
                            "references restored"}


def examine(student: CodeStudent, skill_id: str,
            seed: int) -> Tuple[bool, Dict]:
    kind = SKILLS[skill_id]["kind"]
    if kind == "tracing":
        return _exam_tracing(student, seed)
    if kind == "algorithm":
        return _exam_algorithm(student, skill_id, seed)
    if kind == "testing":
        return _exam_testing(student, seed)
    if kind == "repair":
        return _exam_repair(student, seed)
    return False, {"detail": f"unknown kind {kind}"}


# --------------------------------------------------------- the ladder
def _candidate_record(packet: Dict) -> Dict:
    kind = SKILLS[packet["skill_id"]]["kind"]
    if kind == "algorithm":
        spec = SPECS[packet["skill_id"]]
        formal = {"code": packet["implementation"],
                  "function_name": spec["function_name"],
                  "params": [p["name"] for p in spec["params"]]}
    else:
        formal = {"strategy": packet.get("strategy", "")}
    return {"skill_id": packet["skill_id"], "kind": kind,
            "level": SKILLS[packet["skill_id"]]["level"],
            "formal": formal, "packet_digest": _digest(packet)}


def teach(packet: Dict, store_path: str) -> Dict:
    stages: List[Dict] = []

    def stage(name: str, passed: bool, detail: str) -> bool:
        stages.append({"stage": name, "passed": passed,
                       "detail": str(detail)[:400]})
        return passed

    store = ProcedureStore.load(store_path)
    parent_json = store.to_json()

    def seal(verdict: str) -> Dict:
        conv_flow = {
            "tp_spec_understanding": "active" if len(stages) > 1
            else "cutoff",
            "tp_candidate_generation": "active" if any(
                s["stage"] == "CANDIDATES_COMPILE"
                for s in stages) else "absent",
            "tp_compile": "active" if any(
                s["stage"] == "CANDIDATES_COMPILE" and s["passed"]
                for s in stages) else "cutoff",
            "tp_test_execution": "active" if any(
                s["stage"].startswith("EXAM") for s in stages)
            else "absent",
            "tp_regression": "active" if any(
                s["stage"] == "PRIOR_SKILLS_REGRESSION"
                for s in stages) else "absent",
            "authority_note": "compute-only: no truth, validity, "
                              "meaning, commitment, or permission "
                              "decision may read this record"}
        episode = {
            "lesson_id": packet.get("lesson_id"),
            "skill_id": packet.get("skill_id"),
            "teacher_identity": packet.get("teacher_model"),
            "teacher_revision": packet.get("teacher_revision"),
            "examiner_identity": "ccb_p1_compiler_and_tests",
            "examiner_digest": examiner_digest(),
            "provenance": packet.get("provenance"),
            "rollback_pointer": {
                "parent_revision": parent_json["revision"],
                "parent_digest": parent_json.get("store_digest")},
            "cas_ohm_flow": conv_flow,
            "stages": stages,
            "verdict": verdict,
        }
        episode["episode_digest"] = _digest(episode)
        return episode

    skill_id = packet.get("skill_id")
    if skill_id and skill_id in store.procedures:
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

    defects = validate_packet(packet)
    if not stage("PACKET_VALID", not defects,
                 "; ".join(defects) or "typed packet complete; no "
                 "authority fields; forbidden effects blocked "
                 "statically"):
        return seal("REJECTED_MALFORMED_PACKET")

    kind = SKILLS[skill_id]["kind"]
    if kind == "algorithm":
        spec = SPECS[skill_id]
        spec_defects = validate_spec(spec)
        if not stage("SPEC_TYPED", not spec_defects,
                     "; ".join(spec_defects)
                     or f"typed contract {spec['spec_id']}"):
            return seal("REJECTED_MALFORMED_PACKET")
        candidates = [packet["implementation"]]
        if packet.get("alternative"):
            candidates.append(packet["alternative"])
        compile_failures = []
        for index, candidate in enumerate(candidates):
            gate = sandbox.static_gate(candidate)
            if gate:
                compile_failures.append(f"candidate {index}: "
                                        f"{gate[0]}")
        if not stage("CANDIDATES_COMPILE", not compile_failures,
                     "; ".join(compile_failures)
                     or f"{len(candidates)} candidate(s) parse; "
                       f"forbidden effects blocked before "
                       f"execution"):
            return seal("REJECTED_COMPILE")
        # the teacher's declared bug must BE a bug
        bug_ok, bug_detail = algorithm_battery(
            skill_id, packet["common_bug"], spec,
            seeds=(DEV_SEED,), per_seed=3)
        if not stage("BUG_IS_A_BUG", not bug_ok,
                     "the declared common_bug PASSES the battery - "
                     "teaching it as a defect would corrupt the "
                     "student" if bug_ok
                     else f"bug fails at {bug_detail['stage']} - "
                          f"a real defect exemplar"):
            return seal("REJECTED_BUG_NOT_A_BUG")
        surviving = None
        candidate_outcomes = []
        for index, candidate in enumerate(candidates):
            ok, detail = algorithm_battery(skill_id, candidate,
                                           spec)
            candidate_outcomes.append(
                {"candidate": index, "passed": ok,
                 "detail": str(detail)[:150]})
            if ok and surviving is None:
                surviving = candidate
        if not stage("CANDIDATE_BATTERY",
                     surviving is not None,
                     json.dumps(candidate_outcomes)):
            return seal("REJECTED_TESTS")
        packet = dict(packet)
        packet["implementation"] = surviving
    else:
        stage("SPEC_TYPED", True, f"{kind} lesson - the exam "
                                  f"corpus is the examiner's")

    candidate = _candidate_record(packet)
    student = CodeStudent(store, candidate=candidate)

    ok, detail = examine(student, skill_id, DEV_SEED)
    if not stage("EXAM_DEV", ok, json.dumps(detail)[:400]):
        return seal("REJECTED_DEV_EXAM")
    ok, detail = examine(student, skill_id, PROTECTED_SEED)
    if not stage("EXAM_PROTECTED", ok, json.dumps(detail)[:400]):
        return seal("REJECTED_HELD_OUT")

    failures = []
    for prior_id in store.promoted_ids():
        prior_student = CodeStudent(store, candidate=candidate)
        ok, detail = examine(prior_student, prior_id, DEV_SEED)
        if not ok:
            failures.append(f"{prior_id}: "
                            f"{json.dumps(detail)[:120]}")
    if not stage("PRIOR_SKILLS_REGRESSION", not failures,
                 "; ".join(failures)
                 or "every promoted skill still passes"):
        return seal("REJECTED_REGRESSION")

    # deterministic replay: the same exam twice, identical outcome
    first = examine(CodeStudent(store, candidate=candidate),
                    skill_id, PROTECTED_SEED)
    second = examine(CodeStudent(store, candidate=candidate),
                     skill_id, PROTECTED_SEED)
    if not stage("DETERMINISTIC_REPLAY",
                 _digest(first) == _digest(second),
                 "identical exam -> identical outcome digest"
                 if _digest(first) == _digest(second)
                 else "REPLAY DIVERGED"):
        return seal("REJECTED_NONDETERMINISM")

    store._commit(candidate,
                  provenance=f"lesson:{packet['lesson_id']}"
                             f"|teacher:{packet['teacher_model']}")
    store.save(store_path)
    stage("PROMOTED_PROVISIONALLY", True,
          f"committed at revision {store.revision}")

    fresh = CodeStudent(ProcedureStore.load(store_path))
    ok, detail = examine(fresh, skill_id, RETENTION_SEED)
    if not ok:
        with open(store_path, "w", encoding="utf-8") as fh:
            json.dump(parent_json, fh, indent=1, sort_keys=True)
        stage("DELAYED_RETENTION", False,
              f"{json.dumps(detail)[:200]}; store ROLLED BACK")
        return seal("RETENTION_FAILED_ROLLED_BACK")
    stage("DELAYED_RETENTION", True,
          "fresh reload passes the retention-seed exam")
    return seal("PROMOTED")
