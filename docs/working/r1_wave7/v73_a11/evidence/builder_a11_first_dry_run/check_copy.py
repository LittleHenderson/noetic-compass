"""check_copy.py <zip> <copy_root>/HELM_R1_W7_20261020 <deps_dir> -- the scratch copy equals the sealed v9 zip member for
member (every file in the zip, byte for byte, and no extra file), and every neighbour copy matches its freeze."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ZIP_SHA = "ad3fb98cd3254963263929747791d151949c2f50923672e4bcbf3fc14490942c"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main(zp, root, deps) -> int:
    zp, root, deps = Path(zp), Path(root), Path(deps)
    zs = sha(zp.read_bytes())
    print("zip_sha256", zs, "pinned_ok", zs == ZIP_SHA)
    z = zipfile.ZipFile(zp)
    top = root.name + "/"
    members = {n[len(top):]: z.read(n) for n in z.namelist() if n.startswith(top) and not n.endswith("/")}
    on_disk = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    bad = [rel for rel, b in members.items() if not (root / rel).is_file() or (root / rel).read_bytes() != b]
    extra = sorted(on_disk - set(members))
    print("zip_files", len(members), "copy_files", len(on_disk), "differ", len(bad), "extra", extra[:10])
    ok = zs == ZIP_SHA and not bad and not extra
    pins = {"HELM_R1_W1_20261015": "8c55c4136e1b24bc322779160ffed666f9eb9ee21512c1972101263a243c039b",
            "HELM_R1_W3_20261019": "bd06f324a9643a8aacefab3d8ef52de4cf673a68820544897def95854b73d310",
            "HELM_R1_W3B_20261019": "a6d9dbc78d3f720941c5a358be9a4d514617f8de226811c55938f807833dfbba",
            "HELM_R1_W6_20261019": "da1ec4d2e144a8921d27231e99ff277de0e915b61e2de205cc94646a4723c8a8",
            "HELM_RBW1T_20261019": "04eef88645acbd0c89de9e6e914d8faf2896939769e11f4d4c93f2dfc12e84f4"}
    for d, pin in pins.items():
        fz = deps / d / "PACKAGE_FREEZE.json"
        raw = fz.read_bytes()
        mem = json.loads(raw).get("members") or {}
        badm = [r for r, v in mem.items() if not (deps / d / r).is_file() or sha((deps / d / r).read_bytes()) != v["sha256"]]
        good = sha(raw) == pin and not badm
        print("neighbour", d, "freeze_ok", sha(raw) == pin, "members", len(mem), "bad", len(badm))
        ok = ok and good
    print("ALL_EQUAL", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
