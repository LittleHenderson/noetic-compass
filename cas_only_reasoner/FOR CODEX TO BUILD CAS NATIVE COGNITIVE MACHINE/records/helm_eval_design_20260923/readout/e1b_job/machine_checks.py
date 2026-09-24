"""Two small machine-side checks for the E1b stage script (kept out of the user-data to fit its 16,000-byte limit).
CLAUDE_BUILT_CLAUDE_CHECKED.

    python -B machine_checks.py anchors ROOT      every bundled file equals anchors.json, and nothing unlisted is present
    python -B machine_checks.py smoke TORCH_LOCAL the torch build is TORCH_LOCAL, CUDA works, and the GPU is a T4
Exit 0 on PASS, 1 on FAIL. Prints one line.
"""
import hashlib
import json
import pathlib
import sys


def anchors(root):
    root = pathlib.Path(root)
    files = json.loads((root / "anchors.json").read_text(encoding="utf-8"))["files"]
    bad = [n for n, row in files.items() if hashlib.sha256((root / n).read_bytes()).hexdigest() != row["sha256"]]
    present = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    extra = sorted(present - set(files) - {"anchors.json"})
    ok = not bad and not extra
    print("ANCHORS %s: %d files, %d mismatched, %d unlisted" % ("PASS" if ok else "FAIL", len(files), len(bad), len(extra)))
    return ok


def smoke(torch_local):
    import torch                                      # machine only; the laptop never runs this mode
    ok = (torch.__version__ == torch_local and torch.cuda.is_available() and "T4" in torch.cuda.get_device_name(0)
          and float(torch.ones(8, device="cuda").sum().item()) == 8.0)
    print("SMOKE %s torch=%s cuda=%s" % ("PASS" if ok else "FAIL", torch.__version__, torch.cuda.is_available()))
    return ok


if __name__ == "__main__":
    mode, arg = sys.argv[1], sys.argv[2]
    sys.exit(0 if {"anchors": anchors, "smoke": smoke}[mode](arg) else 1)
