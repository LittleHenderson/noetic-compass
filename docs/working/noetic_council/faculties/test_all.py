"""test_all.py -- one runnable test file for the faculties build. No pytest needed.

WHAT THIS FILE DOES
-------------------
It proves every rule the owning instruction names, with explicit cases and explicit numbers,
and prints one PASS or FAIL line per case plus a total. Run it with:

    python -B test_all.py

It covers, in this order:

  * the four faculties are the four the design names, and there is no fifth;
  * a faculty writes HELD and nothing else, and a direct ADMITTED write is refused;
  * no faculty can write the Bias -- proved three ways: the view a faculty is given has no
    write method, the copied Bias refuses a writer named `FACULTY:<name>`, and a faculty
    return value carrying a Bias write is refused by the guard;
  * **imagined evidence cannot be passed to the verifier at all** -- it is a different type,
    not a subclass, and `verify` refuses it with `IMAGINED_EVIDENCE_CANNOT_VERIFY` before any
    checker is called (the checker is instrumented and proved never to have run);
  * a daydream stays a daydream until real evidence verifies it, and an unverified daydream
    never changes what the brain believes (the Bias version and digest do not move);
  * an admission on real evidence **does** reach the Bias, so the negative cases above are not
    passing vacuously;
  * pondering runs only when idle, in the faculty and in the drive loop;
  * self-notice records one receipt per nesting level, the labels spell the design's own
    example word, a failed level invalidates its parents, and the depth cap holds;
  * the held buffer never loses a refused or expired candidate, and every transition records
    who moved it and why;
  * the drive loop is deterministic for the same inputs, records every tick, and is proved not
    to be deterministic-by-accident (a different seed changes the order);
  * `README.md` states the claim ceiling, gives one line per faculty, and lists every
    `UNDECIDED IN DESIGN` mark in the code word for word -- a test fails if the lists drift;
  * nothing here imports anything outside the standard library.

WHAT THIS FILE DOES NOT DO
--------------------------
  * It does NOT prove anything thinks, wonders or imagines. Every case is a mechanism check on
    inputs this file supplies.
  * It does NOT run a faculty inside HELM. No world, no family, no book, no model is here.
  * It does NOT test a fitter, a writer, RPM, the Lacunarity Machine or Fisher-Rao reporting.
    None of those is in this build.
  * It uses no pytest, no numpy, no torch, no network and writes no file.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import ast
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

import bias as bias_module
import drive_loop
import faculties
import guard
import held

CLAIM_CEILING = "MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM."

COORDINATOR = "COORDINATOR"

#: The modules this build wrote (the copied `bias.py` is checked separately).
OWN_MODULES = ("guard.py", "held.py", "faculties.py", "drive_loop.py", "test_all.py")
COPIED_MODULES = ("bias.py",)

#: The cases, in the order they run.
CASES = []


def case(function):
    """Register one test case."""
    CASES.append(function)
    return function


# --------------------------------------------------------------------------- #
# Small builders
# --------------------------------------------------------------------------- #
def fresh():
    """A Bias and a held buffer at tick 0."""
    working = bias_module.Bias(COORDINATOR)
    buffer = held.HeldBuffer()
    buffer.begin_tick(0)
    return working, buffer


def real_rows(forms, count=1, cell="c1", start=0):
    """`count` real rows, cycling through `forms`."""
    if isinstance(forms, str):
        forms = (forms,)
    out = []
    for index in range(count):
        form = forms[index % len(forms)]
        out.append(
            guard.Row("r%03d" % (start + index), guard.REAL, {"canonical_form": form, "cell": cell})
        )
    return tuple(out)


def internal_rows(forms, count=1, world="W0", start=0):
    if isinstance(forms, str):
        forms = (forms,)
    out = []
    for index in range(count):
        form = forms[index % len(forms)]
        out.append(
            guard.Row(
                "i%03d" % (start + index),
                guard.INTERNAL,
                {"canonical_form": form, "world": world},
            )
        )
    return tuple(out)


def eight_real_rows(form):
    """A real witness set big enough for the default support mark."""
    return real_rows(form, count=guard.MIN_SUPPORT_ROWS)


def world_builder_for(forms, counter=None):
    """A world builder that makes one imagined world per call, cycling through `forms`."""
    state = counter if counter is not None else {"n": 0}

    def build(reading, k=None):
        index = state["n"]
        state["n"] = index + 1
        form = forms[index % len(forms)]
        world_id = "W%d" % index
        rows = internal_rows([form], count=2, world=world_id, start=index * 2)
        return (faculties.ImaginedWorld(world_id, form, rows, "OMEGA_A", seed=index),)

    build.counter = state
    return build


def refit_for(prefix="REFIT"):
    def refit(group, reading):
        return [("%s_%s" % (prefix, group[0].row_id), "OMEGA_A")]

    return refit


def unexplained_idle():
    rows = (guard.Row("u001", guard.REAL, {"canonical_form": "ROW_U1", "cell": "c1"}),)
    return faculties.Unexplained(rows=rows, idle=True)


def make_loop(arm="GREEDY", seed=0, with_imagination=True, with_pondering=True):
    """A drive loop wired to the two faculties this build can give a turn to."""
    working, buffer = fresh()
    builder = world_builder_for(("DREAM_A", "DREAM_B"))

    def imagine_action(idle):
        return faculties.imagination(working, buffer, builder)

    def ponder_action(idle):
        return faculties.pondering(working, buffer, faculties.Unexplained(
            rows=(guard.Row("u001", guard.REAL, {"canonical_form": "ROW_U1", "cell": "c1"}),),
            idle=idle,
        ), refit_for())

    loop = drive_loop.DriveLoop(
        working,
        buffer,
        coordinator=COORDINATOR,
        arm=arm,
        seed=seed,
        imagine=imagine_action if with_imagination else None,
        ponder=ponder_action if with_pondering else None,
    )
    return loop, working, buffer


def drive(loop, ticks=12, input_every=3):
    """Run ticks; every `input_every`-th tick carries one new real row."""
    records = []
    for index in range(ticks):
        incoming = real_rows("IN_ROW", count=1, start=index) if (input_every and index % input_every == 0) else ()
        records.append(loop.tick(new_input=incoming))
    return records


# --------------------------------------------------------------------------- #
# The witnesses: hash of the copy, and what the modules may say
# --------------------------------------------------------------------------- #
def read_build_file(name):
    with open(os.path.join(BUILD_DIR, name), "r", encoding="utf-8") as handle:
        return handle.read()


def undecided_lines(prefix, modules):
    """Every `# UNDECIDED ...` marker in the named modules, as written in the code."""
    marker = re.compile(r"#\s*" + re.escape(prefix) + r":\s*(.+?)\s*$")
    found = []
    for name in modules:
        for line in read_build_file(name).splitlines():
            match = marker.search(line)
            if match:
                found.append((name, match.group(1).strip()))
    return found


# --------------------------------------------------------------------------- #
# 1. The copies
# --------------------------------------------------------------------------- #
@case
def test_the_copied_bias_is_byte_identical_to_the_recorded_hash():
    """The copy of `bias.py` is re-hashed on every run and must match PROVENANCE.md."""
    provenance = read_build_file("PROVENANCE.md")
    recorded = re.search(r"bias\.py copy sha256:\s*([0-9a-f]{64})", provenance)
    assert recorded, "PROVENANCE.md records no bias.py copy sha256"
    with open(os.path.join(BUILD_DIR, "bias.py"), "rb") as handle:
        actual = hashlib.sha256(handle.read()).hexdigest()
    assert actual == recorded.group(1), "copy sha256 %s != recorded %s" % (actual, recorded.group(1))
    source = re.search(r"bias\.py source sha256:\s*([0-9a-f]{64})", provenance)
    assert source, "PROVENANCE.md records no bias.py source sha256"
    assert source.group(1) == actual, "the recorded source hash and the copy disagree"


@case
def test_nothing_here_imports_anything_outside_the_standard_library():
    """Standard library only: no torch, no numpy, no socket, no network, no cloud."""
    allowed = {
        "__future__", "ast", "collections", "dataclasses", "fractions", "hashlib", "json",
        "os", "platform", "re", "sys", "inspect", "copy", "math", "types",
        "bias", "drive_loop", "faculties", "guard", "held",
    }
    for name in OWN_MODULES:
        tree = ast.parse(read_build_file(name), filename=name)
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    roots.add(node.module.split(".")[0])
        strangers = roots - allowed
        assert not strangers, "%s imports %s, which is not allowed here" % (name, sorted(strangers))


# --------------------------------------------------------------------------- #
# 2. The roster
# --------------------------------------------------------------------------- #
@case
def test_the_faculties_are_the_four_the_design_names():
    """Exactly four, named as the design names them, and no fifth faculty."""
    assert faculties.FACULTIES == ("wondering", "pondering", "imagination", "self_notice")
    assert set(faculties.FACULTY_LABELS) == set(faculties.FACULTIES)
    for name in faculties.FACULTIES:
        function = getattr(faculties, name, None)
        assert callable(function), "faculties.%s is not callable" % name
        assert function.__module__ == "faculties"
    # "Contemplation" is not a faculty in this package: it must not be a module-level name.
    assert not hasattr(faculties, "contemplation")
    assert not hasattr(faculties, "contemplation_faculty")
    for name in dir(faculties):
        assert "contemplat" not in name.lower(), "invented a sixth faculty: %s" % name


@case
def test_the_faculty_signatures_are_the_ones_the_instruction_gives():
    """Each faculty takes the parameters the owning instruction names, in that order."""
    expected = {
        "wondering": ["bias", "held", "surface"],
        "pondering": ["bias", "held", "unexplained", "refit"],
        "imagination": ["bias", "held", "world_builder"],
        "self_notice": ["inner_faculty"],
    }
    for name, wanted in expected.items():
        parameters = list(inspect.signature(getattr(faculties, name)).parameters)
        assert parameters[: len(wanted)] == wanted, "%s takes %s, expected %s" % (name, parameters, wanted)


# --------------------------------------------------------------------------- #
# 3. A faculty writes HELD and nothing else
# --------------------------------------------------------------------------- #
@case
def test_a_faculty_writes_held_and_nothing_else():
    """Every one of the four writes HELD candidates and no other state."""
    working, buffer = fresh()
    builder = world_builder_for(("DREAM_A",))

    reports = {
        "wondering": faculties.wondering(working, buffer, [("W_A", "OMEGA_A"), ("W_B", "OMEGA_A")]),
        "pondering": faculties.pondering(working, buffer, unexplained_idle(), refit_for()),
        "imagination": faculties.imagination(working, buffer, builder),
    }

    def inner():
        return faculties.wondering(working, buffer, [("W_C", "OMEGA_A")])

    reports["self_notice"] = faculties.self_notice(inner, depth=1, held=buffer, as_faculty="wondering")

    written = 0
    for name, report in reports.items():
        assert report.faculty in ("wondering", "pondering", "imagination", "self_notice")
        assert report.wrote, "%s wrote nothing on an input that should have produced candidates" % name
        for candidate_id in report.wrote:
            assert buffer.state_of(candidate_id) == held.HELD
            written += 1
    assert written == len(buffer.entries())
    assert buffer.counts()[held.ADMITTED] == 0
    assert buffer.counts()[held.REFUSED] == 0
    assert buffer.counts()[held.EXPIRED] == 0
    # No faculty report carries a verdict or an admission.
    for report in reports.values():
        walked = guard.check_faculty_return(report.faculty, report)
        assert walked is report


@case
def test_a_direct_admitted_write_is_refused():
    """A faculty cannot label a candidate true: the claimed state must be HELD."""
    working, buffer = fresh()
    for claimed in (held.ADMITTED, held.REFUSED, held.EXPIRED):
        try:
            held.Proposal("X", "wondering", claimed_state=claimed)
            proposal = held.Proposal("X", "wondering", claimed_state=claimed)
            buffer.put(proposal)
        except held.HeldRefusal as refusal:
            assert refusal.code in (held.HELD_ONLY_HELD_ENTERS, held.HELD_CLAIMED_STATE_NOT_A_WORD)
            assert claimed in refusal.detail
        else:
            raise AssertionError("a candidate claiming %s was accepted" % claimed)
    assert len(buffer) == 0
    # And the state is not a word at all.
    try:
        held.Proposal("X", "wondering", claimed_state="TRUE")
    except held.HeldRefusal as refusal:
        assert refusal.code == held.HELD_CLAIMED_STATE_NOT_A_WORD
    else:
        raise AssertionError("a proposal claiming TRUE was accepted")
    # A faculty may not label a candidate INSIGHT either: an insight is what an admission
    # produces, not what a faculty writes.
    try:
        held.Proposal("X", "imagination", label=held.INSIGHT)
    except held.HeldRefusal as refusal:
        assert refusal.code == held.HELD_INSIGHT_IS_NOT_A_FACULTY_LABEL
    else:
        raise AssertionError("a faculty labelled a candidate INSIGHT")


@case
def test_a_candidate_leaves_held_only_through_a_minted_verdict():
    """A hand-made verdict, and an unverifiable one, are both refused by the buffer."""
    working, buffer = fresh()
    entry = buffer.put(held.Proposal("FORM_A", "wondering"))
    # 1. Building a Verdict directly is refused.
    try:
        guard.Verdict(guard.ADMITTED, "MADE_UP", guard.REAL_EVIDENCE, "nobody", seal=None)
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.VERDICT_MUST_BE_MINTED
    else:
        raise AssertionError("a Verdict was built without the seal")
    # 2. A hand-made object shaped like a verdict is not a verdict.
    fake = object.__new__(guard.Verdict)
    assert guard.is_verdict(fake) is False
    try:
        buffer.settle(entry.candidate_id, fake)
    except held.HeldRefusal as refusal:
        assert refusal.code == held.HELD_ONLY_A_VERIFIER_MOVES
    else:
        raise AssertionError("the buffer accepted a hand-made verdict")
    # 3. A plain truthy value is not a verdict either.
    try:
        buffer.settle(entry.candidate_id, True)
    except held.HeldRefusal as refusal:
        assert refusal.code == held.HELD_ONLY_A_VERIFIER_MOVES
    else:
        raise AssertionError("the buffer accepted True as a verdict")
    assert buffer.state_of(entry.candidate_id) == held.HELD


# --------------------------------------------------------------------------- #
# 4. No faculty can write the Bias
# --------------------------------------------------------------------------- #
@case
def test_no_faculty_can_write_the_bias():
    """Three separate walls, all proved here."""
    working, buffer = fresh()
    before_version = working.version
    before_digest = working.snapshot().digest

    # Wall 1: the object a faculty is given has no write method at all.
    reading = guard.bias_reading(working)
    assert not hasattr(reading, "write")
    assert not hasattr(reading, "snapshot")
    try:
        reading.write("key", 1, COORDINATOR)
    except AttributeError as exc:
        assert "write" in str(exc)
    else:
        raise AssertionError("a BiasReading offered a write method")

    # Wall 2: the copied Bias itself refuses any faculty as a writer.
    for name in faculties.FACULTIES:
        coordinator = guard.coordinator_for_faculty(name)
        assert coordinator == "FACULTY:%s" % name
        try:
            working.write("faculty:%s" % name, 1, coordinator)
        except bias_module.BiasRefusal as refusal:
            assert refusal.code == bias_module.BIAS_OWNED_BY_ANOTHER_COORDINATOR
        else:
            raise AssertionError("the Bias accepted a write from %s" % coordinator)

    # Wall 3: the belief door refuses a faculty coordinator by name, even with a real verdict.
    verdict = guard.verify("FORM_A", guard.RealEvidence(eight_real_rows("FORM_A"), "REAL_ROWS"))
    try:
        guard.believe(
            working,
            coordinator=guard.coordinator_for_faculty("wondering"),
            key="k",
            value=1,
            verdict=verdict,
        )
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.FACULTY_RETURNED_BIAS_WRITE
    else:
        raise AssertionError("the belief door accepted a faculty coordinator")

    # And after all four faculties have run, the Bias has not moved at all.
    builder = world_builder_for(("DREAM_A",))
    faculties.wondering(working, buffer, [("W_A", "OMEGA_A")])
    faculties.pondering(working, buffer, unexplained_idle(), refit_for())
    faculties.imagination(working, buffer, builder)
    faculties.self_notice(lambda: faculties.wondering(working, buffer, ["W_C"]), depth=1, held=buffer)
    assert working.version == before_version == 0
    assert working.snapshot().digest == before_digest
    assert working.keys == ()


@case
def test_a_faculty_return_carrying_a_bias_write_is_refused():
    """The guard refuses a return value that carries a write, a verdict or an admission."""
    working, buffer = fresh()
    attempt = guard.BiasWriteAttempt("fact", 1, guard.coordinator_for_faculty("wondering"))
    try:
        guard.check_faculty_return("wondering", attempt)
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.FACULTY_RETURNED_BIAS_WRITE
    else:
        raise AssertionError("a Bias write travelled out of a faculty")
    # Nested inside a report, it is still caught.
    report = faculties.FacultyReport(faculty="wondering", tick=0, wrote=(), proposals=())
    shaped = dict(faculty="wondering", tick=0, wrote=(), proposals=(), reason=attempt)
    try:
        guard.check_faculty_return("wondering", (report, shaped))
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.FACULTY_RETURNED_BIAS_WRITE
    else:
        raise AssertionError("a Bias write hidden in a tuple travelled out")
    # Handing the Bias itself back is the same refusal.
    try:
        guard.check_faculty_return("wondering", working)
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.FACULTY_RETURNED_BIAS_WRITE
    else:
        raise AssertionError("a faculty handed the Bias back")
    # A verdict cannot leave a faculty either.
    verdict = guard.verify("FORM_A", guard.RealEvidence(eight_real_rows("FORM_A"), "REAL_ROWS"))
    try:
        guard.check_faculty_return("wondering", verdict)
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.FACULTY_RETURNED_A_VERDICT
    else:
        raise AssertionError("a verdict travelled out of a faculty")
    # And a candidate in ADMITTED state is refused.
    admitted_entry = buffer.put(held.Proposal("FORM_A", "wondering"))
    buffer.settle(admitted_entry.candidate_id, verdict)
    assert buffer.state_of(admitted_entry.candidate_id) == held.ADMITTED
    try:
        guard.check_faculty_return("wondering", buffer.get(admitted_entry.candidate_id))
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.FACULTY_RETURNED_ADMITTED_CANDIDATE
    else:
        raise AssertionError("an ADMITTED candidate travelled out of a faculty")


# --------------------------------------------------------------------------- #
# 5. Imagined evidence cannot reach the verifier at all
# --------------------------------------------------------------------------- #
@case
def test_imagined_evidence_cannot_be_passed_to_the_verifier_at_all():
    """The imagined type is a sibling, and `verify` refuses it before any checker runs."""
    assert guard.RealEvidence is not guard.ImaginedEvidence
    assert not issubclass(guard.ImaginedEvidence, guard.RealEvidence)
    assert not issubclass(guard.RealEvidence, guard.ImaginedEvidence)
    assert guard.evidence_kind(guard.ImaginedEvidence("W0", internal_rows("F"))) == guard.IMAGINED_EVIDENCE
    assert guard.evidence_kind(guard.RealEvidence(real_rows("F", 2), "REAL_ROWS")) == guard.REAL_EVIDENCE

    imagined = guard.ImaginedEvidence("W0", internal_rows("FORM_A", count=8))
    calls = []

    def checker(candidate, evidence):
        calls.append((candidate, type(evidence).__name__))
        return True, "SHOULD_NEVER_RUN", 99

    try:
        guard.verify("FORM_A", imagined, checker=checker)
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.IMAGINED_EVIDENCE_CANNOT_VERIFY
        assert "W0" in refusal.detail
    else:
        raise AssertionError("imagined evidence was verified")
    assert calls == [], "the checker ran on imagined evidence: %r" % (calls,)

    # The default checker is not reached either.
    try:
        guard.verify("FORM_A", imagined)
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.IMAGINED_EVIDENCE_CANNOT_VERIFY
    else:
        raise AssertionError("the default checker admitted imagined evidence")

    # An imagined world cannot carry a real row, so it cannot smuggle a witness in.
    try:
        guard.ImaginedEvidence("W0", (guard.Row("i1", guard.REAL, {"canonical_form": "F"}),))
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.IMAGINED_EVIDENCE_TAKES_INTERNAL_ROWS_ONLY
    else:
        raise AssertionError("an imagined world carried a REAL row")

    # It also has none of the reader the checker uses, so there is nothing to read even if
    # every type check were removed.
    assert not hasattr(guard.ImaginedEvidence, "canonical_forms")
    assert hasattr(guard.RealEvidence, "canonical_forms")

    # Real evidence refuses an INTERNAL row with the design's own code (Rule P).
    try:
        guard.RealEvidence(internal_rows("FORM_A"), "REAL_ROWS")
    except guard.GuardRefusal as refusal:
        assert refusal.code == "REFUSE:INTERNAL_WITNESS"
        assert "INTERNAL" in refusal.detail
    else:
        raise AssertionError("real evidence accepted an INTERNAL row")

    # And an imagined evidence object is not readable as a real one at all.
    try:
        guard.verify("FORM_A", (guard.Row("r1", guard.REAL, {"canonical_form": "FORM_A"}),))
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.EVIDENCE_IS_NOT_REAL_EVIDENCE
    else:
        raise AssertionError("bare rows were accepted as evidence")


@case
def test_the_imagined_type_has_no_conversion_to_the_real_type():
    """There is no method, flag or classmethod that turns imagined evidence into real."""
    for name in dir(guard.ImaginedEvidence):
        assert "real" not in name.lower(), "ImaginedEvidence offers %r" % name
        assert "verify" not in name.lower(), "ImaginedEvidence offers %r" % name
    for name in dir(guard.RealEvidence):
        assert "imagined" not in name.lower(), "RealEvidence offers %r" % name
    source = read_build_file("guard.py")
    assert "base class" in source.lower() or "sibling" in source.lower()
    # The base type has no verify and no conversion either.
    for name in ("verify", "as_real", "to_real", "rows_as_real"):
        assert not hasattr(guard.Evidence, name), "Evidence offers %r" % name
    # A RealEvidence cannot be built out of an ImaginedEvidence object.
    imagined = guard.ImaginedEvidence("W0", internal_rows("F"))
    try:
        guard.RealEvidence(imagined, "REAL_ROWS")
    except guard.GuardRefusal as refusal:
        assert refusal.code in (guard.EVIDENCE_IS_NOT_REAL_EVIDENCE, guard.REAL_EVIDENCE_NEEDS_ROWS)
    else:
        raise AssertionError("RealEvidence was built out of an ImaginedEvidence")


# --------------------------------------------------------------------------- #
# 6. Daydream, insight, and belief
# --------------------------------------------------------------------------- #
@case
def test_a_daydream_stays_a_daydream_until_real_evidence_verifies_it():
    """Imagination labels DAYDREAM; only a real verdict turns it into INSIGHT."""
    working, buffer = fresh()
    store = faculties.DaydreamStore()
    builder = world_builder_for(("DREAM_A",))
    report = faculties.imagination(working, buffer, builder, store=store)
    assert len(report.wrote) == 1
    candidate = report.wrote[0]
    assert buffer.state_of(candidate) == held.HELD
    assert buffer.label_of(candidate) == held.DAYDREAM
    assert store.daydream_count() == 1 and store.matched_count() == 0

    # Five attempts to verify it with the imagined world's own rows: nothing moves.
    world = store.worlds()[0]
    for _ in range(5):
        try:
            guard.verify("DREAM_A", world.evidence())
        except guard.GuardRefusal as refusal:
            assert refusal.code == guard.IMAGINED_EVIDENCE_CANNOT_VERIFY
        else:
            raise AssertionError("an imagined world verified a candidate")
    assert buffer.state_of(candidate) == held.HELD
    assert buffer.label_of(candidate) == held.DAYDREAM
    assert working.version == 0

    # Real rows arrive, and now the same candidate is admitted and becomes an insight.
    verdict = guard.verify("DREAM_A", guard.RealEvidence(eight_real_rows("DREAM_A"), "REAL_ROWS"))
    assert guard.is_verdict(verdict) and verdict.word == held.ADMITTED
    buffer.settle(candidate, verdict)
    assert buffer.state_of(candidate) == held.ADMITTED
    assert buffer.label_of(candidate) == held.INSIGHT
    store.note_admission(world.world_id, candidate, buffer.tick)
    assert store.matched_count() == 1 and store.daydream_count() == 0
    # The label is the only thing that changed meaning: the candidate was HELD throughout
    # until a real verdict moved it, and the transition records the verifier.
    moves = buffer.history_of(candidate)
    assert [move.to_state for move in moves] == [held.HELD, held.ADMITTED]
    assert moves[-1].writer_kind == held.VERIFIER_WRITER
    assert moves[-1].code == "VERIFY_ADMITS_ON_REAL_ROWS"


@case
def test_a_daydream_that_is_never_verified_never_changes_what_the_brain_believes():
    """Twelve ticks of daydreams and imagined evidence move neither the buffer nor the Bias."""
    loop, working, buffer = make_loop(arm="GREEDY", seed=3)
    before_version = working.version
    before_digest = working.snapshot().digest
    builder = world_builder_for(("DREAM_A", "DREAM_B"))
    records = []
    for index in range(12):
        imagined = guard.ImaginedEvidence("W%d" % index, internal_rows(["DREAM_A", "DREAM_B"], count=3))
        records.append(loop.tick(new_input=(), evidence=imagined))
    daydreams = [record for record in records if record.wrote and record.faculty == "imagination"]
    assert daydreams, "no candidates were proposed at all, so this case would be vacuous"
    proposed = sum(len(record.wrote) for record in daydreams)
    assert proposed >= 1
    assert buffer.counts()[held.DAYDREAM] == proposed, (
        "every imagined candidate must still carry DAYDREAM: %r" % (buffer.counts(),)
    )
    assert buffer.counts()[held.ADMITTED] == 0
    assert buffer.counts()[held.INSIGHT] == 0
    assert working.version == before_version == 0
    assert working.snapshot().digest == before_digest
    refusals = {record.verify_refused for record in records if record.verify_refused}
    assert refusals == {guard.IMAGINED_EVIDENCE_CANNOT_VERIFY}
    for record in records:
        assert record.believed == ()
        assert record.verified == ()


@case
def test_an_admission_on_real_evidence_does_reach_the_bias():
    """The positive control: without this, the negative cases above would prove nothing."""
    working, buffer = fresh()
    builder = world_builder_for(("DREAM_A",))
    faculties.imagination(working, buffer, builder)
    candidate = buffer.entries()[0].candidate_id
    verdict = guard.verify("DREAM_A", guard.RealEvidence(eight_real_rows("DREAM_A"), "REAL_ROWS"))
    buffer.settle(candidate, verdict)
    version = guard.believe(
        working,
        coordinator=COORDINATOR,
        key="candidate:%s" % candidate,
        value={"canonical_form": "DREAM_A", "candidate_id": candidate, "insight": True},
        verdict=verdict,
    )
    assert version == 1 and working.version == 1
    fact = working.read("candidate:%s" % candidate)
    assert fact["canonical_form"] == "DREAM_A" and fact["insight"] is True


@case
def test_a_refused_candidate_cannot_be_believed():
    """A refusal is a verdict, and it reaches nothing."""
    working, buffer = fresh()
    entry = buffer.put(held.Proposal("FORM_A", "wondering"))
    thin = guard.RealEvidence(real_rows("FORM_A", count=2), "REAL_ROWS")
    verdict = guard.verify("FORM_A", thin)
    assert verdict.word == held.REFUSED
    assert verdict.code == "NOT_ENOUGH_REAL_ROWS"
    buffer.settle(entry.candidate_id, verdict)
    assert buffer.state_of(entry.candidate_id) == held.REFUSED
    try:
        guard.believe(
            working,
            coordinator=COORDINATOR,
            key="k",
            value=1,
            verdict=verdict,
        )
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.BELIEF_NEEDS_AN_ADMITTED_VERDICT
    else:
        raise AssertionError("a refused candidate was believed")
    assert working.version == 0
    # No verdict at all reaches nothing either.
    try:
        guard.believe(working, coordinator=COORDINATOR, key="k", value=1, verdict=None)
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.BELIEVE_CALLED_WITHOUT_A_VERDICT
    else:
        raise AssertionError("a belief was written with no verdict")


@case
def test_the_support_mark_decides_an_admission_and_a_thin_witness_set_refuses():
    """8 real rows admits, 7 refuses: the mark is a number, not a mood."""
    eight = guard.verify("FORM_A", guard.RealEvidence(real_rows("FORM_A", count=8), "REAL_ROWS"))
    seven = guard.verify("FORM_A", guard.RealEvidence(real_rows("FORM_A", count=7), "REAL_ROWS"))
    assert eight.word == held.ADMITTED and eight.support == 8
    assert seven.word == held.REFUSED and seven.support == 7
    assert guard.MIN_SUPPORT_ROWS == 8
    assert eight.evidence_kind == guard.REAL_EVIDENCE


# --------------------------------------------------------------------------- #
# 7. The test for the guardrail can fail
# --------------------------------------------------------------------------- #
@case
def test_the_guardrail_test_can_fail():
    """A copy of `guard.py` that lets imagined data verify is caught by the same check.

    The law the whole build rests on is that imagined data cannot reach a verification call.
    A test for that law is worth nothing unless it can fail, so this case builds a copy of
    `guard.py` in memory with the two type checks broken, confirms the broken copy really does
    admit imagined evidence, and confirms the check used above reports it as broken.
    """
    source = read_build_file("guard.py")
    injected = source.replace(
        "    if isinstance(evidence, ImaginedEvidence):",
        "    if False and isinstance(evidence, ImaginedEvidence):  # INJECTED BY THE TEST",
    ).replace(
        "    if not isinstance(evidence, RealEvidence):",
        "    if not isinstance(evidence, (RealEvidence, ImaginedEvidence)):  # INJECTED BY THE TEST",
    )
    assert injected.count("INJECTED BY THE TEST") == 2, "the injection did not take effect"

    broken = types.ModuleType("guard_broken")
    # The module is registered before it is executed because `dataclasses` looks a class's
    # module up in `sys.modules` while building it.
    sys.modules["guard_broken"] = broken
    exec(compile(injected, "guard_broken.py", "exec"), broken.__dict__)

    def the_check(module):
        """The core assertion of the imagined-evidence case, run against one guard module."""
        row = module.Row("i1", module.INTERNAL, {"canonical_form": "FORM_A"})
        imagined = module.ImaginedEvidence("W0", (row,))
        try:
            module.verify("FORM_A", imagined)
        except module.GuardRefusal as refusal:
            return refusal.code == "IMAGINED_EVIDENCE_CANNOT_VERIFY"
        except Exception:  # noqa: BLE001 - a guard that crashes has not held the line either
            return False
        return False

    assert the_check(guard) is True, "the real guard failed its own check"
    assert the_check(broken) is False, "the broken copy passed the check, so the check proves nothing"

    # And the broken copy is broken exactly where claimed: the imagined object reaches the
    # checker, which is the event the type wall exists to make impossible.
    seen = []

    def spy(candidate, evidence):
        seen.append(type(evidence).__name__)
        return True, "INJECTED_CHECKER_ADMITS_ANYTHING", 1

    broken_row = broken.Row("i1", broken.INTERNAL, {"canonical_form": "FORM_A"})
    verdict = broken.verify("FORM_A", broken.ImaginedEvidence("W0", (broken_row,)), checker=spy)
    assert seen == ["ImaginedEvidence"], "the injected guard did not hand imagined data over"
    assert verdict.word == "ADMITTED", "the injected copy did not admit imagined data"
    # The real guard never lets that happen, which is the whole build.
    try:
        guard.verify(
            "FORM_A",
            guard.ImaginedEvidence("W0", internal_rows("FORM_A")),
            checker=spy,
        )
    except guard.GuardRefusal as refusal:
        assert refusal.code == guard.IMAGINED_EVIDENCE_CANNOT_VERIFY
    else:
        raise AssertionError("the real guard handed imagined data to a checker")
    assert seen == ["ImaginedEvidence"], "the real guard called the checker after all"


# --------------------------------------------------------------------------- #
# 8. Pondering runs only when idle
# --------------------------------------------------------------------------- #
@case
def test_pondering_refuses_a_tick_with_input_queued():
    """The faculty itself refuses a busy tick."""
    working, buffer = fresh()
    busy = faculties.Unexplained(rows=(guard.Row("u1", guard.REAL, {"cell": "c1"}),), idle=False)
    try:
        faculties.pondering(working, buffer, busy, refit_for())
    except faculties.FacultiesRefusal as refusal:
        assert refusal.code == faculties.PONDERING_RUNS_ONLY_WHEN_IDLE
    else:
        raise AssertionError("pondering ran on a busy tick")
    assert len(buffer) == 0
    idle = faculties.Unexplained(rows=(guard.Row("u1", guard.REAL, {"cell": "c1"}),), idle=True)
    report = faculties.pondering(working, buffer, idle, refit_for())
    assert report.wrote and report.reason == "REFIT"


@case
def test_the_drive_loop_never_runs_pondering_on_a_tick_with_input():
    """In the loop, a tick with queued input masks F7, so pondering cannot be reached."""
    loop, working, buffer = make_loop(arm="GREEDY", seed=0)
    records = drive(loop, ticks=24, input_every=3)
    pondering = [record for record in records if record.faculty == "pondering"]
    assert pondering, "pondering never ran, so this case would be vacuous"
    for record in pondering:
        assert record.idle is True, "pondering ran on tick %d with input queued" % record.tick
        assert record.focus == "F7"
        # No fitter in this build, so F7's measured gain is 0 and the tick says why.
        assert ("F7", 0) in record.gains
        assert drive_loop.GAIN_NOT_MEASURABLE in record.note
    busy = [record for record in records if not record.idle]
    assert busy, "no busy tick was produced, so this case would be vacuous"
    for record in busy:
        reasons = dict((item[0].split(":", 1)[1], item[1]) for item in record.masked)
        assert "F7" in reasons
        assert reasons["F7"] == drive_loop.MASKED_NOT_IDLE
        assert record.faculty != "pondering"


@case
def test_pondering_breaks_down_real_rows_only():
    """An INTERNAL row is not unexplained real data."""
    working, buffer = fresh()
    try:
        with_internal = faculties.Unexplained(rows=internal_rows("F"), idle=True)
        faculties.pondering(working, buffer, with_internal, refit_for())
    except faculties.FacultiesRefusal as refusal:
        assert refusal.code == "REFUSE:INTERNAL_WITNESS"
    else:
        raise AssertionError("pondering broke down an imagined row")
    # The grouping is deterministic: two rows in the same cell make one refit call.
    calls = []

    def refit(group, reading):
        calls.append(tuple(row.row_id for row in group))
        return [("REFIT_%d" % len(calls), "OMEGA_A")]

    rows = (
        guard.Row("b2", guard.REAL, {"cell": "c2"}),
        guard.Row("a1", guard.REAL, {"cell": "c1"}),
        guard.Row("a2", guard.REAL, {"cell": "c1"}),
    )
    report = faculties.pondering(working, buffer, faculties.Unexplained(rows=rows, idle=True), refit)
    assert calls == [("a1", "a2"), ("b2",)], calls
    assert len(report.wrote) == 2


# --------------------------------------------------------------------------- #
# 8. Self-notice: one receipt per level
# --------------------------------------------------------------------------- #
@case
def test_self_notice_records_one_receipt_per_nesting_level():
    """Three nested levels give three receipts, and the labels spell the design's own word."""
    working, buffer = fresh()

    def running_wondering():
        return faculties.wondering(working, buffer, [("W_A", "OMEGA_A")])

    def wondering_level():
        return faculties.self_notice(running_wondering, depth=1, held=buffer, as_faculty="wondering")

    def pondering_level():
        return faculties.self_notice(wondering_level, depth=2, held=buffer, as_faculty="pondering")

    report = faculties.self_notice(pondering_level, depth=3, held=buffer, as_faculty="imagination")
    assert [level.level for level in report.levels] == [1, 2, 3]
    assert [level.faculty for level in report.levels] == ["wondering", "pondering", "imagination"]
    assert [level.phi for level in report.levels] == ["^8->^9", "^6", "^0"]
    assert all(level.epsilon_of_eta for level in report.levels)
    for level in report.levels:
        assert level.forms_written == level.forms_read_back == ("W_A",)
    assert len(report.wrote) == 1
    assert buffer.state_of(report.wrote[0]) == held.HELD


@case
def test_self_notice_depth_cap_holds_and_runs_nothing():
    """A sixth level is refused before the inner faculty runs."""
    working, buffer = fresh()

    def running_wondering():
        return faculties.wondering(working, buffer, ["W_A"])

    try:
        faculties.self_notice(running_wondering, depth=faculties.MAX_NESTING_DEPTH + 1, held=buffer)
    except faculties.FacultiesRefusal as refusal:
        assert refusal.code == faculties.NESTING_DEPTH_CAP
        assert "nothing was written" in refusal.detail
    else:
        raise AssertionError("a sixth nesting level was allowed")
    assert len(buffer) == 0


@case
def test_self_notice_reports_a_depth_it_did_not_record():
    """A call that claims a depth the run does not have is refused."""
    working, buffer = fresh()

    def running_wondering():
        return faculties.wondering(working, buffer, ["W_A"])

    try:
        faculties.self_notice(running_wondering, depth=2, held=buffer)
    except faculties.FacultiesRefusal as refusal:
        assert refusal.code == faculties.NESTING_DEPTH_NOT_RECORDED
    else:
        raise AssertionError("a depth of 2 was accepted for a one-level run")


@case
def test_a_failed_level_invalidates_every_parent():
    """A receipt that does not read back stops the chain: CHAIN_INVALIDATED."""
    working, buffer = fresh()

    def lying_faculty():
        # Says it wrote a candidate it never wrote. The read-back is what catches it.
        return faculties.FacultyReport(
            faculty="wondering",
            tick=buffer.tick,
            wrote=("C999",),
            proposals=(),
        )

    try:
        faculties.self_notice(lying_faculty, depth=1, held=buffer, as_faculty="wondering")
    except faculties.FacultiesRefusal as refusal:
        assert refusal.code == faculties.CHAIN_INVALIDATED
        assert "read-back failed" in refusal.detail
    else:
        raise AssertionError("a level whose receipt failed was recorded")
    # An honest level with an unmatched write count is caught the other way round: the same
    # read-back, so a level that writes nothing and claims a form fails too.
    def partial():
        return faculties.FacultyReport(
            faculty="wondering", tick=buffer.tick, wrote=(), proposals=(held.Proposal("X", "wondering"),)
        )

    try:
        faculties.self_notice(partial, depth=1, held=buffer, as_faculty="wondering")
    except faculties.FacultiesRefusal as refusal:
        assert refusal.code == faculties.CHAIN_INVALIDATED
    else:
        raise AssertionError("a level that wrote nothing but claimed a form was recorded")


# --------------------------------------------------------------------------- #
# 9. The buffer never loses anything
# --------------------------------------------------------------------------- #
@case
def test_the_held_buffer_never_loses_a_refused_or_expired_candidate():
    """Refused, admitted and expired candidates all stay, with their whole history."""
    working, buffer = fresh()
    expire_me = buffer.put(held.Proposal("EXPIRE_ME", "wondering"))
    buffer.begin_tick(6)
    keep = buffer.put(held.Proposal("KEEP", "wondering"))
    refuse_me = buffer.put(held.Proposal("REFUSE_ME", "wondering"))
    admit_me = buffer.put(held.Proposal("ADMIT_ME", "wondering"))

    buffer.settle(refuse_me.candidate_id, guard.verify("REFUSE_ME", guard.RealEvidence(real_rows("REFUSE_ME", 2), "REAL_ROWS")))
    buffer.settle(admit_me.candidate_id, guard.verify("ADMIT_ME", guard.RealEvidence(eight_real_rows("ADMIT_ME"), "REAL_ROWS")))
    expired = buffer.expire(age_cap=5)
    assert expired == (expire_me.candidate_id,)

    assert len(buffer) == 4
    ids = [entry.candidate_id for entry in buffer.entries()]
    assert ids == [expire_me.candidate_id, keep.candidate_id, refuse_me.candidate_id, admit_me.candidate_id]
    assert buffer.state_of(refuse_me.candidate_id) == held.REFUSED
    assert buffer.state_of(expire_me.candidate_id) == held.EXPIRED
    assert buffer.state_of(admit_me.candidate_id) == held.ADMITTED
    assert buffer.state_of(keep.candidate_id) == held.HELD
    counts = buffer.counts()
    assert counts[held.HELD] == 1 and counts[held.REFUSED] == 1
    assert counts[held.EXPIRED] == 1 and counts[held.ADMITTED] == 1 and counts["total"] == 4
    # The expired candidate's record carries the reason and the actor.
    last = buffer.history_of(expire_me.candidate_id)[-1]
    assert last.to_state == held.EXPIRED
    assert last.writer_kind == held.CONSOLIDATOR_WRITER
    assert last.why == held.WHY_AGE_CAP


@case
def test_every_state_transition_records_who_moved_it_and_why():
    """Every move names a writer kind, a writer, its phi, a reason and a code."""
    working, buffer = fresh()
    faculties.wondering(working, buffer, [("W_A", "OMEGA_A")])
    first = buffer.entries()[0].candidate_id
    buffer.settle(first, guard.verify("W_A", guard.RealEvidence(eight_real_rows("W_A"), "REAL_ROWS")))
    second = buffer.put(held.Proposal("W_B", "pondering", phi="^6"))
    buffer.begin_tick(4)
    buffer.expire(age_cap=4)
    assert buffer.state_of(second.candidate_id) == held.EXPIRED
    seen = {"FACULTY": 0, "VERIFIER": 0, "CONSOLIDATOR": 0}
    for move in buffer.transitions():
        assert move.writer_kind in held.WRITER_KINDS
        assert isinstance(move.moved_by, str) and move.moved_by.strip()
        assert isinstance(move.why, str) and move.why.strip()
        assert move.to_state in held.STATE_WORDS
        seen[move.writer_kind] += 1
        if move.writer_kind == held.FACULTY_WRITER:
            # The writer record shape taken from provenance.py: kind + phi.
            assert isinstance(move.phi, str) and move.phi.strip()
        if move.writer_kind == held.VERIFIER_WRITER:
            assert move.code, "a verdict move must carry its code"
    assert all(count > 0 for count in seen.values()), seen
    # A settled candidate does not accept a second verdict.
    later = guard.verify("W_A", guard.RealEvidence(eight_real_rows("W_A"), "REAL_ROWS"))
    try:
        buffer.settle(first, later)
    except held.HeldRefusal as refusal:
        assert refusal.code == held.HELD_ALREADY_SETTLED
    else:
        raise AssertionError("a settled candidate accepted a second verdict")


@case
def test_expiry_refuses_with_no_cap_named():
    """The design names an age cap and gives no number; this build will not invent one."""
    working, buffer = fresh()
    buffer.put(held.Proposal("W_A", "wondering"))
    try:
        buffer.expire()
    except held.HeldRefusal as refusal:
        assert refusal.code == held.HELD_CAP_NOT_NAMED
    else:
        raise AssertionError("expiry picked a cap of its own")


# --------------------------------------------------------------------------- #
# 10. The drive loop: determinism and records
# --------------------------------------------------------------------------- #
def run_pair(arm, seed, ticks=18, input_every=3):
    first, working_a, buffer_a = make_loop(arm=arm, seed=seed)
    second, working_b, buffer_b = make_loop(arm=arm, seed=seed)
    records_a = drive(first, ticks=ticks, input_every=input_every)
    records_b = drive(second, ticks=ticks, input_every=input_every)
    return (first, working_a, buffer_a, records_a), (second, working_b, buffer_b, records_b)


@case
def test_the_drive_loop_is_deterministic_for_the_same_inputs():
    """Same arms, same seed, same inputs: identical records, buffer and Bias."""
    for arm in drive_loop.ARMS:
        a, b = run_pair(arm, seed=11)
        loop_a, working_a, buffer_a, records_a = a
        loop_b, working_b, buffer_b, records_b = b
        assert loop_a.digest() == loop_b.digest(), "%s digests differ" % arm
        assert [record.focus for record in records_a] == [record.focus for record in records_b]
        assert [record.idle for record in records_a] == [record.idle for record in records_b]
        assert buffer_a.digest() == buffer_b.digest(), "%s buffer digests differ" % arm
        assert working_a.snapshot().digest == working_b.snapshot().digest
        assert loop_a.satisfactions() == loop_b.satisfactions()
    # Not deterministic by accident: a different seed reorders the seeded arm.
    loose, _, _, records_one = run_pair("PULL_SAMPLING", seed=1)[0]
    other, _, _, records_two = run_pair("PULL_SAMPLING", seed=2)[0]
    assert loose.digest() != other.digest(), "the seeded arm ignored its seed"
    assert [record.focus for record in records_one] != [record.focus for record in records_two]


@case
def test_the_drive_loop_records_every_tick():
    """Every tick is recorded, masked or not, with what it did and what it refused."""
    loop, working, buffer = make_loop(arm="GREEDY", seed=5)
    records = drive(loop, ticks=20, input_every=4)
    assert len(records) == 20 == loop.tick_count
    assert [record.tick for record in records] == list(range(20))
    assert len(loop.history) == 20
    # Every record names the masks it applied, using the design's event word.
    for record in records:
        words = [item[0] for item in record.masked]
        for word in words:
            assert word.startswith("DRIVE_DEPRIORITIZED:")
        assert ("DRIVE_DEPRIORITIZED:F1", "NO_FACULTY_IN_THIS_BUILD") in record.masked
        assert record.arm == "GREEDY"
        assert record.pulls and record.satisfactions
    acted = [record for record in records if record.acted]
    assert acted, "no drive ever acted"
    assert {record.faculty for record in acted} == {"imagination", "pondering"}
    # Satisfactions stay on the open interval, as the design's clamps require.
    for drive_name, value in loop.satisfactions():
        assert drive_loop.S_LO <= value <= drive_loop.S_HI, (drive_name, value)


@case
def test_the_drive_loop_cannot_believe_anything_on_imagined_evidence():
    """The loop's verify step refuses imagined evidence and writes nothing."""
    loop, working, buffer = make_loop(arm="GREEDY", seed=2)
    drive(loop, ticks=3, input_every=0)
    assert buffer.counts()[held.DAYDREAM] >= 1
    imagined = guard.ImaginedEvidence("W9", internal_rows("DREAM_A", count=4))
    record = loop.tick(evidence=imagined)
    assert record.verify_refused == guard.IMAGINED_EVIDENCE_CANNOT_VERIFY
    assert record.verified == () and record.believed == ()
    assert working.version == 0
    assert buffer.counts()[held.ADMITTED] == 0


@case
def test_the_drive_loop_does_believe_on_real_evidence():
    """The positive control for the loop: real rows do move the Bias."""
    loop, working, buffer = make_loop(arm="GREEDY", seed=2)
    drive(loop, ticks=2, input_every=0)
    assert buffer.counts()[held.DAYDREAM] >= 1
    evidence = guard.RealEvidence(real_rows(["DREAM_A", "DREAM_B"], count=16), "REAL_ROWS")
    record = loop.tick(evidence=evidence)
    assert record.verify_refused is None
    assert record.verified, "real evidence verified nothing"
    assert record.believed, "an admission on real evidence wrote nothing to the Bias"
    assert working.version == len(record.believed)
    assert buffer.counts()[held.INSIGHT] >= 1
    for candidate_id, _version in record.believed:
        fact = working.read("candidate:%s" % candidate_id)
        assert fact["insight"] is True
        assert fact["canonical_form"] in ("DREAM_A", "DREAM_B")


@case
def test_a_drive_with_no_faculty_is_masked_not_given_invented_work():
    """With no imagination and no pondering wired, every drive is masked and nothing runs."""
    loop, working, buffer = make_loop(arm="GREEDY", seed=0, with_imagination=False, with_pondering=False)
    records = drive(loop, ticks=5, input_every=2)
    for record in records:
        assert record.focus is None and record.faculty is None
        assert record.note == drive_loop.NO_UNMASKED_DRIVE
        assert len(record.masked) == len(drive_loop.DRIVES)
    assert len(buffer) == 0 and working.version == 0


@case
def test_the_drive_loop_refuses_imagined_input_rows():
    """Rule P at the loop's own door: an INTERNAL row never arrives as input."""
    loop, working, buffer = make_loop()
    try:
        loop.tick(new_input=(guard.Row("i1", guard.INTERNAL, {}),))
    except drive_loop.DriveLoopRefusal as refusal:
        assert refusal.code == drive_loop.LOOP_INPUT_NOT_REAL
    else:
        raise AssertionError("an imagined row arrived as input")


# --------------------------------------------------------------------------- #
# 11. The README: ceiling, faculties, and the undecided list
# --------------------------------------------------------------------------- #
@case
def test_the_readme_states_the_claim_ceiling_exactly():
    readme = read_build_file("README.md")
    assert CLAIM_CEILING in readme
    assert readme.count(CLAIM_CEILING) >= 2, "the ceiling is stated once and repeated at the end"
    assert "guardrail" in readme.lower() or "imagined" in readme.lower()


@case
def test_the_readme_gives_one_line_per_faculty_and_no_fifth():
    readme = read_build_file("README.md")
    for name in faculties.FACULTIES:
        assert re.search(r"^\|\s*`?%s`?\s*\|" % name, readme, re.M), "README has no row for %s" % name
    assert "contemplat" not in readme.lower().replace("contemplation is not a faculty", "")
    assert "Contemplation is not a faculty" in readme


@case
def test_the_readme_lists_every_undecided_line_and_the_lists_do_not_drift():
    """Every marker in the code must appear in README word for word, and nothing else may."""
    readme = read_build_file("README.md")
    in_code = undecided_lines("UNDECIDED IN DESIGN", OWN_MODULES)
    assert in_code, "no UNDECIDED IN DESIGN marker was found, so this case would be vacuous"
    in_readme = []
    for line in readme.splitlines():
        match = re.match(r"^-\s*UNDECIDED IN DESIGN:\s*(.+?)\s*$", line)
        if match:
            in_readme.append(match.group(1).strip())
    assert len(in_readme) == len(set(in_readme)), "the README lists a line twice"
    code_questions = [question for _name, question in in_code]
    assert len(code_questions) == len(set(code_questions)), "a marker is duplicated in the code"
    missing = [question for question in code_questions if question not in in_readme]
    extra = [question for question in in_readme if question not in code_questions]
    assert not missing, "the README is missing %d undecided line(s); first: %s" % (
        len(missing),
        missing[0][:120],
    )
    assert not extra, "the README lists %d undecided line(s) that are not in the code; first: %s" % (
        len(extra),
        extra[0][:120],
    )
    assert len(in_readme) == len(code_questions)


@case
def test_the_readme_names_what_the_build_does_not_contain():
    readme = read_build_file("README.md")
    for phrase in (
        "MECHANISM ONLY.",
        "NO FACULTY HAS RUN INSIDE HELM.",
        "IMAGINED_EVIDENCE_CANNOT_VERIFY",
        "held buffer",
        "UNDECIDED IN DESIGN",
    ):
        assert phrase in readme, "README does not mention %r" % phrase


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
    print("faculties / test_all.py")
    print("python: %s  platform: %s" % (platform.python_version(), platform.system()))
    print("build folder: %s" % (BUILD_DIR,))
    for name in COPIED_MODULES:
        with open(os.path.join(BUILD_DIR, name), "rb") as handle:
            print("%s sha256: %s" % (name, hashlib.sha256(handle.read()).hexdigest()))
    print("claim ceiling: %s" % (CLAIM_CEILING,))
    print("faculties: %s" % (", ".join(faculties.FACULTIES),))
    print("undecided markers in the code: %d" % (len(undecided_lines("UNDECIDED IN DESIGN", OWN_MODULES)),))
    print("-" * 78)
    passed = 0
    failed = 0
    for function in CASES:
        name = function.__name__
        try:
            function()
        except Exception as exc:  # noqa: BLE001 - a test runner must catch everything
            failed += 1
            print("FAIL %s: %s: %s" % (name, type(exc).__name__, ascii_safe(exc)))
        else:
            passed += 1
            print("PASS %s" % (name,))
    print("-" * 78)
    total = passed + failed
    print("TOTAL %d cases: %d passed, %d failed" % (total, passed, failed))
    print("RESULT: %s" % ("ALL PASS" if failed == 0 else "FAILURES PRESENT",))
    print("claim ceiling, repeated: %s" % (CLAIM_CEILING,))
    return 0 if failed == 0 else 1


def ascii_safe(text) -> str:
    return str(text).encode("ascii", "backslashreplace").decode("ascii")


if __name__ == "__main__":
    sys.exit(main())
