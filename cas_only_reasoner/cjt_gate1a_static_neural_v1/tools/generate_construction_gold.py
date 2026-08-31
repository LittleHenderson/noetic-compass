"""generate_construction_gold.py -- the REGISTERED deterministic generator for the
CJT-T1 four-Noetic restricted-slice CONSTRUCTION_GOLD candidate dataset (Gate 1A).

Law (CONSTRUCTION_GOLD_DATASET_SPEC.md): the formal operation exists FIRST; a
deterministic template renders the sentence; the INDEPENDENT checker must recover
the seed operation exactly; failed round trips are EXCLUDED, never relabeled.

Deterministic: single frozen seed 20260831 driving exec/prng.HashPRNG -- a pure
SHA-256 counter stream, so regeneration is BYTE-IDENTICAL on every CPython >= 3.8.
No wall-clock, no OS entropy. Local execution is permitted in Gate 1A. NO model,
NO GPU, NO network.

BYTE LAW (GATE 1A.1R sections 1-2): every authoritative output is written through
exec/fsio.write_utf8_lf (UTF-8, LF, canonical on every platform), and the frozen
DATASET_MANIFEST contains ONLY environment-invariant facts (algorithm name, code
digests, seed/salt commitment, sizes, content digests, counts). The interpreter
that happened to run the generation is recorded ONLY in the separate runtime
receipt results/generation_runtime_receipt.json (excluded from the frozen tree).
The 3.14-vs-3.11 manifest drift defect is thereby removed structurally.

Modes (GATE 1A.1R sections 3-4):
  (default)                  write train/val + DATASET_MANIFEST to --output-root
                             (default: the package itself -- Gate 1A freeze use)
  --output-root <path>       write to a non-frozen destination; Gate 1B MUST use
                             this (results/<campaign>/regenerated_dataset/) and
                             never mutates the frozen tree
  --check                    WRITE-FREE: regenerate in memory, byte-compare
                             train/val/manifest against the frozen package files,
                             print every mismatch, exit nonzero on any

The PROTECTED split is generated in-memory, checked, counted, and DIGESTED --
never written to disk in Gate 1A (SPLIT_AND_PROTECTED_EVAL_SPEC.md).

Protected-derivation options (owner decision, audit section 9):
  default             -- protected drawn from the same public stream: reconstructible
                         by anyone (INTEGRITY-ONLY; never called secret).
  --protected-salt-hex XX..  -- protected drawn from a FRESH stream domain
                         "CONSTRUCTION_GOLD_PROTECTED|<seed>|<salt-hex>"; the
                         manifest records ONLY sha256(salt-hex utf-8) as the
                         commitment. The salt stays with the owner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PKG))

from independent_roundtrip_checker import check_record  # checker imports NOTHING from here
from exec.prng import HashPRNG
from exec.fsio import write_utf8_lf

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


def generate_all(protected_salt_hex=None):
    """Pure in-memory generation. Returns (bodies, manifest_obj) where bodies maps
    split -> canonical LF bytes. NOTHING is written here; the manifest contains
    ONLY environment-invariant facts (GATE 1A.1R section 2)."""
    rng = HashPRNG(f"CONSTRUCTION_GOLD|{GATE1A_SEED}")
    if protected_salt_hex is not None:
        salt = protected_salt_hex.strip().lower()
        if not salt or any(c not in "0123456789abcdef" for c in salt):
            raise ValueError("--protected-salt-hex must be nonempty lowercase hex")
        protected_rng = HashPRNG(f"CONSTRUCTION_GOLD_PROTECTED|{GATE1A_SEED}|{salt}")
        derivation = ("SALT_SHA256:"
                      + hashlib.sha256(salt.encode("utf-8")).hexdigest())
    else:
        protected_rng = rng                       # status quo: one public stream
        derivation = f"PUBLIC_SEED_{GATE1A_SEED}"
    manifest = {
        "manifest_id": "DATASET_MANIFEST_CANDIDATE",
        "claim_bearing": False,
        "generator_algorithm": "HashPRNG_SHA256_COUNTER_V1",
        "generator_code_sha256": hashlib.sha256(
            (HERE / "generate_construction_gold.py").read_bytes()).hexdigest(),
        "checker_code_sha256": hashlib.sha256(
            (HERE / "independent_roundtrip_checker.py").read_bytes()).hexdigest(),
        "compatibility_claim": ("the generation algorithm is defined independently "
                                "of CPython helper RNGs (pure SHA-256 counter "
                                "stream + rejection sampling); regeneration is "
                                "byte-identical on every CPython >= 3.8"),
        "byte_law": ("all authoritative outputs are written via "
                     "exec/fsio.write_utf8_lf (UTF-8, LF, canonical on every "
                     "platform); the runtime interpreter is recorded ONLY in the "
                     "separate runtime receipt, never in this frozen manifest"),
        "regeneration_law": ("Gate 1B regenerates all splits to a NON-FROZEN "
                             "--output-root and every content_sha256 MUST equal "
                             "this manifest exactly (DATASET_INTEGRITY_FAILURE "
                             "otherwise, never silent); the frozen package tree "
                             "is never mutated during execution"),
        "protected_derivation": derivation,
        "status": "CANDIDATE (CAS_MAPPING_RULES_v1_CANDIDATE still awaits "
                  "owner approval; nothing here is claim-bearing)",
        "generator_seed": GATE1A_SEED,
        "sizes_requested": dict(SIZES), "splits": {}, "files": {},
        "excluded_roundtrip": {}, "protected_materialized": False}
    bodies = {}
    for split in ("train", "val", "protected"):
        srng = protected_rng if split == "protected" else rng
        records, excluded, idx = [], [], 0
        qcycle = 0
        while len(records) < SIZES[split]:
            rec = build_passage(srng, split, idx, QTYPES[qcycle % len(QTYPES)])
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
        bodies[split] = body.encode("utf-8")
        digest = hashlib.sha256(bodies[split]).hexdigest()
        manifest["splits"][split] = {
            "passages": len(records), "content_sha256": digest,
            "op_class_counts": ops_count, "question_type_counts": q_count,
            "template_families": list(SPLIT_FAMILIES[split]),
            "vocab_bundle": SPLIT_BUNDLE[split]}
        manifest["excluded_roundtrip"][split] = excluded
        if split != "protected":                       # protected is NEVER written
            manifest["files"][f"data/candidate/{split}.jsonl"] = digest
    manifest["protected_law"] = (
        "the protected split was generated in-memory, independently round-trip "
        "checked, digested, and NOT written; Gate 1B regenerates it (same seed, "
        "or the owner-held salt) to a non-frozen destination and must reproduce "
        "content_sha256 before any evaluation")
    return bodies, manifest


def manifest_bytes(manifest) -> bytes:
    return (json.dumps(manifest, indent=2) + "\n").encode("utf-8")


def run_check(bodies, manifest) -> int:
    """WRITE-FREE check mode: byte-compare regenerated content against the frozen
    package files; print every mismatch; exit nonzero on any (GATE 1A.1R s.4)."""
    mismatches = []
    for split in ("train", "val"):
        frozen = PKG / "data" / "candidate" / f"{split}.jsonl"
        if not frozen.is_file():
            mismatches.append(f"{frozen.name}: MISSING from the package")
        elif frozen.read_bytes() != bodies[split]:
            mismatches.append(
                f"data/candidate/{split}.jsonl: bytes differ (frozen sha "
                f"{hashlib.sha256(frozen.read_bytes()).hexdigest()[:16]}..., "
                f"regenerated sha "
                f"{hashlib.sha256(bodies[split]).hexdigest()[:16]}...)")
    frozen_manifest = PKG / "DATASET_MANIFEST_CANDIDATE.json"
    if not frozen_manifest.is_file():
        mismatches.append("DATASET_MANIFEST_CANDIDATE.json: MISSING")
    elif frozen_manifest.read_bytes() != manifest_bytes(manifest):
        mismatches.append(
            "DATASET_MANIFEST_CANDIDATE.json: bytes differ (frozen sha "
            f"{hashlib.sha256(frozen_manifest.read_bytes()).hexdigest()[:16]}..., "
            f"regenerated sha "
            f"{hashlib.sha256(manifest_bytes(manifest)).hexdigest()[:16]}...)")
    if mismatches:
        for m in mismatches:
            print(f"CHECK_FAIL: {m}")
        return 1
    print("GENERATOR_CHECK_PASS: train/val/manifest byte-identical; protected "
          f"digest {manifest['splits']['protected']['content_sha256']}")
    return 0


def write_outputs(bodies, manifest, output_root: Path):
    """Write mode: authoritative files via the canonical writer; the runtime
    receipt (environment-OBSERVED facts) goes to results/, never the frozen set."""
    import platform
    out_dir = output_root / "data" / "candidate"
    for split in ("train", "val"):
        write_utf8_lf(out_dir / f"{split}.jsonl", bodies[split].decode("utf-8"))
    write_utf8_lf(output_root / "DATASET_MANIFEST_CANDIDATE.json",
                  manifest_bytes(manifest).decode("utf-8"))
    receipt = {
        "receipt_id": "GENERATION_RUNTIME_RECEIPT",
        "law": ("environment-OBSERVED facts live HERE, never in the frozen "
                "dataset manifest (GATE 1A.1R section 2)"),
        "python_version": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "os": platform.platform(),
        "container_digest": "not_applicable_local_generation",
        "dependency_lock_sha256": "not_applicable_local_generation",
        "invocation": sys.argv,
        "generated_output_digests": {
            "data/candidate/train.jsonl": manifest["splits"]["train"]["content_sha256"],
            "data/candidate/val.jsonl": manifest["splits"]["val"]["content_sha256"],
            "protected (in-memory only)": manifest["splits"]["protected"]["content_sha256"],
            "DATASET_MANIFEST_CANDIDATE.json": hashlib.sha256(
                manifest_bytes(manifest)).hexdigest()}}
    write_utf8_lf(output_root / "results" / "generation_runtime_receipt.json",
                  json.dumps(receipt, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--protected-salt-hex", default=None,
                    help="OWNER-HELD salt (hex). Protected split derives from a "
                         "fresh salted stream; only sha256(salt) is recorded.")
    ap.add_argument("--output-root", default=None,
                    help="destination root (default: the package -- Gate 1A "
                         "freeze use only; Gate 1B MUST pass a non-frozen root)")
    ap.add_argument("--check", action="store_true",
                    help="write-free: regenerate in memory and byte-compare "
                         "against the frozen package files; nonzero on mismatch")
    args = ap.parse_args()
    try:
        bodies, manifest = generate_all(args.protected_salt_hex)
    except ValueError as exc:
        print(f"REFUSED: {exc}")
        return 1
    if args.check:
        if args.output_root is not None:
            print("REFUSED: --check writes nothing; --output-root is meaningless")
            return 1
        return run_check(bodies, manifest)
    output_root = Path(args.output_root) if args.output_root else PKG
    write_outputs(bodies, manifest, output_root)
    total_excluded = sum(len(v) for v in manifest["excluded_roundtrip"].values())
    print(f"train={manifest['splits']['train']['passages']} "
          f"val={manifest['splits']['val']['passages']} "
          f"protected={manifest['splits']['protected']['passages']} "
          f"(not written) excluded={total_excluded} -> {output_root}")
    print("protected sha256:", manifest["splits"]["protected"]["content_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
