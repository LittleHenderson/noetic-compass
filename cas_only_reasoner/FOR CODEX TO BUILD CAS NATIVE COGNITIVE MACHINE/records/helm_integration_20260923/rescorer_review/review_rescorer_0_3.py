"""Claude's read-only review of Codex's rescorer repair (trusted_rescore.py 0.3, commit 60e382b0). Costs nothing.

Compares, field by field, for all six historical decisions (Helm 1.0 and Helm 2.0, 3 seeds each):
  (a) Codex's targeted recheck: records/helm_integrated_repairs_20260923/historical_population_recheck.json @ 96644503
  (b) Claude's independent rule replay: records/helm_integration_20260923/RESCORE_RULE_REPLAY.json @ c995e09d
  (c) the acceptance table fixed in _handoffs/HELM_NEXT_PHASE_20260923/COORDINATION_CLAUDE.md (values below, copied
      before this review)
and checks the rule declaration: b > c, exact one-sided p <= 1/100, >= 2 kinds and >= 2 worlds, all seeds must pass,
no zero-loss veto. Reads git objects only. The verdict below is emitted by this program.

    python -B review_rescorer_0_3.py --out RESCORER_REVIEW.json
"""
import argparse
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[2]
CODEX, CLAUDE = "96644503", "c995e09d"
RECHECK = "records/helm_integrated_repairs_20260923/historical_population_recheck.json"
REPLAY = "records/helm_integration_20260923/RESCORE_RULE_REPLAY.json"
# The acceptance table (COORDINATION_CLAUDE.md), fixed before this review: (gained, lost, exact p, passed)
TABLE = {"helm1": {"20260917": (10, 0, "1/1024", True), "20260918": (12, 0, "1/4096", True), "20260919": (11, 0, "1/2048", True)},
         "helm2": {"20260917": (11, 1, "13/4096", True), "20260918": (12, 0, "1/4096", True), "20260919": (7, 1, "9/256", False)}}
LABELS = {"helm1": "LEARNS_NEW_WORLDS", "helm2": "NO_TRANSFER_TO_NEW_WORLDS"}


def show(commit, rel):
    pre = subprocess.run(["git", "-C", str(PACKAGE), "rev-parse", "--show-prefix"], capture_output=True, text=True, check=True).stdout.strip()
    return json.loads(subprocess.run(["git", "-C", str(PACKAGE), "show", "%s:%s%s" % (commit, pre, rel)],
                                     capture_output=True, check=True).stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    recheck, replay = show(CODEX, RECHECK), show(CLAUDE, REPLAY)
    rule = recheck["historical_rule"]
    rule_ok = {"alpha_1_100": rule.get("alpha") == "1/100", "b_greater_than_c": rule.get("require_b_greater_than_c") is True,
               "min_kinds_2": rule.get("min_improved_kinds") == 2, "min_worlds_2": rule.get("min_improved_worlds") == 2,
               "all_seeds_must_pass": rule.get("all_seeds_must_pass") is True, "no_zero_loss_veto": rule.get("zero_loss_veto") is False}
    rows, mismatches = [], []
    for study, rstudy in (("helm1", "helm1_certified"), ("helm2", "helm2_experimental")):
        for seed, (g, l, p, passed) in TABLE[study].items():
            a = recheck["studies"][study]["per_seed"][seed]
            b = replay["studies"][rstudy]["per_seed"][seed]
            row = {"study": study, "seed": seed, "table": [g, l, p, passed],
                   "codex_recheck": [a["gained"], a["broken"], a["p_one_sided"], a["passed"]],
                   "claude_replay": [b["gained"], b["lost"], b["p_one_sided"], b["passed_by_0_3_rule"]],
                   "codex_breadth": [len(a["kinds_improved"]), a["worlds_improved"]], "claude_breadth": [len(b["kinds"]), b["worlds"]],
                   "codex_agrees_with_frozen_grader": a["agreement"]["agree"]}
            row["all_three_agree"] = row["table"] == row["codex_recheck"] == row["claude_replay"] and row["codex_breadth"] == row["claude_breadth"]
            if not row["all_three_agree"] or not row["codex_agrees_with_frozen_grader"]:
                mismatches.append(row)
            rows.append(row)
    labels = {s: {"codex": recheck["studies"][s]["label"], "expected": LABELS[s]} for s in LABELS}
    labels_ok = all(v["codex"] == v["expected"] for v in labels.values())
    verdict = ("RULE_REPAIR_REPRODUCES_HISTORY" if all(rule_ok.values()) and not mismatches and labels_ok
               and recheck["status"] == "HISTORICAL_POPULATION_REPRODUCED" else "RULE_REPAIR_DISAGREES")
    out = {"schema": "claude.rescorer-review/0.1", "codex_commit": CODEX, "claude_commit": CLAUDE,
           "tool_sha256_lf": recheck["tool"]["sha256_lf"], "recheck_status": recheck["status"], "recheck_scope": recheck["scope"],
           "rule_declared": rule, "rule_checks": rule_ok, "rows": rows, "mismatches": mismatches, "labels": labels, "verdict": verdict,
           "not_covered": ["the full 564-record CLI reading of tool 0.3 (NOT_RUN: laptop timeout)",
                           "the 9 slow rescorer tests (HELM_RUN_SLOW_TESTS=1; NOT_RUN)",
                           "the anchor policy (keep 0.2 anchors and report their zero-loss metadata vs refuse them): OWNER DECISION, unresolved",
                           "independence: Claude reviews Codex's tool, but the six decisions were also replayed by Claude; custody is not outside"]}
    pathlib.Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": verdict, "rule_checks": rule_ok, "mismatches": len(mismatches), "labels": labels}, indent=1))


if __name__ == "__main__":
    main()
