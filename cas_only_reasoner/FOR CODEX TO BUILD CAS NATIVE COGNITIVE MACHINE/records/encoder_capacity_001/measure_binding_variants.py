"""Would re-naming a pair-valued slot as the pair itself make the bits readable?

Pure Python. Standard library plus the project's pure modules. No torch, no device, no learned
weights, no forward pass of the recurrent block, no training, no run.

The proposal under test
-----------------------
`edge_account` slots carry `coordinates = [ref_a, ref_b]` -- the two ends of a directed pair.
`binding._query_spec` turns that into `coordinates = [W15/N0, W15/N1]`, and `row_bytes` binds the
token sequence. So the slot's name states the pair as **two separate things**.

The proposal is to name the pair as **one thing** -- a single coordinate string identifying the
pair -- on the theory that a relation between two positions in a token sequence is harder to bind
than a single token.

Why this file exists rather than a run
--------------------------------------
`context` participants also carry a single node ref per slot, exactly like `parts`, and `context`
fails at 39.7004% against a 78.6517% constant while `parts` succeeds at 73.9130% against a 57.9710%
constant. So arity does **not** separate success from failure, and the proposal is on weak ground.
Before spending a GPU run on it, this file asks the cheap question: does the re-naming change the
geometry at all?

What is measured, per kind and per naming variant
-------------------------------------------------
The frozen encoder is rebuilt exactly and gated on the two published sha256s, so `q` (the slot
vector) and `p` (the packet vector) below are the encoder's own numbers, not an approximation.

For each variant, two questions, both cross-validated by holding out whole questions:

  1. **Is the label linearly decodable?** Ridge-regularised LDA on the slot vector. This is the
     ceiling for a linear readout -- a probe, not the block.
  2. **Is the label memorisable?** A pure lookup keyed on (scope alias, coordinates), trained on the
     other folds. The evaluation reuses the same 64 worlds, so a lookup that has seen a
     (world, pair) key should answer it perfectly. This bounds what "learning the table" would buy.

If the memoriser scores near 100% and the block sits at 53.5471%, the deficit is not geometry at
all -- it is that the block never built the table. If the memoriser also fails, the name does not
determine the answer and no readout of any kind can succeed.
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

from cas_meta2.typed_teaching import binding, checker, course, slots, worker_contract  # noqa: E402
from cncm.analytic_decompose import solve  # noqa: E402

RECEIPT = HOME / "records/typed_matched_001/receipt_20260919_m"
SEED = 20260916
D = 64
FOLDS = 5

FROZEN = {
    "projection": ("4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9", (3829, 64)),
    "readout": ("14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667", (90, 64)),
}
SET_FIELD = {"edge_account": "edge", "parts": "node", "role_set": "role", "context": "participant"}


def rows_of(raw: bytes, width: int = D) -> list:
    flat = list(struct.unpack(f"<{len(raw) // 4}f", raw))
    return [flat[at:at + width] for at in range(0, len(flat), width)]


def unit(vector: list) -> list:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0 or not math.isfinite(norm):
        raise AssertionError("zero or non-finite norm")
    return [value / norm for value in vector]


def gate(tokenizer):
    report, ok, out = [], True, {}
    for name in ("projection", "readout"):
        raw = (binding.projection_bytes(tokenizer, seed=SEED) if name == "projection"
               else binding.readout_bytes(seed=SEED))
        got = hashlib.sha256(raw).hexdigest()
        want, shape = FROZEN[name]
        good = got == want and (len(raw) // 4 // D, D) == shape
        ok = ok and good
        report.append((name, got == want))
        out[name] = rows_of(raw)
    return ok, report, out["projection"], out["readout"]


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


def rename(spec: dict, variant: str) -> dict:
    """The slot spec under a naming variant, leaving `_query_spec`'s own output as variant `real`."""
    if variant == "real":
        return spec
    coordinates = list(spec["coordinates"])
    if variant == "pair_token":
        if len(coordinates) != 2:
            return spec
        return {**spec, "coordinates": [f"{coordinates[0]}->{coordinates[1]}"]}
    if variant == "pair_token_sorted":
        if len(coordinates) != 2:
            return spec
        left, right = sorted(coordinates)
        return {**spec, "coordinates": [f"{left}->{right}"]}
    if variant == "swapped":
        if len(coordinates) != 2:
            return spec
        return {**spec, "coordinates": [coordinates[1], coordinates[0]]}
    raise AssertionError(variant)


VARIANTS = ("real", "pair_token", "pair_token_sorted", "swapped")


def vector_for(validated, slot, variant) -> list:
    spec = rename(binding._query_spec(validated, slot), variant)
    raw = binding.row_bytes(["query", spec], seed=SEED)
    return list(struct.unpack(f"<{D}f", raw))


def lda_probe(train, test) -> float:
    """Ridge LDA fitted on `train`, scored on `test`. Returns accuracy, or NaN if undecidable."""
    present = [row for row in train if row[1] == "PRESENT"]
    absent = [row for row in train if row[1] == "ABSENT"]
    if not present or not absent:
        return float("nan")
    mean_p = [sum(row[0][at] for row in present) / len(present) for at in range(D)]
    mean_a = [sum(row[0][at] for row in absent) / len(absent) for at in range(D)]
    pooled = [[0.0] * D for _ in range(D)]
    for row in train:
        centre = mean_p if row[1] == "PRESENT" else mean_a
        delta = [row[0][at] - centre[at] for at in range(D)]
        for i in range(D):
            for j in range(D):
                pooled[i][j] += delta[i] * delta[j]
    scale = 1.0 / max(1, len(train) - 2)
    ridge = 1e-3
    for i in range(D):
        for j in range(D):
            pooled[i][j] *= scale
        pooled[i][i] += ridge
    direction = solve(pooled, [[mean_p[at] - mean_a[at]] for at in range(D)])
    if direction is None:
        return float("nan")
    weights = [direction[at][0] for at in range(D)]
    centre = [(mean_p[at] + mean_a[at]) / 2 for at in range(D)]
    hits = 0
    for features, label in test:
        score = sum(weights[at] * (features[at] - centre[at]) for at in range(D))
        hits += 1 if (("PRESENT" if score >= 0 else "ABSENT") == label) else 0
    return hits / len(test)


def main() -> int:
    frozen_course, tokenizer, _ = worker_contract.load_material(HOME)
    ok, report, projection, readout = gate(tokenizer)
    print("FROZEN-BYTE GATE: " + "  ".join(f"{name} {'MATCH' if good else 'MISMATCH'}"
                                           for name, good in report), flush=True)
    if not ok:
        print("ABORT: frozen bytes do not reproduce; nothing below may be read as the encoder.")
        return 1
    print()

    predictions = json.loads(
        (RECEIPT / "collected/results/artifacts/final_predictions.json").read_text(encoding="utf-8")
    )["predictions"]
    scoring = {row["record_id"]: row for row in json.loads(
        (RECEIPT / "collected/results/artifacts/final_scoring.json").read_text(encoding="utf-8"))["rows"]}

    # rows[kind][variant] -> list of (question_index, key, features, label)
    rows = defaultdict(lambda: defaultdict(list))
    recorded = defaultdict(lambda: [0, 0])
    for index, prediction in enumerate(predictions):
        record_id = prediction["record_id"]
        kind = scoring[record_id]["kind"]
        if kind not in SET_FIELD:
            continue
        packet = course.model_packet(frozen_course, record_id)
        query = packet["record"]["query"]
        plan = slots.compile_slots(packet)
        validated = slots.validate_plan(packet, plan)
        truth = checker.derive_target(packet["source"], query)["admissible_answers"][0]["value"]
        pv = packet_vector(packet, tokenizer, projection)

        if kind == "edge_account":
            labels = {tuple(sorted((row["source"], row["target"]))) for row in truth["edges"]}
        elif kind == "parts":
            labels = set(truth["nodes"])
        elif kind == "role_set":
            labels = set(truth["roles"])
        else:
            labels = set(truth["participants"])

        for slot in plan["slots"]:
            if slot["field"] != SET_FIELD[kind]:
                continue
            if kind == "edge_account":
                key = tuple(sorted((slot["coordinates"][0], slot["coordinates"][1])))
            else:
                key = slot["coordinates"][0]
            label = "PRESENT" if key in labels else "ABSENT"
            recorded[kind][0] += 1
            recorded[kind][1] += 1 if (prediction["scores"][slot["slot_id"]]["PRESENT"]
                                       > prediction["scores"][slot["slot_id"]]["ABSENT"]) == (label == "PRESENT") else 0
            for variant in VARIANTS:
                qv = vector_for(validated, slot, variant)
                # `encoded` direction: packet plus slot, the quantity the block is handed
                encoded = unit([pv[at] + qv[at] for at in range(D)])
                scope = slot["scope_alias"]
                rows[kind][variant].append((index % FOLDS, (scope, spec_key(slot, kind)), qv, encoded, label))

    print("=" * 112)
    print("IS THE LABEL LINEARLY DECODABLE, AND IS IT MEMORISABLE? 5-fold by question")
    print("=" * 112)
    print()
    print(f"{'kind':>14} {'variant':>18} {'slots':>6} {'q: LDA':>9} {'enc: LDA':>10}"
          f" {'q: lookup':>11} {'enc: lookup':>13} {'block':>8}")
    print("-" * 112)
    for kind in ("edge_account", "parts", "context", "role_set"):
        for variant in VARIANTS:
            data = rows[kind][variant]
            if not data:
                continue
            q_lda, e_lda, q_look, e_look = [], [], [], []
            for fold in range(FOLDS):
                train = [row for row in data if row[0] != fold]
                test = [row for row in data if row[0] == fold]
                if not test:
                    continue
                q_lda.append(lda_probe([(row[2], row[4]) for row in train],
                                       [(row[2], row[4]) for row in test]))
                e_lda.append(lda_probe([(row[3], row[4]) for row in train],
                                       [(row[3], row[4]) for row in test]))
                q_look.append(lookup([(row[1], row[4]) for row in train], [(row[1], row[4]) for row in test]))
                e_look.append(q_look[-1])
            bits = recorded[kind][1] / recorded[kind][0]
            print(f"{kind:>14} {variant:>18} {len(data):6d} {mean(q_lda):9.4%} {mean(e_lda):10.4%}"
                  f" {mean(q_look):11.4%} {mean(e_look):13.4%} {bits:8.4%}")
        print()
    print("q   = the slot vector alone (`binding.row_bytes` of the slot's query spec)")
    print("enc = the encoder's own output, normalize(packet + slot), which is what the block is handed")
    print("lookup = majority label per (scope alias, coordinates) key seen in the training folds,")
    print("         falling back to the training majority when the key is unseen")
    print("block = the recorded per-bit accuracy of the trained machine, for reference")
    return 0


def spec_key(slot, kind):
    if kind == "edge_account":
        return tuple(sorted((slot["coordinates"][0], slot["coordinates"][1])))
    return slot["coordinates"][0]


def lookup(train, test) -> float:
    table = defaultdict(Counter)
    overall = Counter()
    for key, label in train:
        table[key][label] += 1
        overall[label] += 1
    fallback = overall.most_common(1)[0][0] if overall else "ABSENT"
    hits = 0
    for key, label in test:
        guess = table[key].most_common(1)[0][0] if key in table else fallback
        hits += 1 if guess == label else 0
    return hits / len(test)


def mean(values):
    present = [value for value in values if not math.isnan(value)]
    return sum(present) / len(present) if present else float("nan")


if __name__ == "__main__":
    raise SystemExit(main())
