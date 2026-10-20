"""Test: the fetch script carries no '@' anywhere (no e-mail in any User-Agent or header)."""
from pathlib import Path
src = (Path(__file__).resolve().parent / "fetch_c1.py").read_bytes()
assert b"@" not in src, "fetch_c1.py contains '@'"
print("PASS test_fetch_no_email: 0 '@' in fetch_c1.py (%d bytes)" % len(src))
