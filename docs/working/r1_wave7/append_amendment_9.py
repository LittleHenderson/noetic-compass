"""Builder tool (NOT sealed): append amendment A-R1W7-9 (section 21) to the package's PREREGISTRATION_R1W7.md and write the
amendment file beside the zip. The body is a plain file written with an editor (never through a shell here-string).

    python -X utf8 -B -I append_amendment_9.py <v8 package dir>
"""
import sys
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
B = Path(__file__).resolve().parent
A9 = (B / "AMENDMENT_A_R1W7_9_BODY.md").read_bytes().decode("utf-8")
pre = PKG / "PREREGISTRATION_R1W7.md"
text = pre.read_bytes().decode("utf-8")
if "## 21. Amendment A-R1W7-9" in text:
    raise SystemExit("already amended")
if "## 20. Amendment A-R1W7-8" not in text:
    raise SystemExit("section 20 missing: not the v7 preregistration")
if not text.endswith("\n"):
    text += "\n"
pre.write_bytes((text + A9).encode("utf-8"))
(PKG.parent / "AMENDMENT_A_R1W7_9.md").write_bytes(A9.lstrip("\n").encode("utf-8"))
for p in (pre, PKG.parent / "AMENDMENT_A_R1W7_9.md"):
    raw = p.read_bytes()
    if b"\x08" in raw or b"\r" in raw:
        raise SystemExit("stray control byte in " + str(p))
print("appended section 21")
