"""The recurrence costs the analytic solution 19.15 points. Measure why, and whether fitting for
the functional the run actually computes recovers them.

Pure standard library. No torch, no device, no network, no target opened.

The finding this starts from
----------------------------
`records/analytic_decompose_phase0_001/PREPARATION_RESULT.md`, measured out-of-fold:

    direct forward      ^6(x) = T @ tanh(x)               63.83%
    through the recurrence, depth 8                        44.68%

The registered recurrence is, per slot:

    current = zeros(64)
    repeat depth times:
        incoming = encoded + (0.5 * rms(encoded)/sqrt(rms(encoded)^2 + rms(current)^2 + 1e-12)) * current
        current  = ^6(incoming)

The closed-form solve fits ``T`` so that ``T @ tanh(encoded)`` reads the focus world well. But the
run never evaluates the block on the encoded slot: it evaluates it on ``incoming``, which is the
encoded slot plus a scaled carry of the block's own previous output, eight times over.

**So the solve optimises a functional the run does not compute.** That is a candidate explanation
and it is testable without a GPU.

What this measures
------------------
1. **The depth profile.** Focus-alias accuracy of the fitted parameters at depth 0 (direct), 1, 2,
   4 and 8. If the loss is monotone in depth, the recursion is degrading the initialisation
   pass by pass rather than converging to something else.
2. **Whether fitting for the recurrence recovers it.** A fixed-point refinement:

       T_0   fit on tanh(encoded)                          (the current method)
       run   the recurrence with T_0, collect the states the block was given
       T_1   fit on tanh(those states)
       T_2   repeat once more

   Each round is scored **through the recurrence**, out-of-fold, on the same held-out rows. If
   T_1 or T_2 beats T_0's 44.68%, the solve was aimed at the wrong functional and aiming it
   correctly is a $0 architecture improvement. If it does not, the recurrence's cost is not an
   aiming error and the reading must say so.

Fold discipline is preserved throughout: every parameter set is fitted on four folds and scored
on the fifth.
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
LAMBDA = 0.5
EPSILON = 1e-6
DEPTHS = (0, 1, 2, 4, 8)
CACHE = Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
DEFAULT_FOLDS = 5
REFINEMENTS = 2


def unit(vector):
    norm = math.sqrt(math.fsum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def load_encoded() -> tuple:
    from cas_meta2.typed_teaching import binding, course, slots as slots_module, worker_contract

    rows = pickle.loads(CACHE.read_bytes())
    frozen, _tokenizer, _source = worker_contract.load_material(HOME)
    if len(rows) != len(frozen["registry"]):
        raise SystemExit(
            f"cache holds {len(rows)} rows, registry holds {len(frozen['registry'])}; "
            f"they are positionally aligned and must match"
        )

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
        encoded = [(a + b) / math.sqrt(2.0) for a, b in zip(rows[index - 1]["mean"], query)]
        vectors.append(unit(encoded))
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


def recurrence_states(parameters, encoded, depth: int):
    """``recurrence.run_passes`` with ``state=None``. Returns every ``incoming`` the block sees."""
    current = [0.0] * D
    input_rms = math.sqrt(math.fsum(v * v for v in encoded) / len(encoded))
    incomings, finals = [], []
    for _ in range(depth):
        state_rms = math.sqrt(math.fsum(v * v for v in current) / len(current))
        scale = LAMBDA * input_rms / math.sqrt(input_rms ** 2 + state_rms ** 2 + EPSILON ** 2)
        incoming = [base + scale * carry for base, carry in zip(encoded, current)]
        incomings.append(incoming)
        current = parameters.forward(incoming)
        finals.append(current)
    return incomings, current


def score(parameters, encoded, readout, depth: int) -> int:
    if depth == 0:
        vector = parameters.forward(encoded)
    else:
        _, vector = recurrence_states(parameters, encoded, depth)
    scores = [math.fsum(a * b for a, b in zip(row, vector)) for row in readout]
    return max(range(len(scores)), key=lambda c: scores[c])


def fit_on(parameters_inputs, classes, readout, lam=ad.DEFAULT_RIDGE_LAMBDA):
    weights = ad.ridge_weights(
        [ad.tanh_vector(vector) for vector in parameters_inputs], classes,
        nclass=len(readout), lam=lam,
    )
    return ad.decompose_from_free_readout(weights, readout)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--folds", type=int, default=DEFAULT_FOLDS)
    args = parser.parse_args(argv)

    print("loading the cached rows and rebuilding the encoded slots...")
    encoded, classes = load_encoded()
    readout = readout_rows()
    print(f"  slots: {len(encoded)}   classes present: {len(set(classes))}")
    print()

    order = list(range(len(encoded)))
    buckets = [order[index::args.folds] for index in range(args.folds)]

    # --- stage 0: the recorded method, fitted on the encoded slots -------------------------
    print("=" * 100)
    print("1. THE DEPTH PROFILE OF THE RECORDED SOLVE")
    print("=" * 100)
    print()
    fold_parameters = []
    for fold in range(args.folds):
        held = set(buckets[fold])
        train = [index for index in order if index not in held]
        parameters = fit_on([encoded[index] for index in train],
                            [classes[index] for index in train], readout)
        fold_parameters.append({"parameters": parameters, "held": sorted(held), "train": train})

    print(f"{'depth':>7} {'correct':>9} {'total':>7} {'accuracy':>11}")
    print("-" * 100)
    profile = {}
    for depth in DEPTHS:
        correct = total = 0
        for entry in fold_parameters:
            for index in entry["held"]:
                correct += 1 if score(entry["parameters"], encoded[index], readout, depth) == classes[index] else 0
                total += 1
        profile[depth] = correct / total
        print(f"{depth:7d} {correct:9d} {total:7d} {100 * correct / total:10.2f}%")
    print()

    # --- stage 1: refine the solve for the functional the run computes ---------------------
    print("=" * 100)
    print("2. FITTING FOR THE RECURRENCE — a fixed-point refinement, scored through depth 8")
    print("=" * 100)
    print()
    print("  T_0 is the recorded solve. Each refinement re-fits on the states the CURRENT")
    print("  parameters actually feed the block, then is scored through the recurrence.")
    print()
    current = [dict(entry) for entry in fold_parameters]
    print(f"{'round':>7} {'depth 0':>11} {'depth 8':>11}   what was fitted on")
    print("-" * 100)
    for round_index in range(REFINEMENTS + 1):
        at0 = at8 = total = 0
        for entry in current:
            for index in entry["held"]:
                at0 += 1 if score(entry["parameters"], encoded[index], readout, 0) == classes[index] else 0
                at8 += 1 if score(entry["parameters"], encoded[index], readout, 8) == classes[index] else 0
                total += 1
        label = "encoded slots" if round_index == 0 else f"recurrence states (round {round_index})"
        print(f"{round_index:7d} {100 * at0 / total:10.2f}% {100 * at8 / total:10.2f}%   {label}")
        if round_index == REFINEMENTS:
            break
        # re-fit: collect the states the CURRENT parameters feed the block, per training row
        refined = []
        for entry in current:
            inputs, targets = [], []
            for index in entry["train"]:
                incomings, _final = recurrence_states(entry["parameters"], encoded[index], 8)
                # one training example per pass the block actually performs
                for incoming in incomings:
                    inputs.append(incoming)
                    targets.append(classes[index])
            refined.append({
                "parameters": fit_on(inputs, targets, readout),
                "held": entry["held"],
                "train": entry["train"],
            })
        current = refined
    print()

    print("=" * 100)
    print("READING")
    print("=" * 100)
    print()
    print(
        "If the depth profile falls monotonically, the registered recursion degrades the\n"
        "initialisation pass by pass rather than converging elsewhere. If a refinement round\n"
        "scores above the recorded 44.68% through depth 8, the solve was aimed at a functional\n"
        "the run does not compute, and aiming it correctly is a $0 architecture improvement.\n"
        "If no refinement beats it, the recurrence's cost is not an aiming error.\n"
        "\n"
        "Every number here is out-of-fold on the learner's own 564-packet registry, and the\n"
        "encoded slots are rebuilt (RECONSTRUCTION_GAP.md measures that rebuild at +0.781\n"
        "correlation with the recorded logits). This is a construction measurement, not a run."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
