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


def write_utf8_lf_atomic(path, text: str) -> None:
    """Atomic canonical write (GATE 1A.2R.2C section 4). Same byte law as
    write_utf8_lf (UTF-8, LF, no BOM, refuses CR), but a concurrent reader never
    observes a truncated/partial file: the bytes are written to a same-directory
    temp file, flushed + fsynced, then os.replace()d over the target in one
    atomic filesystem step. The watchdog authority file and the protected-lock
    locator use this so a reader (the watchdog) can never see a half-written
    authority while the writer (the driver / the pre-watchdog step) rewrites it."""
    if "\r" in text:
        raise ValueError("CANONICAL_BYTE_VIOLATION: text contains a carriage "
                         "return; authoritative artifacts are LF-only")
    import os
    import tempfile
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent),
                               prefix="." + path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)                      # atomic on the same filesystem
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def canonical_json_bytes(obj) -> bytes:
    """The canonical serialized form used before hashing or comparing in-memory
    content with committed bytes: indent=2, trailing newline, LF only."""
    import json
    return (json.dumps(obj, indent=2) + "\n").encode("utf-8")
