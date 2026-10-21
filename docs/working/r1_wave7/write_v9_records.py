"""Builder tool (NOT sealed): the v8 void note (beside the v8 zip, beside the v9 zip and at the r1_wave7 root) and the v9 row of
TEST_RECORD_R1W7.md (the repo copy is the live file; a copy is written beside the v9 zip). Section 13 is v8's row, so the v9 row is
section 14; the title gains the v9 clause. Written only AFTER v9 is sealed (the seal tool refuses otherwise: the void note names the v9
zip sha256, which must exist).

    python -X utf8 -B -I write_v9_records.py <r1_wave7 dir> <repo TEST_RECORD_R1W7.md>
"""
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
TR = Path(sys.argv[2]).resolve()
B = Path(__file__).resolve().parent

VOID = (B / "V8_VOID_NOTE_BODY.md").read_text(encoding="utf-8")
ROW = (B / "TEST_RECORD_V9_ROW_BODY.md").read_text(encoding="utf-8")
zip9 = ROOT / "build_v9" / "HELM_R1_W7_20261020_SOURCE_R1W7_v9.zip"
if not zip9.is_file():
    raise SystemExit("v9 is not sealed yet: refuse to void v8")
z = hashlib.sha256(zip9.read_bytes()).hexdigest()
if z not in VOID:
    raise SystemExit("the void note does not name the sealed v9 zip sha256 " + z)

for p in (ROOT / "v8_VOID_SUPERSEDED_BY_V9.md", ROOT / "build_v8" / "v8_VOID_SUPERSEDED_BY_V9.md", ROOT / "build_v9" / "v8_VOID_SUPERSEDED_BY_V9.md"):
    p.write_text(VOID, encoding="utf-8", newline="\n")
t = TR.read_text(encoding="utf-8")
if "## 14. v9 row" in t:
    raise SystemExit("already has the v9 row")
old = ("# TEST RECORD — HELM-R1 wave 7, the CHAT WAVE, v3 (FIX FIRST round 2), v4 (reader repair, section 9), v5 (FIX FIRST round 3, "
       "section 10), v6 (machine-neutral pin test + the host-exact suite rule, section 11), v7 (the reseal on the reader-gap cut, "
       "section 12, on PR #436) and v8 (the reseal on the reader v7.1 fix, section 13; builder, laptop, 0 USD; practice data only)")
if t.count(old) != 1:
    raise SystemExit("title not found (is the v8 title here?)")
t = t.replace(old, "# TEST RECORD — HELM-R1 wave 7, the CHAT WAVE, v3 (FIX FIRST round 2), v4 (reader repair, section 9), v5 (FIX FIRST round 3, "
                   "section 10), v6 (machine-neutral pin test + the host-exact suite rule, section 11), v7 (the reseal on the reader-gap cut, "
                   "section 12, on PR #436), v8 (the reseal on the reader v7.1 fix, section 13) and v9 (the reseal on the reader v7.2 fix after "
                   "job c55, section 14; builder, laptop, 0 USD; practice data only)")
if not t.endswith("\n"):
    t += "\n"
TR.write_text(t + ROW, encoding="utf-8", newline="\n")
shutil.copyfile(TR, ROOT / "build_v9" / "TEST_RECORD_R1W7.md")
for p in (ROOT / "v8_VOID_SUPERSEDED_BY_V9.md", ROOT / "build_v9" / "TEST_RECORD_R1W7.md"):
    raw = p.read_bytes()
    if b"\x08" in raw or b"\r" in raw:
        raise SystemExit("stray control byte in " + str(p))
print("written")
