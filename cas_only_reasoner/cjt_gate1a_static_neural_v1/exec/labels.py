"""labels.py -- FROZEN per-arm profile-vector sources (STATIC_CONDITIONS S0-S7).

The S4/S5 corruption formulas are the EXACT strings frozen in
STATIC_CONDITIONS_v3.yaml; hash-int = int(sha256(utf8).hexdigest(), 16).

Runtime-isolation law (audit section 2): corrupted-label arms receive their
profiles from these pure functions at ASSEMBLY time; the assembled example never
carries the gold labels (see dataset_assembly.py), so no arm can read gold at
training runtime.
"""
from __future__ import annotations

import hashlib
import re

CLASSES = ("^2", "^3", "^6", "^8")          # frozen order
_CLASS_INDEX = {c: i for i, c in enumerate(CLASSES)}


def _hash_int(s: str) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest(), 16)


def one_hot(cls: str) -> list:
    v = [0.0, 0.0, 0.0, 0.0]
    v[_CLASS_INDEX[cls]] = 1.0
    return v


def s4_corrupt_label(passage_id: str, idea_index: int, gold_class: str) -> str:
    """Frozen S4 formula: a DIFFERENT class for every Idea, deterministically."""
    others = [c for c in CLASSES if c != gold_class]
    return others[_hash_int(f"S4|{passage_id}|{idea_index}|11") % 3]


def s5_random_label(passage_id: str, idea_index: int) -> str:
    """Frozen S5 formula: clause-independent stable label."""
    return CLASSES[_hash_int(f"S5|{passage_id}|{idea_index}|23") % 4]


def s7_taxonomy_label(clause_text: str, verb_to_class: dict) -> int:
    """S7 (SINGLE_ALTERNATIVE_TAXONOMY) label from the SURFACE head verb only.

    verb_to_class maps each of the 16 registered head verbs to a class index in
    0..3 (the table constructed and digest-pinned at Gate 1B step 3). The lookup
    reads ONLY the clause surface -- never the gold class. Exactly one registered
    verb must occur; anything else fails closed.
    """
    hits = [v for v in verb_to_class
            if re.search(rf"\b{re.escape(v)}\b", clause_text)]
    if len(hits) != 1:
        raise ValueError(f"TAXONOMY_LOOKUP_FAILURE: {len(hits)} registered head "
                         f"verbs in clause {clause_text!r}")
    return verb_to_class[hits[0]]


def profile_vectors(arm_id: str, record: dict, verb_to_class: dict = None):
    """The 4-dim profile vector list for one passage under one arm, or None for
    profile-free arms. Pure; reads only the record and the frozen formulas."""
    labels = record["idea_labels"]
    pid = record["passage_id"]
    if arm_id in ("S0", "S1"):
        return None
    if arm_id in ("S2", "S3"):
        return [one_hot(c) for c in labels]
    if arm_id == "S4":
        return [one_hot(s4_corrupt_label(pid, i, c)) for i, c in enumerate(labels)]
    if arm_id == "S5":
        return [one_hot(s5_random_label(pid, i)) for i in range(len(labels))]
    if arm_id == "S6":
        return [[0.25, 0.25, 0.25, 0.25] for _ in labels]
    if arm_id == "S7":
        if verb_to_class is None:
            raise ValueError("S7 requires the pinned taxonomy verb_to_class table")
        out = []
        for cl in record["clauses"]:
            v = [0.0, 0.0, 0.0, 0.0]
            v[s7_taxonomy_label(cl["text"], verb_to_class)] = 1.0
            out.append(v)
        return out
    raise ValueError(f"unknown arm {arm_id!r}")
