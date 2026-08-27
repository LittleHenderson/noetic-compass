"""CCB-R1's own arm — the board-side adapter for Stage 5.

`runners.py` gets an answer out of a language model. This gets one out of the
board, in the same `Outcome` shape, so the two arms are comparable item for
item.

Three paths, one per criterion:

  deduction  reachability over the premise graph, verified through the RPM
             planner, under a CLOSED-world reading: the premise set is
             complete, so not-derivable is a legitimate NO.
  honesty    the same reachability under an OPEN-world reading: the premise set
             is declared partial, so not-derivable is NEEDS_INFORMATION, never
             NO. This is the whole distinction M1 measures.
  firewall   a rating computed from evidence alone. Identity is not a parameter
             of `rate_case`; there is no argument through which it could reach
             the conclusion.

**On how much of this is RPM.** The planner verifies a *candidate chain* — it
descends first-unmet-prerequisite with a depth bound, exactly as specified. It
does not search: `first_block` short-circuits on one prerequisite and
`subgoals` maps one sub-goal per (goal, prerequisite), so a branching graph has
no representation inside a single descent. The search over candidate paths is
therefore explicit and sits outside the planner, in `_candidate_paths`. Saying
otherwise would overstate what the RPM machinery is doing here.

**Read `docs/working/ccb_r1_stage5_construct_validity_2026_08_27.md` before
reading any Stage 5 result produced with this adapter.** Every path below is
correct by construction, and a trivial control (`b4_trivial_solver`) scores
identically — which bounds what a passing Stage 5 can be claimed to show.
"""

from __future__ import annotations

from dataclasses import dataclass

from flips import Outcome
from rpm import Goal, PrereqState, Prereq, RpmPlanner, Terminal
from tasksets import DeductionItem, FirewallPair, HonestyItem

__all__ = [
    "MAX_CHAIN",
    "reachable",
    "board_deduction",
    "board_honesty",
    "rate_case",
    "board_firewall_pair",
    "b4_trivial_solver",
]

#: Longest chain the board will verify. Matches RpmPlanner's default depth
#: bound: a route needing more hops than the planner can descend is not
#: something this board can claim to have derived.
MAX_CHAIN = 8

#: Scores that make a prerequisite sufficient / blocking under
#: rpm.DEFAULT_SUFFICIENCY (5.0).
_HOLDS = 10.0
_BLOCKS = 0.0


def _edges(premises) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for a, b in premises:
        graph.setdefault(a, set()).add(b)
    return graph


def _candidate_paths(graph: dict[str, set[str]], source: str, target: str,
                     limit: int = MAX_CHAIN):
    """Simple paths from source to target, shortest first, bounded by `limit`.

    Explicit because the RPM planner cannot branch — see the module docstring.
    Simple paths only: revisiting a node cannot shorten a route, and the
    planner treats a repeat as a cycle and reports NONTERMINATING.
    """
    frontier = [(source, (source,))]
    while frontier:
        node, path = frontier.pop(0)
        if len(path) > limit:
            continue
        for nxt in sorted(graph.get(node, ())):
            if nxt in path:
                continue
            extended = path + (nxt,)
            if nxt == target:
                yield extended
            else:
                frontier.append((nxt, extended))


def _chain_goals(path: tuple[str, ...], graph: dict[str, set[str]]):
    """One RPM goal per hop, chained as sub-goals of the hop before it.

    Each hop's Wisdom is "do I know this link holds" — the prerequisite that
    blocks when a premise is missing, which is what makes the honesty path's
    NEEDS_INFORMATION fall out of the planner rather than being asserted.
    """
    names = [f"reach:{path[i + 1]}:from:{path[i]}" for i in range(len(path) - 1)]
    goals = []
    for i, name in enumerate(names):
        known = path[i + 1] in graph.get(path[i], set())
        goals.append(
            Goal(
                name=name,
                d=PrereqState(_HOLDS),                       # the query is wanted
                w=PrereqState(_HOLDS if known else _BLOCKS),  # is the link known?
                p=PrereqState(_HOLDS),                       # no resource limit here
            )
        )
    subgoals = {
        (goals[i].name, Prereq.W): goals[i + 1] for i in range(len(goals) - 1)
    }
    return goals, subgoals


@dataclass(frozen=True)
class Derivation:
    reachable: bool
    terminal: Terminal
    path: tuple[str, ...] | None
    checked: int

    def summary(self) -> str:
        route = " -> ".join(self.path) if self.path else "none"
        return f"{self.terminal.value} via {route} ({self.checked} candidate(s))"


def reachable(premises, query, planner: RpmPlanner | None = None) -> Derivation:
    """Is `query` derivable from `premises`, verified chain by chain?

    Returns the first chain the planner concludes on. When no candidate
    concludes, the terminal is NEEDS_INFORMATION — a Wisdom block — which the
    two callers below read differently depending on their world assumption.
    """
    planner = planner or RpmPlanner(max_depth=MAX_CHAIN)
    graph = _edges(premises)
    source, target = query

    checked = 0
    for path in _candidate_paths(graph, source, target):
        checked += 1
        goals, subgoals = _chain_goals(path, graph)
        result = planner.run(goals[0], subgoals)
        if result.concluded:
            return Derivation(True, Terminal.CONCLUDED, path, checked)

    return Derivation(False, Terminal.NEEDS_INFORMATION, None, checked)


def board_deduction(item: DeductionItem) -> tuple[str, Outcome]:
    """Closed-world: the premise set is complete, so not-derivable means NO.

    The prompt states the premises and asks whether they *guarantee* the query.
    Under that reading a Wisdom block is not missing information — it is the
    answer.
    """
    derivation = reachable(item.syllogism.premises, item.syllogism.query)
    verdict = "YES" if derivation.reachable else "NO"
    return verdict, Outcome(Terminal.CONCLUDED, 1.0 if derivation.reachable else 0.0)


def board_honesty(item: HonestyItem) -> tuple[str, Outcome]:
    """Open-world: the premise set is declared partial, so not-derivable is UNKNOWN.

    This is the M1 claim in one line. A system that answers NO here has applied
    a closed-world assumption to an explicitly open-world premise set — which is
    the specific failure the honesty criterion measures.
    """
    derivation = reachable(item.premises, item.query)
    if derivation.reachable:
        return "YES", Outcome(Terminal.CONCLUDED, 1.0)
    return "UNKNOWN", Outcome(Terminal.NEEDS_INFORMATION)


def rate_case(evidence: dict[str, float], lo: float = 0.0, hi: float = 10.0) -> Outcome:
    """Case strength from evidence alone.

    Identity is not a parameter. The firewall is not a filter applied to a
    conclusion that saw identity — there is no argument through which identity
    could reach this computation.
    """
    if not evidence:
        return Outcome(Terminal.NEEDS_INFORMATION)
    mean = sum(evidence.values()) / len(evidence)
    return Outcome(Terminal.CONCLUDED, round(lo + mean * (hi - lo), 6))


def board_firewall_pair(pair: FirewallPair) -> tuple[Outcome, Outcome]:
    """Both halves of a pair. Identical by construction — that is the point."""
    return rate_case(pair.evidence), rate_case(pair.evidence)


# ---- B4: the control that bounds what a passing Stage 5 shows ---------------

def b4_trivial_solver(item: DeductionItem) -> bool:
    """Breadth-first reachability in a few lines. No CAS, no RPM, no board.

    B0-B2 ask whether CCB-R1's *structure* is doing the work rather than
    accident. B4 asks a harder question: whether anything specific to CAS is
    doing the work rather than plain graph search. If this scores what the board
    scores, a passing M3 is a fact about symbolic solvers, not about CAS.

    Reported alongside the board arm, always, for exactly that reason.
    """
    graph = _edges(item.syllogism.premises)
    source, target = item.syllogism.query
    seen, frontier = {source}, [source]
    while frontier:
        node = frontier.pop()
        for nxt in graph.get(node, ()):
            if nxt == target:
                return True
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return False
