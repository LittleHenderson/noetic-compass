"""Reproduce the learner's forward pass in pure Python and find where the constant comes from.

> # NOT VALIDATED — this rebuild reaches only +0.781 correlation with the recorded logits.
> See `RECONSTRUCTION_GAP.md`. The encoder material is byte-identical to the recorded run
> (identity digest `a00930c5…` matches exactly), the recurrence is neither chaotic nor
> amplifying, and yet the rebuilt logit vector correlates at `+0.781143` with the recorded
> `scores` and its top-1 differs. **The remaining difference is unfound.** The reference encoder
> cannot be used to settle it here: `build_frozen_typed_encoder` raises `TYPED_ENCODER_CUDA_ONLY`
> on CPU and the installed torch is `2.11.0+cpu` with no CUDA device.
>
> Every number this script prints is therefore approximate and must be labelled as such. It must
> not be treated as the machine.

Pure standard library. `torch` is used **only to deserialise** the frozen checkpoints; every
matrix is pulled out as plain floats and all arithmetic after that is on lists.

The forward pass, from the source
---------------------------------
``_forward`` in `cas_meta2/typed_teaching/learner.py` does, per slot:

    encoded = encoder.encode_slot(packet, plan, slot)        # unit 64-vector
    final   = recurrence.run_passes(encoded, core, depth=depth, state=None, ...)
    logits  = encoder.readout_rows[slot symbols] @ final
    pick    = argmax(logits)

and `recurrence.run_passes` with ``state=None`` and ``lambda_ = 0.5``, ``epsilon = 1e-6`` is

    current = zeros(64)
    repeat depth times:
        incoming = encoded + (0.5 * rms(encoded) / sqrt(rms(encoded)^2 + rms(current)^2 + 1e-12)) * current
        current  = ^6(incoming)
    return current

with ``^6(x) = merge @ concat(tanh(left @ x), tanh(right @ x))``.

So the block never sees the encoded slot directly. It sees the encoded slot **plus a scaled
carry of its own previous output**, eight times over.

What this measures
------------------
1. **Reproduction.** Run the pass for the world-typed reference slots and compare the emitted
   alias distribution with the recorded one. The recorded distribution at cursor 160 is 9
   distinct aliases with ``W36`` at 44.3% of 210 slots. If this reproduces it, the
   reconstruction is right and everything below is a statement about the real machine.
2. **Where the constancy enters.** Compare three readings on the same slots: the spread of the
   encoded slots, the spread of the first-pass outputs, and the spread of the eight-pass
   outputs. If the spread contracts across the passes, the recurrence is what removes the
   input dependence, not the block.
3. **How much of the answer survives the recurrence.** Rank of the slot's first symbol after
   one pass versus after eight.

The probe set is capped so the pure-Python cost stays bounded, and the cap is reported.
"""

from __future__ import annotations

import io
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
LAMBDA = 0.5
EPSILON = 1e-6
DEPTH = 8
PROBE_CAP = 120


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


def rms(values) -> float:
    return math.sqrt(sum(value * value for value in values) / len(values))


def run_passes(block, encoded, depth=DEPTH):
    width = len(encoded)
    current = [0.0] * width
    input_rms = rms(encoded)
    states = []
    for _ in range(depth):
        state_rms = rms(current)
        denominator = math.sqrt(input_rms ** 2 + state_rms ** 2 + EPSILON ** 2)
        scale = LAMBDA * input_rms / denominator
        incoming = [base + scale * carry for base, carry in zip(encoded, current)]
        current = block_forward(block, incoming)
        states.append(current)
    return states


def unit(vector):
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def spread(vectors) -> dict:
    count = len(vectors)
    if count < 2:
        return {"mean_cosine": 0.0, "rms_from_mean": 0.0, "mean_norm": 0.0}
    unitized = [unit(vector) for vector in vectors]
    total, pairs = 0.0, 0
    for i in range(count):
        for j in range(i + 1, count):
            total += sum(a * b for a, b in zip(unitized[i], unitized[j]))
            pairs += 1
    mean_vector = [sum(v[k] for v in vectors) / count for k in range(D)]
    rms_from_mean = math.sqrt(
        sum((v[k] - mean_vector[k]) ** 2 for v in vectors for k in range(D)) / (count * D)
    )
    mean_norm = sum(math.sqrt(sum(x * x for x in v)) for v in vectors) / count
    return {"mean_cosine": total / pairs, "rms_from_mean": rms_from_mean, "mean_norm": mean_norm}


def build_probes() -> list:
    """Encoded slots for the world-typed reference slots of context and definition packets."""
    home = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(home / "research" / "CAS_META_2_COMPOSITION"))
    sys.path.insert(0, str(home))
    from cas_meta2.typed_teaching import binding, course, input_frames, slots as slots_module, worker_contract

    frozen, tokenizer, _source = worker_contract.load_material(home)
    base = {index: binding.row_bytes(["token", token], seed=SEED, d_model=D)
            for index, token in enumerate(tokenizer.vocabulary)}

    def row_vector(domain):
        return list(struct.unpack("<64f", binding.row_bytes(domain, seed=SEED, d_model=D)))

    probes = []
    for index, record in enumerate(frozen["registry"], 1):
        packet = course.model_packet(frozen, record["record_id"])
        if packet["record"]["query"]["kind"] not in ("context", "definition"):
            continue
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
        packet_vector = unit([sum(values) for values in zip(*built)])
        plan = slots_module.compile_slots(packet)
        validated = slots_module.validate_plan(packet, plan)
        for slot in plan["slots"]:
            symbols = slot["symbols"]
            if len(symbols) != 64 or symbols[0] != "W0":
                continue
            spec = binding._query_spec(validated, slot)
            query = row_vector(["query", spec])
            probes.append({
                "record_id": record["record_id"],
                "symbols": tuple(symbols),
                "encoded": unit([(a + b) / math.sqrt(2.0)
                                 for a, b in zip(packet_vector, query)]),
            })
            if len(probes) >= PROBE_CAP:
                break
        if len(probes) >= PROBE_CAP:
            break
        if index % 60 == 0:
            print(f"  probed {index} packets, {len(probes)} slots", flush=True)
    return probes


def argmax_alias(readout, vector, symbols):
    best, best_score = None, None
    for symbol, row in zip(symbols, readout):
        score = sum(a * b for a, b in zip(row, vector))
        if best_score is None or score > best_score:
            best, best_score = symbol, score
    return best


def main() -> int:
    print("loading checkpoints (deserialisation only)...")
    initial = load_block("initial.pt")
    trained = load_block("final.pt")
    home = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(home / "research" / "CAS_META_2_COMPOSITION"))
    sys.path.insert(0, str(home))
    from cas_meta2.typed_teaching import binding

    readout = [
        list(struct.unpack("<64f", binding.row_bytes(["readout", f"W{c}"], seed=SEED, d_model=D)))
        for c in range(64)
    ]
    symbols = tuple(f"W{c}" for c in range(64))

    print(f"building up to {PROBE_CAP} world-typed reference slots...")
    probes = build_probes()
    print(f"  probes: {len(probes)}")
    print()

    for label, block in (("cursor 0", initial), ("cursor 160", trained)):
        print("=" * 92)
        print(f"{label} — REPRODUCTION AND WHERE THE CONSTANCY ENTERS")
        print("=" * 92)
        print()
        encoded = [probe["encoded"] for probe in probes]
        first_pass, eighth_pass, picks = [], [], []
        for probe in probes:
            states = run_passes(block, probe["encoded"])
            first_pass.append(states[0])
            eighth_pass.append(states[-1])
            picks.append(argmax_alias(readout, states[-1], symbols))
        for name, group in (
            ("encoded slots (the block's nominal input)", encoded),
            ("after 1 pass", first_pass),
            ("after 8 passes", eighth_pass),
        ):
            stats = spread(group)
            print(f"  {name:>42}: mean cosine {stats['mean_cosine']:8.4f}"
                  f"   rms from mean {stats['rms_from_mean']:9.5f}"
                  f"   mean norm {stats['mean_norm']:9.5f}")
        counts: dict = {}
        for pick in picks:
            counts[pick] = counts.get(pick, 0) + 1
        ordered = sorted(counts.items(), key=lambda kv: -kv[1])
        print()
        print(f"  emitted aliases after 8 passes: {len(counts)} distinct of 64")
        print("  most emitted: " + ", ".join(
            f"{name}={count}({100 * count / len(picks):.1f}%)" for name, count in ordered[:6]
        ))
        print()

    print("=" * 92)
    print("READING")
    print("=" * 92)
    print()
    print(
        "The recorded distribution at cursor 160 was 9 distinct aliases over the 210\n"
        "world-typed reference slots with W36 at 44.3%. If the reproduction here shows the\n"
        "same shape, the three spreads above say where the input dependence is lost: at the\n"
        "encoded slot, at the block, or at the recurrence that carries the block's own output\n"
        "back into its input eight times."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
