"""The bridge that was never measured: does a FITTED readout convert into score?

Pure Python. Standard library plus the project's pure modules. No torch, no device, no learned
weights of the run, no forward pass of the recurrent block, no training, no new run.

The gap this closes
-------------------
Round 29 measured, per bit, that a fitted linear readout of the block's own input reads the
many-decision kinds far better than the trained block does:

    kind           q: LDA      enc: LDA    block       best constant
    edge_account   62.3033%    62.9181%    53.5471%    59.5724%
    parts          87.1525%    86.6700%    70.5314%    57.9710%
    context        96.3758%    94.2490%    40.8240%    78.6517%
    role_set       60.6376%    60.4577%    69.4444%    80.5556%

and separately that a *memoriser* converts into **-6.7033 points** at the answer level. Those two
results point opposite ways, and they are not the same readout: the memoriser keys on the slot's
name, while the probe is a fitted linear map of the encoder's output — which is exactly what
`cncm/analytic_decompose.py::decompose_from_free_readout` installs. `T = R⁻¹Wᵀ` makes the frozen
readout behave as a chosen free readout `W`, so the score for symbol `c` becomes `W[:,c]·tanh(x)`.

**So the answer-level worth of a fitted readout has never been measured.** This file measures it.

Method
------
Build the encoder's own output exactly (the frozen bytes are checksum-gated), then for every slot of
every non-correspondence question form

    encoded = normalize(packet + slot)          the vector the block is handed
    features = tanh(encoded)                    the vector Fix A's block would pass through

fit `W = (XᵀX + lam I)⁻¹ Xᵀ Y` with one-hot `Y` over the true symbol of each slot, predict by
`argmax_c W[:,c]·feature`, and hand the resulting score table to the project's **own**
`slots.score_decisions` and `slots.assemble_answer`. So the decision path after the readout is the
run's own, and only the readout is substituted.

Five folds by question. The truth is derived by the project's own `checker.derive_target` from the
public snapshot and never enters the fit.

What the number means
---------------------
This is the ceiling for the construction the project already has. If it does not beat the recorded
score, then extending `decompose_from_free_readout` to a rectangular readout buys nothing, and the
remaining lever is the encoder's binding rather than the block's readout. If it does beat it, the
size of the gap is the measured target for a GPU run.
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
LAMBDAS = (1.0, 0.01)
FROZEN = {
    "projection": "4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9",
    "readout": "14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667",
}
SYMBOL_INDEX = {symbol: index for index, symbol in enumerate(slots.SYMBOLS)}
MANY = ("edge_account", "role_set", "parts", "context", "definition")


def rows_of(raw: bytes, width: int = D_MODEL) -> list:
    flat = list(struct.unpack(f"<{len(raw) // 4}f", raw))
    return [flat[at:at + width] for at in range(0, len(flat), width)]


def unit(vector: list) -> list:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0 or not math.isfinite(norm):
        raise AssertionError("zero or non-finite norm")
    return [value / norm for value in vector]


def gate(tokenizer) -> tuple:
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


def true_symbol(kind, slot, value, packet, plan) -> str:
    """The true symbol of one slot, by inverting `slots.assemble_answer` kind by kind."""
    worlds = plan["aliases"]["worlds"]
    node_alias = {node["ref"]: node["alias"] for world in worlds for node in world["nodes"]}
    world_alias = {world["world_id"]: world["alias"] for world in worlds}
    if kind == "edge_account":
        present = {(row["source"], row["target"]) for row in value["edges"]}
        key = (slot["coordinates"][0], slot["coordinates"][1])
        return "PRESENT" if key in present else "ABSENT"
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
    if kind == "analogy":
        return "NO_MATCH" if value["world_id"] is None else world_alias[value["world_id"]]
    if kind == "reach":
        if value["state"] == "VIA":
            return "VIA_" + node_alias[value["via"]]
        return value["state"]
    raise AssertionError(kind)


def correspondence_labels(plan, value, world_alias=None) -> dict:
    """Per-slot symbols for a correspondence question, from one admissible answer.

    `correspondence` is decided by the joint candidate decoder over `correspondence` group slots,
    so its slots must be in the fit or the decoder has nothing calibrated to work with. A NO_MATCH
    answer carries no pairs, so only the mode slot gets a label there; leaving the target slots out
    is honest, inventing one is not.
    """
    alias = {node["ref"]: node["alias"] for world in plan["aliases"]["worlds"] for node in world["nodes"]}
    out = {}
    mode_slot = plan["slots"][0]
    if value["status"] == "NO_MATCH":
        out[mode_slot["slot_id"]] = "NO_MATCH"
        return out
    out[mode_slot["slot_id"]] = "MAPPING"
    by_source = {pair["source"]: pair["target"] for pair in value["pairs"]}
    for slot in plan["slots"][1:]:
        source = slot["coordinates"][0]
        if source in by_source:
            out[slot["slot_id"]] = alias[by_source[source]]
    return out


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
        plan = slots.compile_slots(packet)
        validated = slots.validate_plan(packet, plan)
        target = checker.derive_target(packet["source"], query)
        truth = target["admissible_answers"][0]
        # `analogy` and `correspondence` admit 6-9 and 1-6 answers per question respectively, so
        # correctness is MEMBERSHIP of the whole admissible set, never equality with its first
        # element. Equality with `[0]` reports `analogy` at 0.00% when it scores 10%-22.86%.
        admissible = frozenset(json.dumps(row["value"], sort_keys=True)
                               for row in target["admissible_answers"])
        pv = packet_vector(packet, tokenizer, projection)
        extra = (correspondence_labels(plan, truth["value"]) if plan["kind"] == "correspondence"
                 else {})
        rows = []
        for slot in plan["slots"]:
            spec = binding._query_spec(validated, slot)
            qv = list(struct.unpack(f"<{D_MODEL}f", binding.row_bytes(["query", spec], seed=SEED)))
            label = (extra.get(slot["slot_id"]) if plan["kind"] == "correspondence"
                     else true_symbol(plan["kind"], slot, truth["value"], packet, plan))
            rows.append({"slot_id": slot["slot_id"], "symbols": list(slot["symbols"]),
                         "encoded": unit([pv[at] + qv[at] for at in range(D_MODEL)]),
                         "label": label})
        cases.append({"fold": index % FOLDS, "kind": plan["kind"], "packet": packet, "plan": plan,
                      "truth": truth["value"], "admissible": admissible, "truth_key": json.dumps(truth["value"], sort_keys=True),
                      "recorded": prediction["decisions"],
                      "recorded_value": prediction["answer"]["value"], "rows": rows})
    labelled = sum(1 for case in cases for row in case["rows"] if row["label"] is not None)
    print(f"questions: {len(cases)}   labelled slots: {labelled}", flush=True)
    print(f"admissible-set sizes: "
          f"{dict(sorted(Counter(len(case['admissible']) for case in cases).items()))}", flush=True)
    print()

    print("=" * 104)
    print("EXACT-ANSWER ACCURACY OF A FITTED LINEAR READOUT, 5-fold by question")
    print("=" * 104)
    print()
    print(f"{'readout':>26} {'lam':>8} {'edge_acc':>9} {'parts':>8} {'role_set':>9} {'context':>9}"
          f" {'definition':>11} {'MANY':>8} {'ALL':>8}")
    print("-" * 104)

    summary = {}
    for label, transform, lam in ([("frozen (recorded)", None, None)]
                                  + [("fitted on tanh(x)", tanh_vector, value) for value in LAMBDAS]
                                  + [("fitted on x", None, value) for value in LAMBDAS]):
        per_kind = defaultdict(Counter)
        for fold in range(FOLDS):
            train = ([(tanh_vector(row["encoded"]) if transform is not None else row["encoded"],
                       SYMBOL_INDEX[row["label"]])
                      for case in cases if case["fold"] != fold
                      for row in case["rows"] if row["label"] is not None]
                     if lam is not None else None)
            weights = (ridge_weights([row for row, _ in train], [target for _, target in train],
                                     nclass=len(slots.SYMBOLS), lam=lam) if train else None)

            for case in cases:
                if case["fold"] != fold:
                    continue
                kind = case["kind"]
                per_kind[kind]["questions"] += 1
                recorded_ok = (json.dumps(case["recorded_value"], sort_keys=True)
                               in case["admissible"])
                per_kind[kind]["recorded"] += 1 if recorded_ok else 0
                if weights is None:
                    per_kind[kind]["fitted"] += 1 if recorded_ok else 0
                    continue
                table = {}
                for row in case["rows"]:
                    vector = tanh_vector(row["encoded"]) if transform is not None else row["encoded"]
                    table[row["slot_id"]] = {
                        symbol: sum(weights[at][SYMBOL_INDEX[symbol]] * vector[at]
                                    for at in range(D_MODEL)) for symbol in row["symbols"]}
                try:
                    decisions = slots.score_decisions(case["packet"], table)
                    assembled = slots.assemble_answer(case["packet"], decisions)
                except Exception:                                     # noqa: BLE001
                    continue
                per_kind[kind]["fitted"] += 1 if (json.dumps(assembled["value"], sort_keys=True)
                                                  in case["admissible"]) else 0

        cells = {}
        for kind, row in per_kind.items():
            cells[kind] = row["fitted"] / row["questions"]
        many_q = sum(per_kind[kind]["questions"] for kind in MANY if kind in per_kind)
        many_hit = sum(per_kind[kind]["fitted"] for kind in MANY if kind in per_kind)
        all_q = sum(row["questions"] for row in per_kind.values())
        all_hit = sum(row["fitted"] for row in per_kind.values())
        summary[(label, lam)] = (many_hit / many_q, all_hit / all_q, cells)
        print(f"{label:>26} {str(lam):>8}"
              f" {cells.get('edge_account', float('nan')):9.4%} {cells.get('parts', float('nan')):8.4%}"
              f" {cells.get('role_set', float('nan')):9.4%} {cells.get('context', float('nan')):9.4%}"
              f" {cells.get('definition', float('nan')):11.4%}"
              f" {many_hit / many_q:8.4%} {all_hit / all_q:8.4%}")

    print()
    print("=" * 104)
    print("THE ANSWER TO THE QUESTION THIS FILE EXISTS FOR")
    print("=" * 104)
    print()
    base_many, base_all, _ = summary[("frozen (recorded)", None)]
    best = max(((key, value) for key, value in summary.items() if key[1] is not None),
               key=lambda item: item[1][1])
    print(f"recorded MANY DECISIONS   {base_many:9.4%}      recorded ALL   {base_all:9.4%}")
    print(f"best fitted readout       {best[1][0]:9.4%}      best ALL       {best[1][1]:9.4%}"
          f"   ({best[0][0]}, lam={best[0][1]})")
    print(f"lift on MANY DECISIONS    {best[1][0] - base_many:+9.4%}")
    print(f"lift on ALL               {best[1][1] - base_all:+9.4%}")
    print()
    print("The decision path after the readout is the run's own: `slots.score_decisions` then")
    print("`slots.assemble_answer`. Only the readout is substituted, by the construction")
    print("`decompose_from_free_readout` installs. A lift here is the measured target for a run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
