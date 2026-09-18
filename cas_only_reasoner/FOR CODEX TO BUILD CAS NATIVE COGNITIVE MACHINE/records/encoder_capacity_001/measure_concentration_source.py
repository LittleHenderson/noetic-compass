"""Where does the concentration come from: the frozen readout's geometry, the training, or neither?

Pure standard library. `torch` used **only to deserialise** the frozen checkpoints and to read the
frozen public course; all arithmetic after that is on plain lists.

Why this probe is exact
-----------------------
It feeds **invented inputs** through the block, the recurrence and the frozen readout, all of which
are exact for the saved weights and the frozen rows. The encoder is never touched, so
`RECONSTRUCTION_GAP.md`'s +0.781 correlation does not limit anything here.

The four parameterisations
--------------------------
`INPUT_INDEPENDENCE_RESULT.md` showed the recorded concentration has three separable causes and that
**training is the largest**: on 210 task-free inputs the trained block narrows the readout from 58
distinct aliases to 44 at depth 1 and from 57 to 27 at depth 8, while the untrained block leaves it
spread. That leaves one question open, and it decides how to read arm A:

    is the concentration a property of the FROZEN READOUT's geometry, or of the WEIGHTS?

Four parameterisations on the SAME 210 task-free inputs separate them:

1. **identity** — no block at all, `f(x) = x`. Whatever concentrates here comes from the readout's
   own geometry, since no parameter is involved.
2. **untrained** — `initial.pt`, cursor 0.
3. **trained** — `final.pt`, cursor 160.
4. **analytic** — the closed-form `T` of arm A, fitted recurrence-aware out-of-fold.

If the **identity** row is already concentrated, the readout's geometry alone explains it and no
weight change can be blamed. If identity is spread and the analytic row stays spread while the
trained row concentrates, then the concentration is a defect of the trained block specifically, and
arm A's G6 prediction is supported by an encoder-free measurement rather than only by the
approximate rebuild.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import pickle
import struct
import sys
from collections import Counter

HOME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

from cncm import analytic_decompose as ad  # noqa: E402

ARTIFACTS = (
    HOME / "records/typed_matched_001/receipt_20260919_m/collected/results/artifacts"
)
SEED = 20260916
D = ad.D_MODEL
LAMBDA = 0.5
EPSILON = 1e-6
DEPTHS = (1, 8)
COUNT = 210
CACHE = Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
RECORDED_FINAL = {"distinct": 9, "commonest": "W36", "share": 0.443}


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


def load_matrices(name: str) -> dict:
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


def forward(matrices, vector):
    """``merge @ concat(tanh(left x), tanh(right x))`` — or the identity when ``matrices`` is None."""
    if matrices is None:
        return list(vector)
    left, right, merge = matrices["left"], matrices["right"], matrices["merge"]
    hidden = [math.tanh(sum(a * b for a, b in zip(row, vector))) for row in left]
    hidden += [math.tanh(sum(a * b for a, b in zip(row, vector))) for row in right]
    return [sum(a * b for a, b in zip(row, hidden)) for row in merge]


def run_passes(matrices, encoded, depth):
    current = [0.0] * D
    input_rms = math.sqrt(math.fsum(v * v for v in encoded) / len(encoded))
    for _ in range(depth):
        state_rms = math.sqrt(math.fsum(v * v for v in current) / len(current))
        scale = LAMBDA * input_rms / math.sqrt(input_rms ** 2 + state_rms ** 2 + EPSILON ** 2)
        incoming = [base + scale * carry for base, carry in zip(encoded, current)]
        current = forward(matrices, incoming)
    return current


def readout_rows(nclass: int = 64) -> list:
    from cas_meta2.typed_teaching import binding

    return [
        list(struct.unpack("<64f", binding.row_bytes(["readout", f"W{c}"], seed=SEED, d_model=D)))
        for c in range(nclass)
    ]


def analytic_matrices() -> dict:
    """One closed-form ``T``, fitted recurrence-aware on out-of-fold rows exactly as arm A does."""
    from cas_meta2.typed_teaching import binding, course, slots as slots_module, worker_contract

    rows = pickle.loads(CACHE.read_bytes())
    frozen, _tokenizer, _source = worker_contract.load_material(HOME)
    if len(rows) != len(frozen["registry"]):
        raise SystemExit("feature cache and registry are positionally aligned and must match")

    def row_vector(domain):
        return list(struct.unpack("<64f", binding.row_bytes(domain, seed=SEED, d_model=D)))

    encoded, classes = [], []
    for index, record in enumerate(frozen["registry"], 1):
        packet = course.model_packet(frozen, record["record_id"])
        try:
            plan = slots_module.compile_slots(packet)
            validated = slots_module.validate_plan(packet, plan)
            spec = binding._query_spec(validated, plan["slots"][0])
        except Exception:  # noqa: BLE001 - reported by omission
            continue
        query = row_vector(["query", spec])
        encoded.append(unit([(a + b) / math.sqrt(2.0) for a, b in zip(rows[index - 1]["mean"], query)]))
        classes.append(int(rows[index - 1]["focus"]))
        if index % 200 == 0:
            print(f"  encoded slots: {index}/{len(frozen['registry'])}", flush=True)

    readout = readout_rows()
    order = list(range(len(encoded)))
    held = set(order[::5])
    train = [index for index in order if index not in held]
    weights = ad.ridge_weights(
        [ad.tanh_vector(encoded[index]) for index in train],
        [classes[index] for index in train], nclass=len(readout),
    )
    parameters = ad.decompose_from_free_readout(weights, readout)
    for _ in range(2):  # the recurrence-aware refinement
        inputs, targets = [], []
        for index in train:
            current = [0.0] * D
            input_rms = math.sqrt(math.fsum(v * v for v in encoded[index]) / D)
            for _pass in range(8):
                state_rms = math.sqrt(math.fsum(v * v for v in current) / D)
                scale = LAMBDA * input_rms / math.sqrt(input_rms ** 2 + state_rms ** 2 + EPSILON ** 2)
                incoming = [b + scale * c for b, c in zip(encoded[index], current)]
                inputs.append(incoming)
                targets.append(classes[index])
                current = parameters.forward(incoming)
        weights = ad.ridge_weights(
            [ad.tanh_vector(v) for v in inputs], targets, nclass=len(readout)
        )
        parameters = ad.decompose_from_free_readout(weights, readout)
    return {
        "left": parameters.left,
        "right": parameters.right,
        "merge": parameters.merge,
    }


def main() -> int:
    print("building the four parameterisations...")
    identity = None
    untrained = load_matrices("initial.pt")
    trained = load_matrices("final.pt")
    analytic = analytic_matrices()
    print("  identity, untrained, trained, analytic — ready")
    print()

    readout = readout_rows()
    labels = tuple(f"W{c}" for c in range(64))
    inputs = lcg(COUNT, seed=20260917)
    print(f"task-free inputs: {COUNT} pseudo-random unit vectors")
    print()

    print("=" * 104)
    print("ALIAS DISTRIBUTION BY PARAMETERISATION, ON IDENTICAL TASK-FREE INPUTS")
    print("=" * 104)
    print()
    print(f"{'parameterisation':>18} {'depth':>6} {'distinct':>9} {'commonest':>10} {'share':>8}"
          f" {'entropy':>9}")
    print("-" * 104)
    for name, matrices in (
        ("identity (no block)", identity),
        ("untrained cursor 0", untrained),
        ("trained cursor 160", trained),
        ("analytic (arm A)", analytic),
    ):
        for depth in DEPTHS:
            picks = []
            for vector in inputs:
                final = run_passes(matrices, vector, depth)
                scores = [math.fsum(a * b for a, b in zip(row, final)) for row in readout]
                picks.append(labels[max(range(len(scores)), key=lambda c: scores[c])])
            counts = Counter(picks)
            commonest, most = counts.most_common(1)[0]
            entropy = -math.fsum(
                (c / len(picks)) * math.log2(c / len(picks)) for c in counts.values()
            )
            print(f"{name:>18} {depth:6d} {len(counts):9d} {commonest:>10}"
                  f" {100 * most / len(picks):7.1f}% {entropy:9.3f}")
    print()
    print(f"  uniform over 64 aliases                : 64 distinct, 1.6% commonest, 6.000 bits")
    print(f"  RECORDED, real slots, cursor 160       : {RECORDED_FINAL['distinct']} distinct, "
          f"{RECORDED_FINAL['commonest']} at {100 * RECORDED_FINAL['share']:.1f}%, 2.516 bits")
    print()
    print("=" * 104)
    print("READING")
    print("=" * 104)
    print()
    print(
        "The identity row involves no parameter at all: `f(x) = x`, so anything concentrating there\n"
        "comes from the frozen readout's own geometry and no weight change can be blamed for it.\n"
        "Rows below it add, in turn, the untrained block, the training, and the closed-form fit.\n"
        "\n"
        "If the analytic row stays spread while the trained row concentrates, the concentration is a\n"
        "defect of the trained block specifically, and arm A's G6 prediction is supported by an\n"
        "encoder-free measurement rather than only by the approximate rebuild."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
