from __future__ import annotations

import unittest

from cncm.math_kernel import check_math_step, verify_math_receipt
from cncm.math_model import (
    IntegerExpression,
    MathClaim,
    MathClaimStatus,
    MathRejectionCode,
    MathStepOperation,
    MathStepProposal,
    Provenance,
)
from cncm.math_parser import parse_math_statement


def given(notation: str, variables: tuple[str, ...]) -> MathClaim:
    return MathClaim.create(
        statement=parse_math_statement(notation, declared_variables=variables),
        status=MathClaimStatus.GIVEN,
        provenance=(Provenance("fixture", "math_operation_contract", notation),),
    )


class MathOperationContractTests(unittest.TestCase):
    def test_evaluate_exact_accepts_true_closed_arithmetic_and_rejects_falsehood(self) -> None:
        exact = MathStepProposal.create(
            operation=MathStepOperation.EVALUATE_EXACT,
            premise_claim_ids=(),
            proposed_conclusion=parse_math_statement("1/3+1/6=1/2"),
        )

        accepted = check_math_step(exact, ())

        self.assertTrue(accepted.accepted, accepted.detail)
        self.assertEqual(accepted.discharged_guards, ("exact_evaluation",))
        self.assertEqual(
            accepted.reconstructed_conclusion.to_dict(),
            {
                "left": {
                    "kind": "rational",
                    "value": {"numerator": 1, "denominator": 2},
                },
                "relation": "EQUAL",
                "right": {
                    "kind": "rational",
                    "value": {"numerator": 1, "denominator": 2},
                },
            },
        )
        self.assertTrue(verify_math_receipt(exact, (), accepted))

        falsehood = MathStepProposal.create(
            operation=MathStepOperation.EVALUATE_EXACT,
            premise_claim_ids=(),
            proposed_conclusion=parse_math_statement("2+2=5"),
        )

        rejected = check_math_step(falsehood, ())

        self.assertFalse(rejected.accepted)
        self.assertIs(
            rejected.rejection_code,
            MathRejectionCode.INVALID_TRANSFORMATION,
        )

    def test_add_both_sides_reconstructs_the_same_exact_addend(self) -> None:
        premise = given("x=3", ("x",))
        proposal = MathStepProposal.create(
            operation=MathStepOperation.ADD_BOTH_SIDES,
            premise_claim_ids=(premise.claim_id,),
            proposed_conclusion=parse_math_statement(
                "x+2=5",
                declared_variables=("x",),
            ),
            parameter=IntegerExpression(2),
        )

        accepted = check_math_step(proposal, (premise,))

        self.assertTrue(accepted.accepted, accepted.detail)
        self.assertEqual(
            accepted.discharged_guards,
            ("same_expression_both_sides",),
        )
        self.assertTrue(verify_math_receipt(proposal, (premise,), accepted))

        asymmetric = MathStepProposal.create(
            operation=MathStepOperation.ADD_BOTH_SIDES,
            premise_claim_ids=(premise.claim_id,),
            proposed_conclusion=parse_math_statement(
                "x+2=6",
                declared_variables=("x",),
            ),
            parameter=IntegerExpression(2),
        )

        rejected = check_math_step(asymmetric, (premise,))

        self.assertFalse(rejected.accepted)
        self.assertIs(
            rejected.rejection_code,
            MathRejectionCode.INVALID_TRANSFORMATION,
        )

    def test_transitive_less_than_accepts_either_premise_order_only_with_shared_middle(self) -> None:
        less_ab = given("a<b", ("a", "b"))
        less_bc = given("b<c", ("b", "c"))
        conclusion = parse_math_statement("a<c", declared_variables=("a", "c"))

        for premises in ((less_ab, less_bc), (less_bc, less_ab)):
            with self.subTest(order=tuple(claim.claim_id for claim in premises)):
                proposal = MathStepProposal.create(
                    operation=MathStepOperation.TRANSITIVE_LESS_THAN,
                    premise_claim_ids=tuple(claim.claim_id for claim in premises),
                    proposed_conclusion=conclusion,
                )

                receipt = check_math_step(proposal, premises)

                self.assertTrue(receipt.accepted, receipt.detail)
                self.assertEqual(receipt.discharged_guards, ("shared_middle_term",))
                self.assertTrue(verify_math_receipt(proposal, premises, receipt))

        disconnected = given("d<c", ("c", "d"))
        invalid = MathStepProposal.create(
            operation=MathStepOperation.TRANSITIVE_LESS_THAN,
            premise_claim_ids=(less_ab.claim_id, disconnected.claim_id),
            proposed_conclusion=conclusion,
        )

        rejected = check_math_step(invalid, (less_ab, disconnected))

        self.assertFalse(rejected.accepted)
        self.assertIs(
            rejected.rejection_code,
            MathRejectionCode.INVALID_TRANSFORMATION,
        )


if __name__ == "__main__":
    unittest.main()
