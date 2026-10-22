"""apply_amendment_7.py <package_root> -- apply A-R1W7-7 to a wave-7 package source tree (HELM_R1_W7_20261020/):
  1. r1w7/multi_qty_w7.py          (new; the rule)
  2. tests_r1w7/test_multi_qty_w7.py (new; six tests on the author's own lines)
  3. r1w7/custody_w7.py            (one import, one hook in make_all: the frozen key, then the rule)
Refuses if the hook anchor is missing or already applied. Prints the sha256 of every file it wrote or changed.
Usage: python -X utf8 -I apply_amendment_7.py C:\\path\\to\\HELM_R1_W7_20261020
"""
import hashlib
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMPORT_ANCHOR = "from r1w7 import common_w7 as C          # noqa: E402\n"
IMPORT_NEW = "from r1w7 import multi_qty_w7 as MQ      # noqa: E402  A-R1W7-7 (SPEC 7.109 D6)\n"
HOOK_OLD = '"keys": [K.key_item(it) for it in real_items]'
HOOK_NEW = '"keys": [MQ.apply(K.key_item(it), it["raw_lines"], ns.XG) for it in real_items]'


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(root: Path) -> int:
    r1w7, tests = root / "r1w7", root / "tests_r1w7"
    custody = r1w7 / "custody_w7.py"
    if not custody.is_file():
        print("REFUSED: not a wave-7 package root:", root)
        return 2
    s = custody.read_text(encoding="utf-8")
    if "multi_qty_w7" in s:
        print("REFUSED: custody_w7.py already carries the amendment")
        return 3
    if s.count(IMPORT_ANCHOR) != 1 or s.count(HOOK_OLD) != 1:
        print("REFUSED: anchors not found exactly once (import %d, hook %d)" % (s.count(IMPORT_ANCHOR), s.count(HOOK_OLD)))
        return 4
    shutil.copyfile(HERE / "multi_qty_w7.py", r1w7 / "multi_qty_w7.py")
    shutil.copyfile(HERE / "test_multi_qty_w7.py", tests / "test_multi_qty_w7.py")
    s = s.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT_NEW, 1)
    s = s.replace(HOOK_OLD, HOOK_NEW, 1)
    custody.write_text(s, encoding="utf-8", newline="\n")
    for p in (r1w7 / "multi_qty_w7.py", tests / "test_multi_qty_w7.py", custody):
        print(sha(p), p.relative_to(root).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))
