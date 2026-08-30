"""owner_audit_queue.py -- build a BLINDED owner audit queue.

The owner does not label the whole inventory. The owner audits a small blinded sample and
approves the rules. This builds:

  - up to N (default 15) randomly-selected ACCEPTED items per CAS class
  - a sample of ABSTAIN items (so the owner sees what the engine refused)
  - hidden DUPLICATE items (the same item under a second blinded id) to measure whether the
    owner's own judgments are internally consistent -- NOT independent inter-rater validation
  - the full mapping-rule table id/digest for the owner to approve once

Two files are written:
  audit_queue.blinded.json  -- what the owner sees: shuffled, NO programmatic label, an empty
                               owner_judgment slot per item
  audit_queue.sealed.json   -- queue_id -> true programmatic label + duplicate groupings; used
                               ONLY to score after the owner has recorded judgments

score_owner_judgments() joins the two and reports owner-vs-engine disagreement and
within-owner duplicate consistency. Deterministic given the seed. CPU-only.
"""
from __future__ import annotations

import random
from pathlib import Path

import label_common as LC

HERE = Path(__file__).resolve().parent


def build_queue(packets: list[dict], rule_table_digest: str, per_class: int = 15,
                abstain_sample: int = 6, duplicates: int = 4, seed: int = 20260830):
    rng = random.Random(seed)

    accepted = [p for p in packets if p.get("authority") in ("RESOURCE_GOLD", "CONSTRUCTION_GOLD")]
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
