"""Self-check on the 26-point claim: is the loss real information loss, or a regularisation artifact?

Pure standard library. `torch` used **only to deserialise** checkpoints.

Why this check is necessary before the claim stands
---------------------------------------------------
`STAGE_INFORMATION_RESULT.md` reported that the registered `^6` architecture reduces focus-world
decodability from **63.83%** to **37.3%** and called it a loss of linearly available information —
"discards 42% of what was there".

**That conclusion does not follow from the measurement, and this script tests it.** An invertible
linear map followed by a mildly nonlinear `tanh` preserves information. What it changes is the
**conditioning** of the feature space, and the probe used a **fixed ridge penalty of lambda = 1.0**
on every feature set. A penalty that is well suited to raw encoded slots can be badly suited to a
transformed space whose directions are unevenly scaled. In that case the measured drop is the
*probe's* limitation, not the block's.

Three checks separate the two readings:

1. **A penalty sweep.** `lambda` from 1e-6 to 1e4, on the same four feature sets. If `^6(x)`
   recovers to near 63% at some other penalty, the 26-point drop was regularisation.
2. **A rank and conditioning reading.** Singular values of the block's effective linear map
   `merge_left @ left + merge_right @ right`, trained and untrained. A rank-deficient map really does
   destroy information; a full-rank badly-scaled one does not.
3. **Whitening.** Standardise each feature set to unit variance per component before classifying. A
   badly-scaled but informative feature set recovers; an uninformative one does not.

All comparisons are relative: the same rebuilt inputs through different stages and under different
penalties, so `RECONSTRUCTION_GAP.md`'s +0.781 correlation does not invalidate them.
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
NCLASS = 64
FOLDS = 5
CACHE = Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
LAMBDAS = (1e-6, 1e-4, 1e-2, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0)


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


def effective_linear(matrices) -> list:
    """``merge_left @ left + merge_right @ right`` — the block's small-input linearisation."""
    left, right, merge = matrices["left"], matrices["right"], matrices["merge"]
    return [
        [math.fsum(merge[i][k] * left[k][j] + merge[i][D + k] * right[k][j] for k in range(D))
         for j in range(D)]
        for i in range(D)
    ]


def singular_values(matrix) -> list:
    """Singular values of a 64x64 matrix by Jacobi eigendecomposition of ``A^T A``."""
    gram = [[math.fsum(matrix[k][i] * matrix[k][j] for k in range(D)) for j in range(D)]
            for i in range(D)]
    a = [row[:] for row in gram]
    for _ in range(100):
        off = math.sqrt(math.fsum(a[i][j] ** 2 for i in range(D) for j in range(D) if i != j))
        if off < 1e-12:
            break
        for p in range(D - 1):
            for q in range(p + 1, D):
                if abs(a[p][q]) < 1e-18:
                    continue
                theta = 0.5 * math.atan2(2.0 * a[p][q], a[q][q] - a[p][p])
                c, s = math.cos(theta), math.sin(theta)
                for k in range(D):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(D):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
    return sorted((math.sqrt(max(0.0, a[i][i])) for i in range(D)), reverse=True)


def whiten(features: list) -> list:
    """Standardise every component to zero mean and unit variance."""
    count, width = len(features), len(features[0])
    means = [math.fsum(row[j] for row in features) / count for j in range(width)]
    deviations = []
    for j in range(width):
        variance = math.fsum((row[j] - means[j]) ** 2 for row in features) / count
        deviations.append(math.sqrt(variance) if variance > 0 else 1.0)
    return [[(row[j] - means[j]) / deviations[j] for j in range(width)] for row in features]


def cv_accuracy(features: list, classes: list, lam: float) -> float:
    order = list(range(len(features)))
    buckets = [order[index::FOLDS] for index in range(FOLDS)]
    correct = total = 0
    for fold in range(FOLDS):
        held = set(buckets[fold])
        train = [index for index in order if index not in held]
        weights = ad.ridge_weights(
            [features[index] for index in train], [classes[index] for index in train],
            nclass=NCLASS, lam=lam,
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
    print("rebuilding the encoded slots...")
    encoded, classes = encoded_slots()
    print(f"  slots: {len(encoded)}   classes present: {len(set(classes))}")
    print()

    sets = {
        "x (encoded slot)": encoded,
        "tanh(x)": [ad.tanh_vector(v) for v in encoded],
        "^6_untrained(x)": [block_forward(untrained, v) for v in encoded],
        "^6_trained(x)": [block_forward(trained, v) for v in encoded],
    }

    print("=" * 104)
    print("1. PENALTY SWEEP — does any lambda recover the block's decodability?")
    print("=" * 104)
    print()
    print(f"{'features':>20}" + "".join(f"{('l=' + f'{lam:g}'):>10}" for lam in LAMBDAS))
    print("-" * 104)
    best = {}
    for name, features in sets.items():
        row = []
        for lam in LAMBDAS:
            accuracy = cv_accuracy(features, classes, lam)
            row.append(accuracy)
        best[name] = max(row)
        print(f"{name:>20}" + "".join(f"{100 * value:9.2f}%" for value in row))
    print()
    print(f"{'best over the sweep':>20}" + "".join("          " for _ in LAMBDAS))
    for name, value in best.items():
        print(f"  {name:>20}: {100 * value:.2f}%")
    print()

    print("=" * 104)
    print("2. WHITENED FEATURES — a badly scaled but informative set recovers here")
    print("=" * 104)
    print()
    print(f"{'features':>20} {'raw best':>10} {'whitened @ l=1':>16}")
    print("-" * 104)
    for name, features in sets.items():
        whitened = whiten(features)
        print(f"{name:>20} {100 * best[name]:9.2f}% {100 * cv_accuracy(whitened, classes, 1.0):15.2f}%")
    print()

    print("=" * 104)
    print("3. RANK AND CONDITIONING OF THE EFFECTIVE LINEAR MAP")
    print("=" * 104)
    print()
    for label, matrices in (("untrained", untrained), ("trained", trained)):
        values = singular_values(effective_linear(matrices))
        total = math.fsum(values)
        cum = 0.0
        rank99 = 0
        for value in values:
            cum += value
            rank99 += 1
            if cum >= 0.99 * total:
                break
        print(f"  {label:>10}: largest {values[0]:.6f}  smallest {values[-1]:.6e}"
              f"  ratio {values[0] / values[-1] if values[-1] else float('inf'):.3e}")
        print(f"              Frobenius {math.sqrt(math.fsum(v * v for v in values)):.6f}"
              f"   rank holding 99% of the sum: {rank99} of {D}")
    print()

    print("=" * 104)
    print("READING")
    print("=" * 104)
    print()
    print(
        "If a different penalty or whitening recovers ^6(x) to near 63%, the 26-point drop was the\n"
        "probe's fixed regularisation and NOT information loss, and STAGE_INFORMATION_RESULT.md's\n"
        "headline must be corrected. If it does not recover, AND the effective map is full rank,\n"
        "the drop is a conditioning cost the block imposes on any linear read with a fixed penalty.\n"
        "If the map is rank deficient, information really is destroyed."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
