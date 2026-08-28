"""CCB-L1 orchestrator: the full English-to-CAS-to-English pipeline.

English in at the edges, the unchanged kernel reasoning in the middle,
English out. The lexicon is content: it learns under the acceptance law.
"""

from __future__ import annotations

import copy
from typing import Dict, List, Optional

from .acquirer import acquire_word
from .discourse import Discourse
from .grammar import ParseError, generate, parse, tokenize
from .kernel_bridge import answer_question, decode_verdict
from .lexicon import Lexicon, LexiconError


class CCB_L1:
    def __init__(self, seed: Dict) -> None:
        self.lexicon = Lexicon(seed.get("lexicon", {}))
        self.cmb_facts: List[Dict] = list(seed.get("cmb_facts", []))
        self.rules: List[Dict] = list(seed.get("rules", []))
        self.discourse = Discourse()
        self.history: List[Dict] = [{
            "lexicon_digest": _digest(self.lexicon.to_json())}]

    # ----------------------------------------------------------------
    def parse(self, sentence: str) -> Dict:
        meaning, self.discourse = parse(sentence, self.lexicon, self.discourse)
        return meaning

    def generate(self, meaning: Dict) -> str:
        return generate(meaning, self.lexicon)

    def roundtrip(self, sentence: str) -> Dict:
        meaning = self.parse(sentence)
        surface = self.generate(meaning)
        meaning2 = self.parse(surface)
        return {"original": sentence, "meaning": meaning,
                "surface": surface, "meaning2": meaning2,
                "stable": meaning == meaning2}

    # ----------------------------------------------------------------
    def ask(self, question_sentence: str) -> Dict:
        meaning = self.parse(question_sentence)
        result = answer_question(meaning, self.cmb_facts, self.rules)
        answer = decode_verdict(result["kernel_packet"], result["meaning"])
        return {"question": question_sentence, "meaning": meaning,
                "kernel_status": result["kernel_packet"]["terminal_status"],
                "answer": answer}

    # ----------------------------------------------------------------
    def teach(self, spec: Dict) -> Dict:
        cycle = acquire_word(self.lexicon, spec)
        self.history.append({"lexicon_digest": _digest(self.lexicon.to_json())})
        return cycle

    def correct(self, word: str, new_sense: str) -> Dict:
        before = copy.deepcopy(self.lexicon.to_json())
        self.lexicon.correct(word, new_sense, provenance="correction")
        after = self.lexicon.to_json()
        entry = after[word]
        return {
            "action": "CORRECTION",
            "word": word,
            "new_sense": new_sense,
            "revision": entry["revision"],
            "history": entry["history"],
            "before_digest": _digest(before),
            "after_digest": _digest(after),
        }

    def rollback(self) -> Dict:
        if len(self.history) <= 1:
            return {"action": "ROLLBACK", "note": "nothing to restore"}
        return {"action": "ROLLBACK",
                "note": "parent lexicon digest "
                        f"{self.history[0]['lexicon_digest']}"}


def _digest(obj: Dict) -> str:
    import hashlib
    import json
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
