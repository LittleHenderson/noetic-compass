"""Revision Streams — the experiment: organism, controls and ablations on the same probes.

    python scripts/cas_rpu/revision_experiment.py            # the matrix, both worlds
    python scripts/cas_rpu/revision_experiment.py --check    # exit 1 unless the contract holds
    python scripts/cas_rpu/revision_experiment.py --json out.json

Read `docs/working/revision_streams_contract_2026_10_06.md` §0 before reading
any number this prints. The first row of every table is `ctl_recompute`, the
two-set replayer with no truth maintenance in it, and it is at 100% on every
column it can produce. Nothing below it beats it on correctness, by
construction. What the tables establish:

1. **Convergence.** The organism -- which holds beliefs across episodes,
   answers standing conclusions from the record, and un-holds them when their
   support dies -- agrees with recompute-from-scratch on every probe, in both
   worlds, with zero heartbeat faults. `--check` fails if it does not.
2. **Diagnosis.** Each control is the oracle minus one rule and each ablation
   is the organism minus one workspace rule. The per-variant table shows which
   probes each one fails. A class on which every broken solver still scores
   100% diagnoses nothing, and the report says so.
3. **Cost.** Mean work per ask for each solver, split into first asks and
   repeat asks of a pair already asked in the item. The replayer pays the
   walk every time; a held-belief reasoner answers a standing conclusion from
   the record. A design measurement with no empirical claim.

Fingerprints print first. If they differ from the ones pinned in
`test_cas_rpu_revision.py`, the items changed and no number here is
comparable to a number from before.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ccb_r1"))

from ablations import ABLATIONS, Ablation  # noqa: E402
from controls import CONTROLS, CORRECT_BY_CONSTRUCTION, Replayer  # noqa: E402
from events import EventKind  # noqa: E402
from organism import Organism  # noqa: E402
from revision import StreamDifficulty, StreamSet, generate_revision_set  # noqa: E402
from scoring import (  # noqa: E402
    CLASSES,
    Matrix,
    Probe,
    WithdrawnReport,
    probes_from_control,
    probes_from_responses,
    score_item,
    withdrawn_from_control,
    withdrawn_from_responses,
)

ORGANISM = "organism"


# ---------------------------------------------------------------------------
# running one solver over one set
# ---------------------------------------------------------------------------

@dataclass
class SolverRun:
    name: str
    matrix_rows: list[tuple[str, object]]           # (item_id, ItemScore)
    faults: int                                      # heartbeat faults (organism-family only)
    first_ask_work: list[int]
    repeat_ask_work: list[int]


def _repeat_flags(events) -> dict[int, bool]:
    """event index of each ASK -> was this pair asked earlier in the item?"""
    seen: set[tuple[str, str]] = set()
    flags: dict[int, bool] = {}
    for i, ev in enumerate(events):
        if ev.kind is EventKind.ASK:
            flags[i] = ev.pair in seen
            seen.add(ev.pair)
    return flags


def _split_work(probes: list[Probe], flags: dict[int, bool], first: list[int], repeat: list[int]) -> None:
    for p in probes:
        (repeat if flags.get(p.event_index) else first).append(p.work)


def run_control(control: Replayer, stream_set: StreamSet) -> SolverRun:
    run = SolverRun(control.name, [], 0, [], [])
    for item in stream_set.items:
        out = control(item.events, stream_set.closed_world)
        probes = probes_from_control(out)
        run.matrix_rows.append((item.item_id, score_item(item, probes, withdrawn_from_control(out))))
        _split_work(probes, _repeat_flags(item.events), run.first_ask_work, run.repeat_ask_work)
    return run


def run_organism(name: str, stream_set: StreamSet, workspace_factory=None) -> SolverRun:
    """One fresh Organism per item (contract §6): tokens are per item and an
    organism shared across items would carry routes between them."""
    run = SolverRun(name, [], 0, [], [])
    for item in stream_set.items:
        kwargs = {"closed_world": stream_set.closed_world}
        if workspace_factory is not None:
            kwargs["workspace_factory"] = workspace_factory
        org = Organism(**kwargs)
        responses = org.run_stream(item.events)
        probes = probes_from_responses(responses)
        withdrawn = withdrawn_from_responses(responses, item.events)
        run.matrix_rows.append((item.item_id, score_item(item, probes, withdrawn)))
        run.faults += len(org.faults)
        _split_work(probes, _repeat_flags(item.events), run.first_ask_work, run.repeat_ask_work)
    return run


def _mean(values: list[int]) -> float | None:
    return None if not values else sum(values) / len(values)


# ---------------------------------------------------------------------------
# the experiment
# ---------------------------------------------------------------------------

@dataclass
class WorldResult:
    closed_world: bool
    stream_set: StreamSet
    matrix: Matrix
    runs: dict[str, SolverRun]


def run_world(stream_set: StreamSet, *, solvers: set[str] | None = None) -> WorldResult:
    matrix = Matrix()
    runs: dict[str, SolverRun] = {}

    def wanted(name: str) -> bool:
        return solvers is None or name in solvers

    for control in CONTROLS:                       # ctl_recompute is CONTROLS[0]: first row
        if wanted(control.name):
            runs[control.name] = run_control(control, stream_set)
    if wanted(ORGANISM):
        runs[ORGANISM] = run_organism(ORGANISM, stream_set)
    for abl in ABLATIONS:
        if wanted(abl.name):
            runs[abl.name] = run_organism(abl.name, stream_set, abl.workspace)
    for name, run in runs.items():
        for _, score in run.matrix_rows:
            matrix.add(name, score)
    return WorldResult(stream_set.closed_world, stream_set, matrix, runs)


def ablation_verdict(abl: Ablation, open_w: WorldResult, closed_w: WorldResult) -> tuple[bool, str]:
    """Did this ablation fail inside, and only inside, the class it was built to expose?

    Expectations in `ablations.py` are predictions. Here they are checked
    against what happened: the failing *classes* must be a non-empty subset of
    the predicted classes (or, for a prediction about a column, that column).
    An ablation with no prediction is reported, never checked.
    """
    if not abl.expected_to_fail:
        return True, "no prediction; reported only"
    predicted_classes = {e[0] for e in abl.expected_to_fail if e[0] in CLASSES}
    failing: set[str] = set()
    column_hits: list[str] = []
    for world in (open_w, closed_w):
        for mech in CLASSES:
            for col in ("verdict", "contested", "named", "withdrawn"):
                rate = world.matrix.rate(abl.name, mech, col)
                if rate is not None and rate < 1.0:
                    failing.add(mech)
                    column_hits.append(f"{'closed' if world.closed_world else 'open'}:{mech}:{col}={100*rate:.0f}%")
    if abl.name == "abl_fixed_world":
        open_perfect = open_w.matrix.perfect(abl.name)
        closed_bad = not closed_w.matrix.perfect(abl.name)
        ok = open_perfect and closed_bad
        return ok, ("paired-set signature: perfect open, failing closed" if ok else f"unexpected: {column_hits}")
    if abl.name == "abl_no_sweep":
        verdict_perfect = all(
            w.matrix.rate(abl.name, m, "verdict") in (None, 1.0) for w in (open_w, closed_w) for m in CLASSES
        )
        named_cells = [w.matrix.rate(abl.name, m, "named") for w in (open_w, closed_w) for m in CLASSES]
        named_bad = any(r is not None and r < 1.0 for r in named_cells)
        note = ("the named column loses precision" if named_bad
                else "no scored cell changed on this family (reported, not claimed)")
        return verdict_perfect, (f"verdicts unchanged; {note}" if verdict_perfect else f"unexpected verdict change: {column_hits}")
    if abl.name == "abl_amnesic_ask":
        verdict_perfect = all(
            w.matrix.rate(abl.name, m, "verdict") in (None, 1.0) for w in (open_w, closed_w) for m in CLASSES
        )
        named_bad = (open_w.matrix.rate(abl.name, "N", "named") or 1.0) < 1.0
        ok = verdict_perfect and named_bad
        return ok, ("every verdict right; the N named column fails" if ok else f"unexpected: {column_hits}")
    ok = bool(failing) and failing <= predicted_classes
    return ok, (f"fails in {sorted(failing)} ⊆ predicted {sorted(predicted_classes)}: {column_hits}"
                if ok else f"predicted {sorted(predicted_classes)}, failing {sorted(failing)}: {column_hits}")


def contract_checks(open_w: WorldResult, closed_w: WorldResult) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    for name in CORRECT_BY_CONSTRUCTION:
        ok = all(w.matrix.perfect(name) for w in (open_w, closed_w))
        checks.append((f"{name} is 100% on every column, both worlds", ok, ""))
    for w in (open_w, closed_w):
        label = "closed" if w.closed_world else "open"
        ok = w.matrix.perfect(ORGANISM)
        detail = "" if ok else "; ".join(
            f"{p.item_id}@{p.event_index} {p.variant}: expected {p.expected} got {p.got} {p.detail}".strip()
            for p in w.matrix.failures[ORGANISM][:8]
        )
        checks.append((f"organism agrees with the oracle on every probe ({label} world)", ok, detail))
        checks.append((f"organism heartbeat raised no fault ({label} world)", w.runs[ORGANISM].faults == 0,
                       f"{w.runs[ORGANISM].faults} fault(s)"))
    for mech in CLASSES:
        broken_that_fail = [
            name for name in open_w.matrix.solvers
            if name not in CORRECT_BY_CONSTRUCTION and name != ORGANISM
            and any((w.matrix.rate(name, mech, c) or 1.0) < 1.0 for w in (open_w, closed_w) for c in ("verdict", "contested", "named", "withdrawn"))
        ]
        checks.append((f"class {mech} is diagnostic (some broken solver fails it)", bool(broken_that_fail), ", ".join(broken_that_fail)))
    for abl in ABLATIONS:
        ok, why = ablation_verdict(abl, open_w, closed_w)
        checks.append((f"{abl.name}: {why}", ok, ""))
    checks.append((
        "the audit catches the broken cascades structurally (faults > 0 for no_cascade and nontransitive_retract)",
        all(open_w.runs[n].faults > 0 for n in ("abl_no_cascade", "abl_nontransitive_retract") if n in open_w.runs),
        ", ".join(f"{n}: {open_w.runs[n].faults}" for n in ("abl_no_cascade", "abl_nontransitive_retract") if n in open_w.runs),
    ))
    return checks


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def render_cost(open_w: WorldResult, closed_w: WorldResult) -> str:
    head = f"{'solver':<28}{'first ask':>12}{'repeat ask':>12}{'n first':>9}{'n repeat':>9}"
    lines = [
        "work per ask, both worlds pooled (design measurement, not one currency: a control counts",
        "adjacency entries expanded + pairs filtered; an organism counts Workspace.ask calls +",
        "propositions scanned by ^8. Compare a solver with itself as the stream grows, not across rows.)",
        head, "-" * len(head),
    ]
    for name in open_w.matrix.solvers:
        first = open_w.runs[name].first_ask_work + closed_w.runs[name].first_ask_work
        repeat = open_w.runs[name].repeat_ask_work + closed_w.runs[name].repeat_ask_work
        mf, mr = _mean(first), _mean(repeat)
        lines.append(
            f"{name:<28}{'—' if mf is None else f'{mf:.1f}':>12}{'—' if mr is None else f'{mr:.1f}':>12}"
            f"{len(first):>9}{len(repeat):>9}"
        )
    return "\n".join(lines)


def render_balance(stream_set: StreamSet, matrix: Matrix) -> str:
    lines = [f"probe balance per class ({'closed' if stream_set.closed_world else 'open'} world; ceiling 60%)"]
    for mech, mix in matrix.balance_report().items():
        lines.append(f"  {mech}: " + ", ".join(f"{v} {100*f:.0f}%" for v, f in sorted(mix.items())))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--n", type=int, default=40, help="items per set (default 40)")
    ap.add_argument("--seed", type=int, default=20261006)
    ap.add_argument("--hops", type=int, default=3)
    ap.add_argument("--distractors", type=int, default=4)
    ap.add_argument("--probes-before", type=int, default=1)
    ap.add_argument("--no-shadow", action="store_true")
    ap.add_argument("--interleave", type=int, default=2)
    ap.add_argument("--solvers", nargs="*", help="restrict to these solver names")
    ap.add_argument("--check", action="store_true", help="exit 1 unless every contract check passes")
    ap.add_argument("--json", type=Path, help="write matrices and checks here")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    difficulty = StreamDifficulty(
        hops=args.hops, distractors=args.distractors, probes_before=args.probes_before,
        shadow=not args.no_shadow, interleave=args.interleave,
    )
    sets = {
        closed: generate_revision_set(args.n, seed=args.seed, difficulty=difficulty, closed_world=closed)
        for closed in (False, True)
    }
    out: list[str] = []
    out.append("Revision Streams — fingerprints first")
    for closed, s in sets.items():
        out.append(f"  {'closed' if closed else 'open  '} {s.fingerprint()}  n={len(s.items)} seed={args.seed} {difficulty.label()}")
    out.append("")

    solvers = set(args.solvers) if args.solvers else None
    if solvers is not None:
        solvers |= {"ctl_recompute", ORGANISM}
    worlds = {closed: run_world(s, solvers=solvers) for closed, s in sets.items()}
    open_w, closed_w = worlds[False], worlds[True]

    for w in (open_w, closed_w):
        label = "closed" if w.closed_world else "open"
        out.append(w.matrix.render(title=f"{label} world — % of probes correct per class and column (— = not scored)"))
        out.append("")
        out.append(w.matrix.render_variants())
        out.append("")
        out.append(render_balance(w.stream_set, w.matrix))
        out.append("")
    out.append(render_cost(open_w, closed_w))
    out.append("")

    checks = contract_checks(open_w, closed_w)
    out.append("contract checks")
    for text, ok, detail in checks:
        out.append(f"  [{'ok' if ok else 'FAIL'}] {text}" + (f"  — {detail}" if detail and not ok else ""))
        if ok and detail and "faults" in text:
            out.append(f"         {detail}")
    failed = [c for c in checks if not c[1]]
    out.append("")
    out.append(
        "Permitted reading (contract §0): the organism converges with recompute-from-scratch on every "
        "probe; each broken solver fails the class built to catch it; cost is reported. "
        "Nothing here shows truth maintenance is necessary or superior to the replayer."
    )

    if not args.quiet:
        print("\n".join(out))
    if args.json:
        payload = {
            "fingerprints": {("closed" if c else "open"): s.fingerprint() for c, s in sets.items()},
            "difficulty": difficulty.canonical(),
            "n": args.n,
            "seed": args.seed,
            "worlds": {("closed" if c else "open"): json.loads(w.matrix.to_json()) for c, w in worlds.items()},
            "faults": {("closed" if c else "open"): {n: r.faults for n, r in w.runs.items()} for c, w in worlds.items()},
            "checks": [{"check": t, "ok": ok, "detail": d} for t, ok, d in checks],
        }
        args.json.write_text(json.dumps(payload, indent=1, sort_keys=True))
    if args.check and failed:
        print(f"\n{len(failed)} contract check(s) failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
