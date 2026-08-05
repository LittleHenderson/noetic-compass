"""Regression tests for the digest-pinned container environment policy."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from types import ModuleType
from types import SimpleNamespace

import pytest

from app.runtime import container_preflight


def _hashed_lock(*pins: tuple[str, str]) -> str:
    return "\n".join(
        f"{name}=={version} \\\n    --hash=sha256:{'0' * 64}"
        for name, version in pins
    ) + "\n"


def _unified_lock(*pins: tuple[str, str]) -> str:
    runtime = [
        ("cuda-toolkit", "12.6.3"),
        ("nvidia-cudnn-cu12", "9.10.2.21"),
        ("nvidia-nccl-cu12", "2.29.3"),
        ("nvidia-nvshmem-cu12", "3.4.5"),
        ("triton", "3.7.1"),
    ]
    return (
        _hashed_lock(*pins, *runtime)
        + f"{container_preflight.EXPECTED_TORCH_REQUIREMENT} \\\n"
        + f"    --hash=sha256:{'0' * 64}\n"
    )


def _environment_kwargs(
    lock_path: Path,
    versions: dict[str, str],
    *,
    installed_names: set[str] | None = None,
    module_finder=lambda _name: None,
) -> dict:
    locked = container_preflight.read_locked_versions(lock_path)
    return {
        "python_version": container_preflight.EXPECTED_PYTHON,
        "platform_identity": container_preflight.EXPECTED_PLATFORM,
        "version_reader": versions.__getitem__,
        "installed_names_reader": lambda: (
            set(locked) if installed_names is None else installed_names
        ),
        "module_finder": module_finder,
        "torch_module": SimpleNamespace(
            version=SimpleNamespace(cuda=container_preflight.EXPECTED_CUDA)
        ),
        "expected_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "expected_locked_distributions": len(locked),
    }


def test_checked_in_lock_binds_complete_cuda_runtime() -> None:
    lock_path = Path(__file__).resolve().parents[1] / "requirements.txt"
    locked = container_preflight.read_locked_versions(lock_path)
    assert locked["transformers"] == "5.14.1"
    assert locked["torch"] == "2.13.0+cu126"
    assert locked["triton"] == "3.7.1"
    assert locked["cuda-toolkit"] == "12.6.3"
    assert locked["nvidia-cudnn-cu12"] == "9.10.2.21"


def test_environment_policy_accepts_unified_lock(
    tmp_path: Path,
) -> None:
    lock_path = tmp_path / "requirements.txt"
    lock_path.write_text(
        _unified_lock(("transformers", "5.14.1"), ("fastapi", "0.141.1")),
        encoding="utf-8",
    )
    versions = {
        "transformers": "5.14.1",
        "fastapi": "0.141.1",
        "torch": "2.13.0+cu126",
        "cuda-toolkit": "12.6.3",
        "nvidia-cudnn-cu12": "9.10.2.21",
        "nvidia-nccl-cu12": "2.29.3",
        "nvidia-nvshmem-cu12": "3.4.5",
        "triton": "3.7.1",
    }
    observed = container_preflight.verify_environment(
        lock_path,
        **_environment_kwargs(lock_path, versions),
    )
    assert observed["transformers"] == "5.14.1"
    assert observed["torch"] == "2.13.0+cu126"


@pytest.mark.parametrize(
    ("package", "bad_version"),
    [("cuda-toolkit", "13.0.3"), ("triton", "3.6.0")],
)
def test_environment_policy_rejects_wrong_runtime_closure(
    tmp_path: Path,
    package: str,
    bad_version: str,
) -> None:
    lock_path = tmp_path / "requirements.txt"
    pins = [("transformers", "5.14.1")]
    expected_version = {"cuda-toolkit": "12.6.3", "triton": "3.7.1"}[package]
    lock_text = _unified_lock(*pins).replace(
        f"{package}=={expected_version}",
        f"{package}=={bad_version}",
    )
    lock_path.write_text(lock_text, encoding="utf-8")
    versions = {
        name: version
        for name, version in container_preflight.read_locked_versions(lock_path).items()
    }
    with pytest.raises(RuntimeError, match="unified lock must bind"):
        container_preflight.verify_environment(
            lock_path,
            **_environment_kwargs(lock_path, versions),
        )


def test_lock_rejects_unapproved_direct_torch_url(tmp_path: Path) -> None:
    lock_path = tmp_path / "requirements.txt"
    lock_path.write_text(
        _unified_lock(("transformers", "5.14.1")).replace(
            "download-r2.pytorch.org", "example.invalid"
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="unapproved direct requirement"):
        container_preflight.read_locked_versions(lock_path)


def test_environment_policy_rejects_runtime_pip(tmp_path: Path) -> None:
    lock_path = tmp_path / "requirements.txt"
    lock_path.write_text(
        _unified_lock(("transformers", "5.14.1")),
        encoding="utf-8",
    )
    versions = {
        "transformers": "5.14.1",
        "torch": "2.13.0+cu126",
        "cuda-toolkit": "12.6.3",
        "nvidia-cudnn-cu12": "9.10.2.21",
        "nvidia-nccl-cu12": "2.29.3",
        "nvidia-nvshmem-cu12": "3.4.5",
        "triton": "3.7.1",
        "pip": "25.0.1",
    }

    with pytest.raises(RuntimeError, match="must not retain pip"):
        container_preflight.verify_environment(
            lock_path,
            **_environment_kwargs(
                lock_path,
                versions,
                installed_names=(set(versions) | {"pip"}),
            ),
        )


@pytest.mark.parametrize(
    "unapproved",
    [
        "evil==9.9 ; python_version >= '3.12' \\",
        "evil[extra]==9.9 \\",
        "--extra-index-url https://example.invalid/simple",
        "-r nested-requirements.txt",
    ],
)
def test_lock_rejects_every_unparsed_requirement_form(
    tmp_path: Path,
    unapproved: str,
) -> None:
    lock_path = tmp_path / "requirements.txt"
    lock_path.write_text(
        _hashed_lock(("safe", "1.0"))
        + unapproved
        + "\n"
        + f"    --hash=sha256:{'0' * 64}\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="unapproved or unparsed"):
        container_preflight.read_locked_versions(lock_path)


def test_environment_policy_rejects_lock_digest_drift(tmp_path: Path) -> None:
    lock_path = tmp_path / "requirements.txt"
    lock_path.write_text(_unified_lock(("transformers", "5.14.1")), encoding="utf-8")
    versions = container_preflight.read_locked_versions(lock_path)
    kwargs = _environment_kwargs(lock_path, versions)
    kwargs["expected_lock_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="lock SHA-256 differs"):
        container_preflight.verify_environment(lock_path, **kwargs)


def test_environment_policy_rejects_installed_distribution_drift(tmp_path: Path) -> None:
    lock_path = tmp_path / "requirements.txt"
    lock_path.write_text(_unified_lock(("transformers", "5.14.1")), encoding="utf-8")
    versions = container_preflight.read_locked_versions(lock_path)
    kwargs = _environment_kwargs(
        lock_path,
        versions,
        installed_names=(set(versions) | {"unexpected-package"}),
    )
    with pytest.raises(RuntimeError, match="installed distribution set differs"):
        container_preflight.verify_environment(lock_path, **kwargs)


def test_environment_policy_rejects_ensurepip(tmp_path: Path) -> None:
    lock_path = tmp_path / "requirements.txt"
    lock_path.write_text(_unified_lock(("transformers", "5.14.1")), encoding="utf-8")
    versions = container_preflight.read_locked_versions(lock_path)
    kwargs = _environment_kwargs(
        lock_path,
        versions,
        module_finder=lambda name: object() if name == "ensurepip" else None,
    )
    with pytest.raises(RuntimeError, match="ensurepip installer capability"):
        container_preflight.verify_environment(lock_path, **kwargs)


def test_model_cache_preflight_executes_target_contract(monkeypatch) -> None:
    from app.runtime import model_loader

    class _Tensor:
        def __init__(self, shape: tuple[int, ...]) -> None:
            self.shape = shape

    class _Truth:
        def all(self) -> "_Truth":
            return self

        def item(self) -> bool:
            return True

    class _NoGrad:
        def __enter__(self) -> None:
            return None

        def __exit__(self, *_args) -> None:
            return None

    class _Handle:
        def __init__(self, projection: "_Projection") -> None:
            self.projection = projection

        def remove(self) -> None:
            self.projection.hook = None

    class _Projection:
        def __init__(self) -> None:
            self.hook = None

        def register_forward_pre_hook(self, hook):
            self.hook = hook
            return _Handle(self)

    architecture = model_loader.PYTHIA_160M_MANIFEST.model_arch
    projection = _Projection()

    class _Model:
        config = SimpleNamespace(_attn_implementation="eager")
        gpt_neox = SimpleNamespace(
            layers=[
                SimpleNamespace(mlp=SimpleNamespace(dense_4h_to_h=projection))
            ]
        )

        def eval(self) -> None:
            return None

        def __call__(self, **kwargs):
            sequence_length = int(kwargs["input_ids"].shape[1])
            assert projection.hook is not None
            projection.hook(
                projection,
                (_Tensor((1, sequence_length, architecture.mlp_intermediate_dim)),),
            )
            attention = _Tensor(
                (1, architecture.n_heads, sequence_length, sequence_length)
            )
            return SimpleNamespace(
                attentions=[attention] * architecture.n_layers,
                logits=_Tensor((1, sequence_length, 128)),
            )

    calls: dict[str, dict] = {}
    call_order: list[str] = []

    class _Tokenizer:
        def __call__(self, _prompt: str, *, return_tensors: str):
            assert return_tensors == "pt"
            return {"input_ids": _Tensor((1, 4))}

    class _TokenizerFactory:
        @staticmethod
        def from_pretrained(_model_id: str, **kwargs):
            call_order.append("tokenizer")
            calls["tokenizer"] = kwargs
            return _Tokenizer()

    class _ModelFactory:
        @staticmethod
        def from_pretrained(_model_id: str, **kwargs):
            call_order.append("model")
            calls["model"] = kwargs
            return _Model()

    torch_module = ModuleType("torch")
    torch_module.float32 = "torch.float32"
    torch_module.no_grad = _NoGrad
    torch_module.isfinite = lambda _tensor: _Truth()
    transformers_module = ModuleType("transformers")
    transformers_module.AutoTokenizer = _TokenizerFactory
    transformers_module.AutoModelForCausalLM = _ModelFactory
    hub_module = ModuleType("huggingface_hub")
    hub_module.hf_hub_download = object()
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub_module)
    monkeypatch.setattr(model_loader, "_validated_resolved_revision", lambda _model: None)
    monkeypatch.setattr(
        model_loader,
        "_validated_model_artifacts",
        lambda _download: call_order.append("artifact_hashes"),
    )
    monkeypatch.setattr(
        model_loader,
        "_validate_model_execution_layout",
        lambda *_args, **_kwargs: call_order.append("layout"),
    )

    container_preflight.verify_model_cache()

    assert call_order[:3] == ["artifact_hashes", "tokenizer", "model"]
    assert call_order[-1] == "artifact_hashes"
    assert call_order.count("artifact_hashes") == 2
    assert calls["model"]["dtype"] == "torch.float32"
    assert calls["model"]["attn_implementation"] == "eager"
    assert calls["model"]["revision"] == model_loader.PYTHIA_160M_REVISION
    assert calls["model"]["use_safetensors"] is True
    assert calls["model"]["local_files_only"] is True
    assert calls["tokenizer"]["local_files_only"] is True


def test_native_library_closure_allows_only_exact_host_cuda_seam(
    tmp_path: Path,
) -> None:
    python_root = tmp_path / "python3.12"
    artifact = (
        python_root
        / "site-packages"
        / "torch"
        / "lib"
        / "libcaffe2_nvrtc.so"
    )
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"synthetic-elf")

    def _runner(*_args, **_kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="\tlibcuda.so.1 => not found\n",
            stderr="",
        )

    assert (
        container_preflight.verify_native_library_closure(
            python_lib_root=python_root,
            runner=_runner,
        )
        == 1
    )


def test_native_library_closure_rejects_unexpected_missing_soname(
    tmp_path: Path,
) -> None:
    python_root = tmp_path / "python3.12"
    artifact = python_root / "site-packages" / "example" / "unsafe.so"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"synthetic-elf")

    def _runner(*_args, **_kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="\tlibmystery.so.1 => not found\n",
            stderr="",
        )

    with pytest.raises(RuntimeError, match="libmystery.so.1"):
        container_preflight.verify_native_library_closure(
            python_lib_root=python_root,
            runner=_runner,
        )


def test_native_library_closure_rejects_pruned_cluster_plugin(
    tmp_path: Path,
) -> None:
    python_root = tmp_path / "python3.12"
    plugin = (
        python_root
        / "site-packages"
        / container_preflight.PRUNED_OPTIONAL_NATIVE_ARTIFACTS[0]
    )
    plugin.parent.mkdir(parents=True)
    plugin.write_bytes(b"synthetic-cluster-plugin")

    with pytest.raises(RuntimeError, match="cluster/RDMA plugin remains"):
        container_preflight.verify_native_library_closure(
            python_lib_root=python_root,
            runner=lambda *_args, **_kwargs: None,
        )
