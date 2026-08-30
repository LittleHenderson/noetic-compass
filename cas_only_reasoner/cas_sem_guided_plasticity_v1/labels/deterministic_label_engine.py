"""deterministic_label_engine.py -- the ONLY issuer of RESOURCE_GOLD labels.

Given a frozen sense record and the owner-approved CAS_MAPPING_RULES_v1.yaml, this program
re-derives rule firing from the frozen gloss (and frame, if present) and emits exactly one of:

    RESOURCE_GOLD(class)     -- exactly one rule fired
    ABSTAIN(no_rule)         -- zero rules fired (incl. include matched but exclude blocked)
    ABSTAIN(multiple_rules)  -- two or more rules fired
    ABSTAIN(source_conflict) -- caller flagged a source disagreement for this sense

A model's proposed rule id (if any) is accepted only as advisory `evidence` and is NEVER
used to decide firing. The engine always recomputes firing from the frozen text. Model
consensus grants no authority.

CPU-only, deterministic, no network, no model calls.
"""
from __future__ import annotations

from pathlib import Path

import label_common as LC

HERE = Path(__file__).resolve().parent


class RuleTable:
    def __init__(self, rules_yaml_path):
        self.path = Path(rules_yaml_path)
        self.raw = LC.load_yaml(self.path)
        self.digest = LC.sha256_file(self.path)
        self.version = self.raw.get("version")
        self.classes = tuple(self.raw.get("classes", ()))
        self.rules = self.raw.get("rules", [])
        # index by id for provenance / verification
        self.by_id = {r["id"]: r for r in self.rules}

    def fire(self, text: str):
        """Return (fired, blocked) where:
        fired   = sorted list of (rule_id, cas_label) whose include matched AND no exclude matched
        blocked = sorted list of rule_ids whose include matched but an exclude term blocked them
        """
        ntext = LC.normalize_text(text)
        fired = []
        blocked = []
        for r in self.rules:
            inc = LC.any_term_matches(r.get("include", []), ntext)
            if not inc:
                continue
            exc = LC.any_term_matches(r.get("exclude", []), ntext)
            if exc:
                blocked.append(r["id"])
            else:
                fired.append((r["id"], r["cas_label"]))
        fired.sort()
        blocked.sort()
        return fired, blocked


def label_sense(sense: dict, rule_table: RuleTable, frozen_resource_digest: str,
                source_conflict: bool = False, evidence: dict | None = None,
                seed=None) -> dict:
    """Emit one label packet for a single frozen sense record."""
    sense_view = {
        "sense_id": sense.get("sense_id"),
        "lemma": sense.get("lemma"),
        "pos": sense.get("pos"),
        "gloss": sense.get("gloss"),
        "source": sense.get("source"),
        "frame": sense.get("frame"),
    }
    provenance = {
        "frozen_resource_digest": frozen_resource_digest,
        "rule_table_digest": rule_table.digest,
        "engine_version": LC.ENGINE_VERSION,
        "created_by": "deterministic_label_engine",
        "seed": seed,
    }
    packet_id = f"pkt::{sense.get('sense_id')}"

    # frame text participates in firing when present
    text = (sense.get("gloss") or "")
    if sense.get("frame"):
        text = text + " " + str(sense.get("frame"))

    fired, blocked = rule_table.fire(text)
    fired_ids = [fid for fid, _ in fired]

    if source_conflict:
        return LC.make_packet(packet_id, "ABSTAIN", None, provenance, sense=sense_view,
                              fired_rules=fired_ids, blocked_rules=blocked,
                              abstain_reason="source_conflict", evidence=evidence)

    if len(fired) == 1:
        rule_id, cas_label = fired[0]
        return LC.make_packet(packet_id, "RESOURCE_GOLD", cas_label, provenance, sense=sense_view,
                              fired_rules=fired_ids, blocked_rules=blocked,
                              abstain_reason=None, evidence=evidence)
    if len(fired) == 0:
        return LC.make_packet(packet_id, "ABSTAIN", None, provenance, sense=sense_view,
                              fired_rules=fired_ids, blocked_rules=blocked,
                              abstain_reason="no_rule", evidence=evidence)
    # >= 2
    return LC.make_packet(packet_id, "ABSTAIN", None, provenance, sense=sense_view,
                          fired_rules=fired_ids, blocked_rules=blocked,
                          abstain_reason="multiple_rules", evidence=evidence)


def label_resource(resource: dict, rule_table: RuleTable, frozen_resource_digest: str,
                   seed=None) -> list[dict]:
    """Label every sense in a frozen resource. Also detects cross-record source_conflict:
    if the same sense_id appears producing different resolved labels, all its packets ABSTAIN
    with source_conflict."""
    senses = resource.get("senses", [])

    # First pass: naive per-sense label
    first = [label_sense(s, rule_table, frozen_resource_digest, seed=seed) for s in senses]

    # Detect duplicate sense_id producing conflicting labels
    from collections import defaultdict
    labels_by_id = defaultdict(set)
    for p in first:
        sid = p["sense"]["sense_id"]
        if p["authority"] == "RESOURCE_GOLD":
            labels_by_id[sid].add(p["cas_label"])
    conflict_ids = {sid for sid, labs in labels_by_id.items() if len(labs) > 1}

    if not conflict_ids:
        return first

    # Second pass: force conflicting ids to source_conflict ABSTAIN
    out = []
    for s in senses:
        conflict = s.get("sense_id") in conflict_ids
        out.append(label_sense(s, rule_table, frozen_resource_digest,
                               source_conflict=conflict, seed=seed))
    return out


def load_rule_table(path=None) -> RuleTable:
    return RuleTable(path or (HERE / "CAS_MAPPING_RULES_v1.yaml"))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Deterministic CAS label engine (RESOURCE_GOLD/ABSTAIN).")
    ap.add_argument("--resource", default=str(HERE / "dev_resource" / "DEV_SENSE_RESOURCE_v1.yaml"))
    ap.add_argument("--rules", default=str(HERE / "CAS_MAPPING_RULES_v1.yaml"))
    ap.add_argument("--out", default=str(HERE / "reports" / "engine_packets.json"))
    args = ap.parse_args()

    rt = load_rule_table(args.rules)
    res = LC.load_yaml(args.resource)
    digest = LC.sha256_file(args.resource)
    packets = label_resource(res, rt, digest)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    LC.write_json(args.out, packets)
    print(f"labeled {len(packets)} senses -> {args.out}")
