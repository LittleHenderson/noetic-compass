"""Weight-only bound on the per-round step size. NOT a forward pass: reads merge.weight numbers only.

core_block(v) = merge @ cat(tanh(left v), tanh(right v))   (pointer_learner.py:825-831, no bias)
Each tanh output is in [-1, 1], so |u_i| <= L1(row i of merge). Hidden rows have RMS 1 (_rms_unit, :913-935).
Bound on RMS(g*u)/RMS(h) per round:  |g| * sqrt(mean_i L1_i^2).
'Typical' (NOT a bound; assumes independent +-1 tanh signs): |g| * ||merge||_F / sqrt(64).
"""
import io, sys, zipfile, struct, math
sys.path.insert(0, ".")
import rt3_read_round_rate as R

def mat(zf, prefix, t):
    raw = zf.read(prefix + "data/" + t.storage.key)
    rows, cols = t.size
    assert t.stride == (cols, 1), t.stride
    flat = struct.unpack_from("<%df" % (rows * cols), raw, 4 * t.offset)
    return [flat[r * cols:(r + 1) * cols] for r in range(rows)]

for version, seed, rdir in R.RUNS:
    for fname in ("initial.pt", "final.pt"):
        zf = zipfile.ZipFile("%s/%s/checkpoints/%s" % (R.REC, rdir, fname))
        pkl = [n for n in zf.namelist() if n.endswith("data.pkl")][0]; prefix = pkl[:-len("data.pkl")]
        obj = R.StubUnpickler(io.BytesIO(zf.read(pkl))).load(); ms = obj["model_state"]
        M = mat(zf, prefix, ms["merge.weight"])
        rr = struct.unpack_from("<f", zf.read(prefix + "data/" + ms["round_rate"].storage.key), 0)[0]
        g = 0.01 * math.tanh(rr)
        l1 = [sum(abs(x) for x in row) for row in M]
        bound_rms_u = math.sqrt(sum(v * v for v in l1) / len(l1))
        fro = math.sqrt(sum(x * x for row in M for x in row))
        typ_rms_u = fro / math.sqrt(len(M))
        print("%s %s %-10s merge shape %dx%d  ||merge||_F=%r  bound RMS(u)<=%r  typical RMS(u)~%r  g=%r  step bound=%r  step typical~%r"
              % (version, seed, fname, len(M), len(M[0]), fro, bound_rms_u, typ_rms_u, g, abs(g) * bound_rms_u, abs(g) * typ_rms_u))
