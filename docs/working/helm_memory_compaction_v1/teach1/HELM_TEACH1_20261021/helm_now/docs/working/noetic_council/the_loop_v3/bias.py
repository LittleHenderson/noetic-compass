"""bias.py -- the Bias: the CJT's working memory, written by one coordinator, read by the next.

WHAT THIS MODULE DOES
---------------------
It implements the second row of the build plan's own table
(THE_BUILD_RESTART_PLAN_20261016.md:24):

    "**Bias** | the CJT's **working memory**. Attention writes relevant information into
     it; the next CJT reads it. A Bias snapshot is the `^5`. | be written by more than one
     coordinator."

So there are exactly four things here:

  * ``Bias(coordinator)`` -- one working memory, owned by one named coordinator.
  * ``write(key, value, coordinator)`` -- attention writing a named fact. It **increments the
    version by exactly one** and returns the new version. A different coordinator is refused.
  * ``read(key)`` -- the next CJT reading a fact it already has. A key that was never
    written is refused, never guessed.
  * ``snapshot()`` -- a frozen ``BiasSnapshot`` carrying the version and a sha256 digest over
    the version and the facts. The digest changes on every write.

Why the version is strict-increase only: the plan's return rule (THE_BUILD_RESTART_PLAN_20261016.md:69)
requires that "A returned thread must carry a **strictly newer** Bias; a stale or duplicate finish
may not wake an unrelated caller." A version that could stay still or go backwards could not
support that sentence, so ``check_version_increase()`` refuses anything that is not strictly
greater, and ``write()`` is the only thing that ever moves the number.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT decide what facts are relevant. Nothing here reads a thought, a station, an
    atlas node or an ASOM word: writing is the caller's act, not this module's judgement.
  * It does NOT hold live objects. A value must be a plain JSON value; anything else is
    refused rather than pickled, because a Bias is something a later reader has to be able to
    read without this process.
  * It does NOT gate anything, verdict anything, or refuse a turn. Its only refusals are
    about who may write and what a fact may be.
  * It does NOT run a turn, propose, observe, gate or disengage. That is ``loop.py``.
  * It reads no clock, no file, no network, and writes nothing to disk.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass

__all__ = [
    "Bias", "BiasSnapshot", "BiasRefusal", "check_version_increase", "digest_for",
    "BIAS_COORDINATOR_NOT_NAMED", "BIAS_OWNED_BY_ANOTHER_COORDINATOR",
    "BIAS_KEY_NOT_A_STRING", "BIAS_KEY_NOT_WRITTEN", "BIAS_VALUE_NOT_PLAIN",
    "BIAS_VERSION_WOULD_NOT_INCREASE",
]

#: Refusal codes. Every refusal carries one of these, so a caller reads one vocabulary.
BIAS_COORDINATOR_NOT_NAMED = "BIAS_COORDINATOR_NOT_NAMED"
BIAS_OWNED_BY_ANOTHER_COORDINATOR = "BIAS_OWNED_BY_ANOTHER_COORDINATOR"
BIAS_KEY_NOT_A_STRING = "BIAS_KEY_NOT_A_STRING"
BIAS_KEY_NOT_WRITTEN = "BIAS_KEY_NOT_WRITTEN"
BIAS_VALUE_NOT_PLAIN = "BIAS_VALUE_NOT_PLAIN"
BIAS_VERSION_WOULD_NOT_INCREASE = "BIAS_VERSION_WOULD_NOT_INCREASE"

# UNDECIDED IN SOURCES: who counts as "a coordinator" -- THE_BUILD_RESTART_PLAN_20261016.md:24 says one coordinator writes the Bias and never defines the coordinator's identity, its lifetime or its credentials, so this build takes a caller-supplied name string and compares it exactly, by value.

# UNDECIDED IN SOURCES: whether a fact may be overwritten once written -- the plan says attention writes relevant information into the Bias and says nothing about replacing a fact, so this build allows a later write under the same key, records it as a new version, and never refuses it.

# UNDECIDED IN SOURCES: whether a fact may ever be deleted from the Bias -- the sources describe writing and reading and give no delete, so this build has no delete at all rather than invent one.

# UNDECIDED IN SOURCES: which fields a Bias snapshot's digest must cover -- THE_BUILD_RESTART_PLAN_20261016.md:24 says a Bias snapshot is the ^5 and no source says what it hashes, so this build hashes the version and the facts in canonical JSON and records the coordinator beside the digest without hashing it.

# UNDECIDED IN SOURCES: whether the next CJT that reads may be a different coordinator from the one that wrote -- the plan says attention writes and the next CJT reads and does not say whether those are the same actor, so this build refuses a second WRITER and allows any reader.


class BiasRefusal(Exception):
    """A refusal with a stable code. Nothing here is ever a guess."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# What a fact may be
# --------------------------------------------------------------------------- #
_PLAIN_SCALARS = (bool, int, float, str, type(None))


def _plain(value, what: str):
    """Return a plain, owned copy of ``value``, or refuse it as not a plain fact.

    A Bias is read by a later reader, so its values must survive without this process. A
    tuple, a set, an object with methods, or a float that is not finite is refused rather
    than quietly converted, because a conversion would be this module inventing a fact.
    """
    if isinstance(value, _PLAIN_SCALARS):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise BiasRefusal(
                BIAS_VALUE_NOT_PLAIN,
                f"{what} is {value!r}; a Bias holds plain finite facts, and a NaN or an "
                "infinity does not survive a canonical digest",
            )
        return value
    if isinstance(value, list):
        return [_plain(item, f"{what}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise BiasRefusal(
                    BIAS_VALUE_NOT_PLAIN,
                    f"{what} has a key of type {type(key).__name__}; a fact's inner keys "
                    "must be strings so the value has one canonical form",
                )
            out[key] = _plain(item, f"{what}[{key!r}]")
        return out
    raise BiasRefusal(
        BIAS_VALUE_NOT_PLAIN,
        f"{what} is a {type(value).__name__}, which is not a plain JSON value; a Bias holds "
        "facts, not live objects",
    )


def _require_coordinator(coordinator) -> str:
    if not isinstance(coordinator, str) or not coordinator.strip():
        raise BiasRefusal(
            BIAS_COORDINATOR_NOT_NAMED,
            f"a coordinator must be named by a non-empty string, got {coordinator!r}; the "
            "Bias is written by ONE coordinator and nobody unnamed may write it",
        )
    return coordinator


def check_version_increase(before: int, after: int) -> int:
    """Return ``after`` only if it is strictly greater than ``before``.

    "A returned thread must carry a strictly newer Bias"
    [THE_BUILD_RESTART_PLAN_20261016.md:69]. Equal is not newer and smaller is not newer, so
    both are refused. This is the one guard the version rule is made of.
    """
    for name, number in (("before", before), ("after", after)):
        if isinstance(number, bool) or not isinstance(number, int):
            raise BiasRefusal(
                BIAS_VERSION_WOULD_NOT_INCREASE,
                f"{name} must be an int, got {type(number).__name__}",
            )
    if after <= before:
        raise BiasRefusal(
            BIAS_VERSION_WOULD_NOT_INCREASE,
            f"a Bias version must strictly increase: {before} -> {after} does not. A stale or "
            "duplicate Bias may not be presented as newer than the one it replaces",
        )
    return after


# --------------------------------------------------------------------------- #
# The digest
# --------------------------------------------------------------------------- #
def digest_for(version: int, facts) -> str:
    """sha256 over the version and the named facts, in canonical JSON.

    ``facts`` is an iterable of ``(key, value)`` pairs; they are sorted by key so the digest
    depends on what the Bias holds and not on the order it was written in.
    """
    payload = {
        "version": version,
        "facts": [[str(key), value] for key, value in sorted(facts, key=lambda pair: pair[0])],
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# The snapshot the next CJT reads
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BiasSnapshot:
    """One frozen reading of a Bias: its version, its facts, and a digest over both.

    Frozen on purpose. The next CJT reads a snapshot; it cannot write through it, and a
    snapshot taken at version 3 still says version 3 after the Bias moves to version 4.
    """

    version: int
    digest: str
    facts: tuple
    coordinator: str

    def keys(self) -> tuple:
        """Every fact name the snapshot carries, in sorted order."""
        return tuple(key for key, _ in self.facts)

    def has(self, key) -> bool:
        """True when this snapshot carries that named fact."""
        return any(stored == key for stored, _ in self.facts)

    def read(self, key):
        """The fact's value, or a refusal. A snapshot never guesses a fact."""
        for stored, value in self.facts:
            if stored == key:
                return copy.deepcopy(value)
        raise BiasRefusal(
            BIAS_KEY_NOT_WRITTEN,
            f"no fact named {key!r} was written to the Bias this snapshot was taken from; it "
            f"carries {list(self.keys())}",
        )

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "digest": self.digest,
            "coordinator": self.coordinator,
            "facts": [[key, copy.deepcopy(value)] for key, value in self.facts],
        }


# --------------------------------------------------------------------------- #
# The Bias itself
# --------------------------------------------------------------------------- #
class Bias:
    """The working memory: named facts, one writer, a version that only ever goes up.

    The version starts at 0 (nothing written). ``write`` moves it to exactly the old number
    plus one, so the versions a Bias passes through are 1, 2, 3, ... -- there is no setter, no
    ``version=`` argument, and no restore, which is what makes "strict-increase only" a
    property of the object rather than a promise in this docstring.
    """

    #: The version of a Bias nothing has been written to.
    VERSION_ORIGIN = 0

    def __init__(self, coordinator: str) -> None:
        self._coordinator = _require_coordinator(coordinator)
        self._facts: dict = {}
        self._version = self.VERSION_ORIGIN
        self._history: list = []

    # -- read-only views ---------------------------------------------------- #
    @property
    def coordinator(self) -> str:
        """The one coordinator allowed to write this Bias."""
        return self._coordinator

    @property
    def version(self) -> int:
        """The current version. Increments once per write, never reused, never lowered."""
        return self._version

    @property
    def keys(self) -> tuple:
        """Every named fact currently held, in sorted order."""
        return tuple(sorted(self._facts))

    def __repr__(self) -> str:
        return f"Bias(coordinator={self._coordinator!r}, version={self._version}, keys={list(self.keys)})"

    # -- writing ------------------------------------------------------------ #
    def write(self, key, value, coordinator) -> int:
        """Write one named fact under the owning coordinator. Returns the new version.

        Refuses, in this order: an unnamed writer, a writer who is not the owner, a key that
        is not a non-empty string, and a value that is not a plain fact. A refused write
        changes nothing -- the version does not move, which is why a refusal cannot be
        mistaken for a newer Bias.
        """
        _require_coordinator(coordinator)
        if coordinator != self._coordinator:
            raise BiasRefusal(
                BIAS_OWNED_BY_ANOTHER_COORDINATOR,
                f"this Bias is owned by {self._coordinator!r} and {coordinator!r} tried to "
                "write it. One coordinator writes the working memory; a second writer is "
                "refused, not merged",
            )
        if not isinstance(key, str) or not key.strip():
            raise BiasRefusal(
                BIAS_KEY_NOT_A_STRING,
                f"a fact needs a non-empty string name, got {key!r}",
            )
        plain = _plain(value, f"the value for {key!r}")

        self._version = check_version_increase(self._version, self._version + 1)
        self._facts[key] = plain
        self._history.append(
            {"version": self._version, "key": key, "digest": digest_for(self._version, self._facts.items())}
        )
        return self._version

    # -- reading ------------------------------------------------------------ #
    def read(self, key):
        """The named fact, or a refusal. Never a default, never a guess."""
        if not isinstance(key, str):
            raise BiasRefusal(BIAS_KEY_NOT_A_STRING, f"a fact name must be a string, got {key!r}")
        if key not in self._facts:
            raise BiasRefusal(
                BIAS_KEY_NOT_WRITTEN,
                f"no fact named {key!r} was ever written; this Bias carries {list(self.keys)}",
            )
        return copy.deepcopy(self._facts[key])

    def has(self, key) -> bool:
        """True when this Bias carries that named fact."""
        return isinstance(key, str) and key in self._facts

    def snapshot(self) -> BiasSnapshot:
        """A frozen reading of this Bias, with a digest over its version and its facts."""
        facts = tuple((key, copy.deepcopy(value)) for key, value in sorted(self._facts.items()))
        return BiasSnapshot(
            version=self._version,
            digest=digest_for(self._version, self._facts.items()),
            facts=facts,
            coordinator=self._coordinator,
        )

    def history(self) -> tuple:
        """Every write this Bias performed, in order: version, key and digest at that version."""
        return tuple(dict(entry) for entry in self._history)
