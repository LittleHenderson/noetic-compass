"""Does the ridge penalty change arm A's prediction? Sweep it on the recurrence-aware fit.

Pure standard library. No torch, no device, no network, no target opened.

Why this is the right follow-up
-------------------------------
`INFORMATION_LOSS_WITHDRAWN.md` found that a **fixed ridge penalty of lambda = 1.0 applied across
differently-scaled feature sets turns a conditioning difference into an apparent capability
difference**, and that the record's other probes use the same fixed value. The lesson was recorded;
this applies it to the number the whole arm-A proposal rests on.

`PREPARATION_RESULT.md` and `RECURRENCE_AWARE_FIT_RESULT.md` report, at lambda = 1.0:

    direct forward, tanh(x)              62.94%
    through the registered recurrence    62.06%

Round 20's sweep already shows the *direct* fit's penalty dependence on the same features:
`tanh(x)` reads **63.83% at lambda = 1.0** and **64.72% at lambda = 1e-4**. Under one point.

**What has not been measured is the recurrence-aware fit's dependence**, and that is the figure arm A
is predicted on. The refinement fits on the states the block is actually given, and those states may
be scaled differently from `tanh(x)` — which is exactly the condition that made the earlier probe
misread by 26 points.

What this measures
------------------
For each penalty: the naive fit and the recurrence-aware refinement, each scored **at depth 0 and
through the registered depth-8 recurrence**, out-of-fold, on the same folds.

Selection honesty: the best penalty is chosen by looking at these same out-of-fold numbers, so the
best row is mildly optimistic. The **shape of the curve** is the honest reading, and a flat curve
means the choice does not matter.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import pickle
import struct
import sys

HOME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

from cncm import analytic_decompose as ad  # noqa: E402

SEED = 20260916
D = ad.D_MODEL
LAMBDA_RECURRENCE = 0.5
EPSILON = 1e-6
DEPTH = 8
CACHE = Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
FOLDS = 5
PENALTIES = (1e-4, 1e-2, 1.0)


def unit(vector):
    norm = math.sqrt(math.fsum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def load_encoded() -> tuple:
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


def readout_rows(nclass: int = 64) -> list:
    from cas_meta2.typed_teaching import binding

    return [
        list(struct.unpack("<64f", binding.row_bytes(["readout", f"W{c}"], seed=SEED, d_model=D)))
        for c in range(nclass)
    ]


def recurrence_states(parameters, encoded, depth=DEPTH):
    current = [0.0] * D
    input_rms = math.sqrt(math.fsum(v * v for v in encoded) / D)
    incomings, final = [], None
    for _ in range(depth):
        state_rms = math.sqrt(math.fsum(v * v for v in current) / D)
        scale = LAMBDA_RECURRENCE * input_rms / math.sqrt(
            input_rms ** 2 + state_rms ** 2 + EPSILON ** 2
        )
        incoming = [b + scale * c for b, c in zip(encoded, current)]
        incomings.append(incoming)
        current = parameters.forward(incoming)
        final = current
    return incomings, final


def fit(inputs, targets, readout, penalty):
    weights = ad.ridge_weights(
        [ad.tanh_vector(v) for v in inputs], targets, nclass=len(readout), lam=penalty
    )
    return ad.decompose_from_free_readout(weights, readout)


def pick(parameters, encoded, readout, depth):
    vector = parameters.forward(encoded) if depth == 0 else recurrence_states(parameters, encoded)[1]
    scores = [math.fsum(a * b for a, b in zip(row, vector)) for row in readout]
    return max(range(len(scores)), key=lambda c: scores[c])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refinements", type=int, default=1,
                        help="recurrence-aware refinement rounds; 0 gives the naive fit")
    args = parser.parse_args(argv)

    print("rebuilding the encoded slots...")
    encoded, classes = load_encoded()
    readout = readout_rows()
    print(f"  slots: {len(encoded)}   classes present: {len(set(classes))}")
    print()

    order = list(range(len(encoded)))
    buckets = [order[index::FOLDS] for index in range(FOLDS)]

    print("=" * 100)
    print(f"PENALTY SWEEP — naive fit and {args.refinements} recurrence-aware refinement round(s)")
    print("=" * 100)
    print()
    print(f"{'penalty':>10} {'fit':>22} {'depth 0':>11} {'depth 8':>11}")
    print("-" * 100)
    results = []
    for penalty in PENALTIES:
        # naive fit, then the refinement chain, evaluated at each stage
        parameters_per_fold = []
        for fold in range(FOLDS):
            held = set(buckets[fold])
            train = [index for index in order if index not in held]
            parameters_per_fold.append({
                "parameters": fit([encoded[i] for i in train], [classes[i] for i in train],
                                  readout, penalty),
                "held": sorted(held),
                "train": train,
            })
        stages = [("naive", parameters_per_fold)]
        current = parameters_per_fold
        for round_index in range(args.refinements):
            refined = []
            for entry in current:
                inputs, targets = [], []
                for index in entry["train"]:
                    incomings, _final = recurrence_states(entry["parameters"], encoded[index])
                    for incoming in incomings:
                        inputs.append(incoming)
                        targets.append(classes[index])
                refined.append({
                    "parameters": fit(inputs, targets, readout, penalty),
                    "held": entry["held"],
                    "train": entry["train"],
                })
            stages.append((f"refined x{round_index + 1}", refined))
            current = refined
        for stage_name, stage_folds in stages:
            counts = {0: 0, DEPTH: 0}
            total = 0
            for entry in stage_folds:
                for index in entry["held"]:
                    for depth in (0, DEPTH):
                        counts[depth] += 1 if pick(entry["parameters"], encoded[index],
                                                   readout, depth) == classes[index] else 0
                    total += 1
            row = (penalty, stage_name, counts[0] / total, counts[DEPTH] / total)
            results.append(row)
            print(f"{penalty:10.4g} {stage_name:>22} {100 * row[2]:10.2f}% {100 * row[3]:10.2f}%")
        print()

    print("=" * 100)
    print("READING")
    print("=" * 100)
    print()
    best_direct = max(results, key=lambda r: r[2])
    best_recurrence = max(results, key=lambda r: r[3])
    print(f"  best depth 0 : {100 * best_direct[2]:.2f}%  at penalty {best_direct[0]:g}, "
          f"{best_direct[1]}")
    print(f"  best depth 8 : {100 * best_recurrence[3]:.2f}%  at penalty {best_recurrence[0]:g}, "
          f"{best_recurrence[1]}")
    print()
    print(
        "The record's published arm-A figures are 62.94% direct and 62.06% through the recurrence,\n"
        "both at penalty 1.0 with 2 refinement rounds. If the curve is flat, the penalty is not a\n"
        "material choice and those figures stand. If it moves materially, the arm's prediction must\n"
        "be restated at the better penalty -- and the selection is mildly optimistic because the\n"
        "best penalty is chosen on the same out-of-fold numbers that are reported."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
