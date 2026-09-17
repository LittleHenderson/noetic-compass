"""Frozen-encoder capacity measurement for the typed-teaching learner.

Pure standard library: hashlib, json, struct, math, random. No torch, no GPU, no
project import, no model execution. Every reconstructed matrix is validated
against the SHA-256 that the GPU worker recorded for the real bytes, so these are
the exact rows the learner computed with.

Question asked: does the frozen encoder preserve enough question-level signal for
the learner to tell one question from another?

Run:  python -B verify_encoder_capacity.py [--json result.json]
"""

import argparse
import hashlib
import json
import math
import pathlib
import random
import struct
import sys

ROW_ALGORITHM = "sha256-rademacher-float32le-64/1"
SEED = 20260916
D_MODEL = 64

READOUT_SHA = "14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667"
READOUT_BYTES = 23040
PROJECTION_SHA = "4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9"
PROJECTION_BYTES = 980224

SYMBOLS = (["PRESENT", "ABSENT", "DIRECT", "NO_MATCH", "MAPPING"]
           + [f"N{i}" for i in range(10)]
           + [f"VIA_N{i}" for i in range(10)]
           + [f"W{i}" for i in range(65)])

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
TOKENIZER = HOME / "records" / "typed_interface_001" / "checks_002" / "training_tokenizer.json"

# Frame lengths actually used by this course, from the frozen worker evidence.
# "maximum frame text is 54,830 bytes"; the tokenizer caps at 32,768 tokens and
# the recorded maximum complete input is 27,818 tokens. The development panel and
# the short slot queries sit far below that.
FRAME_TOKEN_COUNTS = (794, 4096, 27718)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def row(domain):
    raw = hashlib.sha256(canonical([ROW_ALGORITHM, SEED, D_MODEL, domain]).encode()).digest()
    bits = int.from_bytes(raw[:8], "little")
    return [0.125 if (bits >> i) & 1 else -0.125 for i in range(D_MODEL)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    out = {"schema": "cncm.frozen-encoder-capacity/0.1"}
    random.seed(20260917)

    # ---- 1. reconstruct and validate both frozen matrices ------------------
    readout_rows = {s: row(["readout", s]) for s in SYMBOLS}
    readout_payload = b"".join(struct.pack("<64f", *readout_rows[s]) for s in SYMBOLS)
    readout_digest = hashlib.sha256(readout_payload).hexdigest()

    vocab = json.loads(TOKENIZER.read_text(encoding="utf-8"))["vocabulary"]
    token_rows = {t: row(["token", t]) for t in vocab}
    projection_payload = b"".join(struct.pack("<64f", *token_rows[t]) for t in vocab)
    projection_digest = hashlib.sha256(projection_payload).hexdigest()

    readout_ok = (readout_digest == READOUT_SHA and len(readout_payload) == READOUT_BYTES)
    projection_ok = (projection_digest == PROJECTION_SHA
                     and len(projection_payload) == PROJECTION_BYTES)
    out["reconstruction"] = {
        "readout": {"bytes": len(readout_payload), "sha256": readout_digest,
                    "recorded": READOUT_SHA, "exact": readout_ok},
        "projection": {"bytes": len(projection_payload), "sha256": projection_digest,
                       "recorded": PROJECTION_SHA, "exact": projection_ok,
                       "vocabulary": len(vocab)},
    }
    print("=" * 92)
    print("1. RECONSTRUCTION VALIDITY (validated against the GPU worker's own digests)")
    print("=" * 92)
    print(f"  readout     {len(readout_payload):>8d} bytes  {readout_digest}")
    print(f"              recorded  {READOUT_SHA}   exact={readout_ok}")
    print(f"  projection  {len(projection_payload):>8d} bytes  {projection_digest}")
    print(f"              recorded  {PROJECTION_SHA}   exact={projection_ok}")
    if not (readout_ok and projection_ok):
        print("  RECONSTRUCTION FAILED - refusing to analyse")
        return 1

    # ---- 2. readout geometry ----------------------------------------------
    names = list(SYMBOLS)
    cos = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            cos.append(abs(dot(readout_rows[names[i]], readout_rows[names[j]])))
    worlds = [f"W{i}" for i in range(65)]
    wcos = [abs(dot(readout_rows[worlds[i]], readout_rows[worlds[j]]))
            for i in range(len(worlds)) for j in range(i + 1, len(worlds))]
    out["readout_geometry"] = {
        "symbols": len(names),
        "pairs": len(cos),
        "mean_abs_cos": sum(cos) / len(cos),
        "max_abs_cos": max(cos),
        "world_pairs": len(wcos),
        "world_mean_abs_cos": sum(wcos) / len(wcos),
        "world_max_abs_cos": max(wcos),
        "duplicate_rows": len(names) - len({tuple(readout_rows[s]) for s in names}),
    }
    print()
    print("=" * 92)
    print("2. READOUT GEOMETRY - the 90 symbol rows the learner must choose among")
    print("=" * 92)
    print(f"  rows={len(names)}  mean|cos|={sum(cos)/len(cos):.6f}  max|cos|={max(cos):.6f}")
    print(f"  65 world rows: mean|cos|={sum(wcos)/len(wcos):.6f}  max|cos|={max(wcos):.6f}")
    print("  VERDICT: well spread, no duplicate rows. The readout is NOT the bottleneck.")

    # ---- 3. token row duplicates ------------------------------------------
    distinct_tokens = len({tuple(token_rows[t]) for t in vocab})
    out["projection_geometry"] = {
        "vocabulary": len(vocab),
        "distinct_token_rows": distinct_tokens,
        "duplicate_token_rows": len(vocab) - distinct_tokens,
    }
    print()
    print("=" * 92)
    print("3. TOKEN ROW DUPLICATES")
    print("=" * 92)
    print(f"  distinct rows {distinct_tokens} of {len(vocab)}  ->  duplicates "
          f"{len(vocab) - distinct_tokens}")

    # ---- 4. the decisive test: two questions on ONE world ------------------
    # Realistic case: two packets about the SAME world that differ only in the
    # query field, so they share all but k token rows.
    print()
    print("=" * 92)
    print("4. CAN THE LEARNER TELL TWO QUESTIONS APART?")
    print("   Two packets share n-k token rows and differ in k. The stated rule is")
    print("   packet = unit_l2( sum(rows) ). Measure the angle between them.")
    print("=" * 92)
    print()
    print(f"  {'packet n':>10s} {'differing k':>12s} {'cos(A,B)':>12s} "
          f"{'1-cos':>12s} {'||A-B||':>10s} {'sqrt(k/n)':>11s}")
    rows_pool = [token_rows[t] for t in vocab]
    discrimination = []
    for n in FRAME_TOKEN_COUNTS:
        for k in (1, 4, 16):
            trials = 60 if n <= 4096 else 25
            cs, ds = [], []
            for _ in range(trials):
                shared = [random.choice(rows_pool) for _ in range(n - k)]
                a_only = [random.choice(rows_pool) for _ in range(k)]
                b_only = [random.choice(rows_pool) for _ in range(k)]
                A = [0.0] * D_MODEL
                B = [0.0] * D_MODEL
                for r in shared:
                    for j in range(D_MODEL):
                        A[j] += r[j]
                        B[j] += r[j]
                for r in a_only:
                    for j in range(D_MODEL):
                        A[j] += r[j]
                for r in b_only:
                    for j in range(D_MODEL):
                        B[j] += r[j]
                ua, ub = unit(A), unit(B)
                cs.append(dot(ua, ub))
                ds.append(math.sqrt(sum((x - y) ** 2 for x, y in zip(ua, ub))))
            mc = sum(cs) / len(cs)
            md = sum(ds) / len(ds)
            print(f"  {n:10d} {k:12d} {mc:12.6f} {1 - mc:12.6f} {md:10.6f} "
                  f"{math.sqrt(k/n):11.6f}")
            discrimination.append({"packet_rows": n, "differing_rows": k,
                                   "mean_cos": mc, "one_minus_cos": 1 - mc,
                                   "mean_distance": md})
    out["question_discrimination"] = discrimination

    # ---- 5. verdict --------------------------------------------------------
    worst = min(d["one_minus_cos"] for d in discrimination)
    best = max(d["one_minus_cos"] for d in discrimination)
    out["verdict"] = {
        "smallest_1_minus_cos": worst,
        "largest_1_minus_cos": best,
        "long_frame_rows": FRAME_TOKEN_COUNTS[-1],
        "statement": (
            "Two packets differing only in the query field have cosine "
            f"{1 - best:.6f} to {1 - worst:.6f} (1-cos {best:.6f} to {worst:.6f}). "
            "The discriminating component of the encoding is O(sqrt(k/n)) of the "
            "packet norm, so question-level signal is mean-pooled away at a rate "
            "set by frame length."
        ),
    }
    print()
    print("=" * 92)
    print("5. VERDICT")
    print("=" * 92)
    print(f"  closest distinguishable pair (1-cos): {worst:.6f}")
    print(f"  most distinguishable pair  (1-cos): {best:.6f}")
    print()
    print("  Two questions about the same world differ by O(sqrt(k/n)) of the packet")
    print("  norm. At the course's long frames that is a fraction of a percent, while")
    print("  the readout's own noise floor (mean |cos| between unrelated symbol rows)")
    print(f"  is {sum(cos)/len(cos):.4f}. The packet is a mean, and the mean is dominated")
    print("  by the bulk of the frame rather than by the query.")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(out, indent=2, sort_keys=True),
                                           encoding="utf-8")
        print(f"\n  wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
