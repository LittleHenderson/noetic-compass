"""CAS-Sem v0.1 demonstration: bind, check, query, lacunae."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cassem.coherence import CoherenceChecker
from cassem.store import SemanticCMB
from cassem.time import Timeline

ROOT = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(ROOT, "fixtures", name), "r",
              encoding="utf-8") as fh:
        return json.load(fh)


def main():
    print("CAS-Sem v0.1 - the semantic content and binding layer")
    print("=" * 64)

    doc = load("story_good.json")
    cmb = SemanticCMB(doc)
    print("The good story (two entities, two events, four claims):")
    print(f"  coherent: {cmb.coherent()}")
    print(f"  verified claims: {[c['idea'] for c in cmb.by_truth('VERIFIED')]}")
    print(f"  about cat_1: {len(cmb.by_entity('cat_1'))} records")
    timeline = Timeline()
    timeline.assert_order("t1", "t2")
    events = cmb.events_at_or_before("t2", timeline)
    print(f"  events at or before t2: {[e['pred'] for e in events]}")
    derived = cmb.by_truth("DERIVED")
    print(f"  DERIVED claims re-proved by the kernel: "
          f"{[c['idea'] for c in derived]}")

    print()
    print("The six coherence laws, one broken document each:")
    breaks = [
        ("unresolved reference", lambda s: s["references"].append(
            {"kind": "name", "id": "bird_9"})),
        ("time contradiction", lambda s: s["time_assertions"].append(
            {"earlier": "t2", "later": "t1"})),
        ("verified AND contradicted", lambda s: s["claims"].append({
            "idea": {"kind": "property", "entity": "cat_1",
                     "property": "gray"},
            "truth": "CONTRADICTED",
            "provenance": {"source": "book"},
            "conflict": {"a": "observation t1", "b": "book page 9"}})),
        ("missing provenance", lambda s: s["claims"].append({
            "idea": {"kind": "property", "entity": "cat_1",
                     "property": "quiet"},
            "truth": "UNKNOWN"})),
        ("bad derivation", lambda s: s["claims"].append({
            "idea": {"kind": "property", "entity": "cat_1",
                     "property": "brown"},
            "truth": "DERIVED",
            "provenance": {"source": "prior_proof"},
            "derivation": {
                "propositions": [{"pred": "has", "args": ["cat_1", "gray"]}],
                "rules": [{"rule_id": "r_prop",
                           "premises": [{"pred": "has", "args": ["?X", "?Y"]}],
                           "conclusion": {"pred": "property",
                                          "args": ["?X", "?Y"]},
                           "source": "l1_grounding"}],
                "conclusion": {"pred": "property",
                               "args": ["cat_1", "brown"]}}})),
        ("bad roles", lambda s: s["claims"].append({
            "idea": {"kind": "relation", "pred": "chase",
                     "roles": {"agent": "dog_1"}},
            "truth": "GIVEN",
            "provenance": {"source": "teacher"}})),
    ]
    import copy
    for name, mutate in breaks:
        broken = copy.deepcopy(doc)
        mutate(broken)
        laws = [v.law for v in CoherenceChecker(broken).check()]
        print(f"  {name:<28} -> {laws}")
        cmb2 = SemanticCMB(broken)
        if cmb2.lacunae():
            print(f"    lacunae: {[l.to_json() for l in cmb2.lacunae()]}")


if __name__ == "__main__":
    main()
