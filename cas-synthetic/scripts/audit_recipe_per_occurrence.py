"""One-off audit: apply the new per-occurrence recipe validator to the
398 accepted records from run 20260508T110453Z.

Reports how many recipe records flip from accept to reject and prints
the failure reasons + windows so we can spot-check 5 cases for real
operator-confusion vs false positives.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

# Force UTF-8 stdout on Windows so Greek letters in CAS expressions print.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "cas-synthetic" / "scripts" / "generate_path_d_wave3_v2.py"
ACCEPTED = (
    REPO
    / "cas-synthetic"
    / "data"
    / "path_d"
    / "wave3_step2_5_english_descriptions_20260508T110453Z.jsonl"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v2_under_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["v2_under_audit"] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    m = _load_module()
    n_total = 0
    n_recipe = 0
    n_pass = 0
    n_fail = 0
    fails: list[dict] = []
    with ACCEPTED.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n_total += 1
            rec = json.loads(line)
            cat = rec.get("grammar_category", "")
            expr = rec.get("source_cas", "")
            if cat != "recipe" and "Θ" not in expr and "Theta" not in expr:
                continue
            if not m._RE_RECIPE_OPERAND.search(expr):
                continue
            n_recipe += 1
            english = rec.get("english_description", "")
            r = m.validate_cas_to_english_recipe_per_occurrence(
                source_cas=expr,
                english_output=english,
            )
            if r.passed:
                n_pass += 1
            else:
                n_fail += 1
                fails.append({
                    "seed_id": rec.get("seed_id"),
                    "source_cas": expr,
                    "english": english,
                    "reason": r.reason,
                    "detail": r.detail,
                })

    print(f"total records audited:   {n_total}")
    print(f"recipe records:          {n_recipe}")
    print(f"  pass per-occurrence:   {n_pass}")
    print(f"  FAIL per-occurrence:   {n_fail}")
    print()
    print(f"failure rate on recipes: {n_fail / max(1, n_recipe):.1%}")
    print()
    print("=" * 72)
    print("FAILURE DETAILS (one block per record):")
    print("=" * 72)
    for fr in fails:
        print()
        print(f"seed_id:    {fr['seed_id']}")
        print(f"source_cas: {fr['source_cas']}")
        print(f"english:    {fr['english']}")
        print(f"reason:     {fr['reason']}")
        if fr["detail"].get("operand_failures"):
            for of in fr["detail"]["operand_failures"]:
                print(
                    f"  operand[{of.get('operand_index')}] "
                    f"({of.get('operand')}) coeff={of.get('coefficient')}: "
                    f"{of.get('reason')}"
                )
                if of.get("snippet"):
                    print(f"    snippet: {of['snippet']!r}")


if __name__ == "__main__":
    main()
