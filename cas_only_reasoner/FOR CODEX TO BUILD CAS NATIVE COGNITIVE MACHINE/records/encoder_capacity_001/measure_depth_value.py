"""Does the registered depth actually change the answer? Measure the recurrence's marginal value.

Pure standard library. `torch` used **only to deserialise** the frozen checkpoints; every matrix
is pulled out as plain floats and all arithmetic after that is on lists.

Why this measurement is rebuild-robust
--------------------------------------
`records/encoder_capacity_001/RECONSTRUCTION_GAP.md` established that this rebuild reaches only
**+0.781 correlation** with the recorded logits, so no absolute number from it may be treated as
the machine's. **This measurement does not use absolute numbers.** It feeds the *same* input to
the *same* saved block at several depths and compares the depths with each other. A wrong input
would change all depths together; it cannot manufacture or hide a difference *between* depths.
So the comparison is valid even though the input is approximate, and every number below is
labelled as a relative measurement.

What it measures
----------------
`_forward` runs `recurrence.run_passes(encoded, core, depth=depth, state=None)` at prediction
depth 8, and the recurrence is

    current = zeros(64)
    repeat depth times:
        incoming = encoded + (0.5 * rms(encoded)/sqrt(rms(encoded)^2 + rms(current)^2 + 1e-12)) * current
        current  = ^6(incoming)

So every slot costs `depth` passes through a 16,384-parameter block. This script asks what passes
3 through 8 buy:

    logit vector cosine between depths     is the extra depth changing the scores at all?
    argmax agreement between depths        is the extra depth changing the answer?
    logit scale by depth                   where does it settle?

If depth 8 and depth 2 agree on the answer, then six of the eight passes are not buying an answer.
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
DEPTHS = (1, 2, 4, 8)
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
    """``merge @ concat(tanh(left x), tanh(right x))``, read from ``cas_cjt/neural.py``."""
    left, right, merge = block["left"], block["right"], block["merge"]
    hidden = [math.tanh(sum(a * b for a, b in zip(row, vector))) for row in left]
    hidden += [math.tanh(sum(a * b for a, b in zip(row, vector))) for row in right]
    return [sum(a * b for a, b in zip(row, hidden)) for row in merge]


def rms(values) -> float:
    return math.sqrt(sum(value * value for value in values) / len(values))


def run_passes(block, encoded, depth):
    """``recurrence.run_passes`` with ``state=None``, ``lambda_ = 0.5``, ``epsilon = 1e-6``."""
    current = [0.0] * D
    input_rms = rms(encoded)
    for _ in range(depth):
        state_rms = rms(current)
        scale = LAMBDA * input_rms / math.sqrt(input_rms ** 2 + state_rms ** 2 + EPSILON ** 2)
        incoming = [base + scale * carry for base, carry in zip(encoded, current)]
        current = block_forward(block, incoming)
    return current


def unit(vector):
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def cosine(left, right) -> float:
    a = math.sqrt(sum(x * x for x in left))
    b = math.sqrt(sum(x * x for x in right))
    return sum(x * y for x, y in zip(left, right)) / (a * b) if a * b else float("nan")


def build_probes() -> list:
    """Encoded slots for the world-typed reference slots of `context` and `definition` packets."""
    home = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(home / "research" / "CAS_META_2_COMPOSITION"))
    sys.path.insert(0, str(home))
    from cas_meta2.typed_teaching import binding, course, slots as slots_module, worker_contract

    frozen, tokenizer, _source = worker_contract.load_material(home)
    base = {
        index: binding.row_bytes(["token", token], seed=SEED, d_model=D)
        for index, token in enumerate(tokenizer.vocabulary)
    }

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
            for position, token_id in enumerate(row["token_ids"]):
                order, signs = binding.signed_permutation(
                    seed=SEED, scope=row["scope"], ordinal=row["ordinal"],
                    position=position, d_model=D)
                token_row = base[token_id]
                for dest, (origin, sign) in enumerate(zip(order, signs)):
                    vector[dest] += sign * token_row[origin]
            built.append(unit(vector))
        packet_vector = unit([sum(values) for values in zip(*built)])
        plan = slots_module.compile_slots(packet)
        validated = slots_module.validate_plan(packet, plan)
        for slot in plan["slots"]:
            if len(slot["symbols"]) != 64 or slot["symbols"][0] != "W0":
                continue
            spec = binding._query_spec(validated, slot)
            query = row_vector(["query", spec])
            probes.append({
                "symbols": tuple(slot["symbols"]),
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


def main() -> int:
    print("loading checkpoints (deserialisation only)...")
    blocks = {"cursor 0": load_block("initial.pt"), "cursor 160": load_block("final.pt")}
    home = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(home / "research" / "CAS_META_2_COMPOSITION"))
    sys.path.insert(0, str(home))
    from cas_meta2.typed_teaching import binding

    readout = [
        list(struct.unpack("<64f", binding.row_bytes(["readout", f"W{index}"], seed=SEED, d_model=D)))
        for index in range(64)
    ]

    print(f"building up to {PROBE_CAP} world-typed reference slots...")
    probes = build_probes()
    print(f"  probes: {len(probes)}")
    print(f"  NOTE: the encoded input is approximate (rebuild correlation +0.781). Every number")
    print(f"        below compares depths against each other on the SAME input, so it is valid.")
    print()

    for label, block in blocks.items():
        print("=" * 92)
        print(f"{label} — WHAT DOES DEPTH BUY?")
        print("=" * 92)
        print()
        logits = {depth: [] for depth in DEPTHS}
        picks = {depth: [] for depth in DEPTHS}
        for probe in probes:
            for depth in DEPTHS:
                vector = run_passes(block, probe["encoded"], depth)
                scores = [sum(a * b for a, b in zip(row, vector)) for row in readout]
                logits[depth].append(scores)
                picks[depth].append(
                    probe["symbols"][max(range(len(scores)), key=lambda i: scores[i])]
                )
        print(f"{'comparison':>22} {'mean logit cosine':>19} {'argmax agreement':>18}")
        print("-" * 92)
        for left_index, left in enumerate(DEPTHS):
            for right in DEPTHS[left_index + 1:]:
                agreements = sum(1 for a, b in zip(picks[left], picks[right]) if a == b)
                cosines = [cosine(a, b) for a, b in zip(logits[left], logits[right])]
                print(
                    f"{'depth ' + str(left) + ' vs ' + str(right):>22}"
                    f" {sum(cosines) / len(cosines):19.6f}"
                    f" {100 * agreements / len(picks[left]):17.2f}%"
                )
        print()
        print("logit scale by depth:")
        for depth in DEPTHS:
            mean = sum(sum(row) / len(row) for row in logits[depth]) / len(logits[depth])
            sd = sum(
                math.sqrt(sum((x - sum(r) / len(r)) ** 2 for x in r) / len(r))
                for r in logits[depth]
            ) / len(logits[depth])
            print(f"  depth {depth:>2}: mean {mean:+.6f}   sd {sd:.6f}")
        print()

    print("=" * 92)
    print("READING")
    print("=" * 92)
    print()
    print(
        "Each row asks what the extra passes cost and what they buy. The prediction path runs\n"
        "depth 8 for every slot, so `depth 4 vs 8` is the row that decides whether the last four\n"
        "passes earn their place: they cost twice the block forward passes.\n"
        "\n"
        "A caution on the untrained checkpoint: at cursor 0 the logit sd is around 0.043 across\n"
        "64 symbols, so the scores are near-ties and the argmax is largely decided by the\n"
        "first-wins tie-break rather than by the vector. High depth-to-depth agreement there is\n"
        "an artifact of near-ties, not evidence that the recurrence is unnecessary.\n"
        "\n"
        "This is a relative measurement on a shared input, so the rebuild's 0.781 correlation\n"
        "does not weaken it. It says nothing about whether the answer is CORRECT."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
