"""test_label_phase0b.py -- deterministic tests for the label backbone (Phase 0B + 0C).

Phase 0B checks: exact quote verification, nonexistent sense rejection, one-rule-only
acceptance, multiple-rule abstention, no-rule abstention, conflicting-source abstention,
label stability across occurrences, model consensus granting no authority, protected-data
immutability, deterministic replay.

Phase 0C authority-repair checks (owner directive 2026-08-30):
  RESOURCE_RULE_DERIVED is not claim-bearing; CONSTRUCTION_CANDIDATE is not claim-bearing;
  the current pilot contains zero claim-bearing packets; RESOURCE_GOLD cannot exist without
  owner approval; CONSTRUCTION_GOLD cannot exist without generator approval; wrong approval
  digest is rejected; unsigned promotion is rejected; AI consensus cannot promote;
  source-frame and proposed-CAS fields cannot be confused; generator and checker cannot
  share a class lookup (shared-lookup fixtures are unpromotable); the old preregistration
  is superseded only by an append-only amendment.

Self-runnable (python tests/test_label_phase0b.py) and pytest-discoverable. No network,
no model, no GPU.
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from pathlib import Path

LABELS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LABELS))

import label_common as LC  # noqa: E402
import deterministic_label_engine as ENG  # noqa: E402
import label_source_verifier as VER  # noqa: E402
import construction_gold_generator as CG  # noqa: E402
import owner_audit_queue as AQ  # noqa: E402
import owner_gated_promotion as OGP  # noqa: E402

RULES_PATH = LABELS / "CAS_MAPPING_RULES_v1_CANDIDATE.yaml"
RES_PATH = LABELS / "dev_resource" / "DEV_SENSE_RESOURCE_v1.yaml"
PREREG_A = LABELS.parent / "PREREGISTRATION_v0_3A.md"
PREREG_B = LABELS.parent / "PREREGISTRATION_v0_3B_CANDIDATE.md"

PROV = {"frozen_resource_digest": "d", "rule_table_digest": "r", "engine_version": "v"}


def _rt():
    return ENG.load_rule_table(RULES_PATH)


def _sense(sid, gloss, lemma="x", frame=None):
    return {"sense_id": sid, "lemma": lemma, "pos": "v", "gloss": gloss,
            "source": "TEST", "frame": frame}


def _full_claim(frozen, sid, res_digest, **over):
    rec = frozen.by_id[sid]
    claim = {
        "sense_id": sid,
        "source_locator": f"{frozen.resource_id}#{sid}",
        "exact_gloss": rec.get("gloss"),
        "source_frame_id": rec.get("frame"),
        "proposed_cas_class": "NONE",
        "proposed_rule_id": "NONE",
        "model_id": "test-model",
        "model_revision": "r1",
        "model_role": "source_locator",
        "evidence_timestamp": "2026-08-30T00:00:00Z",
        "resource_digest": res_digest,
    }
    claim.update(over)
    return claim


# --------------------------------------------------------------------------- firing (0B)
def test_one_rule_only_acceptance_is_candidate_not_gold():
    rt = _rt()
    p = ENG.label_sense(_sense("t.6", "to dissect an argument into its parts"), rt, "d")
    assert p["authority"] == "RESOURCE_RULE_DERIVED", p
    assert p["cas_label"] == "^6", p
    assert p["claim_bearing"] is False, "a fired rule is a candidate, never claim-bearing"
    assert p["audit_state"] == "UNAUDITED"
    assert p["fired_rules"] == ["CAS-N6"], p["fired_rules"]


def test_multiple_rule_abstention():
    rt = _rt()
    p = ENG.label_sense(_sense("t.m", "to adore and dissect the topic"), rt, "d")
    assert p["authority"] == "ABSTAIN"
    assert p["abstain_reason"] == "multiple_rules"
    assert p["cas_label"] is None
    assert set(p["fired_rules"]) == {"CAS-N2", "CAS-N6"}, p["fired_rules"]


def test_no_rule_abstention():
    rt = _rt()
    p = ENG.label_sense(_sense("t.n", "to move along on foot at a steady pace"), rt, "d")
    assert p["authority"] == "ABSTAIN"
    assert p["abstain_reason"] == "no_rule"


def test_exclude_blocks_only_candidate_is_no_rule():
    rt = _rt()
    p = ENG.label_sense(_sense("t.b", "to question and analyze a claim"), rt, "d")
    assert p["authority"] == "ABSTAIN", p
    assert p["abstain_reason"] == "no_rule", p
    assert "CAS-N6" in p["blocked_rules"], p["blocked_rules"]


def test_visceral_vs_analytical_boundary():
    rt = _rt()
    p = ENG.label_sense(_sense("t.v", "to scrutinize and assess a proposal"), rt, "d")
    assert not (p["authority"] == "RESOURCE_RULE_DERIVED" and p["cas_label"] == "^3"), p


def test_conflicting_source_abstention():
    rt = _rt()
    res = {"senses": [
        _sense("dup.1", "to adore a thing deeply"),
        _sense("dup.1", "to detest a thing deeply"),
    ]}
    packets = ENG.label_resource(res, rt, "d")
    assert all(p["authority"] == "ABSTAIN" for p in packets), packets
    assert all(p["abstain_reason"] == "source_conflict" for p in packets), packets


def test_verifier_flags_cross_class_packets():
    p_a = LC.make_packet("a", "RESOURCE_RULE_DERIVED", "^2", dict(PROV),
                         sense={"sense_id": "s1", "lemma": "x", "pos": "v", "gloss": "g", "source": "T", "frame": None})
    p_b = LC.make_packet("b", "RESOURCE_RULE_DERIVED", "^3", dict(PROV),
                         sense={"sense_id": "s1", "lemma": "x", "pos": "v", "gloss": "g", "source": "T", "frame": None})
    findings = VER.verify_packets([p_a, p_b])
    assert any((not f.ok) and f.check == "no_cross_class" for f in findings), findings


# --------------------------------------------------------------------------- stability / replay
def test_label_stability_across_occurrences():
    rt = _rt()
    g = "to trigger a memory that then arises"
    labels = {ENG.label_sense(_sense(f"occ.{i}", g), rt, "d")["cas_label"] for i in range(5)}
    assert labels == {"^8"}, labels


def test_engine_is_order_independent():
    rt = _rt()
    res = LC.load_yaml(RES_PATH)
    import copy
    r2 = copy.deepcopy(res)
    r2["senses"] = list(reversed(r2["senses"]))
    p1 = {p["sense"]["sense_id"]: p["cas_label"] for p in ENG.label_resource(res, rt, "d")}
    p2 = {p["sense"]["sense_id"]: p["cas_label"] for p in ENG.label_resource(r2, rt, "d")}
    assert p1 == p2, "labeling must not depend on order"


def test_deterministic_replay():
    rt = _rt()
    res = LC.load_yaml(RES_PATH)
    a = LC.canonical_json(ENG.label_resource(res, rt, "d"))
    b = LC.canonical_json(ENG.label_resource(res, rt, "d"))
    assert a == b
    cg1 = LC.canonical_json(CG.generate(10))
    cg2 = LC.canonical_json(CG.generate(10))
    assert cg1 == cg2
    q1 = AQ.build_queue(ENG.label_resource(res, rt, "d"), "r", seed=1)
    q2 = AQ.build_queue(ENG.label_resource(res, rt, "d"), "r", seed=1)
    assert LC.canonical_json(q1[0]) == LC.canonical_json(q2[0])
    assert LC.canonical_json(q1[1]) == LC.canonical_json(q2[1])


# --------------------------------------------------------------------------- authority (0C)
def test_resource_rule_derived_not_claim_bearing():
    p = LC.make_packet("x", "RESOURCE_RULE_DERIVED", "^2", dict(PROV))
    assert p["claim_bearing"] is False
    assert LC.derive_claim_bearing(p) is False


def test_construction_candidate_not_claim_bearing():
    p = LC.make_packet("x", "CONSTRUCTION_CANDIDATE", "^6", dict(PROV))
    assert p["claim_bearing"] is False


def test_fixture_and_model_and_weak_not_claim_bearing():
    for auth in ("CONTROLLED_TEMPLATE_FIXTURE", "MODEL_PROPOSED", "WEAK_LABEL"):
        assert LC.make_packet("x", auth, "^2", dict(PROV))["claim_bearing"] is False
    assert LC.make_packet("x", "ABSTAIN", None, dict(PROV))["claim_bearing"] is False


def test_make_packet_refuses_all_gold_authorities():
    for auth in ("RESOURCE_GOLD", "CONSTRUCTION_GOLD", "OWNER_CORRECTED"):
        try:
            LC.make_packet("x", auth, "^2", dict(PROV))
            raise AssertionError(f"make_packet must refuse gold authority {auth}")
        except ValueError:
            pass


def test_make_packet_enforces_shape_invariants():
    try:
        LC.make_packet("x", "RESOURCE_RULE_DERIVED", None, dict(PROV))
        raise AssertionError("candidate without class must be refused")
    except ValueError:
        pass
    try:
        LC.make_packet("x", "ABSTAIN", "^2", dict(PROV))
        raise AssertionError("ABSTAIN with a class must be refused")
    except ValueError:
        pass


def test_model_consensus_grants_no_authority():
    rt = _rt()
    evidence = None  # engine ignores proposals entirely; firing is recomputed
    p = ENG.label_sense(_sense("t.consensus", "to dissect an argument into its parts"),
                        rt, "d", evidence=evidence)
    assert p["cas_label"] == "^6", "model proposal must not change firing"
    assert p["claim_bearing"] is False
    mp = LC.make_packet("mp", "MODEL_PROPOSED", "^2", dict(PROV))
    assert mp["claim_bearing"] is False


def test_pilot_contains_zero_claim_bearing_packets():
    rt = _rt()
    res = LC.load_yaml(RES_PATH)
    packets = ENG.label_resource(res, rt, "d") + CG.generate(10)
    assert sum(1 for p in packets if p.get("claim_bearing")) == 0
    # and the on-disk pilot artifact, if present, must agree
    on_disk = LABELS / "reports" / "all_packets.json"
    if on_disk.exists():
        disk_packets = LC.load_packets(on_disk)
        assert sum(1 for p in disk_packets if p.get("claim_bearing")) == 0


def test_retired_generator_emits_fixture_with_shared_lookup_marker():
    packets = CG.generate(2)
    assert packets, "generator produced nothing"
    for p in packets:
        assert p["authority"] == "CONTROLLED_TEMPLATE_FIXTURE"
        assert p["claim_bearing"] is False
        assert p["provenance"]["preservation_check"] == "shared_verb_lookup"


# --------------------------------------------------------------------------- promotion (0C)
def _all_rule_ids():
    return list(_rt().by_id.keys())


def _promotion_env(tmp, *, packet_authority="RESOURCE_RULE_DERIVED", packet_kw=None,
                   receipt=None, sign_key=b"test-owner-key-0c", tamper_after_sign=None,
                   decision="APPROVE", manifest_protected_opened=False,
                   pin_matches_key=True, resource_eligible=True,
                   packet_rule_digest=None):
    """Build a full promotion scratch environment; returns the promote() argument dict.

    Phase 0C hardened env: pinned owner-key fingerprint, promoted registry, eligible
    resource manifest entry, provenance bound to the real rule table, receipt with the
    full rules_reviewed attestation, and (for construction) a generator manifest.
    """
    tmp = Path(tmp)
    kw = packet_kw or {}
    prov = dict(PROV)
    # bind provenance to the artifacts the approval will verify
    prov["rule_table_digest"] = packet_rule_digest or LC.sha256_file(RULES_PATH)
    prov["frozen_resource_digest"] = kw.pop("frozen_resource_digest", "test-res-digest")
    prov.update(kw.pop("provenance_extra", {}))
    packet = LC.make_packet("cand::1", packet_authority, kw.pop("cas_label", "^2"), prov, **kw)
    candidates = tmp / "candidates.json"
    LC.write_json(candidates, [packet])

    manifest = tmp / "manifest.json"
    LC.write_json(manifest, {
        "manifest_id": "TEST",
        "protected_opened": manifest_protected_opened,
        "resources": {"test_resource": {"sha256": "test-res-digest",
                                        "claim_bearing_eligible": bool(resource_eligible)}},
    })

    receipt_path = tmp / "receipt.json"
    default_receipt = {"result": "PASS", "major_errors": 0,
                       "rules_reviewed": {rid: True for rid in _all_rule_ids()}}
    LC.write_json(receipt_path, receipt or default_receipt)

    key_file = tmp / "owner.key"
    key_file.write_bytes(sign_key)

    fingerprint = tmp / "fingerprint.json"
    pinned = LC.sha256_bytes(sign_key) if pin_matches_key else ("0" * 64)
    LC.write_json(fingerprint, {"owner_key_sha256": pinned})

    generator_manifest = tmp / "generator_manifest.json"
    LC.write_json(generator_manifest, {"generator": "test-cas-trace-generator", "version": 1})

    record = {
        "study_id": "cas_sem_guided_plasticity_v1",
        "phase": "label-promotion-test",
        "candidate_dataset_digest": LC.sha256_file(candidates),
        "rule_table_digest": LC.sha256_file(RULES_PATH),
        "source_manifest_digest": LC.sha256_file(manifest),
        "audit_receipt_digest": LC.sha256_file(receipt_path),
        "generator_manifest_digest": LC.sha256_file(generator_manifest),
        "approved_by": "owner",
        "decision": decision,
    }
    approval = tmp / "approval.json"
    LC.write_json(approval, OGP.sign_approval(record, key_file))

    if tamper_after_sign == "candidates":
        LC.write_json(candidates, [packet, packet])  # digest no longer matches the approval

    return {
        "candidate_packets_path": candidates,
        "approval_record_path": approval,
        "key_file_path": key_file,
        "rule_table_path": RULES_PATH,
        "source_manifest_path": manifest,
        "audit_receipt_path": receipt_path,
        "out_path": tmp / "promoted.json",
        "fingerprint_path": fingerprint,
        "registry_path": tmp / "registry.json",
        "generator_manifest_path": generator_manifest,
    }


def _expect_refusal(args, code):
    try:
        OGP.promote(**args)
        raise AssertionError(f"expected PromotionRefused({code})")
    except OGP.PromotionRefused as e:
        assert e.code == code, f"expected {code}, got {e.code}: {e}"


def test_promotion_happy_path_creates_claim_bearing_gold():
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp)
        promoted = OGP.promote(**args)
        assert len(promoted) == 1
        g = promoted[0]
        assert g["authority"] == "RESOURCE_GOLD"
        assert g["audit_state"] == "OWNER_APPROVED"
        assert g["phase_approval_valid"] is True
        assert g["claim_bearing"] is True
        # promoted file is REGISTERED and passes the ingest guard (registry-aware)
        loaded = LC.load_packets(args["out_path"], registry_path=args["registry_path"])
        assert loaded[0]["claim_bearing"] is True


def test_unpinned_or_mismatched_key_rejected():
    # (a) fingerprint still the placeholder -> promotion impossible
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp)
        LC.write_json(args["fingerprint_path"], {"owner_key_sha256": "OWNER_TO_SET"})
        _expect_refusal(args, "KEY_NOT_PINNED")
    # (b) key file does not match the pinned fingerprint -> refused
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, pin_matches_key=False)
        _expect_refusal(args, "KEY_NOT_PINNED")


def test_forged_consistent_gold_rejected_at_ingest():
    # a fully self-CONSISTENT forged gold file (fake digests, phase_approval_valid true)
    # passes per-packet validation but MUST be refused by the registry guard on load
    forged = [{
        "packet_id": "forged::gold", "authority": "RESOURCE_GOLD", "cas_label": "^2",
        "claim_bearing": True, "audit_state": "OWNER_APPROVED",
        "approval_manifest_digest": "deadbeef", "owner_approval_digest": "deadbeef",
        "resource_manifest_digest": "deadbeef", "generator_manifest_digest": None,
        "phase_approval_valid": True,
        "sense": None, "construction": None, "fired_rules": [], "blocked_rules": [],
        "abstain_reason": None, "evidence": None, "surface": None,
        "provenance": {"frozen_resource_digest": "deadbeef", "rule_table_digest": "deadbeef",
                       "engine_version": "forged"},
    }]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "forged_gold.json"
        LC.write_json(path, forged)
        empty_registry = Path(tmp) / "registry.json"
        try:
            LC.load_packets(path, registry_path=empty_registry)
            raise AssertionError("expected UNREGISTERED_GOLD_DATASET")
        except ValueError as e:
            assert "UNREGISTERED_GOLD_DATASET" in str(e), e


def test_provenance_mismatch_rejected():
    # (a) packet labeled under a DIFFERENT rule table than the one the owner approved
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, packet_rule_digest="not-the-approved-rule-table")
        _expect_refusal(args, "PROVENANCE_MISMATCH")
    # (b) packet from a resource the manifest does not mark claim_bearing_eligible
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, resource_eligible=False)
        _expect_refusal(args, "PROVENANCE_MISMATCH")


def test_generator_manifest_required_and_verified():
    ckw = {"cas_label": "^6",
           "construction": {"construction_seed": "s", "noetic": "^6",
                            "semantic_graph": {}, "template_id": "t"}}
    # (a) construction promotion without a generator manifest file -> refused
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, packet_authority="CONSTRUCTION_CANDIDATE", packet_kw=dict(ckw))
        args["generator_manifest_path"] = None
        _expect_refusal(args, "GENERATOR_MANIFEST_REQUIRED")
    # (b) generator manifest tampered after signing -> WRONG_DIGEST
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, packet_authority="CONSTRUCTION_CANDIDATE", packet_kw=dict(ckw))
        LC.write_json(args["generator_manifest_path"], {"generator": "tampered"})
        _expect_refusal(args, "WRONG_DIGEST")


def test_receipt_missing_rule_review_fails():
    partial = {"result": "PASS", "major_errors": 0,
               "rules_reviewed": {rid: True for rid in _all_rule_ids()[:-1]}}  # one rule missing
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, receipt=partial)
        _expect_refusal(args, "FAILED_AUDIT")


def test_resource_gold_requires_owner_approval():
    # (a) construction path refused entirely
    try:
        LC.make_packet("x", "RESOURCE_GOLD", "^2", dict(PROV))
        raise AssertionError("unreachable")
    except ValueError:
        pass
    # (b) promotion without a readable approval record refuses
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp)
        os.unlink(args["approval_record_path"])
        _expect_refusal(args, "OWNER_APPROVAL_REQUIRED")


def test_construction_gold_requires_generator_approval_path():
    # CONSTRUCTION_CANDIDATE promotes to CONSTRUCTION_GOLD only through the same signed gate
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, packet_authority="CONSTRUCTION_CANDIDATE",
                              packet_kw={"cas_label": "^6",
                                         "construction": {"construction_seed": "s", "noetic": "^6",
                                                          "semantic_graph": {}, "template_id": "t"}})
        promoted = OGP.promote(**args)
        assert promoted[0]["authority"] == "CONSTRUCTION_GOLD"
        assert promoted[0]["claim_bearing"] is True
        assert promoted[0]["generator_manifest_digest"], "construction gold must carry a generator digest"
    # and without any approval it cannot exist
    try:
        LC.make_packet("x", "CONSTRUCTION_GOLD", "^6", dict(PROV))
        raise AssertionError("unreachable")
    except ValueError:
        pass


def test_wrong_approval_digest_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, tamper_after_sign="candidates")
        _expect_refusal(args, "WRONG_DIGEST")


def test_unsigned_promotion_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp)
        rec = LC.load_json(args["approval_record_path"])
        rec.pop("signature")
        LC.write_json(args["approval_record_path"], rec)
        _expect_refusal(args, "UNSIGNED_APPROVAL")


def test_ai_consensus_cannot_promote():
    # three models "agreeing" author an approval signed with their OWN key. Even when they
    # also supply that same key file for verification (the full self-signing attack), the
    # pinned owner fingerprint refuses it: their key is not the owner's key.
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp)
        fake_key = Path(tmp) / "model_committee.key"
        fake_key.write_bytes(b"three-models-agree-key")
        rec = {k: v for k, v in LC.load_json(args["approval_record_path"]).items() if k != "signature"}
        rec["approved_by"] = "model-committee-of-three"
        LC.write_json(args["approval_record_path"], OGP.sign_approval(rec, fake_key))
        # (a) fake signature checked against the owner key -> UNSIGNED_APPROVAL
        _expect_refusal(args, "UNSIGNED_APPROVAL")
        # (b) the committee also supplies its own key file -> KEY_NOT_PINNED
        args["key_file_path"] = fake_key
        _expect_refusal(args, "KEY_NOT_PINNED")


def test_rule_table_change_invalidates_approval():
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp)
        # point promotion at a different rule table than the approved digest
        other_rules = Path(tmp) / "rules_changed.yaml"
        other_rules.write_text(RULES_PATH.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
        args["rule_table_path"] = other_rules
        _expect_refusal(args, "RULE_TABLE_CHANGED")


def test_failed_audit_rejected_and_sequential_gate():
    assert OGP.audit_gate_outcome(0) == "PASS"
    assert OGP.audit_gate_outcome(1) == "REPAIR_AND_RESAMPLE"
    assert OGP.audit_gate_outcome(2) == "REPAIR_AND_RESAMPLE"
    assert OGP.audit_gate_outcome(3) == "REJECT"
    assert OGP.audit_gate_outcome(7) == "REJECT"
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, receipt={"result": "PASS", "major_errors": 3})
        _expect_refusal(args, "FAILED_AUDIT")


def test_post_protected_modification_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, manifest_protected_opened=True)
        _expect_refusal(args, "POST_PROTECTED_MODIFICATION")


def test_fixture_not_promotable_and_no_shared_lookup():
    # (a) CONTROLLED_TEMPLATE_FIXTURE authority is refused
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, packet_authority="CONTROLLED_TEMPLATE_FIXTURE",
                              packet_kw={"cas_label": "^2"})
        _expect_refusal(args, "FIXTURE_NOT_PROMOTABLE")
    # (b) a candidate whose provenance admits a shared generator/checker lookup is refused
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp, packet_kw={
            "provenance_extra": {"preservation_check": "shared_verb_lookup"}})
        _expect_refusal(args, "FIXTURE_NOT_PROMOTABLE")


def test_promoted_output_is_immutable():
    with tempfile.TemporaryDirectory() as tmp:
        args = _promotion_env(tmp)
        OGP.promote(**args)
        _expect_refusal(args, "OUTPUT_EXISTS")


# --------------------------------------------------------------------------- evidence schema (0C)
def test_exact_quote_verification():
    frozen = VER.FrozenResource.from_path(RES_PATH)
    d = frozen.digest
    rule_ids = list(_rt().by_id.keys())
    ok = VER.verify_evidence_claim(_full_claim(frozen, "dev.v.6.002", d), frozen, d, rule_ids=rule_ids)
    assert any(f.ok and f.check == "exact_quote" for f in ok), ok
    para = VER.verify_evidence_claim(
        _full_claim(frozen, "dev.v.6.002", d, exact_gloss="to  dissect an argument into its parts."),
        frozen, d, rule_ids=rule_ids)
    assert any((not f.ok) and f.check == "exact_quote" for f in para), para
    invented = VER.verify_evidence_claim(
        _full_claim(frozen, "dev.v.6.002", d, exact_gloss="to shred an argument completely"),
        frozen, d, rule_ids=rule_ids)
    assert any((not f.ok) and f.check == "exact_quote" for f in invented), invented


def test_nonexistent_sense_rejection():
    frozen = VER.FrozenResource.from_path(RES_PATH)
    claim = _full_claim(frozen, "dev.v.6.002", frozen.digest)
    claim["sense_id"] = "does.not.exist"
    r = VER.verify_evidence_claim(claim, frozen, frozen.digest)
    assert any((not f.ok) and f.check == "sense_exists" for f in r), r


def test_source_frame_and_cas_class_fields_cannot_be_confused():
    frozen = VER.FrozenResource.from_path(RES_PATH)
    d = frozen.digest
    rule_ids = list(_rt().by_id.keys())
    # a claim stuffing a CAS class into the frame field fails frame_match, while the
    # separate proposed_cas_class field is validated on its own
    confused = VER.verify_evidence_claim(
        _full_claim(frozen, "dev.v.6.002", d, source_frame_id="^6", proposed_cas_class="^6"),
        frozen, d, rule_ids=rule_ids)
    assert any((not f.ok) and f.check == "frame_match" for f in confused), confused
    assert any(f.ok and f.check == "proposed_cas_class" for f in confused), confused
    # the retired combined field is NOT accepted as a substitute: a claim missing the two
    # separate fields fails completeness
    legacy = _full_claim(frozen, "dev.v.6.002", d)
    del legacy["source_frame_id"]
    del legacy["proposed_cas_class"]
    legacy["frame_or_class"] = "^6"
    r = VER.verify_evidence_claim(legacy, frozen, d, rule_ids=rule_ids)
    assert any((not f.ok) and f.check == "evidence_completeness" for f in r), r


def test_evidence_verifier_checks_locator_rule_role_receipt():
    frozen = VER.FrozenResource.from_path(RES_PATH)
    d = frozen.digest
    rule_ids = list(_rt().by_id.keys())
    bad = VER.verify_evidence_claim(
        _full_claim(frozen, "dev.v.6.002", d,
                    source_locator="OTHER_RESOURCE#dev.v.6.002",
                    proposed_rule_id="CAS-N99",
                    model_role="oracle",
                    model_revision=""),
        frozen, d, rule_ids=rule_ids)
    failed = {f.check for f in bad if not f.ok}
    assert "locator_resolves" in failed, bad
    assert "proposed_rule_exists" in failed, bad
    assert "model_role_allowed" in failed, bad
    assert "model_identity_receipt" in failed, bad


def test_protected_data_immutability():
    frozen = VER.FrozenResource.from_path(RES_PATH)
    claim = _full_claim(frozen, "dev.v.6.002", frozen.digest)
    r = VER.verify_evidence_claim(claim, frozen, "WRONG_DIGEST")
    assert any((not f.ok) and f.check == "resource_digest" for f in r), r
    r2 = VER.verify_evidence_claim(claim, frozen, frozen.digest, protected_opened=True)
    assert any((not f.ok) and f.check == "freeze_time" for f in r2), r2


def test_duplicate_sense_id_in_resource_rejected():
    try:
        VER.FrozenResource({"senses": [_sense("dupe", "g1"), _sense("dupe", "g2")]}, "d")
        raise AssertionError("expected ValueError on duplicate sense_id")
    except ValueError:
        pass


# --------------------------------------------------------------------------- ingest guard
def test_ingest_guard_rejects_forged_claim_bearing():
    forged = {"packet_id": "forge", "authority": "RESOURCE_RULE_DERIVED", "cas_label": "^2",
              "claim_bearing": True, "audit_state": "UNAUDITED"}
    try:
        LC.validate_packet(forged)
        raise AssertionError("expected ValueError on forged claim_bearing")
    except ValueError:
        pass
    good = {"packet_id": "ok", "authority": "MODEL_PROPOSED", "cas_label": "^2",
            "claim_bearing": False, "audit_state": "UNAUDITED"}
    assert LC.validate_packet(good) is good


def test_ingest_guard_rejects_gold_without_approval_fields():
    # even a packet CLAIMING gold authority is rejected unless the full approval state is present
    forged_gold = {"packet_id": "fg", "authority": "RESOURCE_GOLD", "cas_label": "^2",
                   "claim_bearing": True, "audit_state": "UNAUDITED"}
    try:
        LC.validate_packet(forged_gold)
        raise AssertionError("expected ValueError: gold without OWNER_APPROVED audit state")
    except ValueError:
        pass


def test_verify_packets_reports_invariant_violation():
    forged = {"packet_id": "forge", "authority": "MODEL_PROPOSED", "cas_label": "^2",
              "claim_bearing": True, "audit_state": "UNAUDITED", "sense": None}
    findings = VER.verify_packets([forged])
    assert any((not f.ok) and f.check == "claim_bearing_invariant" for f in findings), findings


def test_load_packets_rejects_forged_file():
    forged = [{"packet_id": "forge", "authority": "ABSTAIN", "cas_label": "^2",
               "claim_bearing": False, "audit_state": "UNAUDITED"}]
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    LC.write_json(path, forged)
    try:
        LC.load_packets(path)
        raise AssertionError("expected ValueError loading forged packets")
    except ValueError:
        pass
    finally:
        os.unlink(path)


# --------------------------------------------------------------------------- preregistration
def test_preregistration_superseded_append_only():
    assert PREREG_A.exists(), "governing preregistration v0_3A must remain in place"
    assert PREREG_B.exists(), "append-only amendment candidate must exist"
    text_b = PREREG_B.read_text(encoding="utf-8")
    # the amendment records the digest of v0_3A at amendment time; v0_3A must still match
    recorded = None
    for line in text_b.splitlines():
        line = line.strip().strip("`")
        if len(line) == 64 and all(c in "0123456789abcdef" for c in line):
            recorded = line
            break
    assert recorded, "v0_3B candidate must record the v0_3A digest"
    actual = LC.sha256_file_normalized(PREREG_A)
    assert recorded == actual, (
        f"v0_3A was modified after the append-only amendment: recorded {recorded[:12]}..., "
        f"actual {actual[:12]}...")
    assert "append-only" in text_b.lower()
    assert "NOT modified" in text_b or "not modified" in text_b.lower()


ALL_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed, failed = 0, 0
    for t in ALL_TESTS:
        try:
            t()
            passed += 1
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{passed}/{passed + failed} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
