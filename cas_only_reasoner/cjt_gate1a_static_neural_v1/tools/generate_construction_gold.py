"""generate_construction_gold.py -- the REGISTERED deterministic generator for the
CJT-T1 four-Noetic restricted-slice CONSTRUCTION_GOLD candidate dataset (Gate 1A).

Law (CONSTRUCTION_GOLD_DATASET_SPEC.md): the formal operation exists FIRST; a
deterministic template renders the sentence; the INDEPENDENT checker must recover
the seed operation exactly; failed round trips are EXCLUDED, never relabeled.

Deterministic: single frozen seed 20260831, random.Random only, no wall-clock.
Local execution is permitted in Gate 1A (deterministic dataset generation and
round-trip verification are in the allowed set). NO model, NO GPU, NO network.

The PROTECTED split is generated in-memory, checked, counted, and DIGESTED --
never written to disk in Gate 1A (SPLIT_AND_PROTECTED_EVAL_SPEC.md).
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(HERE))

from independent_roundtrip_checker import check_record  # checker imports NOTHING from here

GATE1A_SEED = 20260831
SIZES = {"train": 6000, "val": 1000, "protected": 1000}
SPLIT_FAMILIES = {"train": ("A", "B"), "val": ("C",), "protected": ("D",)}
SPLIT_BUNDLE = {"train": "T", "val": "V", "protected": "P"}

# RC review fix (bundle-shape confound): every bundle has EXACTLY 6 minds, 8 ideas,
# and 12 parts, so entity-collision statistics match across train/val/protected.
VOCAB = {
    "T": {"minds": ["mira", "tomas", "ilya", "wren", "ada", "kofi"],
          "ideas": ["astronomy", "pottery", "chess", "jazz", "botany",
                    "sailing", "weaving", "algebra"],
          "parts": ["orbits", "spectra", "catalogs", "glazes", "kilns", "wheels",
                    "openings", "endgames", "tactics", "rhythms", "chords", "solos"]},
    "V": {"minds": ["suki", "bram", "noor", "elio", "tamsin", "goran"],
          "ideas": ["falconry", "origami", "calligraphy", "geology",
                    "fencing", "gardening", "ceramics", "astrology"],
          "parts": ["talons", "hoods", "lures", "folds", "creases", "valleys",
                    "inks", "nibs", "strokes", "parries", "lunges", "ripostes"]},
    "P": {"minds": ["zane", "lira", "pavel", "asha", "denton", "yuki"],
          "ideas": ["beekeeping", "archery", "mycology", "cartography",
                    "smithing", "brewing", "falsetto", "topiary"],
          "parts": ["hives", "combs", "swarms", "bows", "arrows", "targets",
                    "spores", "gills", "caps", "anvils", "forges", "bellows"]},
}

TEMPLATES = {
    "^2": {"A": "{m} was drawn to {i}.",
           "B": "{i} pulled {m} toward it.",
           "C": "{m} felt an unmistakable pull toward {i}.",
           "D": "the appeal of {i} captured {m} completely."},
    "^3": {"A": "{m} withdrew from {i}.",
           "B": "{i} repelled {m} from the start.",
           "C": "{m} recoiled whenever {i} came up.",
           "D": "faced with {i}, {m} backed away."},
    "^6": {"A": "{i} broke down into {p1}, {p2}, and {p3}.",
           "B": "inside {i} lay {p1}, {p2}, and {p3}.",
           "C": "{i} could be split into {p1}, {p2}, and {p3}.",
           "D": "three strands made up {i}: {p1}, {p2}, and {p3}."},
    "^8": {"A": "{a} brought {b} to {m}'s mind.",
           "B": "whenever {m} thought of {a}, {b} surfaced.",
           "C": "{a} reminded {m} of {b}.",
           "D": "for {m}, {a} always summoned {b}."},
}

# RC review fix (surface-floor compression): attract/avert carry the clause-type-
# sensitive signal, so they get double weight in the frozen question-type cycle.
QTYPES = ("Q_ATTRACT", "Q_AVERT", "Q_PART", "Q_ATTRACT", "Q_AVERT", "Q_TRIGGER")
QOP = {"Q_ATTRACT": "^2", "Q_AVERT": "^3", "Q_PART": "^6", "Q_TRIGGER": "^8"}


def render(op, family):
    cls = op[0]
    t = TEMPLATES[cls][family]
    if cls in ("^2", "^3"):
        return t.format(m=op[1], i=op[2])
    if cls == "^6":
        return t.format(i=op[1], p1=op[2][0], p2=op[2][1], p3=op[2][2])
    return t.format(m=op[1], a=op[2], b=op[3])


def sample_op(rng, cls, voc, used):
    """Sample one op of class cls honoring the per-passage uniqueness constraints."""
    for _ in range(64):
        if cls == "^2":
            m, i = rng.choice(voc["minds"]), rng.choice(voc["ideas"])
            key = ("^2", m)
            if key not in used:
                used.add(key)
                return ["^2", m, i]
        elif cls == "^3":
            m, i = rng.choice(voc["minds"]), rng.choice(voc["ideas"])
            key = ("^3", m)
            if key not in used:
                used.add(key)
                return ["^3", m, i]
        elif cls == "^6":
            i = rng.choice(voc["ideas"])
            key = ("^6", i)
            if key not in used:
                used.add(key)
                parts = rng.sample(voc["parts"], 3)
                return ["^6", i, parts]
        else:
            m = rng.choice(voc["minds"])
            a, b = rng.sample(voc["ideas"], 2)
            key = ("^8", m, a)
            if key not in used:
                used.add(key)
                return ["^8", m, a, b]
    return None


def sample_distractor(rng, qtype, qop, voc, used):
    """RC review fix (surface-shortcut killer): every passage carries a REGISTERED
    distractor so bare entity co-occurrence cannot answer the question --
      Q_ATTRACT: the questioned mind ALSO averts a different idea (^3 same mind);
      Q_AVERT:   the questioned mind ALSO is drawn to a different idea (^2 same mind);
      Q_PART:    a SECOND idea decomposes into different parts (^6 different idea);
      Q_TRIGGER: the questioned mind has a SECOND trigger with a different source
                 and a different surfaced idea (^8 same mind)."""
    for _ in range(64):
        if qtype == "Q_ATTRACT":
            i = rng.choice([x for x in voc["ideas"] if x != qop[2]])
            key = ("^3", qop[1])
            if key not in used:
                used.add(key)
                return ["^3", qop[1], i]
        elif qtype == "Q_AVERT":
            i = rng.choice([x for x in voc["ideas"] if x != qop[2]])
            key = ("^2", qop[1])
            if key not in used:
                used.add(key)
                return ["^2", qop[1], i]
        elif qtype == "Q_PART":
            i = rng.choice([x for x in voc["ideas"] if x != qop[1]])
            key = ("^6", i)
            if key not in used:
                used.add(key)
                return ["^6", i, rng.sample(voc["parts"], 3)]
        else:
            a = rng.choice([x for x in voc["ideas"] if x not in (qop[2], qop[3])])
            b = rng.choice([x for x in voc["ideas"] if x not in (a, qop[2], qop[3])])
            key = ("^8", qop[1], a)
            if key not in used:
                used.add(key)
                return ["^8", qop[1], a, b]
    return None


def build_passage(rng, split, idx, qtype):
    voc = VOCAB[SPLIT_BUNDLE[split]]
    families = SPLIT_FAMILIES[split]
    n_ops = rng.randint(3, 6)
    used = set()
    qop = sample_op(rng, QOP[qtype], voc, used)        # 1. the question op
    if qop is None:
        return None
    distractor = sample_distractor(rng, qtype, qop, voc, used)   # 2. the distractor
    if distractor is None:
        return None
    ops = [qop, distractor]
    while len(ops) < n_ops:                            # 3. filler ops
        op = sample_op(rng, rng.choice(("^2", "^3", "^6", "^8")), voc, used)
        if op is None:
            return None
        ops.append(op)
    rng.shuffle(ops)                                   # no clause-position leak
    if qtype == "Q_ATTRACT":
        question, answer = f"which idea was {qop[1]} drawn to?", qop[2]
    elif qtype == "Q_AVERT":
        question, answer = f"which idea did {qop[1]} withdraw from?", qop[2]
    elif qtype == "Q_PART":
        k = rng.randint(1, 3)
        question, answer = f"what is part {k} of {qop[1]}?", qop[2][k - 1]
    else:
        question, answer = f"what did {qop[2]} bring to {qop[1]}'s mind?", qop[3]
    fams = [rng.choice(families) for _ in ops]
    clauses = [{"text": render(op, fam), "op_index": j}
               for j, (op, fam) in enumerate(zip(ops, fams))]
    ents = []
    for op in ops:
        for x in (op[1:] if op[0] != "^6" else [op[1], *op[2]]):
            if isinstance(x, str) and x not in ents:
                ents.append(x)
    return {"passage_id": f"{split[0]}{idx:06d}", "split": split,
            "seed_trace": ops, "clauses": clauses,
            "text": " ".join(c["text"] for c in clauses),
            "question": question, "question_type": qtype, "answer": answer,
            "candidates": ents, "idea_labels": [op[0] for op in ops],
            "template_families": fams, "vocab_bundle": SPLIT_BUNDLE[split]}


def canonical_line(rec):
    return json.dumps(rec, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def main():
    rng = random.Random(GATE1A_SEED)
    out_dir = PKG / "data" / "candidate"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"manifest_id": "DATASET_MANIFEST_CANDIDATE",
                "claim_bearing": False,
                "generation_interpreter": sys.version.split()[0],
                "interpreter_law": ("the Gate 1B container regenerates all splits and "
                                    "MUST reproduce every content_sha256 exactly; a "
                                    "Python-version RNG drift therefore fails closed "
                                    "as DATASET_INTEGRITY_FAILURE, never silently"),
                "status": "CANDIDATE (CAS_MAPPING_RULES_v1_CANDIDATE still awaits "
                          "owner approval; nothing here is claim-bearing)",
                "generator_seed": GATE1A_SEED,
                "sizes_requested": dict(SIZES), "splits": {}, "files": {},
                "excluded_roundtrip": {}, "protected_materialized": False}
    for split in ("train", "val", "protected"):
        records, excluded, idx = [], [], 0
        qcycle = 0
        while len(records) < SIZES[split]:
            rec = build_passage(rng, split, idx, QTYPES[qcycle % len(QTYPES)])
            idx += 1
            if rec is None:
                continue
            verdict, reason = check_record(rec)        # INDEPENDENT round trip
            if verdict:
                records.append(rec)
                qcycle += 1                            # keep question types balanced
            else:
                excluded.append({"passage_id": rec["passage_id"], "reason": reason})
        ops_count = {c: 0 for c in ("^2", "^3", "^6", "^8")}
        q_count = {q: 0 for q in QTYPES}
        for r in records:
            q_count[r["question_type"]] += 1
            for lbl in r["idea_labels"]:
                ops_count[lbl] += 1
        body = "\n".join(canonical_line(r) for r in records) + "\n"
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        manifest["splits"][split] = {
            "passages": len(records), "content_sha256": digest,
            "op_class_counts": ops_count, "question_type_counts": q_count,
            "template_families": list(SPLIT_FAMILIES[split]),
            "vocab_bundle": SPLIT_BUNDLE[split]}
        manifest["excluded_roundtrip"][split] = excluded
        if split != "protected":                       # protected is NEVER written
            p = out_dir / f"{split}.jsonl"
            # RC review fix (CRLF split-brain): LF pinned, so the on-disk bytes hash
            # to EXACTLY the content digest on every platform -- one digest per file
            p.write_text(body, encoding="utf-8", newline="\n")
            manifest["files"][f"data/candidate/{split}.jsonl"] = digest
    for tool in ("generate_construction_gold.py", "independent_roundtrip_checker.py"):
        manifest["files"][f"tools/{tool}"] = hashlib.sha256(
            (HERE / tool).read_bytes()).hexdigest()
    manifest["protected_law"] = (
        "the protected split was generated in-memory, independently round-trip "
        "checked, digested, and NOT written; Gate 1B regenerates it from the same "
        "seed on AWS and must reproduce content_sha256 before any evaluation")
    (PKG / "DATASET_MANIFEST_CANDIDATE.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    total_excluded = sum(len(v) for v in manifest["excluded_roundtrip"].values())
    print(f"train={manifest['splits']['train']['passages']} "
          f"val={manifest['splits']['val']['passages']} "
          f"protected={manifest['splits']['protected']['passages']} "
          f"(not written) excluded={total_excluded}")
    print("protected sha256:", manifest["splits"]["protected"]["content_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
