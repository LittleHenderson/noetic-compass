"""test_all.py -- one runnable test file for the return-address build. No pytest needed.

WHAT THIS FILE DOES
-------------------
It proves every rule the owning instruction names, with explicit cases and explicit numbers,
and prints one PASS or FAIL line per case plus a total. Run it with:

    python -B test_all.py

The rules under test, and the case that carries each one:

  * an address with a missing field is refused                        -- every_field_of_an_address_is_required
  * a partial match is refused as INEXACT_ADDRESS                     -- a_partial_match_is_refused_as_inexact
  * resume with an equal Bias version is refused                      -- resume_with_an_equal_bias_version_is_refused
  * resume with an older Bias version is refused                      -- resume_with_an_older_bias_version_is_refused
  * a duplicate finish is refused                                     -- a_duplicate_finish_is_refused
  * a cancelled thread cannot be resumed                              -- a_cancelled_thread_cannot_be_resumed
  * a mismatched call id is refused                                   -- a_mismatched_call_id_is_refused
  * returning to the root directly is refused, the immediate
    caller is returned instead                                        -- returning_to_the_root_is_refused...
  * the caller's remaining work is surfaced before the further return -- the_callers_remaining_work...
  * a dirty child invalidates every ancestor, all the way to the root -- a_dirty_child_invalidates_every_ancestor...
  * a clean sibling is unaffected                                     -- a_clean_sibling_is_unaffected...
  * the root observation reference is distinguishable from any
    return path                                                       -- an_observation_reference_is_not_a_return_path

It also covers the three addendum cases that exist beside the brief, because the owner's
ruling asks for them: two nested levels returning to the exact waiting occurrences in
dependency order with their own saved stages (addendum line 40, AT15/AT20); two callers with
identical fields receiving only their own results (line 41, AT15/AT25/AT26); and stale,
cancelled and duplicate completions not resuming an unrelated caller (line 42, AT16/AT17/AT19).

WHAT THIS FILE DOES NOT DO
--------------------------
  * It does NOT prove that anything recursed, suspended, finished, glued or learned. NO
    CIRCUIT USES THIS: every "call" here is a record this build made, and every "child" is a
    value the test wrote. The claim ceiling is on every line of this build for that reason.
  * It does NOT prove that a return improves anything. There is no engine, no model, no
    training and no measurement of accuracy anywhere in this folder.
  * It does NOT decide glue-back. The two cases about gluing substitute the real model's own
    functions and check that this build's answer follows them; the verdict is the atlas
    model's, and the test says so where it matters.
  * It does NOT use pytest, numpy, torch, any network or any cloud service. Standard library
    plus the real atlas model's own dependencies, and it runs in well under a second.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NO CIRCUIT USES THIS YET.
"""

from __future__ import annotations

import os
import re
import sys
import traceback
from hashlib import sha256
from pathlib import Path

BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

import address
import atlas_binding
import dirty
import stack
from address import ObservationReference, ReturnAddress, ReturnRefusal
from real_atlas.model import ContractError
from real_atlas.rpa_model import (
    AtlasContext,
    AtlasNode,
    AtlasSnapshot,
    CompatibilityReport,
    NodeKind,
    NodeStatus,
)

CLAIM_CEILING = "MECHANISM ONLY. NO CIRCUIT USES THIS YET."

#: The cases, in the order they run.
CASES = []


def case(function):
    """Register one test case."""
    CASES.append(function)
    return function


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
MODULE_FILES = ("address.py", "stack.py", "dirty.py", "atlas_binding.py")


def read(name: str) -> str:
    with open(os.path.join(BUILD_DIR, name), encoding="utf-8") as handle:
        return handle.read()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def refused(code, call, label=""):
    """Call something that must be refused with exactly this code, and answer the refusal."""
    try:
        call()
    except ReturnRefusal as refusal:
        assert refusal.code == code, (
            f"{label}: expected refusal {code}, got {refusal.code}: {refusal}"
        )
        return refusal
    except Exception as error:  # noqa: BLE001 - a wrong exception type is a test failure
        raise AssertionError(
            f"{label}: expected refusal {code}, got {type(error).__name__}: {error}"
        ) from error
    raise AssertionError(f"{label}: expected refusal {code}, but nothing was raised")


# --------------------------------------------------------------------------- #
# The real atlas: three things only -- a real snapshot digest, real nodes to glue, and a
# real saved snapshot to bind an address against. No atlas is built here.
# --------------------------------------------------------------------------- #
REAL_CONTEXT = AtlasContext(
    context_id="ctx-return",
    model_version="cas-rpa/0.1",
    observation_id="obs-return-1",
    observation_time="2026-10-24T00:00:00Z",
    record_version=1,
)


def real_node(node_id, *, kind=NodeKind.IDEA_CONTEXT, status=NodeStatus.OBSERVED,
              members=None, fields=(("board_1", "copied into memory"),), idea_id="idea-main"):
    """One real ``AtlasNode``. Fields and members are chosen sorted, as the real model asks."""
    return AtlasNode(
        node_id=node_id,
        idea_id=idea_id,
        label=node_id,
        context=REAL_CONTEXT,
        status=status,
        kind=kind,
        members=members,
        fields=fields,
    )


def circuit_snapshot(*, focus="S0-possibilities"):
    """The test circuit as a REAL ``AtlasSnapshot``: two nodes, no links, one present state."""
    state = real_node(
        "state-now",
        kind=NodeKind.STATE,
        status=NodeStatus.OBSERVED,
        fields=(("board_1", "copied into memory"), ("board_2", "not copied")),
    )
    root = real_node(
        "S0-possibilities",
        kind=NodeKind.REGION,
        status=NodeStatus.HYPOTHETICAL,
        members=("route-alt", "route-single"),
    )
    return AtlasSnapshot(
        nodes=(state, root), links=(), current_state_id="state-now", focus_node_id=focus
    )


SNAPSHOT = circuit_snapshot()
SNAPSHOT_DIGEST = SNAPSHOT.snapshot_digest
#: A second saved snapshot with a different digest, so "which snapshot" is a real question.
OTHER_SNAPSHOT = circuit_snapshot(focus="state-now")
OTHER_DIGEST = OTHER_SNAPSHOT.snapshot_digest

EPISODE = "ep-root-goal"
BRANCH = "branch-main"


def addr(call_id, parent=None, *, episode=EPISODE, branch=BRANCH, snapshot=SNAPSHOT_DIGEST,
         bias=1):
    """One return address, with every field stated."""
    return ReturnAddress(
        episode=episode,
        branch=branch,
        snapshot_digest=snapshot,
        bias_version=bias,
        call_id=call_id,
        parent_call_id=parent,
    )


def suspend_on(st, one_address, *, payload="the caller's saved continuation", work=()):
    """Suspend with the Bias version the address names, which is the only legal one."""
    return st.suspend(one_address, one_address.bias_version, payload, remaining_work=work)


def build_chain(st, *, root_work=(), mid_work=(), leaf_work=()):
    """A three-level chain on the stack: c0 (root) -> c1 -> c2, each waiting on a child."""
    root = addr("c0", bias=1)
    mid = address.child_of(root, "c1")
    leaf = address.child_of(mid, "c2")
    suspend_on(st, root, work=root_work)
    suspend_on(st, mid, work=mid_work)
    suspend_on(st, leaf, work=leaf_work)
    return root, mid, leaf


def glue_pair(*, conflicting=False):
    """Two REAL nodes that share a member, so the real model can certify them.

    With ``conflicting=True`` they share a field key with different values, so the real
    ``compatibility()`` reports a conflict and its own verdict is a clean ``False``.
    """
    child = real_node(
        "region-child", kind=NodeKind.REGION, members=("w1", "w2"),
        fields=(("key", "same"),),
    )
    parent = real_node(
        "region-parent", kind=NodeKind.REGION, members=("w1", "w3"),
        fields=(("key", "different" if conflicting else "same"),),
    )
    return (child, parent)


# --------------------------------------------------------------------------- #
# 1. The address: every field required, typed, and compared
# --------------------------------------------------------------------------- #
@case
def every_field_of_an_address_is_required():
    good = {
        "episode": EPISODE,
        "branch": BRANCH,
        "snapshot_digest": SNAPSHOT_DIGEST,
        "bias_version": 1,
        "call_id": "c-1",
        "parent_call_id": None,
    }
    for name in ReturnAddress.FIELDS:
        partial = {key: value for key, value in good.items() if key != name}
        refusal = refused(
            address.MISSING_FIELD,
            lambda p=partial: ReturnAddress(**p),
            f"missing {name}",
        )
        assert name in refusal.detail, f"the refusal does not name {name}: {refusal.detail}"

    built = ReturnAddress(**good)
    assert built.is_root is True and built.is_return_path is True
    assert built.parent_call_id is None

    refused(address.BAD_FIELD_TYPE,
            lambda: ReturnAddress(**{**good, "episode": 7}), "episode as an int")
    refused(address.EMPTY_FIELD,
            lambda: ReturnAddress(**{**good, "branch": "   "}), "a blank branch")
    refused(address.BAD_BIAS_VERSION,
            lambda: ReturnAddress(**{**good, "bias_version": -1}), "a negative Bias version")
    refused(address.BAD_BIAS_VERSION,
            lambda: ReturnAddress(**{**good, "bias_version": True}), "True as a Bias version")
    refused(address.BAD_SNAPSHOT_DIGEST,
            lambda: ReturnAddress(**{**good, "snapshot_digest": "not-a-digest"}),
            "a snapshot digest that is not a sha256")
    refused(address.BAD_FIELD_TYPE,
            lambda: ReturnAddress(**{**good, "parent_call_id": 12}),
            "a numeric parent id")
    print("      6 required fields, each refused when missing; 6 type refusals")


@case
def a_partial_match_is_refused_as_inexact():
    base = addr("c-1")
    assert base.is_exact(addr("c-1")) is True

    changes = (
        ("episode", addr("c-1", episode="ep-other")),
        ("branch", addr("c-1", branch="branch-other")),
        ("snapshot_digest", addr("c-1", snapshot=OTHER_DIGEST)),
        ("bias_version", addr("c-1", bias=2)),
        ("call_id", addr("c-2")),
        ("parent_call_id", addr("c-1", parent="c-0")),
    )
    for name, changed in changes:
        differing = base.differing_fields(changed)
        assert differing == (name,), f"{name}: differing fields read {differing}"
        assert base.is_exact(changed) is False, f"{name}: a partial match counted as a match"
        refusal = refused(
            address.INEXACT_ADDRESS, lambda c=changed: base.require_exact(c), f"one {name} differs"
        )
        assert name in refusal.detail, f"{name}: the refusal does not name it: {refusal.detail}"

    assert base.require_exact(addr("c-1")) is True
    report = address.exactness_report(base, addr("c-1", branch="branch-other"))
    assert report["exact"] is False and report["differing_fields"] == ("branch",)
    print(f"      6 single-field differences, each INEXACT_ADDRESS; exact twin accepted")


@case
def an_address_is_immutable_and_hashable():
    one = addr("c-1")
    try:
        one.call_id = "c-2"
    except AttributeError as error:
        assert "immutable" in str(error), error
    else:
        raise AssertionError("an address was re-pointed after it was built")
    assert one.call_id == "c-1"
    assert hash(one) == hash(addr("c-1"))
    assert len({addr("c-1"), addr("c-1"), addr("c-2")}) == 2


@case
def the_child_address_names_its_own_occurrence():
    parent = addr("c-root", bias=4)
    child = address.child_of(parent, "c-root-1")
    assert child.call_id == "c-root-1" and child.parent_call_id == "c-root"
    assert child.episode == parent.episode
    assert child.branch == parent.branch
    assert child.snapshot_digest == parent.snapshot_digest
    assert child.bias_version == parent.bias_version
    assert child.is_root is False and child.is_return_path is True
    assert child.is_exact(parent) is False

    other = address.child_of(parent, "c-root-2", branch="branch-alt",
                             snapshot_digest=OTHER_DIGEST, bias_version=5)
    assert other.branch == "branch-alt"
    assert other.snapshot_digest == OTHER_DIGEST
    assert other.bias_version == 5
    assert other.parent_call_id == "c-root"

    refused(address.DUPLICATE_CALL_ID,
            lambda: address.child_of(parent, "c-root"),
            "a child given its parent's occurrence id")
    refused(address.BAD_PARENT,
            lambda: address.child_of("not-an-address", "c-x"), "a parent that is not an address")
    refused(address.EMPTY_FIELD,
            lambda: address.child_of(parent, "  "), "a blank child occurrence id")


# --------------------------------------------------------------------------- #
# 2. Suspend and resume: the strictly newer Bias
# --------------------------------------------------------------------------- #
@case
def suspend_then_resume_accepts_a_strictly_newer_bias():
    st = stack.ReturnStack()
    one = addr("c-1", bias=3)
    state = suspend_on(st, one, work=("re-check the P2 prerequisite",))
    assert state.status == stack.SUSPENDED and state.bias_version == 3
    assert state.remaining_work == ("re-check the P2 prerequisite",)

    run = st.resume(one, 4, {"checked": "the child result"})
    assert isinstance(run, stack.Resumption)
    assert run.call_id == "c-1" and run.returned_bias_version == 4
    after = st.state_of(one)
    assert after.status == stack.FINISHED and after.returned_bias_version == 4
    assert after.returned_payload == {"checked": "the child result"}
    assert after.payload == "the caller's saved continuation"
    assert run.may_return_further is False

    assert run.finish_all_remaining_work() == ("re-check the P2 prerequisite",)
    assert run.may_return_further is True
    # the root call has no caller above it: the return stops, and no root is invented
    refused(stack.ALREADY_AT_ROOT, run.return_further, "the root call returning further")

    # a child whose caller is not on the stack is refused too, never handed to a substitute
    orphan_stack = stack.ReturnStack()
    orphan = addr("c-2", parent="c-0")
    suspend_on(orphan_stack, orphan)
    orphan_run = orphan_stack.resume(orphan, 2, "result")
    refusal = refused(stack.NO_WAITING_CALLER, orphan_run.return_further,
                      "a child whose caller was never suspended")
    assert "c-0" in refusal.detail and "none is substituted" in refusal.detail
    print(f"      bias 3 -> 4 accepted; {len(st.receipt())} receipt steps recorded")


@case
def resume_with_an_equal_bias_version_is_refused():
    st = stack.ReturnStack()
    one = addr("c-1", bias=3)
    suspend_on(st, one)
    refusal = refused(stack.BIAS_EQUAL_NOT_NEWER, lambda: st.resume(one, 3, "result"),
                      "an equal Bias version")
    assert "strictly newer" in refusal.detail
    assert st.state_of(one).status == stack.SUSPENDED, "the refusal consumed the return token"


@case
def resume_with_an_older_bias_version_is_refused():
    st = stack.ReturnStack()
    one = addr("c-1", bias=3)
    suspend_on(st, one)
    refusal = refused(stack.BIAS_OLDER_THAN_SUSPENDED, lambda: st.resume(one, 2, "result"),
                      "an older Bias version")
    assert "stale" in refusal.detail
    assert st.state_of(one).status == stack.SUSPENDED
    refused(stack.BIAS_OLDER_THAN_SUSPENDED, lambda: st.resume(one, 0, "result"),
            "version zero against a version 3 suspension")


@case
def a_duplicate_finish_is_refused():
    st = stack.ReturnStack()
    one = addr("c-1")
    suspend_on(st, one)
    assert st.resume(one, 2, "first result").returned_bias_version == 2
    refusal = refused(stack.THREAD_ALREADY_FINISHED,
                      lambda: st.resume(one, 3, "second result"), "a second resume")
    assert "duplicate" in refusal.detail.lower(), refusal.detail

    other = stack.ReturnStack()
    once = addr("c-9")
    suspend_on(other, once)
    other.finish(once)
    refused(stack.THREAD_ALREADY_FINISHED, lambda: other.finish(once), "a second finish")
    refused(stack.THREAD_ALREADY_FINISHED, lambda: other.resume(once, 4, "late"),
            "a resume after a finish nobody took")
    assert other.state_of(once).status == stack.FINISHED


@case
def a_cancelled_thread_cannot_be_resumed():
    st = stack.ReturnStack()
    cancelled = addr("c-1")
    finished = addr("c-2")
    waiting = addr("c-3")
    for one in (cancelled, finished, waiting):
        suspend_on(st, one)
    st.cancel(cancelled, "the parent was replaced before the child finished")
    assert st.state_of(cancelled).status == stack.CANCELLED

    refusal = refused(stack.THREAD_CANCELLED, lambda: st.resume(cancelled, 9, "result"),
                      "a resume of a cancelled thread")
    assert "cancelled" in refusal.detail
    refused(stack.THREAD_CANCELLED, lambda: st.finish(cancelled), "a finish of a cancelled thread")
    refused(stack.THREAD_ALREADY_CANCELLED, lambda: st.cancel(cancelled, "again"),
            "a second cancel")

    st.finish(finished)
    refused(stack.THREAD_ALREADY_FINISHED, lambda: st.cancel(finished, "too late"),
            "a cancel of a finished thread")
    refused(stack.BAD_CANCEL_REASON, lambda: st.cancel(waiting, ""), "a cancel with no reason")


@case
def a_mismatched_call_id_is_refused():
    st = stack.ReturnStack()
    waiting = addr("c-1", parent="c-0")
    suspend_on(st, waiting)

    wrong_occurrence = addr("c-2", parent="c-0")  # same place, a different occurrence
    refusal = refused(stack.CALL_ID_MISMATCH, lambda: st.resume(wrong_occurrence, 5, "result"),
                      "a different call occurrence at the same place")
    assert "c-1" in refusal.detail and "c-2" in refusal.detail, refusal.detail
    assert "never substituted" in refusal.detail

    elsewhere = addr("c-1", parent="c-0", branch="branch-other")
    refused(stack.INEXACT_ADDRESS, lambda: st.resume(elsewhere, 5, "result"),
            "the same occurrence named at another place")
    absent = addr("c-99", parent="c-0", branch="branch-other")
    refused(stack.NO_SUCH_THREAD, lambda: st.resume(absent, 5, "result"),
            "an occurrence nobody ever suspended")


# --------------------------------------------------------------------------- #
# 3. The way back: one step up, never the root
# --------------------------------------------------------------------------- #
@case
def returning_to_the_root_is_refused_and_the_immediate_caller_is_returned():
    st = stack.ReturnStack()
    root, mid, leaf = build_chain(st)

    run = st.resume(leaf, 2, {"leaf": "checked"})
    destination = run.return_further()
    assert destination.is_exact(mid), destination
    assert destination.call_id == "c1"
    assert destination.is_exact(root) is False
    assert destination.is_root is False

    assert st.no_root_shortcut(leaf).is_exact(mid)
    assert stack.no_root_shortcut(st, leaf).is_exact(mid)
    refused(address.NO_ROOT_SHORTCUT, lambda: st.no_root_shortcut(leaf, to_root=True),
            "a jump to the root from the stack")
    refused(address.NO_ROOT_SHORTCUT, lambda: stack.no_root_shortcut(st, leaf, to_root=True),
            "a jump to the root through the module function")
    refused(stack.ALREADY_AT_ROOT, lambda: st.no_root_shortcut(root), "the root's own return")
    print(f"      return went to c1 (mid), not to c0 (root); the root jump was refused")


@case
def the_callers_remaining_work_is_surfaced_before_the_further_return():
    st = stack.ReturnStack()
    steps = ("take the checked result", "reaverage the Bias", "reopen the P2 prerequisite")
    root, mid, leaf = build_chain(st, mid_work=steps)

    assert st.resume(leaf, 2, {"leaf": "checked"}).return_further().is_exact(mid)
    run = st.resume(mid, 3, {"mid": "now holds the leaf result"})
    assert run.remaining_work == steps, run.remaining_work
    assert run.may_return_further is False

    refusal = refused(stack.REMAINING_WORK_UNFINISHED, run.return_further,
                      "returning further with work left")
    assert "two" not in refusal.detail and "three" not in refusal.detail
    assert "reopen the P2 prerequisite" in refusal.detail, refusal.detail

    surfaced = st.remaining_work(mid)
    assert surfaced.remaining == steps and surfaced.finished == ()
    assert surfaced.may_return_further is False
    assert stack.remaining_work(st, mid).remaining == steps

    refused(stack.NOT_NEXT_STEP,
            lambda: run.complete_next_step("reopen the P2 prerequisite"),
            "taking a later step first")
    assert run.complete_next_step() == "take the checked result"
    refused(stack.REMAINING_WORK_UNFINISHED, run.return_further, "two steps still owed")
    assert run.finish_all_remaining_work() == steps[1:]
    assert run.finished_work == steps
    assert run.may_return_further is True
    assert st.remaining_work(mid).may_return_further is True
    refused(stack.NO_REMAINING_WORK, run.complete_next_step, "a step after the last one")

    destination = run.return_further()
    assert destination.is_exact(root), destination
    refused(address.NO_ROOT_SHORTCUT, lambda: run.return_further(to_root=True),
            "a root jump after the work was done")
    print(f"      {len(steps)} own steps surfaced and completed before the return to c0")


@case
def nested_levels_return_to_the_exact_waiting_occurrences_in_order():
    st = stack.ReturnStack()
    root, mid, leaf = build_chain(
        st, root_work=("close the episode",), mid_work=("recheck the prerequisite",)
    )

    assert st.resume(leaf, 2, {"leaf": "checked"}).return_further().is_exact(mid)
    mid_run = st.resume(mid, 3, {"mid": "checked"})
    assert mid_run.resumption_stage == "c1:recheck the prerequisite"
    assert mid_run.complete_next_step() == "recheck the prerequisite"
    assert mid_run.resumption_stage == "c1:return"
    assert mid_run.return_further().is_exact(root)

    root_run = st.resume(root, 4, {"root": "checked"})
    assert root_run.remaining_work == ("close the episode",)
    root_run.finish_all_remaining_work()
    refused(stack.ALREADY_AT_ROOT, root_run.return_further, "the root returning further")

    returns = [(entry["event"], entry["call_id"]) for entry in st.edges()
               if entry["relation"] == stack.RETURN]
    assert returns == [
        ("RESUME", "c2"), ("RETURN_FURTHER", "c2"),
        ("RESUME", "c1"), ("RETURN_FURTHER", "c1"),
        ("RESUME", "c0"),
    ], returns
    went_to = [entry["parent_call_id"] for entry in st.edges()
               if entry["event"] == "RETURN_FURTHER"]
    assert went_to == ["c1", "c0"], went_to
    print(f"      returns in dependency order: c2 -> c1 -> c0, each to its own caller")


@case
def two_occurrences_with_the_same_fields_only_get_their_own_result():
    st = stack.ReturnStack()
    first = addr("c-A", parent="c-0", bias=2)
    second = addr("c-B", parent="c-0", bias=2)  # identical place and Bias, own occurrence
    suspend_on(st, first, payload="A's continuation")
    suspend_on(st, second, payload="B's continuation")
    assert first.place() == second.place() and first.is_exact(second) is False

    run = st.resume(first, 3, "result for A")
    assert run.call_id == "c-A" and run.payload == "result for A"
    assert st.state_of(first).status == stack.FINISHED
    assert st.state_of(second).status == stack.SUSPENDED, "B was woken by A's result"
    assert st.state_of(second).payload == "B's continuation"

    run_b = st.resume(second, 3, "result for B")
    assert run_b.call_id == "c-B" and run_b.payload == "result for B"
    refused(stack.THREAD_ALREADY_FINISHED, lambda: st.resume(first, 9, "a second result for A"),
            "A resumed twice")


# --------------------------------------------------------------------------- #
# 4. The list the address keeps: no half-suspension, no disagreement
# --------------------------------------------------------------------------- #
@case
def a_bias_version_that_disagrees_with_the_address_is_refused():
    st = stack.ReturnStack()
    one = addr("c-1", bias=3)
    refusal = refused(stack.BIAS_ADDRESS_MISMATCH,
                      lambda: st.suspend(one, 4, "payload", remaining_work=()),
                      "a suspension at a Bias version the address does not name")
    assert "3" in refusal.detail and "4" in refusal.detail
    refused(stack.MISSING_BIAS_VERSION, lambda: st.suspend(one, payload="p", remaining_work=()),
            "a suspension with no Bias version")
    refused(stack.MISSING_PAYLOAD, lambda: st.suspend(one, 3, remaining_work=()),
            "a suspension with no saved continuation")
    refused(stack.MISSING_REMAINING_WORK, lambda: st.suspend(one, 3, "p"),
            "a suspension that does not say what it owes")
    refused(stack.BAD_REMAINING_WORK,
            lambda: st.suspend(one, 3, "p", remaining_work="one step"), "a bare string as work")
    assert st.threads() == (), "a refused suspension left a thread behind"


@case
def a_duplicate_suspension_or_a_reused_occurrence_id_is_refused():
    st = stack.ReturnStack()
    one = addr("c-1")
    suspend_on(st, one)
    refused(stack.THREAD_ALREADY_SUSPENDED,
            lambda: st.suspend(one, 1, "payload", remaining_work=()),
            "the same address suspended twice")
    moved = addr("c-1", branch="branch-other")
    refused(stack.CALL_ID_REUSED,
            lambda: st.suspend(moved, 1, "payload", remaining_work=()),
            "one occurrence id at two places")
    assert len(st.threads()) == 1
    assert len(st.waiting_callers()) == 1


# --------------------------------------------------------------------------- #
# 5. The root reference: for looking, not for returning
# --------------------------------------------------------------------------- #
@case
def an_observation_reference_is_not_a_return_path():
    st = stack.ReturnStack()
    root, mid, leaf = build_chain(st)

    reference = address.to_root(leaf, st)
    assert type(reference) is ObservationReference
    assert isinstance(reference, ReturnAddress) is False
    assert reference.is_return_path is False
    assert leaf.is_return_path is True and root.is_return_path is True
    assert reference.root_call_id == "c0" and reference.episode == EPISODE
    assert reference.snapshot_digest == SNAPSHOT_DIGEST

    refused(address.NO_ROOT_SHORTCUT, reference.as_return_destination,
            "a root reference used as a destination")
    refused(address.NOT_A_RETURN_PATH, lambda: st.resume(reference, 5, "result"),
            "a resume of a root reference")
    refused(address.NOT_A_RETURN_PATH,
            lambda: st.suspend(reference, 5, "payload", remaining_work=()),
            "a suspension of a root reference")
    assert leaf.is_exact(reference) is False
    refused(address.NOT_A_RETURN_PATH, lambda: leaf.differing_fields(reference),
            "a field comparison against a root reference")
    refused(address.NOT_A_RETURN_PATH, lambda: address.exactness_report(leaf, reference),
            "an exactness report against a root reference")

    refused(address.ROOT_NOT_RESOLVABLE, lambda: address.to_root(leaf),
            "the root guessed with no chain to walk")
    assert address.to_root(root).root_call_id == "c0"
    assert st.root_address_of(leaf).is_exact(root)
    assert [one.call_id for one in st.chain_of(leaf)] == ["c2", "c1", "c0"]
    print("      reference is a different type, carries no call id, and refuses every return")


# --------------------------------------------------------------------------- #
# 6. The dirty child: every ancestor invalid, the siblings left alone
# --------------------------------------------------------------------------- #
@case
def a_dirty_child_invalidates_every_ancestor_to_the_root():
    st = stack.ReturnStack()
    c0 = addr("c0", bias=1)
    c1 = address.child_of(c0, "c1")
    c2 = address.child_of(c1, "c2")
    c3 = address.child_of(c2, "c3")
    for one in (c0, c1, c2, c3):
        suspend_on(st, one, payload=f"continuation of {one.call_id}")
    assert [entry["call_id"] for entry in st.edges() if entry["relation"] == stack.CALL] == [
        "c0", "c1", "c2", "c3"
    ]

    mark = dirty.mark_dirty(st, "c3", "Power bypass: CO-8 and CO-9 fired to cover a Wisdom gap")
    assert mark.call_id == "c3" and mark.seq == 5
    assert dirty.is_dirty(st, "c3") is True

    report = dirty.invalidate_ancestors(st, "c3")
    assert report.invalidated == ("c2", "c1", "c0"), report.invalidated
    assert report.root_call_id == "c0" and report.root_invalidated is True
    assert dirty.is_invalid(st, "c0") and dirty.is_invalid(st, "c1") and dirty.is_invalid(st, "c2")
    assert dirty.is_invalid(st, "c3") is False, "the dirty child was marked invalid itself"
    assert [st.state_of(one).invalid for one in (c0, c1, c2)] == [True, True, True]
    assert all("c3" in (st.state_of(one).invalid_reason or "") for one in (c0, c1, c2))

    again = st.invalidate_ancestors("c3")
    assert again.invalidated == () and again.already_invalid == ("c2", "c1", "c0")
    assert len(report.untouched) == 0

    refused(stack.THREAD_INVALIDATED, lambda: st.resume(c1, 5, "result"),
            "a return to an invalidated caller")
    refused(stack.ANCESTOR_INVALIDATED, lambda: st.resume(c3, 5, "result"),
            "a return into a chain with an invalid ancestor")
    refused(stack.THREAD_INVALIDATED, lambda: st.resume(c0, 6, "result"),
            "a return to the invalidated root")
    print(f"      dirty c3 -> invalidated {report.invalidated}, root {report.root_call_id}")


@case
def a_clean_sibling_is_unaffected_by_a_dirty_child():
    st = stack.ReturnStack()
    c0 = addr("c0", bias=1)
    c1 = address.child_of(c0, "c1")
    dirty_child = address.child_of(c1, "c-bad")
    sibling = address.child_of(c1, "c-good")
    other_root = addr("x0", bias=1, branch="branch-other")
    other_child = address.child_of(other_root, "x1", branch="branch-other")
    for one in (c0, c1, dirty_child, sibling, other_root, other_child):
        suspend_on(st, one, payload=f"continuation of {one.call_id}")

    dirty.mark_dirty(st, "c-bad", "a Power bypass under c1")
    report = dirty.invalidate_ancestors(st, "c-bad")

    assert report.invalidated == ("c1", "c0"), report.invalidated
    assert report.siblings == ("c-good",), report.siblings
    # the sibling of the dirty child keeps its OWN record clean: canon invalidates the parent
    # chain, and c-good is not on it
    assert dirty.is_invalid(st, "c-good") is False
    assert dirty.is_dirty(st, "c-good") is False
    assert st.state_of(sibling).status == stack.SUSPENDED
    assert st.state_of(sibling).invalid_reason is None
    # the other branch was never touched and is still fully usable
    assert dirty.is_invalid(st, "x0") is False and dirty.is_invalid(st, "x1") is False
    assert set(report.untouched) == {"x0", "x1"}
    assert st.resume(other_child, 4, "result in the untouched branch").returned_bias_version == 4
    # the sibling's own record is clean, but its parent chain is invalid, so nothing above it
    # may return: that is canon's propagation reaching it through the ancestors, not through
    # a mark of its own
    refused(stack.ANCESTOR_INVALIDATED, lambda: st.resume(sibling, 3, "result"),
            "a return inside a chain whose parent was invalidated")
    print(f"      dirty c-bad -> invalidated {report.invalidated}; sibling c-good "
          f"invalid={dirty.is_invalid(st, 'c-good')}, branch x0/x1 untouched")


# --------------------------------------------------------------------------- #
# 7. The real atlas: the snapshot the address names, and who decides glue-back
# --------------------------------------------------------------------------- #
@case
def an_address_binds_to_a_real_saved_snapshot():
    digest = atlas_binding.snapshot_digest_of(SNAPSHOT)
    assert digest == SNAPSHOT_DIGEST
    assert re.fullmatch(r"[0-9a-f]{64}", digest) is not None
    assert OTHER_DIGEST != SNAPSHOT_DIGEST

    assert atlas_binding.require_snapshot(addr("c-1"), SNAPSHOT) == digest
    refused(atlas_binding.SNAPSHOT_MISMATCH,
            lambda: atlas_binding.require_snapshot(addr("c-1", snapshot=OTHER_DIGEST), SNAPSHOT),
            "an address naming another saved snapshot")
    refused(atlas_binding.BAD_SNAPSHOT, lambda: atlas_binding.snapshot_digest_of("state-now"),
            "a saved snapshot that is not the real model's")
    refused(atlas_binding.NOT_A_RETURN_PATH,
            lambda: atlas_binding.require_snapshot("c-1", SNAPSHOT),
            "a snapshot check against something that is not an address")
    print(f"      real snapshot digest bound: {digest[:16]}... vs other {OTHER_DIGEST[:16]}...")


@case
def glue_back_is_decided_by_the_real_model():
    good = atlas_binding.glue_back(glue_pair())
    assert good.ok is True
    assert good.compatible is True and good.conflicting_fields == ()
    assert good.certificate_id is not None and good.certificate_id.startswith("overlap-")
    assert good.witness_id == "w1"
    assert atlas_binding.glue_back_ok(glue_pair()) is True

    bad = atlas_binding.glue_back(glue_pair(conflicting=True))
    assert bad.ok is False
    assert bad.compatible is False and bad.conflicting_fields == ("key",)
    assert atlas_binding.glue_back_ok(glue_pair(conflicting=True)) is False

    refused(atlas_binding.REAL_MODEL_REFUSAL,
            lambda: atlas_binding.glue_back((real_node("lonely", members=("only",)),)),
            "fewer than two regions")

    # Substitute the real functions and watch this build's answer follow them: there is no
    # glue rule of its own to disagree with the real model.
    real_compatibility = atlas_binding.compatibility
    real_certify = atlas_binding.certify_overlap
    try:
        atlas_binding.compatibility = lambda nodes: CompatibilityReport(
            node_ids=tuple(sorted(node.node_id for node in nodes)),
            same_context=True,
            shared_fields=("key",),
            conflicting_fields=("key",),
        )
        assert atlas_binding.glue_back(glue_pair()).ok is False
        atlas_binding.compatibility = real_compatibility

        atlas_binding.certify_overlap = lambda nodes, witness_id=None: (_ for _ in ()).throw(
            ContractError("substituted refusal from the real model")
        )
        refusal = refused(atlas_binding.REAL_MODEL_REFUSAL,
                          lambda: atlas_binding.glue_back(glue_pair()),
                          "a substituted overlap refusal")
        assert "substituted refusal" in refusal.detail
    finally:
        atlas_binding.compatibility = real_compatibility
        atlas_binding.certify_overlap = real_certify
    assert atlas_binding.glue_back(glue_pair()).ok is True


@case
def a_refused_glue_back_blocks_the_resume():
    good = atlas_binding.glue_back(glue_pair())
    st = stack.ReturnStack()
    one = addr("c-1", bias=4)
    suspend_on(st, one)
    st.resume(one, 5, "checked result", glue=good)
    assert st.state_of(one).glue_ok is True

    blocked = stack.ReturnStack()
    other = addr("c-1", bias=4)
    suspend_on(blocked, other)
    bad = atlas_binding.glue_back(glue_pair(conflicting=True))
    refusal = refused(stack.GLUE_BACK_REFUSED_BY_REAL_MODEL,
                      lambda: blocked.resume(other, 5, "checked result", glue=bad),
                      "a glue-back the real model refused")
    assert "conflicting" in refusal.detail
    assert blocked.state_of(other).status == stack.SUSPENDED, "the refusal consumed the token"

    refused(stack.GLUE_VERDICT_NOT_FROM_REAL_MODEL,
            lambda: blocked.resume(other, 5, "r", glue={"ok": True}),
            "a hand-made glue verdict")
    imitation = type("Verdict", (), {"ok": True})()
    refused(stack.GLUE_VERDICT_NOT_FROM_REAL_MODEL,
            lambda: blocked.resume(other, 5, "r", glue=imitation),
            "an object that merely looks like a verdict")
    assert blocked.resume(other, 5, "r").returned_bias_version == 5
    assert blocked.state_of(other).glue_ok is None


@case
def the_copied_real_model_still_hashes_as_recorded():
    now = atlas_binding.verify_real_model()
    assert now == atlas_binding.REAL_MODEL_SHA256
    assert len(now) == 6 and set(now) == set(atlas_binding.REAL_MODEL_SHA256)
    assert now["rpa_model.py"] == (
        "323a53b951644a93603cd2f56204fd5a038a3161f4778e28777e650a4f966f01"
    )
    source = Path(
        "C:/Users/wakil/Documents/Codex/2026-10-16/continuity_build_v3/real_atlas"
    )
    if source.is_dir():
        for name, expected in now.items():
            mine = file_sha256(Path(atlas_binding.REAL_MODEL_DIR) / name)
            theirs = file_sha256(source / name)
            assert mine == theirs, f"{name} is not byte-identical to the copy it came from"
            assert expected == theirs, f"{name} does not hash to the recorded value"
        print(f"      6 files hash as recorded and are byte-identical to {source}")
    else:  # pragma: no cover - the source folder is present on this machine
        print(f"      6 files hash as recorded; the source folder {source} was not available")


# --------------------------------------------------------------------------- #
# 8. The discipline itself: no nearest match, and the lists do not drift
# --------------------------------------------------------------------------- #
@case
def there_is_no_nearest_or_closest_lookup():
    forbidden = re.compile(r"def\s+\w*(nearest|closest|fuzzy|approx|most_recent)\w*\s*\(")
    for name in MODULE_FILES:
        found = forbidden.search(read(name))
        assert found is None, f"{name} defines a proximity lookup: {found.group(0)}"

    st = stack.ReturnStack()
    waiting = addr("c-1", parent="c-0")
    suspend_on(st, waiting)
    # three ways of being wrong, three different words -- never one "near enough"
    refused(stack.CALL_ID_MISMATCH,
            lambda: st.resume(addr("c-2", parent="c-0"), 5, "r"), "the wrong occurrence")
    refused(stack.INEXACT_ADDRESS,
            lambda: st.resume(addr("c-1", parent="c-0", snapshot=OTHER_DIGEST), 5, "r"),
            "the right occurrence, another snapshot")
    refused(stack.NO_SUCH_THREAD,
            lambda: st.resume(addr("c-9", parent="c-0", branch="branch-other"), 5, "r"),
            "nothing suspended there")
    print("      0 proximity lookups defined; 3 distinct refusals for 3 distinct mistakes")


@case
def every_undecided_question_is_in_the_readme():
    marker = re.compile(r"#\s*UNDECIDED IN SOURCES:\s*(.+)$")
    found = []
    for name in MODULE_FILES:
        for line in read(name).splitlines():
            match = marker.match(line.strip())
            if match is not None:
                found.append((name, match.group(1).strip()))
    assert len(found) >= 10, f"only {len(found)} UNDECIDED IN SOURCES markers were found"

    readme = read("README.md")
    missing = [f"{name}: {question}" for name, question in found if question not in readme]
    assert not missing, (
        f"README.md does not list {len(missing)} question(s) the modules mark: {missing[:2]}"
    )

    listed = [
        match.group(1).strip()
        for match in re.finditer(r"^- UNDECIDED IN SOURCES: (.+)$", readme, re.MULTILINE)
    ]
    assert listed, "README.md lists no UNDECIDED IN SOURCES lines"
    asked = {question for _, question in found}
    stale = [question for question in listed if question not in asked]
    assert not stale, (
        f"README.md lists {len(stale)} question(s) no module asks, so the list has drifted: "
        f"{stale[:2]}"
    )
    assert len(listed) == len(found), (
        f"README.md lists {len(listed)} questions and the modules mark {len(found)}"
    )
    print(f"      {len(found)} UNDECIDED IN SOURCES markers, all listed in README.md, "
          f"and no stale entries")


@case
def the_claim_ceiling_is_stated_everywhere():
    assert CLAIM_CEILING in read("README.md")
    for name in MODULE_FILES + ("test_all.py", "ATLAS_COPY.md"):
        assert CLAIM_CEILING in read(name), f"{name} does not state the claim ceiling"
    assert "NO CIRCUIT USES THIS YET" in CLAIM_CEILING


@case
def the_receipt_records_call_and_return_edges_with_their_relations():
    st = stack.ReturnStack()
    root, mid, leaf = build_chain(st)
    st.resume(leaf, 2, "leaf result").return_further()

    entries = st.receipt()
    assert [entry["seq"] for entry in entries] == list(range(1, len(entries) + 1))
    for entry in entries:
        assert entry["event"] and entry["relation"] and entry["call_id"]
        assert entry["snapshot_digest"] == SNAPSHOT_DIGEST
        assert entry["episode"] == EPISODE and entry["branch"] == BRANCH
        assert isinstance(entry["note"], str)

    calls = [entry for entry in entries if entry["relation"] == stack.CALL]
    returns = [entry for entry in entries if entry["relation"] == stack.RETURN]
    assert [entry["call_id"] for entry in calls] == ["c0", "c1", "c2"]
    assert [entry["event"] for entry in returns] == ["RESUME", "RETURN_FURTHER"]
    assert all(entry["parent_call_id"] == {"c0": None, "c1": "c0", "c2": "c1"}[entry["call_id"]]
               for entry in calls)

    entries[0]["note"] = "edited by a reader"
    assert st.receipt()[0]["note"] != "edited by a reader", "receipt() handed out its own list"
    print(f"      {len(entries)} ordered entries: "
          f"{len(calls)} call edge(s), {len(returns)} return edge(s)")


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def main() -> int:
    print("return_address / test_all.py -- the return-address mechanism for a recursive "
          "cognitive architecture")
    print(f"python: {sys.version.split()[0]}  platform: {sys.platform}")
    print(f"build folder: {BUILD_DIR}")
    print(f"real atlas model: {atlas_binding.REAL_MODEL_BRANCH} @ "
          f"{atlas_binding.REAL_MODEL_COMMIT}")
    print(f"real atlas rpa_model.py sha256: "
          f"{atlas_binding.REAL_MODEL_SHA256['rpa_model.py']}")
    print(f"real atlas snapshot digest used by the addresses: {SNAPSHOT_DIGEST}")
    print(f"claim ceiling: {CLAIM_CEILING}")
    print("-" * 78)
    passed = 0
    failed = 0
    for function in CASES:
        name = function.__name__
        try:
            function()
        except Exception as error:  # noqa: BLE001 - a test runner must catch everything
            failed += 1
            print(f"FAIL {name}: {type(error).__name__}: {error}")
            traceback.print_exc()
        else:
            passed += 1
            print(f"PASS {name}")
    print("-" * 78)
    total = passed + failed
    print(f"TOTAL {total} cases: {passed} passed, {failed} failed")
    print("RESULT:", "ALL PASS" if failed == 0 else "FAILURES PRESENT")
    print("No engine ran. No recursion ran. No child was really dispatched or returned: every "
          "call in this file is a record this build made.")
    print(f"claim ceiling, repeated: {CLAIM_CEILING}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
