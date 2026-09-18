"""Does the trained block destroy the input's information? Measure decodability through each stage.

Pure standard library. `torch` used **only to deserialise** the frozen checkpoints; all arithmetic
after that is on plain lists. Ridge classification is solved in the primal (64 dimensions) with
5-fold cross-validation, the same method and penalty the record's other probes use.

Why this is worth measuring
---------------------------
The record's central contrast is that the closed-form linear map reaches **63.83%** on the
focus-world alias while the trained learner reaches **1.24%**, and the information is demonstrably
present either way (63.65% decodable from the encoded slot with a free readout).

The trained block's weights **grew** — effective linear operator norm `0.361559 -> 7.135410`,
x19.73 (`COLLAPSE_CLAIM_WITHDRAWN.md`). With an operator norm of 7 and unit-norm inputs, `tanh`
**saturates**, and a saturated `tanh` is a sign function: it keeps which side of zero each
pre-activation falls on and **discards the magnitude**. That is a candidate mechanism for losing the
class information between the input and the output.

This script measures class information at every stage, so the claim can be checked rather than
argued:

    x                        the encoded slot itself
    tanh(x)                  the analytic initialisation's effective first stage
    tanh(left_0 @ x)         the UNTRAINED block's first layer
    tanh(left_160 @ x)       the TRAINED block's first layer
    ^6_0(x), ^6_160(x)       the full untrained and trained blocks
    tanh(s * x)              a scalar saturation sweep

The scalar sweep is the control that separates "this particular trained matrix" from "saturation in
general". It uses no trained parameter at all.

**All comparisons are relative.** `RECONSTRUCTION_GAP.md` measures the encoded-slot rebuild at +0.781
correlation with the recorded logits, so no absolute number here is the machine's. But every row is
the same rebuilt input through a different stage, so the comparison between stages is valid.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import pickle
import struct
import sys

HOME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

from cncm import analytic_decompose as ad  # noqa: E402

ARTIFACTS = HOME / "records/typed_matched_001/receipt_20260919_m/collected/results/artifacts"
SEED = 20260916
D = ad.D_MODEL
CACHE = Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
NCLASS = 64
FOLDS = 5
LAMBDA = ad.DEFAULT_RIDGE_LAMBDA
SCALES = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0)


def unit(vector):
    norm = math.sqrt(math.fsum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


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


def matvec(matrix, vector):
    return [math.fsum(a * b for a, b in zip(row, vector)) for row in matrix]


def block_forward(matrices, vector):
    left, right, merge = matrices["left"], matrices["right"], matrices["merge"]
    hidden = [math.tanh(v) for v in matvec(left, vector)]
    hidden += [math.tanh(v) for v in matvec(right, vector)]
    return matvec(merge, hidden)


def cv_accuracy(features: list, classes: list, *, folds: int = FOLDS) -> float:
    """5-fold cross-validated ridge classification, solved in the primal."""
    order = list(range(len(features)))
    buckets = [order[index::folds] for index in range(folds)]
    correct = total = 0
    for fold in range(folds):
        held = set(buckets[fold])
        train = [index for index in order if index not in held]
        weights = ad.ridge_weights(
            [features[index] for index in train],
            [classes[index] for index in train],
            nclass=NCLASS, lam=LAMBDA,
        )
        for index in buckets[fold]:
            scores = ad.free_readout_scores(weights, features[index])
            correct += 1 if max(range(NCLASS), key=lambda c: scores[c]) == classes[index] else 0
            total += 1
    return correct / total if total else 0.0


def encoded_slots() -> tuple:
    from cas_meta2.typed_teaching import binding, course, slots as slots_module, worker_contract

    rows = pickle.loads(CACHE.read_bytes())
    frozen, _tokenizer, _source = worker_contract.load_material(HOME)
    if len(rows) != len(frozen["registry"]):
        raise SystemExit("feature cache and registry are positionally aligned and must match")

    def row_vector(domain):
        return list(struct.unpack("<64f", binding.row_bytes(domain, seed=SEED, d_model=D)))

    vectors, classes = [], []
    for index, record in enumerate(frozen["registry"], 1):
        packet = course.model_packet(frozen, record["record_id"])
        try:
            plan = slots_module.compile_slots(packet)
            validated = slots_module.validate_plan(packet, plan)
            spec = binding._query_spec(validated, plan["slots"][0])
        except Exception:  # noqa: BLE001 - reported by omission
            continue
        query = row_vector(["query", spec])
        vectors.append(unit([(a + b) / math.sqrt(2.0)
                             for a, b in zip(rows[index - 1]["mean"], query)]))
        classes.append(int(rows[index - 1]["focus"]))
        if index % 200 == 0:
            print(f"  encoded slots: {index}/{len(frozen['registry'])}", flush=True)
    return vectors, classes


def main() -> int:
    print("loading checkpoints (deserialisation only)...")
    untrained = load_matrices("initial.pt")
    trained = load_matrices("final.pt")
    print("rebuilding the encoded slots from the frozen public material...")
    encoded, classes = encoded_slots()
    print(f"  slots: {len(encoded)}   classes present: {len(set(classes))}")
    print()

    def report(label: str, features: list) -> float:
        accuracy = cv_accuracy(features, classes)
        print(f"  {label:>44}  {100 * accuracy:8.2f}%   {accuracy * NCLASS:6.2f}x")
        return accuracy

    print("=" * 100)
    print("FOCUS-WORLD DECODABILITY THROUGH EACH STAGE  (chance = 1/64 = 1.5625%)")
    print("=" * 100)
    print()
    print(f"  {'features':>44}  {'5-fold CV':>9}  {'vs chance':>7}")
    print("-" * 100)
    report("x — the encoded slot itself", encoded)
    report("tanh(x) — the analytic first stage", [ad.tanh_vector(v) for v in encoded])
    report("tanh(left_untrained @ x)", [tuple(math.tanh(u) for u in matvec(untrained["left"], v))
                                        for v in encoded])
    report("tanh(left_trained @ x)", [tuple(math.tanh(u) for u in matvec(trained["left"], v))
                                      for v in encoded])
    report("^6_untrained(x) — full block", [block_forward(untrained, v) for v in encoded])
    report("^6_trained(x) — full block", [block_forward(trained, v) for v in encoded])
    print()

    print("=" * 100)
    print("SCALAR SATURATION SWEEP — tanh(s * x), no trained parameter involved")
    print("=" * 100)
    print()
    print(f"  {'scale s':>9}  {'5-fold CV':>9}  {'vs chance':>9}   mean |pre-activation|")
    print("-" * 100)
    for scale in SCALES:
        features = []
        magnitudes = []
        for vector in encoded:
            scaled = [scale * value for value in vector]
            magnitudes.append(math.fsum(abs(v) for v in scaled) / D)
            features.append(tuple(math.tanh(v) for v in scaled))
        accuracy = cv_accuracy(features, classes)
        print(f"  {scale:9.2f}  {100 * accuracy:8.2f}%   {accuracy * NCLASS:8.2f}x"
              f"   {math.fsum(magnitudes) / len(magnitudes):.4f}")
    print()

    print("=" * 100)
    print("READING")
    print("=" * 100)
    print()
    print(
        "Every row is the SAME rebuilt input through a different stage, so the comparison between\n"
        "rows is valid even though the rebuild is approximate (+0.781 correlation with the recorded\n"
        "logits).\n"
        "\n"
        "The scalar sweep involves no trained parameter. If decodability falls as `s` grows, then\n"
        "saturation itself discards the class information, and the trained block's measured 19.73x\n"
        "growth in effective operator norm is a candidate mechanism for the 1.24%. If decodability\n"
        "holds across the sweep, saturation does not explain it and the trained matrix's own\n"
        "geometry must."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
