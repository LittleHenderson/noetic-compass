"""Is the trained `^6` block input-sensitive at all? Read the weights and measure.

Pure standard library for all arithmetic. `torch` is used **only to deserialise** the frozen
checkpoints — no tensor arithmetic, no device, no autograd, no model execution. Every matrix
below is pulled out as plain Python floats and everything after that is arithmetic on lists.

Why this measurement
--------------------
`READOUT_COLLAPSE_RESULT.md` measured, from the recorded decisions, that at cursor 160 the model
emits only **9 of the 64 world aliases** across the 210 world-typed reference slots, that one
alias accounts for **44.3%** of them, and that the two world-typed slots of a `definition`
question agree with each other at exactly that 44.3% rate. The reading offered there was that the
block has collapsed onto an input-independent fixed point.

That reading was a description of the *readout's argmax*, not of the block. This script tests it
at the block itself. The registered module is

    ^6(x) = merge @ concat( tanh(left @ x), tanh(right @ x) )

with `left` (64,64), `right` (64,64), `merge` (64,128). Three readings, all on the saved
matrices:

1. **Weight scale.** Frobenius norms of `left`, `right`, and the two halves of `merge`, at
   cursor 0 and cursor 160. If the trained weights shrink toward zero, the module approaches the
   zero map, and after normalisation everything looks the same.
2. **Effective linear map.** At small weights `tanh` is transparent, so the module is
   approximately `x |-> (merge_left @ left + merge_right @ right) x`. Its operator norm measures
   how much the block can still distinguish inputs.
3. **Input sensitivity.** Feed the same probe inputs to both checkpoints and compare the spread
   of outputs. A collapse shows up as a much smaller spread at cursor 160.

The probe inputs are the real encoded slot vectors, rebuilt from the frozen public material.
They are **not** the learner's recurrence state — the learner runs the block inside
`recurrence.run_passes` and the block sees the recurrence state, not the encoded slot. So this
measures the block's sensitivity to its input, not its exact forward pass, and it is reported
that way.
"""

from __future__ import annotations

import io
import json
import math
from pathlib import Path
import struct
import sys

ARTIFACTS = (
    Path(__file__).resolve().parents[2]
    / "records/typed_matched_001/receipt_20260919_m/collected/results/artifacts"
)
SEED = 20260916
D = 64


def load_block(name: str) -> dict:
    """Pull the three matrices out of one checkpoint as plain nested lists."""
    import torch

    payload = torch.load(
        io.BytesIO((ARTIFACTS / name).read_bytes()), map_location="cpu", weights_only=True
    )
    state = payload["model_state"]
    return {
        key.replace(".weight", ""): [
            [float(value) for value in row] for row in state[key].tolist()
        ]
        for key in ("left.weight", "right.weight", "merge.weight")
    }


def frobenius(matrix) -> float:
    return math.sqrt(math.fsum(value * value for row in matrix for value in row))


def effective_linear(block) -> list:
    """``merge_left @ left + merge_right @ right`` — the small-weight linear approximation."""
    left, right, merge = block["left"], block["right"], block["merge"]
    out = [[0.0] * D for _ in range(D)]
    for i in range(D):
        for j in range(D):
            total = 0.0
            for k in range(D):
                total += merge[i][k] * left[k][j] + merge[i][D + k] * right[k][j]
            out[i][j] = total
    return out


def operator_norm(matrix, iterations: int = 60) -> float:
    """Largest singular value by power iteration from a deterministic start vector."""
    vector = [1.0 + (index % 7) * 0.125 for index in range(D)]
    norm = math.sqrt(math.fsum(value * value for value in vector))
    vector = [value / norm for value in vector]
    sigma = 0.0
    for _ in range(iterations):
        image = [math.fsum(a * b for a, b in zip(row, vector)) for row in matrix]
        sigma = math.sqrt(math.fsum(value * value for value in image))
        if sigma == 0.0:
            return 0.0
        vector = [value / sigma for value in image]
    return sigma


def forward(block, vector):
    left, right, merge = block["left"], block["right"], block["merge"]
    hidden = [math.tanh(math.fsum(a * b for a, b in zip(row, vector))) for row in left]
    hidden += [math.tanh(math.fsum(a * b for a, b in zip(row, vector))) for row in right]
    return [math.fsum(a * b for a, b in zip(row, hidden)) for row in merge]


def unit(vector):
    norm = math.sqrt(math.fsum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def spread(vectors, *, pair_sample: int = 200) -> dict:
    """Mean pairwise cosine over a deterministic subsample, and RMS distance from the mean.

    The pairwise term is O(n^2), so it is computed on a deterministic subsample and reported
    with the subsample size. The RMS-from-mean and mean-norm terms use every vector.
    """
    count = len(vectors)
    if count < 2:
        return {"pairs": 0, "mean_cosine": 0.0, "rms_from_mean": 0.0, "mean_norm": 0.0}
    step = max(1, count // pair_sample)
    sample = [vectors[index] for index in range(0, count, step)]
    unitized = [unit(vector) for vector in sample]
    cosine_total, pairs = 0.0, 0
    for i in range(len(unitized)):
        for j in range(i + 1, len(unitized)):
            cosine_total += math.fsum(a * b for a, b in zip(unitized[i], unitized[j]))
            pairs += 1
    mean_vector = [
        math.fsum(vector[k] for vector in vectors) / count for k in range(D)
    ]
    rms = math.sqrt(
        math.fsum(
            (vector[k] - mean_vector[k]) ** 2 for vector in vectors for k in range(D)
        )
        / (count * D)
    )
    mean_norm = math.fsum(
        math.sqrt(math.fsum(value * value for value in vector)) for vector in vectors
    ) / count
    return {
        "pairs": pairs,
        "mean_cosine": cosine_total / pairs,
        "rms_from_mean": rms,
        "mean_norm": mean_norm,
        "sampled": len(sample),
    }


def encoded_slots(limit: int | None = None) -> list:
    """The real encoded slot vectors, rebuilt from the frozen public material.

    ``encode_slot`` is ``normalize((packet_vector + query_row) / sqrt(2))``. The packet vector is
    serialised here as ``normalize(sum of unit row vectors)``, which differs from the frozen
    scale by a positive constant that the final ``normalize`` removes.
    """
    home = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(home / "research" / "CAS_META_2_COMPOSITION"))
    sys.path.insert(0, str(home))
    from cas_meta2.typed_teaching import binding, course, slots as slots_module, worker_contract

    frozen, tokenizer, _source = worker_contract.load_material(home)
    base = {index: binding.row_bytes(["token", token], seed=SEED, d_model=D)
            for index, token in enumerate(tokenizer.vocabulary)}

    def row_vector(domain):
        return list(struct.unpack("<64f", binding.row_bytes(domain, seed=SEED, d_model=D)))

    out = []
    for index, record in enumerate(frozen["registry"], 1):
        packet = course.model_packet(frozen, record["record_id"])
        rows = binding.compile_packet(packet, tokenizer, seed=SEED, d_model=D)["rows"]
        built = []
        for row in rows:
            vector = [0.0] * D
            for position, token in enumerate(row["token_ids"]):
                order, signs = binding.signed_permutation(
                    seed=SEED, scope=row["scope"], ordinal=row["ordinal"],
                    position=position, d_model=D)
                token_row = base[token]
                for dest, (origin, sign) in enumerate(zip(order, signs)):
                    vector[dest] += sign * token_row[origin]
            built.append(unit(vector))
        packet_vector = unit([math.fsum(values) for values in zip(*built)])
        plan = slots_module.compile_slots(packet)
        validated = slots_module.validate_plan(packet, plan)
        for slot in plan["slots"]:
            spec = binding._query_spec(validated, slot)
            query = row_vector(["query", spec])
            out.append(unit([(a + b) / math.sqrt(2.0)
                             for a, b in zip(packet_vector, query)]))
        if index % 200 == 0:
            print(f"  encoded slots built: {index}/{len(frozen['registry'])}", flush=True)
        if limit is not None and len(out) >= limit:
            break
    return out


def main() -> int:
    print("loading the two checkpoints (deserialisation only)...")
    initial = load_block("initial.pt")
    trained = load_block("final.pt")
    print()

    print("=" * 92)
    print("1. WEIGHT SCALE")
    print("=" * 92)
    print()
    print(f"{'matrix':>22} {'cursor 0':>14} {'cursor 160':>14} {'ratio':>10}")
    print("-" * 92)
    rows = [
        ("left.weight", frobenius(initial["left"]), frobenius(trained["left"])),
        ("right.weight", frobenius(initial["right"]), frobenius(trained["right"])),
        ("merge left half", frobenius([row[:D] for row in initial["merge"]]),
         frobenius([row[:D] for row in trained["merge"]])),
        ("merge right half", frobenius([row[D:] for row in initial["merge"]]),
         frobenius([row[D:] for row in trained["merge"]])),
    ]
    for name, before, after in rows:
        ratio = after / before if before else float("inf")
        print(f"{name:>22} {before:14.6f} {after:14.6f} {ratio:10.6f}")
    print()

    print("=" * 92)
    print("2. EFFECTIVE LINEAR MAP  x -> (merge_left @ left + merge_right @ right) x")
    print("=" * 92)
    print()
    for label, block in (("cursor 0", initial), ("cursor 160", trained)):
        effective = effective_linear(block)
        print(f"{label:>12}: Frobenius = {frobenius(effective):12.6f}"
              f"   operator norm = {operator_norm(effective):12.6f}")
    print()

    print("building real encoded slot vectors from the frozen public material...")
    probes = encoded_slots()
    print(f"  probe inputs: {len(probes)}")
    print()

    print("=" * 92)
    print("3. INPUT SENSITIVITY — the same probe inputs through both checkpoints")
    print("=" * 92)
    print()
    print(f"{'checkpoint':>12} {'probes':>7} {'sampled':>8} {'mean cosine':>13} {'rms from mean':>15} {'mean norm':>11}")
    print("-" * 92)
    for label, block in (("cursor 0", initial), ("cursor 160", trained)):
        outputs = [forward(block, probe) for probe in probes]
        stats = spread(outputs)
        print(f"{label:>12} {len(outputs):7d} {stats['sampled']:8d} {stats['mean_cosine']:13.6f}"
              f" {stats['rms_from_mean']:15.6f} {stats['mean_norm']:11.6f}")
    print()

    print("=" * 92)
    print("READING")
    print("=" * 92)
    print()
    print(
        "A block that still reads its input produces outputs that differ across inputs: a mean\n"
        "pairwise cosine well below 1 and an rms-from-mean that is a sizeable fraction of the\n"
        "mean norm. A block that has collapsed produces near-identical outputs whatever it is\n"
        "given: cosine approaching 1 and rms-from-mean near zero. Compare the two checkpoints\n"
        "and the recorded behaviour follows or it does not."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
