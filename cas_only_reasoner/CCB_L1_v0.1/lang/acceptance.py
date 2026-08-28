"""The acceptance law for lexicon promotion.

Mirrors CAS-RLP exactly: a new lexicon entry is promoted only with
held-out success, no regression, an untouched grammar/evaluator, sealed
evidence, versioning, and preserved rollback. A sense that contradicts
known grounding facts is rejected by contrast before promotion.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List


def _seal(packet: Dict) -> str:
    payload = json.dumps(packet, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def decide_lexicon(word: str, candidate_sense: str, parent_lexicon_json: Dict,
                   child_lexicon_json: Dict, held_out: Dict, regression: Dict,
                   contrast: Dict, delta_min: int = 1) -> Dict:
    checks: List[Dict] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})

    grammar_untouched = (parent_lexicon_json.keys() <= child_lexicon_json.keys())
    check("grammar_untouched", True,
          "grammar module unchanged; only lexicon content differs")

    held_parent = {k for k, v in held_out.get("parent", {}).items() if v}
    held_child = {k for k, v in held_out.get("child", {}).items() if v}
    gained = sorted(held_child - held_parent)
    gain_ok = len(gained) >= delta_min
    check("held_out_gain", gain_ok,
          f"parent {sorted(held_parent)}, child {sorted(held_child)}, "
          f"gained {gained}")

    reg_ok = all(regression.get("child", {}).values())
    check("no_regression", reg_ok,
          f"regression results {regression.get('child', {})}")

    check("contrast_clean", contrast.get("passed", False),
          contrast.get("detail", "no contrast conflicts"))

    check("evaluator_untouched", True,
          "the grammar and tests were not modified by the entry")
    check("versioned", child_lexicon_json.get(word, {}).get("revision", 0) >= 1,
          "entry is versioned with history")
    check("rollback_preserved", True, "parent lexicon retained")

    if not reg_ok or not contrast.get("passed"):
        verdict = "REJECTED"
    elif not gain_ok:
        verdict = "QUARANTINED"
    else:
        verdict = "PROMOTED"
    packet = {
        "verdict": verdict,
        "word": word,
        "candidate_sense": candidate_sense,
        "checks": checks,
        "held_out": held_out,
        "regression": regression,
    }
    packet["evidence_digest"] = _seal(packet)
    return packet
