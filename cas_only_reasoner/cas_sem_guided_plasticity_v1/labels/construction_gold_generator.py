"""construction_gold_generator.py -- Tier A: labels known BY CONSTRUCTION.

The strongest label authority: build the formal CAS record FIRST, then realize a sentence
from it. The label is the construction seed. The sentence never gets to vote on the label.

Pipeline per item:
    formal CAS op (class known)  ->  deterministic surface template + frozen synonym table
    ->  sentence  ->  round-trip parser recovers the seed op  ->  roundtrip_ok gate

Only items whose round-trip recovers the exact seed class are emitted as CONSTRUCTION_GOLD
(claim-bearing). A round-trip failure is excluded, never relabeled.

Deterministic: no randomness -- examples are enumerated in a fixed order from frozen tables.
CPU-only, no model calls. (An OPTIONAL ai_paraphrase lane is specified but disabled here;
paraphrases would still have to pass the same round-trip + semantic-preservation checks and
would form a separate, harder transfer stratum -- never the primary claim-bearing set.)
"""
from __future__ import annotations

from pathlib import Path

import label_common as LC

HERE = Path(__file__).resolve().parent

# Frozen construction tables. Each class = a CAS op + the verbs that realize it in surface text.
CLASS_OPS = {
    "^2": {"op": "attract",  "verbs": ["adored", "cherished", "loved", "favored"],
           "template": "The {a} {v} the {b}.", "slots": ("experiencer", "object")},
    "^3": {"op": "averse",   "verbs": ["detested", "loathed", "shunned", "avoided"],
           "template": "The {a} {v} the {b}.", "slots": ("experiencer", "object")},
    "^6": {"op": "decompose", "verbs": ["dissected", "decomposed", "dismantled", "disassembled"],
           "template": "The {a} {v} the {b} into its parts.", "slots": ("agent", "object")},
    "^8": {"op": "trigger",  "verbs": ["triggered", "evoked", "prompted", "conjured"],
           "template": "The {a} {v} the {b}.", "slots": ("cue", "effect")},
}

SUBJECTS = ["analyst", "student", "engineer", "child", "scientist", "reader"]
OBJECTS_GENERIC = ["argument", "device", "memory", "signal", "picture", "problem"]

# reverse index: verb -> class, used ONLY by the round-trip check (a preservation test),
# never as a labeler of free text.
VERB_TO_CLASS = {}
for _cls, _spec in CLASS_OPS.items():
    for _v in _spec["verbs"]:
        VERB_TO_CLASS[_v] = _cls


def roundtrip_recover(sentence: str, template: str):
    """Recover (class, a, b) from a controlled sentence. Returns None if it cannot parse.

    This confirms the seed survived realization. It is a CHECK, not a labeler: it only works
    on our controlled templates and known verb set.
    """
    ntoks = sentence.rstrip(".").split()
    verbs = [t for t in ntoks if t in VERB_TO_CLASS]
    if len(verbs) != 1:
        return None
    v = verbs[0]
    cls = VERB_TO_CLASS[v]
    # entity slots: token after "The" (a) and the token after the verb (b)
    try:
        vi = ntoks.index(v)
    except ValueError:
        return None
    a = ntoks[vi - 1] if vi - 1 >= 0 else None
    b = ntoks[vi + 2] if vi + 2 < len(ntoks) else (ntoks[vi + 1] if vi + 1 < len(ntoks) else None)
    if not a or not b:
        return None
    return cls, a, b


def generate(n_per_class: int = 10, seed: int = 20260830) -> list[dict]:
    """Deterministically enumerate construction-gold items (fixed order, no RNG)."""
    rule_digest = "n/a-construction"  # construction gold does not depend on the mapping rules
    provenance_base = {
        "frozen_resource_digest": "construction",
        "rule_table_digest": rule_digest,
        "engine_version": LC.ENGINE_VERSION,
        "created_by": "construction_gold_generator",
        "seed": seed,
    }
    packets = []
    for cls, spec in CLASS_OPS.items():
        made = 0
        # deterministic enumeration over subjects x verbs x objects
        combos = []
        for subj in SUBJECTS:
            for v in spec["verbs"]:
                for obj in OBJECTS_GENERIC:
                    combos.append((subj, v, obj))
        for (subj, v, obj) in combos:
            if made >= n_per_class:
                break
            sentence = spec["template"].format(a=subj, v=v, b=obj)
            rec = roundtrip_recover(sentence, spec["template"])
            roundtrip_ok = bool(rec and rec[0] == cls)
            if not roundtrip_ok:
                continue  # excluded, never relabeled
            semantic_graph = {"op": spec["op"], spec["slots"][0]: subj, spec["slots"][1]: obj}
            construction = {
                "construction_seed": f"{cls}:{subj}:{v}:{obj}",
                "noetic": cls,
                "semantic_graph": semantic_graph,
                "template_id": f"tmpl::{cls}",
            }
            packet = LC.make_packet(
                packet_id=f"cg::{cls}::{made:03d}",
                authority="CONSTRUCTION_GOLD",
                cas_label=cls,
                provenance=dict(provenance_base),
                construction=construction,
                surface={"sentence": sentence, "realization_lane": "deterministic", "roundtrip_ok": True},
                fired_rules=[],
                blocked_rules=[],
                abstain_reason=None,
                evidence=None,
            )
            packets.append(packet)
            made += 1
    return packets


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Construction-gold (Tier A) generator.")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--out", default=str(HERE / "reports" / "construction_gold.json"))
    args = ap.parse_args()
    packets = generate(args.n)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    LC.write_json(args.out, packets)
    print(f"generated {len(packets)} construction-gold items -> {args.out}")
