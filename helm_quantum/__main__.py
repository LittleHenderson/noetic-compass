"""Run from the Q1 repository root: python -m helm_quantum inventory --read-only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .admission import ROOT, admit_offline_fixture
from .backends.offline import OfflineBackend
from .classical import search
from .contracts import QuantumProblem
from .eligibility import assess
from .verifier import propose, verify
from .wire import ContractError, plain, require


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    inventory = commands.add_parser("inventory")
    inventory.add_argument("--read-only", action="store_true", required=True)
    for name in ("baseline", "validate", "compare", "problem", "verify-program", "compile", "estimate"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--fixture", choices=["q1-mod4"], default="q1-mod4")
        cmd.add_argument("--target", choices=["add2", "parity"], default="add2")
        cmd.add_argument("--mode", choices=["disabled", "shadow", "research"], default="disabled")
        if name == "baseline":
            cmd.add_argument("--method", choices=["exhaustive", "structured", "uniform"], default="exhaustive")
            cmd.add_argument("--samples", type=int, default=64)
            cmd.add_argument("--seed", type=int, default=0)
        if name == "compare":
            cmd.add_argument("--offline", action="store_true", required=True)
        if name == "verify-program":
            cmd.add_argument("--program", type=int, nargs=3, required=True)
        if name == "compile":
            cmd.add_argument("--backend", choices=["local"], required=True)
        if name == "estimate":
            cmd.add_argument("--request", type=Path)
    submit = commands.add_parser("submit")
    submit.add_argument("--request", type=Path, required=True)
    submit.add_argument("--authorization", help="refusal testing only; this backend always refuses")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "submit":
            # Refuse before reading any untrusted grant or constructing any client.
            OfflineBackend().submit(None)
        if args.command == "inventory":
            data = json.loads((ROOT / "SOURCE_INVENTORY.json").read_text(encoding="utf-8"))
        else:
            context = admit_offline_fixture(args.target, args.mode)
            problem = context.problem()
            if args.command == "problem":
                data = problem
            elif args.command == "baseline":
                data = search(problem, args.method, samples=args.samples, seed=args.seed)
            elif args.command == "compare":
                data = {method: plain(search(problem, method))
                        for method in ("exhaustive", "structured", "uniform")}
            elif args.command == "validate":
                result = search(problem)
                data = {"fixture": "q1-mod4", "search": plain(result),
                        "verification": plain(verify(problem, result.proposal)) if result.proposal else None,
                        "eligibility": plain(assess(problem)), "host_integrated": False}
            elif args.command == "verify-program":
                data = verify(problem, propose(problem, tuple(args.program)))
            elif args.command == "compile":
                data = OfflineBackend().compile(problem)
            else:
                if args.request:
                    require(args.request.stat().st_size <= 65536, "request exceeds 64 KiB")
                    problem = QuantumProblem.from_json(args.request.read_text(encoding="utf-8"),
                                                       admission=context)
                data = OfflineBackend().estimate(problem)
        print(json.dumps(plain(data), indent=2, allow_nan=False))
        return 0
    except (ContractError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
