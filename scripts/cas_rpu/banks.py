"""The reasoning banks — ^8 surfaces, ^6 takes apart, ^9 lands.

The single most load-bearing correction in the sources is that **association
is not deduction**. `^8` Above/Cause is associative triggering: "that reminds
me", "one thing leads to another". Deductive work is a compound of `^6` Male
(decomposition into constituents) and `^9` Below/Effect (landing on the
conclusion). The PCBA book names the failure directly:

    "^8^C_{F2}|A -> ^9^C_{F2}|A is the cognitive short circuit. It jumps
    straight from the Above/Cause trigger to the Below/Effect result with no
    intermediate processing ... the answer is produced without doing the
    cognitive work that would make it sound."
                                        -- CAS PCBA Engineer, answer 1.2

So the three are separate banks here, and `ShortCircuit` is a refusal, not a
warning. A machine wired `^8 -> ^9` would be fluent and quietly skip the middle
-- an intuition engine wearing a reasoner's clothes.

The three gain regimes
----------------------
Gain is amplification, never correctness, so each bank gets the gain its job
can justify:

    ^8 generation    beta > 1     moderate. Too little is tunnel vision; too
                                  much is a fireworks factory of tangents.
    ^6 decomposition beta == 1    UNITY. The truth firewall. Gain above one
                                  exaggerates evidence and below one suppresses
                                  it; either way the stage stops reporting what
                                  is there. Enforced, not advised.
    ^9 inference     beta == 1    unity, for the same reason.

`UnityGainRequired` is raised at construction. A board that evaluates at gain
does not reason -- it converts Desire into justification.

Scale
-----
Every spec here declares `Scale.UNIT`, so `sat` and `cutoff` live in (0,1] and
[0,1). The default V and R are chosen to put `I = V/R` near 0.4-0.5 and the
effect proxy `E* = beta*I` inside the active band. Feeding these unit-scale
specs the design-scale numbers from the Guide's p.12 worked example (V=8,
R=2) pins every stage at saturation -- that is Preserved Conflict 3.1 biting,
and the cure is to keep the two normalisations apart rather than to widen sat.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ccb_r1"))

from cjt_sim import CjtSpec, Reading, Region, Scale, measure  # noqa: E402

from workspace import (  # noqa: E402
    Pattern,
    Proposition,
    Status,
    Workspace,
    chain_patterns,
)

#: Unity gain is exact. A stage at 1.02 is a stage that exaggerates by 2%.
UNITY = 1.0


class BankError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class Candidate:
    """A route `^8` surfaced: an ordered list of nodes, not yet a conclusion.

    `support` is empty at birth and stays empty until `^6` finds the premises
    that would carry it. A candidate is a question, not an answer.
    """

    label: str
    nodes: tuple[str, ...]
    relation: str
    origin: str = "^8"

    @property
    def hops(self) -> int:
        return max(0, len(self.nodes) - 1)

    def links(self) -> tuple[tuple[str, str], ...]:
        return tuple((self.nodes[i], self.nodes[i + 1]) for i in range(self.hops))

    def __str__(self) -> str:
        return " -> ".join(self.nodes)


@dataclass(frozen=True)
class Decomposition:
    """What `^6` found when it took a candidate apart.

    `missing` is the whole point. A candidate whose constituents are not all
    present does not fail silently: the gap is named, and the runtime turns it
    into an RPM sub-goal rather than a guess.
    """

    candidate: Candidate
    required: tuple[str, ...]
    present: tuple[str, ...]
    missing: tuple[str, ...]
    reading: Reading

    @property
    def complete(self) -> bool:
        return not self.missing


@dataclass(frozen=True)
class Inference:
    """What `^9` landed on, and what it rests on."""

    conclusion: Proposition | None
    verdict: str  # YES | UNKNOWN | REFUSED
    support: tuple[str, ...]
    reading: Reading
    note: str = ""


# ---- ^8 Above/Cause --------------------------------------------------------

class HypothesisBank:
    """`^8` — surfaces candidate routes by association. It cannot conclude.

    There is no method here that returns a verdict, and that absence is the
    design: the bank's entire output type is `Candidate`. Association cannot
    reach a conclusion because association has no way to express one.
    """

    def __init__(self, beta: float = 1.8, *, cutoff: float = 0.05, sat: float = 0.95) -> None:
        if beta <= UNITY:
            raise BankError(
                "E-BANK-001",
                f"^8 generation runs above unity gain; beta={beta} would surface nothing new",
            )
        self.spec = CjtSpec(
            label="^8 hypothesis",
            beta=beta,
            cutoff=cutoff,
            sat=sat,
            bias="associative memory + current goal",
            scale=Scale.UNIT,
            bias_domain="C",
            target_domain="C",
        )

    def surface(
        self,
        ws: Workspace,
        source: str,
        target: str,
        relation: str,
        *,
        v: float = 1.2,
        r_total: float = 3.0,
        max_hops: int = 6,
        limit: int = 8,
        associate_across: bool = True,
    ) -> tuple[list[Candidate], Reading]:
        """Walk outward from `source`, collecting routes that reach `target`.

        **Association does not respect relation type.** With `associate_across`
        set -- the default -- the walk follows *any* edge between two nodes,
        not only edges of the queried relation. That is what "one thing leads
        to another" actually licenses: the fact that A is connected to B makes
        B come to mind, whatever the connection was.

        The consequence is the point. A route surfaced through a `co_occurs`
        edge is a genuine candidate and a genuine possible error, so `^6` has
        real work to do and can genuinely fail. Restricting the walk to the
        queried relation would make `^8` verify its own output and reduce `^6`
        to a rubber stamp -- the trigger would be doing the deduction, which is
        precisely the short circuit this design exists to prevent.

        Set `associate_across=False` only to demonstrate that defect.
        """
        reading = measure(self.spec, v, r_total)
        if reading.region is Region.CUTOFF:
            return [], reading

        edges: dict[str, list[str]] = {}
        for prop in ws.assertive():
            if prop.negated:
                continue
            if associate_across or prop.relation == relation:
                edges.setdefault(prop.subject, []).append(prop.obj)
        for node in edges:
            edges[node] = sorted(dict.fromkeys(edges[node]))

        found: list[Candidate] = []
        stack: list[tuple[str, tuple[str, ...]]] = [(source, (source,))]
        while stack and len(found) < limit:
            node, path = stack.pop(0)
            if len(path) - 1 >= max_hops:
                continue
            for nxt in edges.get(node, []):
                if nxt in path:
                    continue  # a cycle is not a route
                route = path + (nxt,)
                if nxt == target:
                    found.append(
                        Candidate(f"c{len(found):02d}", route, relation)
                    )
                    if len(found) >= limit:
                        break
                else:
                    stack.append((nxt, route))

        # Saturation is real: a bank pinned at its ceiling stops surfacing more.
        if reading.region is Region.SATURATION:
            found = found[: max(1, limit // 2)]

        for cand in found:
            ws.hypothesize(cand.nodes[0], relation, cand.nodes[-1], stage="^8")
        return found, reading


# ---- ^6 Male ---------------------------------------------------------------

class DecompositionBank:
    """`^6` — takes a candidate apart into the constituents it would need.

    Unity gain, enforced. This is the truth firewall: the stage that reports
    what is actually there, neither amplified nor suppressed. Ambition may
    have chosen this candidate; it does not get to decide what the candidate
    is made of.
    """

    def __init__(self, *, cutoff: float = 0.05, sat: float = 0.95) -> None:
        self.spec = CjtSpec(
            label="^6 decomposition",
            beta=UNITY,
            cutoff=cutoff,
            sat=sat,
            bias="constitution + premise set",
            scale=Scale.UNIT,
            bias_domain="P",
            target_domain="E",
        )

    @staticmethod
    def guard_unity(beta: float) -> None:
        if beta != UNITY:
            raise BankError(
                "E-BANK-002",
                f"^6 evaluation must run at unity gain; beta={beta} exaggerates "
                "or suppresses the evidence it was built to report",
            )

    def decompose(
        self, ws: Workspace, candidate: Candidate, *, v: float = 2.5, r_total: float = 5.0
    ) -> Decomposition:
        """Name every link the route requires, and which of them the premises carry.

        The workspace is *asked* for each link even when the answer is already
        obvious, because asking is what records a lacuna. A link that is not
        there becomes a named gap, and a named gap can become a sub-goal.
        """
        self.guard_unity(self.spec.beta)
        reading = measure(self.spec, v, r_total)

        required: list[str] = []
        present: list[str] = []
        missing: list[str] = []
        for left, right in candidate.links():
            key = f"{left}|{candidate.relation}|{right}"
            required.append(key)
            if ws.ask(left, candidate.relation, right) == "YES":
                present.append(key)
            else:
                missing.append(key)

        if reading.region is Region.CUTOFF:
            # A silent stage found nothing; it must not report a clean bill.
            missing = required[:]
            present = []

        return Decomposition(
            candidate=candidate,
            required=tuple(required),
            present=tuple(present),
            missing=tuple(missing),
            reading=reading,
        )

    def decompose_query(
        self, ws: Workspace, source: str, target: str, relation: str, hops: int
    ) -> list[dict[str, str]]:
        """The conjunctive form: what bindings would satisfy an `hops`-link chain.

        Used when no candidate has been surfaced and the processor needs to ask
        the premise set directly what shape an answer would have.
        """
        patterns = chain_patterns(relation, hops, source)
        bound = [p.bind({"?z": target}) if p.obj == "?z" else p for p in patterns]
        return ws.match_all(bound)


# ---- ^9 Below/Effect -------------------------------------------------------

class InferenceBank:
    """`^9` — lands the conclusion the decomposition supports, or declines.

    Unity gain. The bank has exactly one way to produce a positive conclusion:
    a complete decomposition whose every constituent is assertively held. It
    cannot be reached from `^8` directly (`ShortCircuit`), and it cannot rest
    on a hypothesis (`Workspace.derive` refuses).
    """

    def __init__(self, *, cutoff: float = 0.05, sat: float = 0.95) -> None:
        self.spec = CjtSpec(
            label="^9 inference",
            beta=UNITY,
            cutoff=cutoff,
            sat=sat,
            bias="derivation rules + world assumption",
            scale=Scale.UNIT,
            bias_domain="C",
            target_domain="C",
        )

    def land(
        self,
        ws: Workspace,
        decomposition: Decomposition,
        *,
        v: float = 1.0,
        r_total: float = 2.0,
    ) -> Inference:
        """Turn a complete decomposition into a derived conclusion.

        An incomplete one yields `UNKNOWN` under an open world and `NO` under a
        closed one -- the decision is the workspace's world assumption, not this
        bank's mood.
        """
        DecompositionBank.guard_unity(self.spec.beta)
        reading = measure(self.spec, v, r_total)
        candidate = decomposition.candidate

        if reading.region is Region.CUTOFF:
            return Inference(None, "UNKNOWN", (), reading, "^9 in cutoff: nothing landed")

        if not decomposition.complete:
            verdict = "NO" if ws.closed_world else "UNKNOWN"
            return Inference(
                None,
                verdict,
                (),
                reading,
                f"{len(decomposition.missing)} constituent(s) unsupported: "
                + ", ".join(decomposition.missing),
            )

        conclusion = ws.derive(
            candidate.nodes[0],
            candidate.relation,
            candidate.nodes[-1],
            tuple(decomposition.present),
            stage="^9",
            cas="^9^C_{F2}|A",
        )
        return Inference(conclusion, "YES", tuple(decomposition.present), reading)


# ---- the wiring law --------------------------------------------------------

@dataclass
class BankTrace:
    """Which banks fired, in order. The short-circuit detector reads this."""

    stages: list[str] = field(default_factory=list)

    def fire(self, stage: str) -> None:
        if stage == "^9" and self.stages:
            last_reasoning = [s for s in self.stages if s in ("^8", "^6", "^9")]
            if last_reasoning and last_reasoning[-1] == "^8":
                raise BankError(
                    "E-BANK-003",
                    "^8 -> ^9 is the cognitive short circuit: the trigger reached "
                    "the result with no ^6 decomposition between them. The answer "
                    "would be produced without the work that makes it sound.",
                )
        self.stages.append(stage)

    def reset(self) -> None:
        self.stages.clear()
