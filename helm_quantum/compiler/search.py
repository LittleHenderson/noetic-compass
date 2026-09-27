"""Bounded amplitude amplification over a compiled predicate, on the local simulator.

Schedule: Boyer-Brassard-Hoyer-Tapp (BBHT) for an unknown number of marked
states t. Round r draws j uniformly from [0, floor(m_r)), applies j Grover
iterations to the uniform superposition, measures the selection register, and
checks the sample with the compiled circuit itself (classical basis execution
of the same gates). On failure m grows by 6/5, capped at sqrt(N). Nothing in
this module reads t, a solution list, or an evaluator; the schedule constants
are fixed here and are not tuned from observed counts.

Assumptions and limits (stated, not hidden):
  * Ideal, noiseless dense simulation; N = 4**L selection states.
  * BBHT (Theorem 3): for 1 <= t <= 3N/4 the expected number of Grover
    iterations before success is at most 4.5 * sqrt(N / t); for t > 3N/4 a
    j = 0 round (always the first) already succeeds with probability >= 3/4.
  * With an oracle-call budget B, Markov's inequality gives
    P(no candidate | t >= 1) <= E[calls] / B; this is loose. For the 64-state
    fixture the default budget equals the 64 predicate evaluations exhaustive
    classical evaluation would need, so no speed claim follows from this code.
  * For t = 0 no candidate can ever be found; the run ends at the budget with
    NO_CANDIDATE_WITHIN_BUDGET, which is NOT UNSAT_PROVED.
  * Each classical check of a sampled program is counted as one oracle call.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

from ..wire import Record, require
from .ir import Circuit, Gate
from .predicate import CompiledPredicate
from .resources import ResourceModel, SimulationBudget, admit_simulation
from .sim import StateVector

SCHEDULE = {"name": "BBHT", "m_initial": 1.0, "lambda": 1.2, "m_cap": "sqrt(N)",
            "j_draw": "uniform integer in [0, floor(m))", "tuned_from_solution_count": False}

STATUS_CANDIDATE = "CANDIDATE_SAMPLED"
STATUS_NO_CANDIDATE = "NO_CANDIDATE_WITHIN_BUDGET"
STATUS_WALL = "STOPPED_AT_WALL_TIME"
INTERPRETATION = ("a sampled candidate is unverified until the independent verifier recomputes it; "
                  "no candidate within the budget is not a proof of unsatisfiability (not UNSAT_PROVED)")


def uniform_preparation(pred: CompiledPredicate) -> Circuit:
    c = Circuit(pred.layout.total)
    c.extend(Gate("H", q, label="uniform selection") for q in pred.layout.selection)
    return c


def diffusion(pred: CompiledPredicate) -> Circuit:
    """H X (MCZ on selection) X H  ==  -(2|s><s| - I) on the selection register."""
    sel = pred.layout.selection
    c = Circuit(pred.layout.total)
    c.extend(Gate("H", q, label="diffusion") for q in sel)
    c.extend(Gate("X", q, label="diffusion") for q in sel)
    c.append(Gate("Z", sel[-1], tuple(sel[:-1]), (), "diffusion reflect |0..0>"))
    c.extend(Gate("X", q, label="diffusion") for q in sel)
    c.extend(Gate("H", q, label="diffusion") for q in sel)
    return c


def amplified_state(pred: CompiledPredicate, iterations: int, budget: SimulationBudget) -> StateVector:
    """Uniform selection state followed by `iterations` Grover iterations. Admission first."""
    require(type(iterations) is int and iterations >= 0, "iterations must be a non-negative integer")
    admit_simulation(pred, budget)
    state = StateVector(pred.layout.total).run(uniform_preparation(pred))
    d = diffusion(pred)
    for _ in range(iterations):
        state.run(pred.circuit)
        state.run(d)
    return state


@dataclass(frozen=True)
class SearchOutcome(Record):
    schema: str
    status: str
    program: tuple | None
    oracle_calls: int
    rounds: int
    iterations_per_round: tuple
    samples: tuple
    schedule: dict
    seed: int
    elapsed_ns: int
    gates_applied: int
    circuit_digest: str
    interpretation: str
    execution_kind: str
    resource_model: ResourceModel


def bounded_search(pred: CompiledPredicate, budget: SimulationBudget) -> SearchOutcome:
    require(type(pred) is CompiledPredicate and type(budget) is SimulationBudget, "typed inputs required")
    model = admit_simulation(pred, budget)
    rng = random.Random(budget.seed)
    n_sel = len(pred.layout.selection)
    sqrt_n = math.sqrt(1 << n_sel)
    d = diffusion(pred)
    prep = uniform_preparation(pred)
    start = time.perf_counter_ns()
    deadline = start + budget.max_wall_ms * 1_000_000
    m = SCHEDULE["m_initial"]
    calls = 0
    rounds = 0
    gates = 0
    iterations = []
    samples = []
    status = STATUS_NO_CANDIDATE
    program = None
    while True:
        j = rng.randrange(max(1, int(math.floor(m))))
        if calls + j + 1 > budget.max_oracle_calls:
            status = STATUS_NO_CANDIDATE
            break
        if time.perf_counter_ns() > deadline:
            status = STATUS_WALL
            break
        state = StateVector(pred.layout.total).run(prep)
        for _ in range(j):
            state.run(pred.circuit)
            state.run(d)
        calls += j
        rounds += 1
        iterations.append(j)
        index = state.sample(rng)
        gates += state.gates_applied
        candidate = pred.layout.decode_index(index)
        samples.append("".join(str((index >> q) & 1) for q in pred.layout.selection))
        calls += 1  # the classical check below evaluates the compiled predicate once
        if pred.marks(candidate):
            status = STATUS_CANDIDATE
            program = candidate
            break
        m = min(SCHEDULE["lambda"] * m, sqrt_n)
    return SearchOutcome(
        schema="helm-q1-compiler-search-outcome/1", status=status, program=program,
        oracle_calls=calls, rounds=rounds, iterations_per_round=tuple(iterations),
        samples=tuple(samples), schedule=dict(SCHEDULE), seed=budget.seed,
        elapsed_ns=time.perf_counter_ns() - start, gates_applied=gates,
        circuit_digest=pred.circuit_digest, interpretation=INTERPRETATION,
        execution_kind="LOCAL_IDEAL_SIMULATION", resource_model=model)
