"""Bounded baselines. Evaluator code: forbidden as an input to the compiler."""
from __future__ import annotations

import itertools
import random
import time
from dataclasses import dataclass
from uuid import uuid4

from .contracts import QuantumProblem, QuantumProposal, QuantumRunReceipt
from .vendor.q1_tools import run_program
from .verifier import propose, verify
from .wire import ContractError, Record, digest, integer, require


@dataclass(frozen=True)
class SearchResult(Record):
    method: str
    status: str
    proposal: QuantumProposal | None
    receipt: QuantumRunReceipt
    proof: str | None
    transitions: int
    seed: int | None


class SearchBudgetExhausted(ContractError):
    pass


class _Budget:
    def __init__(self, problem):
        self.problem = problem
        self.start = time.perf_counter_ns()
        self.candidates = 0
        self.transitions = 0

    def tick(self, *, candidate=False, transitions=0):
        self.problem.assert_current()
        if time.perf_counter_ns() - self.start >= self.problem.limits.max_wall_ms * 1_000_000:
            raise SearchBudgetExhausted("offline search wall-time exhausted")
        if candidate:
            if self.candidates >= self.problem.limits.max_programs:
                raise SearchBudgetExhausted("candidate budget exhausted")
            self.candidates += 1
        if self.transitions + transitions > self.problem.limits.max_transitions:
            raise SearchBudgetExhausted("transition budget exhausted")
        self.transitions += transitions


def search(problem: QuantumProblem, method: str = "exhaustive", *,
           samples: int = 64, seed: int = 0) -> SearchResult:
    problem.assert_current()
    require(method in ("exhaustive", "structured", "uniform"), "unknown baseline")
    integer(samples, 1, problem.limits.max_programs, "samples")
    integer(seed, 0, 2**32 - 1, "seed")
    budget = _Budget(problem)
    candidate = None
    complete = False
    proof = None
    exhausted = False
    try:
        if method == "structured":
            # Identical prefix transformations have identical possible suffixes.
            # Retain one witness per transformation, preserving exact length.
            frontier = {(0, 1, 2, 3): ()}
            for _ in range(problem.program_length):
                next_frontier = {}
                for outputs, prefix in frontier.items():
                    for op in range(4):
                        budget.tick(transitions=4)
                        transformed = tuple(run_program((op,), x) for x in outputs)
                        next_frontier.setdefault(transformed, prefix + (op,))
                frontier = next_frontier
            for outputs, program in frontier.items():
                budget.tick(candidate=True)
                if outputs == problem.target_outputs:
                    candidate = program
            complete = True
            if candidate is None:
                proof = "complete reachable-transform dynamic program at exact length three"
        else:
            rng = random.Random(seed)
            programs = (itertools.product(range(4), repeat=3) if method == "exhaustive"
                        else (tuple(rng.randrange(4) for _ in range(3)) for _ in range(samples)))
            for program in programs:
                budget.tick(candidate=True, transitions=12)
                outputs = tuple(run_program(program, x) for x in problem.domain)
                if outputs == problem.target_outputs and candidate is None:
                    candidate = program
            complete = method == "exhaustive"
            if complete and candidate is None:
                proof = "all 64 programs evaluated over all four inputs"
    except SearchBudgetExhausted:
        # A typed budget result is permitted only while the admission is current.
        problem.assert_current()
        exhausted = True
    proposal = propose(problem, candidate) if candidate is not None else None
    if proposal is not None:
        require(verify(problem, proposal).accepted, "reference and independent verifier disagree")
        status = "VALID_CANDIDATE"
    elif complete:
        status = "UNSAT_PROVED"
        if len(set(problem.target_outputs)) < 4:
            proof += "; compositions of ID/INC/DEC/NOT2 are bijective; target is not"
    else:
        status = "NO_CANDIDATE_WITHIN_BUDGET"
    receipt = QuantumRunReceipt(
        schema="helm-q1-receipt/1", run_id=str(uuid4()), problem_digest=problem.problem_digest,
        proposal_digest=digest(proposal) if proposal is not None else None,
        binding=problem.binding, mode=problem.mode, requested_backend="offline-classical",
        actual_backend="offline-classical", execution_kind="CLASSICAL_OFFLINE",
        device_properties_digest=None, native_circuit_digest=None,
        compilation_settings=(), measurement_order="NOT_APPLICABLE", shots=0,
        observed_counts=(), job_ids=(), elapsed_ns=time.perf_counter_ns() - budget.start,
        candidates_checked=budget.candidates, quote_id=None, estimated_charges_usd="0.00",
        reconciled_charges_usd=None, status="BUDGET_EXHAUSTED" if exhausted else "COMPLETED",
        _admission=problem._admission, _problem=problem, _proposal=proposal)
    return SearchResult(method, status, proposal, receipt, proof, budget.transitions,
                        seed if method == "uniform" else None)
