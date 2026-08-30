"""run_pilot.py -- DEVELOPMENT-ONLY LABEL PHASE 0B pilot.

Runs the whole deterministic label backbone end to end on the frozen DEV surrogate resource
and the construction-gold generator, builds a blinded owner audit queue, writes a real
SOURCE_RESOURCE_MANIFEST.json (with true SHA-256 digests), and reports pilot metrics.

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

RULES_PATH = HERE / "CAS_MAPPING_RULES_v1.yaml"
RES_PATH = HERE / "dev_resource" / "DEV_SENSE_RESOURCE_v1.yaml"
REPORTS = HERE / "reports"


def write_manifest(rule_digest, res_digest):
    manifest = {
        "manifest_id": "SOURCE_RESOURCE_MANIFEST_v1",
        "note": "Frozen-resource provenance for the label pipeline. Production entries must be "
                "frozen by the owner before any claim-bearing run; the dev surrogate is pilot-only.",
        "rule_table": {"path": "labels/CAS_MAPPING_RULES_v1.yaml", "sha256": rule_digest},
        "resources": {
            "development_surrogate": {
                "resource_id": "DEV_SURROGATE_v1",
                "path": "labels/dev_resource/DEV_SENSE_RESOURCE_v1.yaml",
                "sha256": res_digest,
                "claim_bearing": False,
            },
            "production": {
                "wordnet": {"version": "3.1", "sha256": "OWNER_TO_FREEZE", "claim_bearing": True},
                "verbnet": {"version": "3.4", "sha256": "OWNER_TO_FREEZE", "claim_bearing": True},
                "framenet": {"version": "1.7", "sha256": "OWNER_TO_FREEZE", "claim_bearing": True},
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

    # Tier B: RESOURCE_GOLD / ABSTAIN over the frozen dev resource
    resource_packets = ENG.label_resource(resource, rt, res_digest)
    # Tier A: CONSTRUCTION_GOLD
    construction_packets = CG.generate(n_per_class=10)

    all_packets = resource_packets + construction_packets
    for p in all_packets:  # ingest guard: enforce claim_bearing invariant before anything downstream
        LC.validate_packet(p)
    LC.write_json(REPORTS / "resource_packets.json", resource_packets)
    LC.write_json(REPORTS / "construction_gold.json", construction_packets)
    LC.write_json(REPORTS / "all_packets.json", all_packets)

    # ---- verifier: cross-class integrity + exact-quote sanity on every accepted sense ----
    frozen = VER.FrozenResource.from_path(RES_PATH)
    cross = VER.verify_packets(resource_packets)
    quote_failures = 0
    quote_checks = 0
    for p in resource_packets:
        if p["authority"] == "RESOURCE_GOLD":
            quote_checks += 1
            fs = VER.verify_evidence_claim(
                {"sense_id": p["sense"]["sense_id"], "exact_gloss": p["sense"]["gloss"]},
                frozen, res_digest)
            if not all(f.ok for f in fs):
                quote_failures += 1
    source_verification_failure_rate = (quote_failures / quote_checks) if quote_checks else 0.0
    cross_ok = all(f.ok for f in cross)

    # ---- pilot metrics vs author-intent annotations (sanity, NOT authority) ----
    senses = resource.get("senses", [])
    by_id = {s["sense_id"]: s for s in senses}
    total = len(resource_packets)
    accepted = [p for p in resource_packets if p["authority"] == "RESOURCE_GOLD"]
    abstained = [p for p in resource_packets if p["authority"] == "ABSTAIN"]

    per_rule_error_counts = {}
    accepted_class_mismatch = 0
    decoy_should_abstain_but_accepted = 0
    abstain_reason_mismatch = 0
    for p in resource_packets:
        sid = p["sense"]["sense_id"]
        exp = by_id.get(sid, {})
        exp_auth = exp.get("expected_authority")
        exp_cls = exp.get("expected_class")
        exp_reason = exp.get("expected_reason")
        if p["authority"] == "RESOURCE_GOLD":
            rule = p["fired_rules"][0] if p["fired_rules"] else "?"
            per_rule_error_counts.setdefault(rule, {"accepted": 0, "class_mismatch": 0})
            per_rule_error_counts[rule]["accepted"] += 1
            if exp_auth == "RESOURCE_GOLD" and exp_cls != p["cas_label"]:
                per_rule_error_counts[rule]["class_mismatch"] += 1
                accepted_class_mismatch += 1
            if exp_auth == "ABSTAIN":
                decoy_should_abstain_but_accepted += 1
        else:  # ABSTAIN
            if exp_auth == "ABSTAIN" and exp_reason and exp_reason != p["abstain_reason"]:
                abstain_reason_mismatch += 1

    # ---- owner audit queue ----
    blinded, sealed, qmeta = AQ.build_queue(all_packets, rt.digest, per_class=15)
    LC.write_json(REPORTS / "audit_queue.blinded.json", blinded)
    LC.write_json(REPORTS / "audit_queue.sealed.json", sealed)
    LC.write_json(REPORTS / "audit_queue.meta.json", qmeta)

    coverage = len(accepted) / total if total else 0.0
    abstention_rate = len(abstained) / total if total else 0.0

    report = {
        "pilot_id": "LABEL_PHASE_0B_DEV_PILOT",
        "claim_bearing": False,
        "status": "DEVELOPMENT_ONLY",
        "digests": {"rule_table": rt.digest, "dev_resource": res_digest},
        "counts": {
            "resource_senses": total,
            "resource_accepted_resource_gold": len(accepted),
            "resource_abstained": len(abstained),
            "construction_gold": len(construction_packets),
            "all_packets": len(all_packets),
        },
        "metrics": {
            "automatic_label_coverage_resource": round(coverage, 4),
            "abstention_rate_resource": round(abstention_rate, 4),
            "source_verification_failure_rate": round(source_verification_failure_rate, 4),
            "cross_class_integrity_ok": cross_ok,
            "model_committee_disagreement_rate": "not_exercised_in_dev_pilot (no live model committee; engine is authority)",
            "owner_audit_disagreement_rate": "pending_owner_judgment",
            "duplicate_item_consistency": "pending_owner_judgment",
        },
        "self_consistency_vs_author_intent": {
            "note": "compares engine output to the resource's expected_* annotations; a sanity check only, NOT label authority",
            "accepted_class_mismatch": accepted_class_mismatch,
            "decoy_should_abstain_but_accepted": decoy_should_abstain_but_accepted,
            "abstain_reason_mismatch": abstain_reason_mismatch,
            "per_rule_error_counts": per_rule_error_counts,
        },
        "projected_human_workload": {
            "owner_audit_queue_items": qmeta["counts"]["queue_size"],
            "mapping_rules_to_approve": len(rt.rules),
            "hidden_duplicates": qmeta["counts"]["hidden_duplicates"],
            "note": "single-owner audit; NOT independent human inter-rater validation",
        },
        "manifest": manifest,
    }
    LC.write_json(REPORTS / "PILOT_REPORT.json", report)

    # human-readable
    md = _render_md(report)
    (REPORTS / "PILOT_REPORT.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def _render_md(r):
    m = r["metrics"]
    c = r["counts"]
    sc = r["self_consistency_vs_author_intent"]
    w = r["projected_human_workload"]
    lines = [
        "# LABEL PHASE 0B -- DEVELOPMENT-ONLY PILOT REPORT",
        "",
        "Status: **DEVELOPMENT_ONLY, not claim-bearing.** No neural probe, no hidden-state",
        "extraction, no protected evaluation, no model calls, no GPU. Deterministic.",
        "",
        f"- rule table sha256: `{r['digests']['rule_table']}`",
        f"- dev resource sha256: `{r['digests']['dev_resource']}`",
        "",
        "## Counts",
        f"- resource senses: {c['resource_senses']}",
        f"- accepted RESOURCE_GOLD: {c['resource_accepted_resource_gold']}",
        f"- abstained: {c['resource_abstained']}",
        f"- construction gold (Tier A): {c['construction_gold']}",
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
        "## Self-consistency vs author intent (sanity only, NOT authority)",
        f"- accepted class mismatch: {sc['accepted_class_mismatch']}",
        f"- decoy accepted instead of abstaining: {sc['decoy_should_abstain_but_accepted']}",
        f"- abstain-reason mismatch: {sc['abstain_reason_mismatch']}",
        f"- per-rule: {sc['per_rule_error_counts']}",
        "",
        "## Projected human workload",
        f"- owner audit queue items: {w['owner_audit_queue_items']}",
        f"- mapping rules to approve: {w['mapping_rules_to_approve']}",
        f"- hidden duplicates: {w['hidden_duplicates']}",
        f"- {w['note']}",
        "",
        "## Boundary",
        "This pilot demonstrates the deterministic label BACKBONE only. It establishes no CAS",
        "claim. The claim-bearing readout study is NOT begun. Awaiting owner approval of the",
        "four CAS class rules, the frozen production resource, and a signed phase-0 record.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
