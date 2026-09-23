"""AdamW state of round_rate / round_mix in each final.pt, offset-aware. No torch.

The optimizer is built from list(module.parameters()) (pointer_learner.py:1781 in 2.0, :1578 in 1.0), so
param id i should follow parameters() order. We CHECK which name order matches every exp_avg shape
before using it (state_dict key order vs metadata learnable_names order)."""
import io, sys, zipfile, struct, math
sys.path.insert(0, ".")
import rt3_read_round_rate as R

def load(path):
    zf = zipfile.ZipFile(path)
    pkl = [n for n in zf.namelist() if n.endswith("data.pkl")][0]
    prefix = pkl[:-len("data.pkl")]
    obj = R.StubUnpickler(io.BytesIO(zf.read(pkl))).load()
    return zf, prefix, obj

def tvals(zf, prefix, t):
    assert t.storage.dtype_name == "FloatStorage", t.storage.dtype_name
    raw = zf.read(prefix + "data/" + t.storage.key)
    if len(t.size) == 0:
        return [struct.unpack_from("<f", raw, 4 * t.offset)[0]]
    assert len(t.size) == 1, t.size
    return [struct.unpack_from("<f", raw, 4 * (t.offset + i * t.stride[0]))[0] for i in range(t.size[0])]

for version, seed, rdir in R.RUNS:
    zf, prefix, obj = load("%s/%s/checkpoints/final.pt" % (R.REC, rdir))
    md = obj["metadata"]; ms = obj["model_state"]
    pg = obj["optimizer_state"]["param_groups"][0]; st = obj["optimizer_state"]["state"]
    sd = list(ms.keys()); core = ["left.weight", "merge.weight", "right.weight"]
    orders = {"state_dict": sd, "learnable_names": list(md["learnable_names"]), "core_first": core + [k for k in sd if k not in core]}
    ok = {}
    for oname, order in orders.items():
        ok[oname] = all(st[pg["params"][i]]["exp_avg"].size == ms[n].size for i, n in enumerate(order))
    print("==", version, seed, "cursor", md.get("cursor"), "shape-match:", ok)
    order = orders["core_first"] if ok["core_first"] else None
    if order is None:
        print("   NO ORDER MATCHES; skip"); continue
    for name in ("round_mix", "round_rate"):
        i = order.index(name); s = st[pg["params"][i]]
        step = tvals(zf, prefix, s["step"])[0]
        m = tvals(zf, prefix, s["exp_avg"]); v = tvals(zf, prefix, s["exp_avg_sq"])
        print("   %s idx %d step %r exp_avg %r exp_avg_sq %r" % (name, i, step, [repr(x) for x in m], [repr(x) for x in v]))
        if name == "round_rate":
            rate = tvals(zf, prefix, ms["round_rate"])[0]
            mhat = m[0] / (1 - 0.9 ** step); vhat = v[0] / (1 - 0.999 ** step)
            print("      adam step estimate lr*mhat/(sqrt(vhat)+eps) = %r ; decoupled decay lr*wd*rate = %r ; sqrt(vhat) = %r"
                  % (0.003 * mhat / (math.sqrt(vhat) + 1e-8), 0.003 * 0.01 * rate, math.sqrt(vhat)))
