"""Prepare the analytic-initialisation arm, fold-wise, and refuse the circular version.

`records/analytic_decompose_phase0_001/PHASE0_RECORD_DRAFT.md` specifies arm A: initialise the
registered ``^6`` block at the closed-form solution instead of letting stochastic gradient descent
find it, then run with **zero** updates. `cncm/analytic_decompose.py` is the arithmetic. This tool
is the preparation step, and it exists so the owner has something concrete to sign.

Why this refuses the obvious version
------------------------------------
The tempting thing is to fit one ``T`` on all 564 registry packets and evaluate on all 564. That
is **the same-sample reconstruction the project already prohibits** — the neural rule in OS-017
reads "same-sample resistance reconstruction is circular and prohibited", and the phase-0 record's
section 3.1 requires the fitting material to be disjoint from every evaluation set.

The 63.83% this arm rests on is a **5-fold cross-validated** number. A single whole-course ``T``
would not be that number and would not be admissible. So :func:`fit_folds` produces **one set of
parameters per fold**, each fitted on the other folds, and :func:`fit_whole_course` exists only to
be refused by :func:`refuse_whole_course_fit`.

What it produces
----------------
    fit_folds(...)            per-fold registered parameter sets, fitted out-of-fold
    verify_construction(...)  the exactness identities, measured rather than asserted
    alias_distribution(...)   the G6 reading: distinct aliases, commonest share, focus rank
    refuse_whole_course_fit() the guard, with the reason stated

Nothing here launches a run, reserves budget, or touches a device. It reads the frozen public
course and the cached feature rows, and it writes nothing unless asked.

Pure standard library for all arithmetic.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import pickle
import struct
import sys

HOME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

from cncm import analytic_decompose as ad  # noqa: E402

SEED = 20260916
D = ad.D_MODEL
CACHE = Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
DEFAULT_FOLDS = 5


class PreparationRefused(RuntimeError):
    """The requested preparation would be circular or would not reproduce the recorded figure."""


def refuse_whole_course_fit(evaluation: str) -> None:
    """Refuse fitting one parameter set on the whole course for whole-course evaluation.

    Always raises. It exists so the circular preparation has a name, a reason, and a call site
    rather than being something a future reader has to remember not to do.
    """
    raise PreparationRefused(
        f"refused: fitting one parameter set on the whole course and evaluating it on "
        f"{evaluation!r} is same-sample reconstruction. The 63.83% this arm rests on is a "
        f"5-fold cross-validated number, and the phase-0 record requires the fitting material to "
        f"be disjoint from every evaluation set. Use fit_folds()."
    )


def load_rows() -> list:
    if not CACHE.is_file():
        raise PreparationRefused(
            f"feature cache not found at {CACHE}; build it with "
            f"records/encoder_capacity_001/measure_real_slot_encoding.py first"
        )
    return pickle.loads(CACHE.read_bytes())


def encoded_slots(rows: list) -> tuple:
    """The real encoded slots the learner receives, and the focus class of each.

    Rebuilds ``normalize((packet_vector + slot_query_row)/sqrt(2))`` for one representative slot
    per packet, exactly as `records/encoder_capacity_001/measure_real_slot_encoding.py` does, so
    this tool works on the same features as the recorded 63.83%.
    """
    from cas_meta2.typed_teaching import binding, course, slots as slots_module, worker_contract

    frozen, _tokenizer, _source = worker_contract.load_material(HOME)

    def row_vector(domain):
        return list(struct.unpack("<64f", binding.row_bytes(domain, seed=SEED, d_model=D)))

    queries, positions = [], []
    for index, record in enumerate(frozen["registry"], 1):
        packet = course.model_packet(frozen, record["record_id"])
        try:
            plan = slots_module.compile_slots(packet)
            validated = slots_module.validate_plan(packet, plan)
            spec = binding._query_spec(validated, plan["slots"][0])
        except Exception:  # noqa: BLE001 - reported by omission from `positions`
            continue
        queries.append(row_vector(["query", spec]))
        # the cached feature rows are positionally aligned with the frozen registry, not keyed by
        # record_id; `measure_real_slot_encoding.py` builds its map the same way.
        positions.append(index - 1)
        if index % 200 == 0:
            print(f"  slot queries built: {index}/{len(frozen['registry'])}", flush=True)

    if len(rows) != len(frozen["registry"]):
        raise PreparationRefused(
            f"the feature cache holds {len(rows)} rows but the registry holds "
            f"{len(frozen['registry'])}; they are positionally aligned and must match"
        )
    vectors, classes = [], []
    for position, query in zip(positions, queries):
        row = rows[position]
        encoded = [(a + b) / math.sqrt(2.0) for a, b in zip(row["mean"], query)]
        norm = math.sqrt(math.fsum(value * value for value in encoded))
        vectors.append([value / norm for value in encoded])
        classes.append(int(row["focus"]))
    return vectors, classes


def readout_rows(nclass: int = 64) -> list:
    from cas_meta2.typed_teaching import binding

    return [
        list(struct.unpack("<64f", binding.row_bytes(["readout", f"W{c}"], seed=SEED, d_model=D)))
        for c in range(nclass)
    ]


def fit_folds(
    encoded: list,
    classes: list,
    readout: list,
    *,
    folds: int = DEFAULT_FOLDS,
    lam: float = ad.DEFAULT_RIDGE_LAMBDA,
) -> list:
    """One registered parameter set per fold, each fitted on the other folds.

    Returns a list of dicts, each with the fold index, the held-out row indices, the parameter
    digest and the parameters themselves. **No fold's parameters are fitted on the rows it is
    evaluated on.**
    """
    if folds < 2:
        raise PreparationRefused("cross-validation needs at least two folds")
    order = list(range(len(encoded)))
    buckets = [order[index::folds] for index in range(folds)]
    fitted = []
    for fold in range(folds):
        held = set(buckets[fold])
        train = [index for index in order if index not in held]
        weights = ad.ridge_weights(
            [ad.tanh_vector(encoded[index]) for index in train],
            [classes[index] for index in train],
            nclass=len(readout),
            lam=lam,
        )
        parameters = ad.decompose_from_free_readout(weights, readout)
        fitted.append({
            "fold": fold,
            "rows_fitted_on": len(train),
            "rows_held_out": len(buckets[fold]),
            "held_out_indices": sorted(buckets[fold]),
            "parameter_digest": parameters.digest(),
            "parameters": parameters,
        })
    return fitted


def verify_construction(fitted: list, encoded: list, classes: list, readout: list) -> dict:
    """Measure the two identities on every fold's parameters rather than asserting them.

    ``identity_residual`` is zero for parameters built by ``parameters_for_map`` and is the
    statement that the registered module computes ``T @ tanh(x)`` exactly.
    ``realisation_score_residual`` is the statement that the frozen readout reproduces the free
    readout's scores exactly, and needs the free-readout matrix the fold was built from.
    """
    worst_identity = 0.0
    worst_realisation = 0.0
    shapes_ok = True
    for entry in fitted:
        parameters = entry["parameters"]
        held = entry["held_out_indices"]
        shapes_ok = shapes_ok and parameters.matches_registered_shapes()
        if held:
            worst_identity = max(
                worst_identity,
                ad.identity_residual(parameters, [encoded[index] for index in held[:64]]),
            )
        train = [index for index in range(len(encoded)) if index not in set(held)]
        if not train or not held:
            continue
        weights = ad.ridge_weights(
            [ad.tanh_vector(encoded[index]) for index in train],
            [classes[index] for index in train],
            nclass=len(readout),
        )
        worst_realisation = max(
            worst_realisation,
            ad.realisation_score_residual(
                weights, readout, [encoded[index] for index in held[:64]]
            ),
        )
    return {
        "registered_shapes_hold": shapes_ok,
        "worst_identity_residual": worst_identity,
        "worst_realisation_score_residual": worst_realisation,
    }


def alias_distribution(fitted: list, encoded: list, readout: list, symbols: tuple) -> dict:
    """The G6 reading over held-out rows: distinct aliases, commonest share, focus rank.

    This is the quantity `PHASE0_RECORD_DRAFT.md` G6 is written on. Baseline from the recorded
    run at cursor 160: **9 distinct aliases of 64, `W36` at 44.3%, focus alias ranked #1 in 10 of
    210 world-typed slots.**
    """
    counts: dict = {}
    ranks = []
    for entry in fitted:
        parameters = entry["parameters"]
        for index in entry["held_out_indices"]:
            scores = ad.frozen_readout_scores(readout, parameters, encoded[index])
            order = sorted(range(len(scores)), key=lambda c: (-scores[c], c))
            counts[symbols[order[0]]] = counts.get(symbols[order[0]], 0) + 1
            focus = entry["_classes"][index]
            ranks.append(order.index(focus) + 1)
    total = sum(counts.values())
    commonest = max(counts.values()) if counts else 0
    return {
        "slots": total,
        "distinct_aliases": len(counts),
        "commonest_alias": max(counts, key=lambda name: counts[name]) if counts else None,
        "commonest_share": commonest / total if total else 0.0,
        "focus_rank_1": sum(1 for rank in ranks if rank == 1),
        "focus_rank_6_or_worse": sum(1 for rank in ranks if rank >= 6),
        "median_focus_rank": sorted(ranks)[len(ranks) // 2] if ranks else None,
    }


def evaluate_folds(fitted: list, encoded: list, readout: list) -> float:
    """Held-out accuracy of each fold's parameters through the frozen readout."""
    correct = 0
    total = 0
    for entry in fitted:
        parameters = entry["parameters"]
        for index in entry["held_out_indices"]:
            scores = ad.frozen_readout_scores(readout, parameters, encoded[index])
            pick = max(range(len(scores)), key=lambda c: scores[c])
            correct += 1 if pick == entry["_classes"][index] else 0
            total += 1
    return correct / total if total else 0.0


LAMBDA = 0.5
EPSILON = 1e-6
PREDICTION_DEPTH = 8


def through_recurrence(parameters, encoded, depth: int = PREDICTION_DEPTH):
    """Run the registered recurrence over one slot's encoded vector.

    `recurrence.run_passes` with ``state=None``, ``lambda_ = 0.5``, ``epsilon = 1e-6`` and the
    registered prediction depth of 8. For the analytic parameters the block is ``T @ tanh(x)``
    exactly, so this is exact arithmetic on whatever input it is given; the only approximation is
    the encoded slot itself, which this tool rebuilds.
    """
    current = [0.0] * D
    input_rms = math.sqrt(math.fsum(value * value for value in encoded) / len(encoded))
    for _ in range(depth):
        state_rms = math.sqrt(math.fsum(value * value for value in current) / len(current))
        scale = LAMBDA * input_rms / math.sqrt(input_rms ** 2 + state_rms ** 2 + EPSILON ** 2)
        incoming = [base + scale * carry for base, carry in zip(encoded, current)]
        current = parameters.forward(incoming)
    return current


def evaluate_through_recurrence(fitted: list, encoded: list, readout: list) -> float:
    correct, total = 0, 0
    for entry in fitted:
        parameters = entry["parameters"]
        for index in entry["held_out_indices"]:
            vector = through_recurrence(parameters, encoded[index])
            scores = [
                math.fsum(a * b for a, b in zip(row, vector)) for row in readout
            ]
            pick = max(range(len(scores)), key=lambda c: scores[c])
            correct += 1 if pick == entry["_classes"][index] else 0
            total += 1
    return correct / total if total else 0.0


def alias_distribution_through_recurrence(
    fitted: list, encoded: list, readout: list, symbols: tuple
) -> dict:
    counts: dict = {}
    ranks = []
    for entry in fitted:
        parameters = entry["parameters"]
        for index in entry["held_out_indices"]:
            vector = through_recurrence(parameters, encoded[index])
            scores = [math.fsum(a * b for a, b in zip(row, vector)) for row in readout]
            order = sorted(range(len(scores)), key=lambda c: (-scores[c], c))
            counts[symbols[order[0]]] = counts.get(symbols[order[0]], 0) + 1
            ranks.append(order.index(entry["_classes"][index]) + 1)
    total = sum(counts.values())
    commonest = max(counts.values()) if counts else 0
    return {
        "slots": total,
        "distinct_aliases": len(counts),
        "commonest_alias": max(counts, key=lambda name: counts[name]) if counts else None,
        "commonest_share": commonest / total if total else 0.0,
        "focus_rank_1": sum(1 for rank in ranks if rank == 1),
        "focus_rank_6_or_worse": sum(1 for rank in ranks if rank >= 6),
        "median_focus_rank": sorted(ranks)[len(ranks) // 2] if ranks else None,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--folds", type=int, default=DEFAULT_FOLDS)
    parser.add_argument("--report", action="store_true",
                        help="print the preparation report (default action)")
    parser.add_argument("--write-parameters", type=Path, default=None,
                        help="write the per-fold parameters as JSON; nothing is written without this")
    parser.add_argument("--whole-course-fit", action="store_true",
                        help="always refused; present so the refusal has a call site")
    args = parser.parse_args(argv)

    if args.whole_course_fit:
        refuse_whole_course_fit("the same course")

    print("loading cached feature rows...")
    rows = load_rows()
    print(f"  rows: {len(rows)}")
    print("rebuilding the real encoded slots from the frozen public material...")
    encoded, classes = encoded_slots(rows)
    print(f"  encoded slots: {len(encoded)}")
    readout = readout_rows()
    symbols = tuple(f"W{c}" for c in range(len(readout)))

    print(f"fitting {args.folds} folds, each out-of-fold...")
    fitted = fit_folds(encoded, classes, readout, folds=args.folds)
    for entry in fitted:
        entry["_classes"] = classes

    accuracy = evaluate_folds(fitted, encoded, readout)
    distribution = alias_distribution(fitted, encoded, readout, symbols)
    verification = verify_construction(fitted, encoded, classes, readout)
    recurrence_accuracy = evaluate_through_recurrence(fitted, encoded, readout)
    recurrence_distribution = alias_distribution_through_recurrence(
        fitted, encoded, readout, symbols
    )

    print()
    print("=" * 92)
    print("ARM A PREPARATION REPORT")
    print("=" * 92)
    print()
    print("  Read this as a PREPARATION report, not a result. It measures the CONSTRUCTION on")
    print("  out-of-fold rows. It is not a run: no arm has been launched and nothing is licensed.")
    print()
    print(f"  folds                        {len(fitted)}")
    print(f"  rows fitted/held per fold    "
          f"{fitted[0]['rows_fitted_on']}/{fitted[0]['rows_held_out']}")
    print(f"  registered shapes hold       {verification['registered_shapes_hold']}")
    print(f"  worst identity residual      {verification['worst_identity_residual']:.3e}")
    print(f"  worst realisation residual   {verification['worst_realisation_score_residual']:.3e}")
    print()
    print(f"{'reading':>34} {'direct forward':>16} {'through recurrence':>20}")
    print("-" * 92)
    print(f"{'cross-validated accuracy':>34} {100 * accuracy:15.2f}% {100 * recurrence_accuracy:19.2f}%")
    print(f"{'distinct aliases emitted (of 64)':>34} {distribution['distinct_aliases']:16d}"
          f" {recurrence_distribution['distinct_aliases']:20d}")
    print(f"{'commonest alias share':>34} {100 * distribution['commonest_share']:15.1f}%"
          f" {100 * recurrence_distribution['commonest_share']:19.1f}%")
    print(f"{'focus alias ranked #1 (of 564)':>34} {distribution['focus_rank_1']:16d}"
          f" {recurrence_distribution['focus_rank_1']:20d}")
    print(f"{'focus alias #6 or worse':>34} {distribution['focus_rank_6_or_worse']:16d}"
          f" {recurrence_distribution['focus_rank_6_or_worse']:20d}")
    print()
    print("  G6 as written in the phase-0 record: `arm A emits strictly more than 9 distinct world")
    print("  aliases across the 210 world-typed reference slots, and the commonest single alias is")
    print("  below 44.3% of emissions`.")
    for label, reading in (("direct", distribution), ("recurrence", recurrence_distribution)):
        passes = reading["distinct_aliases"] > 9 and reading["commonest_share"] < 0.443
        print(f"    {label:>10}: {reading['distinct_aliases']} distinct, "
              f"{100 * reading['commonest_share']:.1f}% commonest -> G6 would "
              f"{'PASS' if passes else 'FAIL'}")
    print()
    print("  DENOMINATORS DIFFER. The preparation scores 564 representative slots, one per")
    print("  packet. The recorded 9-of-64 and 44.3% figures are over the 210 world-typed")
    print("  reference slots of the context and definition packets. The comparison is of shape,")
    print("  not of like-for-like counts.")
    print()
    print("  THE RECURRENCE READING IS THE CLOSER PREDICTION of what a run would do, because a")
    print("  run applies `run_passes` at depth 8. It is not exact: the encoded slot is rebuilt,")
    print("  and `RECONSTRUCTION_GAP.md` measures that rebuild at +0.781 correlation with the")
    print("  recorded logits. For the analytic parameters the block itself is exact.")
    print()
    for entry in fitted:
        print(f"    fold {entry['fold']}: fitted on {entry['rows_fitted_on']}, "
              f"held {entry['rows_held_out']}, digest {entry['parameter_digest'][:16]}")
    print()

    if args.write_parameters:
        payload = {
            "schema": "cncm.analytic-arm-preparation/0.1",
            "evaluation": "OUT_OF_FOLD",
            "folds": [
                {
                    "fold": entry["fold"],
                    "rows_fitted_on": entry["rows_fitted_on"],
                    "rows_held_out": entry["rows_held_out"],
                    "parameter_digest": entry["parameter_digest"],
                    "parameters": {
                        name: [list(row) for row in matrix]
                        for name, matrix in entry["parameters"].parameter_dict().items()
                    },
                }
                for entry in fitted
            ],
            "cross_validated_accuracy": accuracy,
            "alias_distribution": distribution,
            "verification": verification,
            "licensed_to_run": False,
            "note": (
                "preparation only; a run needs an owner-signed phase record. Fitting is "
                "out-of-fold and no fold's parameters were fitted on the rows it is scored on."
            ),
        }
        args.write_parameters.parent.mkdir(parents=True, exist_ok=True)
        args.write_parameters.write_text(
            json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8"
        )
        print(f"  wrote {args.write_parameters}")
    else:
        print("  nothing written (pass --write-parameters to emit the per-fold artifacts)")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
