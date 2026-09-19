"""Does the pointer machine's ^6 block start from the practice study's own weights?

Replaces the first version of this probe, which compared raw tensor digests only and used
an ad-hoc digest. This version uses the learner's OWN identity algorithm
(`learner.state_identity`, learner.py:47-61) so the fresh build is compared against exactly
the value the practice study recorded in `metadata.model_state_identity`.

Dev-only check on the local RTX 4070. NOT claim-bearing. $0. No AWS. No training, no
claim-bearing evaluation. Reads existing checkpoints read-only.

Run from a short working directory (the deep OneDrive path can break process start):
    python -B <path to this file>
"""
import hashlib
import json
import math
import sys
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD "
            r"CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX "
            r"TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research" / "CAS_META_2_COMPOSITION")]

import torch  # noqa: E402
from cncm import typed_matched_worker as matched  # noqa: E402
from cas_meta2.typed_teaching import source as _source  # noqa: E402

SEEDS = (20260917, 20260918, 20260919)
CKPT = CNCM / "records" / "typed_practice_001"


def canon(value):
    """Mirror of source.canonical: sorted-key compact JSON, utf-8 bytes."""
    import json as _json
    return _json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def state_identity(sd):
    """Exact copy of learner.state_identity (learner.py:47-61)."""

    def walk(node):
        if torch.is_tensor(node):
            assert not node.is_sparse, "TYPED_STATE_SPARSE"
            raw = bytes(node.detach().contiguous().reshape(-1).view(torch.uint8).cpu().tolist())
            return {"type": "tensor", "dtype": str(node.dtype), "shape": list(node.shape),
                    "sha256": hashlib.sha256(raw).hexdigest()}
        if type(node) is dict:
            return {"type": "dict", "items": [[type(k).__name__, k, walk(node[k])]
                                              for k in sorted(node, key=lambda k: (type(k).__name__, str(k)))]}
        if type(node) in (list, tuple):
            return {"type": type(node).__name__, "items": [walk(v) for v in node]}
        assert type(node) in (str, int, float, bool, type(None))
        return {"type": type(node).__name__, "value": node}

    return hashlib.sha256(canon(walk(sd))).hexdigest()


def raw_digest(sd):
    h = hashlib.sha256()
    for key in sorted(sd):
        t = sd[key].detach().to("cpu").to(torch.float64).contiguous()
        h.update(key.encode("utf-8"))
        h.update(str(tuple(t.shape)).encode("utf-8"))
        h.update(t.numpy().tobytes())
    return h.hexdigest()


out = {"device": torch.cuda.get_device_name(0), "torch": torch.__version__, "seeds": {}}

for seed in SEEDS:
    path = CKPT / ("receipt_%d" % seed) / "checkpoints" / "initial.pt"
    ck = torch.load(path, weights_only=True)
    # export_checkpoint stores a PLAIN dict (learner.py:298 wraps in dict()), and
    # state_identity requires type(node) is dict, so unwrap the same way here.
    ck_sd = dict(ck["model_state"])
    recorded = ck["metadata"]["model_state_identity"]

    # Sanity: can we reproduce the recorded identity from the checkpoint itself?
    recomputed = state_identity(ck_sd)

    fw = matched._framework(torch, "cuda", seed)
    fresh_sd = dict(fw.module.state_dict())

    row = {
        "checkpoint_keys": sorted(ck_sd),
        "fresh_keys": sorted(fresh_sd),
        "same_key_set": sorted(ck_sd) == sorted(fresh_sd),
        "recorded_model_state_identity": recorded,
        "recomputed_from_checkpoint": recomputed,
        "SANITY_ALGORITHM_MATCHES": recomputed == recorded,
        "fresh_state_identity": state_identity(fresh_sd),
        "FRESH_EQUALS_RECORDED_START": state_identity(fresh_sd) == recorded,
        "checkpoint_raw_digest": raw_digest(ck_sd),
        "fresh_raw_digest": raw_digest(fresh_sd),
    }
    # Where do the numbers actually differ? Per-tensor max abs difference.
    diffs = {}
    for key in sorted(set(fresh_sd) & set(ck_sd)):
        a = fresh_sd[key].detach().to("cpu").to(torch.float64)
        b = ck_sd[key].detach().to("cpu").to(torch.float64)
        diffs[key] = {"shape": list(a.shape), "max_abs_diff": float((a - b).abs().max()),
                      "fresh[0,0]": float(a.reshape(-1)[0]), "checkpoint[0,0]": float(b.reshape(-1)[0])}
    row["per_tensor"] = diffs
    out["seeds"][str(seed)] = row
    print(json.dumps({str(seed): row}, indent=2, sort_keys=True), flush=True)

print()
print("SUMMARY")
for seed in SEEDS:
    r = out["seeds"][str(seed)]
    print(json.dumps({"seed": seed, "sanity": r["SANITY_ALGORITHM_MATCHES"],
                      "fresh_equals_recorded_start": r["FRESH_EQUALS_RECORDED_START"],
                      "max_abs_diff_worst": max(v["max_abs_diff"] for v in r["per_tensor"].values())},
                     sort_keys=True), flush=True)
