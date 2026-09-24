#!/usr/bin/env python3
# Validate this handoff's assembly, not project behavior. Standard library only.
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import sys

def main() -> int:
    root = Path(__file__).resolve().parent
    try:
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
        if package["status"] != "COMPLETE":
            raise ValueError("Package assembly incomplete")
        for row in package["files"]:
            p = (root / row["path"]).resolve()
            if p.parent != root or p.is_symlink():
                raise ValueError("Unexpected package path")
            raw = p.read_bytes()
            if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
                raise ValueError("Package identity mismatch: " + row["path"])
        tasks = json.loads((root / "TASKS.json").read_text(encoding="utf-8"))["tasks"]
        tests = json.loads((root / "ACCEPTANCE_TESTS.json").read_text(encoding="utf-8"))["tests"]
        ids = {r["id"] for r in tasks}
        test_ids = {r["id"] for r in tests}
        if len(ids) != len(tasks) or len(test_ids) != len(tests):
            raise ValueError("Duplicate task/test IDs")
        done = set()
        while len(done) < len(ids):
            ready = {r["id"] for r in tasks if r["id"] not in done and set(r["depends_on"]) <= done}
            if not ready:
                raise ValueError("Task cycle or absent dependency")
            done |= ready
        for r in tasks:
            if not set(r["acceptance_tests"]) <= test_ids:
                raise ValueError("Unknown test reference")
        env = json.loads((root / "RESOURCE_ENVELOPE.json").read_text(encoding="utf-8"))
        total = sum(Decimal(v) for v in env["stage_caps_usd"].values())
        if total != Decimal(env["initial_total_cap_usd"]):
            raise ValueError("Budget subtotals do not agree")
        if env["optional_api_is_additional"] or Decimal(env["optional_deepseek_api_subcap_usd"]) > total:
            raise ValueError("API subcap accounting invalid")
        template = json.loads((root / "RUN_MANIFEST.template.json").read_text(encoding="utf-8"))
        if template["status"] != "TEMPLATE_NOT_LAUNCHABLE":
            raise ValueError("A template must not impersonate a launch record")
        print(json.dumps({"status":"HANDOFF_PACKAGE_VALID", "files_checked":len(package["files"]),
                          "tasks":len(tasks), "specified_acceptance_tests":len(tests),
                          "project_tests_executed":0,"model_runs":0,"provider_calls":0}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status":"HANDOFF_PACKAGE_INVALID","error":str(exc)}), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
