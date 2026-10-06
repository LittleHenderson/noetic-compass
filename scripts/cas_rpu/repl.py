"""An interactive console for the CAS reasoning processor.

    python scripts/cas_rpu/repl.py

Type premises, ask a question, read the trace. Nothing here calls a model:
every answer is produced by the CJT banks, the memory board, the comparator and
the RPM planner over the premises you gave it.

One-shot use, for scripting or a quick check:

    python scripts/cas_rpu/repl.py -p "VS->QS, QS->IU" -a "VS->IU"
    python scripts/cas_rpu/repl.py -p "VS->QS" -a "VS->IU" --closed --quiet
        # prints just: NO

Exit status in one-shot mode is 0 when the processor CONCLUDED, 2 when it
withheld (NEEDS_*), 3 when the premises were INADMISSIBLE -- so it can gate a
script on whether the machine was willing to commit.
"""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ccb_r1"))

from cmb import CognitiveMemoryBoard  # noqa: E402
from rpm import Terminal  # noqa: E402

from foundations import (  # noqa: E402
    REASONING_RECIPES,
    FoundationError,
    focused_profile,
    reasoning_profile,
)
from runtime import EXPERIENCE_CELL, Problem, ReasoningProcessor  # noqa: E402

DEFAULT_RELATION = "leads_to"
ASSOC_RELATION = "co_occurs"

EXIT_CONCLUDED = 0
EXIT_WITHHELD = 2
EXIT_INADMISSIBLE = 3

HELP = """
premises
  A -> B              a premise: A leads_to B
  A -leads_to-> B     the same, naming the relation explicitly
  A ~> B              an ASSOCIATIVE link (co_occurs). ^8 will follow it,
                      ^6 will reject it -- this is how you make it backtrack
  not A -> B          an explicit negation. Two of these that disagree make
                      the premise set INADMISSIBLE

asking
  ? A -> B            reason about whether A leads_to B
  why                 the support tree under the last conclusion
  trace               the last episode's full phase trace

settings
  world open|closed   open: an unclosable chain is UNKNOWN (default)
                      closed: it is a legitimate NO
  ambition F2|A 0.9   set the goal channel and its level
                      (bare `ambition` restores the default reasoning profile)
  memory 0.6          pre-charge the ^5 experience cell C5

inspect
  premises            what the workspace holds
  recipes             theoretical yield and limiting reagent per outcome
  lacunae             questions asked that the premises could not answer
  scenario <name>     load a worked example: ladder, gap, assoc, contra
  reset               clear premises (keeps ambition and memory)
  help, quit
""".strip()

SCENARIOS: dict[str, tuple[str, list[str]]] = {
    "ladder": (
        "a four-hop chain with two associative decoys",
        [
            "VS -> QS", "QS -> IU", "IU -> TR", "TR -> NX",
            "VS ~> DE", "DE -> NX",
            "VS -> KP", "KP ~> NX",
        ],
    ),
    "gap": ("a missing link -- it should ask, not guess", ["VS -> QS", "AA -> IU"]),
    "assoc": (
        "association only -- every link is the wrong relation",
        ["VS ~> DE", "DE ~> NX"],
    ),
    "contra": (
        "a self-contradictory premise set",
        ["VS -> QS", "QS -> IU", "not QS -> IU"],
    ),
}


class Session:
    """Mutable console state: premises, world assumption, ambition, memory."""

    def __init__(self) -> None:
        self.premises: list[tuple[str, str, str]] = []
        self.negated: list[tuple[str, str, str]] = []
        self.closed_world = False
        self.profile = reasoning_profile()
        self.target_channel = "F2|A"
        self.memory = CognitiveMemoryBoard()
        self.last = None

    # -- parsing ---------------------------------------------------------

    @staticmethod
    def parse_edge(text: str) -> tuple[str, str, str] | None:
        """`A -> B`, `A -rel-> B`, or `A ~> B`. None if it is not an edge."""
        body = text.strip()
        if "~>" in body:
            left, _, right = body.partition("~>")
            return left.strip(), ASSOC_RELATION, right.strip()
        if "->" not in body:
            return None
        left, _, right = body.partition("->")
        relation = DEFAULT_RELATION
        # `A -rel-> B`: partitioning on "->" consumes the second dash, so the
        # left side arrives as `A -rel`. Split on " -" rather than "-" so that
        # a node whose own name contains a dash survives intact.
        stripped = left.rstrip()
        if " -" in stripped:
            head, _, named = stripped.rpartition(" -")
            if head.strip() and named.strip():
                left, relation = head, named.strip()
        subject, obj = left.strip(), right.strip()
        if not subject or not obj:
            return None
        return subject, relation, obj

    def add(self, text: str, *, negated: bool = False) -> str:
        edge = self.parse_edge(text)
        if edge is None:
            return f"  ? cannot read {text!r} as an edge -- try `A -> B`"
        (self.negated if negated else self.premises).append(edge)
        mark = "not " if negated else ""
        return f"  + {mark}{edge[0]} -[{edge[1]}]-> {edge[2]}"

    # -- reasoning -------------------------------------------------------

    def ask(self, text: str) -> tuple[str, int]:
        edge = self.parse_edge(text)
        if edge is None:
            return f"  ? cannot read {text!r} as a query -- try `? A -> B`", 1
        source, relation, target = edge
        if relation == ASSOC_RELATION:
            relation = DEFAULT_RELATION  # `?` always asks about the real relation
        problem = Problem(
            name="console",
            relation=relation,
            premises=tuple(self.premises),
            query=(source, target),
            target_channel=self.target_channel,
            closed_world=self.closed_world,
            negated_premises=tuple(self.negated),
        )
        episode = ReasoningProcessor(self.profile, self.memory).run(problem)
        self.last = episode
        status = {
            Terminal.CONCLUDED: EXIT_CONCLUDED,
            Terminal.INADMISSIBLE: EXIT_INADMISSIBLE,
        }.get(episode.terminal, EXIT_WITHHELD)
        return episode.report(), status

    # -- inspection ------------------------------------------------------

    def show_premises(self) -> str:
        if not self.premises and not self.negated:
            return "  (none)"
        lines = [f"  {s} -[{r}]-> {o}" for s, r, o in self.premises]
        lines += [f"  not {s} -[{r}]-> {o}" for s, r, o in self.negated]
        return "\n".join(lines)

    def show_recipes(self) -> str:
        lines = []
        for name, recipe in REASONING_RECIPES.items():
            lines.append(
                f"  {name:<18} Y_T={recipe.theoretical_yield(self.profile):.3f}"
                f"  limiting {recipe.limiting_reagent(self.profile)}"
            )
            lines.append(f"      {recipe}")
        return "\n".join(lines)

    def show_why(self) -> str:
        if self.last is None:
            return "  nothing asked yet"
        if self.last.justification is None:
            return (
                f"  no conclusion to justify -- last run ended "
                f"{self.last.terminal.value}"
            )
        return "\n".join(_render_tree(self.last.justification, 1))

    def show_trace(self) -> str:
        if self.last is None:
            return "  nothing asked yet"
        return "\n".join(f"  {step}" for step in self.last.trace)

    def show_lacunae(self) -> str:
        if self.last is None:
            return "  nothing asked yet"
        gaps = self.last.workspace.lacunae()
        return "\n".join(f"  {g}" for g in gaps) if gaps else "  (none)"

    def show_memory(self) -> str:
        recall = self.memory.recall(EXPERIENCE_CELL, decay=False)
        state = "lacuna" if recall.is_lacuna else f"charge {recall.charge:.3f}"
        return f"  {EXPERIENCE_CELL} (^5 Female, Cognitive): {state} [{recall.tier.value}]"

    def set_ambition(self, args: list[str]) -> str:
        if not args:
            self.profile = reasoning_profile()
            self.target_channel = "F2|A"
            return "  ambition reset to the default reasoning profile"
        ref = args[0]
        level = float(args[1]) if len(args) > 1 else 0.9
        try:
            self.profile = focused_profile(ref, level)
        except (FoundationError, ValueError) as exc:
            return f"  ? {exc}"
        self.target_channel = ref
        return f"  ambition {ref} at {level}; dominant {self.profile.dominant()}"


def _render_tree(node: dict, depth: int) -> list[str]:
    pad = "  " * depth
    if node.get("cycle"):
        return [f"{pad}{node['pid']} (cycle)"]
    lines = [f"{pad}{node['claim']}   [{node['status']}{' ' + node['stage'] if node['stage'] else ''}]"]
    for child in node.get("support", []):
        lines.extend(_render_tree(child, depth + 1))
    return lines


def run_command(session: Session, line: str) -> tuple[str | None, bool, int]:
    """Returns (output, should_quit, status)."""
    text = line.strip()
    if not text or text.startswith("#"):
        return None, False, 0
    lowered = text.lower()

    if lowered in ("quit", "exit", "q"):
        return None, True, 0
    if lowered in ("help", "?help", "h"):
        return HELP, False, 0
    if lowered == "premises":
        return session.show_premises(), False, 0
    if lowered == "recipes":
        return session.show_recipes(), False, 0
    if lowered == "why":
        return session.show_why(), False, 0
    if lowered == "trace":
        return session.show_trace(), False, 0
    if lowered == "lacunae":
        return session.show_lacunae(), False, 0
    if lowered == "reset":
        session.premises.clear()
        session.negated.clear()
        session.last = None
        return "  premises cleared", False, 0

    parts = shlex.split(text)
    head = parts[0].lower()

    if head == "world" and len(parts) > 1:
        if parts[1].lower() not in ("open", "closed"):
            return "  ? world must be `open` or `closed`", False, 1
        session.closed_world = parts[1].lower() == "closed"
        return f"  world is {parts[1].lower()}", False, 0
    if head == "ambition":
        return session.set_ambition(parts[1:]), False, 0
    if head == "memory":
        if len(parts) == 1:
            return session.show_memory(), False, 0
        session.memory.write(EXPERIENCE_CELL, float(parts[1]))
        return session.show_memory(), False, 0
    if head == "scenario":
        if len(parts) < 2 or parts[1] not in SCENARIOS:
            return f"  ? scenarios: {', '.join(SCENARIOS)}", False, 1
        blurb, edges = SCENARIOS[parts[1]]
        session.premises.clear()
        session.negated.clear()
        out = [f"  {parts[1]} -- {blurb}"]
        for edge in edges:
            out.append(
                session.add(edge[4:], negated=True)
                if edge.startswith("not ")
                else session.add(edge)
            )
        return "\n".join(out), False, 0

    if text.startswith("?"):
        report, status = session.ask(text[1:])
        return report, False, status
    if lowered.startswith("not "):
        return session.add(text[4:], negated=True), False, 0
    if lowered.startswith("fact "):
        return session.add(text[5:]), False, 0
    if Session.parse_edge(text) is not None:
        return session.add(text), False, 0

    return f"  ? unknown command {text!r} -- type `help`", False, 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Interactive console for the CAS reasoning processor."
    )
    parser.add_argument(
        "-p", "--premises", help="comma-separated premises, e.g. 'VS->QS, QS->IU'"
    )
    parser.add_argument("-a", "--ask", help="a query, e.g. 'VS->IU'")
    parser.add_argument("--closed", action="store_true", help="closed-world reading")
    parser.add_argument("--ambition", help="goal channel, e.g. 'F5|A'")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), help="load a worked example")
    parser.add_argument(
        "--quiet", action="store_true", help="one-shot: print only the answer"
    )
    args = parser.parse_args(argv)

    session = Session()
    session.closed_world = args.closed
    if args.ambition:
        message = session.set_ambition([args.ambition])
        if message.startswith("  ?"):
            print(message, file=sys.stderr)
            return 1
    if args.scenario:
        out, _, _ = run_command(session, f"scenario {args.scenario}")
        if not args.quiet and out:
            print(out)
    if args.premises:
        for chunk in args.premises.split(","):
            out, _, _ = run_command(session, chunk.strip())
            if not args.quiet and out:
                print(out)

    if args.ask:
        report, status = session.ask(args.ask)
        print(session.last.answer if args.quiet and session.last else report)
        return status

    if not sys.stdin.isatty():
        # Piped input: run it as a script, then stop.
        status = 0
        for line in sys.stdin:
            out, quit_now, code = run_command(session, line)
            if out:
                print(out)
            status = code or status
            if quit_now:
                break
        return status

    print("CAS reasoning processor -- no model in the loop. `help` for commands.")
    while True:
        try:
            line = input("cas> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        out, quit_now, _ = run_command(session, line)
        if out:
            print(out)
        if quit_now:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
