"""Which field of the answer binds? Decomposing the fitted readout by field.

Pure Python. Standard library plus the project's pure modules. No torch, no device, no learned run
weights, no forward pass of the block, no training, no new run.

The question
------------
Round 30 measured that a fitted linear readout of `tanh(encoded)` lifts the many-decision half from
5.0167% to 12.0401% (16.0535% with `correspondence` out of the shared fit), and that the lift is
almost entirely one kind:

    definition     0.0000%  ->  25.7143% - 44.2857%
    edge_account   0.0000%  ->   2.8571% -  4.2857%
    context        0.0000%  ->   2.8571% -  4.2857%
    role_set       8.3333%  ->  11.1111%
    parts         22.6415%  ->  15.0943%   (falls)

`definition` and `context` are the same size (70 questions each), their slots have the same shape
(one coordinate each, PRESENT/ABSENT symbols or a world alias), and both answers are verbatim packet
fields. One moves 44 points and the other 4. This file asks which field of the answer binds.

What is measured
----------------
Fit the readout once, on the five many-decision kinds only, five folds by question. Then for every
held-out question score four things through the project's own `assemble_answer`:

  fitted            every slot decided by the fitted readout
  fitted + f truth  every slot decided by the fitted readout, except field `f`'s slots, which are
                    given the true symbol. The jump this produces is what field `f` is worth.
  field slot accuracy   per-slot argmax accuracy of the fitted readout, by field

A field that is worth a large jump is the field that binds the answer. A field worth nothing is one
the readout already gets right, or one whose slots do not decide the answer.

This is a decoder-only decomposition over recorded artifacts and the frozen encoder's own bytes. The
truth is derived by the project's own `checker.derive_target` and is used ONLY in the substitution
arms, never in the fit.
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
COMP = HOME / "research" / "CAS_META_2_COMPOSITION"
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(COMP))

from cas_meta2.typed_teaching import answers, binding, checker, course, slots, worker_contract  # noqa: E402
from cncm.analytic_decompose import D_MODEL, ridge_weights, tanh_vector  # noqa: E402

RECEIPT = HOME / "records/typed_matched_001/receipt_20260919_m"
SEED = 20260916
FOLDS = 5
LAMBDA = 1.0
MANY = ("edge_account", "role_set", "parts", "context", "definition")
FROZEN = {
    "projection": "4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9",
    "readout": "14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667",
}
SYMBOL_INDEX = {symbol: index for index, symbol in enumerate(slots.SYMBOLS)}


def rows_of(raw: bytes, width: int = D_MODEL) -> list:
    flat = list(struct.unpack(f"<{len(raw) // 4}f", raw))
    return [flat[at:at + width] for at in range(0, len(flat), width)]


def unit(vector: list) -> list:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0 or not math.isfinite(norm):
        raise AssertionError("zero or non-finite norm")
    return [value / norm for value in vector]


def gate(tokenizer):
    for name, raw in (("projection", binding.projection_bytes(tokenizer, seed=SEED)),
                      ("readout", binding.readout_bytes(seed=SEED))):
        if hashlib.sha256(raw).hexdigest() != FROZEN[name]:
            raise AssertionError(f"frozen {name} does not reproduce")
    return rows_of(binding.projection_bytes(tokenizer, seed=SEED))


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
    projection = gate(tokenizer)
    print("FROZEN-BYTE GATE: projection MATCH  readout MATCH", flush=True)

    predictions = json.loads(
        (RECEIPT / "collected/results/artifacts/final_predictions.json").read_text(encoding="utf-8")
    )["predictions"]

    cases = []
    for index, prediction in enumerate(predictions):
        packet = course.model_packet(frozen_course, prediction["record_id"])
        query = packet["record"]["query"]
        if query["kind"] not in MANY:
            continue
        plan = slots.compile_slots(packet)
        validated = slots.validate_plan(packet, plan)
        target = checker.derive_target(packet["source"], query)
        truth = target["admissible_answers"][0]
        admissible = {json.dumps(row["value"], sort_keys=True) for row in target["admissible_answers"]}
        pv = packet_vector(packet, tokenizer, projection)
        rows = []
        for slot in plan["slots"]:
            spec = binding._query_spec(validated, slot)
            qv = list(struct.unpack(f"<{D_MODEL}f", binding.row_bytes(["query", spec], seed=SEED)))
            rows.append({"slot_id": slot["slot_id"], "field": slot["field"], "symbols": list(slot["symbols"]),
                         "encoded": unit([pv[at] + qv[at] for at in range(D_MODEL)]),
                         "label": true_symbol(plan["kind"], slot, truth["value"], plan)})
        cases.append({"fold": index % FOLDS, "kind": plan["kind"], "packet": packet, "plan": plan,
                      "admissible": admissible, "rows": rows})
        cases[-1]["decisions"] = prediction["decisions"]
    print(f"questions: {len(cases)}   slots: {sum(len(case['rows']) for case in cases)}", flush=True)
    print()

    fields_of = defaultdict(set)
    for case in cases:
        for row in case["rows"]:
            fields_of[case["kind"]].add(row["field"])

    # variant name -> (kind -> Counter)
    tally = defaultdict(lambda: defaultdict(Counter))
    slot_hits = defaultdict(lambda: defaultdict(Counter))

    for fold in range(FOLDS):
        train = [(tanh_vector(row["encoded"]), SYMBOL_INDEX[row["label"]])
                 for case in cases if case["fold"] != fold for row in case["rows"]]
        weights = ridge_weights([row for row, _ in train], [target for _, target in train],
                                nclass=len(slots.SYMBOLS), lam=LAMBDA)

        for case in cases:
            if case["fold"] != fold:
                continue
            kind = case["kind"]
            per_row = {}
            for row in case["rows"]:
                vector = tanh_vector(row["encoded"])
                scores = {symbol: sum(weights[at][SYMBOL_INDEX[symbol]] * vector[at]
                                      for at in range(D_MODEL)) for symbol in row["symbols"]}
                best = max(scores.values())
                pick = sorted(name for name, value in scores.items() if value == best)[0]
                per_row[row["slot_id"]] = pick
                slot_hits[kind][row["field"]]["slots"] += 1
                slot_hits[kind][row["field"]]["hits"] += 1 if pick == row["label"] else 0
                slot_hits[kind]["ALL"]["slots"] += 1
                slot_hits[kind]["ALL"]["hits"] += 1 if pick == row["label"] else 0

            def assemble(selected):
                """The run's own decision record, with `selected` replaced and nothing else."""
                decisions = {**case["decisions"], "selected": dict(selected)}
                return json.dumps(slots.assemble_answer(case["packet"], decisions)["value"], sort_keys=True)

            fitted = dict(per_row)
            for variant in ("fitted",) + tuple(f"fitted + {f} truth" for f in sorted(fields_of[kind])):
                selected = dict(fitted)
                if variant != "fitted":
                    field = variant[len("fitted + "):-len(" truth")]
                    for row in case["rows"]:
                        if row["field"] == field:
                            selected[row["slot_id"]] = row["label"]
                try:
                    ok = assemble(selected) in case["admissible"]
                except Exception:                                     # noqa: BLE001
                    ok = False
                tally[variant][kind]["questions"] += 1
                tally[variant][kind]["correct"] += 1 if ok else 0

    print("=" * 104)
    print("PER-FIELD SLOT ACCURACY OF THE FITTED READOUT (argmax, 5-fold by question)")
    print("=" * 104)
    print()
    for kind in MANY:
        if kind not in slot_hits:
            continue
        for field, row in sorted(slot_hits[kind].items()):
            if row["slots"]:
                print(f"{kind:>14} {field:>14} {row['slots']:6d} slots  {row['hits'] / row['slots']:9.4%}")
        print()

    print("=" * 104)
    print("WHAT EACH FIELD IS WORTH — exact-answer accuracy when that field is given the truth")
    print("=" * 104)
    print()
    variants = [name for name in tally if name == "fitted" or name.startswith("fitted + ")]
    order = {"fitted": 0}
    for name in variants:
        order.setdefault(name, 1)
    for kind in MANY:
        names = sorted((name for name in variants if kind in tally[name]),
                       key=lambda name: (order[name], name))
        if not names:
            continue
        base = tally["fitted"][kind]
        print(f"{kind}  ({base['questions']} questions)")
        for name in names:
            row = tally[name][kind]
            rate = row["correct"] / row["questions"]
            delta = "" if name == "fitted" else f"   {rate - base['correct'] / base['questions']:+9.4%}"
            print(f"   {name:>26}  {rate:9.4%}{delta}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
