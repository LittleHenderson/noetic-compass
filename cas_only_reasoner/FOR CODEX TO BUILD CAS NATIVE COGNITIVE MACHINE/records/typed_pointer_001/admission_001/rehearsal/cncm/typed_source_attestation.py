"""Manifest-bound source loader for a fresh typed CUDA worker process.

This standalone stdlib module is bootstrapped from manifest-verified bytes.
Install before importing either project package. Project source is compiled
directly from the verified bytes; an existing .pyc can never supply its code.
This is process-level source evidence, not a trusted-hardware attestation.
"""
from __future__ import annotations

from hashlib import sha256
import importlib.abc
import importlib.util
from pathlib import Path, PurePosixPath
import re
import sys

PREFIXES = {"cncm": "cncm", "cas_meta2": "research/CAS_META_2_COMPOSITION/cas_meta2"}
MAX_SOURCE_BYTES = 4 * 1024 ** 2


def require(condition, reason):
    if not condition:
        raise ValueError("TYPED_SOURCE:" + reason)


def owned(name):
    return any(name == prefix or name.startswith(prefix + ".") for prefix in PREFIXES)


class VerifiedLoader(importlib.abc.Loader):
    def __init__(self, owner, name, row, package):
        self.owner, self.name, self.row, self.package = owner, name, row, package

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        require(self.name not in self.owner.executed, "RELOAD_NOT_ADMITTED:" + self.name)
        raw, path = self.owner.read(self.row)
        code = compile(raw, str(path), "exec", dont_inherit=True, optimize=0)
        # Record the exact object and bytes at the actual execution boundary.
        self.owner.executed[self.name] = (module, self, dict(self.row))
        try:
            exec(code, module.__dict__)
            require(self.owner.read(self.row)[0] == raw, "CHANGED_DURING_IMPORT:" + self.name)
        except BaseException:
            self.owner.failed.add(self.name)
            raise


class ManifestImporter(importlib.abc.MetaPathFinder):
    def __init__(self, root, rows):
        self.root = Path(root).resolve(strict=True)
        require(self.root.is_dir(), "ROOT_NOT_DIRECTORY")
        require(type(rows) is list and 0 < len(rows) <= 2000, "MANIFEST_ROWS")
        self.rows, self.executed, self.failed = {}, {}, set()
        names = []
        for row in rows:
            require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}, "ROW_FIELDS")
            name = row["path"]
            require(type(name) is str and name and "\\" not in name
                    and not PurePosixPath(name).is_absolute()
                    and PurePosixPath(name).as_posix() == name
                    and all(p not in ("", ".", "..") and ":" not in p for p in name.split("/")), "ROW_PATH")
            require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_SOURCE_BYTES, "ROW_BYTES")
            require(type(row["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]), "ROW_HASH")
            names.append(name)
            self.rows[name] = dict(row)
        require(names == sorted(set(names)), "ROWS_SORTED_UNIQUE")
        for prefix in PREFIXES.values():
            require(prefix + "/__init__.py" in self.rows, "PACKAGE_INIT_MISSING:" + prefix)

    def read(self, row):
        path = self.root.joinpath(*row["path"].split("/"))
        require(not path.is_symlink() and path.resolve(strict=True).is_relative_to(self.root), "SOURCE_ESCAPE")
        require(path.is_file() and path.stat().st_size == row["bytes"], "SOURCE_SIZE:" + row["path"])
        with path.open("rb") as stream:
            raw = stream.read(MAX_SOURCE_BYTES + 1)
        require(len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"], "SOURCE_BYTES:" + row["path"])
        return raw, path.resolve(strict=True)

    def find_spec(self, fullname, path=None, target=None):
        if not owned(fullname):
            return None
        require(target is None, "RELOAD_NOT_ADMITTED:" + fullname)
        parts = fullname.split(".")
        base = PREFIXES[parts[0]] + ("/" + "/".join(parts[1:]) if len(parts) > 1 else "")
        choices = [(base + "/__init__.py", True), (base + ".py", False)]
        candidates = [(self.rows[name], package) for name, package in choices if name in self.rows]
        require(len(candidates) == 1, "UNDECLARED_OR_AMBIGUOUS_MODULE:" + fullname)
        row, package = candidates[0]
        _, source_path = self.read(row)
        loader = VerifiedLoader(self, fullname, row, package)
        return importlib.util.spec_from_file_location(fullname, str(source_path), loader=loader,
            submodule_search_locations=[str(source_path.parent)] if package else None)

    def snapshot(self):
        require(not self.failed, "FAILED_IMPORTS:" + ",".join(sorted(self.failed)))
        loaded = {name: module for name, module in sys.modules.copy().items() if owned(name)}
        require(set(loaded) == set(self.executed), "UNATTESTED_OR_REMOVED_MODULES")
        result = []
        for name, module in sorted(loaded.items()):
            expected_module, loader, row = self.executed[name]
            _, path = self.read(row)
            require(module is expected_module and module.__loader__ is loader
                    and module.__spec__.loader is loader
                    and Path(module.__file__).resolve(strict=True) == path
                    and Path(module.__spec__.origin).resolve(strict=True) == path, "LOADED_ORIGIN:" + name)
            result.append({"module": name, **row, "execution": "COMPILED_FROM_VERIFIED_SOURCE_BYTES"})
        return {"schema": "cncm.typed-loaded-project-sources/0.1", "modules": result,
                "boundary": "Exact process loader and source bytes; not hardware or OS attestation."}


def install(root, rows):
    require(not any(owned(name) for name in sys.modules), "FRESH_PROCESS_REQUIRED")
    importer = ManifestImporter(root, rows)
    sys.meta_path.insert(0, importer)
    return importer
