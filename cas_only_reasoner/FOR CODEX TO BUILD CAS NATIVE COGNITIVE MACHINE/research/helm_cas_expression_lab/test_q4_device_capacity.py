"""Deterministic capacity checks only; no CUDA, hardware query, or worker launch."""
from copy import deepcopy
from types import SimpleNamespace
import subprocess

import pytest

import q4_device_capacity as capacity

UUID = "GPU-7cfee18b-e83d-b6fb-a946-ae444b329fdd"


def csv_row(**changes):
    fields = {"index": "0", "uuid": UUID, "driver": "WDDM", "display": "Enabled",
              "total": "8188", "free": "7333", "used": "616", "util": "0", "temp": "63"}
    fields.update(changes)
    return ", ".join(fields.values()) + "\n"


def xml_inventory(kind="C+G", **changes):
    fields = {"uuid": UUID, "driver": "WDDM", "attached": "Yes",
              "active": "Enabled", "count": "1", "pid": "2536"}
    fields.update(changes)
    processes = ("None" if kind is None else
        f"<process_info><pid>{fields['pid']}</pid><type>{kind}</type>"
        "<process_name></process_name><used_memory>N/A</used_memory></process_info>")
    return (f"<nvidia_smi_log><attached_gpus>{fields['count']}</attached_gpus><gpu>"
            f"<uuid>{fields['uuid']}</uuid><driver_model><current_dm>{fields['driver']}"
            f"</current_dm></driver_model><display_attached>{fields['attached']}"
            f"</display_attached><display_active>{fields['active']}</display_active>"
            f"<processes>{processes}</processes></gpu></nvidia_smi_log>")


@pytest.fixture
def policy(monkeypatch):
    monkeypatch.setattr(capacity.platform, "system", lambda: "Windows")
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    return capacity.shared_display_policy(UUID)


@pytest.fixture
def telemetry(monkeypatch):
    calls, sleeps = [], []
    def query(arguments):
        calls.append(arguments)
        return xml_inventory() if arguments == ["-q", "-x"] else csv_row()
    monkeypatch.setattr(capacity, "_query", query)
    monkeypatch.setattr(capacity.time, "sleep", sleeps.append)
    return calls, sleeps


def test_shared_contexts_and_raw_metadata_are_retained(policy, telemetry):
    calls, sleeps = telemetry
    receipt = capacity.check_prelaunch(policy, "cuda:0")
    assert receipt["exclusive_idle"] is False
    assert receipt["admission"] == "SHARED_DISPLAY_CAPACITY_ACCEPTED"
    assert len(receipt["samples"]) == 3 and len(calls) == 6
    assert sleeps == [1, 1]
    for sample in receipt["samples"]:
        assert sample["telemetry"]["raw_csv"] == csv_row()
        assert sample["inventory"]["raw_xml"] == xml_inventory()
        assert sample["inventory"]["contexts"][0] == {
            "pid": 2536, "type": "C+G", "process_name": None, "used_memory": "N/A"}
    assert capacity.validate_policy(policy) == policy


@pytest.mark.parametrize("key,value", [
    ("max_start_utilization_percent", 11), ("min_start_free_mib", 4095),
    ("max_start_temperature_c", 76), ("stop_temperature_c", 81),
    ("prelaunch_samples", True), ("sample_interval_seconds", 0),
    ("running_check_interval_seconds", 3), ("query_timeout_seconds", 11),
    ("allowed_prelaunch_context_types", ["G", "C+G", "C"]),
    ("mode", "IDLE"), ("physical_gpu_count", 2)])
def test_changed_policy_fails_closed(policy, key, value):
    policy[key] = value
    with pytest.raises(capacity.CapacityError, match="POLICY_INVALID"):
        capacity.validate_policy(policy)


@pytest.mark.parametrize("policy_value", [None, [], {}, {"expected_gpu_uuid": UUID}])
def test_incomplete_policy_is_refused(policy_value):
    with pytest.raises(capacity.CapacityError, match="POLICY_INVALID"):
        capacity.validate_policy(policy_value)


@pytest.mark.parametrize("uuid", ["", "GPU-unknown", UUID.upper(), 123, None])
def test_exact_uuid_required(uuid):
    with pytest.raises(capacity.CapacityError, match="UUID"):
        capacity.shared_display_policy(uuid)


@pytest.mark.parametrize("setting", ["other_host", "other_device", "mapping"])
def test_unsupported_host_device_or_remap(policy, telemetry, monkeypatch, setting):
    if setting == "other_host":
        monkeypatch.setattr(capacity.platform, "system", lambda: "Linux")
    if setting == "mapping":
        monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    with pytest.raises(capacity.CapacityError):
        capacity.check_prelaunch(policy, "cuda:1" if setting == "other_device" else "cuda:0")
    assert telemetry[0] == []


@pytest.mark.parametrize("changes", [
    {"index": "1"}, {"uuid": UUID.replace("407", "408") + "x"},
    {"driver": "TCC"}, {"display": "Disabled"},
    {"free": "NaN"}, {"used": "Infinity"}, {"temp": "-1"},
    {"util": "101"}, {"total": "0"}, {"free": "99999"},
    {"used": "8188"}, {"temp": "63.5"}, {"util": "[N/A]"}])
def test_invalid_or_changed_metadata_is_refused(policy, changes):
    with pytest.raises(capacity.CapacityError):
        capacity._parse_telemetry(csv_row(**changes), policy)


@pytest.mark.parametrize("raw", ["", csv_row() + csv_row(), "0,one,two\n", '"bad'])
def test_malformed_or_multiple_gpu_csv_is_refused(policy, raw):
    with pytest.raises(capacity.CapacityError):
        capacity._parse_telemetry(raw, policy)


@pytest.mark.parametrize("kind", ["C", "M", "M+C", "O", "", "N/A"])
def test_compute_only_and_unknown_contexts_refused(policy, kind):
    with pytest.raises(capacity.CapacityError, match="COMPETING_CONTEXT"):
        capacity._parse_inventory(xml_inventory(kind), policy)


@pytest.mark.parametrize("kind", ["G", "C+G", None])
def test_explicitly_shared_or_empty_inventory_is_readable(policy, kind):
    parsed = capacity._parse_inventory(xml_inventory(kind), policy)
    assert len(parsed["contexts"]) == (0 if kind is None else 1)


@pytest.mark.parametrize("changes", [
    {"uuid": UUID + "x"}, {"driver": "TCC"}, {"attached": "No"},
    {"active": "Disabled"}, {"count": "2"}, {"pid": ""}, {"pid": "0"}])
def test_changed_inventory_identity_or_missing_pid_refused(policy, changes):
    with pytest.raises(capacity.CapacityError):
        capacity._parse_inventory(xml_inventory(**changes), policy)


@pytest.mark.parametrize("mutation", ["missing", "blank", "duplicate", "entity", "broken"])
def test_malformed_inventory_fails_closed(policy, mutation):
    raw = xml_inventory()
    if mutation == "missing":
        raw = raw.replace("<processes>", "<other>").replace("</processes>", "</other>")
    elif mutation == "blank":
        raw = xml_inventory(None).replace("None", "")
    elif mutation == "duplicate":
        fragment = raw[raw.index("<process_info>"):raw.index("</process_info>") + 15]
        raw = raw.replace("</processes>", fragment + "</processes>")
    elif mutation == "entity":
        raw = '<!DOCTYPE foo [<!ENTITY a "bad">]>' + raw
    else:
        raw = "<broken"
    with pytest.raises(capacity.CapacityError):
        capacity._parse_inventory(raw, policy)


@pytest.mark.parametrize("changes,accepted", [
    ({"free": "4096", "used": "1000", "util": "10", "temp": "75"}, True),
    ({"free": "4095", "used": "1000"}, False),
    ({"util": "11"}, False), ({"temp": "76"}, False)])
def test_prelaunch_threshold_boundaries(policy, monkeypatch, telemetry, changes, accepted):
    monkeypatch.setattr(capacity, "_query", lambda args:
        xml_inventory() if args == ["-q", "-x"] else csv_row(**changes))
    if accepted:
        assert len(capacity.check_prelaunch(policy, "cuda:0")["samples"]) == 3
    else:
        with pytest.raises(capacity.CapacityError):
            capacity.check_prelaunch(policy, "cuda:0")


def test_later_prelaunch_sample_failure_refuses_admission(policy, monkeypatch, telemetry):
    readings = iter([csv_row(), xml_inventory(), csv_row(temp="76"), xml_inventory()])
    monkeypatch.setattr(capacity, "_query", lambda _: next(readings))
    with pytest.raises(capacity.CapacityError, match="TOO_WARM"):
        capacity.check_prelaunch(policy, "cuda:0")


@pytest.mark.parametrize("temperature,accepted", [("79", True), ("80", False), ("81", False)])
def test_running_thermal_stop_boundary(policy, monkeypatch, temperature, accepted):
    # High utilization and low free memory may belong to our own worker.
    monkeypatch.setattr(capacity, "_query", lambda _: csv_row(
        free="100", used="7800", util="100", temp=temperature))
    if accepted:
        assert capacity.check_running(policy, "cuda:0")["temperature_c"] == 79
    else:
        with pytest.raises(capacity.CapacityError, match="THERMAL_STOP"):
            capacity.check_running(policy, "cuda:0")


@pytest.mark.parametrize("changes", [{"uuid": UUID + "x"}, {"driver": "TCC"},
                                     {"temp": "N/A"}, {"display": "Disabled"}])
def test_running_identity_or_telemetry_loss_refused(policy, monkeypatch, changes):
    monkeypatch.setattr(capacity, "_query", lambda _: csv_row(**changes))
    with pytest.raises(capacity.CapacityError):
        capacity.check_running(policy, "cuda:0")


@pytest.mark.parametrize("failure", ["exit", "empty", "oversized", "timeout", "missing"])
def test_query_failures_and_bounded_timeout(monkeypatch, failure):
    seen = []
    def run(command, **kwargs):
        seen.append((command, kwargs))
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if failure == "missing":
            raise FileNotFoundError("nvidia-smi")
        return SimpleNamespace(returncode=1 if failure == "exit" else 0,
            stdout="" if failure == "empty" else "x" * (capacity._MAX_QUERY_BYTES + 1))
    monkeypatch.setattr(capacity.subprocess, "run", run)
    with pytest.raises(capacity.CapacityError, match="UNAVAILABLE"):
        capacity._query(["-q", "-x"])
    assert seen[0][0] == ["nvidia-smi", "-q", "-x"]
    assert seen[0][1]["timeout"] == 10
    assert seen[0][1]["capture_output"] is True

