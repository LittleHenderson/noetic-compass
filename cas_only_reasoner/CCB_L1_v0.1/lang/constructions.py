"""CCB-L1 GRAM: the learnable grammar and construction kernel
(apprenticeship Phase L1).

The machine does not learn sentences - it learns CONSTRUCTIONS: a
typed surface pattern plus a semantic transformation, which compose
with the lexicon and morphology to cover unseen sentences.

A construction:
    surface_pattern: ["NP:patient", "was", "VERB:pred:participle",
                      "by", "NP:agent"]
    semantics:       {"frame": "event", "predicate": "@pred",
                      "agent": "@agent", "patient": "@patient",
                      "tense": "past", "polarity": "positive"}
    surface_meta:    {"voice": "passive"}

Semantic FRAMES separate the truth-conditional CORE (predicate,
roles, tense, polarity, quantifier) from SURFACE metadata (voice,
construction id): active and passive of the same event have EQUAL
cores and different surfaces - the minimal-pair law depends on this.

The store is versioned content under the acceptance law: rules are
PROPOSED by lessons, promoted through the ladder in apprentice.py,
and can be QUARANTINED, SUPERSEDED, or ROLLED_BACK. Time is logical;
persistence is digest-checked JSON.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Dict, List, Optional, Tuple

from .grammar import tokenize
from .lexicon import Lexicon

RULE_STATES = ("PROPOSED", "ACTIVE", "QUARANTINED", "SUPERSEDED",
               "ROLLED_BACK")


class ConstructionError(Exception):
    pass


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ----------------------------------------------------------------------
class MorphTable:
    """MORPH v0.1: learnable word-form table. Regular '-ed' stripping
    plus lesson-taught irregulars. Every entry carries provenance."""

    def __init__(self) -> None:
        self.entries: Dict[str, Dict] = {}

    def teach(self, surface: str, lemma: str, form: str,
              provenance: str) -> Dict:
        """MERGE, never clobber (regression-rung finding: a lesson
        teaching 'chased'=past then 'chased'=participle silently
        overwrote the first and broke the active-past rule). The same
        surface+lemma with past AND participle becomes
        past_or_participle; an identical re-teach is a no-op; a
        conflicting overwrite is a typed refusal - prior knowledge is
        protected."""
        existing = self.entries.get(surface)
        if existing is not None and existing["lemma"] == lemma:
            forms = {existing["form"], form}
            if forms <= {"past", "participle", "past_or_participle"} \
                    and len(forms) > 1:
                form = "past_or_participle"
            elif existing["form"] != form:
                raise ConstructionError(
                    f"morphology conflict for {surface!r}: already "
                    f"{existing['form']} (from "
                    f"{existing['provenance']}), refusing overwrite "
                    f"to {form!r}")
        elif existing is not None:
            raise ConstructionError(
                f"morphology conflict for {surface!r}: already lemma "
                f"{existing['lemma']!r}, refusing {lemma!r}")
        entry = {"surface": surface, "lemma": lemma, "form": form,
                 "provenance": provenance}
        self.entries[surface] = entry
        return entry

    def analyze(self, surface: str) -> Optional[Dict]:
        if surface in self.entries:
            return self.entries[surface]
        # regular past/participle: VERBed
        if surface.endswith("ed") and len(surface) > 3:
            stem = surface[:-2]
            candidates = [stem, stem + "e"]
            if len(stem) > 2 and stem[-1] == stem[-2]:
                candidates.append(stem[:-1])          # chopped -> chop
            for lemma in candidates:
                yield_entry = {"surface": surface, "lemma": lemma,
                               "form": "past_or_participle",
                               "provenance": "regular_-ed_rule"}
                return yield_entry
        # regular 3sg present: VERBs
        if surface.endswith("s") and len(surface) > 2:
            return {"surface": surface, "lemma": surface[:-1],
                    "form": "present_3sg",
                    "provenance": "regular_-s_rule"}
        return None

    def to_json(self) -> Dict:
        return copy.deepcopy(self.entries)


# ----------------------------------------------------------------------
def validate_construction(rule: Dict) -> List[str]:
    """SCHEMA_VALID stage: typed defects, never silent coercion."""
    defects: List[str] = []
    if not rule.get("construction_id"):
        defects.append("missing construction_id")
    pattern = rule.get("surface_pattern")
    if not isinstance(pattern, list) or not pattern:
        defects.append("surface_pattern must be a non-empty list")
        return defects
    slot_names = set()
    for element in pattern:
        if not isinstance(element, str) or not element:
            defects.append(f"bad pattern element {element!r}")
        elif element.startswith("NP:"):
            slot_names.add(element.split(":")[1])
        elif element.startswith("VERB:"):
            parts = element.split(":")
            if len(parts) != 3:
                defects.append(f"VERB slot needs name and form: "
                               f"{element!r}")
            else:
                slot_names.add(parts[1])
    semantics = rule.get("semantics")
    if not isinstance(semantics, dict) or semantics.get("frame") \
            not in ("event", "state", "coordination"):
        defects.append("semantics.frame must be 'event', 'state', or "
                       "'coordination'")
        return defects

    def check_refs(node) -> None:
        if isinstance(node, dict):
            for value in node.values():
                check_refs(value)
        elif isinstance(node, list):
            for item in node:
                check_refs(item)
        elif isinstance(node, str) and node.startswith("@"):
            if node[1:] not in slot_names:
                defects.append(f"semantics references unbound slot "
                               f"{node!r}")

    check_refs(semantics)
    if semantics["frame"] == "coordination":
        conjuncts = semantics.get("conjuncts")
        if not isinstance(conjuncts, list) or len(conjuncts) < 2:
            defects.append("coordination frame needs a 'conjuncts' "
                           "list of at least 2 event objects")
        else:
            for conjunct in conjuncts:
                if not isinstance(conjunct, dict) \
                        or conjunct.get("frame") not in ("event",
                                                         "state"):
                    defects.append("each conjunct must be an event or "
                                   "state object")
                else:
                    for required in ("tense", "polarity"):
                        if required not in conjunct:
                            defects.append(f"conjunct missing "
                                           f"{required!r}")
    else:
        for required in ("tense", "polarity"):
            if required not in semantics:
                defects.append(f"semantics missing {required!r}")
    return defects


# ----------------------------------------------------------------------
class ConstructionParser:
    """Compiles constructions against the lexicon + morph table and
    parses token sequences into semantic frames."""

    def __init__(self, lexicon: Lexicon, morph: MorphTable) -> None:
        self.lexicon = lexicon
        self.morph = morph

    # ------------------------------------------------------------------
    def _match_np(self, tokens: List[str], i: int) -> Optional[Tuple[str, int]]:
        """'the NOUN' or bare known NOUN -> (entity sense, next index)."""
        if i < len(tokens) and tokens[i] == "the" and i + 1 < len(tokens):
            entry = self.lexicon.lookup(tokens[i + 1])
            if entry is not None and entry.pos == "noun":
                return entry.sense, i + 2
            return None
        if i < len(tokens):
            entry = self.lexicon.lookup(tokens[i])
            if entry is not None and entry.pos == "noun":
                return entry.sense, i + 1
        return None

    def _match_verb(self, tokens: List[str], i: int,
                    form: str) -> Optional[Tuple[str, int]]:
        if i >= len(tokens):
            return None
        analysis = self.morph.analyze(tokens[i])
        if analysis is None:
            return None
        if form == "participle" and analysis["form"] not in (
                "participle", "past_or_participle"):
            return None
        if form == "past" and analysis["form"] not in (
                "past", "past_or_participle"):
            return None
        if form == "base" and analysis["form"] != "base":
            return None
        if form == "present_3sg" and analysis["form"] != "present_3sg":
            return None
        return analysis["lemma"], i + 1

    # ------------------------------------------------------------------
    def match(self, rule: Dict, sentence: str) -> Optional[Dict]:
        """One construction against one sentence -> bindings or None."""
        tokens = [t for t in tokenize(sentence) if t not in (".", "?")]
        bindings: Dict[str, str] = {}
        i = 0
        for element in rule["surface_pattern"]:
            if element.startswith("NP:"):
                matched = self._match_np(tokens, i)
                if matched is None:
                    return None
                bindings[element.split(":")[1]], i = matched
            elif element.startswith("VERB:"):
                _, name, form = element.split(":")
                matched = self._match_verb(tokens, i, form)
                if matched is None:
                    return None
                bindings[name], i = matched
            else:
                if i >= len(tokens) or tokens[i] != element:
                    return None
                i += 1
        if i != len(tokens):
            return None
        return bindings

    def realize(self, rule: Dict, bindings: Dict[str, str]) -> Dict:
        """Apply the semantic transformation -> a frame with separated
        CORE (truth-conditional) and SURFACE metadata. Resolution is
        RECURSIVE so coordination frames (nested conjunct events)
        realize their @references too."""
        def resolve(node):
            if isinstance(node, dict):
                return {key: resolve(value)
                        for key, value in node.items()}
            if isinstance(node, list):
                return [resolve(item) for item in node]
            if isinstance(node, str) and node.startswith("@"):
                return bindings[node[1:]]
            return node

        return {"core": resolve(rule["semantics"]),
                "surface": {**rule.get("surface_meta", {}),
                            "construction_id": rule["construction_id"]}}

    def parse(self, rules: List[Dict], sentence: str) -> Dict:
        """All ACTIVE constructions against one sentence. Ambiguity is
        REPORTED (distinct cores), never silently resolved."""
        frames = []
        for rule in rules:
            bindings = self.match(rule, sentence)
            if bindings is not None:
                frames.append(self.realize(rule, bindings))
        distinct_cores = []
        for frame in frames:
            if frame["core"] not in distinct_cores:
                distinct_cores.append(frame["core"])
        if not frames:
            return {"status": "UNKNOWN_CONSTRUCTION", "frames": []}
        if len(distinct_cores) > 1:
            return {"status": "AMBIGUOUS_PARSE", "frames": frames,
                    "alternatives": distinct_cores}
        return {"status": "PARSED", "frames": frames,
                "core": distinct_cores[0]}


# ----------------------------------------------------------------------
class GrammarStore:
    """Versioned construction store under the acceptance law."""

    def __init__(self) -> None:
        self.rules: Dict[str, Dict] = {}
        self.revision = 0
        self.history: List[Dict] = []

    def _record(self, action: str, construction_id: str,
                provenance: str) -> None:
        self.revision += 1
        self.history.append({"revision": self.revision,
                             "action": action,
                             "construction_id": construction_id,
                             "provenance": provenance})

    def add_active(self, rule: Dict, provenance: str) -> Dict:
        if rule["construction_id"] in self.rules:
            raise ConstructionError(
                f"construction {rule['construction_id']} already exists")
        stored = copy.deepcopy(rule)
        stored["state"] = "ACTIVE"
        stored["provenance"] = provenance
        stored["rule_digest"] = _digest(rule)
        self.rules[rule["construction_id"]] = stored
        self._record("PROMOTED", rule["construction_id"], provenance)
        return stored

    def quarantine(self, construction_id: str, reason: str) -> Dict:
        rule = self.rules[construction_id]
        rule["state"] = "QUARANTINED"
        self._record("QUARANTINED", construction_id, reason)
        return rule

    def rollback(self, construction_id: str, reason: str) -> Dict:
        rule = self.rules[construction_id]
        rule["state"] = "ROLLED_BACK"
        self._record("ROLLED_BACK", construction_id, reason)
        return rule

    def active_rules(self) -> List[Dict]:
        return [rule for rule in self.rules.values()
                if rule["state"] == "ACTIVE"]

    def to_json(self) -> Dict:
        return {"revision": self.revision,
                "rules": copy.deepcopy(self.rules),
                "history": copy.deepcopy(self.history)}

    def store_digest(self) -> str:
        return _digest(self.to_json())

    def save(self, path: str) -> str:
        payload = self.to_json()
        payload["store_digest"] = self.store_digest()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
        return payload["store_digest"]

    @classmethod
    def load(cls, path: str) -> "GrammarStore":
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        store = cls()
        store.revision = payload["revision"]
        store.rules = payload["rules"]
        store.history = payload["history"]
        claimed = payload.get("store_digest")
        if claimed is not None and store.store_digest() != claimed:
            raise ConstructionError("grammar store digest mismatch: "
                                    "file tampered or corrupted")
        return store
