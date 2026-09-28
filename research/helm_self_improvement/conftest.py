"""Fixtures run only within a separately admitted AWS acceptance job."""
from dataclasses import asdict
import os
from pathlib import Path
import tempfile
from uuid import uuid4

import pytest

from .admission import (BRANCH, HARNESS_FILES, MANIFEST_SHA, ROOT, RUNTIME_SHA, SOURCE_SHA,
                        TrustedHost, file_hash, write_new)
from .contracts import HarnessConfig, SelfDescription
from .native_bridge import run_baseline


def pytest_configure(config):
    if os.environ.get("HELM_SI_EXECUTION_VENUE") != "ADMITTED_AWS":
        raise pytest.UsageError("AWS_EXECUTION_REQUIRED: use the newly admitted job, never the historical failing freeze")
    if config.option.basetemp is None:
        config.option.basetemp = str(Path(tempfile.gettempdir()) / ("helm-si-" + uuid4().hex))


def host_for(directory, baseline=False):
    """Test host is the authority; this helper is never exposed to candidate data."""
    directory.mkdir(parents=True, exist_ok=True)
    policy = {"schema": "helm.si.host-admission/1", "source_sha": SOURCE_SHA, "runtime_sha": RUNTIME_SHA,
              "manifest_sha256": MANIFEST_SHA, "branch": BRANCH, "checkpoint_sha256": None,
              "harness_files": {name: file_hash(ROOT / "research/helm_self_improvement" / name) for name in HARNESS_FILES},
              "baseline_config": asdict(HarnessConfig(baseline)),
              "source_anchor_kind": "OPERATOR_VERIFIED_ALLOWLISTED_ORIGINAL_GIT_BYTES",
              "source_anchor_ref": SOURCE_SHA, "host_step_limit": 32,
              "candidate_access": "TYPED_PUBLIC_DATA_ONLY_NO_FILES_OR_EXECUTION"}
    path = directory / "admission.json"
    write_new(path, policy)
    return TrustedHost(path, file_hash(path), directory / "host-evidence")


@pytest.fixture(scope="module")
def admitted_case(tmp_path_factory):
    host = host_for(tmp_path_factory.mktemp("admitted"))
    baseline, observation = run_baseline(host)
    return host, SelfDescription(host.parent, host.baseline_config), baseline, observation
