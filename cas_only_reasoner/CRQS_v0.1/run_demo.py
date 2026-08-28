"""CRQS v0.1 demonstration: qualify three Minds honestly."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crqs.qualify import qualify
from crqs.report import format_report
from crqs.workflow import run_workflow

ROOT = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(ROOT, "fixtures", name), "r",
              encoding="utf-8") as fh:
        return json.load(fh)


def main():
    print("CRQS v0.1 - CAS Reasoning Qualification Standard")
    print("=" * 64)
    for name, label in (
        ("manifest_cas_rr.json", "the cas-rr prototype"),
        ("manifest_kernel.json", "the authority-contract kernel alone"),
        ("manifest_cncm.json", "the assembled CNCM (six boards)"),
    ):
        manifest = load(name)
        report, steps = run_workflow(manifest)
        print(f"QUALIFYING: {manifest['mind_id']} ({label})")
        print("-" * 64)
        print(format_report(report))
        print()
        print(f"workflow steps: {len(steps)} (1. {steps[0]['name']} ... "
              f"15. {steps[14]['name']})")
        print()
        print("=" * 64)


if __name__ == "__main__":
    main()
