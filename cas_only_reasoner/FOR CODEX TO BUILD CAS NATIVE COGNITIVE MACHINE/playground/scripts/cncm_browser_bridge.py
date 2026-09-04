"""Narrow JSON bridge between the browser worker and the CNCM runtime."""

from __future__ import annotations

import json

import cncm
from cncm import (
    CognitiveMachine,
    ConversationalMind,
    cognitive_apprenticeship_demo_cases,
    find_math_counterexample,
    language_qualification_demo_cases,
    run_language_qualification_demo,
    run_cognitive_apprenticeship_demo,
    solve_math,
    validate_problem,
    validate_math_notation,
    verify_evidence,
    verify_math_result,
    verify_counterexample_result,
)
from cncm.engine import replay as replay_result


_BRIDGE_VERSION = "0.7.0"
_MACHINE = CognitiveMachine()
_CONVERSATION = ConversationalMind()
_LAST_PROBLEM = None
_LAST_RESULT = None


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key: {key}")
        result[key] = value
    return result


def _reject_constant(token):
    raise ValueError(f"non-standard JSON constant: {token}")


def _loads(payload, label):
    if not isinstance(payload, str):
        raise TypeError(f"{label} must be a JSON string")
    return json.loads(
        payload,
        object_pairs_hook=_strict_object,
        parse_constant=_reject_constant,
    )


def _dumps(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _memory_summary():
    return {
        "episode_count": len(_MACHINE.episodic_memory),
        "episode_ids": [item.episode_id for item in _MACHINE.episodic_memory],
    }


def _error(operation, kind, exc, **extra):
    body = {
        "bridge_version": _BRIDGE_VERSION,
        "ok": False,
        "operation": operation,
        "error": {
            "kind": kind,
            "type": type(exc).__name__,
            "message": str(exc),
        },
        "memory": _memory_summary(),
    }
    body.update(extra)
    return _dumps(body)


def _validate_problem(payload):
    try:
        document = _loads(payload, "problem")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("validate", "json_parse", exc)

    if not isinstance(document, dict):
        return _error(
            "validate",
            "problem_shape",
            TypeError("problem must be a JSON object"),
        )

    try:
        report = validate_problem(document).to_dict()
    except Exception as exc:
        return _error("validate", "problem_contract", exc)

    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "validate",
        "report": report,
        "memory": _memory_summary(),
    })


def _run_problem(payload):
    global _LAST_PROBLEM, _LAST_RESULT

    try:
        document = _loads(payload, "problem")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("run", "json_parse", exc)

    if not isinstance(document, dict):
        return _error(
            "run",
            "problem_shape",
            TypeError("problem must be a JSON object"),
        )

    try:
        validation = validate_problem(document)
    except Exception as exc:
        return _error("run", "problem_contract", exc)

    if not validation.valid:
        return _dumps({
            "bridge_version": _BRIDGE_VERSION,
            "ok": False,
            "operation": "run",
            "error": {
                "kind": "problem_contract",
                "type": "ContractError",
                "message": "problem failed the CNCM contract",
            },
            "validation": validation.to_dict(),
            "memory": _memory_summary(),
        })

    try:
        result = _MACHINE.run(document)
        bundle = result.to_dict()
        verification = verify_evidence(bundle).to_dict()
    except Exception as exc:
        return _error("run", "runtime", exc)

    _LAST_PROBLEM = document
    _LAST_RESULT = result

    response = {
        "bridge_version": _BRIDGE_VERSION,
        "ok": verification["valid"],
        "operation": "run",
        "result": bundle,
        "verification": verification,
        "memory": _memory_summary(),
    }

    if not verification["valid"]:
        response["error"] = {
            "kind": "internal_verification",
            "type": "VerificationError",
            "message": "the generated evidence bundle failed closed verification",
        }

    return _dumps(response)


def _verify_bundle(payload):
    try:
        bundle = _loads(payload, "bundle")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("verify", "json_parse", exc)

    if not isinstance(bundle, dict):
        return _error(
            "verify",
            "bundle_shape",
            TypeError("bundle must be a JSON object"),
        )

    try:
        report = verify_evidence(bundle).to_dict()
    except Exception as exc:
        return _error("verify", "verification_runtime", exc)

    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "verify",
        "report": report,
        "memory": _memory_summary(),
    })


def _replay_last():
    if _LAST_PROBLEM is None or _LAST_RESULT is None:
        return _error(
            "replay",
            "nothing_to_replay",
            ValueError("run a problem before requesting replay"),
        )

    try:
        matches = replay_result(_LAST_PROBLEM, _LAST_RESULT)
    except Exception as exc:
        return _error("replay", "replay_runtime", exc)

    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "replay",
        "report": {
            "matches": matches,
            "run_id": _LAST_RESULT.final_state.run_id,
            "trace_digest": _LAST_RESULT.trace_digest,
        },
        "memory": _memory_summary(),
    })


def _math_validate(payload):
    try:
        document = _loads(payload, "math validation request")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("math_validate", "json_parse", exc)
    if not isinstance(document, dict) or set(document) - {"notation", "variables"}:
        return _error(
            "math_validate",
            "request_shape",
            ValueError("math validation request accepts only notation and variables"),
        )
    if "notation" not in document:
        return _error("math_validate", "request_shape", ValueError("notation is required"))
    try:
        report = validate_math_notation(
            document["notation"],
            declared_variables=document.get("variables"),
        ).to_dict()
    except Exception as exc:
        return _error("math_validate", "math_contract", exc)
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "math_validate",
        "report": report,
        "memory": _memory_summary(),
    })


def _math_solve(payload):
    try:
        document = _loads(payload, "math solve request")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("math_solve", "json_parse", exc)
    if not isinstance(document, dict) or set(document) != {"notation", "variable"}:
        return _error(
            "math_solve",
            "request_shape",
            ValueError("math solve request must contain only notation and variable"),
        )
    try:
        result = solve_math(document["notation"], document["variable"])
        bundle = result.to_dict()
        verification = verify_math_result(bundle).to_dict()
    except Exception as exc:
        return _error("math_solve", "math_runtime", exc)
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": verification["valid"],
        "operation": "math_solve",
        "math_result": bundle,
        "math_verification": verification,
        "memory": _memory_summary(),
    })


def _math_counterexample(payload):
    try:
        document = _loads(payload, "math counterexample request")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("math_counterexample", "json_parse", exc)
    allowed = {"notation", "bounds", "guards", "max_assignments"}
    required = {"notation", "bounds"}
    if (
        not isinstance(document, dict)
        or set(document) - allowed
        or not required <= set(document)
    ):
        return _error(
            "math_counterexample",
            "request_shape",
            ValueError("counterexample request requires notation and bounds only, with optional guards and max_assignments"),
        )
    try:
        result = find_math_counterexample(
            document["notation"],
            document["bounds"],
            guards=document.get("guards", ()),
            max_assignments=document.get("max_assignments", 4096),
        )
        bundle = result.to_dict()
        verification = verify_counterexample_result(bundle).to_dict()
    except Exception as exc:
        return _error("math_counterexample", "math_runtime", exc)
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": verification["valid"],
        "operation": "math_counterexample",
        "math_counterexample": bundle,
        "math_verification": verification,
        "memory": _memory_summary(),
    })


def _math_verify(payload):
    try:
        bundle = _loads(payload, "math result")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("math_verify", "json_parse", exc)
    if not isinstance(bundle, dict):
        return _error("math_verify", "bundle_shape", TypeError("math result must be an object"))
    try:
        report = verify_math_result(bundle).to_dict()
    except Exception as exc:
        return _error("math_verify", "verification_runtime", exc)
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "math_verify",
        "report": report,
        "memory": _memory_summary(),
    })


def _math_verify_counterexample(payload):
    try:
        bundle = _loads(payload, "math counterexample result")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("math_verify_counterexample", "json_parse", exc)
    if not isinstance(bundle, dict):
        return _error(
            "math_verify_counterexample",
            "bundle_shape",
            TypeError("math counterexample result must be an object"),
        )
    try:
        report = verify_counterexample_result(bundle).to_dict()
    except Exception as exc:
        return _error("math_verify_counterexample", "verification_runtime", exc)
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "math_verify_counterexample",
        "report": report,
        "memory": _memory_summary(),
    })


def _conversation_turn(payload):
    try:
        document = _loads(payload, "conversation request")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("conversation_turn", "json_parse", exc)

    if not isinstance(document, dict):
        return _error(
            "conversation_turn",
            "request_shape",
            TypeError("conversation request must be a JSON object"),
        )
    if set(document) != {"text"}:
        return _error(
            "conversation_turn",
            "request_shape",
            ValueError("conversation request must contain only text"),
        )

    try:
        turn = _CONVERSATION.turn(document["text"])
    except Exception as exc:
        return _error("conversation_turn", "conversation_runtime", exc)

    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "conversation_turn",
        "conversation": turn.to_dict(),
        "conversation_state": turn.state.to_dict(),
        "memory": _memory_summary(),
    })


def _conversation_status():
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "conversation_status",
        "conversation_state": _CONVERSATION.state.to_dict(),
        "memory": _memory_summary(),
    })


def _conversation_reset():
    state = _CONVERSATION.reset()
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "conversation_reset",
        "conversation_state": state.to_dict(),
        "memory": _memory_summary(),
    })


def _language_demo_cases():
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "language_demo_cases",
        "language_demo_cases": list(language_qualification_demo_cases()),
        "memory": _memory_summary(),
    })


def _language_qualify(payload):
    try:
        document = _loads(payload, "language qualification request")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("language_qualify", "json_parse", exc)
    if not isinstance(document, dict) or set(document) != {"case_id"}:
        return _error(
            "language_qualify",
            "request_shape",
            ValueError("language qualification request must contain only case_id"),
        )
    if not isinstance(document["case_id"], str) or not document["case_id"]:
        return _error(
            "language_qualify",
            "request_shape",
            ValueError("case_id must be a nonempty string"),
        )
    try:
        result = run_language_qualification_demo(document["case_id"])
    except Exception as exc:
        return _error("language_qualify", "language_runtime", exc)
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "language_qualify",
        "language_qualification": result,
        "memory": _memory_summary(),
    })


def _cognitive_apprenticeship_demo_cases():
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "cognitive_apprenticeship_demo_cases",
        "cognitive_apprenticeship_demo_cases": list(cognitive_apprenticeship_demo_cases()),
        "memory": _memory_summary(),
    })


def _cognitive_apprenticeship_qualify(payload):
    try:
        document = _loads(payload, "cognitive apprenticeship request")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("cognitive_apprenticeship_qualify", "json_parse", exc)
    if not isinstance(document, dict) or set(document) != {"case_id"}:
        return _error(
            "cognitive_apprenticeship_qualify",
            "request_shape",
            ValueError("cognitive apprenticeship request must contain only case_id"),
        )
    if not isinstance(document["case_id"], str) or not document["case_id"]:
        return _error(
            "cognitive_apprenticeship_qualify",
            "request_shape",
            ValueError("case_id must be a nonempty string"),
        )
    try:
        result = run_cognitive_apprenticeship_demo(document["case_id"])
    except Exception as exc:
        return _error("cognitive_apprenticeship_qualify", "cognitive_apprenticeship_runtime", exc)
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "cognitive_apprenticeship_qualify",
        "cognitive_apprenticeship": result,
        "memory": _memory_summary(),
    })


def _reset_machine():
    global _MACHINE, _CONVERSATION, _LAST_PROBLEM, _LAST_RESULT
    _MACHINE = CognitiveMachine()
    _CONVERSATION = ConversationalMind()
    _LAST_PROBLEM = None
    _LAST_RESULT = None
    return _dumps({
        "bridge_version": _BRIDGE_VERSION,
        "ok": True,
        "operation": "reset",
        "runtime_version": cncm.__version__,
        "conversation_state": _CONVERSATION.state.to_dict(),
        "memory": _memory_summary(),
    })


def bridge_dispatch(request_json):
    try:
        request = _loads(request_json, "request")
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        return _error("unknown", "request_parse", exc)

    if not isinstance(request, dict):
        return _error(
            "unknown",
            "request_shape",
            TypeError("request must be a JSON object"),
        )

    operation = request.get("operation")
    if operation == "validate":
        return _validate_problem(request.get("json"))
    if operation == "run":
        return _run_problem(request.get("json"))
    if operation == "verify":
        return _verify_bundle(request.get("json"))
    if operation == "replay":
        return _replay_last()
    if operation == "math_validate":
        return _math_validate(request.get("json"))
    if operation == "math_solve":
        return _math_solve(request.get("json"))
    if operation == "math_counterexample":
        return _math_counterexample(request.get("json"))
    if operation == "math_verify":
        return _math_verify(request.get("json"))
    if operation == "math_verify_counterexample":
        return _math_verify_counterexample(request.get("json"))
    if operation == "conversation_turn":
        return _conversation_turn(request.get("json"))
    if operation == "conversation_status":
        return _conversation_status()
    if operation == "conversation_reset":
        return _conversation_reset()
    if operation == "language_demo_cases":
        return _language_demo_cases()
    if operation == "language_qualify":
        return _language_qualify(request.get("json"))
    if operation == "cognitive_apprenticeship_demo_cases":
        return _cognitive_apprenticeship_demo_cases()
    if operation == "cognitive_apprenticeship_qualify":
        return _cognitive_apprenticeship_qualify(request.get("json"))
    if operation == "reset":
        return _reset_machine()
    if operation == "status":
        return _dumps({
            "bridge_version": _BRIDGE_VERSION,
            "ok": True,
            "operation": "status",
            "runtime_version": cncm.__version__,
            "conversation_state": _CONVERSATION.state.to_dict(),
            "memory": _memory_summary(),
        })

    return _error(
        str(operation),
        "unknown_operation",
        ValueError(
            "operation must be validate, run, verify, replay, math_validate, math_solve, "
            "math_counterexample, math_verify, math_verify_counterexample, conversation_turn, conversation_status, "
            "conversation_reset, language_demo_cases, language_qualify, cognitive_apprenticeship_demo_cases, "
            "cognitive_apprenticeship_qualify, reset, or status"
        ),
    )
