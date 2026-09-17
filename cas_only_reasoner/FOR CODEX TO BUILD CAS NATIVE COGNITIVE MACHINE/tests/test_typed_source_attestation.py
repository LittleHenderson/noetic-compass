"""Fresh-process tests of actual imports, tampering, and compiled-byte custody."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

BOOTSTRAP = Path(__file__).resolve().parents[1] / "cncm/typed_source_attestation.py"


@pytest.fixture
def package(tmp_path):
    files = {"cncm/__init__.py": b"", "cncm/example.py": b"VALUE = 41 + 1\n",
             "research/CAS_META_2_COMPOSITION/cas_meta2/__init__.py": b""}
    rows = []
    for name, raw in sorted(files.items()):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        rows.append({"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    return tmp_path, rows


def child(package, code, *, before="", rows=None):
    root, default_rows = package
    script = ("import json,runpy,sys\nfrom pathlib import Path\n"
              "api=runpy.run_path(sys.argv[1])\nroot=Path(sys.argv[2])\nrows=json.loads(sys.argv[3])\n"
              + before + "\nloader=api['install'](root,rows)\n" + code)
    return subprocess.run([sys.executable, "-I", "-B", "-c", script, str(BOOTSTRAP), str(root),
                           json.dumps(default_rows if rows is None else rows)], capture_output=True, text=True, timeout=20)


def test_actual_source_exec_and_snapshot(package):
    result = child(package, "import cncm.example\nassert cncm.example.VALUE==42\nprint(json.dumps(loader.snapshot()))")
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert [r["module"] for r in receipt["modules"]] == ["cncm", "cncm.example"]
    assert all(r["execution"] == "COMPILED_FROM_VERIFIED_SOURCE_BYTES" for r in receipt["modules"])
    assert not list(package[0].rglob("__pycache__"))


def test_existing_bytecode_cannot_supply_code(package):
    result = child(package, "import cncm.example\nassert cncm.example.VALUE==42\nloader.snapshot()",
        before="import py_compile\np=root/'cncm/example.py'\nraw=p.read_bytes()\np.write_text('VALUE=999\\n')\npy_compile.compile(str(p),doraise=True)\np.write_bytes(raw)")
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("code,reason", [
    ("import cncm.example\n(root/'cncm/example.py').write_text('VALUE=43\\n')\nloader.snapshot()", "SOURCE_"),
    ("import cncm.example\ncncm.example.__file__=str(root/'cncm/__init__.py')\nloader.snapshot()", "LOADED_ORIGIN"),
    ("import types\nsys.modules['cncm.foreign']=types.ModuleType('cncm.foreign')\nloader.snapshot()", "UNATTESTED"),
    ("import cncm.example\ndel sys.modules['cncm.example']\nloader.snapshot()", "UNATTESTED"),
    ("import cncm.example,importlib\nimportlib.reload(cncm.example)", "RELOAD_NOT_ADMITTED"),
    ("import cncm.undeclared", "UNDECLARED_OR_AMBIGUOUS_MODULE"),
    ("(root/'cncm/example.py').write_text('VALUE=43\\n')\nimport cncm.example", "SOURCE_"),
])
def test_import_or_snapshot_rejects_tampering(package, code, reason):
    result = child(package, code)
    assert result.returncode != 0 and reason in result.stderr


def test_preexisting_project_module_rejected(package):
    result = child(package, "", before="import types\nsys.modules['cncm']=types.ModuleType('cncm')")
    assert result.returncode != 0 and "FRESH_PROCESS_REQUIRED" in result.stderr


@pytest.mark.parametrize("name", ["../escape.py", "/escape.py", "cncm\\x.py", "cncm/./x.py", "C:/x.py"])
def test_manifest_path_rejected(package, name):
    rows = package[1] + [{"path": name, "bytes": 0, "sha256": "0" * 64}]
    result = child(package, "", rows=sorted(rows, key=lambda r: r["path"]))
    assert result.returncode != 0 and "ROW_PATH" in result.stderr


def test_duplicate_manifest_path_rejected(package):
    rows = sorted(package[1] + [package[1][0]], key=lambda r: r["path"])
    result = child(package, "", rows=rows)
    assert result.returncode != 0 and "ROWS_SORTED_UNIQUE" in result.stderr
