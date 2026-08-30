"""run_pilot.py -- DEVELOPMENT-ONLY pipeline fixture run (Phase 0C authority model).

Runs the deterministic label backbone end to end on the frozen DEV surrogate resource and
the retired template-fixture generator, builds a DEV_AUDIT_FIXTURE_ONLY queue, writes a
real SOURCE_RESOURCE_MANIFEST.json (with true SHA-256 digests), and reports fixture metrics.

STATUS OF THIS RUN: SYNTHETIC_PIPELINE_FIXTURE_PASS. The 46-sense dev resource was authored
by the same agent that wrote the keyword rules, specifically to exercise them. Agreement
between the fixtures and the rules therefore proves ONLY that the software behaves as
written. It is NOT evidence that the rules map real word senses into CAS correctly.

Every packet this pilot produces is NON-claim-bearing (candidate/fixture/abstain
authorities). The pilot asserts claim_bearing_packet_count == 0 and fails if any packet
claims otherwise.

NO neural probe. NO hidden-state extraction. NO protected evaluation. NO model calls. NO GPU.
CPU-only, deterministic. Not claim-bearing.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import label_common as LC          # noqa: E402
import deterministic_label_engine as ENG  # noqa: E402
import label_source_verifier as VER       # noqa: E402
import construction_gold_generator as CG  # noqa: E402
import owner_audit_queue as AQ            # noqa: E402

RULES_PATH = HERE / "CAS_MAPPING_RULES_v1_CANDIDATE.yaml"
RES_PATH = HERE / "dev_resource" / "DEV_SENSE_RESOURCE_v1.yaml"
REPORTS = HERE / "reports"


def write_manifest(rule_digest, res_digest):
    manifest = {
        "manifest_id": "SOURCE_RESOURCE_MANIFEST_v1",
        "note": "Frozen-resource provenance for the label pipeline. Production entries must be "
                "frozen by the owner before any claim-bearing run; the dev surrogate is pilot-only.",
        "rule_table": {"path": "labels/CAS_MAPPING_RULES_v1_CANDIDATE.yaml", "sha256": rule_digest,
                       "status": "AWAITING_OWNER_APPROVAL"},
        "resources": {
            "development_surrogate": {
                "resource_id": "DEV_SURROGATE_v1",
                "path": "labels/dev_resource/DEV_SENSE_RESOURCE_v1.yaml",
                "sha256": res_digest,
                "claim_bearing_eligible": False,
            },
            "production": {
                "note": "claim_bearing_eligible means eligible ONCE the owner freezes a real digest; "
                        "promotion refuses any entry whose sha256 is still OWNER_TO_FREEZE.",
                "wordnet": {"version": "3.1", "sha256": "OWNER_TO_FREEZE", "claim_bearing_eligible": True},
                "verbnet": {"version": "3.4", "sha256": "OWNER_TO_FREEZE", "claim_bearing_eligible": True},
                "framenet": {"version": "1.7", "sha256": "OWNER_TO_FREEZE", "claim_bearing_eligible": True},
            },
        },
        "protected_opened": False,
    }
    LC.write_json(REPORTS / "SOURCE_RESOURCE_MANIFEST.json", manifest)
    # also place a copy at the labels/ root (owner listed it as a top-level deliverable)
    LC.write_json(HERE / "SOURCE_RESOURCE_MANIFEST.json", manifest)
    return manifest


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    rt = ENG.load_rule_table(RULES_PATH)
    resource = LC.load_yaml(RES_PATH)
    res_digest = LC.sha256_file(RES_PATH)

    manifest = write_manifest(rt.digest, res_digest)

    # candidate labels over the frozen dev resource (RESOURCE_RULE_DERIVED / ABSTAIN)
    resource_packets = ENG.label_resource(resource, rt, res_digest)
    # retired circular generator -> CONTROLLED_TEMPLATE_FIXTURE (pipeline fixtures only)
    fixture_packets = CG.generate(n_per_class=10)

    all_packets = resource_packets + fixture_packets
    for p in all_packets:  # ingest guard: enforce claim_bearing invariant before anything downstream
        LC.validate_packet(p)

    # HARD ASSERTION: this pilot may not contain a single claim-bearing packet
    claim_bearing_count = sum(1 for p in all_packets if p.get("claim_bearing"))
    if claim_bearing_count != 0:
        raise RuntimeError(f"pilot produced {claim_bearing_count} claim-bearing packets; must be 0")

    LC.write_json(REPORTS / "resource_packets.json", resource_packets)
    LC.write_json(REPORTS / "template_fixtures.json", fixture_packets)
    LC.write_json(REPORTS / "all_packets.json", all_packets)

    # ---- verifier plumbing check: cross-class integrity + full-schema evidence claims ----
    frozen = VER.FrozenResource.from_path(RES_PATH)
    cross = VER.verify_packets(resource_packets)
    rule_ids = list(rt.by_id.keys())
    quote_failures = 0
    quote_checks = 0
    for p in resource_packets:
        if p["authority"] == "RESOURCE_RULE_DERIVED":
            quote_checks += 1
            sid = p["sense"]["sense_id"]
            claim = {
                "sense_id": sid,
                "source_locator": f"{frozen.resource_id}#{sid}",
                "exact_gloss": p["sense"]["gloss"],
                "source_frame_id": p["sense"]["frame"],
                "proposed_cas_class": p["cas_label"],
                "proposed_rule_id": p["fired_rules"][0] if p["fired_rules"] else "NONE",
                "model_id": "pilot_deterministic_selfcheck",
                "model_revision": "n/a-fixture",
                "model_role": "source_locator",
                "evidence_timestamp": "2026-08-30T00:00:00Z",
                "resource_digest": res_digest,
            }
            fs = VER.verify_evidence_claim(claim, frozen, res_digest, rule_ids=rule_ids)
            if not all(f.ok for f in fs):
                quote_failures += 1
    source_verification_failure_rate = (quote_failures / quote_checks) if quote_checks else 0.0
    cross_ok = all(f.ok for f in cross)

    # ---- development-fixture consistency check (NOT scientific evidence) ----
    senses = resource.get("senses", [])
    by_id = {s["sense_id"]: s for s in senses}
    total = len(resource_packets)
    accepted = [p for p in resource_packets if p["authority"] == "RESOURCE_RULE_DERIVED"]
    abstained = [p for p in resource_packets if p["authority"] == "ABSTAIN"]

    per_rule_counts = {}
    accepted_class_mismatch = 0
    decoy_should_abstain_but_accepted = 0
    abstain_reason_mismatch = 0
    for p in resource_packets:
        sid = p["sense"]["sense_id"]
        exp = by_id.get(sid, {})
        exp_auth = exp.get("expected_authority")
        exp_cls = exp.get("expected_class")
        exp_reason = exp.get("expected_reason")
        if p["authority"] == "RESOURCE_RULE_DERIVED":
            rule = p["fired_rules"][0] if p["fired_rules"] else "?"
            per_rule_counts.setdefault(rule, {"accepted": 0, "class_mismatch": 0})
            per_rule_counts[rule]["accepted"] += 1
            if exp_auth == "RESOURCE_RULE_DERIVED" and exp_cls != p["cas_label"]:
                per_rule_counts[rule]["class_mismatch"] += 1
                accepted_class_mismatch += 1
            if exp_auth == "ABSTAIN":
                decoy_should_abstain_but_accepted += 1
        else:  # ABSTAIN
            if exp_auth == "ABSTAIN" and exp_reason and exp_reason != p["abstain_reason"]:
                abstain_reason_mismatch += 1

    # ---- dev audit fixture queue (NOT for owner judgment) ----
    blinded, sealed, qmeta = AQ.build_queue(all_packets, rt.digest, per_class=15,
                                            queue_status="DEV_AUDIT_FIXTURE_ONLY")
    LC.write_json(REPORTS / "audit_queue.blinded.json", blinded)
    LC.write_json(REPORTS / "audit_queue.sealed.json", sealed)
    LC.write_json(REPORTS / "audit_queue.meta.json", qmeta)

    coverage = len(accepted) / total if total else 0.0
    abstention_rate = len(abstained) / total if total else 0.0

    report = {
        "pilot_id": "LABEL_PHASE_0C_DEV_PILOT",
        "status": "SYNTHETIC_PIPELINE_FIXTURE_PASS",
        "claim_bearing": False,
        "claim_bearing_packet_count": claim_bearing_count,
        "scope_note": "Software-behavior fixture run ONLY. The dev senses were authored to exercise "
                      "the candidate keyword rules; agreement with them is not semantic validation.",
        "digests": {"rule_table": rt.digest, "dev_resource": res_digest},
        "counts": {
            "resource_senses": total,
            "resource_rule_derived": len(accepted),
            "resource_abstained": len(abstained),
            "controlled_template_fixtures": len(fixture_packets),
            "all_packets": len(all_packets),
        },
        "metrics": {
            "automatic_label_coverage_resource": round(coverage, 4),
            "abstention_rate_resource": round(abstention_rate, 4),
            "source_verification_failure_rate": round(source_verification_failure_rate, 4),
            "cross_class_integrity_ok": cross_ok,
            "model_committee_disagreement_rate": "not_exercised_in_dev_pilot (no live model committee; engine emits candidates only)",
            "owner_audit_disagreement_rate": "not_applicable (queue is DEV_AUDIT_FIXTURE_ONLY; owner not asked to judge it)",
            "duplicate_item_consistency": "not_applicable (queue is DEV_AUDIT_FIXTURE_ONLY)",
        },
        "development_fixture_checks": {
            "note": "Development-fixture check ONLY. Agreement with the author of synthetic fixtures "
                    "is NOT independent validity evidence and is EXCLUDED from scientific reporting.",
            "accepted_class_mismatch": accepted_class_mismatch,
            "decoy_should_abstain_but_accepted": decoy_should_abstain_but_accepted,
            "abstain_reason_mismatch": abstain_reason_mismatch,
            "per_rule_counts": per_rule_counts,
        },
        "projected_human_workload": {
            "note": "production audit is risk-based (~48 visible judgments + high-risk items), per "
                    "OWNER_AUDIT_PROTOCOL.md; the dev queue below is a fixture, not owner work",
            "dev_fixture_queue_items": qmeta["counts"]["queue_size"],
            "mapping_rules_to_approve": len(rt.rules),
            "disclaimer": "single-owner audit; NOT independent human inter-rater validation",
        },
        "manifest": manifest,
    }
    LC.write_json(REPORTS / "PILOT_REPORT.json", report)

    md = _render_md(report)
    (REPORTS / "PILOT_REPORT.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def _render_md(r):
    m = r["metrics"]
    c = r["counts"]
    fx = r["development_fixture_checks"]
    w = r["projected_human_workload"]
    lines = [
        "# LABEL PHASE 0C -- DEVELOPMENT-ONLY PIPELINE FIXTURE REPORT",
        "",
        "Status: **SYNTHETIC_PIPELINE_FIXTURE_PASS -- software behavior only, not claim-bearing.**",
        "No neural probe, no hidden-state extraction, no protected evaluation, no model calls,",
        "no GPU. Deterministic. The dev senses were authored to exercise the candidate rules,",
        "so agreement here validates the SOFTWARE, not the rules' semantics.",
        "",
        f"- claim-bearing packet count: **{r['claim_bearing_packet_count']}** (asserted zero)",
        f"- rule table (CANDIDATE, awaiting owner approval) sha256: `{r['digests']['rule_table']}`",
        f"- dev resource sha256: `{r['digests']['dev_resource']}`",
        "",
        "## Counts",
        f"- resource senses: {c['resource_senses']}",
        f"- RESOURCE_RULE_DERIVED (candidate, non-claim-bearing): {c['resource_rule_derived']}",
        f"- abstained: {c['resource_abstained']}",
        f"- controlled template fixtures (retired generator): {c['controlled_template_fixtures']}",
        f"- all packets: {c['all_packets']}",
        "",
        "## Metrics",
        f"- automatic-label coverage (resource): {m['automatic_label_coverage_resource']}",
        f"- abstention rate (resource): {m['abstention_rate_resource']}",
        f"- source-verification failure rate: {m['source_verification_failure_rate']}",
        f"- cross-class integrity ok: {m['cross_class_integrity_ok']}",
        f"- model-committee disagreement rate: {m['model_committee_disagreement_rate']}",
        f"- owner-audit disagreement rate: {m['owner_audit_disagreement_rate']}",
        f"- duplicate-item consistency: {m['duplicate_item_consistency']}",
        "",
        "## Development-fixture checks (NOT scientific evidence)",
        f"- {fx['note']}",
        f"- accepted class mismatch: {fx['accepted_class_mismatch']}",
        f"- decoy accepted instead of abstaining: {fx['decoy_should_abstain_but_accepted']}",
        f"- abstain-reason mismatch: {fx['abstain_reason_mismatch']}",
        f"- per-rule: {fx['per_rule_counts']}",
        "",
        "## Owner workload",
        f"- {w['note']}",
        f"- dev fixture queue items (do NOT judge): {w['dev_fixture_queue_items']}",
        f"- mapping rules to approve: {w['mapping_rules_to_approve']}",
        f"- {w['disclaimer']}",
        "",
        "## Boundary",
        "This run demonstrates the deterministic label BACKBONE only. Zero packets are",
        "claim-bearing. Gold labels can only be created by owner_gated_promotion.py with an",
        "owner-signed approval, an audit receipt, and matching digests. The claim-bearing",
        "readout study is NOT begun.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
