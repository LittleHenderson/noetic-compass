"""Build the c41 payload zip for SCORE_SCRIBE_L4_SEALED_98 (plan section 5 step 3). Bytes only; no torch; the sealed
file is copied and hashed, never opened as text. Usage: python -B build_payload_c41.py"""
import hashlib, json, subprocess, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "payload_c41"
REPO = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS")
WT = Path(r"C:\tmp\scribe-l4-c41")
PKG = REPO / "HELM_DISTRIBUTION_PACKAGE" / "scribe_l4_aws_gpu_training"
COMMIT = "84812689b6fb6de4250dc9bf2e400df88a95944c"
WANT = {
    "zip": "7179250cbb17a800280d1b6459f2bb3ee4a23048d6b5a2382020296e8cceb58b",
    "weights": "e36cf3cb50fe8ae168b2986a97000a47e7632b058b34b44629f4f17f99af9dc1",
    "vocab": "6746e5dbd77dc6ddaa7bd7270b21ca2558c4da2e439522a2fbcffc66ce4dbc1a",
    "sealed": "e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe",
    "script": "969c845e6636547afcc4d2d8f9eefe3c66e31657d8da981a885e669d182a0b72",
    "plan": "18e350f5d026a9e9ec21d62b3e696ecb5c3ec4b9940775c0964a19a9171d929e",
}


def h(b):
    return hashlib.sha256(b).hexdigest()


def git_show(path):
    return subprocess.run(["git", "-C", str(REPO), "show", COMMIT + ":" + path], capture_output=True, check=True).stdout


members = {}  # name in zip -> bytes
# 1. sealed model package: verify zip against PACKAGE_FREEZE.json, take the two code files from it
freeze = json.loads((PKG / "PACKAGE_FREEZE.json").read_bytes())
zbytes = (PKG / "SCRIBE_L4_AWS_GPU_PACKAGE.zip").read_bytes()
assert h(zbytes) == freeze["zip_sha256"] == WANT["zip"], "PACKAGE_ZIP_SHA_MISMATCH"
assert len(zbytes) == freeze["zip_bytes"]
with zipfile.ZipFile(PKG / "SCRIBE_L4_AWS_GPU_PACKAGE.zip") as z:
    for base in ("scribe_model.py", "cce_shim.py"):
        b = z.read("SCRIBE_L4_AWS_GPU/" + base)
        assert b == git_show("HELM_DISTRIBUTION_PACKAGE/scribe_l4_aws_gpu_training/" + base), base
        members["scribe_src/" + base] = b
# 2. weights + vocabulary from commit 84812689 (equal to the working copies)
for name, key in (("scribe_l4_weights.pt", "weights"), ("scribe_vocab.json", "vocab")):
    b = git_show("HELM_DISTRIBUTION_PACKAGE/scribe_l4_aws_gpu_training/outputs/" + name)
    assert h(b) == WANT[key] and b == (PKG / "outputs" / name).read_bytes(), name
    members[name] = b
# 3. plan folder (script) + approval + sealed file
ev = WT / "docs" / "working" / "scribe_l4_eval"
assert h((ev / "SCORE_SCRIBE_L4_PLAN.md").read_bytes()) == WANT["plan"]
b = (ev / "score_scribe_l4.py").read_bytes(); assert h(b) == WANT["script"]; members["score_scribe_l4.py"] = b
members["OWNER_APPROVAL_SCORE_SCRIBE_L4.md"] = (HERE / "OWNER_APPROVAL_SCORE_SCRIBE_L4.md").read_bytes()
assert b"\nAPPROVE SCORE_SCRIBE_L4_SEALED_98\n" in members["OWNER_APPROVAL_SCORE_SCRIBE_L4.md"]
b = (WT / "cas-synthetic" / "data" / "l4_split" / "real_heldout_unparseables_98.jsonl").read_bytes()
assert h(b) == WANT["sealed"]; members["real_heldout_unparseables_98.jsonl"] = b


def add_tree(src, dest):
    for p in sorted(src.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            members[dest + "/" + p.relative_to(src).as_posix()] = p.read_bytes()


add_tree(WT / "docs" / "working" / "noetic_council" / "language_v3", "language_v3")
add_tree(Path(r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011\sdg_bridge_v2"), "bridge_root/sdg_bridge_v2")
add_tree(Path(r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011\sdg_bridge"), "bridge_root/sdg_bridge")
add_tree(Path(r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1"), "lacunarity_machine_v1")

manifest = {"job": "helm-claude-scribe-l4-score-20261019-c41", "source_commit": COMMIT, "plan_sha256": WANT["plan"],
            "package_zip_sha256": WANT["zip"], "members": {k: h(v) for k, v in sorted(members.items())}}
members["PAYLOAD_MANIFEST.json"] = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode()
OUT.mkdir(exist_ok=True)
zp = OUT / "c41-payload.zip"
assert not zp.exists()
with zipfile.ZipFile(zp, "x", zipfile.ZIP_DEFLATED) as z:
    for name in sorted(members):
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 19, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, members[name])
print(json.dumps({"zip": str(zp), "bytes": zp.stat().st_size, "sha256": h(zp.read_bytes()), "members": len(members),
                  "manifest_sha256": h(members["PAYLOAD_MANIFEST.json"])}, indent=1))
