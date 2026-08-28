"""Procedural learning demonstration: strategy promotion under budget."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rlp.fixture_loader import load_package
from rlp.procedural import ProceduralLearner


def main():
    print("CAS-RLP procedural learning - ring R1 strategies")
    print("=" * 64)
    training = load_package("r1_overgeneralization")
    held_out = load_package("r1_bigger_held_out")

    learner = ProceduralLearner(training, held_out, budget=1)
    cycle = learner.learn()

    print(f"repair budget: {cycle['budget']} sandbox evaluation(s)")
    print("fault class: overgeneral_rule (rule fires without a magnitude guard)")
    print()
    print("strategies under test:")
    for decision in cycle["decisions"]:
        s = decision["strategy"]
        print(f"  {decision['verdict']:<10} {s['strategy_id']:<16} {s['note']}")
        print(f"               training: {decision['training']['evaluations_used']} "
              f"eval(s), repaired={decision['training']['promoted']}; "
              f"held-out: {decision['held_out']['evaluations_used']} eval(s), "
              f"repaired={decision['held_out']['promoted']}")
        for check in decision["checks"]:
            mark = "PASS" if check["passed"] else "FAIL"
            print(f"               {mark} {check['check']}")
    print()
    entry = learner.memory.lookup("overgeneral_rule")
    print(f"promoted strategy: {cycle['promoted_strategy']} "
          f"(status={entry['status']}, revision={entry['revision']}, "
          f"provenance={entry['provenance']})")
    print(f"unbudgeted default behavior regression: {cycle['regression_ok']}")

    rollback = learner.rollback()
    print(f"rollback: {rollback['action']} - parent strategy memory restored")


if __name__ == "__main__":
    main()
