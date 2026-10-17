"""test_all.py -- one runnable test file for the loop build. No pytest needed.

WHAT THIS FILE DOES
-------------------
It proves every rule the owning instruction names, with explicit cases and explicit numbers,
and prints one PASS or FAIL line per case plus a total. Run it with:

    python -B test_all.py

It covers:

  * the Bias refuses a second coordinator, and a refused write moves nothing;
  * the Bias version increments by exactly one per write, snapshot digests change on every
    write, an older snapshot does not move, and the version guard refuses any non-increase;
  * the Bias never invents a fact, never holds a live object, and cannot be told a version;
  * a full turn runs all five stages in order and the record carries each stage's output;
  * the proposal is proposed under the Bias it cites, and a citation of an unwritten fact is
    refused;
  * the ASOM label is computed from the three observation inputs, and all four labels plus
    NOT_EMITTED are reachable;
  * **the ASOM label never changes the gate verdict** -- the full matrix of turns is run once
    with the label computed and once with it forced to every possible output, including a
    forced MISALIGNED, and the decisions must be identical every time;
  * **the ASOM label never changes a disengage decision** -- same matrix, comparing the
    ladder's steps, its ask, its reason and the turn's outcome;
  * **the build is not allowed to pass by being vacuous**: the forced labels are checked to
    have actually differed from the computed ones, and a copy of ``loop.py`` that lets the
    label gate is compiled and run, and the same test must catch it;
  * the gate is the only thing that can stop a turn, and the only thing that can allow one;
  * **the real RPM gate** decides PROCEED when nothing blocks, REPAIR when a prerequisite is
    missing and names the exact gap and the sub-goal, REFUSE at the recursion horizon (naming
    the flatten fix rather than descending), REFUSE when an ancestor is dirty whatever else is
    true, and REFUSE when a returning thread's Bias is not strictly newer;
  * every one of those rules is checked twice: once against the gate's verdict and once
    against the module the rule belongs to (``depth.check_depth``, ``dwp.resolve``,
    ``retraction``, ``bias.check_version_increase``), so the gate cannot quietly re-implement
    one of them;
  * when the gate cannot proceed, the ladder runs and names the exact gap it was given;
  * the ladder's four steps appear in order in the receipt;
  * a disengage carries a reason, and a disengage without one is refused; a gate that names
    no gap is refused rather than asked vaguely;
  * the copied files -- including the four vendored engine modules in ``dwp/`` -- are
    byte-identical to the hashes recorded in ``PROVENANCE.md``, and the source packages they
    came from re-hash to the same values on this machine;
  * the readout is a display with nothing to gate with;
  * ``README.md`` states the claim ceiling and lists every undecided line.

WHAT THIS FILE DOES NOT DO
--------------------------
  * It does NOT prove that anything ran inside Helm. Nothing here is a Helm run, and no claim
    about a real CJT, a real model or a real mind is made or checked.
  * It does NOT prove that a repair happened, that a sub-goal was opened, or that a horizon
    chain was flattened. The gate names each of those and performs none of them.
  * It does NOT prove anything was thought, meant, or understood. Every case is a mechanism
    check.
  * It does NOT use pytest, numpy, torch, any network, or any cloud service. Standard library
    only, and it runs in well under a second.
  * It does NOT write any file.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import dataclasses
import hashlib
import inspect
import os
import platform
import re
import sys
import types

BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

import asom
import bias
import disengage
import loop
import rpm_gate

CLAIM_CEILING = "MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM."

#: The cases, in the order they run.
CASES = []


def case(function):
    """Register one test case."""
    CASES.append(function)
    return function


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
#: A gap name and a reason, said the way the ladder wants them said. Both are TEST strings:
#: this build never invents either, and the gate is what supplies them.
GAP = "the energy budget for the next crossing"
GATE_REASON = "the budget was never supplied, so the crossing cannot be paid for"

REGIONS = ("CUTOFF", "ACTIVE", "BREAKDOWN")
SEMANTIC_OUTCOMES = ("INTENDED", "OPPOSITE", "OFF_AXIS", "UNKNOWN", "UNASSESSED")
SATURATION = (False, True)

OWN_MODULES = ("bias.py", "loop.py", "rpm_gate.py")
COPIED_MODULES = ("asom.py", "disengage.py")
#: The engine, copied read-only into dwp/ and hashed in PROVENANCE.md like the other copies.
VENDORED_MODULES = ("dwp.py", "depth.py", "retraction.py", "lacunarity.py")

#: Where each copy came from, so the SOURCE file can be re-hashed as well as the copy. These
#: folders are read to compute a digest and for nothing else: nothing here is imported from
#: them, and a build checked out without them still passes (the runner says how many it saw).
SOURCE_ROOT = r"C:\Users\wakil\Documents\Codex\2026-10-16"
SOURCE_FOLDERS = {
    "asom.py": os.path.join(SOURCE_ROOT, "continuity_build_v3"),
    "disengage.py": os.path.join(SOURCE_ROOT, "continuity_build_v3"),
    "dwp.py": os.path.join(SOURCE_ROOT, "dwp_engine"),
    "depth.py": os.path.join(SOURCE_ROOT, "dwp_engine"),
    "retraction.py": os.path.join(SOURCE_ROOT, "dwp_engine"),
    "lacunarity.py": os.path.join(SOURCE_ROOT, "dwp_engine"),
}

#: The line in loop.py that the mutation check rewrites. It is looked up by text, so if the
#: line ever moves or changes, the test fails loudly instead of quietly proving nothing.
GATE_LINE = "        verdict = self._gate(request)  # THE GATE DECIDES. Nothing else may."


def ascii_safe(value):
    """A string that is safe to print on a console that cannot take every character."""
    return ascii(str(value))


#: The only annotations a field of a record the gate reads is allowed to carry. Anything else
#: would be a live object on the record -- a place a readout could hide.
PLAIN_ANNOTATIONS = ("int", "bool", "str", "tuple", "object", "None", "NoneType")


def is_plain_record(cls):
    """True when every field of ``cls`` is annotated as a plain value."""
    for field in dataclasses.fields(cls):
        if str(field.type) not in PLAIN_ANNOTATIONS:
            return False
    return True


def field_names(cls):
    """The field names of a record, in order."""
    return [field.name for field in dataclasses.fields(cls)]


def read_build_file(name):
    with open(os.path.join(BUILD_DIR, name), encoding="utf-8") as handle:
        return handle.read()


def locate_copy(name):
    """Where a copy actually sits: the build folder, or the vendored engine folder."""
    for candidate in (os.path.join(BUILD_DIR, name), os.path.join(BUILD_DIR, "dwp", name)):
        if os.path.isfile(candidate):
            return candidate
    raise AssertionError("%s is not in the build folder or in its dwp/ folder" % (name,))


def a_bias(coordinator="cjt-1"):
    """A Bias with one fact written, the way stage 1 will find it."""
    working = bias.Bias(coordinator)
    working.write("goal", "cross to the next node", coordinator)
    return working


def a_proposer(module=loop, cites=("goal",)):
    """A proposer that reads the Bias it is handed and cites one of its facts."""

    def propose(snapshot):
        text = "propose a crossing toward %s" % (snapshot.read("goal") if cites else "nothing",)
        return module.Proposal(text=text, cites=cites)

    return propose


def forced(label):
    """An ASOM reader that ignores its inputs and returns ``label`` -- a forced readout."""

    def readout(region, outcome, saturated=False):
        return label

    return readout


def counting(readout):
    """Wrap a reader and count its calls, so "called once per turn" is checkable."""
    calls = []

    def wrapper(*args, **kwargs):
        calls.append((args, kwargs))
        return readout(*args, **kwargs)

    wrapper.calls = calls
    return wrapper


def capturing(gate, sink):
    """Wrap a gate so every GateRequest it is given is kept."""

    def wrapper(request):
        sink.append(request)
        return gate(request)

    return wrapper


def policies(module):
    """The five gates this file asks a turn to run under.

    One of them is the real RPM gate, which is the loop's default. The other four are written
    here so that a refusal or a repair caused by the gate can be exercised, and the placeholder
    is kept only because a record must be able to say, after the fact, that a verdict was not
    an RPM decision. What they all share is that they read the GateRequest and nothing else.
    """
    return (
        ("proceeding", module.proceeding_gate),
        ("rpm", module.rpm_gate),
        ("refusing", module.refusing_gate(GAP, GATE_REASON)),
        ("repairing", module.repairing_gate(GAP, GATE_REASON)),
        ("refusing-with-no-reason", module.refusing_gate(GAP, "")),
    )


def matrix_run(module=loop, reader=None, records_everything=False):
    """Run the whole matrix of turns and return one row per cell.

    The matrix is every operating region x every semantic outcome x both saturation flags,
    crossed with every gate this file knows. Each row is:

        (policy, region, outcome, saturated, decision, outcome word, label)

    ``decision`` is ``TurnRecord.decision()``, which carries every value the turn decided and
    deliberately does not carry the ASOM label.
    """
    if reader is None:
        reader = asom.readout
    requests = []
    rows = []
    tallies = []
    for policy_name, gate in policies(module):
        engine = module.Loop(
            a_bias("cjt-matrix"),
            "cjt-matrix",
            a_proposer(module),
            gate=capturing(gate, requests),
            asom_reader=reader,
        )
        for region in REGIONS:
            for outcome in SEMANTIC_OUTCOMES:
                for saturated in SATURATION:
                    record = engine.turn(
                        region, outcome, saturated, prerequisites=("desire", "wisdom", "power")
                    )
                    rows.append(
                        (policy_name, region, outcome, saturated, record.decision(),
                         record.outcome, record.asom_label)
                    )
                    if records_everything:
                        tallies.append(record)
    return rows, requests, tallies


def decisions_of(rows):
    """Just the decisions, in matrix order."""
    return [row[4] for row in rows]


def labels_of(rows):
    return [row[6] for row in rows]


# --------------------------------------------------------------------------- #
# The causes this file feeds the real gate
# --------------------------------------------------------------------------- #
#: Test names, never production values: the gap strings are written here so that a change in
#: the gate's own wording cannot silently match itself.
NAMED_GAP = "the ^P safety constraint for a requested task"


def a_request(**changes):
    """A GateRequest the real gate will accept, with the caller's changes applied."""
    fields = dict(
        turn=1,
        coordinator="cjt-1",
        bias_version=1,
        bias_digest="d",
        proposal_text="p",
        prerequisites=("desire", "wisdom", "power"),
        cause=rpm_gate.RpmCause(),
    )
    fields.update(changes)
    return loop.GateRequest(**fields)


def build_cause(cause_class, **changes):
    """An RpmCause of whichever class the module under test defines.

    The gate checks that its cause is its own class, so a broken copy of the gate taken in
    memory needs a cause of that copy's class. Nothing else changes.
    """
    fields = dict(
        blocked_node=None,
        depth=0,
        ancestor_dirty=False,
        dirty_ancestor=None,
        dirty_reason=None,
        unsatisfied=(),
        resume_from_version=None,
        wisdom_route="CO-6",
        decomposition=(),
        resonant_child=None,
        iterations=8,
        state_label="S",
    )
    fields.update(changes)
    return cause_class(**fields)


def a_cause(**changes):
    """The real gate's cause, with the caller's changes applied."""
    return build_cause(rpm_gate.RpmCause, **changes)


HORIZON = rpm_gate.depth.HORIZON

#: Every cause this file exercises, as (name, the cause's fields, declared parallels, Bias
#: version). Named as fields rather than as causes so the same list can be rebuilt for another
#: copy of the gate.
CAUSE_FIELDS = (
    ("nothing-blocked", {}, (), 1),
    ("blocked-power", dict(blocked_node="P", depth=2), ("power",), 1),
    ("blocked-wisdom", dict(blocked_node="W", depth=1, decomposition=("a", "b")), ("wisdom",), 1),
    ("blocked-desire", dict(blocked_node="D", depth=3, iterations=4), ("desire",), 1),
    ("wisdom-needs-parts", dict(blocked_node="W", depth=1), ("wisdom",), 1),
    ("wisdom-needs-a-resonant-child", dict(blocked_node="W", depth=1, wisdom_route="CO-5"), ("wisdom",), 1),
    ("named-gap", dict(blocked_node="P", depth=2, unsatisfied=(NAMED_GAP,)), ("power",), 1),
    ("named-gap-alone", dict(unsatisfied=(NAMED_GAP,)), (), 1),
    ("power-at-horizon", dict(blocked_node="P", depth=HORIZON), ("power",), 1),
    ("wisdom-at-horizon", dict(blocked_node="W", depth=HORIZON, decomposition=("a", "b")), ("wisdom",), 1),
    ("desire-at-horizon", dict(blocked_node="D", depth=HORIZON), ("desire",), 1),
    ("beyond-horizon", dict(blocked_node="P", depth=HORIZON + 1), ("power",), 1),
    ("dirty-ancestor", dict(ancestor_dirty=True, dirty_ancestor="the depth-0 chain",
                            dirty_reason="a Power bypass"), (), 1),
    ("dirty-and-at-horizon", dict(blocked_node="P", depth=HORIZON, ancestor_dirty=True,
                                  dirty_reason="a Power bypass"), ("power",), 1),
    ("stale-return", dict(resume_from_version=1), (), 1),
    ("newer-return", dict(resume_from_version=0), (), 1),
)


def cause_rows(cause_class=None):
    """The whole decision surface, as causes of the module under test."""
    if cause_class is None:
        cause_class = rpm_gate.RpmCause
    return tuple(
        (name, build_cause(cause_class, **fields), prerequisites, version)
        for name, fields, prerequisites, version in CAUSE_FIELDS
    )


def request_for(cause, prerequisites=(), bias_version=1):
    """A request for the real loop's gate, with a cause of any RpmCause class."""
    return a_request(
        bias_version=bias_version, prerequisites=prerequisites, cause=cause
    )


def cause_matrix_run(module=loop, reader=None, cause_class=None):
    """Run every cause through every observation cell, and return one row per turn.

    The matrix is 16 causes x (3 regions x 5 semantic outcomes x 2 saturation flags) = 480
    turns, each one run under the module's own ``rpm_gate``. With ``loop`` that is the real
    RPM gate, so this is the forced-label proof run against the real decision.
    """
    if reader is None:
        reader = asom.readout
    rows = []
    requests = []
    for name, cause, prerequisites, bias_version in cause_rows(cause_class):
        engine = module.Loop(
            a_bias("cjt-causes"),
            "cjt-causes",
            a_proposer(module),
            gate=capturing(module.rpm_gate, requests),
            asom_reader=reader,
        )
        for region in REGIONS:
            for outcome in SEMANTIC_OUTCOMES:
                for saturated in SATURATION:
                    record = engine.turn(
                        region, outcome, saturated, prerequisites=prerequisites, cause=cause
                    )
                    rows.append(
                        (name, region, outcome, saturated, record.decision(), record.outcome,
                         record.asom_label, record)
                    )
    return rows, requests


# --------------------------------------------------------------------------- #
# The Bias
# --------------------------------------------------------------------------- #
@case
def bias_refuses_a_second_coordinator():
    """One coordinator writes the working memory. A second writer is refused, not merged."""
    working = bias.Bias("cjt-1")
    assert working.write("goal", "cross to the next node", "cjt-1") == 1
    before = working.snapshot()

    try:
        working.write("goal", "something a second writer wanted", "cjt-2")
    except bias.BiasRefusal as refusal:
        assert refusal.code == bias.BIAS_OWNED_BY_ANOTHER_COORDINATOR, refusal.code
        assert "cjt-2" in refusal.detail
    else:
        raise AssertionError("a second coordinator was allowed to write the Bias")

    after = working.snapshot()
    assert after.version == before.version == 1, (before.version, after.version)
    assert after.digest == before.digest, "a refused write moved the digest"
    assert working.read("goal") == "cross to the next node", working.read("goal")

    # An unnamed writer is refused before ownership is even considered.
    for nameless in ("", "   ", None, 7):
        try:
            working.write("goal", "x", nameless)
        except bias.BiasRefusal as refusal:
            assert refusal.code == bias.BIAS_COORDINATOR_NOT_NAMED, (nameless, refusal.code)
        else:
            raise AssertionError("an unnamed coordinator was allowed to write: %r" % (nameless,))
    try:
        bias.Bias("")
    except bias.BiasRefusal as refusal:
        assert refusal.code == bias.BIAS_COORDINATOR_NOT_NAMED
    else:
        raise AssertionError("a Bias with no named coordinator was constructed")


@case
def bias_version_increments_and_digest_changes_on_write():
    """Every write moves the version by exactly one and produces a new digest."""
    working = bias.Bias("cjt-1")
    assert working.version == bias.Bias.VERSION_ORIGIN == 0
    versions = [working.write("fact-%d" % index, index, "cjt-1") for index in range(5)]
    assert versions == [1, 2, 3, 4, 5], versions
    assert all(later > earlier for earlier, later in zip(versions, versions[1:])), versions

    digests = [entry["digest"] for entry in working.history()]
    assert len(digests) == 5, digests
    assert len(set(digests)) == 5, "two writes produced the same snapshot digest"
    assert working.snapshot().digest == digests[-1]

    # Writing the same key with the same value still moves the version and the digest: a
    # version is a count of writes, not a count of differences.
    digest_before_repeat = working.snapshot().digest
    assert working.write("fact-0", 0, "cjt-1") == 6
    assert working.snapshot().digest != digest_before_repeat
    assert working.read("fact-0") == 0

    # Writing a different fact moves the digest too, and keys stay sorted.
    assert working.write("zzz", "last", "cjt-1") == 7
    assert working.keys == ("fact-0", "fact-1", "fact-2", "fact-3", "fact-4", "zzz"), working.keys

    # The recorded history agrees with the live version at every step.
    assert [entry["version"] for entry in working.history()] == list(range(1, 8))


@case
def bias_version_guard_refuses_anything_but_a_strict_increase():
    """The one guard the version rule is made of: strictly greater, or nothing."""
    assert bias.check_version_increase(2, 3) == 3
    assert bias.check_version_increase(0, 1) == 1
    for before, after in ((2, 2), (3, 2), (0, 0), (5, -1)):
        try:
            bias.check_version_increase(before, after)
        except bias.BiasRefusal as refusal:
            assert refusal.code == bias.BIAS_VERSION_WOULD_NOT_INCREASE, refusal.code
        else:
            raise AssertionError("%d -> %d was accepted as an increase" % (before, after))
    for odd in ((True, 2), (1, "2"), (1.0, 2)):
        try:
            bias.check_version_increase(*odd)
        except bias.BiasRefusal as refusal:
            assert refusal.code == bias.BIAS_VERSION_WOULD_NOT_INCREASE
        else:
            raise AssertionError("a non-int version pair was accepted: %r" % (odd,))


@case
def bias_cannot_be_told_a_version_and_has_no_setter():
    """No caller may dictate a version: the only mover is write()."""
    working = a_bias()
    try:
        working.write("goal", "again", "cjt-1", 99)
    except TypeError:
        pass
    else:
        raise AssertionError("write() accepted a version argument")
    try:
        working.version = 99
    except AttributeError:
        pass
    else:
        raise AssertionError("the version has a setter")
    assert working.version == 1
    assert not hasattr(bias.Bias, "restore"), "a restore would be a way to lower the version"


@case
def bias_never_invents_a_fact():
    """Reading what was never written is refused, and a snapshot refuses it too."""
    working = a_bias()
    for reader in (working.read, working.snapshot().read):
        try:
            reader("a fact nobody wrote")
        except bias.BiasRefusal as refusal:
            assert refusal.code == bias.BIAS_KEY_NOT_WRITTEN, refusal.code
        else:
            raise AssertionError("an unwritten fact was returned")
    assert working.has("goal") is True
    assert working.has("a fact nobody wrote") is False
    assert working.snapshot().has("goal") is True
    try:
        working.read(7)
    except bias.BiasRefusal as refusal:
        assert refusal.code == bias.BIAS_KEY_NOT_A_STRING
    else:
        raise AssertionError("a non-string fact name was accepted")


@case
def bias_holds_plain_facts_and_never_a_live_object():
    """A fact must survive without this process, so a live object is refused."""
    working = bias.Bias("cjt-1")
    accepted = {"a": [1, 2.5, None, True, "x"], "b": {"c": 3}}
    working.write("plain", accepted, "cjt-1")
    assert working.read("plain") == accepted

    # What comes back is a copy, so a reader cannot write through the Bias.
    borrowed = working.read("plain")
    borrowed["a"].append("smuggled")
    assert working.read("plain") == accepted, working.read("plain")
    assert working.snapshot().read("plain") == accepted

    for bad in (object(), (1, 2), {1: "non-string key"}, float("nan"), float("inf"), {"k": {1: 2}}):
        try:
            working.write("bad", bad, "cjt-1")
        except bias.BiasRefusal as refusal:
            assert refusal.code == bias.BIAS_VALUE_NOT_PLAIN, (bad, refusal.code)
        else:
            raise AssertionError("a live or non-plain value was written: %r" % (bad,))
    assert working.version == 1, "a refused write moved the version"


@case
def bias_snapshot_is_frozen_and_does_not_move():
    """The next CJT reads a reading. It cannot write through it, and it does not age."""
    working = a_bias()
    first = working.snapshot()
    working.write("second", "written after the snapshot was taken", "cjt-1")
    second = working.snapshot()

    assert first.version == 1 and first.digest != second.digest
    assert first.keys() == ("goal",), first.keys()
    assert second.keys() == ("goal", "second"), second.keys()
    assert first.read("goal") == "cross to the next node"
    try:
        first.version = 2
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("a snapshot was mutated")
    assert isinstance(first.facts, tuple), "a snapshot's facts must not be a live dict"
    assert first.coordinator == "cjt-1"


# --------------------------------------------------------------------------- #
# The turn, stage by stage
# --------------------------------------------------------------------------- #
@case
def a_full_turn_runs_all_five_stages_in_order():
    """Five stages, in this order, each one's output feeding the next, all on the record."""
    seen = []

    def propose(snapshot):
        seen.append(snapshot)
        return loop.Proposal(text="cross to the next node", cites=("goal",))

    engine = loop.Loop(a_bias(), "cjt-1", propose)
    record = engine.turn("ACTIVE", "INTENDED", False, prerequisites=("desire",))

    assert record.receipt_stages == ("READ_BIAS", "PROPOSE", "OBSERVE", "GATE", "CONTINUE"), (
        record.receipt_stages,
    )
    assert record.stages_run == record.receipt_stages
    assert [entry["index"] for entry in record.receipt] == [1, 2, 3, 4, 5]
    assert all(entry["kind"] == "STAGE" for entry in record.receipt)

    # Each stage's output is on the record, and each is the one the next stage consumed.
    assert isinstance(record.bias_snapshot, bias.BiasSnapshot)
    assert record.bias_snapshot.version == 1
    assert record.bias_snapshot.keys() == ("goal",)
    assert seen[0] is record.bias_snapshot, "the proposer was not handed the reading stage 1 took"
    assert not isinstance(seen[0], bias.Bias), "the proposer was handed the live Bias"
    assert record.proposal.text == "cross to the next node"
    assert record.proposal.cites == ("goal",)
    assert record.observation.region == "ACTIVE"
    assert record.observation.semantic_outcome == "INTENDED"
    assert record.observation.saturated is False
    assert record.asom_label == asom.ALIGNED, record.asom_label
    assert record.observation.label_known is True
    assert record.gate.verdict == loop.PROCEED
    assert record.outcome == loop.CONTINUE
    assert record.continued is True
    assert record.ladder is None
    assert record.ladder_steps == ()
    assert record.refusal_code is None

    # One call each: nothing else could have given a verdict or a label.
    assert record.gate_calls == 1 and record.asom_calls == 1
    assert engine.turn_count == 1
    assert record.turn == 1

    # The record is frozen and carries its own dictionary form.
    try:
        record.outcome = "DISENGAGED"
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("a TurnRecord was mutated")
    as_dict = record.as_dict()
    assert as_dict["outcome"] == "CONTINUE"
    assert as_dict["asom_label"] == asom.ALIGNED
    # The default gate is the real one now, and the record says which kind of verdict it
    # carries: rpm, not a stub, and with the gate's own decision code on it.
    assert as_dict["gate"]["stub"] is False
    assert as_dict["gate"]["rpm"] is True
    assert as_dict["gate"]["code"] == rpm_gate.NOTHING_BLOCKED
    assert as_dict["cause"]["blocked_node"] is None
    assert as_dict["cause"]["depth"] == 0
    assert len(as_dict["receipt"]) == 5


@case
def the_proposal_is_proposed_under_the_bias_it_cites():
    """A proposal reads the Bias it was handed, and may not cite a fact it never carried."""
    working = a_bias()
    engine = loop.Loop(working, "cjt-1", a_proposer(cites=("goal",)))
    record = engine.turn("ACTIVE", "INTENDED", False)
    assert record.proposal.cites == ("goal",)
    assert working.read("goal") in record.proposal.text

    # A citation of a fact the Bias never carried is an error, not a turn decision, and it
    # does not consume a turn number: the record's number is the index of that record.
    attempts = []

    def flaky(snapshot):
        attempts.append(len(attempts) + 1)
        if len(attempts) == 1:
            return loop.Proposal(text="cites a ghost", cites=("a fact nobody wrote",))
        return loop.Proposal(text="now it cites only what the Bias carried", cites=("goal",))

    engine = loop.Loop(working, "cjt-1", flaky)
    try:
        engine.turn("ACTIVE", "INTENDED", False)
    except loop.LoopRefusal as refusal:
        assert refusal.code == loop.LOOP_PROPOSAL_CITES_UNWRITTEN_FACT, refusal.code
        assert "a fact nobody wrote" in refusal.detail
    else:
        raise AssertionError("a proposal invented a fact the Bias never carried")
    assert engine.turn_count == 0, "a turn that produced no record was counted as one"
    record = engine.turn("ACTIVE", "INTENDED", False)
    assert record.turn == 1 and engine.turn_count == 1, (record.turn, engine.turn_count)
    assert record.proposal.cites == ("goal",)

    # A proposer may also return a bare string, and may cite nothing at all.
    record = loop.Loop(working, "cjt-1", lambda snapshot: "just a sentence").turn(
        "ACTIVE", "INTENDED", False
    )
    assert record.proposal.text == "just a sentence" and record.proposal.cites == ()

    # Anything that is not a proposal or a string is refused.
    engine = loop.Loop(working, "cjt-1", lambda snapshot: 42)
    try:
        engine.turn("ACTIVE", "INTENDED", False)
    except loop.LoopRefusal as refusal:
        assert refusal.code == loop.LOOP_PROPOSAL_NOT_A_PROPOSAL
    else:
        raise AssertionError("a non-proposal was accepted")


@case
def asom_label_is_computed_from_the_three_observation_inputs():
    """Every label is reachable, and the record always carries one."""
    expected = [
        ("CUTOFF", "INTENDED", False, asom.STARVED),
        ("CUTOFF", "OPPOSITE", True, asom.STARVED),
        ("ACTIVE", "INTENDED", False, asom.ALIGNED),
        ("ACTIVE", "INTENDED", True, asom.OVERSATURATED),
        ("ACTIVE", "OPPOSITE", False, asom.MISALIGNED),
        ("ACTIVE", "OFF_AXIS", True, asom.MISALIGNED),
        ("BREAKDOWN", "INTENDED", True, asom.OVERSATURATED),
        ("BREAKDOWN", "OFF_AXIS", False, asom.MISALIGNED),
        ("ACTIVE", "UNKNOWN", False, asom.NOT_EMITTED),
        ("ACTIVE", "UNASSESSED", False, asom.NOT_EMITTED),
    ]
    reached = set()
    for region, outcome, saturated, want in expected:
        engine = loop.Loop(a_bias(), "cjt-1", a_proposer())
        record = engine.turn(region, outcome, saturated)
        assert record.asom_label == want, (region, outcome, saturated, want, record.asom_label)
        assert record.asom_label == asom.readout(region, outcome, saturated)
        assert record.observation.label_known is True
        # The stub gate proceeds whatever the label says -- including MISALIGNED.
        assert record.outcome == loop.CONTINUE
        reached.add(record.asom_label)
    assert set(asom.LABELS).issubset(reached), reached
    assert asom.NOT_EMITTED in reached


# --------------------------------------------------------------------------- #
# ASOM IS A READOUT: THE PROOF THAT IT CANNOT GATE
# --------------------------------------------------------------------------- #
@case
def asom_never_changes_the_gate_verdict():
    """The full matrix twice: computed, and forced to every possible label. Identical.

    This is the requirement in the owning instruction: "a test runs the full matrix of turns
    twice, once with ASOM computed and once with it returning every possible label including
    a forced MISALIGNED, and asserts the gate verdicts are identical every time."

    The comparison is not only on the verdict word: the whole decision is compared, which is
    the verdict, the gap, the reason, the turn's outcome, any refusal code, the ladder steps,
    the ask and the disengage reason. The gate requests are compared too, so the gate was not
    merely asked the same question twice -- it was handed an equal record, field for field.
    """
    computed_rows, computed_requests, _ = matrix_run(loop, asom.readout)
    assert len(computed_rows) == len(REGIONS) * len(SEMANTIC_OUTCOMES) * len(SATURATION) * len(
        policies(loop)
    ) == 150, len(computed_rows)

    # The computed run really did produce a spread of labels: this test is not comparing
    # ALIGNED with ALIGNED for 150 rows.
    computed_labels = set(labels_of(computed_rows))
    assert {asom.STARVED, asom.ALIGNED, asom.OVERSATURATED, asom.MISALIGNED}.issubset(
        computed_labels
    ), computed_labels
    assert asom.NOT_EMITTED in computed_labels
    assert len(computed_labels) == 5, computed_labels

    for forced_label in (
        asom.STARVED,
        asom.ALIGNED,
        asom.OVERSATURATED,
        asom.MISALIGNED,
        asom.NOT_EMITTED,
    ):
        forced_rows, forced_requests, _ = matrix_run(loop, forced(forced_label))
        assert len(forced_rows) == len(computed_rows)

        # 1. The labels really were forced, so nothing below can be satisfied by accident.
        assert labels_of(forced_rows) == [forced_label] * len(forced_rows)
        differed = sum(
            1
            for computed, was_forced in zip(labels_of(computed_rows), labels_of(forced_rows))
            if computed != was_forced
        )
        assert differed > 0, "forcing %s changed no label, so the comparison is vacuous" % (
            forced_label,
        )

        # 2. Every decision is identical, cell for cell.
        assert decisions_of(forced_rows) == decisions_of(computed_rows), (
            "forcing the ASOM label to %s changed a decision" % (forced_label,)
        )

        # 3. The gate was handed an equal request every time.
        assert forced_requests == computed_requests, (
            "forcing the ASOM label to %s changed what the gate was asked" % (forced_label,)
        )

        # 4. And the same turn outcomes fall out, word for word.
        assert [row[5] for row in forced_rows] == [row[5] for row in computed_rows]

    # The headline case, spelled out: every forced-MISALIGNED turn that the gate allowed
    # continued, and the matrix contains such turns.
    forced_rows, _, _ = matrix_run(loop, forced(asom.MISALIGNED))
    through = [
        row
        for row in forced_rows
        if row[4][0] == loop.PROCEED and row[5] == loop.CONTINUE
    ]
    stopped = [row for row in forced_rows if row[4][0] != loop.PROCEED and row[5] != loop.CONTINUE]
    assert through, "no forced-MISALIGNED turn ran under a proceeding gate"
    assert stopped, "no forced-MISALIGNED turn ran under a gate that could not proceed"
    assert len(through) + len(stopped) == len(forced_rows)


@case
def asom_never_changes_a_disengage_decision():
    """Forcing the label moves nothing about the ladder: steps, gap, ask, reason, outcome."""
    baseline = {}
    for forced_label in (
        asom.STARVED,
        asom.ALIGNED,
        asom.OVERSATURATED,
        asom.MISALIGNED,
        asom.NOT_EMITTED,
    ):
        for policy_name, gate in (
            ("refusing", loop.refusing_gate(GAP, GATE_REASON)),
            ("repairing", loop.repairing_gate(GAP, GATE_REASON)),
            ("refusing-with-no-reason", loop.refusing_gate(GAP, "")),
            ("naming-no-gap", loop.refusing_gate(None, GATE_REASON)),
        ):
            for region in REGIONS:
                for outcome in SEMANTIC_OUTCOMES:
                    for saturated in SATURATION:
                        engine = loop.Loop(
                            a_bias(), "cjt-1", a_proposer(), gate=gate,
                            asom_reader=forced(forced_label),
                        )
                        record = engine.turn(region, outcome, saturated)
                        observed = (
                            policy_name, region, outcome, saturated, record.decision(),
                            record.ladder_steps, record.refusal_code,
                        )
                        assert record.asom_label == forced_label
                        key = (policy_name, region, outcome, saturated)
                        if key in baseline:
                            assert observed == baseline[key], (
                                "forcing the label to %s changed the ladder decision for %r"
                                % (forced_label, key)
                            )
                        else:
                            baseline[key] = observed

    # Sanity on the baseline itself: some of those turns disengaged, and some were refused
    # for a reason the ladder gave rather than the gate.
    words = {value[4][3] for value in baseline.values()}
    assert loop.DISENGAGED in words, words
    assert loop.REFUSED in words, words


@case
def a_loop_that_lets_asom_gate_is_caught():
    """The build must not pass by being vacuous: break the rule in a copy and catch it.

    A copy of loop.py is made in memory, with three lines added that let a MISALIGNED label
    overrule the gate. The same matrix is run against that copy, and the check from the case
    above must fail -- which is the proof that the check can fail at all.
    """
    source = read_build_file("loop.py")
    assert GATE_LINE in source, (
        "the gate line this check rewrites is not in loop.py any more, so the mutation would "
        "silently prove nothing"
    )
    injected = (
        GATE_LINE
        + "\n        if observation.label == asom.MISALIGNED:"
        + "\n            verdict = GateVerdict(REFUSE, 'ASOM', 'the readout said MISALIGNED')"
    )
    broken_source = source.replace(GATE_LINE, injected, 1)
    assert broken_source != source

    broken = types.ModuleType("loop_broken_on_purpose")
    broken.__file__ = os.path.join(BUILD_DIR, "loop.py")
    # The dataclass machinery looks its module up by name while decorating, so the copy has to
    # be registered before its own body runs.
    sys.modules[broken.__name__] = broken
    exec(
        compile(broken_source, "<loop.py with ASOM wired into the gate>", "exec"),
        broken.__dict__,
    )

    clean_computed, _, _ = matrix_run(loop, asom.readout)
    computed_rows, _, _ = matrix_run(broken, asom.readout)
    forced_rows, _, _ = matrix_run(broken, forced(asom.MISALIGNED))
    assert decisions_of(forced_rows) != decisions_of(computed_rows), (
        "a loop that lets the ASOM label overrule the gate produced identical decisions, so "
        "the test above cannot catch it -- the test proves nothing"
    )
    assert decisions_of(computed_rows) != decisions_of(clean_computed), (
        "the injection never took effect: the broken copy decided exactly what the real module "
        "decided, so this check proves nothing"
    )

    # And the real module, run the same two ways, is identical: the difference above is caused
    # by the injected three lines and by nothing else.
    clean_forced, _, _ = matrix_run(loop, forced(asom.MISALIGNED))
    assert decisions_of(clean_forced) == decisions_of(clean_computed)


@case
def the_gate_is_the_only_thing_that_can_stop_or_allow_a_turn():
    """Nothing else may stop a turn, and nothing else may allow one."""
    # 1. A gate that proceeds: nothing else can stop a turn -- not a MISALIGNED label, not a
    #    STARVED label, not an unknown label, and not a readout that is broken outright,
    #    whatever the region and outcome say.
    for reader in (
        asom.readout,
        forced(asom.MISALIGNED),
        forced(asom.STARVED),
        forced(asom.NOT_EMITTED),
        forced("NOT A LABEL AT ALL"),
        forced(None),
    ):
        engine = loop.Loop(
            a_bias(), "cjt-1", a_proposer(), gate=loop.proceeding_gate, asom_reader=reader
        )
        for region in REGIONS:
            for outcome in SEMANTIC_OUTCOMES:
                for saturated in SATURATION:
                    record = engine.turn(region, outcome, saturated)
                    assert record.outcome == loop.CONTINUE, (
                        record.asom_label, region, outcome, saturated, record.outcome
                    )
                    assert record.ladder is None
                    assert record.refusal_code is None
                    # A broken readout is recorded as recorded-but-unknown, never as a stop.
                    assert record.observation.label_known == (
                        isinstance(record.asom_label, str)
                        and record.asom_label in loop.KNOWN_LABELS
                    )

    # 2. A gate that cannot proceed: every turn stops, even when the readout says ALIGNED and
    #    the Bias is perfectly written.
    for gate in (
        loop.refusing_gate(GAP, GATE_REASON),
        loop.repairing_gate(GAP, GATE_REASON),
    ):
        engine = loop.Loop(a_bias(), "cjt-1", a_proposer(), gate=gate)
        for region in REGIONS:
            for outcome in SEMANTIC_OUTCOMES:
                for saturated in SATURATION:
                    record = engine.turn(region, outcome, saturated)
                    assert record.outcome != loop.CONTINUE, record.outcome
                    assert record.gate.can_proceed is False
                    assert record.asom_label is not None

    # 3. Across the whole 150-row matrix: a turn continues if and only if the gate allowed it.
    rows, _, _ = matrix_run(loop, asom.readout)
    proceed_words = set()
    allowed = 0
    for row in rows:
        verdict_word, gap, reason, outcome = row[4][0], row[4][1], row[4][2], row[4][3]
        proceed_words.add(verdict_word)
        continues = row[5] == loop.CONTINUE
        assert continues == (verdict_word == loop.PROCEED), (row[0], verdict_word, row[5])
        allowed += 1 if continues else 0
    assert proceed_words == set(loop.VERDICT_WORDS), proceed_words
    assert 0 < allowed < len(rows), (allowed, len(rows))

    # 4. The decision function is a function of the verdict and of nothing else.
    for word in loop.VERDICT_WORDS:
        for gap in (None, "", GAP):
            for reason in (None, "", GATE_REASON):
                for stub in (False, True):
                    verdict = loop.GateVerdict(word, gap, reason, stub)
                    assert loop.may_continue(verdict) is (word == loop.PROCEED)
    try:
        loop.may_continue("PROCEED")
    except loop.LoopRefusal as refusal:
        assert refusal.code == loop.LOOP_GATE_VERDICT_NOT_A_WORD
    else:
        raise AssertionError("may_continue accepted something that is not a verdict")

    # 5. One gate call per turn: no second opinion can stop or allow anything.
    _, requests, records = matrix_run(loop, asom.readout, records_everything=True)
    assert all(record.gate_calls == 1 for record in records)
    assert all(record.asom_calls == 1 for record in records)
    assert len(requests) == len(records)


@case
def the_gate_cannot_be_handed_the_readout_at_all():
    """The structural half of the separation: there is nowhere on the request for a label."""
    fields = [field.name for field in dataclasses.fields(loop.GateRequest)]
    assert fields == [
        "turn",
        "coordinator",
        "bias_version",
        "bias_digest",
        "proposal_text",
        "prerequisites",
        "cause",
    ], fields
    # The gate declares the field list it will accept, and the two must agree: a request with
    # any other field is refused by the gate rather than read.
    assert tuple(fields) == rpm_gate.GATE_REQUEST_FIELDS, (
        fields,
        rpm_gate.GATE_REQUEST_FIELDS,
    )
    forbidden = {
        "asom",
        "asom_label",
        "label",
        "region",
        "operating_region",
        "semantic_outcome",
        "outcome",
        "saturated",
    }
    assert not (forbidden & set(fields)), forbidden & set(fields)
    # And it is not smuggled in through a free-form catch-all either.
    parameters = inspect.signature(loop.GateRequest).parameters
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    ), "GateRequest has a catch-all: a label could be smuggled through it"
    assert "context" not in fields and "extra" not in fields

    # The cause the request carries must be just as empty of the readout: every leaf field of
    # it, checked by name, on the record the gate itself declares.
    cause_fields = [field.name for field in dataclasses.fields(rpm_gate.RpmCause)]
    assert tuple(cause_fields) == rpm_gate.RPM_CAUSE_FIELDS, (
        cause_fields,
        rpm_gate.RPM_CAUSE_FIELDS,
    )
    assert not (forbidden & set(cause_fields)), forbidden & set(cause_fields)
    cause_parameters = inspect.signature(rpm_gate.RpmCause).parameters
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in cause_parameters.values()
    ), "RpmCause has a catch-all: a label could be smuggled through it"
    assert is_plain_record(rpm_gate.RpmCause), "the cause admits non-plain field types"
    assert is_plain_record(loop.GateRequest), "the request admits non-plain field types"

    # And the gate refuses a request that carries anything else at all, rather than reading
    # around it. The extra field names a label; the gate must not even look at it.
    extra = dataclasses.make_dataclass(
        "GateRequestWithALabel",
        [(field.name, object) for field in dataclasses.fields(loop.GateRequest)]
        + [("label", object)],
        frozen=True,
    )
    smuggle = extra(
        turn=1,
        coordinator="cjt-1",
        bias_version=1,
        bias_digest="d",
        proposal_text="p",
        prerequisites=(),
        cause=rpm_gate.RpmCause(),
        label=asom.MISALIGNED,
    )
    assert dataclasses.fields(extra)[-1].name == "label"
    try:
        rpm_gate.rpm_gate(smuggle)
    except rpm_gate.GateViolation as refusal:
        assert refusal.code == rpm_gate.RPM_REQUEST_NOT_A_GATE_REQUEST, refusal.code
    else:
        raise AssertionError("the gate read a request whose field list it was not given")


# --------------------------------------------------------------------------- #
# The disengage ladder, run by the gate's verdict
# --------------------------------------------------------------------------- #
@case
def when_the_gate_cannot_proceed_the_ladder_names_the_exact_gap():
    """The gap in the ask is the gate's gap, and the reason is the gate's reason."""
    engine = loop.Loop(a_bias(), "cjt-1", a_proposer(), gate=loop.refusing_gate(GAP, GATE_REASON))
    record = engine.turn("ACTIVE", "OPPOSITE", True)

    assert record.outcome == loop.DISENGAGED
    assert record.gate.verdict == loop.REFUSE
    assert record.gate.gap == GAP
    assert record.ladder is not None
    assert record.ladder.gap == GAP
    assert record.ladder.ask == "I need %s. What is it?" % (GAP,), record.ladder.ask
    assert GAP in record.ladder.ask
    assert record.ladder.reason == GATE_REASON
    assert record.ladder.terminal is True
    assert record.ladder.utterances == (
        disengage.FIXED_CANNOT_TELL,
        "I need %s. What is it?" % (GAP,),
        "I disengage because %s." % (GATE_REASON,),
    ), record.ladder.utterances

    # The loop ran the owner's ladder and changed none of its rules: the same gap and reason
    # through the module's own driver give the same steps, ask and reason.
    directly = disengage.run_ladder(GAP, reason=GATE_REASON)
    assert record.ladder.steps == directly.steps == disengage.STEPS
    assert record.ladder.ask == directly.ask
    assert record.ladder.reason == directly.reason

    # A REPAIR verdict is treated as "may not proceed", and the word is not lost.
    engine = loop.Loop(a_bias(), "cjt-1", a_proposer(), gate=loop.repairing_gate(GAP, GATE_REASON))
    repair_record = engine.turn("ACTIVE", "INTENDED", False)
    assert repair_record.gate.verdict == loop.REPAIR
    assert repair_record.gate.can_proceed is False
    assert repair_record.outcome == loop.DISENGAGED
    assert repair_record.ladder.gap == GAP
    assert repair_record.asom_label == asom.ALIGNED


@case
def the_ladders_four_steps_appear_in_order_in_the_receipt():
    """NOT_DECLARED, CONFUSED, ASK_CLARITY, DISENGAGE -- in that order, in the turn's receipt."""
    engine = loop.Loop(a_bias(), "cjt-1", a_proposer(), gate=loop.refusing_gate(GAP, GATE_REASON))
    record = engine.turn("CUTOFF", "INTENDED", True)

    assert record.receipt_stages == (
        "READ_BIAS",
        "PROPOSE",
        "OBSERVE",
        "GATE",
        "NOT_DECLARED",
        "CONFUSED",
        "ASK_CLARITY",
        "DISENGAGE",
    ), record.receipt_stages
    assert record.ladder_steps == disengage.STEPS
    assert [entry["index"] for entry in record.receipt] == list(range(1, 9))
    ladder_entries = [entry for entry in record.receipt if entry["kind"] == "LADDER_STEP"]
    assert len(ladder_entries) == 4
    assert all(entry["of_turn"] == loop.STAGE_DISENGAGE_OR_CONTINUE for entry in ladder_entries)
    assert [entry["gap"] for entry in ladder_entries] == [GAP] * 4
    # The reason belongs to the disengage step only: the first three steps carry none.
    assert [entry["reason"] for entry in ladder_entries] == [None, None, None, GATE_REASON]
    # The first step says nothing; the fourth says the reason out loud.
    assert ladder_entries[0]["utterance"] is None
    assert ladder_entries[2]["utterance"] == record.ladder.ask
    assert GATE_REASON in ladder_entries[3]["utterance"]


@case
def a_disengage_carries_a_reason_and_one_without_is_refused():
    """No reason, no disengage: the ladder refuses and the turn is recorded as refused."""
    for empty_reason in ("", "   ", None):
        engine = loop.Loop(
            a_bias(), "cjt-1", a_proposer(), gate=loop.refusing_gate(GAP, empty_reason)
        )
        record = engine.turn("ACTIVE", "INTENDED", False)
        assert record.outcome == loop.REFUSED, (empty_reason, record.outcome)
        assert record.refusal_code == disengage.DISENGAGE_NEEDS_REASON, record.refusal_code
        assert record.ladder is None
        assert "DISENGAGE" not in record.ladder_steps, record.ladder_steps
        # It got as far as the ask, and the receipt shows it asked before it stopped.
        assert record.ladder_steps == (disengage.NOT_DECLARED, disengage.CONFUSED, disengage.ASK_CLARITY)
        assert record.receipt_stages[-1] == disengage.ASK_CLARITY

    # With a reason, the same gate disengages properly.
    engine = loop.Loop(a_bias(), "cjt-1", a_proposer(), gate=loop.refusing_gate(GAP, GATE_REASON))
    record = engine.turn("ACTIVE", "INTENDED", False)
    assert record.outcome == loop.DISENGAGED
    assert record.refusal_code is None
    assert record.ladder.reason == GATE_REASON


@case
def a_gate_that_cannot_name_a_gap_is_refused_rather_than_asked_vaguely():
    """An unnamed gap is refused at the ask: this build never asks a vague question."""
    for nameless in (None, "", "   "):
        engine = loop.Loop(
            a_bias(), "cjt-1", a_proposer(), gate=loop.refusing_gate(nameless, GATE_REASON)
        )
        record = engine.turn("ACTIVE", "INTENDED", False)
        assert record.outcome == loop.REFUSED, (nameless, record.outcome)
        assert record.refusal_code == disengage.CLARITY_ASK_NEEDS_GAP, record.refusal_code
        assert record.ladder is None
        assert record.ladder_steps == (disengage.NOT_DECLARED, disengage.CONFUSED), record.ladder_steps
        assert disengage.ASK_CLARITY not in record.receipt_stages
        said = " ".join(
            str(entry["utterance"])
            for entry in record.receipt
            if entry["kind"] == "LADDER_STEP"
        )
        assert "I need" not in said, "a vague question was asked: %r" % (said,)


@case
def the_stub_gate_is_a_stub_and_the_record_says_so():
    """Nothing here may be mistaken for an RPM decision after the fact.

    The placeholder is still in the file, and it is still honest about itself: it proceeds,
    it says in its own reason that it checked nothing, and its verdict is marked ``stub``. What
    changed is that it is no longer the default -- the default is the real RPM gate -- so the
    two kinds of verdict are now told apart by the record rather than by the docstring.
    """
    assert loop.CLAIM_CEILING == CLAIM_CEILING == (
        "MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM."
    )
    assert rpm_gate.CLAIM_CEILING == CLAIM_CEILING, rpm_gate.CLAIM_CEILING

    # The default gate is the real one, and a plain turn's verdict is an RPM verdict.
    default = inspect.signature(loop.Loop.__init__).parameters["gate"].default
    assert default is loop.rpm_gate, default
    assert default is not loop.stub_gate
    engine = loop.Loop(a_bias(), "cjt-1", a_proposer())
    record = engine.turn("ACTIVE", "INTENDED", False)
    assert record.gate.verdict == loop.PROCEED
    assert record.gate.stub is False
    assert record.gate.rpm is True
    assert record.gate.code == rpm_gate.NOTHING_BLOCKED
    assert "STUB" not in str(record.gate.reason)

    # The placeholder, asked for by name, is still a placeholder and still says so.
    engine = loop.Loop(a_bias(), "cjt-1", a_proposer(), gate=loop.stub_gate)
    record = engine.turn("ACTIVE", "INTENDED", False)
    assert record.gate.verdict == loop.PROCEED
    assert record.gate.stub is True
    assert record.gate.rpm is False
    assert record.gate.reason == loop.STUB_NOTE
    assert "STUB" in record.gate.reason
    assert "no RPM prerequisite check" in record.gate.reason
    assert record.as_dict()["gate"]["stub"] is True
    # The stub gate cannot refuse and cannot name a gap: it is not a decision.
    verdict = loop.stub_gate(loop.GateRequest(1, "cjt-1", 1, "d", "p", ()))
    assert verdict.gap is None and verdict.can_proceed is True and verdict.rpm is False
    # And a gate written by a caller is marked as not the stub, and as not RPM either.
    other = loop.proceeding_gate(loop.GateRequest(1, "cjt-1", 1, "d", "p", ()))
    assert other.stub is False and other.rpm is False


# --------------------------------------------------------------------------- #
# One Bias, one writer, through the loop
# --------------------------------------------------------------------------- #
@case
def a_second_coordinator_cannot_write_the_loops_bias():
    """Two loops may read one Bias. Only the owner may write it, and the loop adds no rule."""
    working = a_bias("cjt-1")
    owner = loop.Loop(working, "cjt-1", a_proposer())
    other = loop.Loop(working, "cjt-2", a_proposer())

    version_before = working.version
    assert owner.remember("note", "written by the owner", ) == version_before + 1
    try:
        other.remember("note", "written by a second coordinator")
    except bias.BiasRefusal as refusal:
        assert refusal.code == bias.BIAS_OWNED_BY_ANOTHER_COORDINATOR, refusal.code
    else:
        raise AssertionError("a second coordinator wrote the Bias through the loop")
    assert working.version == version_before + 1, working.version
    assert working.read("note") == "written by the owner"

    # The second coordinator may still READ it: reading is what the next CJT does.
    record = other.turn("ACTIVE", "INTENDED", False)
    assert record.coordinator == "cjt-2"
    assert record.bias_snapshot.version == working.version
    assert record.bias_snapshot.keys() == ("goal", "note")


@case
def a_turn_never_writes_the_bias():
    """The five stages read the working memory. Writing is a separate act."""
    working = a_bias()
    before = working.snapshot()
    engine = loop.Loop(working, "cjt-1", a_proposer())
    engine.turn("ACTIVE", "INTENDED", False)
    after = working.snapshot()
    assert after.version == before.version == 1
    assert after.digest == before.digest

    # The same holds for a turn that disengages.
    engine = loop.Loop(working, "cjt-1", a_proposer(), gate=loop.refusing_gate(GAP, GATE_REASON))
    engine.turn("CUTOFF", "OPPOSITE", True)
    final = working.snapshot()
    assert final.version == before.version and final.digest == before.digest


# --------------------------------------------------------------------------- #
# The readout, as a display
# --------------------------------------------------------------------------- #
@case
def the_readout_is_a_display_with_nothing_to_gate_with():
    """asom.py holds no state and reaches nothing: a label, and that is all."""
    source = read_build_file("asom.py")
    imports = [
        line
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from ")) and "__future__" not in line
    ]
    assert imports == [], imports
    for forbidden in ("gate", "verdict", "proceed", "refuse", "loop", "bias"):
        assert not hasattr(asom, forbidden), "asom.py exposes %r" % (forbidden,)
    signature = inspect.signature(asom.readout)
    assert list(signature.parameters) == ["region", "outcome", "saturated"], list(
        signature.parameters
    )
    assert all(
        parameter.default is inspect.Parameter.empty or isinstance(parameter.default, bool)
        for parameter in signature.parameters.values()
    ), "a readout parameter has a non-trivial default"
    labels = set()
    for region in REGIONS:
        for outcome in SEMANTIC_OUTCOMES:
            for saturated in SATURATION:
                label = asom.readout(region, outcome, saturated)
                assert isinstance(label, str), label
                labels.add(label)
    assert labels == set(asom.LABELS) | {asom.NOT_EMITTED}, labels
    assert set(loop.KNOWN_LABELS) == set(asom.LABELS) | {asom.NOT_EMITTED}
    # The readout is called exactly once per turn, and its own self-check still passes.
    reader = counting(asom.readout)
    engine = loop.Loop(a_bias(), "cjt-1", a_proposer(), asom_reader=reader)
    engine.turn("ACTIVE", "INTENDED", False)
    assert len(reader.calls) == 1, reader.calls
    assert asom.self_check().startswith("PASS"), asom.self_check()


# --------------------------------------------------------------------------- #
# The copies, the README, and the undecided list
# --------------------------------------------------------------------------- #
@case
def the_copied_files_are_byte_identical_to_the_recorded_hashes():
    """PROVENANCE.md says the bytes; this recomputes them and requires a match.

    It checks three things, not one: that each copy re-hashes to the value recorded for it,
    that the recorded copy and source values are equal, and -- on this machine, where the
    source packages still sit -- that the SOURCE file still hashes to the same value. The third
    is what makes "nothing in the source packages was modified" checkable rather than asserted.
    """
    provenance = read_build_file("PROVENANCE.md")
    recorded = dict(
        re.findall(r"^([\w.]+) copy sha256: ([0-9a-f]{64})$", provenance, re.MULTILINE)
    )
    sources = dict(
        re.findall(r"^([\w.]+) source sha256: ([0-9a-f]{64})$", provenance, re.MULTILINE)
    )
    expected_copies = set(COPIED_MODULES) | set(VENDORED_MODULES)
    assert set(recorded) == expected_copies, sorted(recorded)
    assert set(sources) == expected_copies, sorted(sources)

    for name in sorted(expected_copies):
        path = locate_copy(name)
        with open(path, "rb") as handle:
            actual = hashlib.sha256(handle.read()).hexdigest()
        assert actual == recorded[name], (name, actual, recorded[name])
        assert recorded[name] == sources[name], (
            "%s differs from the source it was copied from" % (name,)
        )

    # The source packages themselves: unchanged, where they are present.
    checked = 0
    for name in sorted(expected_copies):
        origin = os.path.join(SOURCE_FOLDERS[name], name)
        if not os.path.isfile(origin):
            continue  # a checkout without the source package: reported by the runner
        with open(origin, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        assert digest == sources[name], (
            "the SOURCE %s no longer hashes to the value this build copied; something edited a "
            "package this build is not allowed to modify" % (origin,)
        )
        checked += 1
    assert checked in (0, len(expected_copies)), checked

    # The copies still say what this build relies on them saying.
    assert asom.LABELS == (asom.STARVED, asom.ALIGNED, asom.OVERSATURATED, asom.MISALIGNED)
    assert disengage.STEPS == ("NOT_DECLARED", "CONFUSED", "ASK_CLARITY", "DISENGAGE")
    assert asom.MISALIGNED == "MISALIGNED" and disengage.DISENGAGE_NEEDS_REASON
    # And nothing else was copied in: this build is these files plus its own three.
    expected = {
        "asom.py",
        "bias.py",
        "disengage.py",
        "loop.py",
        "rpm_gate.py",
        "test_all.py",
        "README.md",
        "PROVENANCE.md",
    }
    present = {name for name in os.listdir(BUILD_DIR) if os.path.isfile(os.path.join(BUILD_DIR, name))}
    assert present == expected, sorted(present ^ expected)
    # The engine folder holds exactly the four modules and nothing of its own.
    vendored = {
        name
        for name in os.listdir(os.path.join(BUILD_DIR, "dwp"))
        if os.path.isfile(os.path.join(BUILD_DIR, "dwp", name))
    }
    assert vendored == set(VENDORED_MODULES), sorted(vendored ^ set(VENDORED_MODULES))


def undecided_questions(prefix, modules):
    """Every marker of one kind in the named modules, as written in the code."""
    marker = re.compile(r"#\s*" + re.escape(prefix) + r":\s*(.+?)\s*$")
    questions = []
    for name in modules:
        for line in read_build_file(name).splitlines():
            found = marker.search(line)
            if found:
                questions.append(found.group(1).strip())
    return questions


@case
def readme_states_the_claim_ceiling_and_every_undecided_line():
    """The claim ceiling, said exactly; and every undecided line listed, verbatim."""
    readme = read_build_file("README.md")
    assert CLAIM_CEILING in readme, "README.md does not state the claim ceiling"
    assert CLAIM_CEILING in read_build_file("loop.py")
    assert CLAIM_CEILING in read_build_file("rpm_gate.py")
    assert "MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM." in readme
    # And the old ceiling is gone from every file in the build: the gate is real now, and no
    # document may still say it is a stub. (This file is not checked: it is the file that names
    # the old words in order to forbid them, so it necessarily contains them.)
    for name in ("README.md", "loop.py", "rpm_gate.py", "PROVENANCE.md"):
        assert "THE GATE IS A STUB" not in read_build_file(name), name
        assert "NO REAL RPM DECISION IS MADE HERE" not in read_build_file(name), name

    own = undecided_questions("UNDECIDED IN SOURCES", OWN_MODULES)
    assert len(own) >= 10, len(own)
    missing = [question for question in own if question not in readme]
    assert not missing, "README.md does not list %d undecided line(s), first: %s" % (
        len(missing),
        missing[0][:90],
    )

    # Every place canon does not settle what this gate or this turn does, listed word for word.
    # This is the drift test for the whole "# UNDECIDED IN CANON:" marker set.
    canon_undecided = undecided_questions("UNDECIDED IN CANON", OWN_MODULES)
    assert len(canon_undecided) >= 10, len(canon_undecided)
    missing = [question for question in canon_undecided if question not in readme]
    assert not missing, "README.md does not list %d UNDECIDED IN CANON line(s), first: %s" % (
        len(missing),
        missing[0][:90],
    )

    inherited = undecided_questions("UNDECIDED IN DESIGN", COPIED_MODULES)
    assert len(inherited) == 4, len(inherited)
    missing = [question for question in inherited if question not in readme]
    assert not missing, "README.md does not list %d inherited line(s), first: %s" % (
        len(missing),
        missing[0][:90],
    )

    # The README says plainly what the gate is and what this step cannot claim.
    for phrase in (
        "The gate is real",
        "THE GATE IS REAL",
        "MECHANISM ONLY.",
        "UNDECIDED IN SOURCES",
        "UNDECIDED IN CANON",
        "nothing has run inside Helm",
    ):
        assert phrase in readme, phrase


# --------------------------------------------------------------------------- #
# THE REAL GATE: what it decides, and on what
# --------------------------------------------------------------------------- #
@case
def the_real_gate_proceeds_when_nothing_blocks():
    """Nothing blocks and nothing is missing: the section holds, and the turn continues."""
    verdict = rpm_gate.rpm_gate(a_request())
    assert verdict.verdict == loop.PROCEED, verdict
    assert verdict.can_proceed is True
    assert verdict.rpm is True and verdict.stub is False
    assert verdict.code == rpm_gate.NOTHING_BLOCKED, verdict.code
    assert verdict.gap is None and verdict.sub_goal is None and verdict.fix is None
    basis = " | ".join(verdict.basis)
    assert "retraction.is_dirty" in basis, basis
    assert "bias.check_version_increase" in basis, basis
    assert "dwp.resolve -> not asked" in basis, basis
    assert "nothing blocks" in verdict.reason

    # Through a turn, under the default gate.
    record = loop.Loop(a_bias(), "cjt-1", a_proposer()).turn("ACTIVE", "INTENDED", False)
    assert record.outcome == loop.CONTINUE and record.continued
    assert record.ladder is None and record.ladder_steps == ()
    assert record.gate.rpm is True and record.gate.code == rpm_gate.NOTHING_BLOCKED
    assert record.receipt_stages == ("READ_BIAS", "PROPOSE", "OBSERVE", "GATE", "CONTINUE")
    gate_entry = record.receipt[3]
    assert gate_entry["rpm"] is True and gate_entry["stub"] is False
    assert gate_entry["cause"]["blocked_node"] is None
    assert gate_entry["can_proceed"] is True

    # PROCEED is not vacuous: a declared-but-unrealized requirement turns the same gate's word
    # to REPAIR, and a block turns it to REPAIR too. Each verdict below is reached for a
    # different reason, so this case is not measuring a constant.
    assert rpm_gate.rpm_gate(
        a_request(cause=a_cause(unsatisfied=(NAMED_GAP,)))
    ).verdict == loop.REPAIR
    assert rpm_gate.rpm_gate(
        a_request(cause=a_cause(blocked_node="P", depth=1))
    ).verdict == loop.REPAIR
    assert rpm_gate.rpm_gate(
        a_request(cause=a_cause(blocked_node="P", depth=HORIZON))
    ).verdict == loop.REFUSE


@case
def the_real_gate_repairs_and_names_the_exact_gap():
    """REPAIR names the missing prerequisite exactly, and names the sub-goal that would close it."""
    # 1. A requirement the runtime reports as unrealized. The gap is that requirement, in its
    #    own words -- not a class of gap, not a score, not a yes/no.
    gap = NAMED_GAP
    verdict = rpm_gate.rpm_gate(
        a_request(cause=a_cause(blocked_node="P", depth=2, unsatisfied=(gap,)))
    )
    assert verdict.verdict == loop.REPAIR, verdict
    assert verdict.code == rpm_gate.PREREQUISITE_MISSING, verdict.code
    assert verdict.gap == gap, verdict.gap
    assert verdict.can_proceed is False
    assert verdict.sub_goal == "RPM(%s)@3" % (gap,), verdict.sub_goal
    assert "depth 3" in verdict.reason, verdict.reason
    assert "line 71" in verdict.reason, verdict.reason

    # 2. Through a turn: the ladder is run by that verdict, asks for that exact gap, and
    #    disengages with the gate's own reason.
    record = loop.Loop(a_bias(), "cjt-1", a_proposer()).turn(
        "ACTIVE", "INTENDED", False, prerequisites=("power",),
        cause=a_cause(blocked_node="P", depth=2, unsatisfied=(gap,)),
    )
    assert record.outcome == loop.DISENGAGED, record.outcome
    assert record.gate.verdict == loop.REPAIR
    assert record.ladder is not None
    assert record.ladder.gap == gap
    assert record.ladder.ask == "I need %s. What is it?" % (gap,), record.ladder.ask
    assert record.ladder.reason == record.gate.reason
    assert record.ladder_steps == disengage.STEPS
    assert record.sub_goal == verdict.sub_goal
    assert record.receipt[3]["sub_goal"] == verdict.sub_goal
    assert record.refusal_code is None

    # 3. A block whose functor refuses its input: the gap is the missing input, named, and the
    #    engine's own refusal is the reason (so the gate and the engine cannot disagree).
    for cause, needle in (
        (a_cause(blocked_node="W", depth=1), "at least 2 parts"),
        (a_cause(blocked_node="W", depth=1, wisdom_route="CO-5", decomposition=("a", "b")),
         "resonant child"),
    ):
        refused_input = rpm_gate.rpm_gate(a_request(cause=cause))
        assert refused_input.verdict == loop.REPAIR, (cause, refused_input.verdict)
        assert refused_input.code == rpm_gate.FUNCTOR_NEEDS_INPUT, refused_input.code
        assert needle in refused_input.gap, refused_input.gap
        assert needle in refused_input.reason, refused_input.reason
        assert refused_input.sub_goal, "a REPAIR named no sub-goal"

    # 4. A block the matching functor resolves: REPAIR, and the sub-goal is the engine's own
    #    notation for the child chain, taken from dwp.resolve rather than restated here.
    for node, operators in (
        ("P", ("CO-8", "CO-9")),
        ("W", ("CO-6",)),
        ("D", ("CO-1", "CO-4", "CO-7")),
    ):
        cause = a_cause(blocked_node=node, depth=1, decomposition=("a", "b"), iterations=4)
        resolved = rpm_gate.rpm_gate(a_request(cause=cause))
        assert resolved.verdict == loop.REPAIR, (node, resolved.verdict)
        assert resolved.code == rpm_gate.BLOCK_NEEDS_A_CHILD_CHAIN, resolved.code
        assert resolved.gap == "the %s (%s) prerequisite at depth 1" % (
            {"P": "Power", "W": "Wisdom", "D": "Desire"}[node], node), resolved.gap
        engine_says = rpm_gate.dwp.resolve(
            rpm_gate.dwp.Node(node),
            rpm_gate.dwp.Blocked(node, "blocked at depth 1"),
            1,
            rpm_gate.dwp.State(decomposition=("a", "b"), iterations=4),
        )
        assert resolved.sub_goal == engine_says.notation, (resolved.sub_goal, engine_says.notation)
        for operator in operators:
            assert operator in resolved.sub_goal, (operator, resolved.sub_goal)
        assert "opens nothing" in resolved.reason

    # 5. Every REPAIR this gate can return names a gap the ladder can ask about, and none of
    #    them may proceed.
    for name, cause, prerequisites, bias_version in cause_rows():
        verdict = rpm_gate.rpm_gate(
            a_request(bias_version=bias_version, prerequisites=prerequisites, cause=cause)
        )
        if verdict.verdict != loop.REPAIR:
            continue
        assert isinstance(verdict.gap, str) and verdict.gap.strip(), (name, verdict.gap)
        assert verdict.sub_goal, (name, "a REPAIR without a sub-goal")
        assert verdict.can_proceed is False
        ladder = disengage.run_ladder(verdict.gap, reason=verdict.reason)
        assert verdict.gap in ladder.ask, (name, ladder.ask)


@case
def the_real_gate_refuses_at_the_horizon_and_the_fix_is_flatten_not_descend():
    """At the horizon the sub-goal would sit past the limit: REFUSE, and name flattening."""
    # The number is depth.py's, and it is the one canon quotes. Checked here so that a change
    # in the vendored copy cannot pass unnoticed.
    assert HORIZON == 5, HORIZON

    for node in ("P", "W"):
        cause = a_cause(blocked_node=node, depth=HORIZON, decomposition=("a", "b"))
        verdict = rpm_gate.rpm_gate(a_request(cause=cause))
        assert verdict.verdict == loop.REFUSE, (node, verdict.verdict)
        assert verdict.code == rpm_gate.STRUCTURAL_DEADLOCK, verdict.code
        assert verdict.can_proceed is False
        assert verdict.sub_goal is None, "a refusal at the horizon named a sub-goal: it descended"
        assert verdict.fix and verdict.fix.startswith("FLATTEN["), verdict.fix
        assert "flatten" in verdict.reason.lower(), verdict.reason
        assert "does not descend" in verdict.reason, verdict.reason
        assert "stability axiom" in verdict.reason, verdict.reason
        assert verdict.gap == "the %s (%s) prerequisite at depth %d" % (
            {"P": "Power", "W": "Wisdom"}[node], node, HORIZON), verdict.gap

        # The named fix really is the engine's flatten, at the same level, adding no level.
        flattened = rpm_gate.depth.flatten(
            rpm_gate.dwp.Chain(
                node=rpm_gate.dwp.Node(node),
                depth=HORIZON,
                tag=rpm_gate.dwp.PENDING,
                label="S",
                state=rpm_gate.dwp.State("S", decomposition=("a", "b")),
            )
        )
        assert verdict.fix == flattened.notation, (verdict.fix, flattened.notation)
        assert flattened.child_depth is None
        assert flattened.vertical_levels_added == 0
        assert {s.depth for s in flattened.siblings} == {HORIZON}
        assert all(not s.children for s in flattened.siblings)
        assert all(s.tag == rpm_gate.dwp.HORIZONTAL for s in flattened.siblings)

    # The horizon decision is depth.py's and not this gate's: for every node and every depth,
    # the gate refuses exactly when dwp.resolve reaches a DeadlockResolution.
    refused_count = 0
    repaired_count = 0
    for node in ("P", "W", "D"):
        for depth_number in range(0, HORIZON + 3):
            cause = a_cause(blocked_node=node, depth=depth_number, decomposition=("a", "b"))
            verdict = rpm_gate.rpm_gate(a_request(cause=cause))
            engine_says = rpm_gate.dwp.resolve(
                rpm_gate.dwp.Node(node),
                rpm_gate.dwp.Blocked(node, "x"),
                depth_number,
                rpm_gate.dwp.State(decomposition=("a", "b")),
            )
            deadlocked = isinstance(engine_says, rpm_gate.dwp.DeadlockResolution)
            assert (verdict.verdict == loop.REFUSE) == deadlocked, (
                node, depth_number, verdict.verdict, engine_says.tag)
            refused_count += 1 if deadlocked else 0
            repaired_count += 0 if deadlocked else 1
    assert refused_count > 0 and repaired_count > 0, (refused_count, repaired_count)

    # The one exception the engine documents, checked from both sides: a Desire block at the
    # horizon adds no level, so it is not a deadlock, even though check_depth says it is.
    assert rpm_gate.depth.check_depth(HORIZON) is rpm_gate.depth.DepthVerdict.STRUCTURAL_DEADLOCK
    desire = rpm_gate.rpm_gate(a_request(cause=a_cause(blocked_node="D", depth=HORIZON)))
    assert desire.verdict == loop.REPAIR, desire.verdict
    assert "adds no level" in desire.reason, desire.reason
    assert desire.fix is None and desire.sub_goal

    # Beyond the horizon: refused, and NO fix is named, because flattening is not available
    # there at all. That refusal is checked against depth.flatten's own refusal.
    beyond = rpm_gate.rpm_gate(a_request(cause=a_cause(blocked_node="P", depth=HORIZON + 1)))
    assert beyond.verdict == loop.REFUSE, beyond.verdict
    assert beyond.code == rpm_gate.HORIZON_BREACHED, beyond.code
    assert beyond.fix is None, beyond.fix
    assert "no fix is named here" in beyond.reason, beyond.reason
    try:
        rpm_gate.depth.flatten(
            rpm_gate.dwp.Chain(
                node=rpm_gate.dwp.Node.P,
                depth=HORIZON + 1,
                tag=rpm_gate.dwp.PENDING,
                label="S",
                state=rpm_gate.dwp.State("S"),
            )
        )
    except rpm_gate.dwp.ArchitectureViolation:
        pass
    else:
        raise AssertionError(
            "depth.flatten accepted a chain beyond the horizon, so the refusal above would "
            "have had no basis"
        )

    # Through a turn: the horizon refusal runs the ladder and the fix is on the receipt.
    record = loop.Loop(a_bias(), "cjt-1", a_proposer()).turn(
        "ACTIVE", "INTENDED", False,
        prerequisites=("power",), cause=a_cause(blocked_node="P", depth=HORIZON),
    )
    assert record.outcome == loop.DISENGAGED, record.outcome
    assert record.gate.code == rpm_gate.STRUCTURAL_DEADLOCK
    assert record.gate.fix and record.gate.fix.startswith("FLATTEN[")
    assert record.receipt[3]["fix"] == record.gate.fix
    assert record.ladder.gap == record.gate.gap


@case
def a_dirty_ancestor_forces_refuse_whatever_else_is_true():
    """An invalidated ancestor line refuses the turn, and nothing else can outrank it."""
    dirty = dict(ancestor_dirty=True, dirty_ancestor="the depth-0 chain",
                 dirty_reason="a Power bypass")
    pairs = (
        ({}, {}),
        (dict(blocked_node="P", depth=2), dict(blocked_node="P", depth=2)),
        (dict(blocked_node="P", depth=HORIZON), dict(blocked_node="P", depth=HORIZON)),
        (dict(blocked_node="D", depth=HORIZON), dict(blocked_node="D", depth=HORIZON)),
        (dict(blocked_node="W", depth=1, decomposition=("a", "b")),
         dict(blocked_node="W", depth=1, decomposition=("a", "b"))),
        (dict(unsatisfied=(NAMED_GAP,)), dict(unsatisfied=(NAMED_GAP,))),
        (dict(resume_from_version=0), dict(resume_from_version=0)),
        (dict(resume_from_version=1), dict(resume_from_version=1)),
    )
    for when_dirty, when_clean in pairs:
        refused = rpm_gate.rpm_gate(a_request(cause=a_cause(**dirty, **when_dirty)))
        assert refused.verdict == loop.REFUSE, (when_dirty, refused.verdict)
        assert refused.code == rpm_gate.ANCESTOR_DIRTY, (when_dirty, refused.code)
        assert refused.can_proceed is False
        assert refused.gap and "clean" in refused.gap, refused.gap
        assert "Power bypass" in refused.reason or "dirty" in refused.reason, refused.reason
        assert "line 63" in refused.reason, refused.reason
        assert refused.sub_goal is None and refused.fix is None
        # The same cause WITH the dirty flag cleared is decided some other way, so the case
        # above is measuring the dirty rule and not a gate that refuses everything.
        plain = rpm_gate.rpm_gate(a_request(cause=a_cause(**when_clean)))
        assert plain.code != rpm_gate.ANCESTOR_DIRTY, (
            when_clean, "the clean twin was refused for being dirty")

    # The propagation is retraction's, and it reaches every ancestor up to the root.
    at_horizon = rpm_gate.rpm_gate(
        a_request(cause=a_cause(blocked_node="P", depth=HORIZON, **dirty))
    )
    for level in range(0, HORIZON + 1):
        assert "depth-%d chain" % (level,) in at_horizon.reason, at_horizon.reason
    assert "retraction.is_dirty" in " | ".join(at_horizon.basis)

    # Canon's own example of a dirty resolution, propagated by the engine's own marking.
    invalid, chain, marked = rpm_gate._invalid_line(
        a_cause(blocked_node="P", depth=3, **dirty)
    )
    assert marked[0].label == "the dirty child", marked[0].label
    assert len(invalid) == 4, [c.label for c in invalid]
    assert all(c.dirty for c in chain.ancestors)
    assert rpm_gate.retraction.is_dirty(invalid[0]) is True

    # Through a turn: the ladder asks for the clean chain and disengages with the reason.
    record = loop.Loop(a_bias(), "cjt-1", a_proposer()).turn(
        "ACTIVE", "INTENDED", False, cause=a_cause(**dirty)
    )
    assert record.outcome == loop.DISENGAGED, record.outcome
    assert record.gate.code == rpm_gate.ANCESTOR_DIRTY
    assert "I need a clean (un-invalidated) depth-0 chain." in record.ladder.ask, record.ladder.ask


@case
def a_stale_bias_forces_refuse():
    """A returning thread's Bias must be strictly newer, and the guard is bias.py's own."""
    for resume_from, version in ((1, 1), (3, 2), (0, 0)):
        verdict = rpm_gate.rpm_gate(
            a_request(bias_version=version, cause=a_cause(resume_from_version=resume_from))
        )
        assert verdict.verdict == loop.REFUSE, (resume_from, version, verdict.verdict)
        assert verdict.code == rpm_gate.STALE_BIAS, verdict.code
        assert verdict.can_proceed is False
        assert verdict.gap and "newer" in verdict.gap, verdict.gap
        assert verdict.sub_goal is None
        # Delegation: the same pair is refused by the one version guard in the build.
        try:
            bias.check_version_increase(resume_from, version)
        except bias.BiasRefusal as refusal:
            assert refusal.code == bias.BIAS_VERSION_WOULD_NOT_INCREASE
        else:
            raise AssertionError(
                "bias.check_version_increase accepted %d -> %d, but the gate refused it"
                % (resume_from, version)
            )

    # Strictly greater is enough: no step size is required.
    newer = rpm_gate.rpm_gate(
        a_request(bias_version=5, cause=a_cause(resume_from_version=2))
    )
    assert newer.verdict == loop.PROCEED, newer.verdict
    assert "strictly newer" in " | ".join(newer.basis)

    # An ordinary turn is never asked, at any version.
    for version in (0, 1, 7):
        plain = rpm_gate.rpm_gate(a_request(bias_version=version, cause=a_cause()))
        assert plain.verdict == loop.PROCEED, (version, plain.verdict)
        assert "not a returning thread" in " | ".join(plain.basis)

    # Through a turn: a_bias() sits at version 1, so a thread suspended at 1 is stale.
    engine = loop.Loop(a_bias(), "cjt-1", a_proposer())
    record = engine.turn("ACTIVE", "INTENDED", False, cause=a_cause(resume_from_version=1))
    assert record.outcome == loop.DISENGAGED, record.outcome
    assert record.gate.code == rpm_gate.STALE_BIAS
    assert record.bias_snapshot.version == 1
    assert "strictly newer" in record.ladder.ask, record.ladder.ask


@case
def the_asom_label_cannot_change_the_real_gates_verdict():
    """The whole decision surface of the REAL gate, twice: computed, and forced. Identical.

    This is the 150-cell proof of the previous step, extended: the real gate's verdicts now
    depend on the cause, so the matrix is 16 causes x 30 observation cells = 480 turns, and
    every one of them is decided by ``rpm_gate`` itself. All three verdict words are reached,
    so the comparison covers PROCEED, REPAIR and REFUSE.
    """
    computed_rows, computed_requests = cause_matrix_run(loop, asom.readout)
    cells = len(REGIONS) * len(SEMANTIC_OUTCOMES) * len(SATURATION)
    assert cells == 30, cells
    assert len(computed_rows) == len(CAUSE_FIELDS) * cells, len(computed_rows)
    assert len(computed_rows) == 480, len(computed_rows)

    computed_labels = set(labels_of(computed_rows))
    assert {asom.STARVED, asom.ALIGNED, asom.OVERSATURATED, asom.MISALIGNED}.issubset(
        computed_labels
    ), computed_labels
    assert asom.NOT_EMITTED in computed_labels
    assert len(computed_labels) == 5, computed_labels

    computed_words = {row[7].gate.verdict for row in computed_rows}
    assert computed_words == set(loop.VERDICT_WORDS), computed_words
    computed_codes = {row[7].gate.code for row in computed_rows}
    assert {rpm_gate.NOTHING_BLOCKED, rpm_gate.PREREQUISITE_MISSING,
            rpm_gate.BLOCK_NEEDS_A_CHILD_CHAIN, rpm_gate.FUNCTOR_NEEDS_INPUT,
            rpm_gate.STRUCTURAL_DEADLOCK, rpm_gate.HORIZON_BREACHED,
            rpm_gate.ANCESTOR_DIRTY, rpm_gate.STALE_BIAS}.issubset(computed_codes), computed_codes

    for forced_label in (
        asom.STARVED,
        asom.ALIGNED,
        asom.OVERSATURATED,
        asom.MISALIGNED,
        asom.NOT_EMITTED,
    ):
        forced_rows, forced_requests = cause_matrix_run(loop, forced(forced_label))
        assert len(forced_rows) == len(computed_rows)
        # 1. the labels really were forced
        assert labels_of(forced_rows) == [forced_label] * len(forced_rows)
        differed = sum(
            1
            for computed, was_forced in zip(labels_of(computed_rows), labels_of(forced_rows))
            if computed != was_forced
        )
        assert differed > 0, "forcing %s changed no label, so the comparison is vacuous" % (
            forced_label,)
        # 2. every decision is identical, cell for cell: verdict, gap, reason, code, sub-goal,
        #    fix, the turn's outcome, the ladder's steps, its ask and its disengage reason.
        assert decisions_of(forced_rows) == decisions_of(computed_rows), (
            "forcing the ASOM label to %s changed a decision of the real gate" % (forced_label,))
        # 3. the gate was handed an equal request, including the cause, every time.
        assert forced_requests == computed_requests, (
            "forcing the ASOM label to %s changed what the real gate was asked" % (forced_label,))
        assert [row[5] for row in forced_rows] == [row[5] for row in computed_rows]


@case
def a_gate_that_reads_the_label_changes_decisions_and_is_caught():
    """A broken copy of the GATE, wired to the readout, changes decisions -- and is caught.

    The gate cannot reach the label on its own: nothing on the request carries one. So the
    mutation takes two files, and needing both IS the proof. Part (a): the broken gate alone
    decides exactly what the real gate decides, because nothing hands it a label. Part (b): a
    label written into its module changes its answer. Part (c): a broken loop that hands it the
    label changes the verdicts the matrix above compares, which is the failure that test must
    catch -- and does.
    """
    gate_source = read_build_file("rpm_gate.py")
    cause_line = "    cause = _checked(request)"
    assert cause_line in gate_source, (
        "the line this check rewrites is not in rpm_gate.py any more, so the mutation would "
        "silently prove nothing"
    )
    injected = (
        '    _seen = globals().get("ASOM_LABEL")\n'
        '    if _seen == "MISALIGNED":\n'
        '        return GateVerdict(verdict=REFUSE, gap="ASOM", reason="the readout said '
        'MISALIGNED")\n'
    )
    broken_gate_source = gate_source.replace(cause_line, injected + cause_line, 1)
    assert broken_gate_source != gate_source

    broken_gate = types.ModuleType("rpm_gate_broken_on_purpose")
    broken_gate.__file__ = os.path.join(BUILD_DIR, "rpm_gate.py")
    sys.modules[broken_gate.__name__] = broken_gate
    exec(
        compile(broken_gate_source, "<rpm_gate.py with the label read>", "exec"),
        broken_gate.__dict__,
    )
    assert hasattr(broken_gate, "rpm_gate")

    # (a) The broken gate alone, against the real loop's requests: identical decisions.
    pairs = []
    for name, cause, prerequisites, version in cause_rows():
        real = rpm_gate.rpm_gate(request_for(cause, prerequisites, version))
        broken_form = build_cause(broken_gate.RpmCause, **{
            field: getattr(cause, field) for field in field_names(rpm_gate.RpmCause)
        })
        broken = broken_gate.rpm_gate(request_for(broken_form, prerequisites, version))
        assert real.as_dict() == broken.as_dict(), (
            name, "the broken gate decided differently without ever being given a label")
        pairs.append((real, broken))
    assert len(pairs) == len(CAUSE_FIELDS)

    # (b) Write a label into the broken gate's own module and its answer changes.
    before = [row[1].as_dict() for row in pairs]
    broken_gate.ASOM_LABEL = asom.MISALIGNED
    try:
        after = [
            broken_gate.rpm_gate(request_for(build_cause(broken_gate.RpmCause, **{
                field: getattr(cause, field) for field in field_names(rpm_gate.RpmCause)
            }), prerequisites, version)).as_dict()
            for name, cause, prerequisites, version in cause_rows()
        ]
    finally:
        del broken_gate.ASOM_LABEL
    assert before != after, "the injection into the gate never took effect"

    # (c) A broken LOOP that hands the gate the label, plus the broken gate: the matrix catches
    #     it, and the real pair run the same way is unchanged.
    loop_source = read_build_file("loop.py")
    assert GATE_LINE in loop_source, (
        "the gate line this check rewrites is not in loop.py any more")
    broken_loop_source = loop_source.replace(
        GATE_LINE, "        rpm.ASOM_LABEL = observation.label\n" + GATE_LINE, 1
    )
    assert broken_loop_source != loop_source

    broken_loop = types.ModuleType("loop_broken_on_purpose")
    broken_loop.__file__ = os.path.join(BUILD_DIR, "loop.py")
    sys.modules[broken_loop.__name__] = broken_loop
    real_gate_module = sys.modules["rpm_gate"]
    sys.modules["rpm_gate"] = broken_gate
    try:
        exec(
            compile(
                broken_loop_source,
                "<loop.py handing the gate the readout>",
                "exec",
            ),
            broken_loop.__dict__,
        )
    finally:
        sys.modules["rpm_gate"] = real_gate_module
    assert broken_loop.rpm is broken_gate, "the broken loop did not take the broken gate"

    broken_computed, _ = cause_matrix_run(broken_loop, asom.readout,
                                          cause_class=broken_gate.RpmCause)
    broken_forced, _ = cause_matrix_run(broken_loop, forced(asom.MISALIGNED),
                                        cause_class=broken_gate.RpmCause)
    clean_computed, _ = cause_matrix_run(loop, asom.readout)

    # The mutation moved decisions away from the real gate's: the matrix above would fail.
    assert decisions_of(broken_computed) != decisions_of(clean_computed), (
        "the injection never took effect at the turn level: the broken pair decided exactly "
        "what the real pair decided, so this check proves nothing"
    )
    # And it moved them in the direction a label-reading gate would: forced MISALIGNED refuses.
    flipped = sum(
        1
        for clean, dirty in zip(decisions_of(clean_computed), decisions_of(broken_forced))
        if clean != dirty
    )
    assert flipped > 0, flipped
    assert decisions_of(broken_forced) != decisions_of(broken_computed)

    # The real pair, run the same two ways, is identical: the difference above is caused by the
    # injected lines and by nothing else.
    clean_forced, _ = cause_matrix_run(loop, forced(asom.MISALIGNED))
    assert decisions_of(clean_forced) == decisions_of(clean_computed)


@case
def the_gate_uses_the_vendored_engine_and_reimplements_none_of_it():
    """The gate asks depth.py, dwp.resolve, retraction and bias.py. It writes no rule of its own."""
    # The modules really are the copies in dwp/, loaded from there by path.
    for module, name in (
        (rpm_gate.dwp, "dwp.py"),
        (rpm_gate.depth, "depth.py"),
        (rpm_gate.retraction, "retraction.py"),
    ):
        assert os.path.abspath(module.__file__) == os.path.abspath(
            os.path.join(BUILD_DIR, "dwp", name)
        ), (name, module.__file__)
    assert rpm_gate.VENDOR_DIR == os.path.join(BUILD_DIR, "dwp"), rpm_gate.VENDOR_DIR
    assert rpm_gate.depth.HORIZON == 5
    assert rpm_gate.depth.DepthVerdict.OK.value == "OK"
    assert rpm_gate.depth.DepthVerdict.STRUCTURAL_DEADLOCK.value == "STRUCTURAL_DEADLOCK"
    assert rpm_gate.retraction.DEFAULT_DIRTY_REASON
    assert rpm_gate.dwp.CANON_DEADLOCK and rpm_gate.dwp.CANON_PHI_D

    # The gate never writes the horizon itself: no assignment of a horizon constant, and no
    # vertical recursion of its own. It reads depth.HORIZON and asks check_depth/flatten.
    source = read_build_file("rpm_gate.py")
    assert not re.search(r"^HORIZON\s*=", source, re.MULTILINE), (
        "the gate assigned its own horizon; the number belongs to dwp/depth.py")
    assert "depth.check_depth(" in source
    assert "depth.flatten(" in source
    assert "retraction.mark_dirty_upward(" in source
    assert "retraction.is_dirty(" in source
    assert "dwp.resolve(" in source
    assert "bias_module.check_version_increase(" in source
    # And it never touches the readout: no import of it, no handle on it, no field for it.
    assert "import asom" not in source, "the gate imports the readout"
    assert not hasattr(rpm_gate, "asom")
    assert "import loop" not in source, "the gate imports the loop"
    assert "region" not in rpm_gate.RPM_CAUSE_FIELDS
    assert "saturated" not in rpm_gate.RPM_CAUSE_FIELDS
    # What the gate does mention about the readout is prose in its docstring: the executable
    # part of the module never names it.
    code_only = source.split('"""', 2)[2] if source.count('"""') >= 3 else ""
    assert code_only, "rpm_gate.py has no code outside its docstring"
    assert "asom" not in code_only.lower(), "the gate's code mentions the readout"

    # One entry point, and it takes exactly one argument: there is no second opinion.
    parameters = inspect.signature(rpm_gate.rpm_gate).parameters
    assert list(parameters) == ["request"], list(parameters)
    assert rpm_gate.VERDICT_WORDS == (loop.PROCEED, loop.REPAIR, loop.REFUSE)
    assert loop.GateVerdict is rpm_gate.GateVerdict
    assert loop.LOOP_GATE_VERDICT_NOT_A_WORD == rpm_gate.GATE_VERDICT_NOT_A_WORD

    # A verdict word that is not one of the three cannot be constructed at all.
    try:
        rpm_gate.GateVerdict("PROCEED-SORT-OF")
    except rpm_gate.GateViolation as refusal:
        assert refusal.code == rpm_gate.GATE_VERDICT_NOT_A_WORD
    else:
        raise AssertionError("a verdict that is not one of the three words was constructed")

    # A malformed cause is refused by the gate, and never becomes a verdict.
    for bad in (
        dict(depth=-1),
        dict(depth="2"),
        dict(blocked_node="Q"),
        dict(ancestor_dirty="yes"),
        dict(unsatisfied=("",)),
        dict(wisdom_route="CO-7"),
        dict(iterations=-1),
        dict(resume_from_version="3"),
    ):
        cause = rpm_gate.RpmCause(**bad)
        try:
            rpm_gate.rpm_gate(a_request(cause=cause))
        except rpm_gate.GateViolation as refusal:
            assert refusal.code == rpm_gate.RPM_CAUSE_NOT_A_CAUSE, (bad, refusal.code)
        else:
            raise AssertionError("a malformed cause produced a verdict: %r" % (bad,))
    # A cause of the wrong class, and a request that is not a request, are refused too.
    for wrong in (object(), None, "a cause"):
        try:
            rpm_gate.rpm_gate(a_request(cause=wrong))
        except rpm_gate.GateViolation as refusal:
            assert refusal.code == rpm_gate.RPM_CAUSE_NOT_A_CAUSE, (wrong, refusal.code)
        else:
            raise AssertionError("a cause of type %r was accepted" % (type(wrong),))
    try:
        rpm_gate.rpm_gate({"cause": rpm_gate.RpmCause()})
    except rpm_gate.GateViolation as refusal:
        assert refusal.code == rpm_gate.RPM_REQUEST_NOT_A_GATE_REQUEST, refusal.code
    else:
        raise AssertionError("a dict was accepted as a gate request")

    # The number the gate borrows for N is the engine's default, so the two cannot disagree.
    assert rpm_gate.RpmCause().iterations == rpm_gate.dwp.State().iterations, (
        rpm_gate.RpmCause().iterations, rpm_gate.dwp.State().iterations)


# --------------------------------------------------------------------------- #
# The runner
# --------------------------------------------------------------------------- #
def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (ValueError, OSError):  # pragma: no cover - a console that refuses
                pass
    print("the_loop_v2 / test_all.py")
    print("python: %s  platform: %s" % (platform.python_version(), platform.system()))
    print("build folder: %s" % (BUILD_DIR,))
    for name in COPIED_MODULES + VENDORED_MODULES:
        path = locate_copy(name)
        with open(path, "rb") as handle:
            print("%s sha256: %s" % (name, hashlib.sha256(handle.read()).hexdigest()))
    sources_seen = sum(
        1
        for name in COPIED_MODULES + VENDORED_MODULES
        if os.path.isfile(os.path.join(SOURCE_FOLDERS[name], name))
    )
    print("source files re-hashed on this machine: %d of %d" % (
        sources_seen, len(COPIED_MODULES) + len(VENDORED_MODULES)))
    print("engine: dwp %s, depth %s, retraction %s" % (
        os.path.basename(rpm_gate.dwp.__file__),
        os.path.basename(rpm_gate.depth.__file__),
        os.path.basename(rpm_gate.retraction.__file__),
    ))
    print("claim ceiling: %s" % (CLAIM_CEILING,))
    print("undecided markers of this build: %d" % (
        len(undecided_questions("UNDECIDED IN SOURCES", OWN_MODULES)),
    ))
    print("undecided markers marked UNDECIDED IN CANON: %d" % (
        len(undecided_questions("UNDECIDED IN CANON", OWN_MODULES)),
    ))
    print("undecided markers inherited with the copies: %d" % (
        len(undecided_questions("UNDECIDED IN DESIGN", COPIED_MODULES)),
    ))
    print("-" * 78)
    passed = 0
    failed = 0
    for function in CASES:
        name = function.__name__
        try:
            function()
        except Exception as exc:  # noqa: BLE001 - a test runner must catch everything
            failed += 1
            print("FAIL %s: %s: %s" % (name, ascii_safe(type(exc).__name__), ascii_safe(exc)))
        else:
            passed += 1
            print("PASS %s" % (name,))
    print("-" * 78)
    total = passed + failed
    print("TOTAL %d cases: %d passed, %d failed" % (total, passed, failed))
    print("RESULT: %s" % ("ALL PASS" if failed == 0 else "FAILURES PRESENT",))
    print("claim ceiling, repeated: %s" % (CLAIM_CEILING,))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
