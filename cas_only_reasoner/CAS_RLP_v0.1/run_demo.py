"""CAS-RLP v0.1 demonstration: one full improvement cycle."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rlp.fixture_loader import load_package
from rlp.mutations import Mutation
from rlp.rlp import CAS_RLP
from rlp.sandbox import grade, run_suite


def main():
    print("CAS-RLP v0.1 - recursive learning demonstration")
    print("=" * 64)
    print("PARENT v12 rule: taller(X,Y) :- height(X,Hx), height(Y,Hy)")
    print("  (overgeneralized: no magnitude comparison)")
    print()

    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    cycle = rlp.improve()
    print("R1 improvement cycle - decisions:")
    for d in cycle["decisions"]:
        m = d["mutation"]
        print(f"  {d['verdict']:<28} {m['mutation_id']:<26} {m['note']}")
    print(f"  current revision: {cycle['current_revision']}")
    print()

    print("R2 sandbox experiments (parameter changes):")
    r2 = CAS_RLP(load_package("r2_parameter"))
    for mutation in [
        Mutation("m_ticks1", "R2", "max_ticks",
                 {"kind": "param_change", "value": 1},
                 "starve the tick budget"),
        Mutation("m_ticks300", "R2", "max_ticks",
                 {"kind": "param_change", "value": 300},
                 "more ticks, no demonstrated gain"),
    ]:
        parent_results, _ = run_suite(r2.current_package)
        parent_grades = grade(r2.current_package, parent_results)
        d = r2._evaluate_mutation(mutation, parent_grades)
        print(f"  {d['verdict']:<28} {mutation.mutation_id:<26} {mutation.note}")
    print()

    print("R3 protection:")
    r3 = CAS_RLP(load_package("r1_overgeneralization"))
    m = Mutation("m_r3", "R3", "sole_writer", {"kind": "remove_rule"},
                 "remove the sole-writer rule")
    d = r3._evaluate_mutation(m, {})
    print(f"  {d['verdict']:<28} {m.mutation_id:<26} {m.note}")
    print()

    result = rlp.rollback()
    print(f"ROLLBACK: restored revision {result['restored_revision']}, "
          f"regression ok: {result['regression_ok']}")


if __name__ == "__main__":
    main()
