"""Byte checks for protected accepted source and installed frozen wheels."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import zipfile
from . import ROOT

BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
WHEELS = {
    "casformer": ("casformer_reference-0.1.0-py3-none-any.whl", "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee"),
    "cas_cjt": ("cas_neural_cjt-0.2.0-py3-none-any.whl", "6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9"),
}


def verify_baseline():
    manifest = json.loads((ROOT / "BASELINE_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest["baseline_sha"] != BASELINE_SHA:
        raise RuntimeError("BASELINE_COMMIT_MISMATCH")
    research = ROOT.parent.resolve()
    for item in manifest["files"]:
        target = (research / item["path"]).resolve()
        if not target.is_relative_to(research) or not target.is_file():
            raise RuntimeError("BASELINE_PATH_INVALID:" + item["path"])
        if sha256(target.read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError("BASELINE_BYTES_CHANGED:" + item["path"])
    return {"baseline_sha": BASELINE_SHA, "files_verified": len(manifest["files"])}


def verify_installed_wheels():
    # find_spec avoids running these packages' module code merely to locate files.
    results = {}
    for package, (name, expected_hash) in WHEELS.items():
        wheel = ROOT.parent / "CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist" / name
        if sha256(wheel.read_bytes()).hexdigest() != expected_hash:
            raise RuntimeError("FROZEN_WHEEL_HASH_MISMATCH:" + name)
        spec = importlib.util.find_spec(package)
        if spec is None or spec.origin is None:
            raise RuntimeError("FROZEN_WHEEL_NOT_INSTALLED:" + package)
        installed = Path(spec.origin).resolve().parent
        checked = 0
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.infolist():
                if member.is_dir() or not member.filename.startswith(package + "/"):
                    continue
                relative = member.filename.removeprefix(package + "/")
                path = (installed / relative).resolve()
                if not path.is_relative_to(installed) or path.read_bytes() != archive.read(member):
                    raise RuntimeError("INSTALLED_WHEEL_BYTES_DIFFER:" + member.filename)
                checked += 1
        if not checked:
            raise RuntimeError("EMPTY_FROZEN_PACKAGE")
        results[package] = {"path": str(installed), "wheel_sha256": expected_hash,
                            "package_files_verified": checked}
    return results
