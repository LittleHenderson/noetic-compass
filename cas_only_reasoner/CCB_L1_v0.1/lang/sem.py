"""CAS-Sem meanings: propositions and entities, JSON-safe.

A proposition is pred(args...). Negation wraps a proposition. Questions
wrap a proposition. Equality is structural.
"""

from __future__ import annotations

from typing import Dict, List


def proposition(pred: str, *args: str) -> Dict:
    return {"pred": pred, "args": list(args)}


def negation(prop: Dict) -> Dict:
    return {"pred": "negation", "args": [prop]}


def question(prop: Dict) -> Dict:
    return {"pred": "question", "args": [prop]}


def is_question(prop: Dict) -> bool:
    return prop.get("pred") == "question"


def inner(prop: Dict) -> Dict:
    return prop["args"][0]


def propositions_equal(a: Dict, b: Dict) -> bool:
    return a == b


def strip_wrappers(prop: Dict) -> Dict:
    while prop.get("pred") in ("question", "negation"):
        prop = prop["args"][0]
    return prop
