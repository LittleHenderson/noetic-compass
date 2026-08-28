"""Run the CAS reasoning processor with nothing attached to it.

    python scripts/cas_rpu/demo.py

No network, no keys, no model, no cost. Every conclusion printed below is
produced by CJT transitions, CMB recall, `^6` decomposition, `^9` inference,
CDAB comparison and RPM recursion over CAS-encoded premises.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ccb_r1"))

from cmb import CognitiveMemoryBoard, Tier  # noqa: E402

from foundations import (  # noqa: E402
    REASONING_RECIPES,
    Consequence,
    focused_profile,
    reasoning_profile,
)
from runtime import EXPERIENCE_CELL, Problem, ReasoningProcessor  # noqa: E402

RULE = "=" * 78


CASES: list[tuple[str, Problem]] = [
    (
        "A four-hop chain with two associative decoys",
        Problem(
            name="ladder",
            relation="leads_to",
            premises=(
                ("VS", "leads_to", "QS"),
                ("QS", "leads_to", "IU"),
                ("IU", "leads_to", "TR"),
                ("TR", "leads_to", "NX"),
                ("VS", "co_occurs", "DE"),
                ("DE", "leads_to", "NX"),
                ("VS", "leads_to", "KP"),
                ("KP", "co_occurs", "NX"),
            ),
            query=("VS", "NX"),
        ),
    ),
    (
        "A missing link, open world -- it must ask, not guess",
        Problem(
            name="gap",
            relation="leads_to",
            premises=(("VS", "leads_to", "QS"), ("AA", "leads_to", "IU")),
            query=("VS", "IU"),
        ),
    ),
    (
        "The same premises declared complete -- now a NO is legitimate",
        Problem(
            name="gap-closed",
            relation="leads_to",
            premises=(("VS", "leads_to", "QS"), ("AA", "leads_to", "IU")),
            query=("VS", "IU"),
            closed_world=True,
        ),
    ),
    (
        "Association only -- every link is the wrong relation",
        Problem(
            name="assoc-only",
            relation="leads_to",
            premises=(("VS", "co_occurs", "DE"), ("DE", "co_occurs", "NX")),
            query=("VS", "NX"),
        ),
    ),
    (
        "A self-contradictory premise set",
        Problem(
            name="contra",
            relation="leads_to",
            premises=(("VS", "leads_to", "QS"), ("QS", "leads_to", "IU")),
            query=("VS", "IU"),
            negated_premises=(("QS", "leads_to", "IU"),),
        ),
    ),
]


def main() -> int:
    memory = CognitiveMemoryBoard()
    memory.write(EXPERIENCE_CELL, 0.6, Tier.CONSTITUTIONAL)
    profile = reasoning_profile(0.9)

    print(RULE)
    print("CAS REASONING PROCESSOR -- no model in the loop")
    print(RULE)
    print(f"ambition   dominant channel {profile.dominant()}")
    totals = {d.value: round(v, 3) for d, v in profile.drive_totals().items() if v}
    print(f"drive rails {totals}")

    for title, problem in CASES:
        processor = ReasoningProcessor(profile, memory)
        episode = processor.run(problem)
        print("\n" + RULE)
        print(title)
        print(RULE)
        print(episode.report())

    print("\n" + RULE)
    print("28-lane consequence profile -- why a scalar reward loses information")
    print(RULE)
    launch = Consequence(
        "publish and promote the volume",
        {"F5|A": 0.8, "F6|E": 0.4, "F4|f": -0.5, "F7|A": -0.3},
    )
    print(f"candidate   {launch.candidate}")
    print(f"advances    {', '.join(launch.advanced())}")
    print(f"damages     {', '.join(launch.damaged())}")
    for name, ambition in (
        ("agency-seeking (F5|A)", focused_profile("F5|A", 1.0, spread=0.0)),
        ("relational     (F4|f)", focused_profile("F4|f", 1.0, spread=0.0)),
    ):
        print(f"  under {name}: {launch.weighted(ambition):+.3f}")
    print("\nSame candidate, opposite sign. The ranking is profile-relative,")
    print("which is exactly what collapsing 28 lanes into one number destroys.")

    print("\n" + RULE)
    print("Recipes and the limiting reagent -- what an outcome actually costs")
    print(RULE)
    spiked = focused_profile("F2|A", 1.0, spread=0.0)
    balanced = reasoning_profile(0.9)
    for name, ambition in (("single-minded", spiked), ("balanced     ", balanced)):
        for outcome in ("deduction", "honest_abstention"):
            recipe = REASONING_RECIPES[outcome]
            print(
                f"  {name}  {outcome:<18} Y_T={recipe.theoretical_yield(ambition):.3f}"
                f"  limiting {recipe.limiting_reagent(ambition)}"
            )
    print("\nWanting one thing intensely does not supply the rest of the recipe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
