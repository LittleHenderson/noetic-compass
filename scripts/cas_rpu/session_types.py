"""Shared types for the multi-session evaluation: the generator produces them, the harness consumes them.

Evaluation plan §3.2–3.3 (`docs/working/helm_eval_plan_draft_2026_10_06.md`).
A `SeedStream` is one context's whole event stream for one seed, split into
sessions by `boundaries`. Ground truth is the oracle over the WHOLE stream
(`revision.replay`), computed once and stored here, so no persistence
mechanism under test can influence it: the harness only has to know which
session an event index falls in.

This module is the contract between `sessions.py` (generator) and the
harness in `scripts/cas_memory`. It imports only `events` and `revision`
types and does no generation itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from events import Event, EventKind
from revision import Expectation, StreamDifficulty, WithdrawnExpectation


class SessionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class EpisodeSpan:
    """One episode inside a seed stream: a contiguous slice of its events."""

    variant: str                 # e.g. "R-stale", "X-delay", "T-compose", "G-probe"
    mechanism: str               # one letter: R H C N X D T G
    role: str                    # "diagnostic" | "control"
    start: int                   # first event index (inclusive)
    end: int                     # last event index (exclusive)
    designed_probe_index: int    # the probe the variant exists for
    designed_verdict: str        # YES | NO | UNKNOWN | INADMISSIBLE, as the oracle must agree
    cross_session: bool = False  # straddles at least one boundary by design

    def canonical(self) -> dict:
        return {
            "variant": self.variant, "mechanism": self.mechanism, "role": self.role,
            "start": self.start, "end": self.end,
            "designed_probe_index": self.designed_probe_index, "designed_verdict": self.designed_verdict,
            "cross_session": self.cross_session,
        }


@dataclass(frozen=True)
class SeedStream:
    """One context, one seed, one world: the whole stream, its split, and its oracle."""

    seed: int
    context_id: str
    closed_world: bool
    events: tuple[Event, ...]
    boundaries: tuple[int, ...]            # event index at which session k+1 begins; strictly increasing
    episodes: tuple[EpisodeSpan, ...]
    expectations: tuple[Expectation, ...]  # oracle over the whole stream, one per ASK
    withdrawn: tuple[WithdrawnExpectation, ...]
    refused: tuple[int, ...]
    twin_of: int | None = None             # set on an untaught twin: the primary's seed

    def __post_init__(self) -> None:
        n = len(self.events)
        if any(b <= 0 or b >= n for b in self.boundaries):
            raise SessionError("E-SS-003", f"boundary outside the stream (n={n}): {self.boundaries}")
        if list(self.boundaries) != sorted(set(self.boundaries)):
            raise SessionError("E-SS-003", f"boundaries must be strictly increasing: {self.boundaries}")
        asks = [i for i, e in enumerate(self.events) if e.kind is EventKind.ASK]
        if [x.event_index for x in self.expectations] != asks:
            raise SessionError("E-SS-004", "expectations do not line up with the ASK events")
        for k in range(1, self.sessions):
            lo, hi = self.session_range(k)
            if not any(lo <= x.event_index < hi for x in self.expectations):
                raise SessionError("E-SS-001", f"session {k + 1} contains no probe")

    @property
    def sessions(self) -> int:
        return len(self.boundaries) + 1

    def session_of(self, index: int) -> int:
        """0-based session number of an event index."""
        k = 0
        for b in self.boundaries:
            if index >= b:
                k += 1
        return k

    def session_range(self, k: int) -> tuple[int, int]:
        lo = 0 if k == 0 else self.boundaries[k - 1]
        hi = len(self.events) if k == len(self.boundaries) else self.boundaries[k]
        return lo, hi

    def session_events(self, k: int) -> tuple[Event, ...]:
        lo, hi = self.session_range(k)
        return self.events[lo:hi]

    def canonical(self) -> dict:
        return {
            "seed": self.seed, "context_id": self.context_id, "closed_world": self.closed_world,
            "events": [e.canonical() for e in self.events],
            "boundaries": list(self.boundaries),
            "episodes": [ep.canonical() for ep in self.episodes],
            "expectations": [x.canonical() for x in self.expectations],
            "withdrawn": [w.canonical() for w in self.withdrawn],
            "refused": list(self.refused),
            "twin_of": self.twin_of,
        }


@dataclass(frozen=True)
class SessionSet:
    """Every seed stream of one world, with its untaught twins and its fingerprint."""

    name: str
    kind: str
    seed: int
    difficulty: StreamDifficulty
    sessions: int
    closed_world: bool
    streams: tuple[SeedStream, ...] = field(default_factory=tuple)
    twins: tuple[SeedStream, ...] = field(default_factory=tuple)

    def canonical(self) -> dict:
        return {
            "name": self.name, "kind": self.kind, "seed": self.seed,
            "difficulty": self.difficulty.canonical(), "sessions": self.sessions,
            "closed_world": self.closed_world,
            "streams": [s.canonical() for s in self.streams],
            "twins": [t.canonical() for t in self.twins],
        }

    def fingerprint(self) -> str:
        blob = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def summary(self) -> dict:
        per_variant: dict[str, int] = {}
        probes = 0
        cross = 0
        for s in self.streams:
            probes += len(s.expectations)
            for ep in s.episodes:
                per_variant[ep.variant] = per_variant.get(ep.variant, 0) + 1
                cross += int(ep.cross_session)
        return {
            "streams": len(self.streams), "twins": len(self.twins), "sessions": self.sessions,
            "probes": probes, "cross_session_episodes": cross, "variants": dict(sorted(per_variant.items())),
        }
