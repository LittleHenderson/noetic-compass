"""Ring R3 and the evaluator-tampering prohibition."""

from rlp.fixture_loader import load_package
from rlp.mutations import Mutation
from rlp.rlp import CAS_RLP


def test_r3_target_rejected_as_protected():
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    mutation = Mutation("m_r3", "R3", "sole_writer",
                        {"kind": "remove_rule"},
                        "allow branches to write durable memory")
    decision = rlp._evaluate_mutation(mutation, {})
    assert decision["verdict"] == "REJECTED_AS_PROTECTED"
    assert "protected" in decision["detail"]


def test_kernel_target_rejected_as_protected():
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    mutation = Mutation("m_kernel", "R2", "kernel.transaction",
                        {"kind": "param_change", "value": 0})
    decision = rlp._evaluate_mutation(mutation, {})
    assert decision["verdict"] == "REJECTED_AS_PROTECTED"


def test_evaluator_tampering_rejected():
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    mutation = Mutation("m_tamper", "R1", "r_taller",
                        {"kind": "restrict_rule", "guard_pred": "gt",
                         "guard_args": ["?Hx", "?Hy"],
                         "modify_expectations": True},
                        "also weaken the held-out expectation")
    decision = rlp._evaluate_mutation(mutation, {})
    assert decision["verdict"] == "REJECTED_EVALUATOR_TAMPERING"
