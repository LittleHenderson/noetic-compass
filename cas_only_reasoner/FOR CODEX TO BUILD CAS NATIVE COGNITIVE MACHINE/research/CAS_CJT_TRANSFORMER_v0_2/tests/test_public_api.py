from __future__ import annotations

from copy import deepcopy
from importlib import resources
import inspect
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator


# The v0.2 source tree consumes the frozen sibling package.  Installed users
# receive it from the package dependency declared in pyproject.toml.
CASFORMER_ROOT = Path(__file__).resolve().parents[2] / "CASFORMER_v0_1"
sys.path.insert(0, str(CASFORMER_ROOT))

import cas_cjt
from cas_cjt import (
    BiasState,
    CASOhmRouter,
    CausePacket,
    IndependentVerifier,
    NetworkAtomicCoordinator,
    NeuralCJT,
    NeuralCJTNetwork,
    NeuralCJTRuntime,
    ProposalOnlyCNCMBridge,
    PublishedEffect,
    SQLiteAtomicStore,
    make_initial_bias,
)


H0 = "0" * 64


def _parameter_names(value: object) -> tuple[str, ...]:
    return tuple(inspect.signature(value).parameters)


def test_version_and_declared_public_surface_are_stable() -> None:
    assert cas_cjt.__version__ == "0.2.0"
    assert cas_cjt.__all__[0] == "__version__"
    assert len(cas_cjt.__all__) == len(set(cas_cjt.__all__))
    assert not any(name.startswith("_") for name in cas_cjt.__all__[1:])

    expected = {
        "CausePacket",
        "BiasState",
        "PublishedEffect",
        "NeuralCJT",
        "NeuralCJTNetwork",
        "CASOhmRouter",
        "IndependentVerifier",
        "SQLiteAtomicStore",
        "NetworkAtomicCoordinator",
        "NeuralCJTRuntime",
        "ProposalOnlyCNCMBridge",
    }
    assert expected <= set(cas_cjt.__all__)
    legacy_single_bias_harness = {
        "PROPOSE_STATE_UPDATE",
        "PROPOSE_MODEL_UPDATE",
        "PROPOSE_MEMORY_WRITE",
        "REQUEST_EFFECT_PUBLICATION",
        "AtomicCoordinator",
        "BatchRejected",
        "CommitBatch",
        "CoordinatorError",
        "RecoverySnapshot",
        "RollbackRequest",
    }
    assert legacy_single_bias_harness.isdisjoint(cas_cjt.__all__)
    assert all(not hasattr(cas_cjt, name) for name in legacy_single_bias_harness)
    assert all(getattr(cas_cjt, name) is not None for name in cas_cjt.__all__)


def test_top_level_exports_are_the_objects_owned_by_their_modules() -> None:
    from cas_cjt.cncm_bridge import ProposalOnlyCNCMBridge as BridgeOwner
    from cas_cjt.network import NeuralCJTNetwork as NetworkOwner
    from cas_cjt.network_coordinator import (
        NetworkAtomicCoordinator as CoordinatorOwner,
    )
    from cas_cjt.neural import NeuralCJT as NeuralOwner
    from cas_cjt.persistence import SQLiteAtomicStore as StoreOwner
    from cas_cjt.routing import CASOhmRouter as RouterOwner
    from cas_cjt.runtime import NeuralCJTRuntime as RuntimeOwner
    from cas_cjt.types import BiasState as BiasOwner
    from cas_cjt.types import CausePacket as CauseOwner
    from cas_cjt.types import PublishedEffect as EffectOwner
    from cas_cjt.verifier import IndependentVerifier as VerifierOwner

    assert BiasState is BiasOwner
    assert CausePacket is CauseOwner
    assert PublishedEffect is EffectOwner
    assert NeuralCJT is NeuralOwner
    assert NeuralCJTNetwork is NetworkOwner
    assert CASOhmRouter is RouterOwner
    assert IndependentVerifier is VerifierOwner
    assert SQLiteAtomicStore is StoreOwner
    assert NetworkAtomicCoordinator is CoordinatorOwner
    assert NeuralCJTRuntime is RuntimeOwner
    assert ProposalOnlyCNCMBridge is BridgeOwner


def test_documented_entry_point_signatures_are_visible_at_package_root() -> None:
    assert _parameter_names(NeuralCJT.forward) == (
        "self",
        "x",
        "control",
        "operation_id",
    )
    assert inspect.signature(NeuralCJT.forward).parameters[
        "operation_id"
    ].kind is inspect.Parameter.KEYWORD_ONLY
    assert _parameter_names(CASOhmRouter.route) == ("self", "inputs")
    assert _parameter_names(IndependentVerifier.evaluate) == (
        "self",
        "cause",
        "candidate",
        "operation_contract",
        "evidence",
        "bias",
        "operating_region",
    )
    assert _parameter_names(NetworkAtomicCoordinator.commit) == (
        "self",
        "batch",
        "fault_at",
    )
    assert _parameter_names(NeuralCJTRuntime.create) == (
        "path",
        "config",
        "node_specs",
        "topology",
        "seed",
        "labels",
        "model_id",
    )
    assert _parameter_names(NeuralCJTRuntime.open) == (
        "path",
        "config",
        "node_specs",
        "topology",
        "labels",
    )
    assert _parameter_names(NeuralCJTRuntime.inference_tick) == (
        "self",
        "cause",
        "cjt_id",
        "expected_symbol",
        "opposite_symbol",
        "settings",
        "supplied_artifacts",
        "resume_repair_id",
        "write_memory",
    )
    assert _parameter_names(NeuralCJTRuntime.learning_tick) == (
        "self",
        "cause",
        "cjt_id",
        "expected_symbol",
        "loss_fn",
        "score_fn",
        "opposite_symbol",
        "settings",
        "supplied_artifacts",
        "allowed_parameter_names",
        "parameter_group_ids",
        "policy",
        "regression_passed",
        "resume_repair_id",
        "write_memory",
    )
    assert _parameter_names(ProposalOnlyCNCMBridge.translate) == (
        "self",
        "published_effect",
        "store",
    )


def test_lightweight_package_import_does_not_require_casformer() -> None:
    package_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import cas_cjt, sys; "
                "from cas_cjt import BiasState; "
                "assert cas_cjt.__version__ == '0.2.0'; "
                "assert 'casformer' not in sys.modules"
            ),
        ],
        cwd=package_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_standalone_bias_state_schema_is_strict_and_self_contained() -> None:
    schema_resource = resources.files("cas_cjt").joinpath(
        "schemas", "bias_state.schema.json"
    )
    schema = json.loads(schema_resource.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    checkpoint = cas_cjt.TensorArtifactRef(
        artifact_id="checkpoint-root",
        sha256=H0,
        dtype="model-checkpoint",
        shape=(1,),
        encoding="cas-model-checkpoint-v1",
        byte_length=1,
    )
    bias = make_initial_bias(
        cjt_id="cjt-public-api",
        operation_id="^6",
        model_id="model-public-api",
        model_digest=H0,
        checkpoint_ref=checkpoint,
    )
    assert not tuple(validator.iter_errors(bias.to_dict()))

    unknown_field = deepcopy(bias.to_dict())
    unknown_field["uncontracted"] = True
    assert tuple(validator.iter_errors(unknown_field))

    broken_compartment = deepcopy(bias.to_dict())
    del broken_compartment["rpm"]["readiness"]["wisdom"]
    assert tuple(validator.iter_errors(broken_compartment))
