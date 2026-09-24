"""AWS T4 checks for the larger-question path (v0.1). Forward passes only. No training. GPU only.

PLAIN SUMMARY. Four checks. Each emits PASS or FAIL from measured values; the program then emits one verdict.

  a  OLD_PACKET_PRESERVATION. The six Helm 2.0 checkpoints (seeds 20260917-19, initial and final) are loaded into a
     switch-OFF container exactly as `preservation_digest.py` loads them. On all 564 course packets, the ORIGINAL
     steps (frozen `slots`, `GraphForward`, decoder) and the new path must give identical slot plans, identical
     float32 logit bits, and identical scores, decisions and answers. Every packet must take the ORIGINAL route.
  b  FIXTURES_THROUGH_LEARNER. Every public 5- and 6-node fixture goes read -> forward -> decode -> checker v2
     grade with no error, on five containers: the three trained Helm 2.0 final checkpoints (switch OFF), a fresh
     switch-OFF container and a fresh switch-ON container. Only "graded, no error" and the checker's receipt digest
     are written. The correct/incorrect flag is NOT written: the fixtures are plumbing fixtures, not an evaluation
     set, and a public fixture shape might coincide with a sealed TEST shape.
  c  SEVEN_NODE_REFUSAL. Every refusal fixture (a 7-node world; a node of degree 5) raises `LargerPathRefusal`
     with its named code, and `GraphForward` is never called.
  d  FULL_LEARNER_SUBCLASS. Two fresh learners built from the same seed, `PointerCourseLearner` and
     `LargerQuestionPointerLearner`, give byte-identical predictions on all 564 course packets. The subclass answers
     every fixture, refuses the refusal fixtures without moving a counter, and refuses to train. The original
     learner refuses the 6-node correspondence fixture (`TYPED_PERMUTATION_BOUND`), which is why the path exists.

    CAS_META2_RUN_TEACHING_CYCLE=1 python -B t4_larger_question_checks.py --out RESULT.json [--checks a,b,c,d]

The environment variable is the learner's own execution guard (`teaching_cycle/gpu_adapter.py:37-39`); check d
needs it and a Linux worker. It is never set by this script.

Exit codes: 0 = all four checks PASS; 1 = a check FAILED or was not run; 2 = GPU_REQUIRED (no torch or no CUDA);
3 = WALL_LIMIT_REACHED; 4 = SETUP_REFUSED (source drift, a checkpoint or fixture identity mismatch).
"""
import argparse
from copy import deepcopy
import hashlib
import io
import json
import os
import pathlib
import platform
import sys
import time
import traceback

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
HERE = pathlib.Path(__file__).resolve().parent
RESEARCH = HERE.parent
PACKAGE = HERE.parents[2]
SCHEMA = "claude.helm-larger-question-t4-checks/0.1"
SEEDS = (20260917, 20260918, 20260919)
FRESH_SEED = 20260917
WALL_SECONDS = 3600
EXPECTED_COURSE_PACKETS = 564
# (bytes, sha256) of the Helm 2.0 checkpoints, read from the committed git blobs on 2026-09-23. They equal the
# `artifact_manifest.json` rows of each receipt (checked for seed 20260917).
CHECKPOINTS = {
    (20260917, "initial"): (2235079, "59dd46877bd7bf97dbb4059975051cc6102b374d5c387d3a183884048b71b004"),
    (20260917, "final"): (3670007, "c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb"),
    (20260918, "initial"): (2235079, "d3c6292f2c0d09e29952bfe353d47fff058741d42c0a8e8dbe7a80eaad8fd645"),
    (20260918, "final"): (3670007, "a6e72caac1fccbd994433a46684846f5a3de48683dcc6b5def5946b85ef20658"),
    (20260919, "initial"): (2235079, "93b84558c0123673eabcc462f68afe8ecb1537b598e297ee16f7a7458787ee9f"),
    (20260919, "final"): (3670007, "c83e0123643a2433e1650bd4898dc28865204fd3d03fbedd22910632caf7dec8"),
}
BOUNDARY = ("Plumbing checks only: forward passes under torch.no_grad(); no optimizer step and no checkpoint "
            "written. Nothing here measures Helm's accuracy. The fixtures are public and not an evaluation set.")


class SetupRefused(Exception):
    pass


class WallLimit(Exception):
    pass


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _lf_sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _error(error):
    return {"type": type(error).__name__, "message": str(error)[:400]}


class Context:
    """Everything the checks share. Built only after the CUDA check has passed."""

    def __init__(self, torch, device, started):
        self.torch, self.device, self.started = torch, device, started
        sys.dont_write_bytecode = True
        for path in (PACKAGE, RESEARCH):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        from cas_meta2.typed_teaching import (answers, pointer_contract, pointer_inputs, pointer_learner, slots,
                                              source, worker_contract)
        from cncm.typed_matched_worker import _framework
        from eval_paths import larger_question_scope
        try:
            # Checked BEFORE the learner half is imported (that import re-checks the same pins).
            self.source_pins = larger_question_scope.verify_source_pins()
        except larger_question_scope.LargerPathRefusal as error:
            raise SetupRefused(str(error)) from error
        from eval_paths import larger_question_fixtures, larger_question_learner
        self.answers, self.contract, self.pointer_inputs = answers, pointer_contract, pointer_inputs
        self.PL, self.slots, self.source, self.worker_contract = pointer_learner, slots, source, worker_contract
        self.framework = _framework
        self.FX, self.LL, self.scope = larger_question_fixtures, larger_question_learner, larger_question_scope
        frozen, tokenizer = pointer_contract.load_material(PACKAGE)[:2]
        self.course_digest, self.tokenizer = frozen["course_digest"], tokenizer
        self.packets = dict(pointer_contract.public_packets(frozen))
        self.ids = sorted(self.packets)
        if len(self.ids) != EXPECTED_COURSE_PACKETS:
            raise SetupRefused("COURSE_PACKET_COUNT:%d" % len(self.ids))
        self.tagger = pointer_learner.role_tagger(str(PACKAGE))
        try:
            self.document, self.fixtures = larger_question_fixtures.load()
        except ValueError as error:
            raise SetupRefused("FIXTURE_IDENTITY:" + str(error)) from error
        rows = {row["fixture_id"]: row for row in self.document["fixtures"]}
        self.rows = rows
        self.larger_ids = sorted(key for key, row in rows.items() if "expected_refusal" not in row)
        self.refused_ids = sorted(key for key, row in rows.items() if "expected_refusal" in row)
        del frozen

    def wall(self):
        if time.monotonic() - self.started > WALL_SECONDS:
            raise WallLimit()

    def container(self, seed, phase, *, switch):
        """A pointer container. `phase` None = fresh; otherwise a pinned Helm 2.0 checkpoint, loaded strictly."""
        torch = self.torch
        model = self.PL._build_container(torch, self.framework(torch, self.device, seed), self.device,
                                         analogy_focus_comparison=switch)
        checkpoint = None
        if phase is not None:
            path = PACKAGE / ("records/typed_pointer_001/receipt_%d/checkpoints/%s.pt" % (seed, phase))
            raw = path.read_bytes()
            size, digest = CHECKPOINTS[(seed, phase)]
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
                raise SetupRefused("CHECKPOINT_PIN:%d:%s" % (seed, phase))
            state = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)["model_state"]
            model.load_state_dict(state, strict=True)
            checkpoint = {"seed": seed, "phase": phase, "sha256": digest}
        model.eval()
        if model.analogy_focus_comparison is not switch:
            raise SetupRefused("SWITCH_STATE")
        return model, checkpoint

    def original_steps(self, model, packet):
        """The ORIGINAL scoring steps of `PointerCourseLearner._graph` with the frozen `slots`, no route."""
        torch, PL, slots = self.torch, self.PL, self.slots
        with torch.no_grad():
            plan = slots.compile_slots(packet)
            reading = self.pointer_inputs.read_packet(packet)
            reading["_device"] = self.device
            forward = PL.GraphForward(torch, model, reading, self.device)
            indicators = (self.tagger.indicators(packet) if reading["query"]["kind_name"] == "role_set"
                          else [0] * PL.CLAUSE_COUNT)
            rows = forward.head_logits(plan, indicators)
            scores = PL._logit_rows(torch, plan, PL._scalar_scores(torch, rows))
            decisions = slots.score_decisions(packet, scores)
            answer = slots.assemble_answer(packet, decisions)
        return {"plan": plan, "rows": rows, "scores": scores, "decisions": decisions, "answer": answer}


# ------------------------------------------------------------------------------------------------ check a
def check_a(ctx):
    torch, LL = ctx.torch, ctx.LL
    models, failed = [], False
    for seed in SEEDS:
        for phase in ("initial", "final"):
            model, checkpoint = ctx.container(seed, phase, switch=False)
            per_record, mismatches = {}, []
            for rid in ctx.ids:
                ctx.wall()
                packet = ctx.packets[rid]
                old = ctx.original_steps(model, packet)
                new = LL.predict_packet(torch, model, packet, ctx.device, tagger=ctx.tagger)
                bits = LL.logit_bits_digest(torch, old["rows"])
                same = (new["route"] == ctx.scope.ORIGINAL
                        and _canonical(old["plan"]) == _canonical(new["plan"])
                        and bits == LL.logit_bits_digest(torch, new["rows"])
                        and _canonical(old["scores"]) == _canonical(new["scores"])
                        and _canonical(old["decisions"]) == _canonical(new["decisions"])
                        and _canonical(old["answer"]) == _canonical(new["answer"]))
                per_record[rid] = bits
                if not same:
                    mismatches.append(rid)
            overall = hashlib.sha256("\n".join("%s %s" % (r, per_record[r]) for r in ctx.ids).encode()).hexdigest()
            failed = failed or bool(mismatches) or len(per_record) != EXPECTED_COURSE_PACKETS
            models.append({**checkpoint, "switch": False, "records": len(per_record),
                           "identical_records": len(per_record) - len(mismatches),
                           "mismatched_record_ids": mismatches[:20], "mismatch_count": len(mismatches),
                           "overall_logit_digest_preservation_format": overall})
            del model
            torch.cuda.empty_cache()
    return {"name": "OLD_PACKET_PRESERVATION", "verdict": "FAIL" if failed or len(models) != 6 else "PASS",
            "models": models, "comparisons": sum(row["records"] for row in models)}


# ------------------------------------------------------------------------------------------------ check b
def check_b(ctx):
    torch, LL, scope = ctx.torch, ctx.LL, ctx.scope
    specs = [("OFF_HELM20_FINAL_%d" % seed, seed, "final", False) for seed in SEEDS]
    specs += [("OFF_FRESH_%d" % FRESH_SEED, FRESH_SEED, None, False), ("ON_FRESH_%d" % FRESH_SEED, FRESH_SEED, None, True)]
    containers, failed = [], False
    for label, seed, phase, switch in specs:
        model, checkpoint = ctx.container(seed, phase, switch=switch)
        rows, errors = [], 0
        for key in ctx.larger_ids:
            ctx.wall()
            packet = ctx.fixtures[key]
            try:
                result = LL.predict_packet(torch, model, packet, ctx.device, tagger=ctx.tagger)
                if result["route"] != scope.LARGER:
                    raise ValueError("ROUTE:" + result["route"])
                if _canonical(result["plan"]) != _canonical(scope.compile_plan(packet)[1]):
                    raise ValueError("PLAN_DIFFERS_FROM_SCOPE_PLAN")
                ctx.answers.validate_answer(packet["source"], packet["record"]["query"], result["answer"])
                grade = scope.grade(packet, result["answer"])
                if type(grade["correct"]) is not bool:
                    raise ValueError("GRADE_NOT_BOOLEAN")
                # The correct/incorrect flag is deliberately NOT written: this is a plumbing check, and a public
                # fixture shape could coincide with a sealed TEST shape. The check digest seals the full receipt.
                rows.append({"fixture_id": key, "kind": ctx.rows[key]["kind"], "route": result["route"],
                             "plan_profile_schema": result["plan"]["profile"]["schema"],
                             "slots": len(result["plan"]["slots"]),
                             "candidates": len(result["plan"]["correspondence_candidates"]),
                             "logit_bits": LL.logit_bits_digest(torch, result["rows"]),
                             "answer_sha256": hashlib.sha256(_canonical(result["answer"]).encode()).hexdigest(),
                             "graded_by": grade["checker_module"], "graded": True,
                             "check_digest": grade["check"]["check_digest"],
                             "admissible_answer_count": grade["admissible_answer_count"]})
            except Exception as error:  # noqa: BLE001 - every error is recorded and fails the check
                errors += 1
                rows.append({"fixture_id": key, "error": _error(error)})
        failed = failed or errors > 0 or len(rows) != len(ctx.larger_ids)
        containers.append({"label": label, "checkpoint": checkpoint, "switch": switch, "fixtures": len(rows),
                           "errors": errors, "rows": rows})
        del model
        torch.cuda.empty_cache()
    return {"name": "FIXTURES_THROUGH_LEARNER", "verdict": "FAIL" if failed else "PASS", "containers": containers,
            "note": "plumbing only: correct/incorrect flags are not written; the fixtures are not an evaluation set"}


# ------------------------------------------------------------------------------------------------ check c
def check_c(ctx):
    torch, LL, scope = ctx.torch, ctx.LL, ctx.scope
    rows, failed = [], False
    original_forward, calls = LL.GraphForward, [0]

    def counting(*args, **kwargs):
        calls[0] += 1
        return original_forward(*args, **kwargs)

    for label, switch in (("OFF_FRESH_%d" % FRESH_SEED, False), ("ON_FRESH_%d" % FRESH_SEED, True)):
        model, _ = ctx.container(FRESH_SEED, None, switch=switch)
        for key in ctx.refused_ids:
            ctx.wall()
            expected = ctx.rows[key]["expected_refusal"]
            before = calls[0]
            LL.GraphForward = counting
            try:
                LL.predict_packet(torch, model, ctx.fixtures[key], ctx.device, tagger=ctx.tagger)
                outcome = {"refused": False}
            except scope.LargerPathRefusal as error:
                outcome = {"refused": True, "code": error.code, "message": str(error)}
            except Exception as error:  # noqa: BLE001
                outcome = {"refused": False, "error": _error(error)}
            finally:
                LL.GraphForward = original_forward
            outcome.update({"fixture_id": key, "container": label, "expected_code": expected,
                            "graph_forward_calls": calls[0] - before})
            ok = outcome["refused"] and outcome.get("code") == expected and outcome["graph_forward_calls"] == 0
            failed = failed or not ok
            rows.append(outcome)
        del model
        torch.cuda.empty_cache()
    # Informational: the ORIGINAL steps answer the 7-node and degree-5 parts questions without any refusal.
    model, _ = ctx.container(FRESH_SEED, None, switch=False)
    silent = []
    for key in ctx.refused_ids:
        try:
            ctx.original_steps(model, ctx.fixtures[key])
            silent.append({"fixture_id": key, "original_steps_answered": True})
        except Exception as error:  # noqa: BLE001
            silent.append({"fixture_id": key, "original_steps_answered": False, "error": _error(error)})
    del model
    torch.cuda.empty_cache()
    return {"name": "SEVEN_NODE_REFUSAL", "verdict": "FAIL" if failed else "PASS", "rows": rows,
            "original_steps_without_the_route_INFORMATIONAL": silent}


# ------------------------------------------------------------------------------------------------ check d
def check_d(ctx):
    torch, PL, LL, scope = ctx.torch, ctx.PL, ctx.LL, ctx.scope
    if platform.system() != "Linux" or os.environ.get("CAS_META2_RUN_TEACHING_CYCLE") != "1":
        return {"name": "FULL_LEARNER_SUBCLASS", "verdict": "FAIL",
                "reason": "ENV_GUARD_NOT_SET: needs Linux and CAS_META2_RUN_TEACHING_CYCLE=1 (learner guard)"}
    from cas_meta2.typed_teaching import encoder as encoder_module
    design = ctx.contract.DESIGN
    encoder = encoder_module.build_frozen_typed_encoder(torch, ctx.tokenizer, seed=design["encoder_seed"], d_model=64,
                                                        device=ctx.device)
    kwargs = {"optimizer_config": deepcopy(design["optimizer_config"]),
              "run_context": {"run_id": "larger-question-path-check",
                              "course_sha256": ctx.contract.MATERIAL[ctx.worker_contract.COURSE_PATH]["sha256"],
                              "condition": design["condition"], "source_seed": design["source_seed"]},
              "limits": {"max_updates": 1, "max_core_calls": 1000000, "max_wall_seconds": 7200},
              "device": ctx.device, "tagger": ctx.tagger, "python_seed": FRESH_SEED, "root": str(PACKAGE)}
    original = PL.PointerCourseLearner(torch, ctx.framework(torch, ctx.device, FRESH_SEED), encoder, **kwargs)
    larger = LL.LargerQuestionPointerLearner(torch, ctx.framework(torch, ctx.device, FRESH_SEED), encoder, **kwargs)
    same_start = (PL.state_identity(torch, dict(original.module.state_dict()))
                  == PL.state_identity(torch, dict(larger.module.state_dict()))
                  and original.run_identity_digest == larger.run_identity_digest)
    mismatches = []
    for rid in ctx.ids:
        ctx.wall()
        a = original.predict(ctx.packets[rid], PL.PREDICTION_DEPTH)
        b = larger.predict(ctx.packets[rid], PL.PREDICTION_DEPTH)
        if _canonical(a) != _canonical(b):
            mismatches.append(rid)
    counters_equal = original.counters == larger.counters
    fixture_rows, fixture_errors = [], 0
    for key in ctx.larger_ids:
        ctx.wall()
        packet = ctx.fixtures[key]
        try:
            prediction = larger.predict(packet, PL.PREDICTION_DEPTH)
            grade = scope.grade(packet, prediction["answer"])
            if type(grade["correct"]) is not bool:
                raise ValueError("GRADE_NOT_BOOLEAN")
            fixture_rows.append({"fixture_id": key, "prediction_id": prediction["prediction_id"], "graded": True,
                                 "check_digest": grade["check"]["check_digest"]})
        except Exception as error:  # noqa: BLE001
            fixture_errors += 1
            fixture_rows.append({"fixture_id": key, "error": _error(error)})
    try:
        original.predict(ctx.fixtures["F20"], PL.PREDICTION_DEPTH)
        original_refuses = {"refused": False}
    except Exception as error:  # noqa: BLE001
        original_refuses = {"refused": "TYPED_PERMUTATION_BOUND" in str(error), "error": _error(error)}
    refusal_rows, refusal_ok = [], True
    for key in ctx.refused_ids:
        before = dict(larger.counters)
        try:
            larger.predict(ctx.fixtures[key], PL.PREDICTION_DEPTH)
            row = {"fixture_id": key, "refused": False}
        except scope.LargerPathRefusal as error:
            row = {"fixture_id": key, "refused": True, "code": error.code}
        except Exception as error:  # noqa: BLE001
            row = {"fixture_id": key, "refused": False, "error": _error(error)}
        row["counters_unchanged"] = larger.counters == before
        refusal_ok = refusal_ok and row["refused"] and row.get("code") == ctx.rows[key]["expected_refusal"] \
            and row["counters_unchanged"]
        refusal_rows.append(row)
    training_refused = []
    for name, call in (("stage_batch", lambda: larger.stage_batch([], PL.PREDICTION_DEPTH, cursor=0, occurrence_ids=[])),
                       ("train_sealed_batch", lambda: larger.train_sealed_batch("x", expected_sha256="0" * 64,
                                                                                target_receipts=[]))):
        try:
            call()
            training_refused.append({"method": name, "refused": False})
        except scope.LargerPathRefusal as error:
            training_refused.append({"method": name, "refused": error.code == "INFERENCE_ONLY"})
    passed = (same_start and not mismatches and counters_equal and fixture_errors == 0
              and original_refuses["refused"] is True and refusal_ok
              and all(row["refused"] for row in training_refused))
    return {"name": "FULL_LEARNER_SUBCLASS", "verdict": "PASS" if passed else "FAIL",
            "same_start": same_start, "course_packets": len(ctx.ids), "prediction_mismatches": len(mismatches),
            "mismatched_record_ids": mismatches[:20], "counters_equal_after_course": counters_equal,
            "fixtures": fixture_rows, "fixture_errors": fixture_errors,
            "original_learner_refuses_6_node_correspondence": original_refuses,
            "refusals": refusal_rows, "training_refused": training_refused}


CHECKS = {"a": check_a, "b": check_b, "c": check_c, "d": check_d}


def _write(path, payload):
    partial = pathlib.Path(str(path) + ".partial")
    partial.write_bytes((json.dumps(payload, indent=1, sort_keys=True) + "\n").encode())
    os.replace(partial, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--checks", default="a,b,c,d")
    args = parser.parse_args()
    requested = [name.strip() for name in args.checks.split(",") if name.strip()]
    if not requested or any(name not in CHECKS for name in requested) or len(set(requested)) != len(requested):
        print("BAD_CHECKS", args.checks)
        return 1
    started = time.monotonic()
    try:
        import torch
    except ImportError:
        print("GPU_REQUIRED: torch is not importable")
        return 2
    if not torch.cuda.is_available():
        print("GPU_REQUIRED: CUDA is not available; no CPU fallback")
        return 2
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark = True, False
    device = torch.device("cuda", 0)
    payload = {"schema": SCHEMA, "complete": False, "requested": requested, "boundary": BOUNDARY,
               "torch": torch.__version__, "device_name": torch.cuda.get_device_name(device), "checks": {}}
    try:
        ctx = Context(torch, device, started)
    except Exception as error:  # noqa: BLE001 - any setup failure is a refusal, written before exiting
        payload.update({"verdict": "SETUP_REFUSED", "reason": "%s: %s" % (type(error).__name__, str(error)[:400]),
                        "traceback": traceback.format_exc()[-4000:]})
        _write(args.out, payload)
        print("SETUP_REFUSED", type(error).__name__, error)
        return 4
    payload.update({"course_digest": ctx.course_digest, "source_lf_sha256": ctx.source_pins,
                    "eval_paths_lf_sha256": {path.name: _lf_sha256(path) for path in sorted(HERE.glob("*.py"))},
                    "fixture_file_sha256": hashlib.sha256(ctx.FX.FIXTURE_PATH.read_bytes()).hexdigest(),
                    "fixture_set_digest": ctx.document["fixture_set_digest"],
                    "larger_fixtures": len(ctx.larger_ids), "refusal_fixtures": len(ctx.refused_ids)})
    for name in requested:
        try:
            payload["checks"][name] = CHECKS[name](ctx)
        except WallLimit:
            payload.update({"verdict": "WALL_LIMIT_REACHED", "wall_seconds": time.monotonic() - started})
            _write(args.out, payload)
            print("WALL_LIMIT_REACHED")
            return 3
        except SetupRefused as error:
            payload.update({"verdict": "SETUP_REFUSED", "reason": str(error)})
            _write(args.out, payload)
            print("SETUP_REFUSED", error)
            return 4
        except Exception as error:  # noqa: BLE001 - a crashed check is a failed check
            payload["checks"][name] = {"verdict": "FAIL", "crash": _error(error),
                                       "traceback": traceback.format_exc()[-4000:]}
        print(name, payload["checks"][name].get("name", ""), payload["checks"][name]["verdict"], flush=True)
        _write(args.out, payload)
    verdicts = [payload["checks"][name]["verdict"] for name in requested]
    if sorted(requested) == sorted(CHECKS) and all(value == "PASS" for value in verdicts):
        verdict = "INTEGRATION_CHECKS_PASS"
    elif any(value != "PASS" for value in verdicts):
        verdict = "INTEGRATION_CHECKS_FAIL"
    else:
        verdict = "INTEGRATION_CHECKS_INCOMPLETE"
    payload.update({"complete": True, "verdict": verdict, "wall_seconds": time.monotonic() - started})
    _write(args.out, payload)
    print(verdict)
    return 0 if verdict == "INTEGRATION_CHECKS_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
