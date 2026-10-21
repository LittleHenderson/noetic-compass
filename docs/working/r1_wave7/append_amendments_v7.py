"""Builder tool (NOT sealed): append amendments A-R1W7-7 (section 19, the package copy with the hook diff and the measured
effect) and A-R1W7-8 (section 20) to the package's PREREGISTRATION_R1W7.md, and write the two amendment files beside the zip.
Bodies are plain files written with an editor (never through a shell here-string).

    python -X utf8 -B -I append_amendments_v7.py <v7 package dir>
"""
import sys
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
B = Path(__file__).resolve().parent
A7 = (B / "AMENDMENT_A_R1W7_7_PKG_BODY.md").read_bytes().decode("utf-8")
A8 = (B / "AMENDMENT_A_R1W7_8_BODY.md").read_bytes().decode("utf-8")
pre = PKG / "PREREGISTRATION_R1W7.md"
text = pre.read_bytes().decode("utf-8")
if "## 19. Amendment A-R1W7-7" in text or "## 20. Amendment A-R1W7-8" in text:
    raise SystemExit("already amended")
if "## 18. Amendment A-R1W7-6" not in text:
    raise SystemExit("section 18 missing: not the v6 preregistration")
if not text.endswith("\n"):
    text += "\n"
pre.write_bytes((text + A7 + A8).encode("utf-8"))
(PKG.parent / "AMENDMENT_A_R1W7_7_PKG.md").write_bytes(A7.lstrip("\n").encode("utf-8"))
(PKG.parent / "AMENDMENT_A_R1W7_8.md").write_bytes(A8.lstrip("\n").encode("utf-8"))
for p in (pre, PKG.parent / "AMENDMENT_A_R1W7_7_PKG.md", PKG.parent / "AMENDMENT_A_R1W7_8.md"):
    raw = p.read_bytes()
    if b"\x08" in raw or b"\r" in raw:
        raise SystemExit("stray control byte in " + str(p))
print("appended sections 19 and 20")
