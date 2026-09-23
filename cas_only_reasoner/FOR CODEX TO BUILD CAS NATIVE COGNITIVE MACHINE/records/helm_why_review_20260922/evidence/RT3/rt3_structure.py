"""Inspect model_state key order, optimizer param_groups and AdamW state of round_rate/round_mix. No torch."""
import io, json, sys, zipfile, struct, math
sys.path.insert(0, ".")
import rt3_read_round_rate as R

def load(path):
    zf = zipfile.ZipFile(path)
    pkl = [n for n in zf.namelist() if n.endswith("data.pkl")][0]
    prefix = pkl[:-len("data.pkl")]
    obj = R.StubUnpickler(io.BytesIO(zf.read(pkl))).load()
    return zf, prefix, obj

def vals(zf, prefix, t):
    raw = zf.read(prefix + "data/" + t.storage.key)
    n = t.storage.numel
    return list(struct.unpack("<%df" % n, raw[:4*n]))

for version, seed, rdir in R.RUNS:
    path = "%s/%s/checkpoints/final.pt" % (R.REC, rdir)
    zf, prefix, obj = load(path)
    ms = obj["model_state"]
    keys = list(ms.keys())
    print("==", version, seed, "model_state n=%d" % len(keys))
    print("   schema:", obj["schema"])
    md = obj["metadata"]
    print("   metadata keys:", list(md.keys()) if isinstance(md, dict) else type(md))
    if version == "helm1.0" and seed == "20260917":
        for i, k in enumerate(keys):
            print("     %2d %s %s" % (i, k, ms[k].size))
    os_ = obj["optimizer_state"]
    pg = os_["param_groups"]
    for g in pg:
        print("   param_group:", {k: v for k, v in g.items() if k != "params"}, "n_params", len(g["params"]))
    st = os_["state"]
    for name in ("round_mix", "round_rate"):
        idx = keys.index(name)
        pid = pg[0]["params"][idx]
        s = st.get(pid)
        if s is None:
            print("   ", name, "no optimizer state at id", pid); continue
        out = {}
        for k, v in s.items():
            out[k] = [repr(x) for x in vals(zf, prefix, v)] if isinstance(v, R.StubTensor) else repr(v)
        print("   ", name, "index", idx, "param id", pid, out)
