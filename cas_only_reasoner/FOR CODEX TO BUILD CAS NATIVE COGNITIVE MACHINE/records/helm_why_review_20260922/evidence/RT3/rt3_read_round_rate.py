"""RT3: read round_rate and round_mix from six Helm final.pt / initial.pt WITHOUT importing torch.

Read-only. Opens each .pt as a zip, unpickles data.pkl with a custom Unpickler whose find_class
stubs ONLY torch._utils._rebuild_tensor_v2 and torch.*Storage classes. Every find_class request
is logged; anything else from the torch namespace aborts with UNREADABLE_WITHOUT_TORCH.
Then reads raw little-endian float32 bytes of the round_rate and round_mix storages.
"""
import hashlib
import io
import json
import math
import pickle
import struct
import sys
import zipfile

ROOT = ("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE "
        "MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
REC = ROOT + "/records/typed_pointer_001"
RUNS = [
    ("helm1.0", "20260917", "receipt_helm1_certified_20260917"),
    ("helm1.0", "20260918", "receipt_helm1_certified_20260918"),
    ("helm1.0", "20260919", "receipt_helm1_certified_20260919"),
    ("helm2.0", "20260917", "receipt_20260917"),
    ("helm2.0", "20260918", "receipt_20260918"),
    ("helm2.0", "20260919", "receipt_20260919"),
]
FILES = sys.argv[1].split(",") if len(sys.argv) > 1 else ["initial.pt", "final.pt"]

STORAGE_NAMES = {"FloatStorage", "DoubleStorage", "HalfStorage", "LongStorage", "IntStorage",
                 "ShortStorage", "CharStorage", "ByteStorage", "BoolStorage", "BFloat16Storage",
                 "UntypedStorage"}
FIND_CLASS_LOG = []


class Storage:
    def __init__(self, dtype_name, key, location, numel):
        self.dtype_name, self.key, self.location, self.numel = dtype_name, key, location, numel


class StubTensor:
    def __init__(self, storage, offset, size, stride, requires_grad):
        self.storage, self.offset, self.size, self.stride = storage, offset, tuple(size), tuple(stride)
        self.requires_grad = requires_grad


def _rebuild_tensor_v2(storage, storage_offset, size, stride, requires_grad, backward_hooks, metadata=None):
    return StubTensor(storage, storage_offset, size, stride, requires_grad)


class StorageType:
    def __init__(self, name):
        self.name = name


class Unreadable(Exception):
    pass


class StubUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        FIND_CLASS_LOG.append((module, name))
        if module == "torch._utils" and name == "_rebuild_tensor_v2":
            return _rebuild_tensor_v2
        if module == "torch" and name in STORAGE_NAMES:
            return StorageType(name)
        if module.split(".")[0] == "torch":
            raise Unreadable("UNREADABLE_WITHOUT_TORCH: needs %s.%s" % (module, name))
        return super().find_class(module, name)

    def persistent_load(self, pid):
        # torch zip format: ('storage', storage_type, key, location, numel)
        if not (isinstance(pid, tuple) and pid and pid[0] == "storage"):
            raise Unreadable("UNREADABLE_WITHOUT_TORCH: unexpected persistent id %r" % (pid,))
        _, stype, key, location, numel = pid
        return Storage(stype.name if isinstance(stype, StorageType) else repr(stype), key, location, numel)


def walk(obj, path, out):
    if isinstance(obj, StubTensor):
        out.append((path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, path + (str(k),), out)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            walk(v, path + (str(i),), out)


def floats(zf, prefix, tensor):
    st = tensor.storage
    if st.dtype_name != "FloatStorage":
        raise Unreadable("dtype %s" % st.dtype_name)
    raw = zf.read(prefix + "data/" + st.key)
    n = 1
    for d in tensor.size:
        n *= d
    # contiguous check for 1-D
    vals = struct.unpack("<%df" % st.numel, raw[:4 * st.numel])
    if len(tensor.size) == 1:
        return [vals[tensor.offset + i * tensor.stride[0]] for i in range(tensor.size[0])], len(raw)
    raise Unreadable("non-1D %r" % (tensor.size,))


def main():
    report = []
    for version, seed, rdir in RUNS:
        for fname in FILES:
            path = "%s/%s/checkpoints/%s" % (REC, rdir, fname)
            with open(path, "rb") as fh:
                blob = fh.read()
            sha = hashlib.sha256(blob).hexdigest()
            zf = zipfile.ZipFile(io.BytesIO(blob))
            names = zf.namelist()
            pkl = [n for n in names if n.endswith("/data.pkl") or n == "data.pkl"]
            assert len(pkl) == 1, pkl
            prefix = pkl[0][: -len("data.pkl")]
            before = len(FIND_CLASS_LOG)
            obj = StubUnpickler(io.BytesIO(zf.read(pkl[0]))).load()
            classes = sorted(set(FIND_CLASS_LOG[before:]))
            tensors = []
            walk(obj, (), tensors)
            hits = [(p, t) for p, t in tensors if p and p[-1] in ("round_rate", "round_mix")]
            row = {"version": version, "seed": seed, "file": fname, "sha256": sha, "bytes": len(blob),
                   "zip_prefix": prefix, "top_keys": list(obj.keys()) if isinstance(obj, dict) else repr(type(obj)),
                   "find_class": classes, "n_tensors": len(tensors), "entries": []}
            for p, t in hits:
                vals, nbytes = floats(zf, prefix, t)
                entry = {"path": "/".join(p), "key": t.storage.key, "numel": t.storage.numel,
                         "size": list(t.size), "offset": t.offset, "stride": list(t.stride),
                         "storage_bytes": nbytes, "values_repr": [repr(v) for v in vals],
                         "raw_hex": zf.read(prefix + "data/" + t.storage.key).hex()}
                if p[-1] == "round_rate":
                    r = vals[0]
                    entry["tanh"] = repr(math.tanh(r))
                    entry["g"] = repr(0.01 * math.tanh(r))
                if p[-1] == "round_mix":
                    m = max(vals)
                    ex = [math.exp(v - m) for v in vals]
                    s = sum(ex)
                    entry["softmax"] = [repr(e / s) for e in ex]
                row["entries"].append(entry)
            report.append(row)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    try:
        main()
    except Unreadable as exc:
        print(str(exc))
        print("find_class log:", sorted(set(FIND_CLASS_LOG)))
        sys.exit(3)
