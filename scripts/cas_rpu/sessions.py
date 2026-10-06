"""Session streams — the multi-session evaluation dataset (eval plan §3.2–3.3, §4, §8).

One seed stream is one context's whole event stream, built from *episodes* and
split into *sessions*. Every episode is either one of the sixteen existing
variants laid out by `revision._draw_item`, reused byte-for-byte and remapped
onto this stream's tokens, or one of the eleven cross-session variants defined
here, each of which is also built on a `_draw_item` draw (its shuffled setup,
its shadow, its distractors, its interleave, its probes) and then extended
across one or more session boundaries. Ground truth is `revision.replay` over
the WHOLE stream, in both worlds, exactly as `_admit` judges one item; the
split map never enters the oracle, which is what makes the oracle independent
of every persistence mechanism the harness puts under test.

Tokens are drawn without replacement within one stream: a shuffled copy of
the AA..ZZ pool is consumed in order and every draw of `_draw_item` is
remapped onto fresh pool tokens in first-appearance order. Distractors come
from spare nodes no chain node reaches, so routes never form between
episodes, and an episode's verdicts under the whole-stream oracle equal its
own (a test pins this for the sixteen reused variants).

Cross-session variants (mechanism letters X, D, T, G are new; C-cross is C;
N-late is N). Each is laid out as event GROUPS with a nominal session offset
from the episode's base session; `k` is the base session, `L` the designated
link, `c0..ch` the chain, GAP = UNKNOWN open / NO closed:

    X-delay    teach in s_k; ASK(c0,ch) -> YES in s_{k+3} (or the latest later
               session) with only unrelated episodes between; reverse -> GAP.
    X-revive   teach + YES in s_k; RETRACT L, GAP in s_{k+1}; FACT L, YES in
               s_{k+2}; YES again in s_{k+3} (designed). Compresses to fewer
               sessions but always keeps one boundary before the designed probe.
    X-deep     hold (c0,c_{i+1}) and (c0,ch) in s_k (L never first, as R-deep);
               RETRACT L in s_{k+1} -> both GAP (designed: main); both GAP in s_{k+2}.
    X-correct  hold YES in s_k; RETRACT L then FACT bypass legs (as C-bypassed's
               `with_bypass`) in s_{k+1}, ASK -> YES (designed); s_{k+2} YES and
               reverse -> GAP.
    X-hold     control: teach + YES in s_k; YES again in s_{k+1} (designed); reverse -> GAP.
    D-restate  FACT L given twice in s_k, YES; after a boundary RETRACT L once ->
               GAP (designed); a second RETRACT L is refused; sound half -> YES;
               reverse -> GAP (fourth probe, added so class D meets the ceiling).
    C-cross    hold YES in s_k; NEGATION L in s_{k+1} -> INADMISSIBLE with
               contested {L} (designed); INADMISSIBLE again after a boundary; then
               RETRACT L (accepted, contested pair) -> GAP.
    N-late     ASK(c0,ch) with L missing -> GAP in s_k; FACT L -> YES (designed)
               in s_{k+1}, reverse -> GAP; YES again in s_{k+2}.
    T-compose  teach the chain b..d in s_k; in s_{k+2} FACT(a,b), FACT(d,e) over two
               fresh tokens, ASK(a,e) -> YES (designed, never asked before); reverse -> GAP.
    T-exact    control: ASK(b,d) YES and reverse GAP in s_k; ASK(b,d) YES in s_{k+2} (designed).
    G-probe    §8.2 of the plan at hops = 3 over this stream's tokens, L = (b,c):
               steps 1–2 in s_k, steps 3–5 in s_{k+1}, step 6 and the duplicate
               RETRACT in s_{k+2}; designed = step 4 (INADMISSIBLE). Balancing
               ASK(c,d) -> YES in s_k as §8.2 says, plus ASK(a,b) -> YES in s_k and
               ASK(c,d) -> YES in s_{k+2}: with §8.2's single balancing probe the
               closed world is 5/7 NO, above the 60% ceiling, so two more YES
               probes are carried; the §8.3 table is unchanged and pinned by test.

Untaught twins (`twins=True`): for every X-* and T-* episode, every FACT whose
pair is an edge of the episode's chain (or a bypass leg) is replaced, in
place, by a FACT between two of the episode's spare tokens (distractor
sources and interleave nodes), taking ordered spare pairs in first-appearance
order and skipping pairs the episode already states. No chain node gains an
out-edge, so no probe gains a route; the designed X/T probes are then GAP in
both worlds, which is asserted. The twin is a deterministic function of the
primary, so the rng is consumed identically with twins on or off.

Rejection codes: the `revision` codes (E-RS-005/006/010 redraw the whole
seed stream, at most 64 times; E-RS-007 on the finished set; E-RS-008 when a
stream's pool runs dry; E-RS-004 on an argument fault) plus `SessionError`
E-SS-002 when the catalog cannot give every session 2..N a cross-session
designed probe for the requested `sessions`.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import events  # noqa: E402
from session_types import EpisodeSpan, SeedStream, SessionError, SessionSet  # noqa: E402
from events import DEFAULT_RELATION, Event, EventKind  # noqa: E402
from revision import (  # noqa: E402
    _POOL,
    _REDRAW,
    BALANCE_CEILING,
    VARIANTS,
    Expectation,
    RevisionError,
    StreamDifficulty,
    Verdict,
    _Design,
    _Draft,
    _draw_item,
    guard_balance,
    guard_hypotheses_fresh,
    guard_route_bounds,
    replay,
)


__all__ = [
    "CATALOG",
    "CROSS_VARIANTS",
    "EXISTING_VARIANTS",
    "KIND",
    "balance_report",
    "generate_session_set",
    "probe_owners",
]

KIND = "session_streams"

#: The sixteen existing variants, in `revision.VARIANTS` order.
EXISTING_VARIANTS: tuple[str, ...] = tuple(
    v for mechanism in VARIANTS for role in VARIANTS[mechanism] for v in role
)

#: variant -> (mechanism letter, role, base `_draw_item` variant, nominal group offsets).
#: The designed probe is never in the base group, so session 1 never carries a
#: cross-session designed probe and every placement keeps a boundary before it.
CROSS_VARIANTS: dict[str, tuple[str, str, str, tuple[int, ...]]] = {
    "X-delay": ("X", "diagnostic", "N-control", (0, 3)),
    "X-revive": ("X", "diagnostic", "R-stale", (0, 1, 2, 3)),
    "X-deep": ("X", "diagnostic", "R-deep", (0, 1, 2)),
    "X-correct": ("X", "diagnostic", "R-stale", (0, 1, 2)),
    "X-hold": ("X", "control", "N-control", (0, 1)),
    "D-restate": ("D", "diagnostic", "R-stale", (0, 1)),
    "C-cross": ("C", "diagnostic", "C-stale", (0, 1, 2)),
    "N-late": ("N", "diagnostic", "N-actionable", (0, 1, 2)),
    "T-compose": ("T", "diagnostic", "N-control", (0, 2)),
    "T-exact": ("T", "control", "N-control", (0, 2)),
    "G-probe": ("G", "diagnostic", "H-bridge", (0, 1, 2)),
}

#: Which group of each cross-session variant holds its designed probe.
_DESIGNED_GROUP: dict[str, int] = {
    "X-delay": 1, "X-revive": 3, "X-deep": 1, "X-correct": 1, "X-hold": 1,
    "D-restate": 1, "C-cross": 1, "N-late": 1, "T-compose": 1, "T-exact": 1, "G-probe": 1,
}

#: Variants whose teaching the twin removes.
_TWINNED = tuple(v for v in CROSS_VARIANTS if v[0] in "XT")

CATALOG: tuple[str, ...] = EXISTING_VARIANTS + tuple(CROSS_VARIANTS)

_ATTEMPTS = 64


# ---- tokens -----------------------------------------------------------------

class _Pool:
    """One stream's tokens: a shuffled copy of AA..ZZ, consumed in order."""

    def __init__(self, rng: random.Random) -> None:
        self.tokens = list(_POOL)
        rng.shuffle(self.tokens)
        self.cursor = 0

    def take(self, count: int = 1) -> list[str]:
        if self.cursor + count > len(self.tokens):
            raise RevisionError("E-RS-008", f"the AA..ZZ pool cannot name {self.cursor + count} nodes in one stream")
        out = self.tokens[self.cursor:self.cursor + count]
        self.cursor += count
        return out


def _remap(draft: _Draft, pool: _Pool) -> _Draft:
    """The same layout over fresh pool tokens, mapped in first-appearance order."""
    mapping: dict[str, str] = {}
    for e in draft.stream:
        for token in (e.subject, e.obj):
            if token not in mapping:
                mapping[token] = pool.take()[0]
    stream = [replace(e, subject=mapping[e.subject], obj=mapping[e.obj]) for e in draft.stream]
    return _Draft(stream, dict(draft.designed), draft.designed_probe)


# ---- reading a base draft ---------------------------------------------------

def _first(stream: Sequence[Event], kind: EventKind) -> int:
    return next(i for i, e in enumerate(stream) if e.kind is kind)


def _chain(stream: Sequence[Event], main: Event) -> list[str]:
    """c0..ch: walk from the main probe's subject over FACT/HYPOTHESIS `leads_to`
    edges. Chain nodes have exactly one out-edge (distractors leave spare
    nodes), so the walk is unique; anything else is a layout this module
    does not know."""
    succ: dict[str, set[str]] = {}
    for e in stream:
        if e.kind in (EventKind.FACT, EventKind.HYPOTHESIS) and e.relation == DEFAULT_RELATION:
            succ.setdefault(e.subject, set()).add(e.obj)
    chain = [main.subject]
    while chain[-1] != main.obj:
        nxt = succ.get(chain[-1], set())
        if len(nxt) != 1 or len(chain) > len(stream):
            raise RevisionError("E-RS-004", f"cannot read a chain out of the base draft at {chain[-1]}: {sorted(nxt)}")
        chain.append(next(iter(nxt)))
    return chain


def _edges(chain: Sequence[str]) -> list[tuple[str, str]]:
    return list(zip(chain, chain[1:]))


def _sound_half(chain: Sequence[str], link: tuple[str, str]) -> tuple[str, str]:
    """The side of the chain that stays sound when `link` is cut, as `_draw_item`
    chooses it: the longer side, left on a tie."""
    h = len(chain) - 1
    i = chain.index(link[0])
    left, right = (chain[0], chain[i]), (chain[i + 1], chain[-1])
    return left if i >= 1 and i >= h - 1 - i else right


# ---- an episode under construction ---------------------------------------------

@dataclass
class _Episode:
    variant: str
    mechanism: str
    role: str
    groups: list[list[Event]] = field(default_factory=lambda: [[]])
    offsets: list[int] = field(default_factory=lambda: [0])
    designed: dict[tuple[int, int], _Design] = field(default_factory=dict)
    designed_probe: tuple[int, int] | None = None
    chain_edges: tuple[tuple[str, str], ...] = ()   # edges whose FACTs the twin replaces
    protected: frozenset[str] = frozenset()         # tokens the twin never wires (chain, extras)

    @property
    def cross_session(self) -> bool:
        return len(self.groups) > 1

    def say(self, *evs: Event) -> None:
        self.groups[-1].extend(evs)

    def probe(self, event: Event, design: _Design, *, designed: bool = False) -> None:
        self.groups[-1].append(event)
        at = (len(self.groups) - 1, len(self.groups[-1]) - 1)
        self.designed[at] = design
        if designed:
            self.designed_probe = at

    def next_group(self, offset: int) -> None:
        self.groups.append([])
        self.offsets.append(offset)

    def carry(self, draft: _Draft, lo: int, hi: int, *, designed_at: int | None = None,
              override: dict[int, _Design] | None = None) -> None:
        """Copy `draft.stream[lo:hi]` with its designed verdicts, byte for byte."""
        for index in range(lo, hi):
            event = draft.stream[index]
            if index in draft.designed:
                design = (override or {}).get(index, draft.designed[index])
                self.probe(event, design, designed=(index == designed_at))
            else:
                self.say(event)

    def tokens(self) -> list[str]:
        out: list[str] = []
        for group in self.groups:
            for e in group:
                for token in (e.subject, e.obj):
                    if token not in out:
                        out.append(token)
        return out


# ---- the sixteen reused variants ----------------------------------------------

def _mechanism_of(variant: str) -> tuple[str, str]:
    for mechanism, (diagnostic, control) in VARIANTS.items():
        if variant in diagnostic:
            return mechanism, "diagnostic"
        if variant in control:
            return mechanism, "control"
    raise RevisionError("E-RS-004", f"unknown variant {variant!r}")


def _existing(rng: random.Random, diff: StreamDifficulty, pool: _Pool, variant: str) -> _Episode:
    mechanism, role = _mechanism_of(variant)
    draft = _remap(_draw_item(rng, diff, mechanism, variant), pool)
    ep = _Episode(variant, mechanism, role)
    ep.carry(draft, 0, len(draft.stream), designed_at=draft.designed_probe)
    return ep


# ---- the cross-session variants -------------------------------------------------

def _cross(rng: random.Random, diff: StreamDifficulty, pool: _Pool, variant: str) -> _Episode:
    mechanism, role, base, offsets = CROSS_VARIANTS[variant]
    if variant == "G-probe":
        diff = replace(diff, hops=3)
    draft = _remap(_draw_item(rng, diff, _mechanism_of(base)[0], base), pool)
    stream = draft.stream
    fa = _first(stream, EventKind.ASK)
    main = stream[draft.designed_probe]
    chain = _chain(stream, main)
    c0, ch = chain[0], chain[-1]
    reverse = events.ask(ch, c0)
    ep = _Episode(variant, mechanism, role, chain_edges=tuple(_edges(chain)), protected=frozenset(chain))

    if variant == "X-delay":
        ep.carry(draft, 0, fa)                                   # teach (setup + interleave)
        ep.next_group(offsets[1])
        ep.carry(draft, fa, len(stream), designed_at=draft.designed_probe)  # YES designed, reverse GAP
    elif variant == "X-hold":
        ep.carry(draft, 0, fa)
        ep.probe(main, _Design.YES)
        ep.next_group(offsets[1])
        ep.carry(draft, fa, len(stream), designed_at=draft.designed_probe)
    elif variant == "T-exact":
        ep.carry(draft, 0, len(stream))                           # YES, reverse GAP; none designed
        ep.next_group(offsets[1])
        ep.probe(main, _Design.YES, designed=True)
    elif variant == "T-compose":
        a, e = pool.take(2)
        ep.protected = ep.protected | {a, e}
        ep.carry(draft, 0, fa)
        ep.next_group(offsets[1])
        ep.say(events.fact(a, c0), events.fact(ch, e))
        ep.probe(events.ask(a, e), _Design.YES, designed=True)
        ep.probe(events.ask(e, a), _Design.GAP)
    elif variant in ("X-revive", "X-correct", "D-restate", "X-deep"):
        cut = _first(stream, EventKind.RETRACT)
        link = stream[cut].pair
        if variant == "X-deep":
            ep.carry(draft, 0, cut)
            ep.next_group(offsets[1])
            ep.carry(draft, cut, len(stream), designed_at=draft.designed_probe)
            ep.next_group(offsets[2])
            for ask in stream[-2:]:                               # main, then the intermediate
                ep.probe(ask, _Design.GAP)
        elif variant == "X-revive":
            ep.carry(draft, 0, cut)
            ep.next_group(offsets[1])
            ep.carry(draft, cut, len(stream))                     # RETRACT L, interleave, GAP
            ep.next_group(offsets[2])
            ep.say(events.fact(*link))
            ep.probe(main, _Design.YES)
            ep.next_group(offsets[3])
            ep.probe(main, _Design.YES, designed=True)
        elif variant == "X-correct":
            bypass = pool.take(diff.hops - 1)
            legs = [c0] + bypass + [ch]
            ep.chain_edges = ep.chain_edges + tuple(_edges(legs))
            ep.protected = ep.protected | set(bypass)
            ep.carry(draft, 0, cut)
            ep.next_group(offsets[1])
            ep.say(stream[cut], *(events.fact(*leg) for leg in _edges(legs)))
            ep.carry(draft, cut + 1, len(stream), designed_at=draft.designed_probe,
                     override={draft.designed_probe: _Design.YES})
            ep.next_group(offsets[2])
            ep.probe(main, _Design.YES)
            ep.probe(reverse, _Design.GAP)
        else:  # D-restate
            ep.carry(draft, 0, fa)
            ep.say(events.fact(*link))                            # the same FACT, a second time
            ep.carry(draft, fa, cut)
            ep.next_group(offsets[1])
            ep.carry(draft, cut, len(stream), designed_at=draft.designed_probe)
            ep.say(events.retract(*link))                         # refused: already gone
            ep.probe(events.ask(*_sound_half(chain, link)), _Design.YES)
            ep.probe(reverse, _Design.GAP)
    elif variant == "C-cross":
        cut = _first(stream, EventKind.NEGATION)
        link = stream[cut].pair
        ep.carry(draft, 0, cut)
        ep.next_group(offsets[1])
        ep.carry(draft, cut, len(stream), designed_at=draft.designed_probe)
        ep.next_group(offsets[2])
        ep.probe(main, _Design.INADMISSIBLE)
        ep.say(events.retract(*link))                             # accepted: a contested given
        ep.probe(main, _Design.GAP)
    elif variant == "N-late":
        chain_facts = [i for i, e in enumerate(stream)
                       if e.kind is EventKind.FACT and e.relation == DEFAULT_RELATION and e.pair in ep.chain_edges]
        cut = max(chain_facts)                                    # FACT L follows the shuffled setup
        ep.carry(draft, 0, cut)
        ep.probe(main, _Design.GAP)
        ep.next_group(offsets[1])
        ep.carry(draft, cut, len(stream), designed_at=draft.designed_probe)
        ep.next_group(offsets[2])
        ep.probe(main, _Design.YES)
    elif variant == "G-probe":
        a, b, c, d = chain
        roles = iter([events.fact(a, b), events.fact(c, d)])
        setup: list[Event] = []
        for e in stream[:fa]:
            if e.kind is EventKind.HYPOTHESIS:
                setup.append(events.hypothesis(b, c))
            elif e.relation != DEFAULT_RELATION:
                setup.append(events.associate(b, c))
            elif e.pair in ep.chain_edges:
                setup.append(next(roles))
            else:
                setup.append(e)
        ad = events.ask(a, d)
        ep.say(*setup)
        ep.probe(ad, _Design.GAP)                                 # step 1
        ep.say(events.negation(a, d))
        ep.probe(ad, _Design.NO)                                  # step 2
        ep.probe(events.ask(c, d), _Design.YES)                   # §8.2 balancing probe
        ep.probe(events.ask(a, b), _Design.YES)                   # ceiling (module doc)
        ep.next_group(offsets[1])
        ep.probe(ad, _Design.NO)                                  # step 3
        ep.say(events.fact(b, c))
        ep.probe(ad, _Design.INADMISSIBLE, designed=True)         # step 4
        ep.say(events.retract(b, c))
        ep.probe(ad, _Design.NO)                                  # step 5
        ep.next_group(offsets[2])
        ep.probe(ad, _Design.NO)                                  # step 6
        ep.say(events.retract(b, c))                              # duplicate: refused
        ep.probe(events.ask(c, d), _Design.YES)                   # ceiling (module doc)
    else:  # pragma: no cover - CROSS_VARIANTS is the only source of names
        raise RevisionError("E-RS-004", f"unknown variant {variant!r}")

    if ep.designed_probe is None or ep.designed_probe[0] != _DESIGNED_GROUP[variant]:
        raise RevisionError("E-RS-004", f"{variant}: designed probe is not in group {_DESIGNED_GROUP[variant]}")
    return ep


# ---- placement ------------------------------------------------------------------

def _designed_session(ep: _Episode, base: int, sessions: int) -> int:
    span = sessions - 1 - base
    return base + min(ep.offsets[ep.designed_probe[0]], span)


def _bases(rng: random.Random, episodes: list[_Episode], sessions: int) -> list[int]:
    """A base session per episode. Every session 2..N receives the designed probe
    of a distinct cross-session episode (E-SS-002 when the catalog cannot);
    the remaining cross-session episodes keep at least one boundary before
    their designed probe; single-session episodes land anywhere."""
    cross = [i for i, ep in enumerate(episodes) if ep.cross_session]
    rng.shuffle(cross)
    if sessions - 1 > len(cross):
        raise SessionError(
            "E-SS-002",
            f"{sessions} sessions need {sessions - 1} cross-session designed probes; the catalog has {len(cross)}",
        )
    def fits(i: int, base: int) -> bool:
        """Every group lands in its nominal session: no compression."""
        return base + episodes[i].offsets[-1] <= sessions - 1

    bases: dict[int, int] = {}
    for target in range(1, sessions):
        chosen = None
        for compress in (False, True):          # compress only when nothing fits
            for i in cross:
                if i in bases:
                    continue
                nominal = episodes[i].offsets[episodes[i].designed_probe[0]]
                base = max(0, target - nominal)
                if _designed_session(episodes[i], base, sessions) == target and (compress or fits(i, base)):
                    chosen = (i, base)
                    break
            if chosen:
                break
        if chosen is None:
            raise SessionError("E-SS-002", f"no cross-session episode can carry its designed probe into session {target + 1}")
        bases[chosen[0]] = chosen[1]
    for i in cross:
        if i not in bases:
            top = sessions - 1 - episodes[i].offsets[-1]
            bases[i] = rng.randrange(0, top + 1) if top >= 0 else rng.randrange(0, sessions - 1)
    return [bases[i] if ep.cross_session else rng.randrange(0, sessions) for i, ep in enumerate(episodes)]


@dataclass(frozen=True)
class _Laid:
    """One concatenated stream and where everything landed."""

    events: tuple[Event, ...]
    boundaries: tuple[int, ...]
    where: dict[tuple[int, int, int], int]          # (episode, group, local) -> event index
    designed: dict[int, _Design]                    # event index -> design
    episodes: tuple[_Episode, ...]
    sessions_of: tuple[tuple[int, ...], ...]        # per episode: the session of each group


def _lay_out(rng: random.Random, episodes: list[_Episode], sessions: int) -> _Laid:
    bases = _bases(rng, episodes, sessions)
    per_session: list[list[tuple[int, list[int]]]] = [[] for _ in range(sessions)]
    sessions_of: list[tuple[int, ...]] = []
    for i, (ep, base) in enumerate(zip(episodes, bases)):
        span = sessions - 1 - base
        placed = tuple(base + min(off, span) for off in ep.offsets)
        sessions_of.append(placed)
        for g, s in enumerate(placed):
            # groups of one episode that share a session stay one block, in order
            if per_session[s] and per_session[s][-1][0] == i:
                per_session[s][-1][1].append(g)
            else:
                per_session[s].append((i, [g]))
    stream: list[Event] = []
    boundaries: list[int] = []
    where: dict[tuple[int, int, int], int] = {}
    designed: dict[int, _Design] = {}
    for s in range(sessions):
        if s:
            boundaries.append(len(stream))
        blocks = per_session[s]
        rng.shuffle(blocks)
        for i, groups in blocks:
            for g in groups:
                for local, event in enumerate(episodes[i].groups[g]):
                    where[(i, g, local)] = len(stream)
                    if (g, local) in episodes[i].designed:
                        designed[len(stream)] = episodes[i].designed[(g, local)]
                    stream.append(event)
    return _Laid(tuple(stream), tuple(boundaries), where, designed, tuple(episodes), tuple(sessions_of))


# ---- admission ------------------------------------------------------------------

def _judge(stream: Sequence[Event], designed: dict[int, _Design], label: str) -> dict[bool, object]:
    """E-RS-005 on every probe in BOTH worlds, then E-RS-010, then E-RS-006 --
    `_admit`'s order, over the whole stream. Returns the replay per world."""
    truths = {}
    for world in (False, True):
        truth = replay(stream, world)
        by_index = {x.event_index: x for x in truth.expectations}
        if set(by_index) != set(designed):
            raise RevisionError("E-RS-005", f"{label}: a probe without a designed verdict")
        for index, design in designed.items():
            want, got = design.in_world(world), by_index[index].verdict
            if want is not got:
                raise RevisionError(
                    "E-RS-005",
                    f"{label}: designed {want.value} != oracle {got.value} at event {index} "
                    f"({'closed' if world else 'open'} world)",
                )
        truths[world] = truth
    guard_hypotheses_fresh(stream)
    guard_route_bounds(stream)
    return truths


def _spans(laid: _Laid, verdict_at: dict[int, Verdict]) -> tuple[EpisodeSpan, ...]:
    spans = []
    for i, ep in enumerate(laid.episodes):
        indices = [laid.where[(i, g, l)] for g, group in enumerate(ep.groups) for l in range(len(group))]
        probe = laid.where[(i,) + ep.designed_probe]
        spans.append(EpisodeSpan(
            ep.variant, ep.mechanism, ep.role, min(indices), max(indices) + 1,
            probe, verdict_at[probe].value, cross_session=len(set(laid.sessions_of[i])) > 1,
        ))
    return tuple(spans)


def _check_coverage(laid: _Laid, spans: Sequence[EpisodeSpan], sessions: int) -> None:
    def session_of(index: int) -> int:
        return sum(1 for b in laid.boundaries if index >= b)

    covered = {session_of(sp.designed_probe_index) for sp in spans if sp.cross_session}
    if 0 in covered:
        raise SessionError("E-SS-002", "session 1 carries a cross-session designed probe")
    missing = sorted(set(range(1, sessions)) - covered)
    if missing:
        raise SessionError("E-SS-002", f"sessions {[m + 1 for m in missing]} carry no cross-session designed probe")


def _stream(laid: _Laid, truths: dict, *, seed: int, context_id: str, closed_world: bool,
            twin_of: int | None = None) -> SeedStream:
    truth = truths[closed_world]
    verdict_at = {x.event_index: x.verdict for x in truth.expectations}
    return SeedStream(
        seed, context_id, closed_world, laid.events, laid.boundaries, _spans(laid, verdict_at),
        truth.expectations, truth.withdrawn, truth.refused, twin_of,
    )


# ---- twins ----------------------------------------------------------------------

def _twin_events(laid: _Laid) -> tuple[Event, ...]:
    """The primary's events with every X/T teaching FACT replaced in place by a
    FACT between two spare tokens of the same episode (module doc)."""
    stream = list(laid.events)
    for i, ep in enumerate(laid.episodes):
        if ep.variant not in _TWINNED:
            continue
        positions = [
            laid.where[(i, g, l)] for g, group in enumerate(ep.groups) for l, e in enumerate(group)
            if e.kind is EventKind.FACT and e.relation == DEFAULT_RELATION and e.pair in ep.chain_edges
        ]
        stated = {e.pair for group in ep.groups for e in group if e.kind is EventKind.FACT and e.relation == DEFAULT_RELATION}
        spares = [t for t in ep.tokens() if t not in ep.protected]
        fresh = [(u, v) for u in spares for v in spares if u != v and (u, v) not in stated]
        if len(fresh) < len(positions):
            raise RevisionError("E-RS-008", f"{ep.variant}: {len(spares)} spare tokens cannot replace {len(positions)} teaching facts")
        for position, pair in zip(positions, fresh):
            stream[position] = events.fact(*pair)
    return tuple(stream)


def _twin(laid: _Laid, *, seed: int, context_id: str, closed_world: bool) -> SeedStream:
    stream = _twin_events(laid)
    truths = {world: replay(stream, world) for world in (False, True)}
    for world, truth in truths.items():
        by_index = {x.event_index: x.verdict for x in truth.expectations}
        for i, ep in enumerate(laid.episodes):
            if ep.variant in _TWINNED:
                index = laid.where[(i,) + ep.designed_probe]
                if by_index[index] is not _Design.GAP.in_world(world):
                    raise RevisionError(
                        "E-RS-005", f"twin of seed {seed}: {ep.variant} designed probe at {index} is "
                        f"{by_index[index].value}, not GAP ({'closed' if world else 'open'} world)",
                    )
    guard_hypotheses_fresh(stream)
    guard_route_bounds(stream)
    twin_laid = replace(laid, events=stream)
    return _stream(twin_laid, truths, seed=seed, context_id=context_id, closed_world=closed_world, twin_of=seed)


# ---- balance --------------------------------------------------------------------

@dataclass(frozen=True)
class _Tally:
    """What `guard_balance` reads of an item: its mechanism and its probes."""

    mechanism: str
    expectations: tuple[Expectation, ...]


def probe_owners(stream: SeedStream) -> dict[int, int]:
    """probe event index -> position in `stream.episodes` of the episode it belongs to.

    Spans of different episodes interleave, so containment alone cannot say
    whose a probe is; tokens can, because episodes never share one. Every
    event joins its two tokens; the component holding an episode's designed
    probe is that episode's. The one probe that can sit in a component of
    its own is R-control's off-path ask (a distractor cycle that never
    touches the chain): it is attributed to the span that contains it and
    whose designed probe lies inside the component's index range, which is
    exact because a single-session episode is one contiguous block. The
    generator checks this reconstruction against the layout it came from.
    """
    parent: dict[str, str] = {}

    def find(token: str) -> str:
        parent.setdefault(token, token)
        while parent[token] != token:
            parent[token] = parent[parent[token]]
            token = parent[token]
        return token

    lo: dict[str, int] = {}
    hi: dict[str, int] = {}
    for j, e in enumerate(stream.events):
        parent[find(e.subject)] = find(e.obj)
    for j, e in enumerate(stream.events):
        root = find(e.subject)
        lo[root] = min(lo.get(root, j), j)
        hi[root] = max(hi.get(root, j), j)
    anchor: dict[str, int] = {}
    for k, ep in enumerate(stream.episodes):
        root = find(stream.events[ep.designed_probe_index].subject)
        if root in anchor:
            raise RevisionError("E-RS-004", f"episodes {anchor[root]} and {k} share a token component")
        anchor[root] = k
    owners: dict[int, int] = {}
    for x in stream.expectations:
        root = find(x.subject)
        if root in anchor:
            owners[x.event_index] = anchor[root]
            continue
        found = [
            k for k, ep in enumerate(stream.episodes)
            if ep.start <= x.event_index < ep.end and lo[root] <= ep.designed_probe_index <= hi[root]
        ]
        if len(found) != 1:
            raise RevisionError("E-RS-004", f"probe at event {x.event_index} belongs to {len(found)} episodes")
        owners[x.event_index] = found[0]
    return owners


def _tallies(stream: SeedStream) -> list[_Tally]:
    owners = probe_owners(stream)
    per: dict[int, list[Expectation]] = {k: [] for k in range(len(stream.episodes))}
    for x in stream.expectations:
        per[owners[x.event_index]].append(x)
    return [_Tally(ep.mechanism, tuple(per[k])) for k, ep in enumerate(stream.episodes)]


def _verify_owners(laid: _Laid, stream: SeedStream) -> None:
    truth = {
        laid.where[(i, g, l)]: i
        for i, ep in enumerate(laid.episodes) for g, group in enumerate(ep.groups) for l, e in enumerate(group)
        if e.kind is EventKind.ASK
    }
    if probe_owners(stream) != truth:
        raise RevisionError("E-RS-004", f"seed {stream.seed}: probe attribution by tokens disagrees with the layout")


def balance_report(sset: SessionSet, *, twins: bool = False) -> dict:
    """Per mechanism letter over the primary streams (or the twins): probes, the
    verdict mix and the largest share -- the number E-RS-007 is judged on."""
    classes: dict[str, dict] = {}
    for stream in (sset.twins if twins else sset.streams):
        for tally in _tallies(stream):
            entry = classes.setdefault(tally.mechanism, {"probes": 0, "verdicts": {}})
            for x in tally.expectations:
                entry["probes"] += 1
                entry["verdicts"][x.verdict.value] = entry["verdicts"].get(x.verdict.value, 0) + 1
    for entry in classes.values():
        entry["verdicts"] = dict(sorted(entry["verdicts"].items()))
        top_verdict, top = max(entry["verdicts"].items(), key=lambda kv: (kv[1], kv[0]))
        entry["max_share"] = round(top / entry["probes"], 4)
        entry["max_verdict"] = top_verdict
    return {"closed_world": sset.closed_world, "twins": twins, "classes": dict(sorted(classes.items()))}


# ---- the generator --------------------------------------------------------------

def _draw_seed(rng: random.Random, diff: StreamDifficulty, sessions: int, seed: int) -> tuple[_Laid, dict]:
    """One attempt at one seed stream: draw, lay out, judge."""
    pool = _Pool(rng)
    episodes = [_existing(rng, diff, pool, v) for v in EXISTING_VARIANTS]
    episodes += [_cross(rng, diff, pool, v) for v in CROSS_VARIANTS]
    laid = _lay_out(rng, episodes, sessions)
    truths = _judge(laid.events, laid.designed, f"seed {seed}")
    return laid, truths


def generate_session_set(
    seeds: Iterable[int],
    difficulty: StreamDifficulty | None = None,
    sessions: int = 5,
    closed_world: bool = False,
    name: str = KIND,
    ceiling: float = BALANCE_CEILING,
    twins: bool = True,
) -> SessionSet:
    """One seed stream per seed (plus its untaught twin), split into `sessions`.

    Each seed stream carries every variant of `CATALOG` once. It is drawn,
    judged against the oracle on every probe in both worlds (E-RS-005), for
    a hypothesis on a held pair (E-RS-010) and against the bank's route
    bounds (E-RS-006) over the WHOLE stream, and redrawn as a whole on any of
    those faults, at most 64 times. The finished set is judged against
    `ceiling` per mechanism letter in both worlds (E-RS-007). `closed_world`
    never touches the rng, so paired sets are byte-identical in events and
    boundaries; `twins` never touches it either.
    """
    seeds = tuple(seeds)
    if not seeds or len(set(seeds)) != len(seeds) or any(not isinstance(s, int) or isinstance(s, bool) for s in seeds):
        raise RevisionError("E-RS-004", f"seeds must be distinct integers; got {seeds!r}")
    if not isinstance(sessions, int) or sessions < 2:
        raise RevisionError("E-RS-004", f"sessions must be an integer >= 2; got {sessions!r}")
    if not 0.0 < ceiling <= 1.0:
        raise RevisionError("E-RS-004", f"ceiling must be in (0, 1]; got {ceiling!r}")
    diff = difficulty or StreamDifficulty()

    streams: list[SeedStream] = []
    paired: list[SeedStream] = []
    twin_streams: list[SeedStream] = []
    for seed in seeds:
        rng = random.Random(seed)
        for attempt in range(_ATTEMPTS):
            try:
                laid, truths = _draw_seed(rng, diff, sessions, seed)
                break
            except RevisionError as exc:
                if exc.code not in _REDRAW or attempt == _ATTEMPTS - 1:
                    raise
        else:  # pragma: no cover - the loop always breaks or raises
            raise RevisionError("E-RS-005", f"seed {seed}: exhausted retries")
        context_id = f"seed{seed}"
        primary = _stream(laid, truths, seed=seed, context_id=context_id, closed_world=closed_world)
        _check_coverage(laid, primary.episodes, sessions)
        _verify_owners(laid, primary)
        streams.append(primary)
        paired.append(_stream(laid, truths, seed=seed, context_id=context_id, closed_world=not closed_world))
        if twins:
            twin = _twin(laid, seed=seed, context_id=f"{context_id}-twin", closed_world=closed_world)
            _verify_owners(replace(laid, events=twin.events), twin)
            twin_streams.append(twin)

    for world_streams in (streams, paired):
        guard_balance([t for s in world_streams for t in _tallies(s)], ceiling=ceiling)
    return SessionSet(name, KIND, seeds[0], diff, sessions, closed_world, tuple(streams), tuple(twin_streams))


# ---- command line -------------------------------------------------------------------

def _parse_seeds(text: str) -> list[int]:
    out: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.extend(range(int(lo), int(hi) + 1))
        elif part:
            out.append(int(part))
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the fingerprint and summary of a session set, both worlds.")
    parser.add_argument("--seeds", default="0-19", help="e.g. 0-19 or 0,1,5")
    parser.add_argument("--sessions", type=int, default=5)
    parser.add_argument("--hops", type=int, default=StreamDifficulty().hops)
    parser.add_argument("--no-twins", action="store_true")
    args = parser.parse_args(argv)
    diff = StreamDifficulty(hops=args.hops)
    for closed in (False, True):
        sset = generate_session_set(_parse_seeds(args.seeds), diff, sessions=args.sessions,
                                    closed_world=closed, twins=not args.no_twins)
        print(f"{'closed' if closed else 'open'} world  seeds={args.seeds} sessions={args.sessions} "
              f"difficulty={diff.label()}")
        print(f"  fingerprint {sset.fingerprint()}")
        print(f"  summary     {json.dumps(sset.summary(), sort_keys=True)}")
        print(f"  balance     {json.dumps(balance_report(sset)['classes'], sort_keys=True)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
