#!/usr/bin/env python3
"""Where in the capability range does the pipeline actually help?

    python scripts/ccb_r1/capability_sweep.py

A strong model scored 95% on the deduction ladder, leaving no room for a
margin. The obvious fix is a weaker model, or a harder task — the same lever
from either end: open a gap between what the model can do unaided and what the
task demands.

But there is a second edge nobody has stated. The Wrap Pipeline works by asking
the model a *narrower* question than the task ("are these statements enough to
settle it?") and acting on the answer. A model too weak to answer that honestly
cannot be helped by the scaffold either — the gate just inherits its error. So
the prediction is a **band**:

    too strong   the model already gets it right; no headroom
    too weak     the model cannot operate the scaffold; the gate is fooled
    in between   the architecture has something to add

This sweep tests that prediction on simulated models before any budget is
spent. Each simulated model has two independent competences, because the
distinction is the whole mechanism:

    p_route   object level — can it find a chain that exists?
    p_meta    meta level   — can it tell whether the premises settle the question?

and one disposition:

    p_fabricate  when it has no answer, does it invent one rather than decline?

**These are simulated models, not real ones.** The curve below is a
*prediction* about where to look, not a measurement of anything. Its value is
that it says which real models are worth paying for.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from calibration import hard_procedure, honesty_procedure  # noqa: E402
from run_comparison import Counter, run_deduction, run_honesty  # noqa: E402

_LINK_LINE = __import__("re").compile(
    r"^\s*([A-Z]{2})\s+leads to\s+([A-Z]{2})\s*\.\s*$", __import__("re").M
)
_QUERY = __import__("re").compile(
    r"(?:that|does)\s+([A-Z]{2})\s+leads?\s+to\s+([A-Z]{2})"
)


def _premises(prompt: str):
    return [(a, b) for a, b in _LINK_LINE.findall(prompt)]


def _query(prompt: str):
    match = _QUERY.search(prompt)
    return (match.group(1), match.group(2)) if match else ("??", "??")


def _route(premises, query):
    graph: dict[str, set[str]] = {}
    for a, b in premises:
        graph.setdefault(a, set()).add(b)
    src, dst = query
    parent, seen, stack = {}, {src}, [src]
    while stack:
        node = stack.pop()
        for nxt in sorted(graph.get(node, ())):
            if nxt in seen:
                continue
            parent[nxt] = node
            if nxt == dst:
                path, cur = [dst], dst
                while cur in parent:
                    cur = parent[cur]
                    path.append(cur)
                return list(reversed(path))
            seen.add(nxt)
            stack.append(nxt)
    return None


@dataclass(frozen=True)
class Capability:
    """One simulated model.

    The three parameters are set independently on purpose. An earlier version
    derived all three from a single `level`, which welded reasoning skill to
    hallucination rate and produced a curve that looked like "the pipeline
    helps strong models" when the real driver was something else. Separating
    them is what makes the grid below able to answer the question.
    """

    p_route: float       # object level: can it find a chain that exists?
    p_meta: float        # meta level: can it tell whether the premises settle it?
    p_fabricate: float   # disposition: with no answer, does it invent one?

    @classmethod
    def at_level(cls, level: float) -> "Capability":
        """The plausible ladder: skill rises together, bluffing decays slowly.

        Meta skill starts at chance rather than zero — even a poor model is not
        systematically *anti*-correlated with its own knowledge. Fabrication
        declines with capability but never vanishes, because stronger models
        hedge more, they do not stop hallucinating.
        """
        return cls(p_route=level, p_meta=0.5 + 0.5 * level,
                   p_fabricate=0.9 - 0.4 * level)

    def label(self) -> str:
        return f"r{self.p_route:.2f}/f{self.p_fabricate:.2f}"


def graded_model(cap: Capability, seed: int = 0):
    """A deterministic simulated model at the given capability."""
    def model(prompt: str) -> str:
        digest = hashlib.sha256(f"{seed}:{prompt}".encode()).hexdigest()[:12]
        rng = random.Random(int(digest, 16))
        premises, query = _premises(prompt), _query(prompt)
        route = _route(premises, query)

        if "SUFFICIENT" in prompt:                     # the RPM gate's question
            truth = "SUFFICIENT" if route else "INSUFFICIENT"
            if rng.random() < cap.p_meta:
                return truth
            return "INSUFFICIENT" if truth == "SUFFICIENT" else "SUFFICIENT"

        if route and rng.random() < cap.p_route:       # found the real chain
            steps = "\n".join(
                f"{route[i]} leads to {route[i + 1]}." for i in range(len(route) - 1)
            )
            return f"{steps}\nAnswer: YES"

        if rng.random() < cap.p_fabricate:             # guessed rather than declined
            src, dst = query
            return f"{src} leads to {dst}.\nAnswer: YES"

        return "Answer: NO"
    return model


def sweep(levels, n: int, workers: int, seed: int):
    deduction = hard_procedure(n=n).build(0).items
    honesty = honesty_procedure(n=n).build(0).items

    rows = []
    for level in levels:
        cap = Capability.at_level(level)
        model = graded_model(cap, seed)
        counters = [Counter() for _ in range(5)]
        counted = [c.wrap(model) for c in counters]

        d_wrapped, d_bare, d_cot = run_deduction(deduction, workers, 0, *counted[:3])
        h_wrapped, h_bare = run_honesty(honesty, workers, 0, *counted[3:])

        rows.append({
            "level": level,
            "p_route": cap.p_route, "p_meta": cap.p_meta,
            "p_fabricate": cap.p_fabricate,
            "deduction_bare": d_bare.rate, "deduction_wrapped": d_wrapped.rate,
            "deduction_cot": d_cot.rate,
            "deduction_delta": d_wrapped.rate - d_bare.rate,
            "honesty_bare": h_bare.rate, "honesty_wrapped": h_wrapped.rate,
            "honesty_delta": h_wrapped.rate - h_bare.rate,
        })
    return rows


def grid(routes, fabrications, n: int, workers: int, seed: int):
    """Vary reasoning and bluffing independently.

    The single-axis ladder cannot separate "the model reasons badly" from "the
    model bluffs when stuck", and those imply opposite choices of test subject.
    """
    deduction = hard_procedure(n=n).build(0).items
    honesty = honesty_procedure(n=n).build(0).items

    cells = []
    for p_route in routes:
        for p_fabricate in fabrications:
            cap = Capability(p_route=p_route, p_meta=0.5 + 0.5 * p_route,
                             p_fabricate=p_fabricate)
            model = graded_model(cap, seed)
            counters = [Counter() for _ in range(5)]
            counted = [c.wrap(model) for c in counters]
            d_wrapped, d_bare, _ = run_deduction(deduction, workers, 0, *counted[:3])
            h_wrapped, h_bare = run_honesty(honesty, workers, 0, *counted[3:])
            cells.append({
                "p_route": p_route, "p_fabricate": p_fabricate,
                "deduction_delta": d_wrapped.rate - d_bare.rate,
                "honesty_delta": h_wrapped.rate - h_bare.rate,
                "deduction_bare": d_bare.rate, "honesty_bare": h_bare.rate,
            })
    return cells


def render_grid(cells, key: str, title: str) -> str:
    routes = sorted({c["p_route"] for c in cells})
    fabs = sorted({c["p_fabricate"] for c in cells})
    lookup = {(c["p_route"], c["p_fabricate"]): c[key] for c in cells}

    lines = [title, "", "            " + "".join(f"{f:>9.2f}" for f in fabs)]
    lines.append("  p_route   " + "─" * (9 * len(fabs)) + "   <- p_fabricate")
    for r in routes:
        row = "".join(f"{lookup[(r, f)]:>+9.1%}" for f in fabs)
        lines.append(f"  {r:7.2f} │{row}")
    return "\n".join(lines)


def render(rows) -> str:
    head = (f"{'level':>6} {'p_route':>8} {'p_meta':>7} │ "
            f"{'M3 bare':>8} {'M3 wrap':>8} {'Δ':>7} │ "
            f"{'M1 bare':>8} {'M1 wrap':>8} {'Δ':>7}")
    lines = [head, "─" * len(head)]
    for r in rows:
        bar = "█" * round(max(0.0, r["honesty_delta"]) * 40)
        lines.append(
            f"{r['level']:6.2f} {r['p_route']:8.2f} {r['p_meta']:7.2f} │ "
            f"{r['deduction_bare']:8.1%} {r['deduction_wrapped']:8.1%} "
            f"{r['deduction_delta']:+7.1%} │ "
            f"{r['honesty_bare']:8.1%} {r['honesty_wrapped']:8.1%} "
            f"{r['honesty_delta']:+7.1%}  {bar}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--steps", type=int, default=9)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--grid", action="store_true",
                        help="vary reasoning and bluffing independently")
    args = parser.parse_args(argv)

    if args.grid:
        axis = (0.0, 0.25, 0.5, 0.75, 1.0)
        cells = grid(axis, axis, args.n, args.workers, args.seed)
        print(render_grid(cells, "deduction_delta",
                          "M3 deduction — wrapped minus bare"))
        print()
        print(render_grid(cells, "honesty_delta",
                          "M1 honesty — wrapped minus bare"))
        print("\nSimulated models. This predicts where to look; it measures nothing.")
        if args.out:
            args.out.write_text(json.dumps(cells, indent=2) + "\n", encoding="utf-8")
            print(f"wrote {args.out}")
        return 0

    levels = [i / (args.steps - 1) for i in range(args.steps)]
    rows = sweep(levels, args.n, args.workers, args.seed)
    print(render(rows))

    best_m1 = max(rows, key=lambda r: r["honesty_delta"])
    best_m3 = max(rows, key=lambda r: r["deduction_delta"])
    print(f"\nlargest M1 gain at level {best_m1['level']:.2f} "
          f"({best_m1['honesty_delta']:+.1%})")
    print(f"largest M3 gain at level {best_m3['level']:.2f} "
          f"({best_m3['deduction_delta']:+.1%})")
    print("\nSimulated models. This predicts where to look; it measures nothing.")

    if args.out:
        args.out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
