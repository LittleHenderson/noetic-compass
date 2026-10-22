"""Builder tool: report every control byte (0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f, 0x7f) and lone CR in the given files. Exit 1 if any."""
import re
import sys
from pathlib import Path

bad = 0
rx = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]|\r(?!\n)")
for p in sys.argv[1:]:
    d = Path(p).read_bytes()
    hits = [(m.start(), m.group()) for m in rx.finditer(d)]
    print(f"{p}: {len(hits)} control bytes", [(i, b, d[max(0, i - 25):i + 10]) for i, b in hits[:6]])
    bad += len(hits)
sys.exit(1 if bad else 0)
