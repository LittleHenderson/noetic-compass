"""rpm_gate.py -- THE GATE. RPM decides PROCEED / REPAIR / REFUSE, from the turn's cause.

WHAT THIS MODULE DOES
---------------------
It is the RPM gate and the only gate. `rpm_gate(request)` answers one question -- may this
turn go on? -- and answers it with exactly one of three words:

    PROCEED   the section holds: nothing on the D/W/P chain is blocked and nothing the turn
              needs is missing. The action can be computed.
    REPAIR    a prerequisite is missing and a sub-goal can be opened to realize it. The gap is
              named exactly, and the sub-goal that would close it is named too.
    REFUSE    the gap cannot be closed from here: an ancestor is invalid, the returning Bias is
              not strictly newer, or the sub-goal would sit past the recursion horizon.

WHAT IT DECIDES ON
------------------
One record: the turn's cause (`RpmCause`) plus the Bias version the turn read. Nothing else.
The cause carries which node blocked, at what depth, whether the ancestor line is invalid, what
the runtime reports as missing, and the Bias versions of a returning thread.

`RpmCause` has no field for the ASOM label, the operating region, the semantic outcome or
whether the region was saturated. Neither does the request record it arrives on. That is the
structural half of "ASOM may never influence the gate"; the behavioural half is the 150-cell
forced-label matrix in `test_all.py`, run against this gate rather than against a placeholder.

WHAT IT DOES NOT DO
-------------------
  * It does NOT decide whether a node is blocked, what the depth is, or whether an ancestor is
    dirty. All of that arrives in the cause.
  * It does NOT decide the recursion depth limit. `dwp/depth.py` owns `HORIZON` and
    `check_depth`; this module never writes the number and never compares against it except
    through `depth.HORIZON`, which it reads from the copy.
  * It does NOT decide whether a dirty child invalidates its ancestors. `dwp/retraction.py`
    propagates the marking and answers `is_dirty`; this module only asks.
  * It does NOT decide whether a returning Bias is newer. `bias.check_version_increase` is the
    one guard, and this module calls it rather than re-implementing it.
  * It does NOT decide whether a block has a matching functor, or what that functor spawns.
    `dwp.resolve` dispatches to Phi_D / Phi_W / Phi_P and this module reads the result.
  * It does NOT perform a repair. A REPAIR verdict names the sub-goal; opening it is somebody
    else's act, and no code in this build opens one.
  * It does NOT flatten. At the horizon a Structural Deadlock is REFUSED, and the fix is named
    (`depth.flatten` at the same level) without being performed.
  * It does NOT read the ASOM module, import it, or have anywhere to put a label.
  * It reads no clock, no file, no network, and writes nothing to disk. The four engine
    modules under `dwp/` are loaded by path from that folder and are never modified.

CANON
-----
The gate paragraph this module implements, verbatim:

  "Failure Propagation (The RPM Gate)
   ... we use the 'RPM Gate' as our primary safety check before an AI is allowed to generate
   output. We treat the D/W/P chain as a sequence of strict mathematical conditional evaluations
   based on the eps o eta = id identity.
   If the section eta (the embedding) fails to satisfy a requirement -- for example, if the AI
   lacks the specific ^P (Principled) safety constraint for a requested task -- the retraction
   eps (the execution of Power) is mathematically blocked from executing.
   The 'Action' simply cannot be computed. It is not that the AI 'chooses' not to do it; it is
   that the system is architecturally, algebraically incapable of violating its prerequisites.
   The topos evaluates to 'Undetermined'."
      [Chapter_27_RPM_Structure.md, lines 65-73]

and the three rules the cause is read against:

  Definition 27.2 -- "a block at node K triggers a child chain R^(n+1) whose ultimate output
  realizes the prerequisite for K" [Chapter_27_RPM_Structure.md, line 47].
  The horizon -- "recursion is strictly limited to a maximum depth of 5 levels"
  [line 59]; "the fix is horizontal decomposition" [FULL_MANUSCRIPT_v2.md, line 6428].
  The invalidated chain -- "the block propagates back up the stack, and the entire parent chain
  is invalidated" [line 63]; a returned thread "must carry a strictly newer Bias"
  [THE_BUILD_RESTART_PLAN_20261016.md:69].

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import os
import sys
from dataclasses import dataclass

__all__ = [
    "GateVerdict", "RpmCause", "rpm_gate", "GateViolation",
    "PROCEED", "REPAIR", "REFUSE", "VERDICT_WORDS",
    "GATE_REQUEST_FIELDS", "RPM_CAUSE_FIELDS",
    "NOTHING_BLOCKED", "PREREQUISITE_MISSING", "BLOCK_NEEDS_A_CHILD_CHAIN",
    "FUNCTOR_NEEDS_INPUT", "ANCESTOR_DIRTY", "STALE_BIAS",
    "STRUCTURAL_DEADLOCK", "HORIZON_BREACHED", "NO_DEEPER_SUB_GOAL",
    "GATE_VERDICT_NOT_A_WORD", "RPM_REQUEST_NOT_A_GATE_REQUEST",
    "RPM_CAUSE_NOT_A_CAUSE", "RPM_CAUSE_REFUSED_BY_ENGINE",
    "dwp", "depth", "retraction", "VENDOR_DIR", "CLAIM_CEILING",
]

CLAIM_CEILING = "MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM."

# --------------------------------------------------------------------------- #
# The three words. They are the gate's, so they are defined here and imported by loop.py.
# --------------------------------------------------------------------------- #
PROCEED = "PROCEED"
REPAIR = "REPAIR"
REFUSE = "REFUSE"
VERDICT_WORDS = (PROCEED, REPAIR, REFUSE)

#: Why the gate said what it said. One code per case, so a reader never has to parse prose.
NOTHING_BLOCKED = "NOTHING_BLOCKED"
PREREQUISITE_MISSING = "PREREQUISITE_MISSING"
BLOCK_NEEDS_A_CHILD_CHAIN = "BLOCK_NEEDS_A_CHILD_CHAIN"
FUNCTOR_NEEDS_INPUT = "FUNCTOR_NEEDS_INPUT"
ANCESTOR_DIRTY = "ANCESTOR_DIRTY"
STALE_BIAS = "STALE_BIAS"
STRUCTURAL_DEADLOCK = "STRUCTURAL_DEADLOCK"
HORIZON_BREACHED = "HORIZON_BREACHED"
NO_DEEPER_SUB_GOAL = "NO_DEEPER_SUB_GOAL"

#: Refusal codes for a broken contract. These are errors, never verdicts.
GATE_VERDICT_NOT_A_WORD = "GATE_VERDICT_NOT_A_WORD"
RPM_REQUEST_NOT_A_GATE_REQUEST = "RPM_REQUEST_NOT_A_GATE_REQUEST"
RPM_CAUSE_NOT_A_CAUSE = "RPM_CAUSE_NOT_A_CAUSE"
RPM_CAUSE_REFUSED_BY_ENGINE = "RPM_CAUSE_REFUSED_BY_ENGINE"

# --------------------------------------------------------------------------- #
# The vendored engine, loaded by path.
#
# The four files under dwp/ are byte-for-byte copies of dwp_engine's modules. They are loaded
# from THIS folder, by path, under the module names their own top-level imports use
# ("import dwp", "from dwp import ..."), so not one byte of them has to change to be imported
# from here. Nothing in dwp_engine, the_loop or return_address is imported or modified.
# --------------------------------------------------------------------------- #
VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dwp")


def _load_vendored(name):
    """Load one vendored module by path and register it under its own name.

    Registration happens BEFORE the module body runs, because `depth.py` and `retraction.py`
    both import `dwp` at the top, and `dwp.py` imports `depth` lazily inside `resolve()`.
    """
    path = os.path.abspath(os.path.join(VENDOR_DIR, name + ".py"))
    already = sys.modules.get(name)
    if already is not None and os.path.abspath(getattr(already, "__file__", "") or "") == path:
        return already
    if not os.path.isfile(path):
        raise GateViolation(
            RPM_CAUSE_REFUSED_BY_ENGINE,
            f"the vendored engine module {name}.py is missing from {VENDOR_DIR}; the gate "
            "cannot decide without it and will not fall back to a second copy",
        )
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - a broken checkout
        raise GateViolation(
            RPM_CAUSE_REFUSED_BY_ENGINE, f"could not build an import spec for {path}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class GateViolation(Exception):
    """A refusal with a stable code. Raised for a broken contract, never as a verdict."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


dwp = _load_vendored("dwp")
depth = _load_vendored("depth")
retraction = _load_vendored("retraction")

import bias as bias_module  # noqa: E402 - the one version guard, borrowed not re-written

# --------------------------------------------------------------------------- #
# The two records the gate owns
# --------------------------------------------------------------------------- #
#: The exact fields a request must carry. Checked on every call: a request with a field this
#: gate does not know is refused, so a label cannot be smuggled on in a new field.
GATE_REQUEST_FIELDS = (
    "turn",
    "coordinator",
    "bias_version",
    "bias_digest",
    "proposal_text",
    "prerequisites",
    "cause",
)

#: The fields of the cause. Field names are part of the proof: none of them can carry a readout.
RPM_CAUSE_FIELDS = (
    "blocked_node",
    "depth",
    "ancestor_dirty",
    "dirty_ancestor",
    "dirty_reason",
    "unsatisfied",
    "resume_from_version",
    "wisdom_route",
    "decomposition",
    "resonant_child",
    "iterations",
    "state_label",
)

# The ten places canon does not settle what this gate does, each with the reading taken. They
# are listed again, word for word, in README.md, and a test fails if one goes missing there.
#
# UNDECIDED IN CANON: whether a block below the horizon is a REPAIR or a PROCEED -- canon says a block triggers a child chain (Definition 27.2) and that the gate stops the action when a requirement is unsatisfied (line 71), and never says which of the three words a resolvable block gets; this gate answers REPAIR because when the verdict is taken the prerequisite is still missing and nothing in this build opens the child chain.
# UNDECIDED IN CANON: whether the gap a REPAIR names must be a node of the D/W/P chain or a caller-supplied requirement -- canon's own example names a requirement ("the specific ^P (Principled) safety constraint for a requested task", line 71) while Definition 27.2 names a node; this gate prefers a caller-named requirement and falls back to the blocked node's own name.
# UNDECIDED IN CANON: whether a turn declares the prerequisites it needs at all, and whether the declared names must agree with the blocked node -- canon describes no declaration step; this gate records the declared names in its basis and never derives a gap from them, because the gap comes from the cause.
# UNDECIDED IN CANON: whether an invalidated ancestor line forbids a first attempt or only a resume -- canon says "the entire parent chain is invalidated" (line 63) and says nothing about a fresh evaluation; this gate refuses any turn whose chain or ancestor line is invalid, on the reading that an invalidated chain cannot be evaluated.
# UNDECIDED IN CANON: whether the gate itself may flatten at the horizon, or must only name the fix -- canon presents flattening as the fix and never says who performs it; this gate names the flatten plan in its verdict and performs no flatten.
# UNDECIDED IN CANON: whether a chain at a depth beyond the horizon is a refusal or an error -- depth.py refuses any block at or beyond HORIZON and depth.flatten is available only exactly at the horizon, so this gate refuses with HORIZON_BREACHED and names no fix.
# UNDECIDED IN CANON: whether a block on the Desire node at the horizon is also a Structural Deadlock -- canon defines the deadlock as a chain at level 5 that "encounters another blocked node" and also says Phi_D "does not contribute to the recursion depth limit"; this gate follows dwp.resolve's documented default (iterative_exempt_at_horizon=True), so a Desire block at the horizon is a REPAIR at the same depth, not a REFUSE.
# UNDECIDED IN CANON: whether "strictly newer" for a returning Bias means any greater version or exactly one greater -- return_address/stack.py records the same gap for the same rule; this gate accepts any strictly greater version, matching that reading.
# UNDECIDED IN CANON: whether N, the Desire loop's iteration count, is bounded anywhere, and what it defaults to -- canon writes loop(N) with no bound; this gate takes N from the caller and defaults to dwp.State's own default, so the two can never disagree about the number.
# UNDECIDED IN CANON: whether a horizon refusal should name the blocked node's prerequisite or the horizon itself as the gap -- canon names the deadlock and not the ask; this gate names the missing prerequisite so the ladder asks a real question, and puts the horizon in the reason.



@dataclass(frozen=True)
class RpmCause:
    """THE TURN'S CAUSE -- everything the gate is allowed to know about why it is asked.

    ``blocked_node``        which node of the D/W/P chain is blocked: "D", "W", "P", or None.
    ``depth``               the depth of the chain carrying that block (root is 0).
    ``ancestor_dirty``      True when a child resolution came back dirty and the ancestor line
                            was invalidated. ``dirty_ancestor`` names the ancestor the caller
                            reports; ``dirty_reason`` is the reason it was marked.
    ``unsatisfied``         the requirements the runtime reports as NOT realized, in the
                            caller's order. Definition 27.2's "prerequisite for K", named.
    ``resume_from_version`` the Bias version a returning thread was suspended at, or None for
                            an ordinary turn. A returning thread must be strictly newer.
    ``wisdom_route``        "CO-6" (coproduct, >= 2 parts) or "CO-5" (one resonant child).
    ``decomposition``       the CO-6 parts of a Wisdom state.
    ``resonant_child``      the CO-5 single resonant child.
    ``iterations``          N in the Desire loop's "(CO-1 o CO-4 o CO-7)^N".
    ``state_label``         the name of the state being evaluated.

    There is no field for a readout, a region, a semantic outcome or a saturation flag, and no
    catch-all through which one could arrive.
    """

    blocked_node: object = None
    depth: int = 0
    ancestor_dirty: bool = False
    dirty_ancestor: object = None
    dirty_reason: object = None
    unsatisfied: tuple = ()
    resume_from_version: object = None
    wisdom_route: str = "CO-6"
    decomposition: tuple = ()
    resonant_child: object = None
    iterations: int = 8
    state_label: str = "S"

    def as_dict(self) -> dict:
        return {
            "blocked_node": None if self.blocked_node is None else str(self.blocked_node),
            "depth": self.depth,
            "ancestor_dirty": self.ancestor_dirty,
            "dirty_ancestor": self.dirty_ancestor,
            "dirty_reason": self.dirty_reason,
            "unsatisfied": list(self.unsatisfied),
            "resume_from_version": self.resume_from_version,
            "wisdom_route": self.wisdom_route,
            "decomposition": list(self.decomposition),
            "resonant_child": self.resonant_child,
            "iterations": self.iterations,
            "state_label": self.state_label,
        }


@dataclass(frozen=True)
class GateVerdict:
    """What RPM decided, and everything a later reader needs to audit it.

    ``verdict``   PROCEED, REPAIR or REFUSE -- and nothing else can be constructed.
    ``gap``       the exact prerequisite that is missing, for REPAIR and REFUSE. A verdict that
                  cannot proceed and names nothing is refused by the ladder, not by this record.
    ``reason``    why, in a sentence that quotes the rule it was decided by.
    ``stub``      True only for the retained placeholder gate, which is not the default.
    ``rpm``       True for a verdict this module produced. A record can never be mistaken for
                  a stub after the fact, and a stub can never pass itself off as a decision.
    ``code``      one of the stable codes above.
    ``sub_goal``  for REPAIR: the sub-goal whose output would realize the gap, named by the
                  engine's own notation. For REFUSE: None. This gate opens nothing.
    ``fix``       for a horizon refusal: the flatten plan `depth.flatten` produced at the
                  horizon. Named, never performed.
    ``basis``     what was asked and what answered, in order, so the delegation is checkable.
    """

    verdict: str
    gap: object = None
    reason: object = None
    stub: bool = False
    rpm: bool = False
    code: object = None
    sub_goal: object = None
    fix: object = None
    basis: tuple = ()

    def __post_init__(self) -> None:
        if self.verdict not in VERDICT_WORDS:
            raise GateViolation(
                GATE_VERDICT_NOT_A_WORD,
                f"a gate verdict must be one of {list(VERDICT_WORDS)}, got {self.verdict!r}",
            )

    @property
    def can_proceed(self) -> bool:
        """True only for PROCEED. REPAIR and REFUSE both mean the turn may not continue."""
        return self.verdict == PROCEED

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "gap": self.gap,
            "reason": self.reason,
            "stub": self.stub,
            "rpm": self.rpm,
            "code": self.code,
            "sub_goal": self.sub_goal,
            "fix": self.fix,
            "basis": list(self.basis),
            "can_proceed": self.can_proceed,
        }


# --------------------------------------------------------------------------- #
# Reading the cause. Every refusal here is about a broken contract, never a verdict.
# --------------------------------------------------------------------------- #
def _as_node(value):
    """Coerce "D"/"W"/"P" (or a `dwp.Node`) to a `dwp.Node`, refusing anything else."""
    if isinstance(value, dwp.Node):
        return value
    try:
        return dwp.Node(str(value).upper())
    except ValueError:
        raise GateViolation(
            RPM_CAUSE_NOT_A_CAUSE,
            f"{value!r} is not a node of the D/W/P chain; the chain has exactly D, W and P",
        ) from None


def _request_fields(request):
    """The field names of the request, or a refusal if it is not a plain frozen record."""
    if not dataclasses.is_dataclass(type(request)):
        raise GateViolation(
            RPM_REQUEST_NOT_A_GATE_REQUEST,
            f"the gate is asked with a GateRequest, got {type(request).__name__}",
        )
    return tuple(field.name for field in dataclasses.fields(request))


def _checked(request):
    """Validate the request and its cause, and return the cause."""
    fields = _request_fields(request)
    if fields != GATE_REQUEST_FIELDS:
        raise GateViolation(
            RPM_REQUEST_NOT_A_GATE_REQUEST,
            f"the request carries the fields {list(fields)}; this gate knows exactly "
            f"{list(GATE_REQUEST_FIELDS)}. A request with any other field is refused rather "
            "than read, so a value the gate was never meant to see cannot arrive here",
        )
    version = request.bias_version
    if isinstance(version, bool) or not isinstance(version, int):
        raise GateViolation(
            RPM_REQUEST_NOT_A_GATE_REQUEST,
            f"bias_version must be an int, got {type(version).__name__}",
        )
    cause = request.cause
    if not isinstance(cause, RpmCause):
        raise GateViolation(
            RPM_CAUSE_NOT_A_CAUSE,
            f"the request carries a cause of type {type(cause).__name__}; this gate reads an "
            "RpmCause and nothing else",
        )
    if tuple(field.name for field in dataclasses.fields(RpmCause)) != RPM_CAUSE_FIELDS:
        raise GateViolation(
            RPM_CAUSE_NOT_A_CAUSE,
            "the cause's field list changed; the gate refuses to read a cause whose shape it "
            "has not been checked against",
        )
    if isinstance(cause.depth, bool) or not isinstance(cause.depth, int) or cause.depth < 0:
        raise GateViolation(
            RPM_CAUSE_NOT_A_CAUSE,
            f"depth must be a non-negative int, got {cause.depth!r}",
        )
    if not isinstance(cause.ancestor_dirty, bool):
        raise GateViolation(
            RPM_CAUSE_NOT_A_CAUSE,
            f"ancestor_dirty must be a bool, got {type(cause.ancestor_dirty).__name__}",
        )
    if cause.blocked_node is not None:
        _as_node(cause.blocked_node)
    if cause.wisdom_route not in ("CO-5", "CO-6"):
        raise GateViolation(
            RPM_CAUSE_NOT_A_CAUSE,
            f"wisdom_route must be 'CO-5' or 'CO-6', got {cause.wisdom_route!r}",
        )
    if isinstance(cause.iterations, bool) or not isinstance(cause.iterations, int):
        raise GateViolation(
            RPM_CAUSE_NOT_A_CAUSE,
            f"iterations must be an int, got {cause.iterations!r}. Canon bounds N nowhere "
            "(dwp_engine's own U8), so this gate checks only that it is a whole number >= 0",
        )
    if cause.iterations < 0:
        raise GateViolation(
            RPM_CAUSE_NOT_A_CAUSE, f"iterations must be >= 0, got {cause.iterations}"
        )
    if not isinstance(cause.unsatisfied, tuple):
        raise GateViolation(
            RPM_CAUSE_NOT_A_CAUSE,
            f"unsatisfied must be a tuple of names, got {type(cause.unsatisfied).__name__}",
        )
    for name in cause.unsatisfied:
        if not isinstance(name, str) or not name.strip():
            raise GateViolation(
                RPM_CAUSE_NOT_A_CAUSE,
                f"an unsatisfied requirement must be named by a non-empty string, got {name!r}; "
                "this gate never asks about an unnamed gap",
            )
    if cause.resume_from_version is not None and (
        isinstance(cause.resume_from_version, bool)
        or not isinstance(cause.resume_from_version, int)
    ):
        raise GateViolation(
            RPM_CAUSE_NOT_A_CAUSE,
            f"resume_from_version must be None or an int, got {cause.resume_from_version!r}",
        )
    return cause


def _state(cause):
    """The engine's State, built from the cause. Nothing is inferred beyond what it carries."""
    return dwp.State(
        label=cause.state_label,
        decomposition=cause.decomposition,
        resonant_child=cause.resonant_child,
        iterations=cause.iterations,
    )


def _prerequisite_name(cause):
    """The name of the prerequisite the blocked node is missing: the node's own, and its depth.

    Definition 27.2: "a block at node K triggers a child chain R^(n+1) whose ultimate output
    realizes the prerequisite for K". The prerequisite for K is K. Named, not numbered.
    """
    node = _as_node(cause.blocked_node)
    return "the %s (%s) prerequisite at depth %d" % (node.name_long, node.value, cause.depth)


def _needs(cause):
    """What a Wisdom functor needs that this state does not supply, or None if nothing.

    These are the only two ways `dwp.resolve` refuses a block: a CO-6 coproduct of one is not
    a split, and a CO-5 route needs a resonant child. The gate names the missing input from
    the cause; the engine's own refusal text is used as the reason, so the two cannot disagree
    (if they ever did, the gate raises instead of guessing a gap).
    """
    if cause.blocked_node is None or _as_node(cause.blocked_node) is not dwp.Node.W:
        return None
    if cause.wisdom_route == "CO-6" and len(cause.decomposition) < 2:
        return (
            "a CO-6 decomposition of the Wisdom node into at least 2 parts (the state carries "
            "%d)" % (len(cause.decomposition),)
        )
    if (
        cause.wisdom_route == "CO-5"
        and cause.resonant_child is None
        and len(cause.decomposition) != 1
    ):
        return (
            "a single resonant child for the Wisdom node (CO-5: State.resonant_child is not "
            "set and the decomposition is not a single part)"
        )
    return None


# --------------------------------------------------------------------------- #
# The ancestor line, delegated to dwp/retraction.py
# --------------------------------------------------------------------------- #
def _spine(depth_number, state):
    """A chain at `depth_number` wired to a full ancestor chain up to a root at depth 0.

    The gate does not decide anything here: it builds the chain the cause describes so that
    `retraction` can propagate on real links, exactly as canon's "back up the stack" is written.
    """
    root = dwp.Chain(node=None, depth=0, tag=dwp.UNBLOCKED, label="depth-0 chain", state=state)
    current = root
    for level in range(1, depth_number + 1):
        label = "depth-%d chain" % (level,)
        child = dwp.Chain(
            node=None,
            depth=level,
            tag=dwp.UNBLOCKED,
            label=label,
            state=state.child(label),
            parent=current,
            index=0,
        )
        current.children = (child,)
        current = child
    return current


def _invalid_line(cause):
    """Which chains in the ancestor line are invalid, and why. retraction.py answers."""
    chain = _spine(cause.depth, _state(cause))
    if not cause.ancestor_dirty:
        return (), chain, ()
    reason = cause.dirty_reason or retraction.DEFAULT_DIRTY_REASON
    offending = dwp.Chain(
        node=None,
        depth=chain.depth + 1,
        tag=dwp.PENDING,
        label="the dirty child",
        state=_state(cause),
        parent=chain,
        index=0,
    )
    chain.children = (offending,)
    marked = retraction.mark_dirty_upward(offending, reason=reason)
    invalid = tuple(c for c in chain.ancestors if retraction.is_dirty(c))
    return invalid, chain, marked


# --------------------------------------------------------------------------- #
# THE GATE
# --------------------------------------------------------------------------- #
def rpm_gate(request):
    """Decide PROCEED / REPAIR / REFUSE for one turn, from its cause and nothing else.

    The order of the checks is the order of the rules, and each rule is somebody else's:

      1. the ancestor line     -- dwp/retraction.py says whether a chain is invalid
      2. the returning Bias    -- bias.check_version_increase is the one strict-increase guard
      3. the block             -- dwp.resolve dispatches to Phi_D / Phi_W / Phi_P, and applies
                                  depth.check_depth's horizon itself, including the D-exemption
      4. the depth of the sub-goal a REPAIR would open -- depth.check_depth again

    A malformed request raises `GateViolation`. It never becomes a verdict, because a verdict
    is a decision about a turn and a broken record is not one.
    """
    cause = _checked(request)
    basis = []

    # ---- 1. THE ANCESTOR LINE ---------------------------------------------
    # "If a child chain at any level uses a 'dirty' resolution (e.g., a Power bypass), the
    #  retraction morphism fails, the block propagates back up the stack, and the entire parent
    #  chain is invalidated."  [Chapter_27_RPM_Structure.md, line 63]
    # Checked first, and nothing below may override it: an invalidated chain cannot be
    # evaluated, so no later answer about the block or the Bias can make this turn proceedable.
    invalid, _line, _marked = _invalid_line(cause)
    if invalid:
        basis.append(
            "retraction.is_dirty(ancestor line) -> INVALID: "
            + ", ".join(c.label for c in invalid)
        )
        nearest = invalid[0]
        gap = "a clean (un-invalidated) %s" % (nearest.label,)
        reported = (
            "the caller reports the ancestor %r is dirty (%s)"
            % (cause.dirty_ancestor, cause.dirty_reason or retraction.DEFAULT_DIRTY_REASON,)
            if cause.dirty_ancestor is not None
            else "the cause reports a dirty child (%s)"
            % (cause.dirty_reason or retraction.DEFAULT_DIRTY_REASON,)
        )
        return GateVerdict(
            verdict=REFUSE,
            gap=gap,
            reason=(
                "REFUSE: %s. retraction marked %d chain(s) invalid up to the root (%s), and the "
                "invalidation is destructive and cannot be undone, so no version of this turn "
                "may proceed on that chain. Canon: 'the block propagates back up the stack, and "
                "the entire parent chain is invalidated' "
                "[Chapter_27_RPM_Structure.md, line 63]."
                % (
                    reported,
                    len(invalid),
                    ", ".join(c.label for c in invalid),
                )
            ),
            rpm=True,
            code=ANCESTOR_DIRTY,
            basis=tuple(basis),
        )
    basis.append("retraction.is_dirty(ancestor line) -> clean")

    # ---- 2. THE RETURNING BIAS -------------------------------------------
    # A returned thread "must carry a strictly newer Bias; a stale or duplicate finish may not
    # wake an unrelated caller."  [THE_BUILD_RESTART_PLAN_20261016.md:69]
    if cause.resume_from_version is not None:
        try:
            bias_module.check_version_increase(cause.resume_from_version, request.bias_version)
        except bias_module.BiasRefusal as caught:
            basis.append("bias.check_version_increase(%d, %d) -> refused %s" % (
                cause.resume_from_version, request.bias_version, caught.code))
            return GateVerdict(
                verdict=REFUSE,
                gap="a Bias version strictly newer than %d (this turn read %d)"
                % (cause.resume_from_version, request.bias_version),
                reason=(
                    "REFUSE: this is a returning thread and its Bias is not strictly newer than "
                    "the one it was suspended at (%s). A stale or duplicate finish may not wake "
                    "a caller that has moved on. bias.check_version_increase refused it: %s"
                    % (
                        "the versions are equal" if request.bias_version
                        == cause.resume_from_version else "the version went backwards",
                        caught.detail,
                    )
                ),
                rpm=True,
                code=STALE_BIAS,
                basis=tuple(basis),
            )
        basis.append(
            "bias.check_version_increase(%d, %d) -> strictly newer"
            % (cause.resume_from_version, request.bias_version)
        )
    else:
        basis.append("bias.check_version_increase -> not asked (not a returning thread)")

    # ---- 3. IS ANYTHING ASKING FOR A DEEPER CHAIN AT ALL? -----------------
    # Declared-but-unrealized requirements are the gate's own input: canon's example is an AI
    # that "lacks the specific ^P (Principled) safety constraint for a requested task"
    # [Chapter_27_RPM_Structure.md, line 71].
    if cause.blocked_node is None and not cause.unsatisfied:
        basis.append("depth.check_depth -> not asked (nothing blocks, nothing is missing)")
        basis.append("dwp.resolve -> not asked (no block to resolve)")
        return GateVerdict(
            verdict=PROCEED,
            gap=None,
            reason=(
                "PROCEED: no node of the D/W/P chain is blocked and no requirement the turn "
                "carries is reported unrealized, so the section holds and the action may be "
                "computed. Basis: %s; declared prerequisites: %s"
                % ("; ".join(basis), list(request.prerequisites))
            ),
            rpm=True,
            code=NOTHING_BLOCKED,
            basis=tuple(basis),
        )

    # ---- 4. A NAMED MISSING REQUIREMENT ----------------------------------
    # Canon's name for the gap beats the node's own name when the caller has one, because it
    # is the requirement the section failed to satisfy.
    if cause.unsatisfied:
        gap = cause.unsatisfied[0]
        horizon = depth.check_depth(cause.depth)
        basis.append("depth.check_depth(%d) -> %s" % (cause.depth, horizon.name))
        if horizon is depth.DepthVerdict.STRUCTURAL_DEADLOCK:
            return GateVerdict(
                verdict=REFUSE,
                gap=gap,
                reason=(
                    "REFUSE: the gap %r can only be closed by a sub-goal at depth %d, and "
                    "dwp/depth.py reports a chain at depth %d may spawn nothing deeper "
                    "(HORIZON = %d, a stability horizon, not an arbitrary performance cap). No "
                    "sub-goal is opened, and this gate does not descend."
                    % (gap, cause.depth + 1, cause.depth, depth.HORIZON)
                ),
                rpm=True,
                code=NO_DEEPER_SUB_GOAL,
                basis=tuple(basis),
            )
        return GateVerdict(
            verdict=REPAIR,
            gap=gap,
            reason=(
                "REPAIR: the requirement %r is not realized, so the retraction cannot execute "
                "and the action cannot be computed. The gap is named and a sub-goal is opened "
                "for it: RPM(%s) at depth %d. Canon: if the section 'fails to satisfy a "
                "requirement ... the retraction eps (the execution of Power) is mathematically "
                "blocked from executing' [Chapter_27_RPM_Structure.md, line 71]. This gate "
                "opens nothing; it names the sub-goal and the turn does not proceed."
                % (gap, gap, cause.depth + 1)
            ),
            rpm=True,
            code=PREREQUISITE_MISSING,
            sub_goal="RPM(%s)@%d" % (gap, cause.depth + 1),
            basis=tuple(basis),
        )

    # ---- 5. A BLOCK: exactly one functor decides, and the horizon is its own -----
    # "a block at node K triggers a child chain R^(n+1) whose ultimate output realizes the
    #  prerequisite for K"  [Definition 27.2, line 47].
    node = _as_node(cause.blocked_node)
    basis.append("depth.check_depth(%d) -> %s (consulted by dwp.resolve)" % (
        cause.depth, depth.check_depth(cause.depth).name))
    try:
        resolution = dwp.resolve(
            node,
            dwp.Blocked(node, "blocked at depth %d" % (cause.depth,)),
            cause.depth,
            _state(cause),
            wisdom_route=cause.wisdom_route,
        )
    except dwp.FunctorsRefused as caught:
        gap = _needs(cause)
        if gap is None:  # pragma: no cover - the engine refused for a reason this gate cannot name
            raise GateViolation(
                RPM_CAUSE_REFUSED_BY_ENGINE,
                f"dwp.resolve refused the block but this gate cannot name what is missing: "
                f"{caught}. It will not invent a gap",
            ) from None
        basis.append("dwp.resolve(%s@%d) -> refused %s" % (
            node.value, cause.depth, type(caught).__name__))
        return GateVerdict(
            verdict=REPAIR,
            gap=gap,
            reason=(
                "REPAIR: the %s node is blocked and its functor cannot fire on the state the "
                "cause carries. The gap is named, and opening it is the sub-goal RPM(%s). "
                "dwp.resolve said: %s"
                % (node.name_long, gap, caught)
            ),
            rpm=True,
            code=FUNCTOR_NEEDS_INPUT,
            sub_goal="RPM(%s)@%d" % (gap, cause.depth + 1),
            basis=tuple(basis),
        )
    except dwp.ArchitectureViolation as caught:
        raise GateViolation(RPM_CAUSE_REFUSED_BY_ENGINE, str(caught)) from None

    basis.append("dwp.resolve(%s@%d) -> %s" % (node.value, cause.depth, resolution.tag))

    if isinstance(resolution, dwp.DeadlockResolution):
        gap = _prerequisite_name(cause)
        at_the_horizon = cause.depth == depth.HORIZON
        fix = None
        plan = ""
        if at_the_horizon:
            # The fix is flattening at the same level. Note carefully: this gate NAMES it and
            # does not perform it -- "the fix is horizontal decomposition"
            # [FULL_MANUSCRIPT_v2.md, line 6428] -- and horizontal decomposition is an act
            # nobody in this build performs. The chains flatten() builds are discarded with
            # the verdict; only the notation it produces is kept.
            blocked = dwp.Chain(
                node=node,
                depth=cause.depth,
                tag=dwp.PENDING,
                label=cause.state_label,
                state=_state(cause),
            )
            flattened = depth.flatten(blocked)
            fix = flattened.notation
            plan = (
                " depth.flatten names the fix at the same level: %s -- %d sibling(s) at depth "
                "%d, child_depth=%r, vertical levels added=%d. The gate refuses and does not "
                "descend."
                % (
                    flattened.notation,
                    len(flattened.siblings),
                    cause.depth,
                    flattened.child_depth,
                    flattened.vertical_levels_added,
                )
            )
        return GateVerdict(
            verdict=REFUSE,
            gap=gap,
            reason=(
                "REFUSE: a block on the %s node at depth %d is a Structural Deadlock -- the "
                "architecture cannot spawn a level %d chain without violating the global "
                "stability axiom [FULL_MANUSCRIPT_v2.md, line 6428].%s"
                % (
                    node.name_long,
                    cause.depth,
                    cause.depth + 1,
                    plan
                    if plan
                    else (
                        " depth %d is beyond HORIZON = %d, where no chain may sit at all, and "
                        "depth.flatten is available only at the horizon exactly, so no fix is "
                        "named here." % (cause.depth, depth.HORIZON)
                    ),
                )
            ),
            rpm=True,
            code=STRUCTURAL_DEADLOCK if at_the_horizon else HORIZON_BREACHED,
            fix=fix,
            basis=tuple(basis),
        )

    # Below the horizon, or a Desire loop (which adds no level): the block is repairable by
    # opening exactly the child chain its own functor names.
    gap = _prerequisite_name(cause)
    adds = "and adds no level (child_depth=%r)" % (resolution.child_depth,) if (
        isinstance(resolution, dwp.IterativeResolution)
    ) else "child chain depth %r" % (resolution.child_depth,)
    basis.append("resolution.child_depth -> %r" % (resolution.child_depth,))
    return GateVerdict(
        verdict=REPAIR,
        gap=gap,
        reason=(
            "REPAIR: the %s node is blocked at depth %d, so the prerequisite for it is missing "
            "and the retraction cannot execute. Its functor resolves the block: %s (%s, %s). "
            "The gap is named and the sub-goal is that resolution; this gate opens nothing."
            % (node.name_long, cause.depth, resolution.notation, resolution.tag, adds)
        ),
        rpm=True,
        code=BLOCK_NEEDS_A_CHILD_CHAIN,
        sub_goal=resolution.notation,
        basis=tuple(basis),
    )
