"""The curriculum: a prerequisite DAG, ordered and complete."""

from cas_math.curriculum import STAGES, curriculum_order, prerequisites_of


def test_order_respects_prerequisites():
    order = curriculum_order()
    seen = set()
    for stage in order:
        for prereq in prerequisites_of(stage):
            assert prereq in seen, f"{stage} before prerequisite {prereq}"
        seen.add(stage)


def test_all_stages_present_and_start():
    order = curriculum_order()
    assert set(order) == set(STAGES)
    assert order[0] == "exact_arithmetic"


def test_mistake_recovery_after_its_prerequisites():
    order = curriculum_order()
    assert order.index("mistake_recovery") > order.index("procedure_proofs")
    assert order.index("mistake_recovery") > order.index("counterexamples")
