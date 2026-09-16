"""Reproduce the seed-20260913 KeyError without any neural work.

The failed job failed at:
    recurrent_cjt/learner.py:276  position = learner._position(task)
    graph_teaching/real_framework.py:289  return self._index[task["record_id"]]
    KeyError: 'b19c5837...'

So a task the course presents was never indexed on the learner. Both the index
and the course draw from cs.default_tasks_for_round(round_index, built=built),
so either (a) the two calls disagree, or (b) task construction is not
deterministic. This script measures both, on CPU, with no torch model built.
"""

import json
import sys
import traceback

from cas_meta2.recurrent_cjt import course as cs
from cas_meta2.recurrent_cjt import runner as rn


def ids_for_round(round_index, built=None):
    supplied = cs.default_tasks_for_round(round_index, built=built)
    out = []
    for phase, tasks in supplied.items():
        for task in tasks:
            out.append((phase, task["record_id"]))
    return out


def main():
    report = {}

    # --- 1. the index as the runner builds it -----------------------------
    rounds = [entry["round"] for entry in cs.course_plan()["rounds"]]
    report["plan_rounds"] = rounds
    index = rn.course_task_index(built=None)
    index_ids = [task["record_id"] for task in index]
    report["index_size"] = len(index_ids)
    index_set = set(index_ids)

    # --- 2. every task the course will actually present -------------------
    missing = []
    presented = 0
    per_round = {}
    for round_index in rounds:
        rows = ids_for_round(round_index, built=None)
        per_round[round_index] = len(rows)
        for phase, rid in rows:
            presented += 1
            if rid not in index_set:
                missing.append({"round": round_index, "phase": phase,
                                "record_id": rid})
    report["presented_total"] = presented
    report["per_round_counts"] = per_round
    report["missing_count"] = len(missing)
    report["missing_sample"] = missing[:10]

    # --- 3. determinism across a torch reseed -----------------------------
    try:
        import torch
        first = [rid for _p, rid in ids_for_round(0, built=None)]
        torch.manual_seed(20260913)
        second = [rid for _p, rid in ids_for_round(0, built=None)]
        torch.manual_seed(20260914)
        third = [rid for _p, rid in ids_for_round(0, built=None)]
        report["determinism"] = {
            "round0_first_vs_after_seed20260913": first == second,
            "round0_after_seed20260913_vs_20260914": second == third,
            "first_hash_sample": first[:3],
            "third_hash_sample": third[:3],
        }
    except Exception as exc:  # pragma: no cover
        report["determinism"] = {"error": repr(exc)}

    # --- 4. does a repeated call change anything (global RNG drift)? ------
    a = [rid for _p, rid in ids_for_round(0, built=None)]
    b = [rid for _p, rid in ids_for_round(0, built=None)]
    report["repeat_call_stable"] = a == b

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
