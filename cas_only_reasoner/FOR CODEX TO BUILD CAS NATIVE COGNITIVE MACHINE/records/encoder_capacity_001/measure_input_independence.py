"""Is the recorded alias concentration a property of the INPUT, or of the WEIGHTS?

Pure standard library. `torch` used **only to deserialise** the frozen checkpoints; every matrix is
pulled out as plain floats and all arithmetic after that is on lists.

Why this test escapes the reconstruction gap
--------------------------------------------
`RECONSTRUCTION_GAP.md` measures the pure-Python rebuild of the **encoder** at +0.781 correlation
with the recorded logits, so nothing that depends on a rebuilt encoded slot can be treated as the
machine's. **This test does not use the encoder at all.** The block, the recurrence and the frozen
readout are all exact for the saved weights and the frozen rows, so feeding *invented* inputs
through them is exact arithmetic on the real trained parameters.

The question
------------
`READOUT_COLLAPSE_RESULT.md` recorded that at cursor 160 the model emits only **9 of the 64 world
aliases** across the 210 world-typed reference slots, with **`W36` at 44.3%** and 55 aliases never
emitted. At cursor 0 the same measurement gave 26 distinct with `W49` at 15.2%. **The cause is
open.**

A concentration can come from two very different places:

* **the input** — the real encoded slots fall in a region where the block's output happens to align
  with a few readout rows, so the machine is reading its input but the input is not varied enough;
* **the weights** — the trained block plus frozen readout has a preferred symbol that it emits
  whatever it is given, so the machine is not reading its input at that slot at all.

Three input regimes separate them, and the third is decisive:

1. **the real encoded slots** (rebuilt, so approximate) — the recorded situation, for reference;
2. **pseudo-random unit vectors** — if these concentrate the same way, the input is not the cause;
3. **one constant vector repeated for every slot** — the extreme case. Whatever the argmax is here
   is what the machine says when it is given no information at all.

Every regime is measured at depth 1 and depth 8, and at both checkpoints, so the block and the
recurrence are separated.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import struct
import sys
from collections import Counter

ARTIFACTS = (
    Path(__file__).resolve().parents[2]
    / "records/typed_matched_001/receipt_20260919_m/collected/results/artifacts"
)
SEED = 20260916
D = 64
LAMBDA = 0.5
EPSILON = 1e-6
DEPTHS = (1, 8)
COUNT = 210

#: The recorded distribution at cursor 160, over the 210 world-typed reference slots.
RECORDED_FINAL = {"distinct": 9, "commonest": "W36", "share": 0.443}
#: The recorded distribution at cursor 0, same slots.
RECORDED_INITIAL = {"distinct": 26, "commonest": "W49", "share": 0.152}


def load_block(name: str) -> dict:
    import torch

    state = torch.load(
        io.BytesIO((ARTIFACTS / name).read_bytes()), map_location="cpu", weights_only=True
    )["model_state"]
    return {
        key.replace(".weight", ""): [
            [float(value) for value in row] for row in state[key].tolist()
        ]
        for key in ("left.weight", "right.weight", "merge.weight")
    }


def block_forward(block, vector):
    left, right, merge = block["left"], block["right"], block["merge"]
    hidden = [math.tanh(sum(a * b for a, b in zip(row, vector))) for row in left]
    hidden += [math.tanh(sum(a * b for a, b in zip(row, vector))) for row in right]
    return [sum(a * b for a, b in zip(row, hidden)) for row in merge]


def run_passes(block, encoded, depth):
    current = [0.0] * D
    input_rms = math.sqrt(math.fsum(v * v for v in encoded) / len(encoded))
    for _ in range(depth):
        state_rms = math.sqrt(math.fsum(v * v for v in current) / len(current))
        scale = LAMBDA * input_rms / math.sqrt(input_rms ** 2 + state_rms ** 2 + EPSILON ** 2)
        incoming = [base + scale * carry for base, carry in zip(encoded, current)]
        current = block_forward(block, incoming)
    return current


def unit(vector):
    norm = math.sqrt(math.fsum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def lcg(count: int, seed: int) -> list:
    """Deterministic pseudo-random unit vectors, from a small LCG so no RNG module is needed."""
    state = seed & 0x7FFFFFFF
    out = []
    for _ in range(count):
        vector = []
        for _ in range(D):
            state = (1103515245 * state + 12345) & 0x7FFFFFFF
            vector.append((state / 0x3FFFFFFF) - 1.0)
        out.append(unit(vector))
    return out


def readout_rows(nclass: int = 64) -> list:
    home = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(home / "research" / "CAS_META_2_COMPOSITION"))
    sys.path.insert(0, str(home))
    from cas_meta2.typed_teaching import binding

    return [
        list(struct.unpack("<64f", binding.row_bytes(["readout", f"W{c}"], seed=SEED, d_model=D)))
        for c in range(nclass)
    ]


def summarise(picks: list, labels: tuple) -> dict:
    counts = Counter(picks)
    total = len(picks)
    commonest, most = counts.most_common(1)[0]
    entropy = -math.fsum(
        (count / total) * math.log2(count / total) for count in counts.values()
    )
    return {
        "slots": total,
        "distinct": len(counts),
        "commonest": commonest,
        "share": most / total,
        "entropy_bits": entropy,
    }


def main() -> int:
    print("loading checkpoints (deserialisation only)...")
    blocks = {"cursor 0": load_block("initial.pt"), "cursor 160": load_block("final.pt")}
    readout = readout_rows()
    labels = tuple(f"W{c}" for c in range(64))

    random_inputs = lcg(COUNT, seed=20260917)
    constant = unit([1.0] * D)
    constant_inputs = [constant] * COUNT

    print(f"probe count per regime: {COUNT}")
    print()

    print("=" * 104)
    print("ALIAS DISTRIBUTION BY INPUT REGIME — recorded baseline at cursor 160: "
          f"{RECORDED_FINAL['distinct']} distinct, {RECORDED_FINAL['commonest']} at "
          f"{100 * RECORDED_FINAL['share']:.1f}%")
    print("=" * 104)
    print()
    print(f"{'checkpoint':>11} {'depth':>6} {'regime':>26} {'distinct':>9} {'commonest':>10}"
          f" {'share':>8} {'entropy':>9}")
    print("-" * 104)
    rows = []
    for checkpoint, block in blocks.items():
        for depth in DEPTHS:
            for label, inputs in (
                ("pseudo-random unit vectors", random_inputs),
                ("ONE constant vector, repeated", constant_inputs),
            ):
                picks = []
                for vector in inputs:
                    final = run_passes(block, vector, depth)
                    scores = [math.fsum(a * b for a, b in zip(row, final)) for row in readout]
                    picks.append(labels[max(range(len(scores)), key=lambda c: scores[c])])
                stats = summarise(picks, labels)
                rows.append((checkpoint, depth, label, stats))
                print(f"{checkpoint:>11} {depth:6d} {label:>26} {stats['distinct']:9d}"
                      f" {stats['commonest']:>10} {100 * stats['share']:7.1f}%"
                      f" {stats['entropy_bits']:9.3f}")
    print()
    print(f"  (a uniform distribution over 64 aliases would be 64 distinct, 1.6% commonest,")
    print(f"   6.000 bits of entropy)")
    print()

    print("=" * 104)
    print("READING")
    print("=" * 104)
    print()
    for checkpoint, depth, label, stats in rows:
        if "constant" in label and depth == 8:
            print(f"  {checkpoint}, depth 8, ONE constant vector: "
                  f"{stats['distinct']} distinct, {stats['commonest']} at "
                  f"{100 * stats['share']:.1f}%")
    print()
    print(
        "The constant-input row is the decisive one. With every slot given the SAME vector, any\n"
        "spread at all comes from the readout's own geometry, and the commonest alias is what the\n"
        "machine says when it is told nothing. If the random-input rows concentrate like the\n"
        "recorded distribution, the concentration is not caused by the inputs; if they stay\n"
        "spread, the inputs are doing the work and the cause lies in the encoder, which this test\n"
        "does not model.\n"
        "\n"
        "Compare the random-input rows against the recorded cursor-160 baseline of 9 distinct\n"
        "with W36 at 44.3%, and against the cursor-0 baseline of 26 distinct with W49 at 15.2%."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
