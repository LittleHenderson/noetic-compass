"""test_rc04e.py -- RC-0.4E permanent tests (OWNER DIRECTIVE RC-0.4E: execution-
lifecycle authority, finalization atomicity, split caging, global cause-id
uniqueness, honest cutoff semantics).

One section per directive section:
  1. RUN OWNS THE LIFECYCLE -- typed phases; tick() needs run()'s private scheduler
     capability; result() exists only in a terminal phase.
  2. PROMOTION IS AN AUTHORITY OPERATION -- one-use FinalizationPermit bound to the
     exact provisional sets; the owner's tick-then-promote bypass is dead.
  3. FINALIZATION IS ONE GUARDED TRANSACTION -- any exception (RuntimeError,
     MemoryError, mid-promotion) yields a typed, voided, FAULTED terminal state;
     planned final digest == installed final digest. (Third-party F-01 exact.)
  4. SPLIT OBEYS EVERY BRANCH CEILING -- unit = child branch.
  5. CAUSE IDS ARE GLOBALLY UNIQUE -- generated child ids reserved; collisions get
     deterministic collision-free ids + a typed ID_COLLISION event; registry sealed.
  6. CUTOFF CANNOT REPAIR ITSELF BY RELABELING -- typed CUTOFF_CAUSE_UNRESOLVED,
     non-conducting, no repairs_completed; Desire emitted once; no double repair.

Deterministic, CPU-only, no neural network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parent.parent / "sim"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIM))
sys.path.insert(0, str(ROOT))

import rc0_types as T0             # noqa: E402
import rc01_types as T             # noqa: E402
import rc01_engine as E            # noqa: E402
import rc01_scenarios as SC        # noqa: E402
from rc01_coordinator import (HardenedCoordinator, PublicationCoordinator,  # noqa: E402
                              PublicationRefused)

PAY = "alpha beta gamma delta"
C6 = ("structure_cue",)
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def c6(cid, payload=PAY):
    return SC.cause(cid, C6, payload)


def eng(cid="a0", **kw):
    return SC.engine([c6(cid)], SC.Reg().add(cid, "^6_decompose", "intended", PAY), **kw)


def _standalone_flow(cid="s0"):
    v = E.SealedVerifier({(cid, "^6_decompose"): "intended"},
                         {(cid, "^6_decompose"): "parts[alpha|beta|gamma|delta]"},
                         "ep0")
    coord = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0",
                                receipt_validator=v.validator())
    pubc = PublicationCoordinator("ep0", coord)
    causeS = SC.cause(cid, C6, PAY)
    eff = T.EffectCandidate("^6_decompose", cid, "decompose",
                            "parts[alpha|beta|gamma|delta]", originating_tick=0,
                            base_bias_version=coord.version("^6_decompose"),
                            base_bias_digest=coord.get_digest("^6_decompose"))
    receipt = v.verify(causeS, eff, 0)
    coord.register_verifier_receipt(receipt)
    rec = T0.RegionRecord(region_posterior=(0.05, 0.85, 0.05, 0.05),
                          committed_region="active", semantic_outcome="intended")
    it = T.VersionedIntent("ep0", 0, "kernel", "^6_decompose", "record", rec,
                           coord.version("^6_decompose"),
                           coord.get_digest("^6_decompose"),
                           verifier_receipt_digest=receipt.receipt_digest)
    dcr = coord.commit([it], 0, effect_context=T.EffectCommitContext(
        effect=eff, verifier_receipt_digest=receipt.receipt_digest))
    intent = T.EffectPublicationIntent(
        "ep0", 0, cid, eff.effect_digest, "^6_decompose", "intended",
        receipt.receipt_digest, base_state_version=dcr.pre_state_version,
        base_state_digest=dcr.pre_state_digest,
        diagnostic_commit_digest=dcr.commit_digest)
    return pubc, intent


# ================================================ 1. run owns the lifecycle
def test_direct_tick_before_run_is_refused():
    e = eng("l0")
    sealed = e.seal()
    left = e.budget.left
    try:
        e.tick(0, e.causes[0])
        raise AssertionError("a direct tick() executed without the scheduler")
    except E.ControllerLifecycleError:
        pass
    assert e.phase == "NEW" and e.budget.left == left and e.events == []
    assert e.seal() == sealed, "the refused tick mutated state"


def test_direct_tick_cannot_inject_unregistered_cause():
    e = eng("l1")
    sealed = e.seal()
    try:
        e.tick(0, c6("ghost_injected"))
        raise AssertionError("a direct tick() injected an unregistered cause")
    except E.ControllerLifecycleError:
        pass
    assert "ghost_injected" not in e.used_cause_ids
    assert e.seal() == sealed and e.metrics["executions"] == 0


def test_result_before_finalization_is_refused():
    e = eng("l2")
    try:
        e.result()
        raise AssertionError("result() emitted evidence before a terminal phase")
    except E.ControllerLifecycleError:
        pass
    except AssertionError:
        raise
    except BaseException as exc:  # noqa: BLE001
        raise AssertionError(
            f"pre-final result() refused via the WRONG law ({type(exc).__name__}); "
            "the terminal-phase requirement is gone")


def test_run_is_the_only_execution_entry_point():
    e = eng("l3")
    assert e.phase == "NEW"
    r = e.run()
    assert e.phase == "FINALIZED" and r["metrics"]["published"] == 1
    try:
        e.run()
        raise AssertionError("run() executed a second time")
    except E.FinalizedControllerError:
        pass
    try:
        e.tick(9, e.causes[0])
        raise AssertionError("tick() executed after finalization")
    except (E.FinalizedControllerError, E.ControllerLifecycleError):
        pass


def test_manual_tick_then_run_cannot_duplicate_execution():
    e = eng("l4")
    try:
        e.tick(0, e.causes[0])
    except E.ControllerLifecycleError:
        pass
    r = e.run()
    assert r["metrics"]["executions"] == 1 and r["metrics"]["published"] == 1, \
        "the refused manual tick changed the run's execution count"


# ================================================ 2. promotion is authority
def test_public_promotion_without_finalization_permit_refused():
    pubc, intent = _standalone_flow("p0")
    assert pubc.commit_publication(intent) == "PROVISIONAL_PUBLICATION"
    try:
        pubc.promote_provisionals()
        raise AssertionError("promotion succeeded without a FinalizationPermit")
    except PublicationRefused as pr:
        assert pr.law == "PUB_LAW_PROMOTION_REQUIRES_PERMIT", pr.law
    assert all(d["decision"] != "PUBLISHED" for d in pubc.ledger)


def test_tick_then_direct_promotion_cannot_publish():
    # THE OWNER'S BYPASS, verbatim: tick -> promote -> result. All three doors closed.
    e = eng("p1")
    try:
        e.tick(0, e.causes[0])
        raise AssertionError("bypass step 1: direct tick executed")
    except E.ControllerLifecycleError:
        pass
    try:
        e.pubcoord.promote_provisionals()
        raise AssertionError("bypass step 2: direct promotion succeeded")
    except PublicationRefused:
        pass
    try:
        e.pubcoord.claim_lifecycle_authority()
        raise AssertionError("bypass step 2b: lifecycle authority re-claimed")
    except PublicationRefused:
        pass
    try:
        e.result()
        raise AssertionError("bypass step 3: result before finalization")
    except E.ControllerLifecycleError:
        pass
    assert e.metrics["published"] == 0
    assert all(d["decision"] != "PUBLISHED" for d in e.pubcoord.ledger)


def test_promotion_permit_bound_to_exact_provisional_ledger():
    pubc, intent = _standalone_flow("p2")
    auth = pubc.claim_lifecycle_authority()
    # permit issued over an EMPTY provisional set...
    permit = pubc.issue_finalization_permit(auth, planned_snapshot_digest="x",
                                            engine_provisional_indices=(),
                                            state_digest="d", sequence=0)
    # ...then the provisional set changes
    pubc.commit_publication(intent)
    try:
        pubc.promote_provisionals(permit)
        raise AssertionError("a stale permit promoted a changed provisional set")
    except PublicationRefused as pr:
        assert pr.law == "PUB_LAW_PERMIT_STALE_PROVISIONALS", pr.law


def test_promotion_permit_is_one_use():
    pubc, intent = _standalone_flow("p3")
    pubc.commit_publication(intent)
    auth = pubc.claim_lifecycle_authority()
    permit = pubc.issue_finalization_permit(auth, planned_snapshot_digest="x",
                                            engine_provisional_indices=(),
                                            state_digest="d", sequence=0)
    assert pubc.promote_provisionals(permit) == 1
    try:
        pubc.promote_provisionals(permit)
        raise AssertionError("a consumed permit promoted a second time")
    except PublicationRefused as pr:
        assert pr.law == "PUB_LAW_PERMIT_CONSUMED", pr.law


def test_result_cannot_expose_published_before_final_seal():
    e = eng("p4")
    try:
        e.result()
        raise AssertionError("pre-final evidence exposed")
    except E.ControllerLifecycleError:
        pass
    r = e.run()
    assert e.phase == "FINALIZED"
    assert r["publications"][0]["status"] == "PUBLISHED", \
        "the finalized result does not carry the promoted publication"


# ================================================ 3. finalization atomicity
def _raise_factory(exc):
    def _r(*_a, **_k):
        raise exc
    return _r


def test_finalization_runtimeerror_is_typed():
    """Third-party auditor F-01, exact: a RuntimeError during the prospective final
    snapshot must become a typed FAULT with a voided, terminal, deterministic state --
    never a raw escape with a stranded provisional."""
    e = eng("f0")
    e._planned_final_snapshot_digest = _raise_factory(RuntimeError("environmental"))
    try:
        e.run()
        raise AssertionError("finalization error produced no exception at all")
    except E.ControllerFault as cf:
        assert cf.fault["exception_class"] == "RuntimeError"
    except AssertionError:
        raise
    except BaseException as exc:  # noqa: BLE001
        raise AssertionError(
            f"finalization error escaped UNTYPED as {type(exc).__name__}")
    assert e.phase == "FAULTED" and e.finalized
    assert e.metrics["published"] == 0
    assert all(d["decision"] != "PUBLISHED" for d in e.pubcoord.ledger)
    assert all(d["decision"] != "PROVISIONAL_PUBLICATION" for d in e.pubcoord.ledger), \
        "a provisional publication was left stranded"
    assert HEX64.match(e.seal_digest), "the faulted state did not seal deterministically"
    assert e.result()["fault"] is not None


def test_memoryerror_during_prospective_snapshot_is_typed():
    e = eng("f1")
    e._planned_final_snapshot_digest = _raise_factory(MemoryError("simulated"))
    try:
        e.run()
        raise AssertionError("MemoryError produced no exception at all")
    except E.ControllerFault as cf:
        assert cf.fault["exception_class"] == "MemoryError"
    except AssertionError:
        raise
    except BaseException as exc:  # noqa: BLE001
        raise AssertionError(f"MemoryError escaped UNTYPED as {type(exc).__name__}")
    assert e.phase == "FAULTED" and e.metrics["published"] == 0
    assert all(d["decision"] != "PROVISIONAL_PUBLICATION" for d in e.pubcoord.ledger)


def test_exception_during_promotion_voids_all_publications():
    e = eng("f2")
    e.pubcoord.promote_provisionals = _raise_factory(RuntimeError("promotion died"))
    try:
        e.run()
        raise AssertionError("promotion failure escaped")
    except E.ControllerFault:
        pass
    assert e.phase == "FAULTED" and e.metrics["published"] == 0
    assert all(d["decision"] != "PUBLISHED" for d in e.pubcoord.ledger)
    assert any(d["decision"] == "VOIDED_UNSEALED" for d in e.pubcoord.ledger)


def test_exception_after_engine_promotion_before_ledger_promotion_rolls_back():
    # the sabotage promotes the LEDGER for real, then raises -- the terminal fault
    # must roll the partially promoted state back to VOIDED everywhere
    e = eng("f3")
    real = e.pubcoord.promote_provisionals

    def sabotage(permit=None):
        real(permit)
        raise RuntimeError("died after partial promotion")
    e.pubcoord.promote_provisionals = sabotage
    try:
        e.run()
        raise AssertionError("partial promotion escaped")
    except E.ControllerFault:
        pass
    assert e.metrics["published"] == 0
    assert all(d["decision"] != "PUBLISHED" for d in e.pubcoord.ledger), \
        "a partially promoted PUBLISHED row survived the fault"
    voided = [d for d in e.pubcoord.ledger if d["decision"] == "VOIDED_UNSEALED"]
    assert voided and voided[0].get("voided_from") == "PUBLISHED"


def test_planned_final_digest_equals_installed_final_digest():
    e = eng("f4")
    r = e.run()
    assert HEX64.match(r["trace_digest"])
    assert r["trace_digest"] == e.seal() == e.seal_digest, \
        "the installed final digest is not the live final digest"
    assert e.phase == "FINALIZED" and r["metrics"]["published"] == 1


def test_no_partial_promotion_state_can_escape():
    e = eng("f5")
    e.pubcoord.promote_provisionals = _raise_factory(RuntimeError("x"))
    try:
        e.run()
    except E.ControllerFault:
        pass
    for row in e.publications:
        assert row["status"] in ("VOIDED_UNSEALED", "REFUSED", "ABSTAINED"), \
            f"a partial promotion state escaped: {row['status']}"
    assert e.metrics["voided_publications"] >= 1


# ================================================ 4. split caging
def _split_engine(**kw):
    reg = (SC.Reg().add("sp0.c0", "^6_decompose", "intended", "alpha beta")
                 .add("sp0.c1", "^6_decompose", "intended", "gamma delta")
                 .add("sp0", "^6_decompose", "intended",
                      combined_children=("alpha beta", "gamma delta")))
    return SC.engine([SC.cause("sp0", ("structure_cue", "overload_cue"), PAY)], reg,
                     states=SC.states(**{"^6_decompose": {"region": "saturation"}}),
                     **kw)


def test_split_refused_when_max_active_branches_zero():
    e = _split_engine(max_active_branches=0)
    r = e.run()
    assert e.child_to_frame == {} and e.split_frames == {}, \
        "a split opened children past max_active_branches = 0"
    assert r["metrics"]["splits_created"] == 0
    assert any(ev["event"] == "CAUSE_DEFERRED" and ev["why"] == "split_branch_limit"
               for ev in r["events"]), "no typed limit event"


def test_two_child_split_requires_two_total_branch_slots():
    e1 = _split_engine(max_total_branches=1)      # one slot: two children refused
    r1 = e1.run()
    assert r1["metrics"]["splits_created"] == 0, \
        "a two-child split fit into one total-branch slot"
    e2 = _split_engine(max_total_branches=2)      # two slots: allowed, both consumed
    r2 = e2.run()
    assert r2["metrics"]["splits_created"] == 2
    assert e2.total_branches_opened == 2, "two children consumed only one slot"


def test_split_respects_expert_governance_branch_limit():
    e = _split_engine()
    # rebuild with the chosen expert's OWN governance cage at 1
    reg = (SC.Reg().add("sp0.c0", "^6_decompose", "intended", "alpha beta")
                 .add("sp0.c1", "^6_decompose", "intended", "gamma delta")
                 .add("sp0", "^6_decompose", "intended",
                      combined_children=("alpha beta", "gamma delta")))
    e = SC.engine([SC.cause("sp0", ("structure_cue", "overload_cue"), PAY)], reg,
                  states=SC.states(**{"^6_decompose": {"region": "saturation",
                                                       "max_branches": 1}}))
    r = e.run()
    assert r["metrics"]["splits_created"] == 0, \
        "a split ignored the expert's Governance branch cage"


def test_split_limit_refusal_creates_no_child_mapping():
    e = _split_engine(max_active_branches=0)
    ids_before = set(e.used_cause_ids)
    e.run()
    assert e.child_to_frame == {} and e.split_frames == {}
    assert e.used_cause_ids == ids_before, "a refused split reserved child ids"


def test_split_limit_refusal_spends_no_child_execution_budget():
    e = _split_engine(max_active_branches=0, budget=10)
    r = e.run()
    assert r["budget_left"] == 10, \
        "a refused split spent budget"


# ================================================ 5. global cause-id uniqueness
def _collision_engine(child0_verdict="intended"):
    reg = (SC.Reg().add("sp0.c0", "^6_decompose", child0_verdict, "alpha beta")
                 .add("sp0.c1.g1", "^6_decompose", "intended", "gamma delta")
                 .add("sp0", "^6_decompose", "intended",
                      combined_children=("alpha beta", "gamma delta"))
                 .add("sp0.c1", "^6_decompose", "intended", "own payload here"))
    return SC.engine([SC.cause("sp0", ("structure_cue", "overload_cue"), PAY),
                      SC.cause("sp0.c1", C6, "own payload here")], reg,
                     states=SC.states(**{"^6_decompose": {"region": "saturation"}}))


def test_top_level_id_cannot_collide_with_generated_child():
    e = _collision_engine()
    r = e.run()
    collisions = [ev for ev in r["events"] if ev["event"] == "ID_COLLISION"]
    assert collisions and collisions[0]["requested"] == "sp0.c1" \
        and collisions[0]["allocated"] == "sp0.c1.g1", \
        "no deterministic collision-free child id was allocated"
    top = [p for p in r["publications"]
           if p["cause"] == "sp0.c1" and p["status"] == "PUBLISHED"]
    assert top, "the unrelated top-level Cause lost its own publication"


def test_failed_child_cannot_cancel_unrelated_top_level_cause():
    # the failing child uses off_axis (consequence REPAIR) rather than opposite --
    # opposite would correctly QUARANTINE the shared expert (RC-0.4E round-2
    # consequence law) and mask what this test isolates: sibling cancellation scope
    e = _collision_engine(child0_verdict="off_axis")   # first child fails the frame
    r = e.run()
    cancelled = [ev["cause"] for ev in r["events"] if ev["event"] == "CHILD_CANCELLED"]
    assert "sp0.c1" not in cancelled, \
        "an unrelated top-level Cause was cancelled as a sibling"
    top = [p for p in r["publications"]
           if p["cause"] == "sp0.c1" and p["status"] == "PUBLISHED"]
    assert top, "the unrelated top-level Cause did not publish"


def test_two_distinct_cause_envelopes_never_share_one_id():
    try:
        SC.engine([c6("dup"), SC.cause("dup", C6, "different payload")],
                  SC.Reg().add("dup", "^6_decompose", "intended", PAY))
        raise AssertionError("two envelopes shared one id at construction")
    except ValueError:
        pass
    e = _collision_engine()
    e.run()
    assert len(e.used_cause_ids) == len(set(e.used_cause_ids))
    assert {"sp0", "sp0.c0", "sp0.c1", "sp0.c1.g1"} <= e.used_cause_ids


def test_global_id_registry_is_seal_bound():
    e = eng("gid0")
    e.run()
    sealed = e.seal()
    e.used_cause_ids.add("ghost_id")
    assert e.seal() != sealed, "the seal is blind to the global cause-id registry"


# ================================================ 6. honest cutoff semantics
def _ready_cutoff_engine(cid="rc0", **bias_over):
    over = {"region": "cutoff"}
    over.update(bias_over)
    return SC.engine([c6(cid)], SC.Reg().add(cid, "^6_decompose", "intended", PAY),
                     states=SC.states(**{"^6_decompose": over}))


def test_ready_cutoff_cannot_self_clear_without_new_evidence():
    e = _ready_cutoff_engine("rc1")
    r = e.run()
    names = [ev["event"] for ev in r["events"]]
    assert "CUTOFF_CAUSE_UNRESOLVED" in names, "no typed unresolved status"
    assert r["metrics"]["published"] == 0 and r["metrics"]["executions"] == 0, \
        "a ready-but-cutoff route conducted after relabeling itself"
    assert r["final_states"]["^6_decompose"]["version"] == 0, \
        "the cutoff route rewrote its own region record"


def test_cutoff_reassessment_does_not_count_as_completed_repair():
    e = _ready_cutoff_engine("rc2")
    r = e.run()
    assert r["metrics"]["repairs_completed"] == 0 and r["metrics"]["action_repair"] == 0, \
        "clearing a warning label was counted as a completed repair"
    assert r["metrics"]["cutoff_unresolved"] >= 1


def test_cutoff_unresolved_does_not_execute():
    e = _ready_cutoff_engine("rc3")
    r = e.run()
    assert r["metrics"]["executions"] == 0 and r["metrics"]["published"] == 0
    assert "HALT" not in [ev["event"] for ev in r["events"]], \
        "unresolved cutoff degraded to a silent HALT"


def test_cutoff_desire_block_emitted_once():
    e = _ready_cutoff_engine("rc4", desire=0.0)
    r = e.run()
    n = sum(1 for ev in r["events"] if ev["event"] == "DESIRE_DEPRIORITIZED")
    assert n == 1, f"Desire deprioritization emitted {n} times"
    assert r["metrics"]["desire_deprioritized"] == 1


def test_failed_cutoff_repair_not_retried_twice_same_tick():
    e = _ready_cutoff_engine("rc5", wisdom=0.0)
    # exhaust the budget so the ASOM repair attempt fails
    e2 = SC.engine([c6("rc5")], SC.Reg().add("rc5", "^6_decompose", "intended", PAY),
                   states=SC.states(**{"^6_decompose": {"region": "cutoff",
                                                        "wisdom": 0.0}}),
                   budget=0)
    r = e2.run()
    names = [ev["event"] for ev in r["events"]]
    assert "ASOM_REPAIR_FAILED" in names
    assert r["metrics"]["repair_failures"] == 1, \
        f"a failed ASOM repair was retried ({r['metrics']['repair_failures']} attempts)"
    assert "NO_READY_CJT" not in names, \
        "the failed ASOM repair fell through to a second repair path"


# ================================================ internal round-2 locks
def test_prerun_internal_execution_refused():
    """Internal audit round-2 MAJOR: the execution internals carry the LIFECYCLE
    guard, not just the finalization latch -- pre-run direct calls refuse BEFORE any
    budget, commit, event, or provisional publication exists, so a later run() has
    nothing injected to launder."""
    e = eng("pi0")
    sealed = e.seal()
    left = e.budget.left
    for name, call in (
            ("_repair", lambda: e._repair("^6_decompose", "WISDOM", 0)),
            ("_execute_verify_commit", lambda: e._execute_verify_commit(
                0, e.causes[0], "^6_decompose", 1.0, {"^6_decompose": (1, None)})),
            ("_do_split", lambda: e._do_split(0, e.causes[0], "^6_decompose")),
            ("_publish_or_refuse", lambda: e._publish_or_refuse(
                0, e.causes[0], None, None, None))):
        try:
            call()
            raise AssertionError(f"{name} executed outside run()'s lifecycle")
        except E.ControllerLifecycleError:
            pass
    assert e.budget.left == left and e.events == [] and e.coord.trace == []
    assert e.seal() == sealed, "a refused pre-run internal call mutated state"
    r = e.run()
    assert r["metrics"]["published"] == 1 and r["metrics"]["executions"] == 1


def test_run_refuses_non_pristine_engine():
    e = eng("pi1")
    e.events.append({"tick": 0, "event": "INJECTED"})   # raw write past the API
    try:
        e.run()
        raise AssertionError("run() sealed injected pre-run work")
    except E.ControllerLifecycleError:
        pass


def test_terminal_phase_without_seal_refused():
    e = eng("pi2")
    e.phase = "FINALIZED"                                # raw write past the API
    try:
        e.result()
        raise AssertionError("unsealed evidence emitted under a terminal phase")
    except E.ControllerTampered:
        pass


def test_split_resume_applies_publication_consequences():
    """Internal audit round-2 CRITICAL: a verifier-confirmed 'opposite' combined
    Effect on the RESUME path quarantines its producer exactly as the direct path."""
    reg = (SC.Reg().add("qp.c0", "^6_decompose", "intended", "alpha beta")
                 .add("qp.c1", "^6_decompose", "intended", "gamma delta")
                 .add("qp", "^6_decompose", "opposite"))
    e = SC.engine([SC.cause("qp", ("structure_cue", "overload_cue"), PAY)], reg,
                  states=SC.states(**{"^6_decompose": {"region": "saturation"}}))
    r = e.run()
    q = [ev for ev in r["events"] if ev["event"] == "QUARANTINE"]
    assert q and q[0]["authorized_by"] == "publication_law:opposite", \
        "the resume path swallowed the opposite-verdict quarantine"
    assert "^6_decompose" in r["quarantined"]


def test_dropped_causes_have_terminal_disposition():
    e = _ready_cutoff_engine("dd0")
    r = e.run()
    drops = [ev for ev in r["events"] if ev["event"] == "CAUSE_DROPPED"]
    assert drops and drops[0]["cause"] == "dd0" \
        and drops[0]["why"] == "cutoff_unresolved", \
        "a dropped cause has no typed terminal disposition"
    assert r["metrics"]["dropped_causes"] >= 1


def test_split_restricted_to_registered_combined_ops():
    # ^2_attract has no registered combined op -> the overload split fails closed
    reg = SC.Reg().add("na0", "^2_attract", "intended", PAY)
    e = SC.engine([SC.cause("na0", ("valence_positive", "overload_cue"), PAY)], reg,
                  states=SC.states(**{"^2_attract": {"region": "saturation"}}))
    r = e.run()
    assert r["metrics"]["splits_created"] == 0
    assert any(ev.get("why") == "split_no_combined_op" for ev in r["events"]), \
        "no typed deferral for an unregistered combined op"


def test_suspended_frame_swept_at_finalize():
    # the budget dies between split children -> the frame may NOT stay SUSPENDED
    reg = (SC.Reg().add("sw.c0", "^6_decompose", "intended", "alpha beta")
                 .add("sw.c1", "^6_decompose", "intended", "gamma delta")
                 .add("sw", "^6_decompose", "intended",
                      combined_children=("alpha beta", "gamma delta")))
    e = SC.engine([SC.cause("sw", ("structure_cue", "overload_cue"), PAY)], reg,
                  states=SC.states(**{"^6_decompose": {"region": "saturation"}}),
                  budget=2)
    e.run()
    assert e.split_frames == {} and e.child_to_frame == {}, \
        "a SUSPENDED frame survived finalization"
    assert any(d.get("law") == "PUB_LAW_SPLIT_CHILD_FAILED" for d in e.pubcoord.ledger
               if d["decision"] == "REFUSED"), "no terminal refusal for the swept parent"


def test_failed_frame_refusal_in_both_surfaces():
    sc = next(s for s in SC.SCENARIOS() if s["id"] == "split_child_failure_no_orphan")
    e = sc["build"]()
    r = e.run()
    eng_rows = [p for p in r["publications"]
                if p.get("law") == "PUB_LAW_SPLIT_CHILD_FAILED"]
    led_rows = [d for d in e.pubcoord.ledger
                if d.get("law") == "PUB_LAW_SPLIT_CHILD_FAILED"]
    assert eng_rows and led_rows, \
        "the split refusal is missing from an evidence surface"


def test_governance_split_cage_is_per_expert():
    from rc01_engine import SplitFrame
    from rc01_types import Cause
    reg = (SC.Reg().add("gp.c0", "^6_decompose", "intended", "alpha beta")
                 .add("gp.c1", "^6_decompose", "intended", "gamma delta")
                 .add("gp", "^6_decompose", "intended",
                      combined_children=("alpha beta", "gamma delta")))
    e = SC.engine([SC.cause("gp", ("structure_cue", "overload_cue"), PAY)], reg,
                  states=SC.states(**{"^6_decompose": {"region": "saturation",
                                                       "max_branches": 2}}))
    # a FOREIGN expert's open frame (raw injection): its children must not consume
    # ^6_decompose's OWN governance cage
    foreign = SplitFrame(parent_cause=Cause("fp", ("association_cue",), "x y"),
                         chosen_expert="^8_trigger", child_ids=("fp.c0", "fp.c1"),
                         pending={"fp.c0": None, "fp.c1": None}, return_address="fp")
    e.split_frames["fp"] = foreign
    e.child_to_frame["fp.c0"] = "fp"
    e.child_to_frame["fp.c1"] = "fp"
    r = e.run()
    assert r["metrics"]["splits_created"] == 2, \
        "a foreign expert's open children blocked this expert's governance cage"


# ================================================ F-02 / F-03 addendum locks
def test_states_coverage_both_directions():
    partial = {k: SC.bias() for k in ("^6_decompose",)}
    try:
        SC.engine([c6("cv0")], SC.Reg(), states=partial)
        raise AssertionError("missing-expert states accepted")
    except ValueError:
        pass
    ghost = dict(SC.states())
    ghost["^99_ghost"] = SC.bias()
    try:
        SC.engine([c6("cv0")], SC.Reg(), states=ghost)
        raise AssertionError("extra-expert states accepted")
    except ValueError:
        pass


def test_voided_rows_carry_provenance():
    e = eng("vp0")
    e.invalidation_events = {("x", object())}     # out-of-API poison past the gate
    try:
        e.run()
    except E.ControllerFault:
        pass
    voided_ledger = [d for d in e.pubcoord.ledger if d["decision"] == "VOIDED_UNSEALED"]
    voided_engine = [p for p in e.publications if p["status"] == "VOIDED_UNSEALED"]
    assert voided_ledger and voided_engine
    for d in voided_ledger:
        assert d.get("voided_from") in ("PROVISIONAL_PUBLICATION", "PUBLISHED")
    for p in voided_engine:
        assert p.get("voided_from") in ("PROVISIONAL_PUBLICATION", "PUBLISHED")


ALL_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed, failed = 0, 0
    for t in ALL_TESTS:
        try:
            t()
            passed += 1
            print(f"PASS {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
    print(f"\n{passed}/{passed + failed} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
