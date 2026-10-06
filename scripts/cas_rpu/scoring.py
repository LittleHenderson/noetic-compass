"""Scoring — a verdict is right or wrong per probe; a lacuna set is bounded, not matched.

Contract §6 fixes the unit: the ASK probe. Every number this module produces
is a fraction of probes (or, for the withdrawn column, of mutation events),
never a fraction of items, so a class whose items carry several warm-up
probes cannot hide a diagnostic failure behind them.

Four columns, each defined on the probes where it is meaningful and left
unscored (`None`) elsewhere, so a solver is never credited for a column it
could not have got wrong:

    verdict     expected == reported                     every probe
    contested   set equality with `contested_required`   expected and got INADMISSIBLE
    named       required ⊆ reported ⊆ admissible          expected and got UNKNOWN, open world
    withdrawn   required ⊆ reported ⊆ permitted           every RETRACT / NEGATION

The two naming columns are scored only where the verdict was right: they
measure the quality of a correct answer's explanation, and a wrong verdict
is already a miss in the first column.

`named` is bounded rather than matched because the organism and the
replayer legitimately name different gaps: ^6 names the links it asked for
along the routes ^8 surfaced; the replayer names every hypothesised or
associated pair on any route. Both are correct answers to "what would close
this?" and the contract says so (§4). The lower bound defeats "name
nothing"; the upper bound defeats "name the whole frontier product".

This module knows nothing about how an answer was produced. It takes
`Probe`s -- adapters turn an `Organism`'s responses or a control's run into
them -- and `StreamItem`-shaped expectations, duck-typed on the field names
contract §2–§5 fix, so it can be tested on hand-built stand-ins before the
generator exists and binds to the real one when it lands.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

YES, NO, UNKNOWN, INADMISSIBLE = "YES", "NO", "UNKNOWN", "INADMISSIBLE"
VERDICTS = (YES, NO, UNKNOWN, INADMISSIBLE)
COLUMNS = ("verdict", "contested", "named", "withdrawn")
CLASSES = ("R", "H", "C", "N")


class ScoringError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Probe:
    """One answered ASK, however it was answered."""

    event_index: int
    verdict: str
    lacunae: tuple[str, ...] = ()
    contested: tuple[str, ...] = ()
    work: int = 0


@dataclass(frozen=True)
class WithdrawnReport:
    """What a solver said fell at one RETRACT / NEGATION event."""

    event_index: int
    keys: tuple[str, ...]


def probes_from_control(run: Any) -> list[Probe]:
    """A `controls.ControlRun` -> probes."""
    return [Probe(a.event_index, a.verdict, tuple(a.lacunae), tuple(a.contested), a.work) for a in run.answers]


def withdrawn_from_control(run: Any) -> list[WithdrawnReport]:
    return [WithdrawnReport(w.event_index, tuple(w.keys)) for w in run.withdrawn]


def probes_from_responses(responses: Sequence[Any]) -> list[Probe]:
    """An `Organism.run_stream` result -> probes, one per ASK response.

    Responses are one per event; only ASK responses carry a verdict. The
    event index is the response's position in the stream.
    """
    out: list[Probe] = []
    for index, resp in enumerate(responses):
        if getattr(resp, "verdict", None) is None:
            continue
        work = getattr(resp, "work", 0)
        if not isinstance(work, int):
            work = int(getattr(work, "total", 0) or 0)
        out.append(Probe(index, resp.verdict, tuple(resp.lacunae), tuple(resp.contested), work))
    return out


def withdrawn_from_responses(responses: Sequence[Any], events: Sequence[Any]) -> list[WithdrawnReport]:
    """Withdrawn reports at every RETRACT / NEGATION event, empty where nothing fell."""
    out: list[WithdrawnReport] = []
    for index, (resp, ev) in enumerate(zip(responses, events)):
        kind = getattr(ev.kind, "value", ev.kind)
        if kind in ("retract", "negation"):
            out.append(WithdrawnReport(index, tuple(getattr(resp, "withdrawn", ()) or ())))
    return out


# ---------------------------------------------------------------------------
# per-probe and per-item scores
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProbeScore:
    item_id: str
    mechanism: str
    variant: str
    closed_world: bool
    event_index: int
    designed: bool
    expected: str
    got: str
    verdict_ok: bool
    contested_ok: bool | None
    named_ok: bool | None
    work: int
    detail: str = ""

    def ok(self, column: str) -> bool | None:
        return {"verdict": self.verdict_ok, "contested": self.contested_ok, "named": self.named_ok}[column]


@dataclass(frozen=True)
class WithdrawnScore:
    item_id: str
    mechanism: str
    variant: str
    event_index: int
    ok: bool
    detail: str = ""


@dataclass(frozen=True)
class ItemScore:
    item_id: str
    mechanism: str
    variant: str
    probes: tuple[ProbeScore, ...]
    withdrawn: tuple[WithdrawnScore, ...]

    @property
    def all_verdicts_ok(self) -> bool:
        return all(p.verdict_ok for p in self.probes)


def _verdict(value: Any) -> str:
    """Plain string for a verdict given as a string or as a `str`-Enum member."""
    return str(getattr(value, "value", value))


def _bounded(required: Iterable[str], reported: Iterable[str], admissible: Iterable[str]) -> tuple[bool, str]:
    req, rep, adm = set(required), set(reported), set(admissible)
    missing = sorted(req - rep)
    extra = sorted(rep - adm)
    if not missing and not extra:
        return True, ""
    parts = []
    if missing:
        parts.append("missing " + ", ".join(missing))
    if extra:
        parts.append("inadmissible " + ", ".join(extra))
    return False, "; ".join(parts)


def score_item(
    item: Any,
    probes: Sequence[Probe],
    withdrawn: Sequence[WithdrawnReport] = (),
) -> ItemScore:
    """Score one solver's probes against one item's expectations.

    Probes must line up one-to-one with the item's expectations, in order,
    on `event_index`; a solver that skipped or invented a probe is refused
    (E-SC-001) rather than scored against the wrong expectation.
    """
    expectations = tuple(item.expectations)
    if len(probes) != len(expectations):
        raise ScoringError(
            "E-SC-001",
            f"{item.item_id}: {len(probes)} probe(s) answered, {len(expectations)} expected",
        )
    designed_index = getattr(item, "designed_probe_index", None)
    closed = bool(getattr(item, "closed_world", False))
    scored: list[ProbeScore] = []
    for probe, exp in zip(probes, expectations):
        if probe.event_index != exp.event_index:
            raise ScoringError(
                "E-SC-001",
                f"{item.item_id}: probe at event {probe.event_index} scored against expectation "
                f"at event {exp.event_index}",
            )
        got, expected = _verdict(probe.verdict), _verdict(exp.verdict)
        if got not in VERDICTS:
            raise ScoringError("E-SC-002", f"{item.item_id}: unknown verdict {probe.verdict!r}")
        if expected not in VERDICTS:
            raise ScoringError("E-SC-002", f"{item.item_id}: unknown expected verdict {exp.verdict!r}")
        verdict_ok = got == expected
        contested_ok: bool | None = None
        named_ok: bool | None = None
        detail = ""
        # The two naming columns measure the quality of a right answer's
        # explanation. A wrong verdict is already a miss in the verdict column
        # and is not counted twice here.
        if expected == INADMISSIBLE and verdict_ok:
            contested_ok = set(probe.contested) == set(exp.contested_required)
            if not contested_ok:
                detail = f"contested {sorted(probe.contested)} != {sorted(exp.contested_required)}"
        if expected == UNKNOWN and not closed and verdict_ok:
            named_ok, why = _bounded(exp.lacunae_required, probe.lacunae, exp.lacunae_admissible)
            if not named_ok:
                detail = (detail + "; " if detail else "") + why
        scored.append(
            ProbeScore(
                item_id=item.item_id,
                mechanism=item.mechanism,
                variant=item.variant,
                closed_world=closed,
                event_index=probe.event_index,
                designed=(designed_index == probe.event_index),
                expected=expected,
                got=got,
                verdict_ok=verdict_ok,
                contested_ok=contested_ok,
                named_ok=named_ok,
                work=probe.work,
                detail=detail,
            )
        )

    withdrawn_scores: list[WithdrawnScore] = []
    expected_w = {w.event_index: w for w in getattr(item, "withdrawn", ())}
    reported_w = {w.event_index: w for w in withdrawn}
    for index in sorted(expected_w):
        exp_w = expected_w[index]
        rep = reported_w.get(index)
        if rep is None:
            # The solver produced no column at this event: scored as a miss
            # only when something was required to fall.
            ok, why = _bounded(exp_w.required, (), exp_w.permitted)
        else:
            ok, why = _bounded(exp_w.required, rep.keys, exp_w.permitted)
        withdrawn_scores.append(WithdrawnScore(item.item_id, item.mechanism, item.variant, index, ok, why))

    return ItemScore(item.item_id, item.mechanism, item.variant, tuple(scored), tuple(withdrawn_scores))


# ---------------------------------------------------------------------------
# the matrix
# ---------------------------------------------------------------------------

@dataclass
class Cell:
    """A fraction with its denominator kept, so 0/0 is unscored, not 100%."""

    hits: int = 0
    total: int = 0

    def add(self, ok: bool | None) -> None:
        if ok is None:
            return
        self.total += 1
        self.hits += int(ok)

    @property
    def rate(self) -> float | None:
        return None if self.total == 0 else self.hits / self.total

    def __str__(self) -> str:
        return "  —  " if self.rate is None else f"{100 * self.rate:5.1f}"


@dataclass
class Matrix:
    """Solvers × classes × columns, plus the per-variant breakdown and the cost column."""

    cells: dict[tuple[str, str, str], Cell] = field(default_factory=lambda: defaultdict(Cell))
    variant_cells: dict[tuple[str, str, str], Cell] = field(default_factory=lambda: defaultdict(Cell))
    work: dict[tuple[str, str], list[int]] = field(default_factory=lambda: defaultdict(list))
    balance: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    solvers: list[str] = field(default_factory=list)
    probes: int = 0
    failures: dict[str, list[ProbeScore]] = field(default_factory=lambda: defaultdict(list))

    def add(self, solver: str, score: ItemScore) -> None:
        if solver not in self.solvers:
            self.solvers.append(solver)
        for p in score.probes:
            if solver == self.solvers[0]:
                self.balance[(p.mechanism, p.expected)] += 1
                self.probes += 1
            for column in ("verdict", "contested", "named"):
                ok = p.ok(column)
                self.cells[(solver, p.mechanism, column)].add(ok)
                self.variant_cells[(solver, p.variant, column)].add(ok)
            self.work[(solver, p.mechanism)].append(p.work)
            if not p.verdict_ok or p.contested_ok is False or p.named_ok is False:
                self.failures[solver].append(p)
        for w in score.withdrawn:
            self.cells[(solver, w.mechanism, "withdrawn")].add(w.ok)
            self.variant_cells[(solver, w.variant, "withdrawn")].add(w.ok)

    # ---- queries ---------------------------------------------------------

    def rate(self, solver: str, mechanism: str, column: str) -> float | None:
        return self.cells[(solver, mechanism, column)].rate

    def variant_rate(self, solver: str, variant: str, column: str = "verdict") -> float | None:
        return self.variant_cells[(solver, variant, column)].rate

    def mean_work(self, solver: str, mechanism: str | None = None) -> float | None:
        values = (
            self.work[(solver, mechanism)]
            if mechanism is not None
            else [w for (s, _), ws in self.work.items() if s == solver for w in ws]
        )
        return None if not values else sum(values) / len(values)

    def variants(self) -> list[str]:
        return sorted({v for (_, v, _) in self.variant_cells})

    def failing_variants(self, solver: str, column: str = "verdict") -> list[str]:
        """Variants on which `solver` is below 100% in `column`."""
        return [
            v for v in self.variants()
            if (r := self.variant_rate(solver, v, column)) is not None and r < 1.0
        ]

    def perfect(self, solver: str) -> bool:
        return all(
            cell.rate in (None, 1.0)
            for (s, _, _), cell in self.cells.items()
            if s == solver
        )

    def balance_report(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for mech in CLASSES:
            total = sum(n for (m, _), n in self.balance.items() if m == mech)
            if total:
                out[mech] = {v: self.balance[(mech, v)] / total for v in VERDICTS if self.balance[(mech, v)]}
        return out

    # ---- rendering ---------------------------------------------------------

    def render(self, *, title: str = "", columns: Sequence[str] = COLUMNS) -> str:
        lines: list[str] = []
        if title:
            lines.append(title)
        head = f"{'solver':<28}" + "".join(
            f"{mech + ':' + col:>{max(9, len(mech) + len(col) + 2)}}" for mech in CLASSES for col in columns
        ) + f"{'work/ask':>10}"
        lines.append(head)
        lines.append("-" * len(head))
        for solver in self.solvers:
            row = f"{solver:<28}"
            for mech in CLASSES:
                for col in columns:
                    width = max(9, len(mech) + len(col) + 2)
                    row += f"{str(self.cells[(solver, mech, col)]):>{width}}"
            mw = self.mean_work(solver)
            row += f"{'—' if mw is None else f'{mw:8.1f}':>10}"
            lines.append(row)
        return "\n".join(lines)

    def render_variants(self, solvers: Sequence[str] | None = None, column: str = "verdict") -> str:
        solvers = list(solvers or self.solvers)
        variants = self.variants()
        head = f"{'solver':<28}" + "".join(f"{v:>13}" for v in variants)
        lines = [f"per-variant {column} %", head, "-" * len(head)]
        for solver in solvers:
            row = f"{solver:<28}"
            for v in variants:
                row += f"{str(self.variant_cells[(solver, v, column)]):>13}"
            lines.append(row)
        return "\n".join(lines)

    def to_json(self) -> str:
        payload = {
            "solvers": self.solvers,
            "probes": self.probes,
            "balance": self.balance_report(),
            "cells": {
                f"{s}|{m}|{c}": {"hits": cell.hits, "total": cell.total}
                for (s, m, c), cell in sorted(self.cells.items())
            },
            "variants": {
                f"{s}|{v}|{c}": {"hits": cell.hits, "total": cell.total}
                for (s, v, c), cell in sorted(self.variant_cells.items())
            },
            "work": {f"{s}|{m}": (sum(ws) / len(ws) if ws else None) for (s, m), ws in sorted(self.work.items())},
        }
        return json.dumps(payload, indent=1, sort_keys=True)
