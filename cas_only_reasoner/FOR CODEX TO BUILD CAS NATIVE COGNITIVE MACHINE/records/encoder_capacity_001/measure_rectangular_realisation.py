"""Does the rectangular construction actually carry a fitted readout? Measured on the real readout.

Pure Python. Standard library plus the project's pure modules. No torch, no device, no learned run
weights, no forward pass of the recurrent block, no training, no new run.

What this adds
--------------
Round 30 fitted a free readout `W` directly on `tanh(encoded)` and scored it: the many-decision half
went 5.0167% -> 12.0401%, with `definition` at 48.5714%, but the one-decision half fell 44.1510
points, and it was **a substituted readout, not the machine's**.

`cncm/analytic_decompose.decompose_from_free_readout` is the registered way to install such a readout
into the real machine -- it builds `^6` parameters with `T = R^-1 W^T` so the frozen readout `R`
behaves as `W`. It requires `nclass == core_width`, and the registered readout is `[90, 64]`, so it
**refuses the real readout** and every analytic measurement so far has used a 64-row submatrix.

Round 36 added `decompose_from_free_readout_rectangular`, which takes `nclass > core_width`. It
cannot realise every `W`: `R T` always lands in the column space of `R`, so it realises the
**orthogonal projection** of `W^T` onto that space and reports the residual.

This file measures the three things that decide whether that is worth a run:

  1. the residual of the construction on the registered `[90, 64]` readout
  2. the exact-answer score when the scores come from `R . (T . tanh(encoded))` -- the real path
  3. the same score when they come from `W^T . tanh(encoded)` -- the idealised path round 30 measured

The difference between (2) and (3) is what the frozen readout costs. If it is small, the rectangular
construction is a working engineering path; if it is large, the frozen readout is the obstacle and the
free readout is an idealisation that cannot be installed.
"""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import struct
import sys
from collections import Counter, defaultdict

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

from cas_meta2.typed_teaching import answers, binding, checker, course, slots, worker_contract  # noqa: E402
from cncm.analytic_decompose import (  # noqa: E402
    D_MODEL, AnalyticDecomposeError, decompose_from_free_readout_rectangular, matmul,
    matvec, ridge_weights, tanh_vector, transpose,
)

RECEIPT = HOME / "records/typed_matched_001/receipt_20260919_m"
SEED = 20260916
FOLDS = 5
LAMBDA = 1.0
MANY = ("edge_account", "role_set", "parts", "context", "definition")
FROZEN_READOUT = "14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667"
FROZEN_PROJECTION = "4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9"
SYMBOL_INDEX = {symbol: index for index, symbol in enumerate(slots.SYMBOLS)}


def rows_of(raw: bytes, width: int = D_MODEL) -> list:
    flat = list(struct.unpack(f"<{len(raw) // 4}f", raw))
    return [flat[at:at + width] for at in range(0, len(flat), width)]


def unit(vector: list) -> list:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0 or not math.isfinite(norm):
        raise AssertionError("zero or non-finite norm")
    return [value / norm for value in vector]


def packet_vector(packet, tokenizer, projection) -> list:
    plan = binding.compile_packet(packet, tokenizer, seed=SEED)
    ids = [token for row in plan["rows"] for token in row["token_ids"]]
    vectors = []
    for row in plan["rows"]:
        span = ids[row["start"]:row["start"] + row["count"]]
        accumulated = [0.0] * D_MODEL
        for at, token in enumerate(span):
            order, signs = binding.signed_permutation(seed=SEED, scope=row["scope"],
                                                      ordinal=row["ordinal"], position=at, d_model=D_MODEL)
            base = projection[token]
            for dest, (origin, sign) in enumerate(zip(order, signs)):
                accumulated[dest] += sign * base[origin]
        vectors.append(unit([value / math.sqrt(row["count"]) for value in accumulated]))
    total = [0.0] * D_MODEL
    for vector in vectors:
        for index in range(D_MODEL):
            total[index] += vector[index]
    return unit([value / math.sqrt(len(vectors)) for value in total])


def true_symbol(kind, slot, value, plan) -> str:
    worlds = plan["aliases"]["worlds"]
    node_alias = {node["ref"]: node["alias"] for world in worlds for node in world["nodes"]}
    if kind == "edge_account":
        present = {(row["source"], row["target"]) for row in value["edges"]}
        return "PRESENT" if (slot["coordinates"][0], slot["coordinates"][1]) in present else "ABSENT"
    if kind == "parts":
        return "PRESENT" if slot["coordinates"][0] in set(value["nodes"]) else "ABSENT"
    if kind == "role_set":
        return "PRESENT" if slot["coordinates"][0] in set(value["roles"]) else "ABSENT"
    if kind == "context":
        if slot["field"] == "participant":
            return "PRESENT" if slot["coordinates"][0] in set(value["participants"]) else "ABSENT"
        for world in worlds:
            if answers.declaration_ref(world["world_id"], "setting") == value["setting_ref"]:
                return world["alias"]
    if kind == "definition":
        if slot["field"] == "whole":
            return node_alias[value["whole"]]
        for world in worlds:
            if answers.declaration_ref(world["world_id"], slot["field"].replace("_ref", "")) == value[slot["field"]]:
                return world["alias"]
    raise AssertionError(kind)


def main() -> int:
    frozen_course, tokenizer, _ = worker_contract.load_material(HOME)
    readout_raw = binding.readout_bytes(seed=SEED)
    projection_raw = binding.projection_bytes(tokenizer, seed=SEED)
    gate = (hashlib.sha256(readout_raw).hexdigest() == FROZEN_READOUT
            and hashlib.sha256(projection_raw).hexdigest() == FROZEN_PROJECTION)
    print(f"FROZEN-BYTE GATE: {'MATCH' if gate else 'MISMATCH'}", flush=True)
    if not gate:
        return 1
    readout = rows_of(readout_raw)
    projection = rows_of(projection_raw)
    print(f"registered readout shape: ({len(readout)}, {len(readout[0])})", flush=True)
    print()

    predictions = json.loads(
        (RECEIPT / "collected/results/artifacts/final_predictions.json").read_text(encoding="utf-8")
    )["predictions"]
    cases = []
    for index, prediction in enumerate(predictions):
        packet = course.model_packet(frozen_course, prediction["record_id"])
        query = packet["record"]["query"]
        kind = query["kind"]
        if kind not in MANY:
            continue
        plan = slots.compile_slots(packet)
        validated = slots.validate_plan(packet, plan)
        truth = checker.derive_target(packet["source"], query)["admissible_answers"][0]
        pv = packet_vector(packet, tokenizer, projection)
        rows = []
        for slot in plan["slots"]:
            spec = binding._query_spec(validated, slot)
            qv = list(struct.unpack(f"<{D_MODEL}f", binding.row_bytes(["query", spec], seed=SEED)))
            rows.append({"slot_id": slot["slot_id"], "symbols": list(slot["symbols"]),
                         "encoded": unit([pv[at] + qv[at] for at in range(D_MODEL)]),
                         "label": true_symbol(kind, slot, truth["value"], plan)})
        cases.append({"fold": index % FOLDS, "kind": kind, "packet": packet, "plan": plan,
                      "truth": truth["value"], "recorded": prediction["decisions"],
                      "recorded_value": prediction["answer"]["value"], "rows": rows})
    print(f"questions: {len(cases)}", flush=True)
    print()

    residuals = []
    scores = {name: defaultdict(Counter) for name in ("recorded", "direct", "through_T")}
    for fold in range(FOLDS):
        train = [(tanh_vector(row["encoded"]), SYMBOL_INDEX[row["label"]])
                 for case in cases if case["fold"] != fold for row in case["rows"]]
        weights = ridge_weights([row for row, _ in train], [target for _, target in train],
                                nclass=len(slots.SYMBOLS), lam=LAMBDA)
        try:
            parameters, report = decompose_from_free_readout_rectangular(weights, readout)
        except AnalyticDecomposeError as error:
            print(f"fold {fold}: the construction REFUSED the registered readout: {error}", flush=True)
            return 1
        residuals.append(report["residual"])
        print(f"fold {fold}: residual {report['residual']:.10f}   exact {report['exact']}", flush=True)

        for case in cases:
            if case["fold"] != fold:
                continue
            kind = case["kind"]
            scores["recorded"][kind]["questions"] += 1
            scores["recorded"][kind]["correct"] += 1 if (
                json.dumps(case["recorded_value"], sort_keys=True)
                == json.dumps(case["truth"], sort_keys=True)) else 0
            tables = {}
            for name in ("direct", "through_T"):
                tables[name] = {}
            for row in case["rows"]:
                feature = tanh_vector(row["encoded"])
                for name in ("direct", "through_T"):
                    if name == "direct":
                        vector = feature
                        rows_out = [[sum(weights[at][c] * vector[at] for at in range(D_MODEL))
                                     for c in range(len(slots.SYMBOLS))]]
                        score_vector = rows_out[0]
                    else:
                        transformed = parameters.forward(row["encoded"])
                        score_vector = matvec(readout, transformed)
                    tables[name][row["slot_id"]] = {
                        symbol: score_vector[SYMBOL_INDEX[symbol]] for symbol in row["symbols"]}
            for name in ("direct", "through_T"):
                scores[name][kind]["questions"] += 1
                try:
                    decisions = slots.score_decisions(case["packet"], tables[name])
                    assembled = slots.assemble_answer(case["packet"], decisions)["value"]
                except Exception:                                     # noqa: BLE001
                    continue
                scores[name][kind]["correct"] += 1 if (
                    json.dumps(assembled, sort_keys=True) == json.dumps(case["truth"], sort_keys=True)) else 0

    print()
    print("=" * 96)
    print("EXACT-ANSWER ACCURACY — recorded vs idealised readout vs the registered path")
    print("=" * 96)
    print()
    print(f"{'kind':>15} {'q':>4} {'recorded':>10} {'direct W':>10} {'through T':>11}"
          f" {'T - direct':>11}")
    print("-" * 96)
    many = {name: Counter() for name in scores}
    for kind in MANY:
        row = scores["recorded"][kind]
        if not row["questions"]:
            continue
        questions = row["questions"]
        cells = {}
        for name in ("recorded", "direct", "through_T"):
            cells[name] = scores[name][kind]["correct"] / questions
            many[name]["correct"] += scores[name][kind]["correct"]
            many[name]["questions"] += questions
        print(f"{kind:>15} {questions:4d} {cells['recorded']:10.4%} {cells['direct']:10.4%}"
              f" {cells['through_T']:11.4%} {cells['through_T'] - cells['direct']:+11.4%}")
    print("-" * 96)
    for name, label in (("recorded", "recorded (the run itself)"),
                        ("direct", "direct free readout (idealised)"),
                        ("through_T", "through the registered ^6 block")):
        print(f"{label:>40} {many[name]['correct'] / many[name]['questions']:10.4%}"
              f"   ({many[name]['correct']} of {many[name]['questions']})")
    print()
    print(f"construction residual: max {max(residuals):.10f}   exact in "
          f"{sum(1 for value in residuals if value == 0.0)} of {len(residuals)} folds")
    print()
    print("direct    = W^T . tanh(encoded), the idealised readout round 30 measured")
    print("through_T = R . (T . tanh(encoded)) with T from the registered construction,")
    print("            which is the path a real run would take")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
