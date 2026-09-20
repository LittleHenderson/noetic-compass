"""Held-out evaluation for the face-grounding pilot, with the rows kept.

Three layers, reported separately and never pooled into one flattering number:

A. **role recognition** - 16 held-out families x 6 roles = 96 three-choice
   ``ROLE_FROM_CONTENT`` questions, with no cue and no support answers;
B. **role application** - 16 x 6 = 96 three-choice ``FACE_APPLY`` questions whose
   options all attempt the requested role. The panel carries **no face cue**, so
   it doubles as the plan's "remove the explicit cue during application"
   diagnostic and is identical for both comparison arms;
C. **targeted behavioural checks** on a frozen subset - consistent renaming must
   preserve the answer, harmless reordering must preserve it, and a meaningful
   rewiring must change it *to the right answer*. Output movement alone is never
   counted as understanding.

Every item keeps its per-question row: the expected answer, the selected answer,
both categories, all three scores, the loss, the delivered slot order and the
update index. That is the row Attempt 007's report discarded, and the reason its
paired comparison could not be computed afterwards.

The 192 primary questions are views of 16 families, not 192 independent families,
and the report says so; uncertainty claims are therefore limited to what a single
initialization can support.
"""
from __future__ import annotations

import hashlib
import random
from collections import Counter, OrderedDict

from .graph import canonical, digest, require
from . import face_corpus as corpus
from . import face_roles as roles
from . import face_tasks as tasks

SCHEMA = "cas.cube-face-evaluation/0.1"

#: The evaluation panel carries no cue in either arm: the requested role is given
#: in words, so the panel is identical across conditions and tests cue-free use.
EVALUATION_ARM = "none"

#: Small frozen diagnostic subset: families and the role they are probed on.
DIAGNOSTIC_FAMILIES = 8
DIAGNOSTIC_FACE = 5
DIAGNOSTIC_KINDS = ("renamed", "reordered", "rewired")


def held_out_families(built=None):
    built = corpus.families() if built is None else built
    return corpus.by_split(corpus.FINAL_HELD_OUT, built)


def panel(built=None):
    """The frozen final panel: 192 primary items plus the diagnostic subset."""
    built = corpus.families() if built is None else built
    families = held_out_families(built)
    items = []
    for family in families:
        for face in roles.FACE_NUMBERS:
            items.append({"item_id": "recognition:%s:%d" % (family["family_id"], face),
                          "layer": "role_recognition",
                          "profile": roles.ROLE_FROM_CONTENT, "face": face,
                          "family_id": family["family_id"], "kind": "primary"})
            items.append({"item_id": "application:%s:%d" % (family["family_id"], face),
                          "layer": "role_application",
                          "profile": roles.FACE_APPLY, "face": face,
                          "family_id": family["family_id"], "kind": "primary"})
    for position, family in enumerate(families[:DIAGNOSTIC_FAMILIES]):
        for kind in DIAGNOSTIC_KINDS:
            items.append({"item_id": "diagnostic:%s:%s" % (family["family_id"], kind),
                          "layer": "targeted_check",
                          "profile": roles.FACE_APPLY, "face": DIAGNOSTIC_FACE,
                          "family_id": family["family_id"], "kind": kind})
    return items


def panel_manifest(built=None):
    items = panel(built)
    by_layer = Counter(item["layer"] for item in items)
    by_face = Counter()
    for item in items:
        if item["kind"] == "primary":
            by_face["%s:%d" % (item["layer"], item["face"])] += 1
    return {"schema": SCHEMA, "items": len(items),
            "primary_items": sum(1 for item in items if item["kind"] == "primary"),
            "by_layer": dict(by_layer), "by_face": dict(by_face),
            "base_families": len(held_out_families(built)),
            "repeat_note": ("the 192 primary questions are views of 16 base "
                            "families, not 192 independent families"),
            "cue_note": ("the panel carries no face cue in either arm, so it is "
                         "identical across conditions and doubles as the "
                         "cue-removal check"),
            "panel_digest": digest(canonical([item["item_id"] for item in items]))}


# --------------------------------------------------------------------------
# diagnostics: rename, reorder, rewire
# --------------------------------------------------------------------------

def renamed_family(family, style="alpha"):
    """Consistent renaming that preserves every relationship."""
    if style == "alpha":
        labels = tuple("R%d" % (index + 1) for index in range(len(family["labels"])))
    else:
        labels = tuple("unit_%d" % (index + 1)
                       for index in range(len(family["labels"])))
    mapping = dict(zip(family["labels"], labels))
    renamed = dict(family)
    renamed["labels"] = labels
    renamed["branches"] = tuple({"source": mapping[branch["source"]],
                                 "target": mapping[branch["target"]]}
                                for branch in family["branches"])
    renamed["family_id"] = family["family_id"] + ":renamed"
    renamed["original_id"] = family.get("original_id", family["family_id"])
    renamed["kind"] = "a renamed arrangement"
    return renamed, mapping


def reordered_family(family, seed=20260912):
    """Harmless reordering of unordered facts; refused where order is declared."""
    require(family["domain"] != "procedural",
            "FACE_EVAL_REORDER_ORDERED_DOMAIN:" + family["family_id"])
    reordered = dict(family)
    branches = [dict(branch) for branch in family["branches"]]
    random.Random(seed + len(branches)).shuffle(branches)
    reordered["branches"] = tuple(branches)
    reordered["family_id"] = family["family_id"] + ":reordered"
    reordered["original_id"] = family.get("original_id", family["family_id"])
    return reordered


def rewired_family(family):
    """One meaningful rewiring: the answer must change, and to the right one."""
    return tasks._rewired_variant(family)


def diagnostic_item(item, built=None):
    """Compile one diagnostic item and its expected answer under the edit."""
    built = corpus.families() if built is None else built
    families = corpus.family_index(built)
    family = families[item["family_id"]]
    kind = item["kind"]
    if kind == "renamed":
        edited, mapping = renamed_family(family)
        episode = tasks.compile_episode(edited, item["face"], item["profile"],
                                        arm=EVALUATION_ARM, built=built)
        expectation = {"edit": kind, "mapping": mapping,
                       "answer_preserved_under_mapping": True}
    elif kind == "reordered":
        edited = reordered_family(family)
        episode = tasks.compile_episode(edited, item["face"], item["profile"],
                                        arm=EVALUATION_ARM, built=built)
        expectation = {"edit": kind, "answer_preserved": True}
    else:
        edited = rewired_family(family)
        episode = tasks.compile_episode(edited, item["face"], item["profile"],
                                        arm=EVALUATION_ARM, built=built)
        expectation = {"edit": kind, "answer_must_change": True}
    return {"item": item, "episode": episode, "expectation": expectation,
            "edited_family": edited}


def compile_panel_item(item, built=None):
    """Compile one primary panel item: cue-free, unsupported, answer private."""
    built = corpus.families() if built is None else built
    families = corpus.family_index(built)
    family = families[item["family_id"]]
    episode = tasks.compile_episode(family, item["face"], item["profile"],
                                    arm=EVALUATION_ARM, built=built)
    return {"item": item, "episode": episode}


# --------------------------------------------------------------------------
# baselines: what a rule that ignores the content would score
# --------------------------------------------------------------------------

def baselines(items_with_episodes):
    """Constant-rule baselines over the actual panel, reported not assumed.

    These are the comparisons that matter on a panel whose answers are not evenly
    spread: a fixed slot, the most frequent semantic answer category, and the
    longest and shortest option. They are computed from the delivered option
    order, not from the authoring layout.
    """
    total = len(items_with_episodes)
    require(total, "FACE_EVAL_EMPTY_PANEL")
    scores = OrderedDict()
    for slot in range(tasks.OPTIONS_PER_QUESTION):
        scores["always_slot_%d" % slot] = sum(
            1 for entry in items_with_episodes
            if entry["episode"]["encoded_correct_index"] == slot)
    longest = shortest = 0
    for entry in items_with_episodes:
        options = entry["episode"]["encoded_options"]
        index = entry["episode"]["encoded_correct_index"]
        lengths = [len(str(option)) for option in options]
        if lengths[index] == max(lengths):
            longest += 1
        if lengths[index] == min(lengths):
            shortest += 1
    scores["always_longest_option"] = longest
    scores["always_shortest_option"] = shortest
    category_counts = Counter(
        _answer_category(entry) for entry in items_with_episodes)
    majority_category, majority_count = (category_counts.most_common(1)[0]
                                         if category_counts else (None, 0))
    scores["most_frequent_answer_category"] = majority_count
    return {"questions": total, "rules": dict(scores),
            "uniform_random_expectation": round(total / 3, 2),
            "most_frequent_answer_category": majority_category,
            "answer_category_histogram": dict(category_counts),
            "note": ("a rule that ignores the content and always takes one slot, "
                     "the longest option, or the most frequent answer category "
                     "scores as shown; no aggregate above these baselines is "
                     "evidence of the intended skill")}


def _answer_category(entry):
    """The meaning of the correct answer, by profile first and then by role.

    Recognition answers are role labels, so their category is ``role_label``; an
    application answer's category is the semantic kind of the correct option for
    that face. Mixing the two would make the "most frequent answer" baseline
    incomparable across layers, so the layers are classified differently on
    purpose and the baseline is computed per layer.
    """
    target = entry["episode"]["teacher_target"]
    answer = target["correct"]
    if target["profile"] == roles.ROLE_FROM_CONTENT:
        return "role_label"
    face = target["face"]
    if face == 5:
        if isinstance(answer, str) and answer.startswith("["):
            return "empty_inventory" if answer.strip() == "[]" else "inventory"
        if answer in ("direct", "absent"):
            return str(answer)
        return "via_constituent" if str(answer).startswith("via:") else str(answer)
    if face == 3:
        return "analogy_candidate"
    if face == 4:
        return "mapping"
    if face == 6:
        return "recomposition"
    return "statement"


# --------------------------------------------------------------------------
# scoring and reporting
# --------------------------------------------------------------------------

def evaluate(rows_by_layer, *, before_rows=None, built=None):
    """Per-layer, per-face, per-subtype reporting with paired differences.

    ``rows_by_layer`` maps layer name to the per-question rows produced by the
    runner. Nothing is averaged across layers, and a face that fails is reported
    as failing rather than hidden inside a macro figure.
    """
    report = {"schema": SCHEMA, "layers": OrderedDict()}
    for layer, rows in rows_by_layer.items():
        correct = sum(1 for row in rows if row["is_correct"])
        by_face = OrderedDict()
        for row in rows:
            bucket = by_face.setdefault(str(row["face"]), {"correct": 0, "total": 0,
                                                           "subtypes": Counter()})
            bucket["total"] += 1
            bucket["correct"] += 1 if row["is_correct"] else 0
            bucket["subtypes"][row.get("subtype", "unknown")] += 1
        for bucket in by_face.values():
            bucket["accuracy"] = (bucket["correct"] / bucket["total"]
                                  if bucket["total"] else None)
            bucket["subtypes"] = dict(bucket["subtypes"])
        face_accuracies = [bucket["accuracy"] for bucket in by_face.values()
                           if bucket["accuracy"] is not None]
        report["layers"][layer] = {
            "questions": len(rows), "correct": correct,
            "accuracy": (correct / len(rows)) if rows else None,
            "by_face": by_face,
            "macro_accuracy": (sum(face_accuracies) / len(face_accuracies)
                               if face_accuracies else None),
            "minimum_face_accuracy": (min(face_accuracies)
                                      if face_accuracies else None),
            "faces_at_or_above_half": sum(1 for value in face_accuracies
                                          if value >= 0.5),
            "rows": rows,
        }
    if before_rows is not None:
        report["before_after"] = _paired(before_rows, rows_by_layer)
    report["limitations"] = (
        "one paired initialization: this is an exploratory pilot, not multi-seed "
        "replication, and it cannot establish architectural superiority")
    return report


def _paired(before_rows, after_rows):
    """Per-question before/after and between-condition pairing.

    Paired differences need the per-question rows, which is why they are kept:
    the row-level pairing is the only form of this comparison that is valid when
    both conditions answer the same questions.
    """
    paired = OrderedDict()
    for layer, after in after_rows.items():
        before = before_rows.get(layer) or []
        by_id_before = {row["item_id"]: row for row in before}
        only_after = only_before = both = neither = 0
        gained, lost = [], []
        for row in after:
            prior = by_id_before.get(row["item_id"])
            if prior is None:
                continue
            if row["is_correct"] and not prior["is_correct"]:
                only_after += 1
                gained.append(row["item_id"])
            elif prior["is_correct"] and not row["is_correct"]:
                only_before += 1
                lost.append(row["item_id"])
            elif row["is_correct"]:
                both += 1
            else:
                neither += 1
        paired[layer] = {"gained": gained, "lost": lost,
                         "gained_count": only_after, "lost_count": only_before,
                         "both_correct": both, "neither_correct": neither,
                         "discordant_pairs": only_after + only_before,
                         "mcnemar_ready": True}
    return paired


def between_conditions(first_rows, second_rows):
    """Paired comparison between two conditions on the same frozen panel."""
    comparison = OrderedDict()
    for layer in first_rows:
        by_id_first = {row["item_id"]: row for row in first_rows[layer]}
        only_first = only_second = both = neither = 0
        for row in second_rows[layer]:
            other = by_id_first.get(row["item_id"])
            if other is None:
                continue
            if other["is_correct"] and not row["is_correct"]:
                only_first += 1
            elif row["is_correct"] and not other["is_correct"]:
                only_second += 1
            elif row["is_correct"]:
                both += 1
            else:
                neither += 1
        comparison[layer] = {
            "only_first_correct": only_first,
            "only_second_correct": only_second,
            "both_correct": both, "neither_correct": neither,
            "discordant_pairs": only_first + only_second,
            "note": ("McNemar compares the two discordant counts; with zero "
                     "discordant pairs no difference is measurable on this panel")}
    return comparison


def milestone_report(evaluation, *, role_minimum=0.75, application_minimum=0.70,
                     face_minimum=0.50):
    """The plan's provisional advancement targets, as declared targets only."""
    layers = evaluation["layers"]
    recognition = layers.get("role_recognition", {})
    application = layers.get("role_application", {})
    return {
        "targets_are_declared_engineering_targets": True,
        "role_recognition_macro": recognition.get("macro_accuracy"),
        "role_recognition_target": role_minimum,
        "role_recognition_met": (recognition.get("macro_accuracy") or 0)
        >= role_minimum,
        "role_application_macro": application.get("macro_accuracy"),
        "role_application_target": application_minimum,
        "role_application_met": (application.get("macro_accuracy") or 0)
        >= application_minimum,
        "every_face_at_least": face_minimum,
        "faces_below_minimum": {
            layer: {face: bucket["accuracy"]
                    for face, bucket in values.get("by_face", {}).items()
                    if (bucket["accuracy"] or 0) < face_minimum}
            for layer, values in layers.items()},
        "interpretation_rule": ("meeting the capability targets does not establish "
                                "that stable cues beat the control; that is a "
                                "paired comparison, reported separately"),
    }
