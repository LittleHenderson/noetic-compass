"""Does the architecture block neuron-level learning, and does a bilinear binding unblock it?

Pure Python. Standard library plus the project's pure modules. No torch, no device, no learned run
weights, no forward pass of the block, no training, no new run.

The mechanism the owner's question points at
--------------------------------------------
`encoder.py:212` is the whole of the slot encoding:

    result = normalize((entry["vector"] + query) / math.sqrt(2.0))

packet plus slot, **added**. `learner.py:153` then reads it out with `readout_rows[indexes] @ vector`,
which is **linear**. So for a fixed readout row `r`:

    r . encoded  =  ( r.p + r.q ) / norm

and `r.p` is the **same for every slot of the question**. Round 29 measured the consequence on the
frozen readout: `before == name-alone` was **100.0000%** for `edge_account` and `context` -- deleting
the packet changed not one decision.

**Why that blocks learning, precisely.** The loss is computed over slots. The gradient that reaches
the block's response to the packet is therefore the same for every slot: the architecture offers the
neurons **one scalar per question** with which to express everything the packet says, while the answer
needs four to sixteen independent bits. The block has no way to learn "use the packet's content
differently for this slot than for that one", because the representation does not distinguish them.
**That is an architectural block on neuron-level learning, not a training deficiency.**

The change that serves learning
-------------------------------
Add the **Hadamard product**:

    result = normalize((packet + query + packet * query) / sqrt(3.0))

`(p * q)_i = p_i q_i`, so a linear readout can compute `sum_i w_i p_i q_i` -- a **bilinear form**, which
is where conjunctions live. "Is pair X an edge of THIS world's declared set" is exactly such a form,
and under the additive binding it is not expressible at all.

What is measured, and what is not
---------------------------------
**Not** measured: any trained result. There is no run, no fine-tuning and no claim that a run would
improve. This is the encoder's geometry, which is deterministic and specified, so it can be rebuilt and
compared exactly from the frozen bytes -- the same method rounds 29 and 36 used, gated on the published
digests.

**Measured**, per kind, over every slot of one run:

  1. **whether the packet reaches the per-slot decision at all** -- the fraction of slots whose frozen
     readout decision changes when the packet term is deleted. 0.0000% is the additive binding's
     signature; anything above that means the packet is no longer a per-question constant.
  2. **linear decodability of the true symbol** -- ridge LDA, five folds by question, which is the
     ceiling for any linear readout and a proxy for what a gradient could find.
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
from cncm.analytic_decompose import solve  # noqa: E402

RECEIPT = HOME / "records/typed_matched_001/receipt_20260919_m"
SEED = 20260916
D = 64
FOLDS = 5
FROZEN = {
    "projection": "4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9",
    "readout": "14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667",
}
SET_FIELD = {"edge_account": "edge", "parts": "node", "role_set": "role",
             "context": "participant", "definition": "whole"}


def rows_of(raw: bytes, width: int = D) -> list:
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
    return rows_of(binding.projection_bytes(tokenizer, seed=SEED)), rows_of(binding.readout_bytes(seed=SEED))


def packet_vector(packet, tokenizer, projection) -> list:
    plan = binding.compile_packet(packet, tokenizer, seed=SEED)
    ids = [token for row in plan["rows"] for token in row["token_ids"]]
    vectors = []
    for row in plan["rows"]:
        span = ids[row["start"]:row["start"] + row["count"]]
        accumulated = [0.0] * D
        for at, token in enumerate(span):
            order, signs = binding.signed_permutation(seed=SEED, scope=row["scope"],
                                                      ordinal=row["ordinal"], position=at, d_model=D)
            base = projection[token]
            for dest, (origin, sign) in enumerate(zip(order, signs)):
                accumulated[dest] += sign * base[origin]
        vectors.append(unit([value / math.sqrt(row["count"]) for value in accumulated]))
    total = [0.0] * D
    for vector in vectors:
        for index in range(D):
            total[index] += vector[index]
    return unit([value / math.sqrt(len(vectors)) for value in total])


def encode(p, q, variant) -> list:
    if variant == "additive":
        return unit([p[at] + q[at] for at in range(D)])
    if variant == "bilinear":
        return unit([p[at] + q[at] + p[at] * q[at] for at in range(D)])
    if variant == "bilinear_strong":
        return unit([p[at] + q[at] + 4.0 * p[at] * q[at] for at in range(D)])
    raise AssertionError(variant)


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
    if kind in ("context", "definition"):
        if slot["field"] == "whole":
            return node_alias[value["whole"]]
        if slot["field"] == "participant":
            return "PRESENT" if slot["coordinates"][0] in set(value["participants"]) else "ABSENT"
        for world in worlds:
            decl = "setting" if slot["field"] == "setting_ref" else slot["field"].replace("_ref", "")
            if answers.declaration_ref(world["world_id"], decl) == value[slot["field"]]:
                return world["alias"]
    raise AssertionError(kind)


def lda(train, test, width=D) -> float:
    pos = [row for row in train if row[1] == 1]
    neg = [row for row in train if row[1] == 0]
    if not pos or not neg:
        return float("nan")
    mean_p = [sum(r[0][at] for r in pos) / len(pos) for at in range(width)]
    mean_n = [sum(r[0][at] for r in neg) / len(neg) for at in range(width)]
    pooled = [[0.0] * width for _ in range(width)]
    for row in train:
        centre = mean_p if row[1] == 1 else mean_n
        delta = [row[0][at] - centre[at] for at in range(width)]
        for i in range(width):
            for j in range(width):
                pooled[i][j] += delta[i] * delta[j]
    scale = 1.0 / max(1, len(train) - 2)
    for i in range(width):
        for j in range(width):
            pooled[i][j] *= scale
        pooled[i][i] += 1e-3
    direction = solve(pooled, [[mean_p[at] - mean_n[at]] for at in range(width)])
    if direction is None:
        return float("nan")
    w = [direction[at][0] for at in range(width)]
    centre = [(mean_p[at] + mean_n[at]) / 2 for at in range(width)]
    hits = 0
    for features, label in test:
        score = sum(w[at] * (features[at] - centre[at]) for at in range(width))
        hits += 1 if (("PRESENT" if score >= 0 else "ABSENT") == ("PRESENT" if label else "ABSENT")) else 0
    return hits / len(test)


def main() -> int:
    frozen_course, tokenizer, _ = worker_contract.load_material(HOME)
    projection, readout = gate(tokenizer)
    print("FROZEN-BYTE GATE: projection MATCH  readout MATCH", flush=True)
    index = {symbol: at for at, symbol in enumerate(slots.SYMBOLS)}
    d = [readout[index["PRESENT"]][at] - readout[index["ABSENT"]][at] for at in range(D)]
    print()

    predictions = json.loads(
        (RECEIPT / "collected/results/artifacts/final_predictions.json").read_text(encoding="utf-8")
    )["predictions"]

    # kind -> variant -> list of (fold, packet_only_vector, features, label01)
    data = defaultdict(lambda: defaultdict(list))
    for at_q, prediction in enumerate(predictions):
        packet = course.model_packet(frozen_course, prediction["record_id"])
        query = packet["record"]["query"]
        kind = query["kind"]
        if kind not in SET_FIELD:
            continue
        plan = slots.compile_slots(packet)
        validated = slots.validate_plan(packet, plan)
        truth = checker.derive_target(packet["source"], query)["admissible_answers"][0]
        pv = packet_vector(packet, tokenizer, projection)
        for slot in plan["slots"]:
            if slot["field"] != SET_FIELD[kind]:
                continue
            try:
                label = true_symbol(kind, slot, truth["value"], plan)
            except (AssertionError, KeyError):
                continue
            spec = binding._query_spec(validated, slot)
            qv = list(struct.unpack(f"<{D}f", binding.row_bytes(["query", spec], seed=SEED)))
            binary = 1 if label == "PRESENT" else 0
            for variant in ("additive", "bilinear", "bilinear_strong"):
                data[kind][variant].append((at_q % FOLDS, pv, qv, encode(pv, qv, variant), binary))

    print("=" * 104)
    print("1. DOES THE PACKET REACH THE PER-SLOT DECISION? — the round-29 test, on each binding")
    print("=" * 104)
    print()
    print("For each slot: sign(d . encoded(packet, slot)) against sign(d . slot_vector) — that is,")
    print("the frozen readout's decision WITH the packet against the same decision WITHOUT it.")
    print("The column is the fraction of slots where the two AGREE.")
    print()
    print(f"{'kind':>15} {'slots':>7} {'additive':>11} {'bilinear':>11} {'bilinear x4':>13}")
    print("-" * 104)
    for kind in sorted(data):
        cells = {}
        for variant in ("additive", "bilinear", "bilinear_strong"):
            rows = data[kind][variant]
            agree = 0
            for _fold, _pv, qv, features, _label in rows:
                with_packet = sum(d[at] * features[at] for at in range(D))
                without = sum(d[at] * qv[at] for at in range(D))
                agree += 1 if (with_packet >= 0) == (without >= 0) else 0
            cells[variant] = agree / len(rows)
        print(f"{kind:>15} {len(data[kind]['additive']):7d} {cells['additive']:11.4%}"
              f" {cells['bilinear']:11.4%} {cells['bilinear_strong']:13.4%}")
    print()
    print("100.0000% is the additive binding's signature: the packet moves every slot the same way,")
    print("so it can never change one decision relative to another. Round 29 measured exactly that")
    print("at 100.0000% for edge_account and context. A rate below 100% means the packet now enters")
    print("the per-slot decision, which is what the neurons need in order to learn from it.")

    print("=" * 104)
    print("2. LINEAR DECODABILITY OF THE TRUE SYMBOL — ridge LDA, five folds by question")
    print("=" * 104)
    print()
    print(f"{'kind':>15} {'slots':>7} {'additive':>11} {'bilinear':>11} {'bilinear x4':>13} {'chance':>9}")
    print("-" * 104)
    for kind in sorted(data):
        cells = {}
        for variant in ("additive", "bilinear", "bilinear_strong"):
            rows = data[kind][variant]
            scores = []
            for fold in range(FOLDS):
                train = [(r[3], r[4]) for r in rows if r[0] != fold]
                test = [(r[3], r[4]) for r in rows if r[0] == fold]
                if train and test:
                    scores.append(lda(train, test))
            scores = [s for s in scores if not math.isnan(s)]
            cells[variant] = sum(scores) / len(scores) if scores else float("nan")
        present = sum(r[4] for r in data[kind]["additive"]) / len(data[kind]["additive"])
        chance = present * present + (1 - present) * (1 - present)
        print(f"{kind:>15} {len(data[kind]['additive']):7d} {cells['additive']:11.4%}"
              f" {cells['bilinear']:11.4%} {cells['bilinear_strong']:13.4%} {chance:9.4%}")
    print()
    print("chance = p^2 + (1-p)^2 for p = the truth PRESENT rate of that kind's slots.")
    print()
    print("NOT MEASURED: any trained result. This is the encoder's geometry, which is deterministic,")
    print("compared exactly from the checksum-gated frozen bytes. Decodability is the ceiling for a")
    print("linear readout and a proxy for what a gradient could find -- it is not a run's score.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
