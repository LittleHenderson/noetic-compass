"""Where is the conjunction lost: before the block, or inside it?

Pure Python. Standard library plus the project's pure modules (`binding`, `slots`, `course`,
`checker`, `worker_contract`). No torch, no device, no learned weights, no forward pass of the
recurrent block, no training.

The question
------------
Round 27 measured per-bit accuracy for the four binary kinds and found three of them at or below
chance, two of them worse than a constant answer. It attributed that to the binding:

    encoder.py:212   result = normalize((entry["vector"] + query) / math.sqrt(2.0))
    learner.py:153   logits = self.encoder.readout_rows[indexes] @ vector

Packet plus slot, added; then a linear readout. A set-membership slot asks for a conjunction --
this pair AND that world's declared set -- and a linear functional over an additive binding gives a
sum. But round 27 measured *after* the recurrent block, which is nonlinear and could in principle
synthesise the missing product. It did not, but "the trained block failed to learn it" is a
statement about training, not about architecture.

This file computes the same quantity **before the block** -- the frozen encoder's own output, and
the frozen readout's own decision on it. That separates two very different worlds:

  the conjunction is in `encoded` and the block destroys it   -> an initialisation/training problem
  the conjunction is not in `encoded` at all                  -> an encoder-binding problem

Method, and why it can be trusted
---------------------------------
`encoder.encode_slot` is a fixed deterministic transform. Every byte it consumes is produced by
`binding`, which is pure standard library:

    projection = binding.projection_bytes(tokenizer, seed)      # [3829, 64] float32
    readout    = binding.readout_bytes(seed)                    # [90, 64]    float32
    query      = binding.row_bytes(["query", spec], seed)        # [64]        float32
    packet rows = binding.compile_packet(packet, tokenizer, seed)

So the encoder's output can be rebuilt exactly, without torch. **And it can be checked**: the run
published a sha256 for the frozen projection and the frozen readout. This file recomputes those
bytes and refuses to continue unless both hashes match. If they match, the reconstruction is not a
proxy -- it is the encoder.

    identity digest   a00930c51a06adc88ad0194b0439c076a2ddd7096eb8329be5ffc4d4935fc68b
    projection        sha256 4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9
    readout           sha256 14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667
    encoder seed      20260916

Arithmetic is float64 here and float32 in the run. Margins will differ in the last digits; what is
being read is sign and rank, which float32 cannot reorder at these magnitudes.
"""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import struct
import sys
from collections import Counter

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
COMP = HOME / "research" / "CAS_META_2_COMPOSITION"
sys.path.insert(0, str(COMP))
sys.path.insert(0, str(HOME))

from cas_meta2.typed_teaching import binding, checker, course, slots, worker_contract  # noqa: E402

RECEIPTS = HOME / "records/typed_matched_001"
SEED = 20260916
D = 64

FROZEN = {
    "projection": "4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9",
    "readout": "14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667",
}
SHAPES = {"projection": (3829, 64), "readout": (90, 64)}


def floats(raw: bytes) -> list:
    return list(struct.unpack(f"<{len(raw) // 4}f", raw))


def rows_of(raw: bytes, width: int = D) -> list:
    """The byte string as a list of `width`-long float rows, the way `_make_encoder` reshapes it."""
    flat = floats(raw)
    return [flat[at:at + width] for at in range(0, len(flat), width)]


def unit(vector: list) -> list:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0 or not math.isfinite(norm):
        raise AssertionError("zero or non-finite norm")
    return [value / norm for value in vector]


def packet_vector(packet, tokenizer, projection) -> list:
    """`encoder.packet_entry`, lines 154-164, in float64.

    `ids` is the concatenation of every row's token ids (`encoder.py:154`), and each row's `start`
    is an offset into that concatenation -- so the projection rows selected for a row are those for
    its own token ids, not a contiguous slice of the projection.
    """
    plan = binding.compile_packet(packet, tokenizer, seed=SEED)
    ids = [token for row in plan["rows"] for token in row["token_ids"]]
    vectors = []
    for row in plan["rows"]:
        span = ids[row["start"]:row["start"] + row["count"]]
        if len(span) != row["count"]:
            raise AssertionError("row span out of range")
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


def query_vector(validated, slot) -> list:
    spec = binding._query_spec(validated, slot)
    return floats(binding.row_bytes(["query", spec], seed=SEED))


#: kind -> the field whose PRESENT set is the answer; every such slot carries ABSENT/PRESENT.
SET_FIELD = {"edge_account": "edge", "parts": "node", "role_set": "role", "context": "participant"}


def true_symbols(kind: str, plan: dict, answer: dict) -> dict:
    """PRESENT/ABSENT per set-valued slot, read out of the derived answer."""
    value = answer["value"]
    if kind == "edge_account":
        present = {(row["source"], row["target"]) for row in value["edges"]}
    elif kind == "parts":
        present = set(value["nodes"])
    elif kind == "role_set":
        present = set(value["roles"])
    elif kind == "context":
        present = set(value["participants"])
    else:
        raise AssertionError(kind)
    field = SET_FIELD[kind]
    out = {}
    for slot in plan["slots"]:
        if slot["field"] != field:
            continue
        if kind == "edge_account":
            key = (slot["coordinates"][0], slot["coordinates"][1])
        else:
            key = slot["coordinates"][0]
        out[slot["slot_id"]] = "PRESENT" if key in present else "ABSENT"
    return out


def gate(tokenizer) -> tuple:
    """Recompute the frozen bytes and refuse to continue unless they are the published ones."""
    projection_raw = binding.projection_bytes(tokenizer, seed=SEED)
    readout_raw = binding.readout_bytes(seed=SEED)
    report = []
    ok = True
    for name, raw in (("projection", projection_raw), ("readout", readout_raw)):
        got = hashlib.sha256(raw).hexdigest()
        shape = (len(raw) // 4 // D, D)
        good = got == FROZEN[name] and shape == SHAPES[name]
        ok = ok and good
        report.append((name, shape, SHAPES[name], got, FROZEN[name], good))
    return ok, report, rows_of(projection_raw), rows_of(readout_raw)


def main() -> int:
    wanted = [row for row in sys.argv[1:] if not row.startswith("-")]
    frozen_course, tokenizer, _ = worker_contract.load_material(HOME)
    ok, report, projection, readout = gate(tokenizer)

    print("=" * 112)
    print("FROZEN-BYTE GATE — is this reconstruction the encoder, or a proxy?")
    print("=" * 112)
    print()
    for name, shape, want_shape, got, want, good in report:
        print(f"{name:>12}  shape {str(shape):>12} (want {str(want_shape):>12})  "
              f"{'MATCH' if good else 'MISMATCH'}")
        print(f"{'':>12}  sha256 {got}")
        print(f"{'':>12}  wanted {want}")
    print()
    if not ok:
        print("ABORT: the frozen bytes do not reproduce. Nothing below may be read as the encoder.")
        return 1
    print("Both frozen byte strings reproduce exactly. The transform below is the encoder.")
    print()

    index = {symbol: position for position, symbol in enumerate(slots.SYMBOLS)}
    d = [readout[index["PRESENT"]][column] - readout[index["ABSENT"]][column] for column in range(D)]

    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/artifacts/final_predictions.json").is_file()
        and (not wanted or directory.name in wanted)
    )
    print(f"runs: {[row.name for row in receipts]}", flush=True)
    print(flush=True)

    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        predictions = json.loads((artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        scoring = {row["record_id"]: row for row in
                   json.loads((artifacts / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}

        tally = {}
        agreement = {}
        for prediction in predictions:
            record_id = prediction["record_id"]
            kind = scoring[record_id]["kind"]
            if kind not in SET_FIELD:
                continue
            packet = course.model_packet(frozen_course, record_id)
            query = packet["record"]["query"]
            plan = slots.compile_slots(packet)
            validated = slots.validate_plan(packet, plan)
            truth = true_symbols(kind, plan, checker.derive_target(packet["source"], query)["admissible_answers"][0])
            pv = packet_vector(packet, tokenizer, projection)
            recorded = prediction["scores"]

            row = tally.setdefault(kind, Counter())
            seen = agreement.setdefault(kind, Counter())
            row["questions"] += 1
            for slot in plan["slots"]:
                if slot["field"] != SET_FIELD[kind]:
                    continue
                want = truth[slot["slot_id"]]
                qv = query_vector(validated, slot)
                # d . normalize((packet + query)/sqrt(2)); the positive normaliser and the
                # constant 1/sqrt(2) do not change the sign, so the frozen readout's decision on
                # the encoder's own output is sign(d . (packet + query)).
                dot = sum(d[column] * (pv[column] + qv[column]) for column in range(D))
                pick = "PRESENT" if dot >= 0.0 else "ABSENT"
                # the same slot, the same readout, but packet-free: the slot's name alone
                alone = sum(d[column] * qv[column] for column in range(D))
                pick_alone = "PRESENT" if alone >= 0 else "ABSENT"
                # and with no slot term at all: the packet's constant contribution alone
                packet_only = sum(d[column] * pv[column] for column in range(D))
                pick_packet = "PRESENT" if packet_only >= 0 else "ABSENT"
                # what the run actually recorded, after the block
                per_symbol = recorded[slot["slot_id"]]
                pick_recorded = "PRESENT" if per_symbol["PRESENT"] > per_symbol["ABSENT"] else "ABSENT"

                row["bits"] += 1
                row[f"truth_{want}"] += 1
                row["before_hits"] += 1 if pick == want else 0
                row["alone_hits"] += 1 if pick_alone == want else 0
                row["packet_hits"] += 1 if pick_packet == want else 0
                row["recorded_hits"] += 1 if pick_recorded == want else 0
                seen["before_vs_recorded"] += 1 if pick == pick_recorded else 0
                seen["before_vs_alone"] += 1 if pick == pick_alone else 0

        for kind in sorted(tally):
            row, seen = tally[kind], agreement[kind]
            bits = row["bits"]
            present = row["truth_PRESENT"] / bits
            chance = present * present + (1 - present) * (1 - present)
            const = max(row["truth_ABSENT"], row["truth_PRESENT"]) / bits
            print(f"{receipt.name}  {kind:>13}  {row['questions']:3d} q, {bits:5d} slots", flush=True)
            print(f"   chance {chance:8.4%}   best constant {const:8.4%}")
            print(f"   BEFORE block, frozen readout on `encoded`   {row['before_hits'] / bits:9.4%}"
                  f"   ({row['before_hits'] / bits - chance:+7.4%} vs chance)")
            print(f"   slot name alone, no packet term             {row['alone_hits'] / bits:9.4%}")
            print(f"   packet term alone, no slot term             {row['packet_hits'] / bits:9.4%}")
            print(f"   AFTER block, what the run recorded          {row['recorded_hits'] / bits:9.4%}"
                  f"   ({row['recorded_hits'] / bits - const:+7.4%} vs constant)")
            print(f"   before == recorded  {seen['before_vs_recorded'] / bits:9.4%}"
                  f"    before == name-alone  {seen['before_vs_alone'] / bits:9.4%}")
            print(flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
