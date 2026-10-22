"""EYE-ACT-1 seal: hash every source file the run loads (found by running one world of every kind in every arm and
listing the loaded modules under the repo), plus the pre-registration, amendments and the kit; zip them with the
manifest. The zip's sha256 goes into the owner's line; the scored run checks the manifest before it starts.

  python -B seal_ea1.py <out_dir>          -> <out_dir>/EYE_ACT_1_SEALED.zip, SOURCE_MANIFEST.json, ZIP_SHA256.txt
  python -B seal_ea1.py --verify <SOURCE_MANIFEST.json>   -> exit 0 only if every file still matches
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

KIT = Path(__file__).resolve().parent
REPO = KIT.parents[3]
PACKET = KIT.parent
sys.path[:0] = [str(KIT), str(REPO)]
sys.dont_write_bytecode = True


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def loaded_sources():
    import ea1_world as G
    import ea1_arms as A
    for k in G.KINDS:
        w = G.make_world("seal:" + k, k)
        for arm in A.ARMS:
            A.run_world(w, arm)
    files = set()
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if f:
            p = Path(f).resolve()
            try:
                p.relative_to(REPO)
            except ValueError:
                continue
            files.add(p)
    files |= {p.resolve() for p in PACKET.glob("*.md")} | {p.resolve() for p in PACKET.glob("*.sha256")}
    files |= {p.resolve() for p in KIT.glob("*.py")}
    files.add((REPO / "test_helm_eye_act.py").resolve())
    files.add((REPO / "test_helm_cas_address.py").resolve())
    return sorted(files)


def verify(manifest_path: Path) -> int:
    m = json.loads(manifest_path.read_text("utf-8"))
    bad = [e["path"] for e in m["files"] if not (REPO / e["path"]).exists() or sha(REPO / e["path"]) != e["sha256"]]
    print(json.dumps({"files": len(m["files"]), "bad": bad}))
    return 0 if not bad else 1


def main():
    if sys.argv[1] == "--verify":
        sys.exit(verify(Path(sys.argv[2])))
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    files = loaded_sources()
    entries = [{"path": p.relative_to(REPO).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size} for p in files]
    manifest = {"version": "eye_act_1_seal_v1", "files": entries}
    mpath = out / "SOURCE_MANIFEST.json"
    mpath.write_bytes(json.dumps(manifest, indent=1, sort_keys=True).encode("utf-8"))
    zpath = out / "EYE_ACT_1_SEALED.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for e in sorted(entries, key=lambda e: e["path"]):
            info = zipfile.ZipInfo(e["path"], date_time=(2026, 10, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, (REPO / e["path"]).read_bytes())
        info = zipfile.ZipInfo("SOURCE_MANIFEST.json", date_time=(2026, 10, 21, 0, 0, 0))
        z.writestr(info, mpath.read_bytes())
    zsha = sha(zpath)
    (out / "ZIP_SHA256.txt").write_text(zsha + "  EYE_ACT_1_SEALED.zip\n", "utf-8")
    print(json.dumps({"files": len(entries), "manifest_sha256": sha(mpath), "zip_sha256": zsha,
                      "zip_bytes": zpath.stat().st_size}, indent=1))


if __name__ == "__main__":
    main()
