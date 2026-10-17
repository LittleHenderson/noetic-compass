"""dwp.py -- the D/W/P recursion engine: three resolution functors over one prerequisite chain.

WHAT THIS MODULE DOES
---------------------
Defines the three nodes of the prerequisite chain (D = Desire, W = Wisdom, P = Power),
the `Blocked` outcome, the node-local `Chain` record, and `resolve(node, blocked, depth,
state)` -- the single entry point that dispatches a blocked node to exactly one of the
three functors the book defines. It also provides `expand()`, a small driver that walks a
scripted blockade schedule and builds the whole chain tree, so that depth invariants can be
tested rather than asserted in prose.

The one structural promise this module makes and enforces in code:

    Power (P) blocked      -> exactly ONE child chain, tag SINGLE
    Wisdom (W) blocked     -> a COPRODUCT of >= 2 child chains, tag PARALLEL; 1 is refused
    Desire (D) blocked     -> NO child chains at all, tag ITERATIVE, depth unchanged

"Impossible to get a child from D" is not a comment here. An iterative resolution is a
different class (`IterativeResolution`) that has no `children` attribute and is not an
instance of `SpawnedResolution`, so `resolution.children` raises `AttributeError` on it and
the module-level accessor `child_chains()` raises `NoChildrenError`. You cannot accidentally
read a child chain out of a Desire resolution, because there is no such field to read.

The Desire loop is also BOUNDED here, at `DESIRE_BOUND = 12` -- a second number, separate from
`depth.HORIZON` (also 12), doing a different job. It is the owner's ruling of 2026-10-16 and it
is NOT derived from canon: canon writes `loop(N)` with no maximum. A loop may cycle 12 times;
the 13th is refused with the typed word `DESIRE_BOUND_EXHAUSTED`.

WHAT THIS MODULE DOES NOT DO
----------------------------
- It does NOT decide whether a node is blocked. Blocks arrive from outside as `Blocked`.
- It does NOT measure satisfaction, score a mind, or compute the Seshvar/Fisher-Rao metric.
- It does NOT run anything inside Helm, and it is not the Helm brain. It is a mechanism.
- It does NOT decide the depth limit; that lives in `depth.py` (HORIZON = 12, the owner's
  ruling of 2026-10-16) and is imported there lazily inside `resolve()` to keep the two modules
  free of an import cycle. The two 12s are not the same 12: the horizon is how deep a chain may
  sit, DESIRE_BOUND is how many times a loop may cycle in place. A Desire loop is still not
  counted against the horizon, bound or not.
- It does NOT implement the CO-8/CO-9/CO-5/CO-6/CO-1/CO-4/CO-7 operators themselves. It
  names them, in the order the book names them, and leaves their semantics to the caller.
- It does NOT resolve a Structural Deadlock. That is `depth.flatten()`'s job, and `expand()`
  calls it rather than resolving anything deeper.
- It does NOT define what a "dirty" resolution is. That is `retraction.py`.
"""

import enum

# ---------------------------------------------------------------------------
# CANON -- quoted verbatim below. ASCII transliteration only: the manuscript uses
# LaTeX (\\Phi, \\circ, \\bigoplus, \\to, \\lor, \\Rightarrow); I spell those as
# Phi, o (composition), (+), ->, v, =>. Wording is otherwise untouched.
# ---------------------------------------------------------------------------

CANON_DEF_27_2 = (
    'Definition 27.2 (Recursive Depth). "A recursive evaluation R^(n) is a nested '
    'D/W/P chain spawned at depth n. For any parent chain at depth n, a block at '
    'node K triggers a child chain R^(n+1) whose ultimate output realizes the '
    'prerequisite for K."  [Chapter_27_RPM_Structure.md, line 47]'
)

CANON_INTRO_27 = (
    '"While the primary RPM chain is a one-way valve, the architecture is not a static '
    'line. It is a Recursive Manifold. When any node in the D/W/P chain is blocked, the '
    'system initiates a Formal Recursive Evaluation."  [Chapter_27_RPM_Structure.md, line 45]'
)

CANON_PHI_P = (
    '"1. Power Resolution (Rational Recursion): Functor: \\Phi_P: P_blocked -> '
    '(CO-8 o CO-9) => RPM(P). Nature: Rational and structured. It spawns a single child '
    'chain to solve a resource gap."  [Chapter_27_RPM_Structure.md, line 53]'
)

CANON_PHI_W = (
    '"2. Wisdom Resolution (Parallel Branching): Functor: \\Phi_W: W_blocked -> '
    '(CO-5 v CO-6). Nature: This is the only case allowing parallel morphisms. Via CO-6, '
    'the Wisdom node splits into a coproduct of child chains: W ~= (+)_i RPM(w_i). The '
    'parent Wisdom node is satisfied only when the total sum of child realization '
    'morphisms glues into the parent sheaf."  [Chapter_27_RPM_Structure.md, line 54]'
)

CANON_PHI_D = (
    '"3. Desire Loop (Iterative Cultivation): Functor: \\Phi_D: D_blocked -> '
    '(CO-1 o CO-4 o CO-7)^N. Nature: Iterative, not recursive. It does not spawn child '
    'chains but instead cycles the current state through an exposure loop until the '
    'motivation threshold is reached. Because it is iterative, it does not contribute to '
    'the recursion depth limit."  [Chapter_27_RPM_Structure.md, line 55]'
)

CANON_CH5_NOTATION = (
    'Chapter 5, lines 81-84, gives the surface syntax this module emits: '
    '"Power Resolution: RPM(F5)[P -> CO-8 -> CO-9 -> RPM(F5.P)]", '
    '"Wisdom Resolution: RPM(F2)[W -> CO-5 -> RPM(F2.W)]", '
    '"Wisdom Decomposition: RPM(F2)[W -> CO-6 -> RPM(F2.W.c1) + RPM(F2.W.c2)]", '
    '"Desire Loop: RPM(F3)[D -> CO-1 -> CO-4 -> CO-7 -> loop(N)]"'
)

CANON_CH5_DEPTH = (
    '"The Depth Limit: To prevent infinite loops and architectural collapse, recursion is '
    'limited to a maximum depth of 5 levels. If a child chain at level 5 also blocks, the '
    'system reaches a Structural Deadlock. It is important to note that the Section-Retraction '
    'principle holds at every depth: the child chain must be as rigorous and valid as the '
    'parent. Note that Desire loops, being iterative rather than recursive, do not count '
    'toward this depth limit."  [Chapter_05_The_Prerequisite_Chain.md, line 87]'
)

CANON_DEADLOCK = (
    '"We define Structural Deadlock as the state where a recursive chain at depth n=5 '
    'encounters another blocked node. At this point, the system has exhausted its structural '
    'capacity to bridge the gap. The architecture cannot spawn another level without '
    'violating the global stability axiom."  [FULL_MANUSCRIPT_v2.md, line 6428]'
)

# NOTE ON THE NUMBERS INSIDE THESE QUOTES. CANON_CH5_DEPTH and CANON_DEADLOCK say "5", because
# canon says 5. They are quotations and are NOT edited: a quote that has been renumbered is no
# longer a quotation. `depth.HORIZON` is 12 -- the owner's ruling of 2026-10-16, not derived from
# canon -- so the two will differ on purpose wherever both appear.

__all__ = [
    "Node", "Blocked", "State", "Chain", "DesireCycle", "DesireLoop",
    "Resolution", "SpawnedResolution", "SingleChildResolution", "CoproductResolution",
    "IterativeResolution", "DeadlockResolution",
    "resolve", "expand", "child_chains",
    "SINGLE", "PARALLEL", "ITERATIVE", "HORIZONTAL", "DEADLOCK", "UNBLOCKED", "PENDING",
    "DESIRE_BOUND", "DESIRE_BOUND_EXHAUSTED",
    "DwpError", "ArchitectureViolation", "FunctorsRefused", "NoChildrenError",
    "DesireBoundExhausted",
    "CANON_DEF_27_2", "CANON_INTRO_27", "CANON_PHI_P", "CANON_PHI_W", "CANON_PHI_D",
    "CANON_CH5_NOTATION", "CANON_CH5_DEPTH", "CANON_DEADLOCK",
]

# ---------------------------------------------------------------------------
# Resolution tags. These strings are the vocabulary the rest of the build and the
# tests assert on, so they are plain strings, not an enum.
# ---------------------------------------------------------------------------

SINGLE = "SINGLE"          # exactly one child chain (Phi_P)
PARALLEL = "PARALLEL"      # a coproduct of child chains (Phi_W via CO-6)
ITERATIVE = "ITERATIVE"    # no child chains, a cycle in place (Phi_D)
HORIZONTAL = "HORIZONTAL"  # same-level siblings, the deadlock fix (depth.flatten)
DEADLOCK = "DEADLOCK"      # STRUCTURAL_DEADLOCK, superseded by HORIZONTAL flat
UNBLOCKED = "UNBLOCKED"    # leaf: nothing blocked here, no resolution needed
PENDING = "PENDING"        # child chain created by a functor, not yet dispatched

# Canon drive labels used in the surface notation of each functor (Ch. 5 lines 81-84).
_DRIVE_P = "F5"
_DRIVE_W = "F2"
_DRIVE_D = "F3"

# ---------------------------------------------------------------------------
# THE SECOND NUMBER -- the Desire loop's bound, and what it is not.
#
# Canon, on N in "(CO-1 o CO-4 o CO-7)^N", quoted verbatim:
#
#   "It does not spawn child chains but instead cycles the current state through an exposure
#    loop until the motivation threshold is reached."
#       [Chapter_27_RPM_Structure.md, line 55]
#
# Canon gives NO maximum for N and NO threshold function. It writes loop(N). So the bound below
# is NOT derived from canon, and nothing in this package proves it:
#
#   DESIRE_BOUND = 12 is the OWNER'S RULING of 2026-10-16, on the owner's authority alone.
#
# It is a DIFFERENT NUMBER FROM `depth.HORIZON` even though both are 12 this year. Two jobs:
#
#   depth.HORIZON  = 12   how DEEP a chain may sit before a further block is a
#                         Structural Deadlock.
#   dwp.DESIRE_BOUND = 12 how many times a Desire loop may CYCLE IN PLACE before it must stop.
#
# The rule that the Desire loop does not count toward depth is unchanged by this bound. A loop
# that exhausts DESIRE_BOUND is refused as DESIRE_BOUND_EXHAUSTED, and its depth counter is
# exactly where it was: an exhausted loop is not a deep loop, and the two refusals must never be
# used interchangeably.
#
# UNDECIDED IN CANON (U8): whether N in `(CO-1 o CO-4 o CO-7)^N` is bounded anywhere, and at
# what value. Canon writes loop(N) and gives no maximum and no threshold function. The owner
# ruled 12 on 2026-10-16; that ruling is the whole warrant for this constant. If the ruling is
# withdrawn, this is the one line to change back.
# ---------------------------------------------------------------------------

DESIRE_BOUND = 12  # THE OWNER'S RULING OF 2026-10-16, NOT DERIVED FROM CANON (canon: no bound).
# A Desire loop may cycle 12 times. The 13th cycle is refused, with the word below.
#
#: The typed word this build uses when a Desire loop asks for a cycle past DESIRE_BOUND. It is
#: deliberately NOT "STRUCTURAL_DEADLOCK": that word belongs to the horizon, and the two must
#: stay distinguishable in a record.
DESIRE_BOUND_EXHAUSTED = "DESIRE_BOUND_EXHAUSTED"


class DwpError(Exception):
    """Base class for every refusal this engine raises."""


class ArchitectureViolation(DwpError):
    """The requested call would violate the D/W/P architecture as the book defines it."""


class FunctorsRefused(ArchitectureViolation):
    """A resolution functor refused its input (e.g. a coproduct asked for one child)."""


class NoChildrenError(ArchitectureViolation):
    """Child chains were requested from a resolution that cannot have any."""


class DesireBoundExhausted(ArchitectureViolation):
    """A Desire loop asked to cycle past DESIRE_BOUND. NOT a Structural Deadlock.

    Carries ``word == "DESIRE_BOUND_EXHAUSTED"`` so a caller can branch on the typed word
    rather than on the message text. The depth it reports is the depth the loop sat at, which
    is unchanged by the refusal: the refusal is about how many cycles ran, never about depth.
    """

    word = DESIRE_BOUND_EXHAUSTED
    code = DESIRE_BOUND_EXHAUSTED

    def __init__(self, requested, bound=DESIRE_BOUND, depth=None, iterations_run=None):
        self.requested = requested
        self.bound = bound
        self.depth = depth
        self.iterations_run = iterations_run
        super().__init__(
            f"{DESIRE_BOUND_EXHAUSTED}: the Desire loop may cycle {bound} times "
            f"(DESIRE_BOUND = {bound}, the owner's ruling of 2026-10-16); a cycle {requested} "
            "was refused. Canon bounds N nowhere; the bound is the ruling's, not canon's. "
            "This is NOT a Structural Deadlock: the loop cycles in place and the depth "
            f"counter is unchanged (depth={depth!r})."
        )


# ---------------------------------------------------------------------------
# Node, Blocked, State
# ---------------------------------------------------------------------------

class Node(str, enum.Enum):
    """The three nodes of the prerequisite chain.

    "all lasting, structural achievement must flow sequentially from Desire to Wisdom to
    Power" [Chapter_05_The_Prerequisite_Chain.md, line 3]. Subclasses `str`, so
    `Node.D == "D"` is True and node identity survives JSON round-trips.
    """

    D = "D"
    W = "W"
    P = "P"

    def __str__(self):
        return self.value

    @property
    def name_long(self):
        return {"D": "Desire", "W": "Wisdom", "P": "Power"}[self.value]


def _as_node(node):
    """Coerce a str or Node to a Node, refusing anything else loudly."""
    if isinstance(node, Node):
        return node
    if isinstance(node, str):
        try:
            return Node(node.upper())
        except ValueError:
            raise ArchitectureViolation(
                f"{node!r} is not a node of the D/W/P chain; the chain has exactly D, W, P."
            ) from None
    raise ArchitectureViolation(f"node must be Node or str, got {type(node).__name__}")


class Blocked:
    """The outcome "this node is blocked".

    Canon: "When any node in the D/W/P chain is blocked, the system initiates a Formal
    Recursive Evaluation." A block -- not a wish, not a low score -- is the only trigger.
    """

    __slots__ = ("node", "reason")

    def __init__(self, node, reason=""):
        self.node = _as_node(node)
        self.reason = str(reason)

    def __repr__(self):
        return f"Blocked({self.node.value}, {self.reason!r})"

    def __eq__(self, other):
        return isinstance(other, Blocked) and (self.node, self.reason) == (other.node, other.reason)

    def __hash__(self):
        return hash((self.node, self.reason))


class State:
    """The cognitive state a chain is evaluating. Deliberately thin.

    Fields are the minimum the functors need:
      label        -- name of this state / sub-problem.
      decomposition-- the CO-6 parts of a Wisdom problem, in order. This is what makes the
                      Wisdom coproduct concrete: "Via CO-6, the Wisdom node splits into a
                      coproduct of child chains". Fewer than 2 parts is not a split.
      resonant_child-- the CO-5 route: the single resonant child (Ch. 5 line 58: "they find
                      a specific professor whose lectures resonate with them").
      iterations   -- N in "loop(N)" for the Desire loop. Canon does not bound N; this build
                      does, at DESIRE_BOUND = 12, by the owner's ruling of 2026-10-16.
      drive        -- free-form drive tag for reporting (F2/F3/F5 etc.); not interpreted.

    UNDECIDED IN CANON (U8): whether N in "(CO-1 o CO-4 o CO-7)^N" is bounded anywhere, and at
    what value. Canon writes loop(N) and says the loop runs "until the motivation threshold is
    reached"; it gives no maximum and no threshold function. The owner ruled 12 on 2026-10-16,
    which is the only warrant for the bound this build enforces: `resolve()` accepts N up to
    DESIRE_BOUND and refuses N > DESIRE_BOUND with DESIRE_BOUND_EXHAUSTED. Before the ruling a
    1000-iteration loop was legal by construction; it is refused now, at the loop's own bound,
    and not at the horizon.
    """

    __slots__ = ("label", "decomposition", "resonant_child", "iterations", "drive")

    def __init__(self, label="S", decomposition=(), resonant_child=None, iterations=8, drive=""):
        self.label = str(label)
        self.decomposition = tuple(str(p) for p in decomposition)
        self.resonant_child = None if resonant_child is None else str(resonant_child)
        self.iterations = iterations
        self.drive = str(drive)

    def child(self, label):
        """A sub-state inheriting this state's shape but with its own label."""
        return State(label=label, decomposition=self.decomposition,
                     resonant_child=self.resonant_child, iterations=self.iterations,
                     drive=self.drive)

    def __repr__(self):
        return (f"State(label={self.label!r}, decomposition={self.decomposition!r}, "
                f"resonant_child={self.resonant_child!r}, iterations={self.iterations})")

    def __eq__(self, other):
        return isinstance(other, State) and (
            (self.label, self.decomposition, self.resonant_child, self.iterations, self.drive)
            == (other.label, other.decomposition, other.resonant_child, other.iterations, other.drive))

    def __hash__(self):
        return hash((self.label, self.decomposition, self.resonant_child))


# ---------------------------------------------------------------------------
# Chain -- one node of the recursion tree
# ---------------------------------------------------------------------------

class Chain:
    """One chain in the recursive manifold.

    A Chain records: which node was blocked in it (or None if it was never evaluated),
    its depth, its tag, its children, and whether it has been invalidated. Links are
    mutable at build time (`expand` wires `parent` before recursing) and read-only after;
    nothing in this build mutates a finished tree except `retraction.mark_dirty_upward`,
    which is *supposed* to invalidate it in place.

    Back-pointers (`parent`) exist so that "the block propagates back up the stack" can be
    walked literally: `chain.ancestors` runs child -> parent -> ... -> root.
    """

    def __init__(self, node=None, depth=0, tag=UNBLOCKED, label=None, state=None,
                 parent=None, index=0):
        self.node = node
        self.depth = depth
        self.tag = tag
        self.label = label if label is not None else f"{tag}@{depth}"
        self.state = state if state is not None else State(self.label)
        self.parent = parent
        self.index = index
        self.children = ()
        self.resolution = None    # the Resolution that produced this chain's children
        self.horizontal = None    # the FlattenedResolution attached at the horizon
        self.dirty = False
        self.dirty_reason = None

    # -- navigation ---------------------------------------------------------
    @property
    def root(self):
        """The topmost chain of this tree (walks parent pointers to the end)."""
        cur = self
        while cur.parent is not None:
            cur = cur.parent
        return cur

    @property
    def ancestors(self):
        """(self, parent, ..., root) -- the propagation path for a dirty resolution."""
        out = []
        cur = self
        while cur is not None:
            out.append(cur)
            cur = cur.parent
        return tuple(out)

    def walk(self):
        """Pre-order traversal of this chain and every descendant."""
        yield self
        for kid in self.children:
            yield from kid.walk()

    def leaves(self):
        return tuple(c for c in self.walk() if not c.children)

    def tree_depth(self):
        """Deepest depth anywhere in this tree."""
        return max(c.depth for c in self.walk())

    def depth_histogram(self):
        hist = {}
        for c in self.walk():
            hist[c.depth] = hist.get(c.depth, 0) + 1
        return hist

    def index_of_child(self, child):
        for i, kid in enumerate(self.children):
            if kid is child:
                return i
        raise ArchitectureViolation("that chain is not a child of this chain")

    # -- reporting ----------------------------------------------------------
    def __repr__(self):
        bits = [f"Chain({self.label!r}", f"depth={self.depth}"]
        if self.node is not None:
            bits.append(f"node={self.node.value}")
        bits.append(f"tag={self.tag}")
        if self.children:
            bits.append(f"children={len(self.children)}")
        if self.dirty:
            bits.append("DIRTY")
        return " ".join(bits) + ")"

    def __str__(self):
        return f"{self.label}[{self.tag}@{self.depth}]"


# ---------------------------------------------------------------------------
# Resolution result objects.
#
# The brief: "Return types must make it impossible to get a child from D. Use an explicit
# result object, not a bare list." Hence a sealed hierarchy:
#
#   Resolution                      (no children field at all)
#     SpawnedResolution             children: tuple[Chain, ...]   <- P and W only
#       SingleChildResolution       exactly 1
#       CoproductResolution         >= 2
#     IterativeResolution           NO children field, has .cycle  <- D only
#     DeadlockResolution            NO children field, has .verdict
#
# depth.FlattenedResolution is the fourth sibling (siblings at the same level, tag
# HORIZONTAL) and likewise has no children field.
# ---------------------------------------------------------------------------

class Resolution:
    """Base result of `resolve()`. Carries no child chain of any kind.

    `depth` is the depth of the chain that CONTAINED the block; `child_depth` is the depth
    a child chain would occupy. For Desire those are equal -- that is the whole point of
    "Because it is iterative, it does not contribute to the recursion depth limit."
    """

    __slots__ = ("node", "depth", "tag", "notation", "canon", "note")

    def __init__(self, node, depth, tag, notation, canon="", note=""):
        self.node = _as_node(node)
        self.depth = depth
        self.tag = tag
        self.notation = notation
        self.canon = canon
        self.note = note

    @property
    def child_depth(self):
        """Depth the children of this resolution occupy, or None if it has none."""
        return None

    def spawns_children(self):
        return isinstance(self, SpawnedResolution)

    def summary(self):
        return f"{self.node.value}@{self.depth} -> {self.tag}"


class SpawnedResolution(Resolution):
    """A resolution that produces child chains. Power (1) and Wisdom (>=2) only."""

    __slots__ = ("children",)

    def __init__(self, node, depth, tag, children, notation, canon="", note=""):
        super().__init__(node, depth, tag, notation, canon, note)
        self.children = tuple(children)
        if not self.children:
            raise NoChildrenError(
                f"{self.node.value} resolution produced zero children; use IterativeResolution "
                "for a resolution that spawns nothing."
            )
        for kid in self.children:
            if not isinstance(kid, Chain):
                raise ArchitectureViolation("children must be Chain objects")
            if kid.depth != depth + 1:
                raise ArchitectureViolation(
                    f"child chain at depth {kid.depth} under a parent at depth {depth}; "
                    "Definition 27.2 spawns the child at exactly n+1."
                )

    @property
    def child_depth(self):
        return self.depth + 1

    def child_count(self):
        return len(self.children)


class SingleChildResolution(SpawnedResolution):
    """Phi_P: "It spawns a single child chain to solve a resource gap." Exactly one."""

    __slots__ = ()

    def __init__(self, node, depth, children, notation, canon=CANON_PHI_P, note=""):
        super().__init__(node, depth, SINGLE, children, notation, canon, note)
        if len(self.children) != 1:
            raise FunctorsRefused(
                f"a SINGLE resolution must carry exactly 1 child chain, got {len(self.children)}"
            )


class CoproductResolution(SpawnedResolution):
    """Phi_W via CO-6: "the Wisdom node splits into a coproduct of child chains".

    A coproduct of one is not a split, so arity < 2 is refused here as well as in
    `resolve()`. This class cannot be constructed with a single child at all.
    """

    __slots__ = ()

    def __init__(self, node, depth, children, notation, canon=CANON_PHI_W, note=""):
        super().__init__(node, depth, PARALLEL, children, notation, canon, note)
        if len(self.children) < 2:
            raise FunctorsRefused(
                f"a PARALLEL coproduct requires >= 2 child chains, got {len(self.children)}"
            )


class DesireCycle:
    """The iterative exposure loop of Phi_D. NOT a recursion: it has no children.

    Canon: "(CO-1 o CO-4 o CO-7)^N ... It does not spawn child chains but instead cycles
    the current state through an exposure loop until the motivation threshold is reached."
    Chapter 5 names the three stages: CO-1 directed attention, CO-4 encoding intensity,
    CO-7 pattern entrainment.
    """

    __slots__ = ("operators", "iterations", "state_label")

    def __init__(self, operators=("CO-1", "CO-4", "CO-7"), iterations=8, state_label="S"):
        self.operators = tuple(operators)
        self.iterations = iterations
        self.state_label = state_label

    def __repr__(self):
        return f"DesireCycle({' o '.join(self.operators)})^N, N={self.iterations}"


class IterativeResolution(Resolution):
    """Phi_D. Spawns nothing: no `children` field exists on this class.

    Attempting `resolution.children` raises AttributeError, and `dwp.child_chains()` raises
    NoChildrenError. `child_depth == depth`, so a Desire loop at depth 0 leaves depth 0.
    """

    __slots__ = ("cycle",)

    def __init__(self, node, depth, cycle, notation, canon=CANON_PHI_D, note=""):
        super().__init__(node, depth, ITERATIVE, notation, canon, note)
        if not isinstance(cycle, DesireCycle):
            raise ArchitectureViolation("an iterative resolution must carry a DesireCycle")
        self.cycle = cycle

    @property
    def child_depth(self):
        # "Because it is iterative, it does not contribute to the recursion depth limit."
        return self.depth


class DesireLoop:
    """Runs one Desire resolution's cycle in place, counting cycles against DESIRE_BOUND.

    This is the only place in the package where a loop's iteration COUNT advances, so it is the
    only place where the bound can fire. It owns no depth arithmetic at all: the depth is read
    once from the resolution and handed back unchanged on every step, including the step that
    refuses. A loop that exhausts its bound is refused as DesireBoundExhausted, whose typed word
    is DESIRE_BOUND_EXHAUSTED -- never STRUCTURAL_DEADLOCK, which belongs to the horizon.

    "Because it is iterative, it does not contribute to the recursion depth limit."
    [Chapter_27_RPM_Structure.md, line 55] -- true at every cycle, and still true at the cycle
    that is refused.
    """

    __slots__ = ("resolution", "depth", "bound", "completed")

    def __init__(self, resolution, bound=DESIRE_BOUND):
        if not isinstance(resolution, IterativeResolution):
            raise ArchitectureViolation(
                "a DesireLoop runs an IterativeResolution (Phi_D); got "
                f"{type(resolution).__name__}. Only a Desire block cycles in place."
            )
        if isinstance(bound, bool) or not isinstance(bound, int) or bound < 0:
            raise ArchitectureViolation(f"bound must be a non-negative int, got {bound!r}")
        if bound != DESIRE_BOUND:
            raise ArchitectureViolation(
                f"the Desire bound is DESIRE_BOUND = {DESIRE_BOUND} (the owner's ruling of "
                f"2026-10-16); this build does not take a different bound, got {bound!r}"
            )
        self.resolution = resolution
        self.depth = resolution.depth
        self.bound = bound
        self.completed = 0

    def step(self):
        """Run one more cycle. Refuses the 13th with DESIRE_BOUND_EXHAUSTED.

        Returns the number of cycles completed. Raises DesireBoundExhausted when the next cycle
        would be the (DESIRE_BOUND + 1)th. Nothing about depth changes either way.
        """
        nxt = self.completed + 1
        if nxt > self.bound:
            raise DesireBoundExhausted(requested=nxt, bound=self.bound, depth=self.depth,
                                       iterations_run=self.completed)
        self.completed = nxt
        return self.completed

    def run(self, cycles):
        """Run exactly `cycles` cycles, stopping at the bound. Returns the count completed.

        Runs in order and refuses the first cycle past the bound, so `run(12)` completes and
        `run(13)` raises on the 13th rather than up front: the bound is a per-cycle guard, not
        an argument pre-check.
        """
        if isinstance(cycles, bool) or not isinstance(cycles, int) or cycles < 0:
            raise ArchitectureViolation(f"cycles must be a non-negative int, got {cycles!r}")
        for _ in range(cycles):
            self.step()
        return self.completed

    @property
    def depth_now(self):
        """The loop's depth counter. Constant: an exhausted loop has not gone deeper."""
        return self.depth

    def __repr__(self):
        return (f"DesireLoop({self.resolution.notation!r}, cycles {self.completed}/{self.bound}, "
                f"depth={self.depth})")


class DeadlockResolution(Resolution):
    """The horizon verdict. Spawns nothing; the fix is `depth.flatten()`, not depth+1.

    "We define Structural Deadlock as the state where a recursive chain at depth n=5
    encounters another blocked node ... The architecture cannot spawn another level without
    violating the global stability axiom."
    """

    __slots__ = ("reason", "verdict")

    def __init__(self, node, depth, reason, notation=None, canon=CANON_DEADLOCK, note=""):
        self.reason = reason
        self.verdict = "STRUCTURAL_DEADLOCK"
        super().__init__(node, depth, DEADLOCK,
                         notation or f"STRUCTURAL_DEADLOCK[RPM({node.value}@{depth})]",
                         canon, note)

    @property
    def child_depth(self):
        return None


def child_chains(resolution):
    """The only sanctioned way to ask "what children did this produce?".

    Returns a tuple for Power and Wisdom resolutions; raises NoChildrenError for Desire and
    Deadlock resolutions, which structurally cannot have children.
    """
    if isinstance(resolution, SpawnedResolution):
        return resolution.children
    if isinstance(resolution, IterativeResolution):
        raise NoChildrenError(
            "a Desire resolution is ITERATIVE, not recursive: "
            "Phi_D: D_blocked -> (CO-1 o CO-4 o CO-7)^N does not spawn child chains."
        )
    if isinstance(resolution, DeadlockResolution):
        raise NoChildrenError(
            "a Structural Deadlock spawns nothing; the fix is depth.flatten(), "
            "horizontal decomposition at the same level."
        )
    raise NoChildrenError(f"{type(resolution).__name__} carries no child chains")


# ---------------------------------------------------------------------------
# The three functors.
# ---------------------------------------------------------------------------

def resolve(node, blocked, depth, state, *, wisdom_route="CO-6",
            iterative_exempt_at_horizon=True):
    """Dispatch a blocked node to exactly one resolution functor.

    Parameters
    ----------
    node     : Node or "D"/"W"/"P" -- the node that is blocked.
    blocked  : Blocked -- the block outcome. Required; an unblocked node is not a trigger.
    depth    : int >= 0 -- depth of the chain containing the block. Root chain is depth 0.
    state    : State -- carries the decomposition (CO-6 parts / CO-5 resonant child) and N.
    wisdom_route : "CO-6" (default) or "CO-5". Canon: "Phi_W: W_blocked -> (CO-5 v CO-6)".
        CO-6 is the coproduct route and needs >= 2 parts. CO-5 is the single-resonant-child
        route; it is NOT a coproduct and is tagged SINGLE, not PARALLEL.
    iterative_exempt_at_horizon : bool -- see UNDECIDED (U3) below.

    Returns one of SingleChildResolution / CoproductResolution / IterativeResolution /
    DeadlockResolution. Raises FunctorsRefused when an input cannot satisfy the functor.

    UNDECIDED IN CANON (U2): depth origin. Canon says "a maximum depth of 5 levels" and
    "a recursive chain at depth n=5", but never says whether the root chain is depth 0 or
    depth 1. This build pins the root at depth 0 and the horizon at 12 (the owner's ruling of
    2026-10-16; canon's number is 5), so a block at depth 12 is the deadlock and no chain can sit
    at depth 13. A root-at-1 reading would make "12 levels" mean depths 1..12; the arithmetic of
    the horizon check is identical, only the label of the root changes.

    UNDECIDED IN CANON (U3): whether a Desire block at the horizon is also a Structural
    Deadlock. Canon defines the deadlock as a chain at depth 5 that "encounters another
    blocked node" -- any node -- but also says Phi_D "does not contribute to the recursion
    depth limit". Both readings are exposed: with
    iterative_exempt_at_horizon=True (default) a D block at depth 12 (canon's 5; the horizon is
    12 by the owner's ruling of 2026-10-16) stays iterative at that depth; with False it
    deadlocks like P and W.

    The Desire loop's OWN bound is separate from the horizon and lives at DESIRE_BOUND = 12 (the
    owner's ruling of 2026-10-16, canon bounds N nowhere). A D block whose state asks for more
    than DESIRE_BOUND cycles raises DesireBoundExhausted -- word DESIRE_BOUND_EXHAUSTED -- and
    that is a different refusal from the horizon's STRUCTURAL_DEADLOCK in both meaning and code.
    """
    # Local import: depth.py imports Chain/Resolution from this module, so importing it at
    # module level would be a cycle.
    from depth import HORIZON as _HORIZON, DepthVerdict as _DepthVerdict, check_depth as _check_depth

    node = _as_node(node)
    if not isinstance(blocked, Blocked):
        raise ArchitectureViolation(
            "resolve() needs a Blocked outcome. Definition 27.2: the trigger is a BLOCK at a "
            "node, not a request to resolve a node in general."
        )
    if blocked.node is not node:
        raise ArchitectureViolation(
            f"blocked is on node {blocked.node.value} but resolve() was called for {node.value}"
        )
    if isinstance(depth, bool) or not isinstance(depth, int):
        raise ArchitectureViolation(f"depth must be an int, got {type(depth).__name__}")
    if depth < 0:
        raise ArchitectureViolation(f"depth must be >= 0, got {depth}")
    if not isinstance(state, State):
        raise ArchitectureViolation("state must be a State instance")

    # --- the horizon gate -------------------------------------------------
    # "a recursive chain at depth n=5 encounters another blocked node" -> deadlock.
    verdict = _check_depth(depth)
    if verdict is _DepthVerdict.STRUCTURAL_DEADLOCK:
        exempt = (node is Node.D) and iterative_exempt_at_horizon
        if not exempt:
            return DeadlockResolution(
                node=node, depth=depth,
                reason=(
                    f"blocked {node.name_long} node at depth {depth} == HORIZON {_HORIZON}: "
                    "structural capacity exhausted. No child chain is spawned at depth "
                    f"{depth + 1}. The fix is horizontal decomposition (depth.flatten), "
                    "not a deeper recursion."
                ),
            )
        # else: fall through to Phi_D, which adds no level and so cannot exhaust the horizon.

    # --- Phi_P: "It spawns a single child chain to solve a resource gap." --
    if node is Node.P:
        child = Chain(node=None, depth=depth + 1, tag=PENDING,
                      label=f"{state.label}.P", state=state.child(f"{state.label}.P"))
        return SingleChildResolution(
            node=Node.P, depth=depth, children=[child],
            notation=f"RPM({_DRIVE_P})[P -> CO-8 -> CO-9 -> RPM({_DRIVE_P}.P)]",
        )

    # --- Phi_W: "the Wisdom node splits into a coproduct of child chains" --
    if node is Node.W:
        if wisdom_route not in ("CO-5", "CO-6"):
            raise ArchitectureViolation("wisdom_route must be 'CO-5' or 'CO-6'")
        parts = tuple(state.decomposition)

        if wisdom_route == "CO-6":
            # "at least 2 required or refused" -- a coproduct of one is not a split.
            #
            # UNDECIDED IN CANON (U4): the minimum arity of the Wisdom coproduct. Canon says
            # the Wisdom node "splits into a coproduct of child chains" and prints a two-child
            # example, but never states a minimum. This build refuses 1: a coproduct of one is
            # not a split, and calling it parallel would misreport a single chain as a branch.
            if len(parts) < 2:
                raise FunctorsRefused(
                    f"Phi_W via CO-6 must split the Wisdom node into a coproduct of child "
                    f"chains: at least 2 parts required, State.decomposition has {len(parts)} "
                    f"({parts!r}). A single child is not a coproduct -- use wisdom_route='CO-5' "
                    "for the single resonant child, or supply >= 2 parts."
                )
            kids = [Chain(node=None, depth=depth + 1, tag=PENDING,
                          label=f"{state.label}.W.c{i + 1}",
                          state=state.child(f"{state.label}.W.c{i + 1}"))
                    for i in range(len(parts))]
            notation = ("RPM(F2)[W -> CO-6 -> "
                        + " + ".join(f"RPM({_DRIVE_W}.W.c{i + 1})" for i in range(len(parts)))
                        + "]")
            return CoproductResolution(
                node=Node.W, depth=depth, children=kids, notation=notation,
                note=("canon prints the 2-child case; this notation generalises the same "
                      "coproduct to n parts"),
            )

        # CO-5: "they find a specific professor whose lectures resonate with them".
        #
        # UNDECIDED IN CANON (U7): whether the CO-5 route is a "parallel morphism" at all.
        # Canon says Phi_W: W_blocked -> (CO-5 v CO-6) and calls Wisdom resolution "the only
        # case allowing parallel morphisms", but the CO-5 example in Chapter 5 produces ONE
        # resonant child, not a split. This build tags CO-5 SINGLE (not PARALLEL) and keeps
        # the >= 2 coproduct requirement on the CO-6 route only. The default route is CO-6.
        single = state.resonant_child
        if single is None and len(parts) == 1:
            single = parts[0]
        if single is None:
            raise FunctorsRefused(
                "Phi_W via CO-5 requires exactly one resonant child: set "
                "State.resonant_child (or supply a single-part decomposition)."
            )
        child = Chain(node=None, depth=depth + 1, tag=PENDING,
                      label=f"{state.label}.W", state=state.child(f"{state.label}.W"))
        return SingleChildResolution(
            node=Node.W, depth=depth, children=[child],
            notation=f"RPM({_DRIVE_W})[W -> CO-5 -> RPM({_DRIVE_W}.W)]",
            note="CO-5 route: one resonant child, NOT a coproduct; tagged SINGLE.",
        )

    # --- Phi_D: iterative, "does not spawn child chains", adds no level -----
    # "D_blocked -> (CO-1 o CO-4 o CO-7)^N"
    cycles = state.iterations
    if isinstance(cycles, bool) or not isinstance(cycles, int) or cycles < 0:
        raise ArchitectureViolation(f"State.iterations must be a non-negative int, got {cycles!r}")
    # THE SECOND NUMBER, applied where the loop is planned. Canon bounds N nowhere; the owner
    # ruled 12 on 2026-10-16. A request for more cycles than that is refused here, with the
    # loop's own word -- never with the horizon's. Note that this refusal cannot become a
    # Structural Deadlock: a Desire loop cycles in place, so `depth` is untouched by it.
    if cycles > DESIRE_BOUND:
        raise DesireBoundExhausted(requested=cycles, bound=DESIRE_BOUND, depth=depth,
                                   iterations_run=0)
    cycle = DesireCycle(operators=("CO-1", "CO-4", "CO-7"), iterations=cycles,
                        state_label=state.label)
    return IterativeResolution(
        node=Node.D, depth=depth, cycle=cycle,
        notation=f"RPM({_DRIVE_D})[D -> CO-1 -> CO-4 -> CO-7 -> loop({cycles})]",
    )


# ---------------------------------------------------------------------------
# Driver: build a whole tree under a scripted blockade schedule.
# ---------------------------------------------------------------------------

def expand(state, blockade, *, depth=0, parent=None, index=0, path=(),
           wisdom_route="CO-6", iterative_exempt_at_horizon=True,
           flatten_at_horizon=True):
    """Recursively resolve the chain at `depth`, then its children, and return the Chain tree.

    `blockade(depth, path) -> Node | None` is the scripted policy: which node (if any) is
    blocked in a chain at that depth, reached by that path. `path` is the tuple of node
    letters of the ancestors, so a policy can vary by position as well as by depth.

    When a chain hits the horizon, `expand` attaches `chain.horizontal = depth.flatten(chain)`
    -- "We move from vertical recursion to horizontal decomposition, preserving the stability
    of the manifold." [FULL_MANUSCRIPT_v2.md, line 6428]. It never spawns depth+1 there.

    This is a test/orchestration driver, not a scheduler: blocks are supplied, not detected.
    """
    from depth import HORIZON as _HORIZON
    from depth import flatten as _flatten

    node = None if blockade is None else blockade(depth, path)
    if node is not None:
        node = _as_node(node)

    chain = Chain(node=node, depth=depth, tag=UNBLOCKED if node is None else PENDING,
                  label=state.label, state=state, parent=parent, index=index)

    if node is None:
        return chain  # nothing blocked here: a leaf, no resolution needed

    resolution = resolve(node, Blocked(node, f"blocked at depth {depth}"), depth, state,
                         wisdom_route=wisdom_route,
                         iterative_exempt_at_horizon=iterative_exempt_at_horizon)
    chain.tag = resolution.tag
    chain.resolution = resolution

    if isinstance(resolution, SpawnedResolution):
        kids = []
        for i, child in enumerate(resolution.children):
            child.parent = chain
            child.index = i
            kids.append(expand(child.state, blockade, depth=child.depth, parent=chain,
                               index=i, path=path + (node.value,),
                               wisdom_route=wisdom_route,
                               iterative_exempt_at_horizon=iterative_exempt_at_horizon,
                               flatten_at_horizon=flatten_at_horizon))
        chain.children = tuple(kids)
    elif isinstance(resolution, DeadlockResolution):
        if flatten_at_horizon and chain.depth == _HORIZON:
            chain.horizontal = _flatten(chain)
    # IterativeResolution: no children, depth unchanged. Nothing to do by design.

    return chain
