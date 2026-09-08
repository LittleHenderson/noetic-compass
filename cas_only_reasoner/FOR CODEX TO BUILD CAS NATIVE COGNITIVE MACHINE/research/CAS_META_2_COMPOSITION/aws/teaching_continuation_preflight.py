"""Read-only current provider check for the bounded four-arm continuation.

Uses the existing provider observations and a six-GB storage worksheet, which
includes both retained prior input and the new output. No launch/reservation.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from aws import teaching_cycle_preflight as base
from aws import teaching_continuation_plan as plan

SCHEMA = "cas-teaching-continuation-live-preflight/1"


def observe(clients):
    facts = base.observe(clients)
    facts.update(schema=SCHEMA, cost_worksheet=plan.worksheet(facts["raw_prices"]),
        base_preflight_sha256=sha256(Path(base.__file__).read_bytes()).hexdigest(),
        plan_sha256=sha256(Path(plan.__file__).read_bytes()).hexdigest(),
        source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        restore_proved=False, logical_run_id=plan.LOGICAL_RUN_ID)
    return facts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    output = Path(args.output).absolute()
    records = Path(__file__).resolve().parents[1] / "records/teaching_cycle_001"
    base.require(".." not in output.parts and output.is_relative_to(records) and not output.exists(),
                 "FRESH_CONTINUATION_RECORD_REQUIRED")
    base.require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                         for p in (output, *output.parents)), "LINK_REJECTED")
    # SDK presence/configuration is checked before consuming the one-shot path.
    clients = base.build_clients(args.profile)
    output.mkdir(parents=True)
    try:
        result = observe(clients)
        code = 0
    except Exception as error:
        result = {"schema": SCHEMA, "status": "PREFLIGHT_FAILED",
            "observed_utc": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "error": str(error) if isinstance(error, (ValueError, plan.PlanError)) else "PROVIDER_CHECK_FAILED",
            "read_only": True, "reservation_created": False}
        code = 1
    result["source_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
    result["command"] = [sys.executable, *sys.argv]
    raw = base.encoded(result)
    with (output / "receipt.json").open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"exit_code": code, "receipt": str(output / "receipt.json"),
                      "sha256": sha256(raw).hexdigest()}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
