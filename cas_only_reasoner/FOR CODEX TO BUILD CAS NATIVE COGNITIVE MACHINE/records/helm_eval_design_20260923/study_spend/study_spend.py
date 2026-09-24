"""HELM-REPAIR-CONTROLLED-1 study spend: program-derived, never hand-edited. Label CLAUDE_BUILT_CLAUDE_CHECKED.

The owner's ceiling is $60.00 of ACTUAL AWS spend for the whole comparison (plan section 0). The canonical meta1
ledger is written only by the training launcher (its fixed $15 bookings are bookkeeping, not spend) and is never
touched here. Every other job keeps its own watch record. This program sums a CONSERVATIVE upper bound per job from
those records and applies the admission rule:

    admit(next) iff  spent_upper_bound + next.worst_case + reserve(remaining mandatory slots incl. E1) <= 60.00

Conservative bound for a typed-pointer training/smoke job (the runner's rule): launcher elapsed seconds x the
recorded on-demand rate ceiling ($2.52/h) + the $1.48 ancillary allowance. Other jobs: their watcher's
cost_upper_bound_usd. A job still running counts at its declared worst case.
"""
import json
import math
import pathlib
import subprocess
import sys

CEILING = 60.00


def up(x):
    """Round an upper bound UP to the cent (conservative)."""
    return math.ceil(round(x * 100, 6)) / 100

RATE, ANCILLARY = 2.52, 1.48
TRAIN_WORST = up(14400 / 3600 * RATE + ANCILLARY)   # instance_seconds_max 14,400 s -> 11.56

# Every job in the envelope, in order. kind: pointer (launcher result.json) or watched (watch_record.json).
JOBS = [
    {"slot": "S1", "what": "switch-ON smoke attempt 1 (capacity refusal, no instance)", "kind": "pointer_git",
     "ref": "origin/claude/helm-on-launch-20260924",
     "path": "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001/receipt_analogy_on_smoke_20260917_attempt1/result.json"},
    {"slot": "S2", "what": "switch-ON smoke attempt 2 (passed)", "kind": "pointer_git",
     "ref": "origin/claude/helm-on-launch-20260924",
     "path": "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001/receipt_analogy_on_smoke_20260917/result.json"},
    {"slot": "P1a", "what": "larger-question route checks, both arms (T4)", "kind": "watched",
     "path": str(pathlib.Path(__file__).resolve().parents[1] / "larger_question_t4_job" / "watch_record.json"), "worst_case": 1.66},
]
# Declared future slots (conservative worst cases; see PREREQUISITE_SLOTS.md for timing bases).
FUTURE = [
    {"slot": "P1b", "what": "reader acceptance + corrected-probe validation + admission validation (one T4 job)", "worst_case": 2.00},
    {"slot": "P2", "what": "HSET-2 custodian build (CPU)", "worst_case": 1.00},
    {"slot": "M1", "what": "unchanged reproduction seed 20260917 of 20208c92 (g7.2xlarge)", "worst_case": TRAIN_WORST},
    {"slot": "M2", "what": "repaired seed 20260917", "worst_case": TRAIN_WORST},
    {"slot": "M3", "what": "repaired seed 20260918", "worst_case": TRAIN_WORST},
    {"slot": "M4", "what": "repaired seed 20260919", "worst_case": TRAIN_WORST},
    {"slot": "E1", "what": "TEST readout + 18 checkpoint probe reads + gates (T4)", "worst_case": 2.00},
]
FALLBACK_B = [{"slot": "M5", "worst_case": TRAIN_WORST}, {"slot": "M6", "worst_case": TRAIN_WORST}]


def git_json(ref, path):
    here = pathlib.Path(__file__).resolve().parent
    raw = subprocess.run(["git", "-C", str(here), "show", "%s:%s" % (ref, path)], capture_output=True, check=True).stdout
    return json.loads(raw)


def bound(job):
    if job["kind"] == "pointer_git":
        res = git_json(job["ref"], job["path"])
        seconds = float(res.get("elapsed_seconds") or 0.0)
        return up(seconds / 3600 * RATE + ANCILLARY), "elapsed %.1f s x $%.2f/h + $%.2f" % (seconds, RATE, ANCILLARY)
    p = pathlib.Path(job["path"])
    if p.is_file():
        w = json.loads(p.read_text(encoding="utf-8"))
        if w.get("terminated_confirmed") is True and w.get("cost_upper_bound_usd") is not None:
            return float(w["cost_upper_bound_usd"]), "watcher cost_upper_bound_usd (terminated)"
    return float(job["worst_case"]), "still running or unconfirmed: declared worst case"


def main():
    rows, spent = [], 0.0
    for job in JOBS:
        b, basis = bound(job)
        spent += b
        rows.append({"slot": job["slot"], "what": job["what"], "upper_bound_usd": b, "basis": basis})
    spent = round(spent, 2)
    future_total = round(sum(j["worst_case"] for j in FUTURE), 2)
    state = {"schema": "claude.helm-repair-controlled-1.study-spend/0.1", "ceiling_usd": CEILING,
             "spent_upper_bound_usd": spent, "jobs": rows, "future_mandatory_slots": FUTURE,
             "future_mandatory_worst_case_usd": future_total,
             "plan_C_worst_case_total_usd": round(spent + future_total, 2),
             "plan_C_fits_ceiling_at_worst_case": spent + future_total <= CEILING,
             "fallback_B_extra_worst_case_usd": round(sum(j["worst_case"] for j in FALLBACK_B), 2),
             "fallback_B_fits_at_worst_case": spent + future_total + sum(j["worst_case"] for j in FALLBACK_B) <= CEILING,
             "admission_rule": "admit(next) iff spent_upper_bound + next.worst_case + remaining mandatory worst cases <= 60.00; "
                               "the owner's $30-before-third-training-job stop also applies",
             "meta1_ledger": "not read or written by this program; training bookings are the launcher's own bookkeeping"}
    out = pathlib.Path(__file__).resolve().parent / "STUDY_SPEND_STATE.json"
    out.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: state[k] for k in ("spent_upper_bound_usd", "future_mandatory_worst_case_usd", "plan_C_worst_case_total_usd",
                                            "plan_C_fits_ceiling_at_worst_case", "fallback_B_extra_worst_case_usd", "fallback_B_fits_at_worst_case")}))
    for r in rows:
        print(r["slot"], r["upper_bound_usd"], r["basis"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
