#!/usr/bin/env python3
"""CURRICULUM_002: read-only factual review of the RETAINED GRAPH6 errors.

What this script does (nothing else):
  1. reads the sealed confirmation result packet
     (``graph6_confirmation_result.json``) and joins its retained fresh-panel
     predictions to the deterministic fresh panel by ``record_id``;
  2. classifies every WRONG fresh prediction into one declared category per
     operation, using set comparisons against the panel record's ``correct``
     field only;
  3. verifies that the correct answer was present among the three options and
     reports the encoded position of the correct option (panel vs teaching);
  4. compares teaching coverage (30 whole-part records, seed 20260909) with
     fresh-panel coverage (90 cases, panel_seed 20260920) from the deterministic
     generators only;
  5. lists what CANNOT be recovered from the saved records.

Boundaries: pure Python; no torch import at module level and no torch use at
all; no training; no network; no GPU; no writes except the requested
``--output`` / ``--markdown`` paths; nothing cached across runs; every number is
a deterministic function of the frozen generators plus the stored packet.

No causal claim is made anywhere. The report states counts, distributions, and
verified/unavailable fields.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:                      # runnable from any cwd
    sys.path.insert(0, str(ROOT))

from cas_meta2.features_v2 import (UNIT_RULE, WORD_START,   # noqa: E402
                                   LosslessPublicTokenizer)
from cas_meta2.graph_teaching import (adapter, fresh_panel,  # noqa: E402
                                      lessons, reference, trainer)
from cas_meta2.graph_teaching.graph import (Graph, canonical,  # noqa: E402
                                            digest)

SCHEMA = "cas-meta2-curriculum-002-error-review/1"
PACKET_PATH = ROOT / (
    "records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/"
    "receipt_cas-meta2-graph6conf-20260910023000-a387d882/"
    "graph6_confirmation_result.json")
TEACHING_SEED = 20260909
ARM = "cas"                     # the arm the frozen encoder was fitted on
MAX_LENGTH = 1024               # FROZEN_ENCODER_MAX_LENGTH
PAD = "none_of_the_above"
OPS = ("LIST_PARTS", "FIND_SHARED_PART", "REACHED_VIA")
PHASES = ("before", "after")
LIST_PARTS_CATEGORIES = ("missing_part", "extra_part", "mixed_missing_and_extra",
                         "wrong_whole", "padding_choice", "other")
FIND_SHARED_PART_CATEGORIES = ("wrong_part", "chose_none", "other")
REACHED_VIA_CATEGORIES = ("said_direct", "said_absent", "said_via",
                          "padding_choice", "other")
EXAMPLES_PER_CATEGORY = 5
EXAMPLE_LABEL_LIMIT = 20
_WORD = re.compile(r"\[WORD:([0-9a-f]+)\]\Z")
_UNIT = re.compile(UNIT_RULE, flags=re.UNICODE)


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def _sha256_file(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _counts(counter):
    """Deterministic str-keyed counts (numeric order for int keys)."""
    keys = list(counter)
    if keys and all(isinstance(key, int) for key in keys):
        order = sorted(keys)
    else:
        order = sorted(keys, key=str)
    return {str(key): counter[key] for key in order}


def _records_by_op(records):
    grouped = {op: [] for op in OPS}
    for record in records:
        grouped.setdefault(record["op"], []).append(record)
    return grouped


def _reach_label(correct):
    if correct in ("direct", "absent"):
        return correct
    if isinstance(correct, str) and correct.startswith("via:"):
        return "via"
    return "other"


def _flatten_labels(values):
    labels = set()
    for value in values:
        if isinstance(value, list):
            labels.update(str(item) for item in value)
        else:
            labels.add(str(value))
    return labels


def _recover_panel_records(packet_ids):
    """Recover the frozen panel's case RECORDS by record_id.

    Why not just ``fresh_panel.build_panel()``: the panel builder's SELECTION
    logic changed after the confirmation run was sealed (``fresh_panel.py`` was
    edited while this review was being produced), so a fresh ``build_panel()``
    no longer returns the same 90 cases. The case records themselves are still
    produced by the same frozen lesson generator, so every packet record_id is
    recovered by generating every whole-part record of every candidate family in
    the declared family-seed region and matching on the record id. The builder is
    still called once for verification (``checks.build_panel_verification``).
    """
    base = fresh_panel.PANEL_FAMILY_BASE + fresh_panel.PANEL_SEED % 1000
    wanted = set(packet_ids)
    found = {}
    for probe in range(1, fresh_panel.MAX_FAMILY_PROBES + 1):
        family_seed = base + probe
        for record in lessons._whole_part_exercises(family_seed,
                                                    fresh_panel.PANEL_SPLIT):
            if record["record_id"] in wanted:
                found[record["record_id"]] = {"family_seed": family_seed,
                                              "record": record}
        if len(found) == len(wanted):
            break
    return found


def _verify_build_panel(packet_ids):
    """Call the panel builder once and record whether it still reproduces the
    sealed panel's record ids."""
    try:
        built = fresh_panel.build_panel()
    except Exception as error:                       # noqa: BLE001 - recorded, not raised
        return {"status": "error",
                "error": type(error).__name__ + ":" + str(error)[:200]}
    built_ids = [case["record_id"] for case in built["cases"]]
    return {
        "status": "reproduced" if built_ids == packet_ids else "mismatch",
        "built_case_count": len(built_ids),
        "overlap_with_sealed_panel_record_ids":
            len(set(built_ids) & set(packet_ids)),
        "same_order": built_ids == packet_ids,
        "built_panel_digest": digest(canonical(built_ids)),
    }


# --------------------------------------------------------------------------
# A/B: wrong-answer classification (fresh panel only)
# --------------------------------------------------------------------------
def _classify_list_parts(predicted, correct):
    """Exactly one category; set comparisons against the correct part list."""
    if predicted == PAD:
        return "padding_choice"
    if not isinstance(predicted, list) or not isinstance(correct, list):
        return "other"
    pred, right = set(predicted), set(correct)
    if pred == right:                   # order/duplicate anomaly, not a set class
        return "other"
    if pred < right:
        return "missing_part"
    if right < pred:
        return "extra_part"
    if pred & right:
        return "mixed_missing_and_extra"
    return "wrong_whole"


def _classify_find_shared_part(predicted, correct):
    if predicted == PAD:
        return "other"
    if predicted == "none":
        return "chose_none"
    if isinstance(predicted, str) and predicted != correct:
        return "wrong_part"
    return "other"


def _classify_reached_via(predicted, correct):
    if predicted == PAD:
        return "padding_choice"
    if predicted == "direct":
        return "said_direct"
    if predicted == "absent":
        return "said_absent"
    if isinstance(predicted, str) and predicted.startswith("via:"):
        return "said_via"
    return "other"


def _list_parts_block(rows, by_id):
    block = {"cases": 0, "correct": 0, "wrong": 0,
             "categories": {name: 0 for name in LIST_PARTS_CATEGORIES},
             "wrong_predicted_size_distribution": {},
             "wrong_correct_size_distribution": {},
             "wrong_size_pair_distribution": {},
             "examples_by_category": {},
             "anomalies": {"identical_set_different_order": 0,
                           "correct_not_a_list": 0,
                           "predicted_not_list_and_not_padding": 0}}
    pred_sizes, right_sizes, pairs, examples = Counter(), Counter(), Counter(), {}
    for row in rows:
        if row["op"] != "LIST_PARTS":
            continue
        block["cases"] += 1
        case = by_id[row["record_id"]]
        record = case["record"]
        correct, predicted = record["correct"], row["predicted"]
        if row["correct"]:
            block["correct"] += 1
            continue
        block["wrong"] += 1
        category = _classify_list_parts(predicted, correct)
        block["categories"][category] += 1
        if not isinstance(correct, list):
            block["anomalies"]["correct_not_a_list"] += 1
        if not isinstance(predicted, list) and predicted != PAD:
            block["anomalies"]["predicted_not_list_and_not_padding"] += 1
        if isinstance(predicted, list) and isinstance(correct, list) \
                and set(predicted) == set(correct):
            block["anomalies"]["identical_set_different_order"] += 1
        if isinstance(predicted, list):
            pred_sizes[len(predicted)] += 1
        if isinstance(correct, list):
            right_sizes[len(correct)] += 1
        if isinstance(predicted, list) and isinstance(correct, list):
            pairs["%d|%d" % (len(predicted), len(correct))] += 1
        bucket = examples.setdefault(category, [])
        if len(bucket) < EXAMPLES_PER_CATEGORY:
            bucket.append({"family_id": case["family_id"],
                           "record_id": row["record_id"],
                           "predicted": predicted, "correct": correct})
    block["wrong_predicted_size_distribution"] = _counts(pred_sizes)
    block["wrong_correct_size_distribution"] = _counts(right_sizes)
    block["wrong_size_pair_distribution"] = {key: pairs[key] for key in sorted(pairs)}
    block["examples_by_category"] = {key: examples[key] for key in sorted(examples)}
    return block


def _simple_block(rows, by_id, op, classifier, categories, other_breakdown):
    block = {"cases": 0, "correct": 0, "wrong": 0,
             "categories": {name: 0 for name in categories},
             "other_breakdown": {}, "examples_by_category": {}}
    breakdown, examples = Counter(), {}
    for row in rows:
        if row["op"] != op:
            continue
        block["cases"] += 1
        if row["correct"]:
            block["correct"] += 1
            continue
        block["wrong"] += 1
        case = by_id[row["record_id"]]
        predicted, correct = row["predicted"], case["record"]["correct"]
        category = classifier(predicted, correct)
        block["categories"][category] += 1
        if category == "other":
            breakdown[other_breakdown(predicted, correct)] += 1
        bucket = examples.setdefault(category, [])
        if len(bucket) < EXAMPLES_PER_CATEGORY:
            bucket.append({"family_id": case["family_id"],
                           "record_id": row["record_id"],
                           "predicted": predicted, "correct": correct})
    block["other_breakdown"] = {key: breakdown[key] for key in sorted(breakdown)}
    block["examples_by_category"] = {key: examples[key] for key in sorted(examples)}
    return block


def _fsp_other_breakdown(predicted, correct):
    if predicted == PAD:
        return "padding_choice"
    if not isinstance(predicted, str):
        return "non_string_prediction"
    if predicted == correct:
        return "identical_to_correct_but_scored_wrong"
    return "unclassified"


def _rv_other_breakdown(predicted, correct):
    if predicted == correct:
        return "identical_to_correct_but_scored_wrong"
    if not isinstance(predicted, str):
        return "non_string_prediction"
    return "unclassified"


def _phase_block(rows, by_id):
    return {
        "LIST_PARTS": _list_parts_block(rows, by_id),
        "FIND_SHARED_PART": _simple_block(rows, by_id, "FIND_SHARED_PART",
                                          _classify_find_shared_part,
                                          FIND_SHARED_PART_CATEGORIES,
                                          _fsp_other_breakdown),
        "REACHED_VIA": _simple_block(rows, by_id, "REACHED_VIA",
                                     _classify_reached_via,
                                     REACHED_VIA_CATEGORIES,
                                     _rv_other_breakdown),
    }


def _pool_phase(blocks, op):
    pooled = {}
    for key, value in blocks[0][op].items():
        if key == "examples_by_category":
            continue
        if isinstance(value, dict) and value and all(
                isinstance(item, int) for item in value.values()):
            merged = Counter()
            for block in blocks:
                merged.update(block[op][key])
            pooled[key] = {name: merged[name] for name in sorted(merged)}
        elif isinstance(value, int):
            pooled[key] = sum(block[op][key] for block in blocks)
        else:
            pooled[key] = value
    return pooled


def _error_classification(packet, by_id):
    per_op = {op: {"per_candidate": [], "pooled": {}} for op in OPS}
    phase_blocks = {phase: [] for phase in PHASES}
    for candidate in packet["candidates"]:
        entry = {"learner_seed": candidate["learner_seed"]}
        for phase in PHASES:
            block = _phase_block(candidate["fresh"][phase]["results"], by_id)
            entry[phase] = block
            phase_blocks[phase].append(block)
        for op in OPS:
            per_op[op]["per_candidate"].append(
                {"learner_seed": candidate["learner_seed"],
                 "before": entry["before"][op], "after": entry["after"][op]})
    for op in OPS:
        per_op[op]["pooled"] = {
            phase: _pool_phase(phase_blocks[phase], op) for phase in PHASES}
    return {
        "per_op": per_op,
        "practice_set_classification": {
            "available": False,
            "reason": ("packet practice predictions rows carry ONLY "
                       "record_id, op, correct; the predicted option string is "
                       "not stored, so no practice error can be classified"),
        },
    }


# --------------------------------------------------------------------------
# C: correct-option availability and encoded position
# --------------------------------------------------------------------------
def _availability(packet, by_id):
    checked = present = absent = duplicated = 0
    per_op = {op: {"wrong_cases": 0, "correct_present_exactly_once": 0}
              for op in OPS}
    anomalies = []
    for candidate in packet["candidates"]:
        for phase in PHASES:
            for row in candidate["fresh"][phase]["results"]:
                if row["correct"]:
                    continue
                checked += 1
                per_op[row["op"]]["wrong_cases"] += 1
                record = by_id[row["record_id"]]["record"]
                occurrences = record["options"].count(record["correct"])
                if occurrences == 1:
                    present += 1
                    per_op[row["op"]]["correct_present_exactly_once"] += 1
                elif occurrences == 0:
                    absent += 1
                    if len(anomalies) < EXAMPLES_PER_CATEGORY:
                        anomalies.append({"kind": "correct_absent",
                                          "op": row["op"],
                                          "record_id": row["record_id"]})
                else:
                    duplicated += 1
                    if len(anomalies) < EXAMPLES_PER_CATEGORY:
                        anomalies.append({"kind": "correct_duplicated",
                                          "op": row["op"],
                                          "record_id": row["record_id"]})
    return {"wrong_cases_checked": checked,
            "correct_present_exactly_once_in_record_options": present,
            "correct_absent_from_record_options": absent,
            "correct_duplicated_in_record_options": duplicated,
            "per_op": per_op, "anomaly_examples": anomalies}


def _encoded_positions(records):
    distribution, pads = Counter(), Counter()
    per_op = {}
    mismatches = 0
    for record in records:
        public = adapter.public_records(record, ARM)
        index = public["encoded_correct_index"]
        distribution[index] += 1
        per_op.setdefault(record["op"], Counter())[index] += 1
        pads[sum(1 for option in public["encoded_options"] if option == PAD)] += 1
        if public["encoded_options"][index] != record["correct"]:
            mismatches += 1
    return {
        "records": len(records),
        "distribution": _counts(distribution),
        "per_op": {op: _counts(per_op[op]) for op in sorted(per_op)},
        "padding_slots_per_encoded_option_list": _counts(pads),
        "encoded_options_at_index_equals_correct_mismatches": mismatches,
    }


def _correct_option_block(packet, by_id, panel_cases, teaching_records):
    return {
        "source": "adapter.public_records(record, 'cas')['encoded_correct_index']",
        "availability_on_wrong_cases": _availability(packet, by_id),
        "encoded_correct_index_panel": _encoded_positions(
            [case["record"] for case in panel_cases]),
        "encoded_correct_index_teaching": _encoded_positions(teaching_records),
    }


# --------------------------------------------------------------------------
# D: coverage comparison (teaching 30 records vs fresh panel 90 cases)
# --------------------------------------------------------------------------
def _list_parts_structure(records):
    cases = all_lists = competing_lists = 0
    position, spread, distractor_relation = Counter(), Counter(), Counter()
    correct_max = correct_min = distractor_longer = distractor_shorter = 0
    case_has_superset = case_has_subset = case_has_disjoint = 0
    for record in records:
        if record["op"] != "LIST_PARTS":
            continue
        cases += 1
        options, correct = record["options"], record["correct"]
        if all(isinstance(option, list) for option in options):
            all_lists += 1
        competing_lists += sum(1 for option in options
                               if isinstance(option, list) and option != correct)
        lengths = [len(option) for option in options]
        correct_length = len(correct)
        others = [length for option, length in zip(options, lengths)
                  if option != correct]
        if correct_length == max(lengths) == min(lengths):
            position["all_three_equal_length"] += 1
        elif correct_length == max(lengths) and lengths.count(correct_length) == 1:
            position["unique_longest"] += 1
        elif correct_length == max(lengths):
            position["tied_longest"] += 1
        elif correct_length == min(lengths) and lengths.count(correct_length) == 1:
            position["unique_shortest"] += 1
        elif correct_length == min(lengths):
            position["tied_shortest"] += 1
        else:
            position["strictly_middle"] += 1
        spread[max(lengths) - min(lengths)] += 1
        if correct_length == max(lengths):
            correct_max += 1
        if correct_length == min(lengths):
            correct_min += 1
        if others and max(others) > correct_length:
            distractor_longer += 1
        if others and min(others) < correct_length:
            distractor_shorter += 1
        has_superset = has_subset = has_disjoint = False
        for option in options:
            if option == correct:
                continue
            left, right = set(option), set(correct)
            if left > right:
                distractor_relation["strict_superset_of_correct"] += 1
                has_superset = True
            elif left < right:
                distractor_relation["strict_subset_of_correct"] += 1
                has_subset = True
            elif left == right:
                distractor_relation["same_set_as_correct"] += 1
            elif left & right:
                distractor_relation["partial_overlap_with_correct"] += 1
            else:
                distractor_relation["disjoint_from_correct"] += 1
                has_disjoint = True
        case_has_superset += int(has_superset)
        case_has_subset += int(has_subset)
        case_has_disjoint += int(has_disjoint)
    return {
        "cases": cases,
        "cases_all_three_options_are_lists": all_lists,
        "competing_options_that_are_lists_total": competing_lists,
        "correct_option_position_by_length": _counts(position),
        "option_length_spread_distribution": _counts(spread),
        "correct_option_is_max_length": correct_max,
        "correct_option_is_min_length": correct_min,
        "cases_with_a_distractor_strictly_longer_than_correct": distractor_longer,
        "cases_with_a_distractor_strictly_shorter_than_correct": distractor_shorter,
        "distractor_relation_to_correct_total": _counts(distractor_relation),
        "cases_with_a_strict_superset_distractor": case_has_superset,
        "cases_with_a_strict_subset_distractor": case_has_subset,
        "cases_with_a_disjoint_distractor": case_has_disjoint,
    }


def _observed_shortcut(packet, by_id):
    """Supplementary: among WRONG LIST_PARTS choices, was the chosen option the
    longest (or the shortest) of the three?"""
    per_candidate = []
    pooled = Counter()
    for candidate in packet["candidates"]:
        entry = {"learner_seed": candidate["learner_seed"]}
        for phase in PHASES:
            counter = Counter()
            wrong = 0
            for row in candidate["fresh"][phase]["results"]:
                if row["op"] != "LIST_PARTS" or row["correct"]:
                    continue
                wrong += 1
                record = by_id[row["record_id"]]["record"]
                options, predicted = record["options"], row["predicted"]
                if not isinstance(predicted, list):
                    counter["chosen_not_a_list"] += 1
                    continue
                lengths = [len(option) for option in options]
                if len(predicted) == max(lengths):
                    counter["chosen_was_longest"] += 1
                if len(predicted) == min(lengths):
                    counter["chosen_was_shortest"] += 1
                if max(lengths) == min(lengths):
                    counter["all_options_equal_length"] += 1
            counter["wrong_cases"] = wrong
            entry[phase] = _counts(counter)
            pooled.update(counter)
        per_candidate.append(entry)
    return {"per_candidate": per_candidate, "pooled": _counts(pooled)}


def _graph_stats(records):
    nodes, relations, distinct = Counter(), Counter(), set()
    for record in records:
        graph = record["graph"]
        nodes[len(graph["nodes"])] += 1
        relations[len(graph["relations"])] += 1
        distinct.add(digest(canonical(graph)))
    return {"records": len(records), "distinct_graphs": len(distinct),
            "node_count_distribution": _counts(nodes),
            "relation_count_distribution": _counts(relations)}


def _label_coverage(teaching_records, panel_records):
    def node_labels(records):
        labels = set()
        for record in records:
            labels.update(node["identifier"] for node in record["graph"]["nodes"])
        return labels

    def option_labels(records):
        labels = set()
        for record in records:
            labels |= _flatten_labels(record["options"])
        return labels

    def answer_labels(records):
        labels = set()
        for record in records:
            labels |= _flatten_labels([record["correct"]])
        return labels

    out = {}
    for name, extractor in (("node_labels", node_labels),
                            ("option_labels", option_labels),
                            ("answer_labels", answer_labels)):
        teaching = extractor(teaching_records)
        panel = extractor(panel_records)
        panel_only = sorted(panel - teaching)
        teaching_only = sorted(teaching - panel)
        out[name] = {
            "teaching_distinct": len(teaching),
            "panel_distinct": len(panel),
            "shared": len(teaching & panel),
            "panel_labels_absent_from_teaching_count": len(panel_only),
            "panel_labels_absent_from_teaching_examples":
                panel_only[:EXAMPLE_LABEL_LIMIT],
            "teaching_labels_absent_from_panel_count": len(teaching_only),
            "teaching_labels_absent_from_panel_examples":
                teaching_only[:EXAMPLE_LABEL_LIMIT],
        }
    return out


def _token_coverage(tokenizer, teaching_records, panel_records):
    lexical = set()
    for token in tokenizer.vocabulary[WORD_START:]:
        match = _WORD.fullmatch(token)
        lexical.add(bytes.fromhex(match.group(1)).decode("utf-8"))

    def scan(records):
        outside = 0
        unseen = Counter()
        cases_with_unseen = 0
        lengths = []
        total_ids = 0
        for record in records:
            public = adapter.public_records(record, ARM)["public"]
            encoded = tokenizer.encode_public(public)
            lengths.append(len(encoded["ids"]))
            total_ids += len(encoded["ids"])
            outside += sum(1 for token_id in encoded["ids"]
                           if not 0 <= token_id < len(tokenizer.vocabulary))
            texts = [public["problem"]] + [row["tag"]
                                           for row in public["observations"]]
            hits = 0
            for text in texts:
                for unit in _UNIT.findall(text):
                    if unit not in lexical:
                        unseen[unit] += 1
                        hits += 1
            if hits:
                cases_with_unseen += 1
        return {"records": len(records),
                "max_sequence_length": max(lengths) if lengths else 0,
                "min_sequence_length": min(lengths) if lengths else 0,
                "total_token_ids": total_ids,
                "token_ids_outside_fitted_vocabulary": outside,
                "cases_with_at_least_one_unseen_unit": cases_with_unseen,
                "distinct_unseen_units": len(unseen),
                "unseen_unit_occurrences": sum(unseen.values()),
                "unseen_unit_examples":
                    {key: unseen[key] for key in sorted(unseen)[:EXAMPLE_LABEL_LIMIT]}}

    return {
        "tokenizer": {"fit_source": "30 teaching records, arm 'cas' "
                                    "(matches the frozen encoder fit)",
                      "max_length": tokenizer.max_length,
                      "fitted_examples": tokenizer.fitted_examples,
                      "fitted_public_sha256": tokenizer.fitted_public_sha256,
                      "vocabulary_size": len(tokenizer.vocabulary),
                      "lexical_vocabulary_size": len(lexical),
                      "fixed_vocabulary_size": WORD_START},
        "lossless_by_construction": (
            "features_v2 LosslessPublicTokenizer has a fixed 256-byte UTF-8 "
            "fallback vocabulary and no UNK token; every unit is encodable, so "
            "'unknown token' does not exist and out-of-vocabulary ids are "
            "verified to be 0 rather than assumed"),
        "teaching": scan(teaching_records),
        "panel": scan(panel_records),
    }


def _coverage_block(teaching_records, panel_records, tokenizer):
    teaching_by_op = _records_by_op(teaching_records)
    panel_by_op = _records_by_op(panel_records)
    coverage = {}

    def sizes(records, field):
        return _counts(Counter(len(record[field]) for record in records
                               if isinstance(record[field], list)))

    coverage["list_parts_answer_size"] = {
        "teaching": sizes(teaching_by_op["LIST_PARTS"], "correct"),
        "panel": sizes(panel_by_op["LIST_PARTS"], "correct")}

    direct = {"teaching": Counter(), "panel": Counter()}
    mismatch = {"teaching": 0, "panel": 0}
    for name, grouped in (("teaching", teaching_by_op), ("panel", panel_by_op)):
        for record in grouped["LIST_PARTS"]:
            graph = Graph.from_record(record["graph"])
            count = len(reference.direct_parts(graph, record["question"]["idea"]))
            direct[name][count] += 1
            if count != len(record["correct"]):
                mismatch[name] += 1
    coverage["list_parts_direct_parts_of_questioned_idea"] = {
        "teaching": _counts(direct["teaching"]),
        "panel": _counts(direct["panel"]),
        "cases_where_count_differs_from_len_correct": mismatch}

    for label, adjust in (("option_count", 0), ("distractor_option_count", -1)):
        block = {}
        for name, grouped in (("teaching", teaching_by_op), ("panel", panel_by_op)):
            block[name] = {op: _counts(Counter(len(record["options"]) + adjust
                                               for record in grouped[op]))
                           for op in OPS}
        coverage[label] = block

    coverage["reached_via_answer_label"] = {
        "teaching": _counts(Counter(_reach_label(record["correct"])
                                    for record in teaching_by_op["REACHED_VIA"])),
        "panel": _counts(Counter(_reach_label(record["correct"])
                                 for record in panel_by_op["REACHED_VIA"]))}
    coverage["find_shared_part_answer_kind"] = {
        "teaching": _counts(Counter("none" if record["correct"] == "none"
                                    else "part_label"
                                    for record in teaching_by_op["FIND_SHARED_PART"])),
        "panel": _counts(Counter("none" if record["correct"] == "none"
                                 else "part_label"
                                 for record in panel_by_op["FIND_SHARED_PART"]))}
    fsp_options = {"teaching": Counter(), "panel": Counter()}
    for name, grouped in (("teaching", teaching_by_op), ("panel", panel_by_op)):
        for record in grouped["FIND_SHARED_PART"]:
            options = record["options"]
            fsp_options[name]["cases"] += 1
            fsp_options[name]["cases_with_none_among_options"] += int("none" in options)
            fsp_options[name]["cases_answer_is_none"] += int(record["correct"] == "none")
            fsp_options[name]["cases_answer_is_none_and_none_is_an_option"] += int(
                record["correct"] == "none" and "none" in options)
            fsp_options[name]["cases_all_options_equal_character_length"] += int(
                len({len(str(option)) for option in options}) == 1)
    coverage["find_shared_part_option_composition"] = {
        name: _counts(fsp_options[name]) for name in ("teaching", "panel")}
    coverage["label_coverage"] = _label_coverage(teaching_records, panel_records)
    coverage["token_coverage"] = _token_coverage(tokenizer, teaching_records,
                                                 panel_records)
    coverage["graph_size"] = {"teaching": _graph_stats(teaching_records),
                              "panel": _graph_stats(panel_records)}
    coverage["list_parts_option_structure"] = {
        "teaching": _list_parts_structure(teaching_by_op["LIST_PARTS"]),
        "panel": _list_parts_structure(panel_by_op["LIST_PARTS"])}
    return coverage


# --------------------------------------------------------------------------
# checks + unavailable
# --------------------------------------------------------------------------
def _checks(packet, panel_meta, panel_cases, by_id, build_panel_verification):
    panel_ids = [case["record_id"] for case in panel_cases]
    packet_ids = [row["record_id"]
                  for row in packet["candidates"][0]["fresh"]["before"]["results"]]
    recomputed = {}
    for candidate in packet["candidates"]:
        for phase in PHASES:
            rows = candidate["fresh"][phase]["results"]
            key = "%d:%s" % (candidate["learner_seed"], phase)
            per_op = {op: {"attempted": 0, "correct": 0} for op in OPS}
            for row in rows:
                per_op[row["op"]]["attempted"] += 1
                per_op[row["op"]]["correct"] += int(row["correct"])
            recomputed[key] = {
                "results": len(rows),
                "correct": sum(1 for row in rows if row["correct"]),
                "per_op": per_op,
                "packet_per_op_match": per_op == candidate["fresh"][phase]["per_op"],
                "packet_correct_match":
                    sum(1 for row in rows if row["correct"])
                    == candidate["fresh"][phase]["correct"],
                "all_record_ids_in_panel":
                    all(row["record_id"] in by_id for row in rows),
                "row_order_matches_panel":
                    [row["record_id"] for row in rows] == panel_ids,
                "panel_digest_matches":
                    digest(canonical([row["record_id"] for row in rows]))
                    == candidate["fresh"][phase]["panel_digest"],
                "sealed_predictions_match_results":
                    candidate["fresh"][phase]["sealed_predictions"]
                    == [{name: row[name] for name in
                         ("family_id", "record_id", "op", "predicted")}
                        for row in rows],
            }
    practice = []
    for candidate in packet["candidates"]:
        for phase in PHASES:
            rows = candidate["practice"][phase]["predictions"]
            practice.append({
                "learner_seed": candidate["learner_seed"], "phase": phase,
                "rows": len(rows),
                "row_fields": sorted({key for row in rows for key in row}),
                "predicted_string_present": any("predicted" in row for row in rows),
            })
    return {
        "packet_path": str(PACKET_PATH.relative_to(ROOT)).replace("\\", "/"),
        "packet_sha256": _sha256_file(PACKET_PATH),
        "candidates": len(packet["candidates"]),
        "learner_seeds": [candidate["learner_seed"]
                          for candidate in packet["candidates"]],
        "panel_case_count": panel_meta["case_count"],
        "panel_family_count": panel_meta["family_count"],
        "panel_seed": panel_meta["panel_seed"],
        "panel_cases_per_op": panel_meta["cases_per_op"],
        "panel_reach_label_counts": panel_meta["reach_label_counts"],
        "panel_digest_recomputed": panel_meta["panel_digest"],
        "panel_record_ids_equal_sealed_panel": set(panel_ids) == set(packet_ids),
        "panel_record_ids_same_order_as_sealed_panel": panel_ids == packet_ids,
        "panel_record_recovery": {
            "source": ("fresh_panel family-seed region + lessons."
                       "_whole_part_exercises, matched on record_id"),
            "requested": len(packet_ids), "recovered": len(panel_cases),
            "missing": [rid for rid in packet_ids if rid not in by_id]},
        "build_panel_verification": build_panel_verification,
        "source_sha256": {
            name: _sha256_file(ROOT / name) for name in (
                "cas_meta2/graph_teaching/fresh_panel.py",
                "cas_meta2/graph_teaching/lessons.py",
                "cas_meta2/graph_teaching/adapter.py",
                "cas_meta2/graph_teaching/trainer.py",
                "cas_meta2/graph_teaching/reference.py",
                "cas_meta2/graph_teaching/graph.py",
                "cas_meta2/features_v2.py",
                "tools/graph6_curriculum_error_review.py")},
        "teaching_record_count": len(trainer.training_records(TEACHING_SEED)),
        "recomputed_from_packet": recomputed,
        "practice_prediction_rows": practice,
    }


def _unavailable():
    return [
        {"item": "practice-set predicted option strings",
         "status": "UNAVAILABLE",
         "detail": ("packet practice rows store only record_id, op, correct "
                    "(30 rows per candidate/phase); no predicted option string "
                    "is stored, so practice errors cannot be classified or sized")},
        {"item": "practice-set wrong-answer categories and predicted sizes",
         "status": "UNAVAILABLE",
         "detail": "follows from the missing practice predicted strings"},
        {"item": "per-option readout scores / logits / softmax probabilities",
         "status": "UNAVAILABLE",
         "detail": ("the packet stores only the argmax option per case; no "
                    "score vector, logit, or probability is persisted")},
        {"item": "option ranking beyond the argmax (2nd/3rd preference, ties)",
         "status": "UNAVAILABLE",
         "detail": "only the selected option is stored"},
        {"item": "model internals (activations, embeddings, attention, module tensors)",
         "status": "UNAVAILABLE",
         "detail": ("no forward-pass state is persisted; only parameter "
                    "digests (initial/trained checkpoint identity) and the "
                    "containment change list are stored")},
        {"item": "optimizer state (AdamW moments, per-parameter values)",
         "status": "UNAVAILABLE",
         "detail": ("the packet stores permitted/frozen parameter NAMES and "
                    "parameter digests, never tensors; the baseline row states "
                    "the run-005 weights were never written to evidence")},
        {"item": "trained weights for any candidate",
         "status": "UNAVAILABLE",
         "detail": "only trained_checkpoint_identity digests are stored"},
        {"item": "per-step training loss curve",
         "status": "UNAVAILABLE",
         "detail": ("history is sampled every 8 optimizer steps (9 points: "
                    "0,8,...,64); the intermediate steps are not stored")},
        {"item": "per-case token counts and encoded public inputs as stored artifacts",
         "status": "DERIVED_ONLY",
         "detail": ("not persisted in the packet, but exactly reconstructible "
                    "from the deterministic generators plus the fitted "
                    "tokenizer (computed in section D)")},
        {"item": "per-case encoded option order",
         "status": "DERIVED_ONLY",
         "detail": ("not persisted per case; deterministically reconstructible "
                    "via adapter.public_records(record, 'cas')")},
        {"item": "per-case wall-clock timings",
         "status": "UNAVAILABLE",
         "detail": "no per-case or per-step timing is stored"},
        {"item": "tokenizer artifact for the run",
         "status": "DERIVED_ONLY",
         "detail": ("only encoder_identity (a digest of the frozen projection) "
                    "is stored; the tokenizer is refitted here from the 30 "
                    "teaching publics, matching the frozen fit source")},
    ]


# --------------------------------------------------------------------------
# report assembly
# --------------------------------------------------------------------------
def build_report():
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    packet_rows = packet["candidates"][0]["fresh"]["before"]["results"]
    packet_ids = [row["record_id"] for row in packet_rows]
    family_of = {row["record_id"]: row["family_id"] for row in packet_rows}
    recovered = _recover_panel_records(packet_ids)
    missing = [record_id for record_id in packet_ids
               if record_id not in recovered]
    if missing:
        raise ValueError("PANEL_RECORD_RECOVERY_INCOMPLETE:%d" % len(missing))
    panel_cases = [{"family_id": family_of[record_id], "record_id": record_id,
                    "family_seed": recovered[record_id]["family_seed"],
                    "signature": fresh_panel.signature_key(
                        recovered[record_id]["record"]),
                    "record": recovered[record_id]["record"]}
                   for record_id in packet_ids]
    by_id = {case["record_id"]: case for case in panel_cases}
    panel_records = [case["record"] for case in panel_cases]
    panel_meta = {
        "builder": ("cas_meta2.graph_teaching.fresh_panel family-seed region; "
                    "records recovered by record_id (see checks."
                    "build_panel_verification)"),
        "panel_seed": fresh_panel.PANEL_SEED,
        "family_base": fresh_panel.PANEL_FAMILY_BASE,
        "max_family_probes": fresh_panel.MAX_FAMILY_PROBES,
        "family_count": len({case["family_id"] for case in panel_cases}),
        "case_count": len(panel_cases),
        "cases_per_op": _counts(Counter(case["record"]["op"]
                                        for case in panel_cases)),
        "reach_label_counts": {
            label: sum(1 for case in panel_cases
                       if case["record"]["op"] == "REACHED_VIA"
                       and _reach_label(case["record"]["correct"]) == label)
            for label in ("direct", "via", "absent")},
        "panel_digest": digest(canonical(packet_ids)),
    }
    build_panel_verification = _verify_build_panel(packet_ids)
    teaching_records = trainer.training_records(TEACHING_SEED)
    publics = [adapter.public_records(record, ARM)["public"]
               for record in teaching_records]
    tokenizer = LosslessPublicTokenizer.fit_train(publics, max_length=MAX_LENGTH)

    errors = _error_classification(packet, by_id)
    return {
        "schema": SCHEMA,
        "boundaries": {
            "read_only": True,
            "torch_imported": False,
            "training_performed": False,
            "network_used": False,
            "cached_on_disk": False,
            "causal_claims_made": False,
            "deterministic": True,
        },
        "inputs": {
            "packet": {"path": str(PACKET_PATH.relative_to(ROOT)).replace("\\", "/"),
                       "sha256": _sha256_file(PACKET_PATH)},
            "panel": dict(panel_meta,
                          build_panel_verification=build_panel_verification),
            "teaching": {"builder": "cas_meta2.graph_teaching.trainer.training_records",
                         "seed": TEACHING_SEED,
                         "record_count": len(teaching_records),
                         "by_op": _counts(Counter(record["op"]
                                                  for record in teaching_records))},
            "tokenizer": {"builder": ("cas_meta2.features_v2."
                                      "LosslessPublicTokenizer.fit_train"),
                          "arm": ARM, "max_length": MAX_LENGTH,
                          "fitted_examples": len(publics)},
        },
        "A_list_parts_error_classification": errors["per_op"]["LIST_PARTS"],
        "B_other_ops_error_classification": {
            "FIND_SHARED_PART": errors["per_op"]["FIND_SHARED_PART"],
            "REACHED_VIA": errors["per_op"]["REACHED_VIA"],
        },
        "B_classification_contract": {
            "list_parts_categories": list(LIST_PARTS_CATEGORIES),
            "find_shared_part_categories": list(FIND_SHARED_PART_CATEGORIES),
            "reached_via_categories": list(REACHED_VIA_CATEGORIES),
            "categories_are_mutually_exclusive": True,
            "practice_set_classification": errors["practice_set_classification"],
        },
        "C_correct_option_availability_and_position":
            _correct_option_block(packet, by_id, panel_cases, teaching_records),
        "D_coverage_comparison": dict(
            _coverage_block(teaching_records, panel_records, tokenizer),
            shortcut_observed_choices=_observed_shortcut(packet, by_id)),
        "E_unavailable": _unavailable(),
        "checks": _checks(packet, panel_meta, panel_cases, by_id,
                          build_panel_verification),
    }


# --------------------------------------------------------------------------
# markdown summary (numbers come from the same report object)
# --------------------------------------------------------------------------
def _implications(report):
    lp = report["A_list_parts_error_classification"]
    fsp = report["B_other_ops_error_classification"]["FIND_SHARED_PART"]
    cov = report["D_coverage_comparison"]
    teaching_struct = cov["list_parts_option_structure"]["teaching"]
    panel_struct = cov["list_parts_option_structure"]["panel"]
    labels = cov["label_coverage"]["node_labels"]
    tokens = cov["token_coverage"]
    fsp_opts = cov["find_shared_part_option_composition"]
    bullets = [
        "LIST_PARTS: `missing_part` is the largest wrong class in every cell "
        "(pooled %d/%d before, %d/%d after); a strict-subset distractor is "
        "already present in %d/%d teaching and %d/%d panel cases, so vary the "
        "subset distractors instead of only adding one (two competing subsets, "
        "or a subset of size |correct|-%d)."
        % (lp["pooled"]["before"]["categories"]["missing_part"],
           lp["pooled"]["before"]["wrong"],
           lp["pooled"]["after"]["categories"]["missing_part"],
           lp["pooled"]["after"]["wrong"],
           teaching_struct["cases_with_a_strict_subset_distractor"],
           teaching_struct["cases"],
           panel_struct["cases_with_a_strict_subset_distractor"],
           panel_struct["cases"], 1),
        "LIST_PARTS: `extra_part` grew (pooled %d/%d before, %d/%d after); a "
        "strict-superset distractor is present in only %d/%d teaching and %d/%d "
        "panel cases, so add superset distractors to every LIST_PARTS lesson."
        % (lp["pooled"]["before"]["categories"]["extra_part"],
           lp["pooled"]["before"]["wrong"],
           lp["pooled"]["after"]["categories"]["extra_part"],
           lp["pooled"]["after"]["wrong"],
           teaching_struct["cases_with_a_strict_superset_distractor"],
           teaching_struct["cases"],
           panel_struct["cases_with_a_strict_superset_distractor"],
           panel_struct["cases"]),
        "LIST_PARTS: add equal-length competing lists to test length as a cue - "
        "%d/%d teaching and %d/%d panel cases have all three options equal "
        "length (teaching option-length spread %s, panel %s)."
        % (teaching_struct["correct_option_position_by_length"]
           .get("all_three_equal_length", 0),
           teaching_struct["cases"],
           panel_struct["correct_option_position_by_length"]
           .get("all_three_equal_length", 0),
           panel_struct["cases"],
           json.dumps(teaching_struct["option_length_spread_distribution"],
                      sort_keys=True),
           json.dumps(panel_struct["option_length_spread_distribution"],
                      sort_keys=True)),
        "LIST_PARTS: keep disjoint (`wrong_whole`) distractors (pooled %d/%d "
        "before, %d/%d after; present in %d/%d teaching and %d/%d panel cases) "
        "so 'wrong whole' stays separable from 'wrong size'."
        % (lp["pooled"]["before"]["categories"]["wrong_whole"],
           lp["pooled"]["before"]["wrong"],
           lp["pooled"]["after"]["categories"]["wrong_whole"],
           lp["pooled"]["after"]["wrong"],
           teaching_struct["cases_with_a_disjoint_distractor"],
           teaching_struct["cases"],
           panel_struct["cases_with_a_disjoint_distractor"],
           panel_struct["cases"]),
        "Vocabulary: %d panel text units are absent from the teaching-fitted "
        "vocabulary and fall back to byte tokens in %d/%d panel cases "
        "(%d unseen units in teaching), and %d node labels appear in the panel "
        "that never appear in teaching (%s), so add consistent renaming lessons "
        "covering the panel label styles."
        % (tokens["panel"]["distinct_unseen_units"],
           tokens["panel"]["cases_with_at_least_one_unseen_unit"],
           tokens["panel"]["records"], tokens["teaching"]["distinct_unseen_units"],
           labels["panel_labels_absent_from_teaching_count"],
           json.dumps(list(tokens["panel"]["unseen_unit_examples"]))),
        "Graph form: panel graphs run %s nodes / %s relations vs teaching %s / "
        "%s (%d of %d panel graphs distinct vs %d of %d teaching), so add "
        "harmless reordering lessons that permute node and relation order "
        "without changing counts."
        % (json.dumps(cov["graph_size"]["panel"]["node_count_distribution"],
                      sort_keys=True),
           json.dumps(cov["graph_size"]["panel"]["relation_count_distribution"],
                      sort_keys=True),
           json.dumps(cov["graph_size"]["teaching"]["node_count_distribution"],
                      sort_keys=True),
           json.dumps(cov["graph_size"]["teaching"]["relation_count_distribution"],
                      sort_keys=True),
           cov["graph_size"]["panel"]["distinct_graphs"],
           cov["graph_size"]["panel"]["records"],
           cov["graph_size"]["teaching"]["distinct_graphs"],
           cov["graph_size"]["teaching"]["records"]),
        "REACHED_VIA: the panel is a declared even split (%s) while teaching is "
        "%s, so keep maintenance lessons at the panel split and add `via:` "
        "questions whose correct label is not the first direct constituent."
        % (json.dumps(cov["reached_via_answer_label"]["panel"], sort_keys=True),
           json.dumps(cov["reached_via_answer_label"]["teaching"], sort_keys=True)),
        "FIND_SHARED_PART: `chose_none` is %d wrong before and %d wrong after "
        "(pooled %d and %d wrong), while the answer is `none` in %d/%d panel and "
        "%d/%d teaching cases and `none` is among the three options in %d/%d "
        "panel and %d/%d teaching cases, so keep maintenance lessons that pair a "
        "one-shared-part case with a `none` case at equal option length."
        % (fsp["pooled"]["before"]["categories"]["chose_none"],
           fsp["pooled"]["after"]["categories"]["chose_none"],
           fsp["pooled"]["before"]["wrong"], fsp["pooled"]["after"]["wrong"],
           int(cov["find_shared_part_answer_kind"]["panel"].get("none", 0)),
           int(fsp_opts["panel"].get("cases", 0)),
           int(cov["find_shared_part_answer_kind"]["teaching"].get("none", 0)),
           int(fsp_opts["teaching"].get("cases", 0)),
           int(fsp_opts["panel"].get("cases_with_none_among_options", 0)),
           int(fsp_opts["panel"].get("cases", 0)),
           int(fsp_opts["teaching"].get("cases_with_none_among_options", 0)),
           int(fsp_opts["teaching"].get("cases", 0))),
    ]
    return bullets


def render_markdown(report):
    checks = report["checks"]
    lp = report["A_list_parts_error_classification"]
    fsp = report["B_other_ops_error_classification"]["FIND_SHARED_PART"]
    rv = report["B_other_ops_error_classification"]["REACHED_VIA"]
    contract = report["B_classification_contract"]
    pos = report["C_correct_option_availability_and_position"]
    cov = report["D_coverage_comparison"]
    lp_cat = contract["list_parts_categories"]
    fsp_cat = contract["find_shared_part_categories"]
    rv_cat = contract["reached_via_categories"]

    def row(block, categories):
        return " | ".join(str(block["categories"][name]) for name in categories)

    lines = []
    add = lines.append
    add("# CURRICULUM_002 - GRAPH6 retained-error review (factual counts only)")
    add("")
    add("Regenerated by `tools/graph6_curriculum_error_review.py` (pure Python, no "
        "torch, no training) into `CURRICULUM_002_ERROR_REVIEW.json`.")
    add("Packet `%s` sha256 `%s`; panel_seed %d, %d families, %d cases, %s per op; "
        "teaching seed %d, %d whole-part records (%s); 3 candidates (%s)."
        % (checks["packet_path"], checks["packet_sha256"], checks["panel_seed"],
           checks["panel_family_count"], checks["panel_case_count"],
           json.dumps(checks["panel_cases_per_op"], sort_keys=True),
           report["inputs"]["teaching"]["seed"],
           report["inputs"]["teaching"]["record_count"],
           json.dumps(report["inputs"]["teaching"]["by_op"], sort_keys=True),
           json.dumps(checks["learner_seeds"])))
    bpv = checks["build_panel_verification"]
    add("Panel join: %d/%d sealed case records recovered by record_id from the "
        "frozen family-seed region (same order as the sealed results, digest "
        "`%s`); a fresh `fresh_panel.build_panel()` returns a different panel "
        "(status `%s`, %s/%d record ids overlapping), so the builder is used for "
        "verification only. Source `fresh_panel.py` sha256 `%s`, `lessons.py` "
        "sha256 `%s`."
        % (checks["panel_record_recovery"]["recovered"],
           checks["panel_record_recovery"]["requested"],
           checks["panel_digest_recomputed"], bpv.get("status"),
           bpv.get("overlap_with_sealed_panel_record_ids"),
           checks["panel_record_recovery"]["requested"],
           checks["source_sha256"]["cas_meta2/graph_teaching/fresh_panel.py"],
           checks["source_sha256"]["cas_meta2/graph_teaching/lessons.py"]))
    add("")
    add("## 1. LIST_PARTS wrong-answer categories (30 cases per candidate and phase)")
    add("")
    add("| candidate seed | phase | cases | correct | " + " | ".join(lp_cat) + " |")
    add("|---:|---|---:|---:|" + "|".join(["---:"] * len(lp_cat)) + "|")
    for entry in lp["per_candidate"]:
        for phase in PHASES:
            block = entry[phase]
            add("| %d | %s | %d | %d | %s |"
                % (entry["learner_seed"], phase, block["cases"],
                   block["correct"], row(block, lp_cat)))
    for phase in PHASES:
        block = lp["pooled"][phase]
        add("| pooled (3 candidates) | %s | %d | %d | %s |"
            % (phase, block["cases"], block["correct"], row(block, lp_cat)))
    add("")
    keys = sorted(set(lp["pooled"]["before"]["wrong_size_pair_distribution"])
                  | set(lp["pooled"]["after"]["wrong_size_pair_distribution"]))
    add("Wrong-case size pairs `|predicted| x |correct|` (pooled, before -> after): "
        + "; ".join("%s: %s -> %s"
                    % (key,
                       lp["pooled"]["before"]["wrong_size_pair_distribution"].get(key, 0),
                       lp["pooled"]["after"]["wrong_size_pair_distribution"].get(key, 0))
                    for key in keys) + ".")
    wrong_total = sum(lp["pooled"][phase]["wrong"] for phase in PHASES)
    pad_total = sum(lp["pooled"][phase]["categories"]["padding_choice"]
                    for phase in PHASES)
    anomaly_total = sum(lp["pooled"][phase]["anomalies"]
                        ["predicted_not_list_and_not_padding"] for phase in PHASES)
    add("`padding_choice` = %d of %d pooled wrong LIST_PARTS predictions; %d were "
        "lists and %d were neither a list nor padding (anomalies: %s)."
        % (pad_total, wrong_total, wrong_total - pad_total - anomaly_total,
           anomaly_total,
           json.dumps(lp["pooled"]["before"]["anomalies"], sort_keys=True)))
    add("")
    add("## 2. FIND_SHARED_PART and REACHED_VIA wrong-answer categories")
    add("")
    add("| candidate seed | phase | FIND_SHARED_PART cases/correct | " +
        " | ".join(fsp_cat) + " |")
    add("|---:|---|---:|" + "|".join(["---:"] * len(fsp_cat)) + "|")
    for entry in fsp["per_candidate"]:
        for phase in PHASES:
            block = entry[phase]
            add("| %d | %s | %d / %d | %s |"
                % (entry["learner_seed"], phase, block["cases"], block["correct"],
                   row(block, fsp_cat)))
    for phase in PHASES:
        block = fsp["pooled"][phase]
        add("| pooled (3 candidates) | %s | %d / %d | %s |"
            % (phase, block["cases"], block["correct"], row(block, fsp_cat)))
    add("")
    add("| candidate seed | phase | REACHED_VIA cases/correct | " +
        " | ".join(rv_cat) + " |")
    add("|---:|---|---:|" + "|".join(["---:"] * len(rv_cat)) + "|")
    for entry in rv["per_candidate"]:
        for phase in PHASES:
            block = entry[phase]
            add("| %d | %s | %d / %d | %s |"
                % (entry["learner_seed"], phase, block["cases"], block["correct"],
                   row(block, rv_cat)))
    for phase in PHASES:
        block = rv["pooled"][phase]
        add("| pooled (3 candidates) | %s | %d / %d | %s |"
            % (phase, block["cases"], block["correct"], row(block, rv_cat)))
    add("")
    add("`other` breakdown (pooled; an empty object means zero `other` "
        "predictions): FIND_SHARED_PART before %s / after %s; REACHED_VIA before "
        "%s / after %s."
        % (json.dumps(fsp["pooled"]["before"]["other_breakdown"], sort_keys=True),
           json.dumps(fsp["pooled"]["after"]["other_breakdown"], sort_keys=True),
           json.dumps(rv["pooled"]["before"]["other_breakdown"], sort_keys=True),
           json.dumps(rv["pooled"]["after"]["other_breakdown"], sort_keys=True)))
    add("Practice-set classification is UNAVAILABLE: each of the %d practice rows "
        "in each of the %d candidate/phase blocks stores fields %s, and "
        "`predicted` is present in %d of those %d blocks."
        % (checks["practice_prediction_rows"][0]["rows"],
           len(checks["practice_prediction_rows"]),
           json.dumps(checks["practice_prediction_rows"][0]["row_fields"]),
           sum(1 for item in checks["practice_prediction_rows"]
               if item["predicted_string_present"]),
           len(checks["practice_prediction_rows"])))
    add("")
    add("## 3. Correct option availability and encoded position")
    add("")
    avail = pos["availability_on_wrong_cases"]
    add("Correct answer present exactly once among the options in %d/%d wrong "
        "cases (absent %d, duplicated %d); per op %s."
        % (avail["correct_present_exactly_once_in_record_options"],
           avail["wrong_cases_checked"], avail["correct_absent_from_record_options"],
           avail["correct_duplicated_in_record_options"],
           json.dumps(avail["per_op"], sort_keys=True)))
    add("`encoded_correct_index` distribution - panel (%d cases): %s; teaching "
        "(%d records): %s."
        % (pos["encoded_correct_index_panel"]["records"],
           json.dumps(pos["encoded_correct_index_panel"]["distribution"],
                      sort_keys=True),
           pos["encoded_correct_index_teaching"]["records"],
           json.dumps(pos["encoded_correct_index_teaching"]["distribution"],
                      sort_keys=True)))
    add("Padding slots per encoded option list - panel %s; teaching %s; "
        "`encoded_options[index] == correct` mismatches %d (panel) and %d (teaching)."
        % (json.dumps(pos["encoded_correct_index_panel"]
                      ["padding_slots_per_encoded_option_list"], sort_keys=True),
           json.dumps(pos["encoded_correct_index_teaching"]
                      ["padding_slots_per_encoded_option_list"], sort_keys=True),
           pos["encoded_correct_index_panel"]
           ["encoded_options_at_index_equals_correct_mismatches"],
           pos["encoded_correct_index_teaching"]
           ["encoded_options_at_index_equals_correct_mismatches"]))
    add("")
    add("## 4. Coverage: teaching (30 records) vs fresh panel (90 cases)")
    add("")
    add("| measure | teaching | panel |")
    add("|---|---|---|")
    for key, label in (("list_parts_answer_size", "LIST_PARTS answer size"),
                       ("list_parts_direct_parts_of_questioned_idea",
                        "LIST_PARTS direct parts of questioned idea"),
                       ("reached_via_answer_label", "REACHED_VIA answer label"),
                       ("find_shared_part_answer_kind",
                        "FIND_SHARED_PART answer kind (none vs part)")):
        add("| %s | %s | %s |"
            % (label, json.dumps(cov[key]["teaching"], sort_keys=True),
               json.dumps(cov[key]["panel"], sort_keys=True)))
    add("| distractor option count (all three ops) | %s | %s |"
        % (json.dumps(cov["distractor_option_count"]["teaching"], sort_keys=True),
           json.dumps(cov["distractor_option_count"]["panel"], sort_keys=True)))
    add("| FIND_SHARED_PART option composition | %s | %s |"
        % (json.dumps(cov["find_shared_part_option_composition"]["teaching"],
                      sort_keys=True),
           json.dumps(cov["find_shared_part_option_composition"]["panel"],
                      sort_keys=True)))
    for name in ("node_labels", "option_labels", "answer_labels"):
        block = cov["label_coverage"][name]
        add("| %s (distinct) | %d | %d (panel-only %d; teaching-only %d) |"
            % (name, block["teaching_distinct"], block["panel_distinct"],
               block["panel_labels_absent_from_teaching_count"],
               block["teaching_labels_absent_from_panel_count"]))
    add("| graph nodes / relations (distinct graphs) | %s / %s (%d of %d) | "
        "%s / %s (%d of %d) |"
        % (json.dumps(cov["graph_size"]["teaching"]["node_count_distribution"],
                      sort_keys=True),
           json.dumps(cov["graph_size"]["teaching"]["relation_count_distribution"],
                      sort_keys=True),
           cov["graph_size"]["teaching"]["distinct_graphs"],
           cov["graph_size"]["teaching"]["records"],
           json.dumps(cov["graph_size"]["panel"]["node_count_distribution"],
                      sort_keys=True),
           json.dumps(cov["graph_size"]["panel"]["relation_count_distribution"],
                      sort_keys=True),
           cov["graph_size"]["panel"]["distinct_graphs"],
           cov["graph_size"]["panel"]["records"]))
    add("")
    tc = cov["token_coverage"]
    add("Tokenizer vocabulary %d (fixed %d + lexical %d) fitted on %d teaching "
        "publics; panel token ids outside the fitted vocabulary %d of %d panel "
        "token ids; distinct unseen text units %d in %d occurrences across "
        "%d/%d panel cases (teaching: %d unseen units, %d ids outside); panel "
        "sequence length min %d / max %d (teaching min %d / max %d)."
        % (tc["tokenizer"]["vocabulary_size"], tc["tokenizer"]["fixed_vocabulary_size"],
           tc["tokenizer"]["lexical_vocabulary_size"], tc["tokenizer"]["fitted_examples"],
           tc["panel"]["token_ids_outside_fitted_vocabulary"],
           tc["panel"]["total_token_ids"],
           tc["panel"]["distinct_unseen_units"], tc["panel"]["unseen_unit_occurrences"],
           tc["panel"]["cases_with_at_least_one_unseen_unit"], tc["panel"]["records"],
           tc["teaching"]["distinct_unseen_units"],
           tc["teaching"]["token_ids_outside_fitted_vocabulary"],
           tc["panel"]["min_sequence_length"], tc["panel"]["max_sequence_length"],
           tc["teaching"]["min_sequence_length"], tc["teaching"]["max_sequence_length"]))
    add("Lossless by construction: %s." % tc["lossless_by_construction"])
    add("Panel-only examples: node labels %s; unseen text units %s."
        % (json.dumps(cov["label_coverage"]["node_labels"]
                      ["panel_labels_absent_from_teaching_examples"]),
           json.dumps(tc["panel"]["unseen_unit_examples"], sort_keys=True)))
    add("")
    add("## 5. Shortcut check: choose the longest list")
    add("")
    for name in ("teaching", "panel"):
        block = cov["list_parts_option_structure"][name]
        add("- %s (%d LIST_PARTS records): all three options are lists in %d "
            "cases; competing list options %d; correct position by length %s; "
            "correct is max length %d and min length %d; a distractor is strictly "
            "longer in %d cases and strictly shorter in %d; distractor relations %s."
            % (name, block["cases"], block["cases_all_three_options_are_lists"],
               block["competing_options_that_are_lists_total"],
               json.dumps(block["correct_option_position_by_length"], sort_keys=True),
               block["correct_option_is_max_length"],
               block["correct_option_is_min_length"],
               block["cases_with_a_distractor_strictly_longer_than_correct"],
               block["cases_with_a_distractor_strictly_shorter_than_correct"],
               json.dumps(block["distractor_relation_to_correct_total"],
                          sort_keys=True)))
    add("- Observed WRONG LIST_PARTS choices (pooled, 3 candidates x 2 phases): %s; "
        "the longest and shortest counts sum to the %d wrong cases because no "
        "panel LIST_PARTS case has three equal-length options."
        % (json.dumps(cov["shortcut_observed_choices"]["pooled"], sort_keys=True),
           cov["shortcut_observed_choices"]["pooled"]["wrong_cases"]))
    add("")
    add("## 6. UNAVAILABLE (cannot be recovered from the saved records)")
    add("")
    for entry in report["E_unavailable"]:
        add("- **%s** - %s: %s" % (entry["item"], entry["status"], entry["detail"]))
    add("")
    add("## 7. Curriculum implications (proposed, not established)")
    add("")
    for bullet in _implications(report):
        add("- " + bullet)
    add("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=("CURRICULUM_002 read-only factual review of the retained "
                     "GRAPH6 fresh-panel errors"))
    parser.add_argument("--output", metavar="PATH",
                        help="write the canonical JSON report to PATH")
    parser.add_argument("--markdown", metavar="PATH",
                        help="write the markdown summary to PATH")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = build_report()
    text = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(report), encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
