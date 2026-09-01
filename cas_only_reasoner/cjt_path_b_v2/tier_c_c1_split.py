"""tier_c_c1_split.py -- the frozen C1/C2 evaluation partition (owner C1
law 3/4): C1 uses a dedicated C1_TRANSFORM_SELECT split; C2_STRUCTURE_EVAL
remains UNOPENED during C1 (never extracted, never evaluated, never
inspected -- enforcement is at the extraction level: the C1 harness only
ever materializes activations for the C1 half).

Partition law: for each retained-primary val record, HashPRNG
("TIERC_SPLIT|<pid>").randbelow(2) == 0 -> C1_TRANSFORM_SELECT, else
C2_STRUCTURE_EVAL. Deterministic, pid-keyed, frozen before any GPU spend.

Development-only, non-claim-bearing. CPU.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "cjt_gate1a_static_neural_v1"
sys.path.insert(0, str(PKG))
from exec.fsio import write_utf8_lf  # noqa: E402
from exec.prng import HashPRNG  # noqa: E402

PRIMARY = ("QB_REL", "QB_COMP", "QB_INT")


def c1_side(pid: str) -> bool:
    """True -> C1_TRANSFORM_SELECT; False -> C2_STRUCTURE_EVAL."""
    return HashPRNG(f"TIERC_SPLIT|{pid}").randbelow(2) == 0


def build_manifest():
    recs = [json.loads(l) for l in
            (HERE / "data" / "val.jsonl").read_text("utf-8").splitlines()
            if l]
    recs = [r for r in recs if r["question_type"] in PRIMARY]
    c1_pids, c2_pids = [], []
    fam_counts = {"C1": {q: 0 for q in PRIMARY},
                  "C2": {q: 0 for q in PRIMARY}}
    for r in recs:
        if c1_side(r["passage_id"]):
            c1_pids.append(r["passage_id"])
            fam_counts["C1"][r["question_type"]] += 1
        else:
            c2_pids.append(r["passage_id"])
            fam_counts["C2"][r["question_type"]] += 1
    man = {"manifest_id": "TIERC_C1_SPLIT_MANIFEST",
           "non_claim_bearing": True,
           "law": "HashPRNG('TIERC_SPLIT|<pid>').randbelow(2)==0 -> C1",
           "n_val_primary": len(recs),
           "n_c1_transform_select": len(c1_pids),
           "n_c2_structure_eval": len(c2_pids),
           "family_counts": fam_counts,
           "c1_pids_sha256": hashlib.sha256(
               "\n".join(sorted(c1_pids)).encode()).hexdigest(),
           "c2_pids_sha256": hashlib.sha256(
               "\n".join(sorted(c2_pids)).encode()).hexdigest(),
           "c2_enforcement": "the C1 harness materializes activations ONLY "
                             "for C1 pids; C2 pids are never extracted, "
                             "evaluated, or inspected during C1",
           "noise_disclosure": "per-family C1 counts ~185; single-seed "
                               "family-accuracy sd ~ sqrt(.25/185) = .0367; "
                               "3-seed mean se ~ .021 -- the 0.02 family "
                               "margin is ~1 se and is applied by the "
                               "deterministic law regardless"}
    write_utf8_lf(HERE / "tier_c" / "C1_SPLIT_MANIFEST.json",
                  json.dumps(man, indent=2, sort_keys=True) + "\n")
    return man


if __name__ == "__main__":
    m = build_manifest()
    print(json.dumps({k: v for k, v in m.items()
                      if k in ("n_c1_transform_select",
                               "n_c2_structure_eval", "family_counts")},
                     indent=1))
