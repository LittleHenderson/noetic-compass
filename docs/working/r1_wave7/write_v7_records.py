"""Builder tool (NOT sealed): the v6 void note (beside the v6 zip and at the r1_wave7 root) and the v7 row of TEST_RECORD_R1W7.md
(the repo copy is the live file; a copy is written beside the v7 zip).

    python -X utf8 -B -I write_v7_records.py <r1_wave7 dir> <repo TEST_RECORD_R1W7.md>
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
TR = Path(sys.argv[2]).resolve()
B = Path(__file__).resolve().parent

VOID = (B / "V6_VOID_NOTE_BODY.md").read_text(encoding="utf-8")
ROW = (B / "TEST_RECORD_V7_ROW_BODY.md").read_text(encoding="utf-8")

for p in (ROOT / "v6_VOID_SUPERSEDED_BY_V7.md", ROOT / "build_v6" / "v6_VOID_SUPERSEDED_BY_V7.md"):
    p.write_text(VOID, encoding="utf-8", newline="\n")
t = TR.read_text(encoding="utf-8")
if "## 12. v7 row" in t:
    raise SystemExit("already has the v7 row")
old = ("# TEST RECORD — HELM-R1 wave 7, the CHAT WAVE, v3 (FIX FIRST round 2), v4 (reader repair, section 9), v5 (FIX FIRST round 3, "
       "section 10) and v6 (machine-neutral pin test + the host-exact suite rule, section 11; builder, laptop, 0 USD; practice data only)")
if t.count(old) != 1:
    raise SystemExit("title not found")
t = t.replace(old, "# TEST RECORD — HELM-R1 wave 7, the CHAT WAVE, v3 (FIX FIRST round 2), v4 (reader repair, section 9), v5 (FIX FIRST round 3, "
                   "section 10), v6 (machine-neutral pin test + the host-exact suite rule, section 11) and v7 (the reseal on the reader-gap cut "
                   "with amendments A-R1W7-7 and A-R1W7-8, section 12; builder, laptop, 0 USD; practice data only)")
if not t.endswith("\n"):
    t += "\n"
TR.write_text(t + ROW, encoding="utf-8", newline="\n")
shutil.copyfile(TR, ROOT / "build_v7" / "TEST_RECORD_R1W7.md")
for p in (ROOT / "v6_VOID_SUPERSEDED_BY_V7.md", ROOT / "build_v7" / "TEST_RECORD_R1W7.md"):
    raw = p.read_bytes()
    if b"\x08" in raw or b"\r" in raw:
        raise SystemExit("stray control byte in " + str(p))
print("written")
