from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import copy
import unittest

from cncm.math_counterexample import (
    CounterexampleStatus,
    search_math_counterexample,
    verify_counterexample_result,
)
from cncm.math_engine import MathTerminalStatus, solve_linear_equation, verify_math_result
from cncm.math_kernel import check_math_step, issue_checked_math_claim, verify_math_receipt
from cncm.math_model import (
    CounterexampleBounds,
    DivideExpression,
    ExactRational,
    IntegerExpression,
    MATH_BRANCH_ID,
    MATH_MAX_DERIVATION_DEPTH,
    MATH_THEORY_ID,
    MathBudgetError,
    MathClaim,
    MathClaimStatus,
    MathContractError,
    MathGuardError,
    MathParseLimits,
    MathRejectionCode,
    MathRelation,
    MathStatement,
    MathStepOperation,
    MathStepProposal,
    MathStepReceipt,
    Provenance,
    RationalExpression,
    VariableExpression,
)
from cncm.math_normalize import evaluate_expression, normalize_linear
from cncm.math_parser import parse_math_expression, parse_math_statement


def given(notation: str, variables: tuple[str, ...]) -> MathClaim:
    return MathClaim.create(
        statement=parse_math_statement(notation, declared_variables=variables),
        status=MathClaimStatus.GIVEN,
        provenance=(Provenance("fixture", "math_test", notation),),
    )


class ExactMathModelTests(unittest.TestCase):
    def test_rationals_are_reduced_signed_and_never_floats(self) -> None:
        self.assertEqual(ExactRational(2, 4), ExactRational(1, 2))
        self.assertEqual(ExactRational(2, -4), ExactRational(-1, 2))
        self.assertEqual(ExactRational(0, 99), ExactRational(0, 1))
        self.assertEqual(
            ExactRational(1, 3) + ExactRational(1, 6),
            ExactRational(1, 2),
        )
        with self.assertRaises(MathGuardError):
            ExactRational(1, 0)
        with self.assertRaises(MathContractError):
            ExactRational(True, 1)
        with self.assertRaises(MathContractError):
            ExactRational(0.5, 1)  # type: ignore[arg-type]

    def test_math_objects_are_immutable(self) -> None:
        value = ExactRational(1, 3)
        with self.assertRaises(FrozenInstanceError):
            value.numerator = 4  # type: ignore[misc]

    def test_parser_preserves_exact_fraction_and_precedence(self) -> None:
        expression = parse_math_expression("1/3 + 1/6")
        self.assertEqual(evaluate_expression(expression, {}), ExactRational(1, 2))
        form = normalize_linear(
            parse_math_expression("2*(x+3)-4", declared_variables=("x",))
        )
        self.assertEqual(form.coefficient("x"), ExactRational(2))
        self.assertEqual(form.constant, ExactRational(2))

    def test_parser_rejects_unfrozen_syntax_and_undeclared_variables(self) -> None:
        invalid = (
            "3x=6",
            "x^2=4",
            "x=0.5",
            "x=y=z",
            "sin(x)=0",
            "x<=2",
        )
        for notation in invalid:
            with self.subTest(notation=notation), self.assertRaises(MathContractError):
                parse_math_statement(notation, declared_variables=("x", "y"))
        with self.assertRaises(MathContractError):
            parse_math_statement("x+y=1", declared_variables=("x",))

    def test_parser_budgets_fail_closed(self) -> None:
        with self.assertRaises(MathBudgetError):
            parse_math_expression("1234", limits=MathParseLimits(max_integer_digits=3))
        with self.assertRaises(MathBudgetError):
            parse_math_expression(
                "((((x))))",
                declared_variables=("x",),
                limits=MathParseLimits(max_depth=2),
            )
        with self.assertRaises(MathBudgetError):
            parse_math_expression("1+2+3", limits=MathParseLimits(max_tokens=4))


class ProtectedMathCheckerTests(unittest.TestCase):
    def test_checked_status_cannot_be_caller_asserted_or_deserialized(self) -> None:
        statement = parse_math_statement("2=3")
        with self.assertRaises(MathContractError):
            MathClaim.create(
                statement=statement,
                status=MathClaimStatus.VERIFIED,
                provenance=(Provenance("caller", "false_claim"),),
            )

        wire = given("2=3", ()).to_dict()
        wire["status"] = "VERIFIED"
        wire["derivation_receipt_id"] = "math-receipt-0000000000000000"
        wire["provenance"] = [
            {
                "source_type": "math_receipt",
                "source_id": "math-receipt-0000000000000000",
                "detail": "forged",
            }
        ]
        with self.assertRaises(MathContractError):
            MathClaim.from_dict(wire)

    def test_content_id_and_fixed_context_cannot_be_forged(self) -> None:
        premise = given("x=1", ("x",))
        with self.assertRaises(MathContractError):
            replace(premise, claim_id="math-claim-0000000000000000")

        proposal = MathStepProposal.create(
            operation=MathStepOperation.SIMPLIFY_EXACT,
            premise_claim_ids=(premise.claim_id,),
            proposed_conclusion=premise.statement,
        )
        with self.assertRaises(MathContractError):
            replace(proposal, proposal_id="math-proposal-0000000000000000")
        with self.assertRaises(MathContractError):
            MathStepProposal.create(
                operation=MathStepOperation.SIMPLIFY_EXACT,
                premise_claim_ids=(premise.claim_id,),
                proposed_conclusion=premise.statement,
                branch_id="forged_branch",
            )
        with self.assertRaises(MathContractError):
            MathStepProposal.create(
                operation=MathStepOperation.SIMPLIFY_EXACT,
                premise_claim_ids=(premise.claim_id,),
                proposed_conclusion=premise.statement,
                theory_id="attacker.theory/9.9",
            )
        with self.assertRaises(MathContractError):
            MathStepProposal.create(
                operation=MathStepOperation.SUBSTITUTE,
                premise_claim_ids=tuple(
                    f"math-claim-{index:016x}" for index in range(65)
                ),
                proposed_conclusion=premise.statement,
            )

    def test_claim_mapping_alias_is_rejected(self) -> None:
        premise = given("x=1", ("x",))
        alias = "math-claim-0000000000000000"
        proposal = MathStepProposal.create(
            operation=MathStepOperation.SIMPLIFY_EXACT,
            premise_claim_ids=(alias,),
            proposed_conclusion=premise.statement,
        )
        receipt = check_math_step(proposal, {alias: premise})
        self.assertFalse(receipt.accepted)
        self.assertEqual(receipt.rejection_code, MathRejectionCode.UNVERIFIED_PREMISE)

    def test_forged_accepted_receipt_does_not_verify(self) -> None:
        premise = given("x+1=4", ("x",))
        wrong_conclusion = parse_math_statement("x=2", declared_variables=("x",))
        proposal = MathStepProposal.create(
            operation=MathStepOperation.SUBTRACT_BOTH_SIDES,
            premise_claim_ids=(premise.claim_id,),
            proposed_conclusion=wrong_conclusion,
            parameter=IntegerExpression(1),
        )
        forged = MathStepReceipt.create(
            proposal=proposal,
            accepted=True,
            reconstructed_conclusion=wrong_conclusion,
        )
        self.assertFalse(verify_math_receipt(proposal, (premise,), forged))
        with self.assertRaises(MathContractError):
            replace(forged, receipt_id="math-receipt-0000000000000000")

    def test_same_operation_on_both_sides_is_reconstructed(self) -> None:
        premise = given("x+1=4", ("x",))
        proposal = MathStepProposal.create(
            operation=MathStepOperation.SUBTRACT_BOTH_SIDES,
            premise_claim_ids=(premise.claim_id,),
            proposed_conclusion=parse_math_statement("x=3", declared_variables=("x",)),
            parameter=IntegerExpression(1),
        )
        receipt = check_math_step(proposal, (premise,))
        self.assertTrue(receipt.accepted)
        self.assertIn("same_expression_both_sides", receipt.discharged_guards)
        self.assertTrue(verify_math_receipt(proposal, (premise,), receipt))

    def test_invalid_transformation_and_zero_divisor_are_rejected(self) -> None:
        premise = given("2*x=8", ("x",))
        wrong = MathStepProposal.create(
            operation=MathStepOperation.DIVIDE_BOTH_SIDES,
            premise_claim_ids=(premise.claim_id,),
            proposed_conclusion=parse_math_statement("x=5", declared_variables=("x",)),
            parameter=IntegerExpression(2),
        )
        receipt = check_math_step(wrong, (premise,))
        self.assertFalse(receipt.accepted)
        self.assertEqual(receipt.rejection_code, MathRejectionCode.INVALID_TRANSFORMATION)

        zero = MathStepProposal.create(
            operation=MathStepOperation.DIVIDE_BOTH_SIDES,
            premise_claim_ids=(premise.claim_id,),
            proposed_conclusion=parse_math_statement("2*x=8", declared_variables=("x",)),
            parameter=IntegerExpression(0),
        )
        zero_receipt = check_math_step(zero, (premise,))
        self.assertFalse(zero_receipt.accepted)
        self.assertEqual(zero_receipt.rejection_code, MathRejectionCode.UNDISCHARGED_GUARD)

    def test_negative_scaling_reverses_less_than(self) -> None:
        premise = given("x<2", ("x",))
        proposal = MathStepProposal.create(
            operation=MathStepOperation.MULTIPLY_BOTH_SIDES,
            premise_claim_ids=(premise.claim_id,),
            proposed_conclusion=parse_math_statement("-2 < -x", declared_variables=("x",)),
            parameter=IntegerExpression(-1),
        )
        receipt = check_math_step(proposal, (premise,))
        self.assertTrue(receipt.accepted, receipt.detail)
        self.assertIn("negative_scale_reverses_inequality", receipt.discharged_guards)

    def test_transitivity_and_cited_substitution_are_checked(self) -> None:
        ab = given("a=b", ("a", "b", "c"))
        bc = given("b=c", ("a", "b", "c"))
        transitive = MathStepProposal.create(
            operation=MathStepOperation.TRANSITIVE_EQUAL,
            premise_claim_ids=(ab.claim_id, bc.claim_id),
            proposed_conclusion=parse_math_statement("a=c", declared_variables=("a", "c")),
        )
        self.assertTrue(check_math_step(transitive, (ab, bc)).accepted)

        target = given("x+1=4", ("x",))
        binding = given("x=3", ("x",))
        substitution = MathStepProposal.create(
            operation=MathStepOperation.SUBSTITUTE,
            premise_claim_ids=(target.claim_id, binding.claim_id),
            proposed_conclusion=parse_math_statement("4=4"),
            substitutions={"x": IntegerExpression(3)},
        )
        self.assertTrue(check_math_step(substitution, (target, binding)).accepted)

    def test_transitivity_fails_closed_on_undefined_middle_path(self) -> None:
        undefined = DivideExpression(IntegerExpression(1), IntegerExpression(0))
        first = MathClaim.create(
            statement=MathStatement(undefined, MathRelation.EQUAL, VariableExpression("b")),
            status=MathClaimStatus.GIVEN,
            provenance=(Provenance("fixture", "undefined_transitivity"),),
        )
        second = given("b=c", ("b", "c"))
        proposal = MathStepProposal.create(
            operation=MathStepOperation.TRANSITIVE_EQUAL,
            premise_claim_ids=(first.claim_id, second.claim_id),
            proposed_conclusion=MathStatement(
                undefined,
                MathRelation.EQUAL,
                VariableExpression("c"),
            ),
        )
        receipt = check_math_step(proposal, (first, second))
        self.assertFalse(receipt.accepted)
        self.assertEqual(receipt.rejection_code, MathRejectionCode.UNDISCHARGED_GUARD)

    def test_checked_premise_requires_reexecuted_derivation_registry(self) -> None:
        result = solve_linear_equation("2*x=8", "x")
        derived = next(
            claim for claim in result.claims if claim.status is MathClaimStatus.DERIVED
        )
        proposal = MathStepProposal.create(
            operation=MathStepOperation.SIMPLIFY_EXACT,
            premise_claim_ids=(derived.claim_id,),
            proposed_conclusion=derived.statement,
        )
        claims = {claim.claim_id: claim for claim in result.claims}
        missing = check_math_step(proposal, claims)
        self.assertFalse(missing.accepted)
        self.assertEqual(missing.rejection_code, MathRejectionCode.UNVERIFIED_PREMISE)

        derivations = {
            step.receipt.receipt_id: (step.proposal, step.receipt)
            for step in result.checked_steps
            if step.receipt.accepted
        }
        accepted = check_math_step(proposal, claims, derivations)
        self.assertTrue(accepted.accepted, accepted.detail)

    def test_nonterminal_receipt_cannot_authorize_verified_status(self) -> None:
        result = solve_linear_equation("2*x=8", "x")
        simplify_step = next(
            step
            for step in result.checked_steps
            if step.proposal.operation is MathStepOperation.SIMPLIFY_EXACT
        )
        forged_verified = MathClaim._from_checked_receipt(
            receipt=simplify_step.receipt,
            status=MathClaimStatus.VERIFIED,
        )
        claims = {claim.claim_id: claim for claim in result.claims}
        claims[forged_verified.claim_id] = forged_verified
        derivations = {
            step.receipt.receipt_id: (step.proposal, step.receipt)
            for step in result.checked_steps
            if step.receipt.accepted
        }
        proposal = MathStepProposal.create(
            operation=MathStepOperation.SIMPLIFY_EXACT,
            premise_claim_ids=(forged_verified.claim_id,),
            proposed_conclusion=forged_verified.statement,
        )
        receipt = check_math_step(proposal, claims, derivations)
        self.assertFalse(receipt.accepted)
        self.assertEqual(receipt.rejection_code, MathRejectionCode.UNVERIFIED_PREMISE)

    def test_checked_claim_binds_exact_assumption_closure(self) -> None:
        assumption = MathClaim.create(
            statement=parse_math_statement("x=1", declared_variables=("x",)),
            status=MathClaimStatus.ASSUMED,
            provenance=(Provenance("fixture", "declared_assumption"),),
        )
        proposal = MathStepProposal.create(
            operation=MathStepOperation.SIMPLIFY_EXACT,
            premise_claim_ids=(assumption.claim_id,),
            proposed_conclusion=assumption.statement,
        )
        receipt = check_math_step(proposal, (assumption,))
        self.assertTrue(receipt.accepted)
        with self.assertRaises(MathContractError):
            issue_checked_math_claim(
                proposal=proposal,
                claims=(assumption,),
                receipt=receipt,
                status=MathClaimStatus.DERIVED,
                assumption_claim_ids=(),
            )
        derived = issue_checked_math_claim(
            proposal=proposal,
            claims=(assumption,),
            receipt=receipt,
            status=MathClaimStatus.DERIVED,
            assumption_claim_ids=(assumption.claim_id,),
        )
        self.assertEqual(derived.assumption_claim_ids, (assumption.claim_id,))

    def test_deep_derivation_fails_with_budget_receipt_not_recursion_error(self) -> None:
        current = given("x=1", ("x",))
        claims = {current.claim_id: current}
        derivations = {}
        terminal_receipt = None
        for _ in range(MATH_MAX_DERIVATION_DEPTH + 2):
            proposal = MathStepProposal.create(
                operation=MathStepOperation.SIMPLIFY_EXACT,
                premise_claim_ids=(current.claim_id,),
                proposed_conclusion=current.statement,
            )
            receipt = check_math_step(proposal, claims, derivations)
            if not receipt.accepted:
                terminal_receipt = receipt
                break
            current = issue_checked_math_claim(
                proposal=proposal,
                claims=claims,
                receipt=receipt,
                status=MathClaimStatus.DERIVED,
                derivations=derivations,
            )
            derivations[receipt.receipt_id] = (proposal, receipt)
            claims[current.claim_id] = current
        self.assertIsNotNone(terminal_receipt)
        self.assertEqual(
            terminal_receipt.rejection_code,
            MathRejectionCode.BUDGET_EXHAUSTED,
        )

    def test_linear_solution_rule_rejects_nonlinear_single_root(self) -> None:
        nonlinear = given("x*x=4", ("x",))
        proposal = MathStepProposal.create(
            operation=MathStepOperation.VERIFY_LINEAR_SOLUTION,
            premise_claim_ids=(nonlinear.claim_id,),
            proposed_conclusion=parse_math_statement("x=2", declared_variables=("x",)),
            branch_id=MATH_BRANCH_ID,
            theory_id=MATH_THEORY_ID,
        )
        receipt = check_math_step(proposal, (nonlinear,))
        self.assertFalse(receipt.accepted)
        self.assertEqual(receipt.rejection_code, MathRejectionCode.NEEDS_CAPABILITY)

    def test_conjecture_cannot_support_a_verified_step(self) -> None:
        conjecture = MathClaim.create(
            statement=parse_math_statement("x=1", declared_variables=("x",)),
            status=MathClaimStatus.CONJECTURED,
            provenance=(Provenance("generator", "candidate_1"),),
        )
        proposal = MathStepProposal.create(
            operation=MathStepOperation.SIMPLIFY_EXACT,
            premise_claim_ids=(conjecture.claim_id,),
            proposed_conclusion=conjecture.statement,
        )
        receipt = check_math_step(proposal, (conjecture,))
        self.assertFalse(receipt.accepted)
        self.assertEqual(receipt.rejection_code, MathRejectionCode.INVALID_TRANSFORMATION)

    def test_proposal_wire_cannot_smuggle_verified_flag(self) -> None:
        premise = given("x=1", ("x",))
        proposal = MathStepProposal.create(
            operation=MathStepOperation.SIMPLIFY_EXACT,
            premise_claim_ids=(premise.claim_id,),
            proposed_conclusion=premise.statement,
        ).to_dict()
        proposal["verified"] = True
        with self.assertRaises(MathContractError):
            MathStepProposal.from_dict(proposal)


class MathEngineAndCounterexampleTests(unittest.TestCase):
    def test_linear_solver_emits_checked_exact_proof(self) -> None:
        cases = {
            "2*(x+3)=14": ExactRational(4),
            "3*x-5=10": ExactRational(5),
            "2*x+1=x+4": ExactRational(3),
            "x/3=1/2": ExactRational(3, 2),
            "-2*x=3": ExactRational(-3, 2),
        }
        for notation, expected in cases.items():
            with self.subTest(notation=notation):
                result = solve_linear_equation(notation, "x")
                self.assertEqual(result.terminal_status, MathTerminalStatus.VERIFIED)
                self.assertEqual(result.solution, expected)
                self.assertTrue(result.checked_steps)
                self.assertTrue(all(step.receipt.accepted for step in result.checked_steps))
                self.assertEqual(result.claims[-1].status, MathClaimStatus.VERIFIED)
                self.assertTrue(verify_math_result(result.to_dict()).valid)

    def test_solver_distinguishes_identity_contradiction_and_missing_capability(self) -> None:
        self.assertEqual(
            solve_linear_equation("0*x=0", "x").terminal_status,
            MathTerminalStatus.UNDERDETERMINED,
        )
        self.assertEqual(
            solve_linear_equation("0*x=3", "x").terminal_status,
            MathTerminalStatus.NO_SOLUTION,
        )
        self.assertEqual(
            solve_linear_equation("x*x=4", "x").terminal_status,
            MathTerminalStatus.NEEDS_CAPABILITY,
        )
        self.assertEqual(
            solve_linear_equation("x/0=2", "x").terminal_status,
            MathTerminalStatus.NEEDS_GUARD,
        )

    def test_math_result_tampering_fails_semantic_reexecution(self) -> None:
        bundle = solve_linear_equation("2*x=8", "x").to_dict()
        tampered = copy.deepcopy(bundle)
        tampered["solution"] = {"numerator": 5, "denominator": 1}
        self.assertFalse(verify_math_result(tampered).valid)

    def test_counterexample_search_is_exact_bounded_and_deterministic(self) -> None:
        statement = parse_math_statement("x*x<5", declared_variables=("x",))
        bounds = (CounterexampleBounds("x", -3, 3),)
        first = search_math_counterexample(statement, bounds)
        second = search_math_counterexample(statement, bounds)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.status, CounterexampleStatus.FOUND)
        self.assertEqual(first.assignment, (("x", -3),))
        self.assertEqual(first.exact_left, ExactRational(9))
        self.assertEqual(first.exact_right, ExactRational(5))
        self.assertTrue(verify_counterexample_result(first.to_dict()).valid)

        tampered = copy.deepcopy(first.to_dict())
        tampered["assignment"] = [["x", 2]]
        self.assertFalse(verify_counterexample_result(tampered).valid)

    def test_no_counterexample_within_bounds_is_explicitly_not_proof(self) -> None:
        statement = parse_math_statement("x=x", declared_variables=("x",))
        result = search_math_counterexample(
            statement,
            (CounterexampleBounds("x", -2, 2),),
        )
        self.assertEqual(result.status, CounterexampleStatus.NONE_WITHIN_BOUNDS)
        self.assertIn("not a proof", result.detail)

    def test_counterexample_guard_and_budget_fail_closed(self) -> None:
        undefined = search_math_counterexample(
            parse_math_statement("1/x<2", declared_variables=("x",)),
            (CounterexampleBounds("x", -1, 1),),
        )
        self.assertEqual(undefined.status, CounterexampleStatus.NEEDS_GUARD)
        exhausted = search_math_counterexample(
            parse_math_statement("x=x", declared_variables=("x",)),
            (CounterexampleBounds("x", -5, 5),),
            max_assignments=2,
        )
        self.assertEqual(exhausted.status, CounterexampleStatus.BUDGET_EXHAUSTED)
        self.assertEqual(exhausted.tested_assignments, 2)

        huge_lazy_domain = search_math_counterexample(
            parse_math_statement("x=x", declared_variables=("x",)),
            (CounterexampleBounds("x", -250_000, 250_000),),
            max_assignments=1,
        )
        self.assertEqual(
            huge_lazy_domain.status,
            CounterexampleStatus.BUDGET_EXHAUSTED,
        )
        self.assertEqual(huge_lazy_domain.tested_assignments, 1)


if __name__ == "__main__":
    unittest.main()
