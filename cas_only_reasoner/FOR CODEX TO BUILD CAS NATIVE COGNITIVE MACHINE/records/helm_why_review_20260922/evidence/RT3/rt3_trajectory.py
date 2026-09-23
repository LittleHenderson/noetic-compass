"""round_rate / g over the saved checkpoints of each run (evidence/main_checkpoint_*.pt + checkpoints/*.pt). No torch."""
import io, sys, zipfile, struct, math, hashlib, os
sys.path.insert(0, ".")
import rt3_read_round_rate as R

def read(path):
    zf = zipfile.ZipFile(path)
    pkl = [n for n in zf.namelist() if n.endswith("data.pkl")][0]
    prefix = pkl[:-len("data.pkl")]
    before = len(R.FIND_CLASS_LOG)
    obj = R.StubUnpickler(io.BytesIO(zf.read(pkl))).load()
    fc = set(R.FIND_CLASS_LOG[before:])
    ms = obj["model_state"] if isinstance(obj, dict) and "model_state" in obj else None
    if ms is None:
        return None, sorted(fc), list(obj.keys()) if isinstance(obj, dict) else type(obj)
    out = {}
    for name in ("round_rate", "round_mix"):
        t = ms[name]
        raw = zf.read(prefix + "data/" + t.storage.key)
        out[name] = [struct.unpack_from("<f", raw, 4 * (t.offset + i * t.stride[0]))[0] for i in range(t.size[0])]
    md = obj.get("metadata", {})
    return (out, md.get("cursor")), sorted(fc), None

for version, seed, rdir in R.RUNS:
    base = "%s/%s" % (R.REC, rdir)
    ev = sorted(f for f in os.listdir(base + "/collected/results/evidence") if f.endswith(".pt"))
    paths = [("checkpoints/initial.pt", base + "/checkpoints/initial.pt"),
             ("checkpoints/pass_01.pt", base + "/checkpoints/pass_01.pt")]
    paths += [("evidence/" + f, base + "/collected/results/evidence/" + f) for f in ev]
    paths += [("checkpoints/prelast.pt", base + "/checkpoints/prelast.pt"),
              ("checkpoints/final.pt", base + "/checkpoints/final.pt"),
              ("checkpoints/retained.pt", base + "/checkpoints/retained.pt")]
    print("==", version, seed)
    for label, p in paths:
        res, fc, other = read(p)
        extra = [c for c in fc if c not in {("collections", "OrderedDict"), ("torch", "ByteStorage"), ("torch", "FloatStorage"), ("torch._utils", "_rebuild_tensor_v2")}]
        if res is None:
            print("   %-34s NO model_state; top=%r extra_classes=%r" % (label, other, extra)); continue
        (vals, cursor) = res
        r = vals["round_rate"][0]
        print("   %-34s cursor=%-5s round_rate=%-24r g=%-26r round_mix=%r%s" % (
            label, cursor, r, 0.01 * math.tanh(r), vals["round_mix"], (" EXTRA " + repr(extra)) if extra else ""))
