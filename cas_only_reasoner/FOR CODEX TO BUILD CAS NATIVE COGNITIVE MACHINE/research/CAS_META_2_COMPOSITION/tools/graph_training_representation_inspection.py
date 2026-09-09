"""Pure token-structure inspection for the representation follow-up review.

No torch, no GPU, no AWS, no sealed splits. Uses the SAME training/practice
records, public-record contract, and real tokenizer as the AWS worker, and
measures at the token-id level what the owner's review asked:

  1. per-option token counts (with duplicates) and distinct-token counts —
     the sum-pooled vector is count x mean, so a pure count signal would
     show up here;
  2. how much of each option is shared with the other two options (the
     common component) vs unique to it (the content component);
  3. same-length, different-content option pairs — does the learner receive
     meaningfully different representations when token counts match?
  4. problem-side sensitivity: when one connector's commonality (or one
     node's contents) changes, is that change present in the problem token
     sequence, and at what dilution (1 / problem-token-count)?

Usage: python tools/graph_training_representation_inspection.py <evidence_dir>
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

from cas_meta2.graph_teaching import adapter, lessons, trainer
from cas_meta2.features_v2 import LosslessPublicTokenizer


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    evidence = Path(argv[0] if argv else "records/representation_inspection_001")
    evidence.mkdir(parents=True, exist_ok=True)

    records = trainer.training_records(20260909)  # train + practice ONLY
    publics = [adapter.public_records(record, arm)["public"]
               for record in records for arm in ("cas", "generic")]
    tokenizer = LosslessPublicTokenizer.fit_train(list(publics), max_length=1024)

    rows = []
    for record in records:
        for arm in ("cas", "generic"):
            public = adapter.public_records(record, arm)["public"]
            encoded = tokenizer.encode_public(public)
            problem_ids = [token_id for token_id, kind in
                           zip(encoded["ids"], encoded["kinds"]) if kind == 0]
            slot_ids = {slot: [] for slot in (0, 1, 2)}
            for token_id, kind, slot in zip(encoded["ids"], encoded["kinds"],
                                            encoded["slots"]):
                if kind == 2 and slot in (1, 2, 3):
                    slot_ids[slot - 1].append(token_id)
            sequences = [slot_ids[slot] for slot in (0, 1, 2)]
            distinct = [set(sequence) for sequence in sequences]
            counts = [len(sequence) for sequence in sequences]
            shared_all = set.intersection(*distinct) if all(distinct) else set()
            unique = [item - set.union(*(other for j, other in enumerate(distinct)
                                          if j != i), set())
                      for i, item in enumerate(distinct)]
            same_length_pairs = []
            for i in range(3):
                for j in range(i + 1, 3):
                    if counts[i] == counts[j] and distinct[i] != distinct[j]:
                        same_length_pairs.append({
                            "slots": [i, j], "token_count": counts[i],
                            "symmetric_difference": len(distinct[i] ^ distinct[j]),
                            "distinct_counts": [len(distinct[i]), len(distinct[j])]})
            problem_set = set(problem_ids)
            rows.append({
                "record_id": record["record_id"], "arm": arm, "op": record["op"],
                "option_token_counts": counts,
                "option_distinct_counts": [len(item) for item in distinct],
                "length_spread": max(counts) - min(counts),
                "distinct_spread": max(len(item) for item in distinct)
                                   - min(len(item) for item in distinct),
                "shared_by_all_three": sorted(shared_all),
                "unique_to_each": [sorted(item) for item in unique],
                "same_length_different_content_pairs": same_length_pairs,
                "problem_token_count": len(problem_ids),
                "problem_distinct_count": len(problem_set),
                "problem_shared_with_options": len(problem_set & set.union(*distinct)),
            })

    def median(values):
        return statistics.median(values) if values else None

    per_op = {}
    for op in sorted({row["op"] for row in rows}):
        subset = [row for row in rows if row["op"] == op]
        lengths = [row["option_token_counts"] for row in subset]
        per_op[op] = {
            "records": len(subset),
            "all_three_equal_length": sum(1 for counts in lengths
                                          if counts[0] == counts[1] == counts[2]),
            "median_length_spread": median([row["length_spread"] for row in subset]),
            "median_distinct_spread": median([row["distinct_spread"] for row in subset]),
            "option_token_count_range": [min(min(counts) for counts in lengths),
                                         max(max(counts) for counts in lengths)],
            "same_length_different_content_pairs_total":
                sum(len(row["same_length_different_content_pairs"]) for row in subset),
            "median_unique_tokens_per_option":
                median([len(item) for row in subset for item in row["unique_to_each"]]),
            "median_shared_all_three":
                median([len(row["shared_by_all_three"]) for row in subset]),
            "median_problem_token_count": median([row["problem_token_count"] for row in subset]),
        }

    # Problem-side sensitivity: connector-retarget and node-contents edits
    # on a few LIST_PARPS training records (synthetic but GRAPH-VALID edits;
    # no answers used).
    sensitivity = []
    for record in [row for row in records if row["op"] == "LIST_PARTS"][:3]:
        baseline = adapter.encode_graph(record["graph"])
        for edit_kind in ("connector_retarget", "node_contents"):
            edited = json.loads(json.dumps(record["graph"]))
            if edit_kind == "connector_retarget":
                contains = [relation for relation in edited["relations"]
                            if relation["kind"] == "contains"]
                source = contains[0]["source"]
                taken = {relation["target"] for relation in contains}
                other = next(node["identifier"] for node in edited["nodes"]
                             if node["identifier"] != source
                             and node["identifier"] not in taken)
                contains[0]["target"] = other
                contains[0]["content"] = ["constituent", other]
            else:
                edited["nodes"][0]["fields"].append(["edited", "marker"])
            changed = adapter.encode_graph(edited)
            added = Counter(changed) - Counter(baseline)
            removed = Counter(baseline) - Counter(changed)
            sensitivity.append({
                "record_id": record["record_id"], "edit": edit_kind,
                "problem_tokens_before": len(baseline),
                "problem_tokens_after": len(changed),
                "tokens_added": dict(added), "tokens_removed": dict(removed),
                "change_present": bool(added or removed)})

    # Decoded samples: one record per op (cas arm) — tags and the actual
    # token sequences the option vectors are built from.
    vocabulary = tokenizer.vocabulary
    samples = []
    for op in ("LIST_PARTS", "FIND_SHARED_PART", "REACHED_VIA"):
        record = next(row for row in records if row["op"] == op)
        public = adapter.public_records(record, "cas")["public"]
        encoded = tokenizer.encode_public(public)
        slot_tokens = {slot: [] for slot in (1, 2, 3)}
        for token_id, kind, slot in zip(encoded["ids"], encoded["kinds"],
                                        encoded["slots"]):
            if kind == 2 and slot in (1, 2, 3):
                slot_tokens[slot].append(vocabulary[token_id])
        samples.append({
            "op": op, "record_id": record["record_id"],
            "option_tags": [item["tag"] for item in public["observations"]],
            "option_token_sequences": [slot_tokens[slot] for slot in (1, 2, 3)]})

    document = {"schema": "cas-graph-training-representation-inspection/1",
                "boundary": ("pure token-id inspection over train+practice records only; "
                             "no sealed splits, no answers consulted for correction design, "
                             "no torch, no GPU"),
                "records": len(rows), "arms": ["cas", "generic"],
                "per_op": per_op, "sensitivity": sensitivity,
                "samples": samples,
                "same_length_different_content_pairs_total":
                    sum(len(row["same_length_different_content_pairs"]) for row in rows),
                "length_spread_median_all": median([row["length_spread"] for row in rows]),
                "records_with_equal_length_options":
                    sum(1 for row in rows
                        if row["option_token_counts"][0] == row["option_token_counts"][1]
                        == row["option_token_counts"][2])}
    raw = (json.dumps(document, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    (evidence / "inspection.json").write_bytes(raw)
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
