"""Is the alias concentration general, or specific to one run? Measure all six.

Pure standard library. `torch` used **only to deserialise** the six runs' checkpoints. Two
measurements per run, and the first needs no rebuild at all:

1. **THE RECORDED DISTRIBUTION.** From each run's own `initial_predictions.json` and
   `final_predictions.json`, the aliases the model actually emitted at the world-typed reference
   slots. This is read straight from the worker's records — **no encoder rebuild, nothing
   reconstructed**, so `RECONSTRUCTION_GAP.md` does not touch it.
2. **THE TASK-FREE DISTRIBUTION.** 210 pseudo-random unit vectors through each run's `initial.pt`
   and `final.pt` at depth 1 and depth 8. The block, the recurrence and the frozen readout are exact
   for the saved weights, so this is exact arithmetic on the real trained parameters and again needs
   no encoder.

Why this matters
----------------
`READOUT_COLLAPSE_RESULT.md` and `CONCENTRATION_SOURCE_RESULT.md` measured that at cursor 160 the
model emits only **9 of the 64 world aliases** with **`W36` at 44.3%**, and that training — not the
readout's geometry and not the inputs — is the largest cause. **Both were measured on
`receipt_20260919_m` alone.** Round 23 discharged the "one arm, one seed" caveat for the
decision-shape decomposition; this does the same for the concentration, or shows it does not hold.
"""

from __future__ import annotations

import io
import json
import math
from pathlib import Path
import struct
import sys
from collections import Counter

HOME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

RECEIPTS = HOME / "records/typed_matched_001"
SEED = 20260916
D = 64
LAMBDA = 0.5
EPSILON = 1e-6
DEPTHS = (1, 8)
COUNT = 210
ALIAS = tuple(f"W{c}" for c in range(64))


def unit(vector):
    norm = math.sqrt(math.fsum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def lcg(count: int, seed: int) -> list:
    state = seed & 0x7FFFFFFF
    out = []
    for _ in range(count):
        vector = []
        for _ in range(D):
            state = (1103515245 * state + 12345) & 0x7FFFFFFF
            vector.append((state / 0x3FFFFFFF) - 1.0)
        out.append(unit(vector))
    return out


def load_matrices(path: Path) -> dict:
    import torch

    state = torch.load(
        io.BytesIO(path.read_bytes()), map_location="cpu", weights_only=True
    )["model_state"]
    return {
        key.replace(".weight", ""): [
            [float(value) for value in row] for row in state[key].tolist()
        ]
        for key in ("left.weight", "right.weight", "merge.weight")
    }


def block_forward(matrices, vector):
    left, right, merge = matrices["left"], matrices["right"], matrices["merge"]
    hidden = [math.tanh(sum(a * b for a, b in zip(row, vector))) for row in left]
    hidden += [math.tanh(sum(a * b for a, b in zip(row, vector))) for row in right]
    return [sum(a * b for a, b in zip(row, hidden)) for row in merge]


def run_passes(matrices, encoded, depth):
    current = [0.0] * D
    input_rms = math.sqrt(math.fsum(v * v for v in encoded) / D)
    for _ in range(depth):
        state_rms = math.sqrt(math.fsum(v * v for v in current) / D)
        scale = LAMBDA * input_rms / math.sqrt(input_rms ** 2 + state_rms ** 2 + EPSILON ** 2)
        current = block_forward(matrices, [b + scale * c for b, c in zip(encoded, current)])
    return current


def readout_rows(nclass: int = 64) -> list:
    from cas_meta2.typed_teaching import binding

    return [
        list(struct.unpack("<64f", binding.row_bytes(["readout", f"W{c}"], seed=SEED, d_model=D)))
        for c in range(nclass)
    ]


def world_typed_slots() -> dict:
    """``record_id -> [slot_id]`` for slots whose alphabet is the 64 world aliases.

    The plan is a deterministic function of the public packet and is identical across all six runs —
    same course, same tokenizer, same seed — so it is built once here.
    """
    from cas_meta2.typed_teaching import course, slots as slots_module, worker_contract

    frozen, _tokenizer, _source = worker_contract.load_material(HOME)
    out = {}
    for index, record in enumerate(frozen["registry"], 1):
        packet = course.model_packet(frozen, record["record_id"])
        try:
            plan = slots_module.compile_slots(packet)
        except Exception:  # noqa: BLE001 - reported by omission
            continue
        ids = [
            slot["slot_id"] for slot in plan["slots"]
            if len(slot["symbols"]) == 64 and slot["symbols"][0] == "W0"
        ]
        if ids:
            out[record["record_id"]] = ids
        if index % 200 == 0:
            print(f"  plans built: {index}/{len(frozen['registry'])}", flush=True)
    return out


def summarise(picks: list) -> dict:
    counts = Counter(picks)
    total = len(picks)
    commonest, most = counts.most_common(1)[0]
    entropy = -math.fsum((c / total) * math.log2(c / total) for c in counts.values())
    return {
        "slots": total, "distinct": len(counts), "commonest": commonest,
        "share": most / total, "entropy": entropy,
    }


def main() -> int:
    aliases = {str(c): f"W{c}" for c in range(64)}
    print("building the world-typed slot map from the frozen public course...")
    slots = world_typed_slots()
    print(f"  packets with world-typed slots: {len(slots)}")
    print()

    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/result.json").is_file()
    )
    random_inputs = lcg(COUNT, seed=20260917)
    readout = readout_rows()

    print("=" * 112)
    print("1. THE RECORDED DISTRIBUTION — read from the workers' own predictions, no rebuild")
    print("=" * 112)
    print()
    print(f"{'receipt':>22} {'arm':>4} {'seed':>9} {'cursor':>7} {'distinct':>9} {'commonest':>10}"
          f" {'share':>8} {'entropy':>9}")
    print("-" * 112)
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        result = json.loads((receipt / "collected/results/result.json").read_text(encoding="utf-8"))
        arm = "ALT" if result["summary"]["condition"].startswith("ALT") else "MIX"
        seed = result["summary"]["model_seed"]
        for label, name in (("0", "initial_predictions.json"), ("160", "final_predictions.json")):
            payload = json.loads((artifacts / name).read_text(encoding="utf-8"))
            picks = []
            for prediction in payload["predictions"]:
                ids = slots.get(prediction["record_id"])
                if not ids:
                    continue
                selected = prediction["decisions"]["selected"]
                for slot_id in ids:
                    symbol = selected.get(slot_id)
                    if symbol in ALIAS:
                        picks.append(symbol)
            stats = summarise(picks)
            print(f"{receipt.name:>22} {arm:>4} {seed:9d} {label:>7} {stats['distinct']:9d}"
                  f" {stats['commonest']:>10} {100 * stats['share']:7.1f}%"
                  f" {stats['entropy']:9.3f}")
    print()

    print("=" * 112)
    print("2. THE TASK-FREE DISTRIBUTION — 210 random unit vectors, no encoder involved")
    print("=" * 112)
    print()
    print(f"{'receipt':>22} {'arm':>4} {'seed':>9} {'cursor':>7} {'depth':>6} {'distinct':>9}"
          f" {'commonest':>10} {'share':>8} {'entropy':>9}")
    print("-" * 112)
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        result = json.loads((receipt / "collected/results/result.json").read_text(encoding="utf-8"))
        arm = "ALT" if result["summary"]["condition"].startswith("ALT") else "MIX"
        seed = result["summary"]["model_seed"]
        for cursor, name in (("0", "initial.pt"), ("160", "final.pt")):
            matrices = load_matrices(artifacts / name)
            for depth in DEPTHS:
                picks = []
                for vector in random_inputs:
                    final = run_passes(matrices, vector, depth)
                    scores = [math.fsum(a * b for a, b in zip(row, final)) for row in readout]
                    picks.append(ALIAS[max(range(len(scores)), key=lambda c: scores[c])])
                stats = summarise(picks)
                print(f"{receipt.name:>22} {arm:>4} {seed:9d} {cursor:>7} {depth:6d}"
                      f" {stats['distinct']:9d} {stats['commonest']:>10}"
                      f" {100 * stats['share']:7.1f}% {stats['entropy']:9.3f}")
    print()
    print("  uniform over 64 aliases would be 64 distinct, 1.6% commonest, 6.000 bits")
    print()

    print("=" * 112)
    print("READING")
    print("=" * 112)
    print()
    print(
        "The recorded block above is exact and is the primary reading. It shows whether the\n"
        "concentration at cursor 160 holds in every run or only in the one first measured. The\n"
        "task-free block below shows whether the SAME change is produced by training in every run,\n"
        "with inputs that carry no task information at all."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
