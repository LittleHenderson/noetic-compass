"""test_label_phase0b.py -- deterministic tests for the LABEL PHASE 0B backbone.

Covers the owner's required checks:
  exact quote verification, nonexistent sense rejection, one-rule-only acceptance,
  multiple-rule abstention, no-rule abstention, conflicting-source abstention,
  label stability across occurrences, model consensus granting no authority,
  protected-data immutability, deterministic replay.

Self-runnable (python test_label_phase0b.py) and pytest-discoverable. No network, no model,
no GPU.
"""
from __future__ import annotations

import sys
from pathlib import Path

LABELS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LABELS))

import label_common as LC  # noqa: E402
import deterministic_label_engine as ENG  # noqa: E402
import label_source_verifier as VER  # noqa: E402
import construction_gold_generator as CG  # noqa: E402
import owner_audit_queue as AQ  # noqa: E402

RULES_PATH = LABELS / "CAS_MAPPING_RULES_v1.yaml"
RES_PATH = LABELS / "dev_resource" / "DEV_SENSE_RESOURCE_v1.yaml"


def _rt():
    return ENG.load_rule_table(RULES_PATH)


def _sense(sid, gloss, lemma="x", frame=None):
    return {"sense_id": sid, "lemma": lemma, "pos": "v", "gloss": gloss,
            "source": "TEST", "frame": frame}


# --------------------------------------------------------------------------- firing
def test_one_rule_only_acceptance():
    rt = _rt()
    p = ENG.label_sense(_sense("t.6", "to dissect an argument into its parts"), rt, "d")
    assert p["authority"] == "RESOURCE_GOLD", p
    assert p["cas_label"] == "^6", p
    assert p["claim_bearing"] is True
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
    # "question and analyze" -> ^6 include 'analyze' matched but ^6 exclude 'question' blocks it
    rt = _rt()
    p = ENG.label_sense(_sense("t.b", "to question and analyze a claim"), rt, "d")
    assert p["authority"] == "ABSTAIN", p
    assert p["abstain_reason"] == "no_rule", p
    assert "CAS-N6" in p["blocked_rules"], p["blocked_rules"]


def test_visceral_vs_analytical_boundary():
    # ^3 must be visceral; an analytical 'scrutinize' gloss must NOT fire ^3
    rt = _rt()
    p = ENG.label_sense(_sense("t.v", "to scrutinize and assess a proposal"), rt, "d")
    assert not (p["authority"] == "RESOURCE_GOLD" and p["cas_label"] == "^3"), p


# --------------------------------------------------------------------------- conflict
def test_conflicting_source_abstention():
    rt = _rt()
    # same sense_id, two conflicting glosses -> both must ABSTAIN(source_conflict)
    res = {"senses": [
        _sense("dup.1", "to adore a thing deeply"),      # would be ^2
        _sense("dup.1", "to detest a thing deeply"),      # would be ^3
    ]}
    packets = ENG.label_resource(res, rt, "d")
    assert all(p["authority"] == "ABSTAIN" for p in packets), packets
    assert all(p["abstain_reason"] == "source_conflict" for p in packets), packets


def test_verifier_flags_cross_class_packets():
    p_a = LC.make_packet("a", "RESOURCE_GOLD", "^2", {"frozen_resource_digest": "d",
                         "rule_table_digest": "r", "engine_version": "v"},
                         sense={"sense_id": "s1", "lemma": "x", "pos": "v", "gloss": "g", "source": "T", "frame": None})
    p_b = LC.make_packet("b", "RESOURCE_GOLD", "^3", {"frozen_resource_digest": "d",
                         "rule_table_digest": "r", "engine_version": "v"},
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


# --------------------------------------------------------------------------- authority invariant
def test_model_consensus_grants_no_authority():
    rt = _rt()
    # three "models" all insist ^2; the frozen gloss deterministically fires ^6
    evidence = {"model_id": "committee", "model_role": "source_locator",
                "proposed_rule_id": "CAS-N2", "exact_gloss": "to dissect an argument into its parts"}
    p = ENG.label_sense(_sense("t.consensus", "to dissect an argument into its parts"),
                        rt, "d", evidence=evidence)
    assert p["cas_label"] == "^6", "model proposal must not change firing"
    # a MODEL_PROPOSED packet is never claim-bearing
    mp = LC.make_packet("mp", "MODEL_PROPOSED", "^2", {"frozen_resource_digest": "d",
                        "rule_table_digest": "r", "engine_version": "v"})
    assert mp["claim_bearing"] is False


def test_make_packet_enforces_invariant():
    prov = {"frozen_resource_digest": "d", "rule_table_digest": "r", "engine_version": "v"}
    for auth in ("CONSTRUCTION_GOLD", "RESOURCE_GOLD", "OWNER_CORRECTED"):
        assert LC.make_packet("x", auth, "^2", prov)["claim_bearing"] is True
    for auth in ("MODEL_PROPOSED", "WEAK_LABEL", "ABSTAIN"):
        lbl = None if auth == "ABSTAIN" else "^2"
        assert LC.make_packet("x", auth, lbl, prov)["claim_bearing"] is False
    # gold without a class is illegal
    try:
        LC.make_packet("x", "RESOURCE_GOLD", None, prov)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # abstain with a class is illegal
    try:
        LC.make_packet("x", "ABSTAIN", "^2", prov)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


# --------------------------------------------------------------------------- verifier
def test_exact_quote_verification():
    frozen = VER.FrozenResource.from_path(RES_PATH)
    d = frozen.digest
    ok = VER.verify_evidence_claim({"sense_id": "dev.v.6.002", "exact_gloss": "to dissect an argument into its parts"}, frozen, d)
    assert any(f.ok and f.check == "exact_quote" for f in ok), ok
    para = VER.verify_evidence_claim({"sense_id": "dev.v.6.002", "exact_gloss": "to  dissect an argument into its parts."}, frozen, d)
    assert any((not f.ok) and f.check == "exact_quote" for f in para), para
    invented = VER.verify_evidence_claim({"sense_id": "dev.v.6.002", "exact_gloss": "to shred an argument completely"}, frozen, d)
    assert any((not f.ok) and f.check == "exact_quote" for f in invented), invented


def test_nonexistent_sense_rejection():
    frozen = VER.FrozenResource.from_path(RES_PATH)
    r = VER.verify_evidence_claim({"sense_id": "does.not.exist"}, frozen, frozen.digest)
    assert any((not f.ok) and f.check == "sense_exists" for f in r), r


def test_protected_data_immutability():
    frozen = VER.FrozenResource.from_path(RES_PATH)
    # (a) resource digest mismatch is rejected (tampered/altered protected data)
    r = VER.verify_evidence_claim({"sense_id": "dev.v.6.002"}, frozen, "WRONG_DIGEST")
    assert any((not f.ok) and f.check == "resource_digest" for f in r), r
    # (b) any source consulted after protected results opened is rejected
    r2 = VER.verify_evidence_claim({"sense_id": "dev.v.6.002"}, frozen, frozen.digest, protected_opened=True)
    assert any((not f.ok) and f.check == "freeze_time" for f in r2), r2


def test_duplicate_sense_id_in_resource_rejected():
    try:
        VER.FrozenResource({"senses": [_sense("dupe", "g1"), _sense("dupe", "g2")]}, "d")
        raise AssertionError("expected ValueError on duplicate sense_id")
    except ValueError:
        pass


def test_ingest_guard_rejects_forged_claim_bearing():
    # a disk/model-authored packet claiming MODEL_PROPOSED is claim-bearing must be rejected
    forged = {"packet_id": "forge", "authority": "MODEL_PROPOSED", "cas_label": "^2",
              "claim_bearing": True}
    try:
        LC.validate_packet(forged)
        raise AssertionError("expected ValueError on forged claim_bearing")
    except ValueError:
        pass
    # a consistent MODEL_PROPOSED packet (claim_bearing False) passes
    good = {"packet_id": "ok", "authority": "MODEL_PROPOSED", "cas_label": "^2",
            "claim_bearing": False}
    assert LC.validate_packet(good) is good


def test_verify_packets_reports_invariant_violation():
    forged = {"packet_id": "forge", "authority": "MODEL_PROPOSED", "cas_label": "^2",
              "claim_bearing": True, "sense": None}
    findings = VER.verify_packets([forged])
    assert any((not f.ok) and f.check == "claim_bearing_invariant" for f in findings), findings


def test_load_packets_rejects_forged_file(tmp_path=None):
    import tempfile
    import os
    forged = [{"packet_id": "forge", "authority": "ABSTAIN", "cas_label": "^2",  # ABSTAIN must be null
               "claim_bearing": False}]
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
