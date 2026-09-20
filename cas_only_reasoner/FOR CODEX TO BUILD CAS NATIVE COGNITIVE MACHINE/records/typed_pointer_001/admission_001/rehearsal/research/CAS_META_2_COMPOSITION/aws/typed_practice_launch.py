"""One practice-study job through the bounded AWS lifecycle (owner-approved 2026-09-18, "Practice test").

Reuses the matched study's proven launcher (`typed_matched_launch`) and changes only what this study
needs: its own worker, schemas and job names; a 4-hour instance envelope instead of 2 hours; and a
$15.00 reservation instead of $7.00 (4 h x $2.52 + $1.48 ancillary = $11.56, rounded up; owner cap
$45.00 for the three jobs). The shared lifecycle modules are not modified: this module overrides the
provider's reservation, wait and guest-watchdog methods instead.

Source/package admission is pure. Only explicit execute enters provider code.
"""
from __future__ import annotations

import ast
import io
import json
from pathlib import Path
import re
import sys
import time
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
for root in (ROOT, PROJECT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
from aws import typed_matched_launch as matched
from aws import graph_training_candidate_launch as lifecycle
from aws import graph_training_curriculum_launch as shared
from aws import recurrent_cjt_launch as worker_template
from aws import run_evidence, budget
from cas_meta2.typed_teaching import practice_contract as contract

require, canonical, digest = shared.require, shared.canonical, shared.digest
CANDIDATE = contract.CANDIDATE
CONFIG_SCHEMA = contract.CONFIG_SCHEMA
RESULT_SCHEMA = "cncm.typed-practice-worker-result/0.1"
FAILURE_SCHEMA = "cncm.typed-practice-failure/0.1"
REQUEST_SCHEMA = "cncm.typed-practice-request/0.1"
AUTHORITY_SCHEMA = "cncm.typed-practice-authority/0.1"
OWNER_SCHEMA = "cncm.typed-practice-owner/0.1"
WORKER_NAME = "typed_practice_worker.py"
JOB_PATTERN = contract.JOB_PATTERN
MAX_WALL_SECONDS = contract.MAX_WALL_SECONDS            # numeric child timeout, 12,600 s
OUTER_TIMEOUT_SECONDS = 13500                           # setup + worker + publication
BOOT_WATCHDOG_SECONDS = 14100                           # guest-owned poweroff, never cancelled
INSTANCE_SECONDS_MAX = contract.INSTANCE_SECONDS_MAX    # launcher wait budget, 14,400 s
RESERVATION_USD = contract.RESERVATION_USD              # "15.00"
# 1,470 main + 16 interference + 2 validation replays. Pinned by a test against the schedule.
OPTIMIZER_UPDATES_MAX = 1488
# Provider errors that mean "try again", not "the job failed". Anything else still ends the wait.
TRANSIENT_ERROR_CODES = frozenset({"Throttling", "ThrottlingException", "RequestLimitExceeded", "SlowDown",
    "RequestTimeout", "RequestTimeoutException", "InternalError", "InternalFailure", "ServiceUnavailable",
    "Unavailable", "500", "502", "503", "504",
    # A sleeping laptop wakes with a skewed clock or expired request signatures; the next poll re-signs.
    "RequestTimeTooSkewed", "RequestExpired"})
# Only network-level SDK failures are transient. Credential, parameter or profile errors are not: retrying
# them for four hours would only hide the failure (second pre-flight review, 2026-09-18).
TRANSIENT_ERROR_CLASSES = frozenset({"EndpointConnectionError", "ConnectTimeoutError", "ReadTimeoutError",
    "ConnectionClosedError", "ResponseStreamingError", "IncompleteReadError", "ProxyConnectionError",
    "ConnectionError", "HTTPClientError"})
MAX_TRANSIENT_WAIT_ERRORS = 500
EXPERIMENT = {"profile": "typed_practice_v1", "candidate": CANDIDATE, "entrypoint": "cncm.typed_practice_worker.run"}
BOUNDS = {"training": True, "optimizer_updates_max": OPTIMIZER_UPDATES_MAX, "max_wall_seconds": MAX_WALL_SECONDS,
          "jobs": 1, "automatic_retries": 0, "reservation_usd": RESERVATION_USD,
          "instance_type": "g7.2xlarge", "region": "us-west-2", "instance_seconds_max": INSTANCE_SECONDS_MAX}
DESIGN = json.loads(canonical(contract.DESIGN))
CANONICAL_LEDGER = matched.CANONICAL_LEDGER
PACKAGING_SOURCES = tuple("aws/" + name + ".py" for name in (
    "typed_practice_launch", "typed_matched_launch", "recurrent_cjt_launch", "graph_training_candidate_launch",
    "graph_training_curriculum_launch", "run_evidence", "budget", "__init__"))
require(shared.RESOURCE_PLAN["instance_seconds_max"] < BOOT_WATCHDOG_SECONDS < INSTANCE_SECONDS_MAX
        and contract.WORKER_DEADLINE_SECONDS < MAX_WALL_SECONDS < OUTER_TIMEOUT_SECONDS < BOOT_WATCHDOG_SECONDS,
        "PRACTICE_TIME_ORDER")


def _probe():
    import importlib
    probe = importlib.import_module("cncm.typed_practice_worker")
    for name in ("CANDIDATE", "CONFIG_SCHEMA", "RESULT_SCHEMA", "FAILURE_SCHEMA"):
        require(getattr(probe, name) == globals()[name], "PRACTICE_PROBE_CONTRACT:" + name)
    return probe


def frozen_inputs():
    return contract.input_inventory(PROJECT)


def frozen_inputs_hash():
    return digest(canonical(frozen_inputs()))


def worker_config(job, *, source_sha):
    _, model_seed = contract.parse_job(job)
    return contract.make_config(PROJECT, source_sha=source_sha, job=job, model_seed=model_seed,
                                bucket=job + "-" + shared.RESOURCE_PLAN["account"])


def validate_request(request):
    require(type(request) is dict and set(request) == {"schema", "job", "source_sha", "archive_sha256",
                                                       "manifest_sha256", "launch_authorized"}, "PRACTICE_REQUEST_FIELDS")
    require(request["schema"] == REQUEST_SCHEMA, "PRACTICE_REQUEST_SCHEMA")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]), "PRACTICE_REQUEST_JOB")
    for key, pattern in (("source_sha", shared.HEX40), ("archive_sha256", shared.HEX64), ("manifest_sha256", shared.HEX64)):
        require(type(request[key]) is str and pattern.fullmatch(request[key]), "PRACTICE_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "PRACTICE_REQUEST_INERT")
    return request


def _check_bounds(document, code):
    for key, expected in BOUNDS.items():
        require(type(document.get(key)) is type(expected) and document[key] == expected, code + ":" + key)


def validate_authority(authority):
    identity = {"job", "source_sha", "archive_sha256", "manifest_sha256"}
    fields = identity | set(BOUNDS) | {"schema", "candidate", "owner_authorization_sha256", "inputs_sha256",
                                       "design_sha256", "evidence_contract_sha256", "worker_config"}
    require(type(authority) is dict and set(authority) == fields, "PRACTICE_AUTHORITY_FIELDS")
    require(authority["schema"] == AUTHORITY_SCHEMA and authority["candidate"] == CANDIDATE, "PRACTICE_AUTHORITY_CANDIDATE")
    validate_request({**{key: authority[key] for key in identity}, "schema": REQUEST_SCHEMA, "launch_authorized": False})
    require(type(authority["owner_authorization_sha256"]) is str
            and shared.HEX64.fullmatch(authority["owner_authorization_sha256"]), "PRACTICE_OWNER_HASH")
    _check_bounds(authority, "PRACTICE_AUTHORITY_BOUND")
    for key, expected in (("inputs_sha256", frozen_inputs_hash()), ("design_sha256", digest(canonical(DESIGN))),
                          ("evidence_contract_sha256", run_evidence.contract_digest(evidence_contract()))):
        require(authority[key] == expected, "PRACTICE_AUTHORITY_BINDING:" + key)
    expected = worker_config(authority["job"], source_sha=authority["source_sha"])
    require(type(authority["worker_config"]) is dict and canonical(authority["worker_config"]) == canonical(expected),
            "PRACTICE_AUTHORITY_CONFIG")
    return authority


def validate_owner(path, authority):
    raw = Path(path).read_bytes()
    require(digest(raw) == authority["owner_authorization_sha256"], "PRACTICE_OWNER_FILE_HASH")
    record = json.loads(raw)
    require(type(record) is dict and record.get("schema") == OWNER_SCHEMA and record.get("candidate") == CANDIDATE,
            "PRACTICE_OWNER_SCOPE")
    quote = record.get("owner_instruction_raw")
    require(type(quote) is str and bool(quote.strip()), "PRACTICE_OWNER_QUOTE")
    require(record.get("job") == authority["job"], "PRACTICE_OWNER_JOB")
    require(type(record.get("bounds")) is dict, "PRACTICE_OWNER_BOUNDS")
    _check_bounds(record["bounds"], "PRACTICE_OWNER_BOUND")
    return record


def validate_ledger_path(value):
    return matched.validate_ledger_path(value)


def bootstrap_source():
    source = matched.bootstrap_source()
    require(source.count("typed_matched_worker") == 2, "PRACTICE_BOOTSTRAP_TEMPLATE_CHANGED")
    return source.replace("typed_matched_worker", "typed_practice_worker")


def render_worker():
    tree = ast.parse(worker_template.render_worker())
    replacements = {"INNER_RUNNER": bootstrap_source(), "RESULT_SCHEMA": RESULT_SCHEMA,
                    "FAILURE_SCHEMA": FAILURE_SCHEMA, "MAX_WALL_SECONDS": MAX_WALL_SECONDS}
    found, timeouts, regions = set(), 0, 0
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in replacements:
                node.value = ast.Constant(replacements[name]); found.add(name)
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "timeout" and ast.unparse(node.value) == "MAX_WALL_SECONDS + 1800":
            node.value = ast.Name(id="MAX_WALL_SECONDS", ctx=ast.Load()); timeouts += 1
        if isinstance(node, ast.Subscript) and ast.unparse(node) == "config['region']":
            node.value = ast.Subscript(value=ast.Name(id="config", ctx=ast.Load()), slice=ast.Constant("design"),
                                       ctx=ast.Load()); regions += 1
    require(found == set(replacements) and timeouts == 1 and regions == 1, "PRACTICE_WORKER_TEMPLATE_CHANGED")
    tree.body[0] = ast.Expr(ast.Constant(CANDIDATE + ": ten-pass practice with held-back questions; "
                                         "no learning claim is made by the worker."))
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def evidence_contract():
    names = {"results/result.json": "terminal envelope", "results/result.json.sha256": "envelope digest",
             "results/artifacts/manifest.json": "artifact inventory"}
    names.update({"results/artifacts/" + name: "complete typed-practice worker evidence"
                  for name in _probe().EXPECTED_ARTIFACTS})
    return run_evidence.contract(EXPERIMENT["profile"], [
        run_evidence.requirement(key, title, kind="json" if key.endswith(".json") else "file")
        for key, title in names.items()], notes=[
            "Ten passes: 1470 main, 16 interference and 2 validation replay updates, 1488 actual total.",
            "Five held worlds never enter a training batch; all declared checkpoints must arrive.",
            "One seed only; the three-seed gate reading is a separate deterministic program."])


def package_data_files():
    return tuple(sorted(set(shared.PILOT + name for name in PACKAGING_SOURCES)
                        | {shared.WORKER_REQUIREMENTS} | {item["path"] for item in frozen_inputs()}))


def git_package_bytes(root, commit, name):
    require(type(commit) is str and shared.HEX40.fullmatch(commit), "PRACTICE_SOURCE_COMMIT")
    shared.checked_names([name])
    permitted = (name.startswith("research/") or name in contract.MATERIAL
                 or (name.startswith("cncm/") and name.endswith(".py")))
    require(permitted, "PRACTICE_SOURCE_MEMBER_SCOPE")
    return shared._run_git(["-c", "core.autocrlf=false", "show", commit + ":" + shared.GIT_PREFIX + name], root)


def build_practice_package(output, *, source_sha, git_bytes_fn=None):
    """Exact committed member allowlist, as the matched package; this study's worker and manifest."""
    output = Path(output).absolute()
    require(not output.exists() and output.parent.is_dir() and output.is_relative_to(ROOT / "records")
            and output != ROOT / "records", "PRACTICE_FRESH_PACKAGE_PATH")
    require(type(source_sha) is str and shared.HEX40.fullmatch(source_sha), "PRACTICE_SOURCE_COMMIT")
    get_bytes = git_bytes_fn or git_package_bytes
    rows = frozen_inputs()
    names = package_data_files()
    shared.checked_names(list(names))
    members = {name: get_bytes(ROOT, source_sha, name) for name in names}
    for name in PACKAGING_SOURCES + ("requirements-gpu.txt",):
        require(members[shared.PILOT + name] == (ROOT / name).read_bytes(), "PRACTICE_PACKAGING_SOURCE_NOT_COMMITTED:" + name)
    for row in rows:
        raw = members[row["path"]]
        require(len(raw) == row["bytes"] and digest(raw) == row["sha256"], "PRACTICE_INPUT_NOT_COMMITTED:" + row["path"])
    source = render_worker()
    transport = run_evidence.unified_transport(source)
    members[WORKER_NAME] = run_evidence.unified_worker_source(source).encode("utf-8")
    require(all(len(raw) <= shared.MAX_MEMBER_BYTES for raw in members.values()), "PRACTICE_MEMBER_BOUND")
    manifest = shared.manifest_for(members, source_sha, worker_name=WORKER_NAME, experiment=EXPERIMENT,
                                   package_schema="cncm.typed-practice-package/0.1", design=DESIGN)
    manifest["frozen_budget"] = {**BOUNDS, "main_updates": OPTIMIZER_UPDATES_MAX - 18, "interference_updates": 16,
                                 "validation_replay_updates": 2}
    manifest["typed_design"] = DESIGN
    manifest["inputs"] = rows
    manifest["inputs_sha256"] = digest(canonical(rows))
    manifest["transport"] = {"implementation": "aws.run_evidence.render_transport",
        "replaced_functions": transport["replaced"], "publisher_wired": transport["publisher_wired"],
        "marker_last": True, "predeclared_contract_sha256": run_evidence.contract_digest(evidence_contract())}
    members[shared.MANIFEST_NAME] = canonical(manifest)
    require(len(members) <= shared.MAX_MEMBER_COUNT and all(len(raw) <= shared.MAX_MEMBER_BYTES for raw in members.values())
            and sum(map(len, members.values())) <= shared.MAX_EXPANDED_BYTES, "PRACTICE_PACKAGE_BOUND")
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, raw in sorted(members.items()):
            info = ZipInfo(name, date_time=(2026, 9, 18, 0, 0, 0))
            info.compress_type, info.external_attr = ZIP_DEFLATED, 0o100644 << 16
            archive.writestr(info, raw)
    raw = buffer.getvalue()
    require(len(raw) <= shared.MAX_ARCHIVE_BYTES, "PRACTICE_ARCHIVE_BOUND")
    output.mkdir()
    (output / "source.zip").write_bytes(raw)
    receipt = {"schema": "cncm.typed-practice-package-receipt/0.1", "status": "SOURCE_ONLY_NO_LAUNCH",
               "source_sha": source_sha, "archive": str(output / "source.zip"), "archive_sha256": digest(raw),
               "archive_bytes": len(raw), "manifest_sha256": digest(members[shared.MANIFEST_NAME]),
               "member_count": len(members), "manifest": manifest}
    (output / "receipt.json").write_bytes(canonical(receipt))
    return receipt


def reservation_plan_for(design):
    plan = shared.reservation_plan()
    plan["runtime_seconds_max"] = INSTANCE_SECONDS_MAX
    plan["task_scope"] = "cncm_typed_practice_001"
    plan["frozen_budget"] = json.loads(canonical(design))
    return plan


class TypedPracticeProvider(matched.TypedMatchedProvider):
    def reservation_plan(self):
        require(hasattr(self, "bound_config"), "PRACTICE_RESERVATION_CONFIG_REQUIRED")
        return reservation_plan_for(self.bound_config["design"])

    def reserve(self, amount):
        """The inherited lifecycle passes its own $7.00 constant; this study's frozen amount is $15.00."""
        require(hasattr(self, "bound_config"), "PRACTICE_RESERVATION_CONFIG_REQUIRED")
        require(not self._reserved and amount == shared.RESERVATION_USD, "PRACTICE_RESERVATION_CALLER")
        self.calls.append("reserve")
        self._event("budget_reservation", "REQUESTED", amount=RESERVATION_USD)
        receipt = self.budget.reserve_budget(self.job, self.source_sha, self.archive_sha256, RESERVATION_USD,
                                             self.reservation_plan(), self.ledger_path)
        self._reserved = True
        return {**receipt, "aws_side_reservation": self._record_aws_side_reservation(receipt)}

    def _transient(self, error):
        if isinstance(error, self._client_error):
            return self._error_code(error) in TRANSIENT_ERROR_CODES
        if isinstance(error, (ConnectionError, TimeoutError)):
            return True
        return any(cls.__name__ in TRANSIENT_ERROR_CLASSES for cls in type(error).__mro__)

    def wait(self, job, timeout, *, poll_interval=5.0):
        """Wait up to the 4-hour envelope, in segments the inherited 2-hour wait accepts.

        The inherited poll has no SDK retries, and any error it raises ends the lifecycle and terminates the
        instance. Over a ~2-hour job a network blip on the operator's machine is likely, so a transient
        provider error is recorded and the poll resumes; only the deadline, a terminal instance state, the
        worker's own result, or a non-transient error ends the wait (pre-flight review, 2026-09-18).
        """
        require(timeout == shared.RESOURCE_PLAN["instance_seconds_max"], "PRACTICE_WAIT_CALLER")
        deadline = time.monotonic() + INSTANCE_SECONDS_MAX
        transient = 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"worker_status": "REMOTE_TIMED_OUT"}
            try:
                outcome = super().wait(job, min(remaining, shared.RESOURCE_PLAN["instance_seconds_max"]),
                                       poll_interval=poll_interval)
            except Exception as error:                              # noqa: BLE001 - classified below
                if not self._transient(error) or transient >= MAX_TRANSIENT_WAIT_ERRORS:
                    raise
                transient += 1
                self._event("wait_transient_error", "RETRYING", error=type(error).__name__,
                            detail=str(error)[:300], count=transient)
                time.sleep(max(5.0, min(30.0, poll_interval * 6)))
                continue
            if outcome.get("worker_status") != "REMOTE_TIMED_OUT":
                return outcome

    def _user_data(self, bucket):
        """The matched study's guest watchdog, with this study's 4-hour envelope."""
        require(re.fullmatch(JOB_PATTERN, self.job) is not None, "PRACTICE_WATCHDOG_JOB")
        require(hasattr(self, "bound_config") and self.bound_config["bucket"] == bucket, "PRACTICE_CONFIG_BUCKET")
        original = super(matched.TypedMatchedProvider, self)._user_data(bucket)
        anchor = "PY=''"
        require(original.count(anchor) == 1, "PRACTICE_BOOTSTRAP_CONFIG_ANCHOR")
        checks = ("echo '" + digest(canonical(self.bound_config)) + "  /opt/cas-graph6curr/package/config.json' | sha256sum -c -\n"
                  "echo '" + self.manifest_sha256 + "  /opt/cas-graph6curr/package/" + shared.MANIFEST_NAME + "' | sha256sum -c -\n")
        original = original.replace(anchor, checks + anchor)
        delimiter = "CNCM_PRACTICE_BOOTSTRAP_BODY"
        require(delimiter not in original.splitlines(), "PRACTICE_BOOTSTRAP_DELIMITER")
        lines = [
            "#!/bin/bash", "set -eu", "umask 077",
            'cas_typed_shutdown="$(command -v shutdown)"',
            "cas_typed_shutdown_on_exit() {",
            "  cas_typed_status=$?",
            "  trap - EXIT HUP INT TERM",
            '  "$cas_typed_shutdown" --poweroff +1 || true',
            '  exit "$cas_typed_status"',
            "}",
            "trap cas_typed_shutdown_on_exit EXIT",
            "trap 'exit 129' HUP", "trap 'exit 130' INT", "trap 'exit 143' TERM",
            'cas_typed_systemd_run="$(command -v systemd-run)"',
            'cas_typed_systemctl="$(command -v systemctl)"',
            'cas_typed_timeout="$(command -v timeout)"',
            'cas_typed_unit="' + self.job + '-deadline"',
            # Boot-relative deadline five minutes inside this study's 14,400 s envelope. Never cancelled.
            '"$cas_typed_systemd_run" --unit="$cas_typed_unit" --on-boot=%ds ' % BOOT_WATCHDOG_SECONDS
            + '--timer-property=AccuracySec=1s --property=Type=oneshot "$cas_typed_shutdown" --poweroff now',
            '"$cas_typed_systemctl" is-active --quiet "$cas_typed_unit.timer"',
            '"$cas_typed_systemctl" show "$cas_typed_unit.timer" --no-pager '
            '--property=ActiveState --property=NextElapseUSecMonotonic',
            'echo "CNCM_GUEST_WATCHDOG_ARMED unit=$cas_typed_unit boot_deadline_seconds=%d"' % BOOT_WATCHDOG_SECONDS,
            # Setup, the 12,600 s numeric child and its publisher, bounded together below the watchdog.
            '"$cas_typed_timeout" --signal=TERM --kill-after=30s %ds /bin/bash <<\'' % OUTER_TIMEOUT_SECONDS
            + delimiter + "'",
            original.rstrip("\n"), delimiter, "",
        ]
        return "\n".join(lines)

    def bind_authority(self, authority):
        validate_authority(authority)
        for key in ("job", "source_sha", "archive_sha256", "manifest_sha256"):
            require(getattr(self, key) == authority[key], "PRACTICE_PROVIDER_BINDING:" + key)
        self.bound_config = json.loads(canonical(authority["worker_config"]))
        self.worker_name, self.result_schema = WORKER_NAME, RESULT_SCHEMA
        self.failure_statuses = ("WORKER_FAILED", "REMOTE_WORKER_FAILED", "TYPED_PRACTICE_FAILED")

    def _worker_config(self, bucket):
        require(hasattr(self, "bound_config"), "PRACTICE_AUTHORITY_NOT_BOUND")
        require(self.region == BOUNDS["region"], "PRACTICE_PROVIDER_REGION")
        require(bucket == self.bound_config["bucket"], "PRACTICE_PROVIDER_BUCKET")
        return json.loads(canonical(self.bound_config))


def validate_reserved_transition(before, after, receipt, request, *, expected_plan):
    """The shared transition check, with this study's frozen $15.00 amount."""
    prior, current = before["ledger"], after["ledger"]
    require(current["revision"] == prior["revision"] + 1, "RESERVATION_REVISION_MISMATCH")
    require(current["reservations"][:-1] == prior["reservations"], "RESERVATION_NOT_APPEND_ONLY")
    require(current["previous_state_sha256"] == budget.digest(budget.encoded(prior)), "RESERVATION_PREDECESSOR_MISMATCH")
    entry = current["reservations"][-1]
    for key in ("job", "source_sha", "archive_sha256"):
        require(entry[key] == request[key], "RESERVATION_IDENTITY_MISMATCH:" + key)
    require(entry["status"] == budget.STATUS and budget.amount(entry["reserved_usd"]) == budget.amount(RESERVATION_USD),
            "PRACTICE_RESERVATION_AMOUNT_FROZEN")
    require(entry["plan"] == expected_plan and entry["plan_sha256"] == budget.digest(budget.encoded(expected_plan)),
            "RESERVATION_RESOURCE_PLAN_MISMATCH")
    require(receipt.get("ledger_sha256") == after["ledger_sha256"], "RESERVATION_RECEIPT_HASH_MISMATCH")
    return receipt


def execute(request, authority, provider, *, receipt_dir, owner_authorization_path, ledger_path):
    validate_request(request)
    validate_authority(authority)
    validate_owner(owner_authorization_path, authority)
    ledger_path = validate_ledger_path(ledger_path)
    require(Path(provider.ledger_path).resolve() == ledger_path, "PRACTICE_PROVIDER_LEDGER_MISMATCH")
    require(isinstance(provider, TypedPracticeProvider), "PRACTICE_PROVIDER_REQUIRED")
    provider.bind_authority(authority)
    return lifecycle.execute(request, authority, provider, ledger_path=ledger_path,
        receipt_dir=receipt_dir, owner_authorization_path=owner_authorization_path,
        validate_request_fn=validate_request, validate_authority_fn=validate_authority,
        evidence_contract=evidence_contract(), validate_reserved_transition_fn=lambda before, after, receipt, request:
            validate_reserved_transition(before, after, receipt, request, expected_plan=provider.reservation_plan()))


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--package")
    parser.add_argument("--source-sha")
    for field in ("request", "request-sha256", "authority", "authority-sha256", "receipt-dir", "owner-authorization",
                  "ledger-path"):
        parser.add_argument("--" + field)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    if args.package:
        require(not args.execute and args.source_sha, "PRACTICE_PACKAGE_ARGUMENTS")
        print(json.dumps(build_practice_package(args.package, source_sha=args.source_sha)))
        return 0
    if not args.execute:
        print(json.dumps({"status": "PLAN_ONLY", "design": DESIGN, "bounds": BOUNDS, "provider_calls": 0,
                          "reservation_created": False}))
        return 0
    require(all(getattr(args, key) for key in ("request", "request_sha256", "authority", "authority_sha256",
                                               "receipt_dir", "owner_authorization", "ledger_path")), "PRACTICE_EXPLICIT_INPUTS")
    request_raw, authority_raw = Path(args.request).read_bytes(), Path(args.authority).read_bytes()
    require(digest(request_raw) == args.request_sha256 and digest(authority_raw) == args.authority_sha256,
            "PRACTICE_REQUEST_AUTHORITY_FILE_HASH")
    request, authority = json.loads(request_raw), json.loads(authority_raw)
    validate_request(request)
    validate_authority(authority)
    validate_owner(args.owner_authorization, authority)
    ledger_path = validate_ledger_path(args.ledger_path)
    provider = TypedPracticeProvider(job=request["job"], source_sha=request["source_sha"],
        archive_sha256=request["archive_sha256"], manifest_sha256=request["manifest_sha256"],
        ledger_path=ledger_path, clients=lifecycle._clients(args.profile), client_error=lifecycle._client_error(),
        source_archive=lifecycle._locate_archive(request["archive_sha256"]))
    result = execute(request, authority, provider, receipt_dir=args.receipt_dir,
                     owner_authorization_path=args.owner_authorization, ledger_path=ledger_path)
    print(json.dumps({"status": result["status"], "completed_deliverable": result["completed_deliverable"],
                      "stages": result["stages"]}))
    return 0 if result["completed_deliverable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
