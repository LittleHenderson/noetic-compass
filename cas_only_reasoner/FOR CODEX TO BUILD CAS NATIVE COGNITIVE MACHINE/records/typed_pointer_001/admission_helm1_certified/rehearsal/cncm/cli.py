"""File-system host adapter for the pure deterministic kernel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .canonical import canonical_json
from .engine import CognitiveMachine
from .model import ContractError, ProblemPacket, TerminalStatus
from .verification import validate_problem, verify_bundle


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | None, value: Any) -> None:
    if path is None:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cncm", description="CAS Native Cognitive Machine v0.1 reference kernel")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="validate a typed CAS-Sem problem packet")
    check.add_argument("--problem", required=True)

    run = subparsers.add_parser("run", help="execute one deterministic reasoning episode")
    run.add_argument("--problem", required=True)
    run.add_argument("--trace")
    run.add_argument("--final-state")
    run.add_argument("--evidence")
    run.add_argument("--bundle")

    replay = subparsers.add_parser("replay", help="rerun and compare against a retained trace")
    replay.add_argument("--problem", required=True)
    replay.add_argument("--against", required=True)

    verify = subparsers.add_parser("verify", help="verify hashes and bindings in a retained run bundle")
    verify.add_argument("--bundle", required=True)

    demo = subparsers.add_parser("demo", help="run every fixture problem below a directory")
    demo.add_argument("--fixtures", default="fixtures")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "check":
            report = validate_problem(_load_json(args.problem))
            print(canonical_json(report.to_dict()))
            return 0 if report.valid else 2

        if args.command == "run":
            problem = ProblemPacket.from_dict(_load_json(args.problem))
            result = CognitiveMachine().run(problem)
            _write_json(args.trace, [item.to_dict() for item in result.trace])
            _write_json(args.final_state, result.final_state.to_dict())
            _write_json(args.evidence, result.evidence)
            _write_json(args.bundle, result.to_dict())
            print(canonical_json(result.summary()))
            return 3 if result.terminal_status is TerminalStatus.FAULT else 0

        if args.command == "replay":
            problem = ProblemPacket.from_dict(_load_json(args.problem))
            expected_document = _load_json(args.against)
            expected_trace = expected_document.get("trace", expected_document) if isinstance(expected_document, dict) else expected_document
            result = CognitiveMachine().run(problem)
            actual_trace = [item.to_dict() for item in result.trace]
            matches = actual_trace == expected_trace
            output = {
                "schema_version": "cncm.replay/0.1",
                "matches": matches,
                "actual_trace_digest": result.trace_digest,
                "expected_trace_digest": __import__("hashlib").sha256(
                    canonical_json(expected_trace).encode("utf-8")
                ).hexdigest(),
            }
            print(canonical_json(output))
            return 0 if matches else 4

        if args.command == "verify":
            report = verify_bundle(_load_json(args.bundle))
            print(canonical_json(report.to_dict()))
            return 0 if report.valid else 4

        if args.command == "demo":
            fixture_root = Path(args.fixtures)
            problems = sorted(fixture_root.glob("*/problem.json"))
            if not problems:
                raise ContractError(f"no fixture problems found below {fixture_root}")
            summaries = []
            for problem_path in problems:
                problem = ProblemPacket.from_dict(_load_json(str(problem_path)))
                summaries.append(CognitiveMachine().run(problem).summary())
            print(canonical_json({"schema_version": "cncm.demo/0.1", "runs": summaries}))
            return 0
    except (ContractError, KeyError, TypeError, ValueError, json.JSONDecodeError, OSError) as exc:
        print(canonical_json({"error": type(exc).__name__, "detail": str(exc)}), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

