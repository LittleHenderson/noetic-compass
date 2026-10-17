"""depth.py -- the recursion horizon, the Structural Deadlock verdict, and horizontal flattening.

WHAT THIS MODULE DOES
---------------------
1. Pins the horizon: `HORIZON = 12`. The number is the OWNER'S RULING of 2026-10-16, not a
   reading of canon: canon says 5, and "THE NUMBER" below keeps the canon quote visible beside
   the ruling. It is a separate number from `dwp.DESIRE_BOUND`, which is also 12 and does a
   different job.
2. `check_depth(depth)` answers one question only: may a BLOCK at this depth spawn anything
   deeper? Returns DepthVerdict.OK, or DepthVerdict.STRUCTURAL_DEADLOCK when the block occurs
   at (or beyond) the horizon.
3. `flatten(chain)` is the sanctioned fix for a deadlock: it takes a chain that reached the
   horizon and returns a FLAT set of sibling sub-problems AT THE SAME LEVEL, tagged
   HORIZONTAL, with no deeper child. It is the fix, not an exception and not a retry.
4. `assert_within_horizon(chain)` / `max_depth(chain)` let a test prove by traversal that no
   chain anywhere in a tree ever reaches depth 13.

WHAT THIS MODULE DOES NOT DO
----------------------------
- It does NOT resolve blocks. Blocks are resolved in `dwp.resolve()`; this module only rules
  on whether a deeper chain is allowed.
- It does NOT raise the limit when the limit is inconvenient. The horizon moved from 5 to 12 by
  the owner's ruling of 2026-10-16 and by nothing else: no test, no proof and no line of code in
  this package derived 12. "The fix is to flatten into horizontal decomposition -- NOT to raise
  the number" is still the rule for a chain that reaches the horizon; the ruling moved where the
  horizon sits, not what happens when it is reached.
- It does NOT bound the Desire loop. That is `dwp.DESIRE_BOUND`, a different number doing a
  different job, in `dwp.py`.
- It does NOT pick which sub-problems a horizontal decomposition should contain beyond a
  documented placeholder (see UNDECIDED (U6)); the caller may pass `parts`.
- It does NOT run anything inside Helm. It is a mechanism.
"""

import enum

import dwp
from dwp import (
    ArchitectureViolation,
    Chain,
    HORIZONTAL,
    Resolution,
    State,
)

__all__ = [
    "HORIZON", "HORIZON_READING", "HORIZON_QUOTE", "HORIZON_RULING", "CANON_FLATTEN",
    "DepthVerdict", "check_depth", "flatten", "FlattenedResolution",
    "max_depth", "assert_within_horizon", "depth_histogram",
]

# ---------------------------------------------------------------------------
# The number.
#
# CANON, quoted verbatim -- note what it actually says and does not say:
#
#   "Why is the recursion depth limited to 5 levels? In the formal manifold of CAS, this
#    limit is not an arbitrary performance cap, but a stability horizon."
#       [FULL_MANUSCRIPT_v2.md, line 6424]
#
#   "To ensure global stability and prevent stack-overflow in the cognitive manifold,
#    recursion is strictly limited to a maximum depth of 5 levels."
#       [Chapter_27_RPM_Structure.md, line 59]
#
# The brief paraphrases this as "depth 5 is a stability horizon, not an arbitrary cap".
# That exact sentence is NOT in the manuscript, and the manuscript does not say the horizon
# IS 5 *because* it is a stability horizon -- it says the limit of 5 is not an arbitrary
# performance cap but a stability horizon. The number 5 is pinned here as a READING of the
# book, not as a quotation of a sentence the book contains.
#
# ---------------------------------------------------------------------------
# THE OWNER'S RULING OF 2026-10-16 -- the number this build pins is NOT the book's number.
#
# The owner ruled that the recursion horizon is 12. Twelve is NOT derived from canon. It is not
# computed from the sources, it is not implied by any passage, and nothing in this package
# proves it. The published book says 5, and so does the Rust engine. Twelve is a DECISION, taken
# by the owner on 2026-10-16, and recorded here beside the book's own words so that a reader can
# see both at once:
#
#   canon, on its own number:   "Why is the recursion depth limited to 5 levels? In the formal
#                                manifold of CAS, this limit is not an arbitrary performance
#                                cap, but a stability horizon."   [FULL_MANUSCRIPT_v2.md:6424]
#                               -- i.e. the book calls 5 "not an arbitrary performance cap, but
#                               a stability horizon". That sentence is KEPT, unchanged, in
#                               HORIZON_QUOTE below. It is still true of the book. It is no
#                               longer a description of the number this build pins.
#
#   the owner, on this build:   12, ruled 2026-10-16, on the owner's authority alone. The book's
#                               reasoning -- that a depth limit is a stability horizon rather
#                               than a performance cap -- is not evidence for 12, and is not
#                               offered as evidence here. 12 is a ruling, not a result.
#
# What that means for anyone reading a refusal from this module: a block at depth 12 is a
# Structural Deadlock because the owner said so, not because the sources say so. If the ruling
# is withdrawn, HORIZON is the one line to change back, and the suite re-proves the horizon
# property at whatever number is pinned.
#
# UNDECIDED IN CANON (U11): which number the recursion horizon should be. Canon says 5 in three
# places; the Rust engine uses 5; the owner ruled 12 on 2026-10-16. Canon does not support 12 and
# this build does not claim it does. The pinned value follows the ruling; the conflict is left
# visible rather than resolved in prose.
# ---------------------------------------------------------------------------

HORIZON = 12  # THE OWNER'S RULING OF 2026-10-16, NOT DERIVED FROM CANON (canon says 5).
# The depth at which a further block is a Structural Deadlock. Twelve, by the owner's ruling of
# 2026-10-16. Separate number, separate job from `dwp.DESIRE_BOUND` (also 12): this one is how
# deep a chain may sit; that one is how many times a Desire loop may cycle in place.
#
# "a stability horizon, not an arbitrary cap" -- the brief's phrasing; the book's own words
# are "not an arbitrary performance cap, but a stability horizon" (quoted in HORIZON_QUOTE).
# The quote is the book's description of ITS number, 5. It is kept here, unedited, so the
# distance between the book's 5 and the ruling's 12 stays visible.
HORIZON_READING = "a stability horizon, not an arbitrary cap"

#: The ruling, as a string other modules and tests can print without re-typing it.
HORIZON_RULING = (
    "HORIZON = 12 is the owner's ruling of 2026-10-16 and is not derived from canon; "
    "canon calls 5 \"not an arbitrary performance cap, but a stability horizon\""
)

HORIZON_QUOTE = (
    '"Why is the recursion depth limited to 5 levels? In the formal manifold of CAS, this '
    'limit is not an arbitrary performance cap, but a stability horizon."  '
    "[FULL_MANUSCRIPT_v2.md, line 6424]"
)

CANON_FLATTEN = (
    '"By understanding the depth limit, we can design workflows and AI pipelines that '
    'intentionally flatten the recursion--solving sub-problems at the same depth level '
    'rather than nesting them indefinitely. We move from vertical recursion to horizontal '
    'decomposition, preserving the stability of the manifold."  '
    "[FULL_MANUSCRIPT_v2.md, line 6428]"
)


class DepthVerdict(str, enum.Enum):
    """The only two answers the horizon can give to "may this block go deeper?"."""

    OK = "OK"
    STRUCTURAL_DEADLOCK = "STRUCTURAL_DEADLOCK"


def check_depth(depth):
    """May a block at `depth` spawn a deeper chain?

    Returns DepthVerdict.OK for depth < HORIZON, and DepthVerdict.STRUCTURAL_DEADLOCK for
    depth >= HORIZON. The >= is deliberate on both ends: depth == HORIZON is the shape canon
    calls the deadlock ("a recursive chain at depth n=5 encounters another blocked node" --
    canon's number is 5, this build's horizon is 12 by the owner's ruling of 2026-10-16; the
    SHAPE is canon's, the NUMBER is the ruling's), and depth > HORIZON cannot be legitimate, so
    it is refused rather than silently allowed.

    This function presumes a block has occurred. An unblocked node needs no verdict.

    UNDECIDED IN CANON (U2) is handled in `dwp.resolve`, which documents the root-at-0
    reading of "5 levels" that makes depth 5 the horizon and depth 6 unreachable. Under the
    owner's ruling of 2026-10-16 the same root-at-0 reading puts the horizon at depth 12 and
    depth 13 out of reach. The origin question (U2) is unchanged by the ruling; only the
    number is.
    """
    if isinstance(depth, bool) or not isinstance(depth, int):
        raise ArchitectureViolation(f"depth must be an int, got {type(depth).__name__}")
    if depth < 0:
        raise ArchitectureViolation(f"depth must be >= 0, got {depth}")
    if depth >= HORIZON:
        return DepthVerdict.STRUCTURAL_DEADLOCK
    return DepthVerdict.OK


class FlattenedResolution(Resolution):
    """The horizontal decomposition of a horizon chain.

    Deliberately carries `siblings`, not `children`: a flattened chain has NO deeper child,
    so there is no attribute through which a caller could reach one. Every sibling sits at
    the same depth as the chain that deadlocked, carries the HORIZONTAL tag, and has no
    children of its own.
    """

    __slots__ = ("siblings", "source_label")

    def __init__(self, node, depth, siblings, notation, source_label="", canon=CANON_FLATTEN,
                 note=""):
        super().__init__(node, depth, HORIZONTAL, notation, canon, note)
        self.siblings = tuple(siblings)
        self.source_label = source_label
        if not self.siblings:
            raise ArchitectureViolation("a flattened resolution needs at least 1 sibling")
        for sib in self.siblings:
            if not isinstance(sib, Chain):
                raise ArchitectureViolation("siblings must be Chain objects")
            if sib.depth != depth:
                raise ArchitectureViolation(
                    f"sibling {sib.label!r} sits at depth {sib.depth}, but flattening must "
                    f"stay at the deadlocked level {depth}; a deeper sibling is just the "
                    "vertical recursion that deadlocked"
                )
            if sib.tag != HORIZONTAL:
                raise ArchitectureViolation(f"sibling {sib.label!r} is not tagged HORIZONTAL")
            if sib.children:
                raise ArchitectureViolation(
                    f"sibling {sib.label!r} has children; horizontal decomposition has none"
                )

    @property
    def child_depth(self):
        """None: flattening adds no level. That is the entire point."""
        return None

    @property
    def vertical_levels_added(self):
        return 0

    def level_set(self):
        return {s.depth for s in self.siblings}


def _default_parts(chain):
    """Pick the horizontal sub-problems for a deadlocked chain.

    UNDECIDED IN CANON (U6): how a horizon chain is to be decomposed horizontally. The book
    says "solving sub-problems at the same depth level" without saying what the sub-problems
    ARE. This build uses, in order: (a) whatever CO-6 decomposition the chain's state
    already carries, (b) two placeholder parts derived from the chain label. Placeholders
    are placeholders -- a caller with real structure should pass `parts`.
    """
    if chain.state is not None and chain.state.decomposition:
        return tuple(chain.state.decomposition)
    base = chain.label or "deadlock"
    return (f"{base}#h1", f"{base}#h2")


def flatten(chain, parts=None):
    """Flatten a deadlocked horizon chain into same-level siblings. THE FIX.

    `chain` must be a Chain sitting exactly at HORIZON (depth 12) whose block could not be
    resolved. Returns a FlattenedResolution whose `.siblings` are fresh Chains at the SAME
    depth, tagged HORIZONTAL, with no children and no deeper level.

    Refuses if the chain is not at the horizon: canon presents flattening as the repair for
    depth exhaustion, and using it lower down would be re-labelling ordinary recursion.

    UNDECIDED IN CANON (U5): whether flattening is also legitimate below the horizon. The
    book only describes it as the deadlock repair. This build refuses it below the horizon
    rather than permit a legal-looking shortcut that canon never licensed.
    """
    if not isinstance(chain, Chain):
        raise ArchitectureViolation("flatten() takes a Chain")
    if chain.node is None:
        raise ArchitectureViolation(
            "flatten() takes a chain that BLOCKED; this chain carries no blocked node"
        )
    if chain.depth != HORIZON:
        raise ArchitectureViolation(
            f"flatten() takes a chain that has hit the horizon (depth {HORIZON}); got depth "
            f"{chain.depth}. Below the horizon the answer is dwp.resolve(), not flattening."
        )

    names = tuple(parts) if parts is not None else _default_parts(chain)
    names = tuple(str(n) for n in names)
    if not names:
        raise ArchitectureViolation("flatten() needs at least one horizontal part")

    siblings = []
    for i, name in enumerate(names):
        sub_state = (chain.state.child(name) if chain.state is not None else State(name))
        # Same depth as the deadlocked chain. Same parent. No children. Tagged HORIZONTAL.
        siblings.append(Chain(node=chain.node, depth=chain.depth, tag=HORIZONTAL,
                              label=name, state=sub_state, parent=chain.parent, index=i))

    return FlattenedResolution(
        node=chain.node,
        depth=chain.depth,
        siblings=siblings,
        notation=(f"FLATTEN[RPM({chain.node.value}@{chain.depth})"
                  f" -> {len(siblings)} x HORIZONTAL@{chain.depth}]"),
        source_label=chain.label,
    )


def max_depth(chain):
    """Deepest depth anywhere in a Chain tree (or -1 for something that is not a Chain)."""
    if not isinstance(chain, Chain):
        raise ArchitectureViolation("max_depth() takes a Chain")
    return chain.tree_depth()


def depth_histogram(chain):
    """{depth: number of chains at that depth} for a whole tree."""
    return chain.depth_histogram()


def assert_within_horizon(chain):
    """Raise unless every chain in the tree sits at depth <= HORIZON. Returns the deepest.

    This is the code-level form of "no path produces depth 13": it walks the tree rather than
    trusting the constructor that built it. (Never at depth 13, which is one past HORIZON = 12,
    the owner's ruling of 2026-10-16.)
    """
    deepest = max_depth(chain)
    for c in chain.walk():
        if c.depth > HORIZON:
            raise ArchitectureViolation(
                f"chain {c.label!r} sits at depth {c.depth} > HORIZON {HORIZON}; the horizon "
                "was breached -- use flatten(), never a deeper child."
            )
    return deepest
