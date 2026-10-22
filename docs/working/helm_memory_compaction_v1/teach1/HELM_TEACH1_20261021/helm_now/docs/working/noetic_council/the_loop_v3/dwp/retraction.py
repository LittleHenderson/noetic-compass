"""retraction.py -- Section-Retraction integrity per depth, and dirty-child propagation.

WHAT THIS MODULE DOES
---------------------
1. `SectionRetraction` carries the eta (section / embed) and epsilon (retraction / realize)
   pair for ONE depth, and checks the identity epsilon o eta = id *at that depth only*.
2. `RetractionRegistry` holds one SectionRetraction per depth and `verify(depth)` consults
   only that depth's pair. Independence is not a claim here, it is a structural fact: the
   callables belonging to other depths are never invoked, and each pair keeps a call log so
   a test can prove it.
3. `dirty_child(chain, child_index)` marks one child resolution dirty, marks every ancestor
   above it invalid, and propagates the block all the way to the root. It returns a
   `DirtyReport` with the propagation path so the walk can be inspected.

WHAT THIS MODULE DOES NOT DO
----------------------------
- It does NOT decide on its own that a resolution is dirty. Canon gives one example ("a
  Power bypass") and no classification procedure, so the reason is supplied by the caller.
- It does NOT check eta o epsilon = id. Canon is explicit that the reverse is NOT required:
  "We do *not* require the reverse to be true: eta_I o epsilon_I = id_{R(I)}." Checking it
  would be a different, wrong theorem.
- It does NOT invalidate siblings of a dirty child; see UNDECIDED (U9).
- It does NOT restore a chain. Retraction is destructive in canon ("the retraction operation
  is destructive and cannot be safely undone"), so there is no un-dirty operation.
- It does NOT run anything inside Helm. It is a mechanism.

CANON
-----
"Definition 27.1 (RPM Structure). ... the section eta : id_Noetica => R (the embedding) and
the retraction epsilon : R => id_Noetica (the realization), satisfying the critical identity:
epsilon_I o eta_I = id_I for all states I in Obj(Noetica)."
    [Chapter_27_RPM_Structure.md, line 28-31]

"Theorem 27.3 (Depth-Wise Integrity). For any recursive depth n, the Section-Retraction
identity epsilon^(n) o eta^(n) = id^(n) must hold independently."
    [Chapter_27_RPM_Structure.md, line 61]

"This ensures that a child chain cannot resolve a block by violating the architecture. If a
child chain at any level uses a 'dirty' resolution (e.g., a Power bypass), the retraction
morphism fails, the block propagates back up the stack, and the entire parent chain is
invalidated. Structural integrity is preserved at every level of the recursion."
    [Chapter_27_RPM_Structure.md, line 63]
"""

from dataclasses import dataclass, field
from typing import Any, Tuple

from dwp import ArchitectureViolation, Chain

__all__ = [
    "CANON_DEF_27_1", "CANON_THM_27_3", "CANON_DIRTY",
    "SectionRetraction", "RetractionReport", "RetractionRegistry",
    "identity_pair", "dirty_child", "mark_dirty_upward", "DirtyReport",
    "is_dirty", "DEFAULT_DIRTY_REASON", "POWER_BYPASS_REASON",
]

CANON_DEF_27_1 = (
    '"Definition 27.1 (RPM Structure). ... the section \\eta : id => R (the embedding) and the '
    'retraction \\varepsilon : R => id (the realization), satisfying the critical identity: '
    '\\varepsilon_I o \\eta_I = id_I for all states I in Obj(Noetica)."  '
    "[Chapter_27_RPM_Structure.md, lines 28-31]"
)

CANON_THM_27_3 = (
    '"Theorem 27.3 (Depth-Wise Integrity). For any recursive depth n, the Section-Retraction '
    'identity \\varepsilon^(n) o \\eta^(n) = id^(n) must hold independently."  '
    "[Chapter_27_RPM_Structure.md, line 61]"
)

CANON_DIRTY = (
    '"If a child chain at any level uses a \'dirty\' resolution (e.g., a Power bypass), the '
    'retraction morphism fails, the block propagates back up the stack, and the entire parent '
    'chain is invalidated."  [Chapter_27_RPM_Structure.md, line 63]'
)

DEFAULT_DIRTY_REASON = (
    "dirty child resolution: the child did not satisfy epsilon o eta = id, so its retraction "
    "failed and the block propagates to every ancestor"
)

POWER_BYPASS_REASON = (
    "Power bypass: the child bridged a non-Power block with Power machinery (CO-8/CO-9 fired "
    "to cover a Wisdom or Desire gap) -- the example canon gives for a dirty resolution"
)

# Witnesses a pair is checked against when the caller supplies none. Any set of values that
# supports == is fine; the pair's own eta/eps define what the values mean.
DEFAULT_WITNESSES = (0, 1, 2, "alpha")


@dataclass(frozen=True)
class RetractionReport:
    """The outcome of one per-depth integrity check. Never aggregates other depths."""

    depth: int
    holds: bool
    witnesses_checked: Tuple[Any, ...]
    failures: Tuple[Any, ...]
    depths_consulted: Tuple[int, ...]
    note: str = ""

    def __str__(self):
        verdict = "HOLDS" if self.holds else "FAILS"
        return (f"RetractionReport(depth={self.depth}, epsilon o eta = id {verdict} on "
                f"{len(self.witnesses_checked)} witnesses, depths_consulted="
                f"{self.depths_consulted})")


class SectionRetraction:
    """The (eta, epsilon) pair for exactly ONE depth.

    `eta` embeds a state into the prerequisite structure; `epsilon` realizes it back down.
    Only epsilon o eta = id is checked. eta o epsilon = id is deliberately not required --
    "This missing equation is the mathematical formalization of the 'One-Way Valve.'"
    """

    __slots__ = ("depth", "eta", "eps", "label", "calls")

    def __init__(self, depth, eta, eps, label=""):
        if isinstance(depth, bool) or not isinstance(depth, int):
            raise ArchitectureViolation("a SectionRetraction is bound to one integer depth")
        if depth < 0:
            raise ArchitectureViolation(f"depth must be >= 0, got {depth}")
        if not callable(eta) or not callable(eps):
            raise ArchitectureViolation("eta and eps must be callable")
        self.depth = depth
        self.eta = eta
        self.eps = eps
        self.label = label or f"SR[{depth}]"
        self.calls = []  # [(depth, "eta"|"eps", witness)] -- the independence evidence

    # -- the pair, named as canon names it ----------------------------------
    def embed(self, state):
        """eta: the section. Moves a state up into its prerequisite structure."""
        self.calls.append((self.depth, "eta", state))
        return self.eta(state)

    def realize(self, rstate):
        """epsilon: the retraction. Projects a realized state back down."""
        self.calls.append((self.depth, "eps", rstate))
        return self.eps(rstate)

    def roundtrip(self, state):
        """epsilon o eta applied to one state."""
        return self.realize(self.embed(state))

    def roundtrip_holds(self, state):
        return self.roundtrip(state) == state

    # -- the theorem, at this depth only ------------------------------------
    def verify(self, depth, witnesses=None):
        """Check epsilon^(depth) o eta^(depth) = id^(depth), independently.

        Refuses any depth other than the one this pair is bound to: that refusal is what
        makes "must hold independently at every depth" enforceable rather than decorative.
        """
        if depth != self.depth:
            raise ArchitectureViolation(
                f"this SectionRetraction is bound to depth {self.depth} and cannot be used to "
                f"verify depth {depth}. Theorem 27.3: the identity holds INDEPENDENTLY at "
                "every depth, so each depth is checked with its own pair."
            )
        if witnesses is None:
            witnesses = DEFAULT_WITNESSES
        holders, failures = [], []
        for w in witnesses:
            if self.roundtrip_holds(w):
                holders.append(w)
            else:
                failures.append(w)
        return RetractionReport(
            depth=self.depth,
            holds=not failures,
            witnesses_checked=tuple(witnesses),
            failures=tuple(failures),
            depths_consulted=(self.depth,),
            note=("checked with this depth's own eta/eps only" if not failures
                  else f"{len(failures)} witness(es) broke epsilon o eta = id"),
        )

    def __repr__(self):
        return f"SectionRetraction(depth={self.depth}, label={self.label!r})"


def identity_pair(depth, label=""):
    """A SectionRetraction whose eta and eps are identities (kept only to make a valid pair)."""
    return SectionRetraction(depth, eta=lambda s: s, eps=lambda s: s, label=label or f"id[{depth}]")


class RetractionRegistry:
    """One SectionRetraction per depth, verified per depth and never across depths."""

    def __init__(self):
        self._pairs = {}

    def install(self, pair):
        if not isinstance(pair, SectionRetraction):
            raise ArchitectureViolation("install() takes a SectionRetraction")
        if pair.depth in self._pairs:
            raise ArchitectureViolation(f"depth {pair.depth} already has a pair installed")
        self._pairs[pair.depth] = pair
        return pair

    def pair(self, depth):
        try:
            return self._pairs[depth]
        except KeyError:
            raise ArchitectureViolation(f"no SectionRetraction installed for depth {depth}") from None

    def depths(self):
        return tuple(sorted(self._pairs))

    def verify(self, depth, witnesses=None):
        """Verify exactly one depth. No other depth's morphisms are touched."""
        pair = self.pair(depth)
        return pair.verify(depth, witnesses)

    def verify_all(self, witnesses=None):
        """Verify every installed depth, one independent per-depth check at a time."""
        return {d: self.verify(d, witnesses) for d in self.depths()}

    def total_calls(self, depth):
        return len(self.pair(depth).calls)


# ---------------------------------------------------------------------------
# Dirty children and upward propagation.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DirtyReport:
    """Result of marking a child resolution dirty.

    `invalidated` runs from the dirty child up to the root, in that order -- the propagation
    path canon describes: "the block propagates back up the stack, and the entire parent
    chain is invalidated."
    """

    child_label: str
    reason: str
    invalidated: Tuple[str, ...]
    root_invalidated: bool
    marked: Tuple[Chain, ...] = field(default=(), repr=False, compare=False)

    def __str__(self):
        return (f"DirtyReport({self.child_label} -> {' -> '.join(self.invalidated)}, "
                f"root_invalidated={self.root_invalidated})")

    def path_to_root(self):
        """The marked chains from the dirty child up to the root."""
        return self.marked


def mark_dirty_upward(chain, reason=DEFAULT_DIRTY_REASON):
    """Mark `chain` and every ancestor invalid. Returns (chain, parent, ..., root).

    The marking is in place: an invalidated chain IS invalid, so recording it elsewhere while
    the chain still claims validity would be the wrong way round. There is no undo -- canon's
    retraction "is destructive and cannot be safely undone".

    UNDECIDED IN CANON (U9): whether the SIBLINGS of a dirty child are also invalidated.
    Canon names only "the entire parent chain", which is the ancestor line. This build
    invalidates ancestors only and leaves same-level siblings valid; a dirty sibling does not
    license condemning the parts of a coproduct that resolved cleanly.
    """
    if not isinstance(chain, Chain):
        raise ArchitectureViolation("mark_dirty_upward() takes a Chain")
    marked = []
    cur = chain
    while cur is not None:
        cur.dirty = True
        cur.dirty_reason = reason if cur is chain else f"{reason} (propagated from {chain.label})"
        marked.append(cur)
        cur = cur.parent
    return tuple(marked)


def dirty_child(parent, child_index=0, reason=DEFAULT_DIRTY_REASON):
    """A child resolution came back dirty: invalidate it and the whole parent chain.

    `parent` is the chain that OWNS the offending child. The block propagates from that child
    through the parent and on to the root -- it does not stop at the first ancestor.

    UNDECIDED IN CANON (U10): what counts as dirty beyond the one example canon gives ("a
    Power bypass"). No classification procedure is published, so this function does not
    guess: the caller names the reason. `power_bypass()` is the named helper for the canon
    example; anything else must be named explicitly, which keeps an unnamed judgement out of
    the audit trail.
    """
    if not isinstance(parent, Chain):
        raise ArchitectureViolation("dirty_child() takes the parent Chain")
    if not parent.children:
        raise ArchitectureViolation(
            f"chain {parent.label!r} has no children, so it has no dirty child to report"
        )
    if isinstance(child_index, bool) or not isinstance(child_index, int):
        raise ArchitectureViolation("child_index must be an int")
    if not (0 <= child_index < len(parent.children)):
        raise ArchitectureViolation(
            f"child_index {child_index} out of range for {len(parent.children)} children"
        )
    child = parent.children[child_index]
    marked = mark_dirty_upward(child, reason)
    root = marked[-1]
    return DirtyReport(
        child_label=child.label,
        reason=reason,
        invalidated=tuple(c.label for c in marked),
        root_invalidated=bool(root.dirty),
        marked=marked,
    )


def power_bypass(parent, child_index=0):
    """The canon example of a dirty resolution, named as such."""
    return dirty_child(parent, child_index, reason=POWER_BYPASS_REASON)


def is_dirty(chain):
    """True if this chain (or anything it was told about) invalidated it."""
    if not isinstance(chain, Chain):
        raise ArchitectureViolation("is_dirty() takes a Chain")
    return bool(chain.dirty)
