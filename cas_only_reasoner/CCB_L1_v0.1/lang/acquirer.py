"""The word-learning loop: detect, store provisionally, test, promote.

Candidate senses are evaluated under the acceptance law. A sense that
contradicts known grounding facts (antonym conflicts) is rejected by
contrast. Promotion is versioned; the parent lexicon is preserved for
rollback.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Dict, List, Optional

from .acceptance import decide_lexicon
from .grammar import ParseError, parse
from .lexicon import Lexicon
from .sem import propositions_equal


def _meaning_ok(sentence: str, expected: Dict, lexicon: Lexicon) -> bool:
    try:
        meaning, _ = parse(sentence, lexicon)
        return propositions_equal(meaning, expected)
    except ParseError:
        return False


def _contrast_conflict(sense: str, cmb_facts: List[Dict],
                       antonyms: Dict[str, str]) -> Optional[str]:
    """A candidate sense conflicts if some known entity holds a property
    that is its antonym."""
    for fact in cmb_facts:
        if fact.get("pred") == "has" and len(fact.get("args", [])) == 2:
            _, quality = fact["args"]
            if antonyms.get(sense) == quality:
                return (f"sense '{sense}' conflicts with known fact "
                        f"has({fact['args'][0]}, {quality})")
    return None


def _evaluate_sense(word: str, pos: str, sense: str, spec: Dict,
                    parent: Lexicon) -> Dict:
    child = copy.deepcopy(parent)
    child.add_provisional(word, pos, sense, provenance="teacher")

    held_parent: Dict[str, bool] = {}
    held_child: Dict[str, bool] = {}
    for item in spec.get("held_out", []):
        held_parent[item["sentence"]] = _meaning_ok(
            item["sentence"], item["expected"], parent)
        held_child[item["sentence"]] = _meaning_ok(
            item["sentence"], item["expected"], child)

    reg_child: Dict[str, bool] = {}
    reg_parent: Dict[str, bool] = {}
    for item in spec.get("regression", []):
        reg_parent[item["sentence"]] = _meaning_ok(
            item["sentence"], item["expected"], parent)
        reg_child[item["sentence"]] = _meaning_ok(
            item["sentence"], item["expected"], child)

    conflict = _contrast_conflict(sense, spec.get("cmb_facts", []),
                                  spec.get("antonyms", {}))
    contrast = {
        "passed": conflict is None,
        "detail": conflict or "no antonym conflicts with known facts",
    }

    examples_ok = all(
        _meaning_ok(item["sentence"], item["expected"], child)
        for item in spec.get("examples", []))
    if not examples_ok:
        contrast["passed"] = False
        contrast["detail"] = (contrast["detail"] +
                              "; examples do not match the candidate sense")

    decision = decide_lexicon(
        word, sense, parent.to_json(), child.to_json(),
        {"parent": held_parent, "child": held_child},
        {"parent": reg_parent, "child": reg_child},
        contrast)
    decision["examples_ok"] = examples_ok
    return decision


def acquire_word(lexicon: Lexicon, spec: Dict) -> Dict:
    word = spec["word"]
    pos = spec["pos"]
    decisions: List[Dict] = []
    parent_snapshot = copy.deepcopy(lexicon)
    promoted_sense: Optional[str] = None

    for sense in spec.get("candidate_senses", []):
        decision = _evaluate_sense(word, pos, sense, spec, lexicon)
        decisions.append(decision)
        if decision["verdict"] == "PROMOTED" and promoted_sense is None:
            promoted_sense = sense

    if promoted_sense is not None:
        lexicon.add_provisional(word, pos, promoted_sense,
                                provenance="teacher")
        lexicon.promote(word)

    packet = {
        "word": word,
        "pos": pos,
        "candidate_senses": list(spec.get("candidate_senses", [])),
        "decisions": decisions,
        "promoted_sense": promoted_sense,
        "parent_lexicon_digest": _digest(parent_snapshot.to_json()),
        "child_lexicon_digest": _digest(lexicon.to_json()),
    }
    packet["cycle_digest"] = _digest(packet)
    return packet


def _digest(obj: Dict) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
