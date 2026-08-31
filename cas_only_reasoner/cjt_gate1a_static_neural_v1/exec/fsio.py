"""fsio.py -- the ONE canonical writer for authoritative generated text files.

Owner directive GATE 1A.1R section 1: the package failed its freeze because two
byte-writing laws coexisted (train/val pinned LF; the dataset manifest written
with the platform default, CRLF on Windows). The package uses `.gitattributes
* -text`, so Git deliberately preserves the writer's bytes -- the writer must
therefore be canonical on every platform. Every authoritative generated file
goes through write_utf8_lf(); no other code path may write one.

Canonical byte law: UTF-8, LF line endings, no BOM, exactly the text given.
"""
from __future__ import annotations

from pathlib import Path


def write_utf8_lf(path, text: str) -> None:
    if "\r" in text:
        raise ValueError("CANONICAL_BYTE_VIOLATION: text contains a carriage "
                         "return; authoritative artifacts are LF-only")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def canonical_json_bytes(obj) -> bytes:
    """The canonical serialized form used before hashing or comparing in-memory
    content with committed bytes: indent=2, trailing newline, LF only."""
    import json
    return (json.dumps(obj, indent=2) + "\n").encode("utf-8")
