"""Measure the lacunarity of a CTT training corpus (read-only).

Usage:
    python -X utf8 measure_corpus_lacunarity.py [path/to/train.jsonl]

Defaults to the c45 extract used by design note v1. Prints only; writes nothing.
The numbers in LACUNARITY_CTT_DESIGN_v1.md section 3 come from this script.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter

DEFAULT_TRAIN = (
    "C:/Users/wakil/Documents/Codex/2026-10-19/cas_token_transformer/"
    "run_c45_ctt1_20261020/a1_unpacked/c45_out/ctt_out/data/train.jsonl"
)


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


def main(argv) -> int:
    path = argv[1] if len(argv) > 1 else DEFAULT_TRAIN
    first, tokens, lengths = Counter(), Counter(), Counter()
    rows = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            target = json.loads(line)["target"]
            rows += 1
            first[target[0] if target else "<empty>"] += 1
            lengths[len(target)] += 1
            tokens.update(target)

    total = sum(tokens.values())
    distinct = len(tokens)
    ordered = [c for _t, c in sorted(tokens.items(), key=lambda kv: (-kv[1], kv[0]))]
    entropy = -sum((c / total) * math.log2(c / total) for c in ordered)

    print("rows", rows)
    print("target first token:", dict(first.most_common()))
    print("distinct target tokens:", distinct, "total target tokens:", total)
    print("top-10 token mass: %d / %d = %.4f" % (sum(ordered[:10]), total, sum(ordered[:10]) / total))
    print("token entropy (bits): %.4f  (max %.4f)" % (entropy, math.log2(distinct)))
    print("lacunarity over vocabulary sorted by frequency:")
    for box in (4, 8, 16, 32, 64, 128):
        v = gliding_box(ordered, box)
        if v is not None:
            print("  box=%-4d L=%.3f" % (box, v))
    print("lacunarity over rows sorted by target length:")
    seq = [lengths[k] for k in sorted(lengths)]
    for box in (4, 8, 16, 32):
        v = gliding_box(seq, box)
        if v is not None:
            print("  box=%-4d L=%.3f" % (box, v))
    print("target length distribution:", dict(sorted(lengths.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
