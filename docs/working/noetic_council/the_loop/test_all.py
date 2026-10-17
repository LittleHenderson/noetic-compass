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
  * when the gate cannot proceed, the ladder runs and names the exact gap it was given;
  * the ladder's four steps appear in order in the receipt;
  * a disengage carries a reason, and a disengage without one is refused; a gate that names
    no gap is refused rather than asked vaguely;
  * the copied files are byte-identical to the hashes recorded in ``PROVENANCE.md``;
  * the readout is a display with nothing to gate with;
  * ``README.md`` states the claim ceiling and lists every undecided line.

WHAT THIS FILE DOES NOT DO
--------------------------
  * It does NOT make or check any RPM decision. The gate is a stub; the refusals exercised
    here are gates written in this file, not RPM.
  * It does NOT prove anything was thought, meant, or understood. Every case is a mechanism
    check.
  * It does NOT use pytest, numpy, torch, any network, or any cloud service. Standard library
    only, and it runs in well under a second.
  * It does NOT write any file.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. THE GATE IS A STUB. NO REAL RPM DECISION IS MADE HERE.
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

CLAIM_CEILING = "MECHANISM ONLY. THE GATE IS A STUB. NO REAL RPM DECISION IS MADE HERE."

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

OWN_MODULES = ("bias.py", "loop.py")
COPIED_MODULES = ("asom.py", "disengage.py")

#: The line in loop.py that the mutation check rewrites. It is looked up by text, so if the
#: line ever moves or changes, the test fails loudly instead of quietly proving nothing.
GATE_LINE = "        verdict = self._gate(request)  # THE GATE DECIDES. Nothing else may."


def ascii_safe(value):
    """A string that is safe to print on a console that cannot take every character."""
    return ascii(str(value))


def read_build_file(name):
    with open(os.path.join(BUILD_DIR, name), encoding="utf-8") as handle:
        return handle.read()


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

    Two of them proceed and three of them cannot, and none of them is RPM: the stub is a
    placeholder, and the other four are written here so that a refusal caused by the gate can
    be exercised. What they all share is that they read the GateRequest and nothing else.
    """
    return (
        ("proceeding", module.proceeding_gate),
        ("stub", module.stub_gate),
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
    assert as_dict["gate"]["stub"] is True
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
    ], fields
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
    """Nothing here may be mistaken for an RPM decision after the fact."""
    assert loop.CLAIM_CEILING == CLAIM_CEILING == (
        "MECHANISM ONLY. THE GATE IS A STUB. NO REAL RPM DECISION IS MADE HERE."
    )
    engine = loop.Loop(a_bias(), "cjt-1", a_proposer())
    record = engine.turn("ACTIVE", "INTENDED", False)
    assert record.gate.verdict == loop.PROCEED
    assert record.gate.stub is True
    assert record.gate.reason == loop.STUB_NOTE
    assert "STUB" in record.gate.reason
    assert "no RPM prerequisite check" in record.gate.reason
    assert record.as_dict()["gate"]["stub"] is True
    # The stub gate cannot refuse and cannot name a gap: it is not a decision.
    verdict = loop.stub_gate(loop.GateRequest(1, "cjt-1", 1, "d", "p", ()))
    assert verdict.gap is None and verdict.can_proceed is True
    # And a gate written by a caller is marked as not the stub.
    assert loop.proceeding_gate(loop.GateRequest(1, "cjt-1", 1, "d", "p", ())).stub is False


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
    """PROVENANCE.md says the bytes; this recomputes them and requires a match."""
    provenance = read_build_file("PROVENANCE.md")
    recorded = dict(
        re.findall(r"^([\w.]+) copy sha256: ([0-9a-f]{64})$", provenance, re.MULTILINE)
    )
    sources = dict(
        re.findall(r"^([\w.]+) source sha256: ([0-9a-f]{64})$", provenance, re.MULTILINE)
    )
    assert set(recorded) == set(COPIED_MODULES), sorted(recorded)
    assert set(sources) == set(COPIED_MODULES), sorted(sources)

    for name in COPIED_MODULES:
        with open(os.path.join(BUILD_DIR, name), "rb") as handle:
            actual = hashlib.sha256(handle.read()).hexdigest()
        assert actual == recorded[name], (name, actual, recorded[name])
        assert recorded[name] == sources[name], (
            "%s differs from the source it was copied from" % (name,)
        )

    # The copies still say what this build relies on them saying.
    assert asom.LABELS == (asom.STARVED, asom.ALIGNED, asom.OVERSATURATED, asom.MISALIGNED)
    assert disengage.STEPS == ("NOT_DECLARED", "CONFUSED", "ASK_CLARITY", "DISENGAGE")
    assert asom.MISALIGNED == "MISALIGNED" and disengage.DISENGAGE_NEEDS_REASON
    # And nothing else was copied in: this build is these four files plus its own two.
    expected = {
        "asom.py",
        "bias.py",
        "disengage.py",
        "loop.py",
        "test_all.py",
        "README.md",
        "PROVENANCE.md",
    }
    present = {name for name in os.listdir(BUILD_DIR) if os.path.isfile(os.path.join(BUILD_DIR, name))}
    assert present == expected, sorted(present ^ expected)


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
    assert "MECHANISM ONLY. THE GATE IS A STUB. NO REAL RPM DECISION IS MADE HERE." in readme

    own = undecided_questions("UNDECIDED IN SOURCES", OWN_MODULES)
    assert len(own) >= 10, len(own)
    missing = [question for question in own if question not in readme]
    assert not missing, "README.md does not list %d undecided line(s), first: %s" % (
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
        "The gate is a stub",
        "placeholder",
        "MECHANISM ONLY.",
        "UNDECIDED IN SOURCES",
    ):
        assert phrase in readme, phrase


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
    print("the_loop / test_all.py")
    print("python: %s  platform: %s" % (platform.python_version(), platform.system()))
    print("build folder: %s" % (BUILD_DIR,))
    for name in COPIED_MODULES:
        with open(os.path.join(BUILD_DIR, name), "rb") as handle:
            print("%s sha256: %s" % (name, hashlib.sha256(handle.read()).hexdigest()))
    print("claim ceiling: %s" % (CLAIM_CEILING,))
    print("undecided markers of this build: %d" % (
        len(undecided_questions("UNDECIDED IN SOURCES", OWN_MODULES)),
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
