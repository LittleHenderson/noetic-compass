"""cube_task/build_cube.py -- builds the CUBE TRAIN package's data, weights and frozen settings ON THE LAPTOP, before the
seal (A-CUBE-TRAIN-1..5). Standard library only; no neural code.

    python -B -m cube_task.build_cube --repo <tksCAS worktree> --c45 <c45 ctt_out folder>

Writes data/: train_cube.jsonl (SDG + AI-written TRAIN rows), dev_sdg.jsonl, dev_llm.jsonl, cas_keep.jsonl (20,000 c45
training rows, fixed seed), cas_val.jsonl (2,000 c45 validation rows, fixed seed), vocab.json (c45's), and
DATA_MANIFEST_CUBE.json; weights/<model>.pt (the c45 final weights, checked against their manifests); and
FROZEN_CUBE_TRAIN.json. A row whose target has no pointer in its line is dropped and counted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from cube_task import target  # noqa: E402

MODELS = {"A4-s1": "A4_9p6M", "A4-s2": "A4_9p6M", "A4-s3": "A4_9p6M", "A5-s1": "A5_2p5M"}
CAS_KEEP_SEED, CAS_VAL_SEED = "CUBE-TRAIN-CAS-KEEP-20261022", "CUBE-TRAIN-CAS-VAL-20261022"
FROZEN = {
    "schema": "cube-train.frozen/1",
    "preregistration": "PREREGISTRATION_CUBE_TRAIN.precode.md 6e1afceb + A-CUBE-TRAIN-1..5",
    "direction": "B", "steps": 6000, "batch": 256, "lr": 0.0005, "weight_decay": 0.01, "warmup_steps": 600,
    "schedule": "linear warm-up then cosine to 0 (the c45 train.py rule: warm-up = min(1000, steps // 10))",
    "dropout": 0.1, "grad_clip": 1.0, "precision": "fp32", "checkpoint_scored": "final", "early_stopping": False,
    "mix": {"SDG": 6, "LLM": 1, "CAS": 3},
    "init": "each model starts from its c45 final.pt (pinned below)",
    "seed_rule": "model RNG: sha256('CUBE-TRAIN-<model>-20261022') mod 2^63; batch order: sha256('CUBE TRAIN at 3 USD' "
                 "+ ':' + the sealed zip's sha256) mod 2^63 (the house rule; computed on the host)",
    "gates": {"confident_wrong_sdg_max": 0.01, "confident_wrong_llm_max": 0.02, "confident_wrong_trap_max": 0.01,
              "exercised_sdg_min": 0.40, "exercised_llm_min": 0.25, "keep_old_max_drop": 0.02},
    "vote": "ACCEPT-2: A4-s1, A4-s2, A4-s3 all give the same complete answer",
    "cap_usd": 3, "host": "one AWS g5.xlarge, us-west-2, on demand; the controller stops it at the cap",
    "labels": ["SYNTHETIC_ONLY", "LLM_WRITTEN_STRATUM", "CTT_RETRAINED_V1"],
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write(path: str, rows) -> int:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def _cube_rows(src, stratum: str, drops: dict):
    out = []
    for r in src:
        toks = target.encode_target(r["input"], r["target"])
        if toks is None:
            drops[stratum] = drops.get(stratum, 0) + 1
            continue
        out.append({"direction": "B", "text": r["input"], "target": toks, "truth": r["target"], "kind": r["kind"],
                    "stratum": stratum, "family": r.get("family", "sdg")})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--c45", required=True, help="the c45 ctt_out folder (data/ and runs/)")
    a = ap.parse_args(argv)
    sys.path.insert(0, os.path.join(a.repo, "docs", "working", "helm_cube_oscillation_v1", "cube_train"))
    import rows_ct as R  # the repository's row builder (generator truth)
    data, weights = os.path.join(PKG, "data"), os.path.join(PKG, "weights")
    os.makedirs(data, exist_ok=True)
    os.makedirs(weights, exist_ok=True)
    drops: dict = {}
    sdg_train = R.build_rows(R.TRAIN_BAND, R.TRAIN_ROWS, R.TRAIN_SAYBACK)
    sdg_dev = R.build_dev(sdg_train)
    llm_dir = os.path.join(a.repo, "docs", "working", "helm_cube_oscillation_v1", "cube_train", "llm")
    llm_train = [json.loads(l) for l in open(os.path.join(llm_dir, "rows_llm_train.jsonl"), encoding="utf-8")]
    llm_dev = [json.loads(l) for l in open(os.path.join(llm_dir, "rows_llm_dev.jsonl"), encoding="utf-8")]
    train = _cube_rows(sdg_train, "SDG", drops) + _cube_rows(llm_train, "LLM", drops)
    dev_sdg = _cube_rows(sdg_dev, "DEV_SDG", drops)
    dev_llm = _cube_rows(llm_dev, "DEV_LLM", drops)
    train_texts = {r["text"] for r in train}
    dev_llm = [r for r in dev_llm if r["text"] not in train_texts]
    c45_train = [l for l in open(os.path.join(a.c45, "data", "train.jsonl"), encoding="utf-8") if l.strip()]
    c45_val = [l for l in open(os.path.join(a.c45, "data", "val.jsonl"), encoding="utf-8") if l.strip()]
    keep = [json.loads(c45_train[i]) for i in sorted(random.Random(CAS_KEEP_SEED).sample(range(len(c45_train)), 20000))]
    val = [json.loads(c45_val[i]) for i in sorted(random.Random(CAS_VAL_SEED).sample(range(len(c45_val)), 2000))]
    files = {"train_cube.jsonl": train, "dev_sdg.jsonl": dev_sdg, "dev_llm.jsonl": dev_llm, "cas_keep.jsonl": keep,
             "cas_val.jsonl": val}
    manifest = {"schema": "cube-train.data/1", "files": {}, "counts": {
        "train_sdg": sum(r["stratum"] == "SDG" for r in train), "train_llm": sum(r["stratum"] == "LLM" for r in train),
        "dev_sdg": len(dev_sdg), "dev_llm": len(dev_llm), "dropped_no_pointer": drops},
        "sources": {"sdg": "rows_ct.py (generator truth), bands 2,050M / 2,051M",
                    "llm": "cube_train/llm/rows_llm_{train,dev}.jsonl (four families, two other-family keys)",
                    "cas_keep": "c45 train.jsonl, 20,000 rows, seed " + CAS_KEEP_SEED,
                    "cas_val": "c45 val.jsonl, 2,000 rows, seed " + CAS_VAL_SEED}}
    for name, rows in files.items():
        n = _write(os.path.join(data, name), rows)
        manifest["files"][name] = {"rows": n, "sha256": sha256_file(os.path.join(data, name))}
    shutil.copyfile(os.path.join(a.c45, "data", "vocab.json"), os.path.join(data, "vocab.json"))
    manifest["files"]["vocab.json"] = {"rows": None, "sha256": sha256_file(os.path.join(data, "vocab.json"))}
    with open(os.path.join(data, "DATA_MANIFEST_CUBE.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    frozen = dict(FROZEN, models={})
    for m, cfg in MODELS.items():
        wm = json.load(open(os.path.join(a.c45, "runs", m, "WEIGHTS_MANIFEST.json"), encoding="utf-8"))
        src = os.path.join(a.c45, "runs", m, "final.pt")
        if sha256_file(src) != wm["final_sha256"]:
            raise SystemExit("c45 weights for %s do not match their manifest" % m)
        shutil.copyfile(src, os.path.join(weights, m + ".pt"))
        frozen["models"][m] = {"config": cfg, "init_sha256": wm["final_sha256"], "c45_seed_name": wm["seed_name"]}
    with open(os.path.join(PKG, "FROZEN_CUBE_TRAIN.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(frozen, fh, indent=1, sort_keys=True)
    print(json.dumps(manifest["counts"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
