"""Pure synthetic import-resolution tests; no stored tasks or models are opened."""
from hashlib import sha256
import importlib
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

SPEC = importlib.util.spec_from_file_location("record_diagnostic_v2_tested", Path(__file__).with_name("check_records.py"))
diagnostic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnostic)


@pytest.fixture
def project(tmp_path, monkeypatch):
    root, shadow = tmp_path / "checked", tmp_path / "shadow"
    for base in (root, shadow):
        (base / "tools").mkdir(parents=True)
        (base / "cas_meta2").mkdir()
    values = {"tools/member.py": b"ORIGIN = 'checked-tools'\n",
              "cas_meta2/__init__.py": b"ORIGIN = 'checked-package'\n",
              "cas_meta2/member.py": b"ORIGIN = 'checked-child'\n"}
    for name, raw in values.items():
        (root / name).write_bytes(raw)
    for name in ("tools/__init__.py", "tools/member.py", "cas_meta2/__init__.py", "cas_meta2/member.py"):
        (shadow / name).write_text("raise AssertionError('SHADOW_PACKAGE_EXECUTED')\n")
    hashes = {name: sha256(raw).hexdigest() for name, raw in values.items()}
    guard = diagnostic.CheckedProjectImports(root, hashes)
    for name in list(sys.modules):
        if name == "tools" or name.startswith("tools.") or name == "cas_meta2" or name.startswith("cas_meta2."):
            monkeypatch.delitem(sys.modules, name)
    guard.reject_preloaded()
    monkeypatch.syspath_prepend(str(shadow))
    monkeypatch.setattr(sys, "meta_path", [guard, diagnostic.NoNeuralOrProviderImports(), *sys.meta_path])
    yield root, guard
    # Imports create these entries outside monkeypatch, so remove only the
    # synthetic objects this guard owns before monkeypatch restores prior state.
    for name, module in guard.executed.items():
        if sys.modules.get(name) is module:
            del sys.modules[name]


def test_regular_shadow_tools_package_cannot_override_checked_namespace(project):
    root, guard = project
    tools = importlib.import_module("tools")
    member = importlib.import_module("tools.member")
    assert list(tools.__path__) == [str(root / "tools")]
    assert getattr(tools, "__file__", None) is None
    assert member.ORIGIN == "checked-tools"
    records = guard.loaded_records()
    assert records["tools"]["kind"] == "explicit_checked_namespace"
    assert records["tools.member"]["path"] == str(root / "tools/member.py")
    assert records["tools.member"]["sha256"] == sha256((root / "tools/member.py").read_bytes()).hexdigest()


def test_shadow_cas_meta2_package_and_child_cannot_override_checked_paths(project):
    root, guard = project
    package = importlib.import_module("cas_meta2")
    child = importlib.import_module("cas_meta2.member")
    assert package.ORIGIN == "checked-package" and child.ORIGIN == "checked-child"
    assert list(package.__path__) == [str(root / "cas_meta2")]
    assert set(guard.loaded_records()) == {"cas_meta2", "cas_meta2.member"}


@pytest.mark.parametrize("name", ["tools", "tools.member", "cas_meta2", "cas_meta2.member"])
def test_preloaded_project_objects_are_rejected_even_with_plausible_file(project, name):
    root, guard = project
    module = ModuleType(name)
    module.__file__ = str(root / (name.replace(".", "/") + ".py"))
    with pytest.raises(ValueError, match="PRELOADED_PROJECT_MODULE_REFUSED"):
        guard.reject_preloaded({name: module})


@pytest.mark.parametrize("name", ["tools.unknown", "cas_meta2.unknown"])
def test_unknown_project_module_has_no_fallback(project, name):
    _, guard = project
    with pytest.raises(ValueError, match="UNPINNED_PROJECT_IMPORT_REFUSED"):
        guard.find_spec(name)


def test_changed_source_is_rejected_before_execution(project):
    root, _ = project
    (root / "tools/member.py").write_text("raise AssertionError('CHANGED_SOURCE_EXECUTED')\n")
    with pytest.raises(ValueError, match="PROJECT_IMPORT_BYTES_DIFFER_FROM_GIT"):
        importlib.import_module("tools.member")
    assert "tools.member" not in sys.modules


def test_loaded_module_replacement_is_rejected(project):
    _, guard = project
    original = importlib.import_module("tools.member")
    modules = dict(sys.modules)
    replacement = ModuleType("tools.member")
    replacement.__file__ = original.__file__
    replacement.__spec__ = original.__spec__
    modules["tools.member"] = replacement
    with pytest.raises(ValueError, match="PROJECT_MODULE_OBJECT_REPLACED"):
        guard.loaded_records(modules)


@pytest.mark.parametrize("name", ["torch", "boto3", "casformer", "cas_cjt"])
def test_neural_and_provider_imports_remain_forbidden(name):
    with pytest.raises(RuntimeError, match="DIAGNOSTIC_IMPORT_FORBIDDEN"):
        diagnostic.NoNeuralOrProviderImports().find_spec(name)


def test_failed_full_protocol_gate_is_preserved_without_running_diagnostic():
    source = Path(diagnostic.__file__).read_text()
    assert diagnostic.PACKET_HASH == "0d1b13aa711685cc488bdfdb981d8682d3d1b02b8e67530a3742add44dd13e93"
    assert diagnostic.INSPECTION_HASH == "4fb60dc51248b2c75dbd2bf2c0f278e95fc29c7612b792e6b7e82a79936fd2a9"
    assert '"full_protocol_accepted": False' in source
    assert "CAS_META_2_V2_STORED_RESULTS_CHECKED_FULL_ACCEPTANCE_BLOCKED" in source
    assert 'inspection["issues"] == [ISSUE]' in source
    assert 'stored.Extracted(' not in source
    assert 'project_imports.loaded_records()' in source
