"""owner_audit_queue.py -- build a BLINDED owner audit queue.

PHASE 0C STATUS: the queue built from the current DEV pilot is DEV_AUDIT_FIXTURE_ONLY.
It mixes synthetic decoys (adoredissect, dreadevoke), dev-surrogate senses authored to
exercise the keyword rules, and circular template fixtures. The owner must NOT be asked to
judge it -- it tests the development pipeline, not a production dataset.

The PRODUCTION audit (specified in OWNER_AUDIT_PROTOCOL.md, built by build_production_queue
once a real frozen resource exists) is risk-based:

  - every mapping rule reviewed once;
  - 8 randomly selected real RESOURCE_RULE_DERIVED items per class (32 items);
  - ALL high-risk model disagreements (variable count);
  - 8 ABSTAIN boundary cases;
  - 8 hidden duplicates (within-owner consistency);
  - labels hidden until the judgment is committed.

Sequential gate on the audited sample (owner_gated_promotion.audit_gate_outcome):
  0 major errors -> PASS (rule table may proceed to the controlled pilot);
  1-2            -> REPAIR_AND_RESAMPLE (repair rules, regenerate, audit a fresh sample);
  3+             -> REJECT (rule table redesigned).

Two files are written:
  audit_queue.blinded.json  -- what the owner sees: shuffled, NO programmatic label, an empty
                               owner_judgment slot per item
  audit_queue.sealed.json   -- queue_id -> true programmatic label + duplicate groupings; used
                               ONLY to score after the owner has recorded judgments

score_owner_judgments() joins the two and reports owner-vs-engine disagreement and
within-owner duplicate consistency. Every report carries the disclaimer: single-owner audit;
NOT independent human inter-rater validation. Deterministic given the seed. CPU-only.
"""
from __future__ import annotations

import random
from pathlib import Path

import label_common as LC

HERE = Path(__file__).resolve().parent


ACCEPTED_AUTHORITIES = (
    "RESOURCE_RULE_DERIVED", "CONSTRUCTION_CANDIDATE", "CONTROLLED_TEMPLATE_FIXTURE",
    "RESOURCE_GOLD", "CONSTRUCTION_GOLD",
)


def build_queue(packets: list[dict], rule_table_digest: str, per_class: int = 15,
                abstain_sample: int = 6, duplicates: int = 4, seed: int = 20260830,
                queue_status: str = "DEV_AUDIT_FIXTURE_ONLY"):
    rng = random.Random(seed)

    accepted = [p for p in packets if p.get("authority") in ACCEPTED_AUTHORITIES]
    abstains = [p for p in packets if p.get("authority") == "ABSTAIN"]

    # sample accepted per class
    by_class = {c: [] for c in LC.CAS_CLASSES}
    for p in accepted:
        by_class.setdefault(p["cas_label"], []).append(p)
    chosen = []
    for c in LC.CAS_CLASSES:
        pool = list(by_class.get(c, []))
        rng.shuffle(pool)
        take = pool[: min(per_class, len(pool))]
        chosen.extend(take)

    # sample abstains
    ab_pool = list(abstains)
    rng.shuffle(ab_pool)
    chosen_abstain = ab_pool[: min(abstain_sample, len(ab_pool))]

    base_items = chosen + chosen_abstain

    # hidden duplicates: re-add a few chosen items as separate entries
    dup_pool = list(chosen)
    rng.shuffle(dup_pool)
    dup_items = dup_pool[: min(duplicates, len(dup_pool))]

    # assemble entries (each carries an internal ref to its source packet)
    entries = []
    for p in base_items:
        entries.append({"src": p, "dup_group": None})
    dup_group_id = 0
    for p in dup_items:
        dup_group_id += 1
        # tag the original(s) and the duplicate with the same group id
        for e in entries:
            if e["src"] is p:
                e["dup_group"] = dup_group_id
        entries.append({"src": p, "dup_group": dup_group_id})

    # shuffle final order and assign blinded ids
    rng.shuffle(entries)

    blinded = []
    sealed = {}
    for i, e in enumerate(entries):
        p = e["src"]
        qid = f"q{i:04d}"
        display_text = None
        if p.get("surface"):
            display_text = p["surface"]["sentence"]
        elif p.get("sense"):
            display_text = p["sense"]["gloss"]
        blinded.append({
            "queue_id": qid,
            "lemma": (p.get("sense") or {}).get("lemma"),
            "text": display_text,
            "question": "Which CAS class fits this sense-in-context? one of ^2 / ^3 / ^6 / ^8 / ABSTAIN",
            "owner_judgment": None,
        })
        sealed[qid] = {
            "engine_authority": p.get("authority"),
            "engine_label": p.get("cas_label"),
            "abstain_reason": p.get("abstain_reason"),
            "dup_group": e["dup_group"],
        }

    meta = {
        "queue_status": queue_status,
        "owner_action_required": (queue_status != "DEV_AUDIT_FIXTURE_ONLY"),
        "note": ("development-pipeline fixture queue; do NOT ask the owner to judge it"
                 if queue_status == "DEV_AUDIT_FIXTURE_ONLY" else
                 "production risk-based audit queue"),
        "seed": seed,
        "rule_table_digest": rule_table_digest,
        "counts": {
            "accepted_available": len(accepted),
            "abstain_available": len(abstains),
            "per_class_target": per_class,
            "queue_size": len(blinded),
            "hidden_duplicates": len(dup_items),
        },
        "disclaimer": "single-owner audit; NOT independent human inter-rater validation",
    }
    return blinded, sealed, meta


def build_production_queue(packets: list[dict], rule_table_digest: str,
                           high_risk_packets: list[dict] | None = None,
                           seed: int = 20260830):
    """The PRODUCTION risk-based audit: 8 accepted/class + all high-risk model disagreements
    + 8 ABSTAIN boundary cases + 8 hidden duplicates. ~48 visible judgments plus high-risk.

    high_risk_packets: items flagged by model disagreement or source-verification concern;
    ALL of them enter the queue (never sampled away).
    """
    blinded, sealed, meta = build_queue(
        packets, rule_table_digest, per_class=8, abstain_sample=8, duplicates=8,
        seed=seed, queue_status="PRODUCTION_RISK_BASED")
    if high_risk_packets:
        start = len(blinded)
        for j, p in enumerate(high_risk_packets):
            qid = f"hr{start + j:04d}"
            display_text = None
            if p.get("surface"):
                display_text = p["surface"]["sentence"]
            elif p.get("sense"):
                display_text = p["sense"]["gloss"]
            blinded.append({
                "queue_id": qid,
                "lemma": (p.get("sense") or {}).get("lemma"),
                "text": display_text,
                "question": "Which CAS class fits this sense-in-context? one of ^2 / ^3 / ^6 / ^8 / ABSTAIN",
                "owner_judgment": None,
            })
            sealed[qid] = {
                "engine_authority": p.get("authority"),
                "engine_label": p.get("cas_label"),
                "abstain_reason": p.get("abstain_reason"),
                "dup_group": None,
                "high_risk": True,
            }
        meta["counts"]["high_risk_items"] = len(high_risk_packets)
        meta["counts"]["queue_size"] = len(blinded)
    return blinded, sealed, meta


def score_owner_judgments(blinded: list[dict], sealed: dict):
    """After the owner fills owner_judgment, compute disagreement + duplicate consistency."""
    judged = [b for b in blinded if b.get("owner_judgment")]
    disagreements = []
    for b in judged:
        s = sealed.get(b["queue_id"], {})
        engine = s.get("engine_label") if s.get("engine_authority") != "ABSTAIN" else "ABSTAIN"
        owner = b["owner_judgment"]
        if owner != engine:
            disagreements.append({"queue_id": b["queue_id"], "owner": owner, "engine": engine})

    # duplicate consistency: same dup_group -> owner should give the same judgment
    groups = {}
    for b in judged:
        s = sealed.get(b["queue_id"], {})
        g = s.get("dup_group")
        if g is not None:
            groups.setdefault(g, []).append(b["owner_judgment"])
    inconsistent = {g: v for g, v in groups.items() if len(set(v)) > 1}

    return {
        "n_judged": len(judged),
        "n_disagreements": len(disagreements),
        "disagreements": disagreements,
        "duplicate_groups_checked": len(groups),
        "duplicate_inconsistent": len(inconsistent),
        "owner_engine_agreement_rate": (1 - len(disagreements) / len(judged)) if judged else None,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Build a blinded owner audit queue.")
    ap.add_argument("--packets", default=str(HERE / "reports" / "all_packets.json"))
    ap.add_argument("--outdir", default=str(HERE / "reports"))
    ap.add_argument("--per-class", type=int, default=15)
    args = ap.parse_args()
    packets = LC.load_packets(args.packets)  # ingest guard: enforce claim_bearing invariant on load
    blinded, sealed, meta = build_queue(packets, rule_table_digest="see-manifest", per_class=args.per_class)
    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    LC.write_json(Path(args.outdir) / "audit_queue.blinded.json", blinded)
    LC.write_json(Path(args.outdir) / "audit_queue.sealed.json", sealed)
    LC.write_json(Path(args.outdir) / "audit_queue.meta.json", meta)
    print(f"audit queue: {meta['counts']}")
