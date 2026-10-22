"""eye/tap.py -- the read-only, digest-checked tap the eye reads a build through.

UNITY_EYE.md section 3, in the design's own words: "Every read is a TAP (`TAP_AND_INJECT.md`
1.1): `D(brain)` before = after, digest-checked." And guardrail 6 (`:159-161`): the eye
"reads, computes and logs what it would propose, and acts on nothing."

This module is that tap, over a folder instead of a station. Three properties, and each is a
line of code rather than a promise:

  1. **It only reads.** Nothing in this file opens a file for writing, deletes anything, or
     imports the thing it is watching. It walks the folder, hashes each file, and returns the
     hashes and the file text it was asked for.
  2. **It checks the digest.** `Tap.read()` hashes the folder before it reads anything and again
     after, and refuses with `WATCHED_VALUE_MOVED` when the two differ. A read that changed what
     it read is not a read.
  3. **It names what it does not watch.** The eye's own folder holds the eye's log, and a
     watcher's log is not a watched value (UNITY_EYE.md: "its log is a separate store",
     EYE-R2). `exclude` names every directory the tap refuses to hash, and the refusal is
     recorded in the reading so the exclusion can never be silent.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import hashlib
import os

__all__ = [
    "Tap", "TapReading", "TapRefusal", "folder_digest", "file_digest",
    "WATCHED_VALUE_MOVED", "NOT_A_FOLDER", "EYE_OWNS_THE_LOG",
]

#: Refusal codes.
WATCHED_VALUE_MOVED = "WATCHED_VALUE_MOVED"
NOT_A_FOLDER = "NOT_A_FOLDER"
EYE_OWNS_THE_LOG = "EYE_OWNS_THE_LOG"

#: The files a tap reads the text of. Everything else is hashed, never read as text.
TEXT_SUFFIXES = (".py", ".md", ".json", ".txt")

#: Directories a tap never watches: the eye's own store, and the interpreter's bytecode cache
#: (a compiled copy of a file is not the value; watching it would let a stale cache read as a
#: change to the build). Both exclusions are printed in every reading.
DEFAULT_EXCLUDE = ("eye", "__pycache__")

# UNDECIDED IN SOURCES: what the eye's digest must cover, when UNITY_EYE.md says "`D(brain)` before = after, digest-checked" and never says what D hashes -- so this build hashes every watched file's path and bytes, excludes the eye's own folder by name, and prints the exclusion in the reading.
# UNDECIDED IN SOURCES: whether a tap may read a file's text at all, when the design's tap is described as reading a station out loud and this build's stations are source files -- so this build reads text for the suffixes it lists and hashes everything else, and it never writes either.


class TapRefusal(Exception):
    """A refusal with a stable code. Nothing here is ever a guess."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def file_digest(path: str) -> str:
    """sha256 of one file's bytes. Reading only."""
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def folder_digest(root: str, *, exclude=DEFAULT_EXCLUDE, suffixes=None) -> str:
    """sha256 over every watched file in a folder: its relative path and its own sha256.

    `exclude` names directory names (any depth) that are not watched. The digest is over the
    sorted `(relative path, sha256)` pairs, in plain ASCII, so two folders with the same bytes
    in the same paths give the same digest on any machine.
    """
    if not os.path.isdir(root):
        raise TapRefusal(NOT_A_FOLDER, f"a tap reads a folder, and {root!r} is not one")
    excluded = tuple(name for name in exclude)
    rows = []
    for directory, subdirectories, filenames in os.walk(root):
        subdirectories[:] = sorted(name for name in subdirectories if name not in excluded)
        for filename in sorted(filenames):
            if suffixes is not None and not filename.endswith(tuple(suffixes)):
                continue
            path = os.path.join(directory, filename)
            relative = os.path.relpath(path, root).replace(os.sep, "/")
            rows.append("%s %s" % (relative, file_digest(path)))
    payload = "\n".join(sorted(rows)).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


class TapReading:
    """What one tap read: the folder's digest before and after, and the files it saw."""

    __slots__ = ("root", "excluded", "digest_before", "digest_after", "files", "texts", "moved")

    def __init__(self, root, excluded, digest_before, digest_after, files, texts) -> None:
        self.root = root
        self.excluded = tuple(excluded)
        self.digest_before = digest_before
        self.digest_after = digest_after
        self.files = tuple(files)
        self.texts = dict(texts)
        self.moved = digest_before != digest_after

    @property
    def wrote_nothing(self) -> bool:
        return not self.moved

    def text(self, name: str) -> str:
        if name not in self.texts:
            raise TapRefusal(
                "TAP_DID_NOT_READ_THAT_FILE",
                f"{name!r} was not read by this tap; it read {sorted(self.texts)}",
            )
        return self.texts[name]

    def as_dict(self) -> dict:
        return {
            "root": self.root,
            "excluded": list(self.excluded),
            "digest_before": self.digest_before,
            "digest_after": self.digest_after,
            "moved": self.moved,
            "files": [list(item) for item in self.files],
        }

    def __repr__(self) -> str:
        return "TapReading(%s, %d files, moved=%s)" % (self.root, len(self.files), self.moved)


class Tap:
    """A tap on one folder. It reads; it cannot write, and it refuses when the value moved."""

    def __init__(self, root: str, *, exclude=DEFAULT_EXCLUDE) -> None:
        if not os.path.isdir(root):
            raise TapRefusal(NOT_A_FOLDER, f"a tap reads a folder, and {root!r} is not one")
        self._root = os.path.abspath(root)
        self._exclude = tuple(exclude)

    @property
    def root(self) -> str:
        return self._root

    @property
    def exclude(self) -> tuple:
        return self._exclude

    def read(self) -> TapReading:
        """Read every watched file, digesting the folder before and after.

        Refuses `WATCHED_VALUE_MOVED` when the two digests differ: something wrote to what the
        eye is watching, and a reading taken across a write is not a reading of the value.
        """
        before = folder_digest(self._root, exclude=self._exclude)
        files = []
        texts = {}
        for directory, subdirectories, filenames in os.walk(self._root):
            subdirectories[:] = sorted(name for name in subdirectories if name not in self._exclude)
            for filename in sorted(filenames):
                path = os.path.join(directory, filename)
                relative = os.path.relpath(path, self._root).replace(os.sep, "/")
                digest = file_digest(path)
                files.append((relative, digest))
                if filename.endswith(TEXT_SUFFIXES):
                    with open(path, "r", encoding="utf-8", errors="replace") as handle:
                        texts[relative] = handle.read()
        after = folder_digest(self._root, exclude=self._exclude)
        reading = TapReading(self._root, self._exclude, before, after, files, texts)
        if reading.moved:
            raise TapRefusal(
                WATCHED_VALUE_MOVED,
                f"the folder {self._root!r} changed while it was being read ({before[:16]} -> "
                f"{after[:16]}); the eye reads a value it cannot move, so this reading is refused",
            )
        return reading

    def __repr__(self) -> str:
        return "Tap(%s, excludes %s)" % (self._root, list(self._exclude))
