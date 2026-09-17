"""Ablate the real packet by scope family to find where the question signal lives.

Pure Python, project's pure modules only, no torch, no GPU.
"""

import math
import pathlib
import sys

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
COMP = HOME / "research" / "CAS_META_2_COMPOSITION"
sys.path.insert(0, str(COMP))
sys.path.insert(0, str(HOME))

from cas_meta2.typed_teaching import binding, course, worker_contract  # noqa: E402

SEED = 20260916
D = 64
FLOOR = 0.098408


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def main():
    frozen, tokenizer, _ = worker_contract.load_material(HOME)
    base = {i: binding.row_bytes(["token", v], seed=SEED, d_model=D)
            for i, v in enumerate(tokenizer.vocabulary)}

    def build(packet):
        rows = binding.compile_packet(packet, tokenizer, seed=SEED, d_model=D)["rows"]
        out = []
        for row in rows:
            rv = [0.0] * D
            for position, token in enumerate(row["token_ids"]):
                order, signs = binding.signed_permutation(
                    seed=SEED, scope=row["scope"], ordinal=row["ordinal"],
                    position=position, d_model=D)
                b = base[token]
                for dest, (origin, sign) in enumerate(zip(order, signs)):
                    rv[dest] += sign * b[origin]
            out.append((tuple(row["scope"]), row["count"], unit(rv)))
        return out

    def alias_of(packet):
        frame = binding.input_frames.compile_packet(packet)
        fw = packet["record"]["query"]["focus_world_id"]
        for row in frame["aliases"]:
            if row["world_id"] == fw:
                return row["alias"]
        return None

    registry = frozen["registry"]
    by = {}
    for row in registry:
        by.setdefault((row["source_world_id"], row["query"]["kind"]), []).append(row)
    worlds = {}
    for (w, k), rows in by.items():
        if len(rows) >= 2:
            worlds.setdefault(w, set()).add(k)
    chosen = [w for w, ks in worlds.items() if len(ks) >= 3][:5]

    def variant_vector(rvs, alias, keep):
        sel = [v for s, c, v in rvs if keep(s, alias)]
        return unit([sum(x) for x in zip(*sel)]) if sel else None

    variants = {
        "all 76 rows": lambda s, a: True,
        "no other 63 worlds": lambda s, a: not (s[0] == "WORLD" and len(s) > 1 and s[1] != a),
        "query+record+support": lambda s, a: s[0] in {"QUERY", "RECORD", "SUPPORT"},
        "focus world row only": lambda s, a: s[0] == "WORLD" and len(s) > 1 and s[1] == a,
        "focus+query+support (proposed)": lambda s, a: (
            s[0] in {"START", "FORMAT", "BINDINGS", "POLICY", "SOURCE", "RECORD", "QUERY", "SUPPORT", "END"}
            or (s[0] == "WORLD" and len(s) > 1 and s[1] == a)),
    }

    acc = {name: {"same": [], "cross": []} for name in variants}
    for w in chosen:
        kinds = sorted(worlds[w])
        items = []
        for k in kinds:
            for r in by[(w, k)][:2]:
                p = course.model_packet(frozen, r["record_id"])
                rvs = build(p)
                a = alias_of(p)
                items.append((k, {name: variant_vector(rvs, a, fn) for name, fn in variants.items()}))
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                bucket = "same" if items[i][0] == items[j][0] else "cross"
                for name in variants:
                    va, vb = items[i][1][name], items[j][1][name]
                    if va and vb:
                        acc[name][bucket].append(1 - dot(va, vb))

    print("=" * 100)
    print("REAL-PACKET ABLATION: mean 1-cos between two questions about the SAME world")
    print(f"readout cross-talk floor = {FLOOR:.6f}   (measured mean |cos| between unrelated symbol rows)")
    print("=" * 100)
    print()
    print(f"  {'variant':32s} {'same kind':>22s} {'different kind':>22s}")
    print("  " + "-" * 80)
    for name in variants:
        row = f"  {name:32s}"
        for bucket in ("same", "cross"):
            vals = acc[name][bucket]
            if not vals:
                row += f"{'n/a':>22s}"
            else:
                m = sum(vals) / len(vals)
                mark = "OK" if m >= FLOOR else f"{FLOOR/m:.0f}x low"
                row += f"{m:>13.9f} {mark:>8s}"
        print(row)
    print()
    print("  'OK' means the question signal at least matches the readout's own")
    print("  cross-talk; anything below needs the model to resolve a difference")
    print("  smaller than the interference between unrelated answers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
