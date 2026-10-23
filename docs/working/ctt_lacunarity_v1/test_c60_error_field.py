"""Measure the error-field lacunarity of the real C60 (mouth v2) language run.

Scores the trained checkpoints on the held-out mouth dev split (English replies) and computes,
per row, the gliding-box lacunarity of the per-token negative log-likelihood at boxes 4, 16, 64.
That is the R1 measurement of the design note, on the actual CTT-v2 language run.

Usage (the laptop's RTX 4070 is enough; diagnostic only):
    <python-with-cuda> test_c60_error_field.py --checkpoint <final.pt> --config A4_9p6M \
        --payload <payload root> --rows 1500

torch.no_grad only. No training, no optimiser step, nothing written except stdout.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path


def gliding_box(values, box):
    n = len(values)
    if box < 1 or n < box or sum(values) <= 0:
        return None
    window = float(sum(values[:box]))
    windows = [window]
    for i in range(box, n):
        window += values[i] - values[i - box]
        windows.append(window)
    mean = sum(windows) / len(windows)
    var = sum((w - mean) ** 2 for w in windows) / len(windows)
    return 1.0 + var / (mean * mean)


def summarise(values):
    if not values:
        return None
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "median": round(statistics.median(ordered), 4),
        "mean": round(sum(ordered) / len(ordered), 4),
        "p10": round(ordered[int(0.1 * (len(ordered) - 1))], 4),
        "p90": round(ordered[int(0.9 * (len(ordered) - 1))], 4),
        "share_le_1_05": round(sum(1 for v in ordered if v <= 1.05) / len(ordered), 4),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--config", required=True, choices=("A4_9p6M", "A5_2p5M"))
    ap.add_argument("--payload", required=True)
    ap.add_argument("--rows", type=int, default=1500)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--file", default="mouth_dev.jsonl",
                    help="data file under <payload>/data to score (mouth_dev.jsonl, mouth_train.jsonl)")
    a = ap.parse_args(argv)

    import torch

    sys.path.insert(0, a.payload)
    from helm_cas_translator import model as M, param_count
    from helm_cas_translator.vocab import BOS, PAD
    from mouth_task.vocab_m import VocabM, base

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise SystemExit("GPU_REQUIRED: no CUDA device")

    vm = VocabM(base(str(Path(a.payload) / "data" / "vocab.json")))
    cfg = param_count.CONFIGS[a.config]
    net = M.CTTModel.from_config(len(vm), cfg, dropout=0.0).to(device)
    state = torch.load(a.checkpoint, map_location=device)
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    missing, unexpected = net.load_state_dict(state, strict=False)
    if missing or unexpected:
        print("LOAD MISMATCH", {"missing": missing[:5], "unexpected": unexpected[:5]})
        return 2
    net.eval()

    rows = []
    with open(Path(a.payload) / "data" / a.file, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
            if len(rows) >= a.rows:
                break

    srcs, tgts = [], []
    for r in rows:
        srcs.append(vm.encode_mouth_source(r["situation"], tuple(r["tone"]), r["input_text"],
                                           tuple(r["style"]) if r.get("style") else None))
        tgts.append(vm.encode_mouth_target(r["target"]))

    per_row_l = {4: [], 16: [], 64: []}
    total_tokens, total_nll, row_means, saturated = 0, 0.0, [], 0

    with torch.no_grad():
        for start in range(0, len(rows), a.batch):
            idx = list(range(start, min(len(rows), start + a.batch)))
            src = M.pad_batch([srcs[i] for i in idx], device)
            tgt_out = M.pad_batch([tgts[i] for i in idx], device)
            tgt_in = M.pad_batch([[BOS] + tgts[i][:-1] for i in idx], device)
            logp = net(src, tgt_in)
            nll = -logp.gather(-1, tgt_out.unsqueeze(-1)).squeeze(-1)
            mask = tgt_out.ne(PAD)
            for j, _i in enumerate(idx):
                vec = nll[j][mask[j]].tolist()
                if not vec:
                    continue
                total_tokens += len(vec)
                total_nll += sum(vec)
                mean = sum(vec) / len(vec)
                row_means.append(mean)
                if mean <= 1e-6:
                    saturated += 1
                for box in per_row_l:
                    value = gliding_box(vec, box)
                    if value is not None:
                        per_row_l[box].append(value)

    result = {
        "checkpoint": str(a.checkpoint),
        "config": a.config,
        "device": torch.cuda.get_device_name(0),
        "rows_scored": len(row_means),
        "file": a.file,
        "tokens": total_tokens,
        "mean_token_nll": round(total_nll / max(1, total_tokens), 6),
        "mean_row_nll": round(sum(row_means) / max(1, len(row_means)), 6),
        "saturated_rows": saturated,
        "lacunarity": {str(b): summarise(v) for b, v in per_row_l.items()},
    }
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

