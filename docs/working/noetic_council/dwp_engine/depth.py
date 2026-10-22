"""depth.py -- the recursion horizon, the Structural Deadlock verdict, and horizontal flattening.

WHAT THIS MODULE DOES
---------------------
1. Pins the horizon: `HORIZON = 5`.
2. `check_depth(depth)` answers one question only: may a BLOCK at this depth spawn anything
   deeper? Returns DepthVerdict.OK, or DepthVerdict.STRUCTURAL_DEADLOCK when the block occurs
   at (or beyond) the horizon.
3. `flatten(chain)` is the sanctioned fix for a deadlock: it takes a chain that reached the
   horizon and returns a FLAT set of sibling sub-problems AT THE SAME LEVEL, tagged
   HORIZONTAL, with no deeper child. It is the fix, not an exception and not a retry.
4. `assert_within_horizon(chain)` / `max_depth(chain)` let a test prove by traversal that no
   chain anywhere in a tree ever reaches depth 6.

WHAT THIS MODULE DOES NOT DO
----------------------------
- It does NOT resolve blocks. Blocks are resolved in `dwp.resolve()`; this module only rules
  on whether a deeper chain is allowed.
- It does NOT raise the limit when the limit is inconvenient. "The fix is to flatten into
  horizontal decomposition -- NOT to raise the number."
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
    "HORIZON", "HORIZON_READING", "HORIZON_QUOTE", "CANON_FLATTEN",
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
# ---------------------------------------------------------------------------

HORIZON = 5
# "a stability horizon, not an arbitrary cap" -- the brief's phrasing; the book's own words
# are "not an arbitrary performance cap, but a stability horizon" (quoted in HORIZON_QUOTE).
HORIZON_READING = "a stability horizon, not an arbitrary cap"

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
    depth >= HORIZON. The >= is deliberate on both ends: depth == HORIZON is the canonical
    deadlock ("a recursive chain at depth n=5 encounters another blocked node"), and
    depth > HORIZON cannot be legitimate, so it is refused rather than silently allowed.

    This function presumes a block has occurred. An unblocked node needs no verdict.

    UNDECIDED IN CANON (U2) is handled in `dwp.resolve`, which documents the root-at-0
    reading of "5 levels" that makes depth 5 the horizon and depth 6 unreachable.
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

    `chain` must be a Chain sitting exactly at HORIZON (depth 5) whose block could not be
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

    This is the code-level form of "no path produces depth 6": it walks the tree rather than
    trusting the constructor that built it.
    """
    deepest = max_depth(chain)
    for c in chain.walk():
        if c.depth > HORIZON:
            raise ArchitectureViolation(
                f"chain {c.label!r} sits at depth {c.depth} > HORIZON {HORIZON}; the horizon "
                "was breached -- use flatten(), never a deeper child."
            )
    return deepest
