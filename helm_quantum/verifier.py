"""Independent behavior checker; no helper, search result, or compiler import."""
from __future__ import annotations

from .contracts import QuantumProblem, QuantumProposal, QuantumVerification, validate_program
from .wire import require


def direct_outputs(program: tuple[int, ...]) -> tuple[int, ...]:
    validate_program(program)
    result = []
    for value in (0, 1, 2, 3):
        for operation in program:
            if operation == 0:
                pass
            elif operation == 1:
                value = (value + 1) & 3
            elif operation == 2:
                value = (value - 1) & 3
            else:
                value = value ^ 3
        result.append(value)
    return tuple(result)


def verify(problem: QuantumProblem, proposal: QuantumProposal) -> QuantumVerification:
    problem.assert_current()
    proposal.__post_init__()
    require(proposal._problem is problem, "proposal belongs to another problem object")
    outputs = direct_outputs(proposal.program)
    accepted = outputs == problem.target_outputs
    disposition = ("REJECTED" if not accepted else {
        "disabled": "VERIFIED_OFFLINE_ONLY", "shadow": "VERIFIED_SHADOW_ONLY",
        "research": "VERIFIED_RESEARCH_CANDIDATE"}[problem.mode])
    return QuantumVerification(
        schema="helm-q1-verification/1", problem_digest=problem.problem_digest,
        binding=problem.binding, mode=problem.mode, program=proposal.program,
        verifier_digest=problem.verifier_digest, outputs=outputs, inputs_checked=4,
        accepted=accepted, disposition=disposition, retained=False,
        _admission=problem._admission, _problem=problem)


def propose(problem: QuantumProblem, program: tuple[int, ...]) -> QuantumProposal:
    return QuantumProposal(schema="helm-q1-proposal/1", problem_digest=problem.problem_digest,
                           binding=problem.binding, mode=problem.mode, program=program,
                           origin="offline-classical", _admission=problem._admission,
                           _problem=problem)
