"""One predeclared matched-study arm through the bounded AWS lifecycle.

Source/package admission is pure. Only explicit execute enters provider code.
The worker imports project code through a manifest-verified fresh-process loader.
"""
from __future__ import annotations

import ast
from decimal import Decimal, InvalidOperation
import importlib
import io
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
WORKSPACE_HOME = next(parent for parent in reversed(ROOT.parents)
                      if parent.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
for root in (ROOT, PROJECT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
from aws import recurrent_cjt_launch as worker_template
from aws import graph_training_candidate_launch as lifecycle
from aws import graph_training_curriculum_launch as shared
from aws import run_evidence
from cas_meta2.typed_teaching import matched_contract as contract

require, canonical, digest = shared.require, shared.canonical, shared.digest
CANDIDATE = contract.CANDIDATE
CONFIG_SCHEMA = contract.CONFIG_SCHEMA
RESULT_SCHEMA = "cncm.typed-matched-worker-result/0.1"
FAILURE_SCHEMA = "cncm.typed-matched-failure/0.1"
REQUEST_SCHEMA = "cncm.typed-matched-request/0.1"
AUTHORITY_SCHEMA = "cncm.typed-matched-authority/0.1"
OWNER_SCHEMA = "cncm.typed-matched-owner/0.1"
WORKER_NAME = "typed_matched_worker.py"
JOB_PATTERN = contract.JOB_PATTERN
SEED, MAX_WALL_SECONDS = contract.MODEL_SEEDS[0], contract.MAX_WALL_SECONDS
EXPERIMENT = {"profile": "typed_matched_development_v1", "candidate": CANDIDATE,
              "entrypoint": "cncm.typed_matched_worker.run"}
BOUNDS = {"training": True, "optimizer_updates_max": 178, "max_wall_seconds": MAX_WALL_SECONDS,
          "jobs": 1, "automatic_retries": 0, "reservation_usd": "7.00",
          "instance_type": "g7.2xlarge", "region": "us-west-2"}
DESIGN = json.loads(canonical(contract.DESIGN))
CANONICAL_LEDGER = (WORKSPACE_HOME / "_worktrees/meta1/cas_only_reasoner/"
    "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/"
    "records/budget/campaign_ledger.json")
PACKAGING_SOURCES = tuple("aws/" + name + ".py" for name in (
    "typed_matched_launch", "recurrent_cjt_launch", "graph_training_candidate_launch",
    "graph_training_curriculum_launch", "run_evidence", "budget", "__init__"))


def _probe():
    probe = importlib.import_module("cncm.typed_matched_worker")
    for name in ("CANDIDATE", "CONFIG_SCHEMA", "RESULT_SCHEMA", "FAILURE_SCHEMA"):
        require(getattr(probe, name) == globals()[name], "TYPED_PROBE_CONTRACT:" + name)
    return probe


def frozen_inputs():
    return contract.input_inventory(PROJECT)


def frozen_inputs_hash():
    return digest(canonical(frozen_inputs()))


def worker_config(job, *, source_sha):
    condition, model_seed = contract.parse_job(job)
    return contract.make_config(PROJECT, source_sha=source_sha, job=job, condition=condition, model_seed=model_seed,
        bucket=job + "-" + shared.RESOURCE_PLAN["account"])


def validate_request(request):
    require(type(request) is dict and set(request) == {"schema", "job", "source_sha",
        "archive_sha256", "manifest_sha256", "launch_authorized"}, "TYPED_REQUEST_FIELDS")
    require(request["schema"] == REQUEST_SCHEMA, "TYPED_REQUEST_SCHEMA")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]), "TYPED_REQUEST_JOB")
    for key, pattern in (("source_sha", shared.HEX40), ("archive_sha256", shared.HEX64),
                         ("manifest_sha256", shared.HEX64)):
        require(type(request[key]) is str and pattern.fullmatch(request[key]), "TYPED_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "TYPED_REQUEST_INERT")
    return request


def _check_bounds(document, code):
    for key, expected in BOUNDS.items():
        require(type(document.get(key)) is type(expected) and document[key] == expected, code + ":" + key)


def validate_authority(authority):
    identity = {"job", "source_sha", "archive_sha256", "manifest_sha256"}
    fields = identity | set(BOUNDS) | {"schema", "candidate", "owner_authorization_sha256",
        "inputs_sha256", "design_sha256", "evidence_contract_sha256", "worker_config"}
    require(type(authority) is dict and set(authority) == fields, "TYPED_AUTHORITY_FIELDS")
    require(authority["schema"] == AUTHORITY_SCHEMA and authority["candidate"] == CANDIDATE,
            "TYPED_AUTHORITY_CANDIDATE")
    validate_request({**{key: authority[key] for key in identity}, "schema": REQUEST_SCHEMA,
                      "launch_authorized": False})
    require(type(authority["owner_authorization_sha256"]) is str and
            shared.HEX64.fullmatch(authority["owner_authorization_sha256"]), "TYPED_OWNER_HASH")
    _check_bounds(authority, "TYPED_AUTHORITY_BOUND")
    for key, expected in (("inputs_sha256", frozen_inputs_hash()),
                          ("design_sha256", digest(canonical(DESIGN))),
                          ("evidence_contract_sha256", run_evidence.contract_digest(evidence_contract()))):
        require(authority[key] == expected, "TYPED_AUTHORITY_BINDING:" + key)
    expected = worker_config(authority["job"], source_sha=authority["source_sha"])
    # Canonical bytes distinguish False from 0 and integral from floating values.
    require(type(authority["worker_config"]) is dict and
            canonical(authority["worker_config"]) == canonical(expected), "TYPED_AUTHORITY_CONFIG")
    return authority


def validate_owner(path, authority):
    raw = Path(path).read_bytes()
    require(digest(raw) == authority["owner_authorization_sha256"], "TYPED_OWNER_FILE_HASH")
    record = json.loads(raw)
    require(type(record) is dict and record.get("schema") == OWNER_SCHEMA and
            record.get("candidate") == CANDIDATE, "TYPED_OWNER_SCOPE")
    quote = record.get("owner_instruction_raw")
    require(type(quote) is str and bool(quote.strip()), "TYPED_OWNER_QUOTE")
    require(type(record.get("bounds")) is dict, "TYPED_OWNER_BOUNDS")
    _check_bounds(record["bounds"], "TYPED_OWNER_BOUND")
    return record


def validate_ledger_path(value):
    require(isinstance(value, (str, Path)), "TYPED_LEDGER_PATH_REQUIRED")
    path = Path(value).expanduser().resolve()
    require(path == CANONICAL_LEDGER.resolve() and path.is_file(), "TYPED_CANONICAL_META1_LEDGER_REQUIRED")
    return path


def bootstrap_source():
    """Stdlib-only child: the verified loader is installed before owned imports."""
    return "\n".join((
        "import hashlib, json, os, sys, types",
        "from pathlib import Path",
        "ROOT = Path(sys.argv[1]).resolve(strict=True)",
        "def require(ok, reason):",
        "    if not ok: raise ValueError('TYPED_BOOTSTRAP:' + reason)",
        "def canonical(value):",
        "    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\\n').encode('utf-8')",
        "CONFIG = json.loads((ROOT / 'config.json').read_bytes())",
        "MANIFEST = json.loads((ROOT / " + repr(shared.MANIFEST_NAME) + ").read_bytes())",
        "require(MANIFEST['source_sha'] == CONFIG['source_sha'], 'SOURCE_SHA')",
        "require(hashlib.sha256(canonical(CONFIG['inputs'])).hexdigest() == CONFIG['inputs_sha256'], 'INPUT_INDEX_HASH')",
        "require(MANIFEST['inputs_sha256'] == CONFIG['inputs_sha256'], 'MANIFEST_INPUT_INDEX_HASH')",
        "require(canonical(MANIFEST['inputs']) == canonical(CONFIG['inputs']), 'MANIFEST_INPUT_INDEX')",
        "require(all(k in CONFIG['design'] and canonical(v) == canonical(CONFIG['design'][k]) for k, v in MANIFEST['typed_design'].items()), 'MANIFEST_STUDY_DESIGN')",
        "for row in CONFIG['inputs']:",
        "    require(MANIFEST['files_sha256'].get(row['path']) == row['sha256'] and type(row['bytes']) is int and MANIFEST['files_bytes'].get(row['path']) == row['bytes'], 'MANIFEST_INPUT_JOIN')",
        "require(not any(n == 'cncm' or n.startswith('cncm.') or n == 'cas_meta2' or n.startswith('cas_meta2.') for n in sys.modules), 'FRESH_PROCESS')",
        "NAME = 'cncm/typed_source_attestation.py'",
        "PINS = [r for r in CONFIG['inputs'] if r['path'] == NAME]",
        "require(len(PINS) == 1 and 0 < PINS[0]['bytes'] <= 4194304, 'BOOTSTRAP_PIN')",
        "PATH = ROOT / NAME",
        "require(not PATH.is_symlink() and PATH.resolve(strict=True).is_relative_to(ROOT) and PATH.stat().st_size == PINS[0]['bytes'], 'BOOTSTRAP_PATH')",
        "with PATH.open('rb') as stream: RAW = stream.read(4194305)",
        "require(len(RAW) == PINS[0]['bytes'] and hashlib.sha256(RAW).hexdigest() == PINS[0]['sha256'], 'BOOTSTRAP_BYTES')",
        "MODULE = types.ModuleType('_typed_verified_source_bootstrap')",
        "MODULE.__file__ = str(PATH)",
        "sys.modules[MODULE.__name__] = MODULE",
        "exec(compile(RAW, str(PATH), 'exec', dont_inherit=True, optimize=0), MODULE.__dict__)",
        "ATTESTOR = MODULE.install(ROOT, CONFIG['inputs'])",
        "sys.path.insert(0, str(ROOT))",
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))",
        "os.environ['CAS_META2_RUN_TEACHING_CYCLE'] = '1'",
        "from cncm import typed_matched_worker",
        "RESULTS = ROOT / 'results'",
        "ARTIFACTS = RESULTS / 'artifacts'",
        "report = typed_matched_worker.run(CONFIG, root=ROOT, results=RESULTS, artifacts=ARTIFACTS, attestor=ATTESTOR)",
        "print(json.dumps({'status': report['status']}))",
    ))


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
            node.value = ast.Subscript(value=ast.Name(id="config", ctx=ast.Load()),
                slice=ast.Constant("design"), ctx=ast.Load()); regions += 1
    require(found == set(replacements) and timeouts == 1 and regions == 1, "TYPED_WORKER_TEMPLATE_CHANGED")
    tree.body[0] = ast.Expr(ast.Constant(CANDIDATE + ": complete exposed training; no learning-advantage claim."))
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def evidence_contract():
    names = {"results/result.json": "terminal envelope", "results/result.json.sha256": "envelope digest",
             "results/artifacts/manifest.json": "artifact inventory"}
    names.update({"results/artifacts/" + name: "complete typed-matched worker evidence"
                  for name in _probe().EXPECTED_ARTIFACTS})
    return run_evidence.contract(EXPERIMENT["profile"], [
        run_evidence.requirement(key, title, kind="json" if key.endswith(".json") else "file")
        for key, title in names.items()], notes=[
            "Full course:160 main,16 interference and2 validation replay updates,178 actual total.",
            "All declared stages/checkpoints/scoring must arrive; partial course is not success.",
            "One arm only; paired analysis required. Development transfer is limited to parts/reach."])


def package_data_files():
    return tuple(sorted(set(shared.PILOT + name for name in PACKAGING_SOURCES)
                        | {shared.WORKER_REQUIREMENTS} | {item["path"] for item in frozen_inputs()}))


def git_package_bytes(root, commit, name):
    require(type(commit) is str and shared.HEX40.fullmatch(commit), "TYPED_SOURCE_COMMIT")
    shared.checked_names([name])
    permitted = (name.startswith("research/") or name in contract.MATERIAL
                 or (name.startswith("cncm/") and name.endswith(".py")))
    require(permitted, "TYPED_SOURCE_MEMBER_SCOPE")
    return shared._run_git(["-c", "core.autocrlf=false", "show",
                            commit + ":" + shared.GIT_PREFIX + name], root)


def build_matched_package(output, *, source_sha, git_bytes_fn=None, git_paths_fn=None):
    """Exact committed member allowlist; no retained target/frames/slots bundles."""
    output = Path(output).absolute()
    require(not output.exists() and output.parent.is_dir() and output.is_relative_to(ROOT / "records")
            and output != ROOT / "records", "TYPED_FRESH_PACKAGE_PATH")
    require(type(source_sha) is str and shared.HEX40.fullmatch(source_sha), "TYPED_SOURCE_COMMIT")
    get_bytes = git_bytes_fn or git_package_bytes
    rows = frozen_inputs()
    names = package_data_files()
    shared.checked_names(list(names))
    members = {name: get_bytes(ROOT, source_sha, name) for name in names}
    for name in PACKAGING_SOURCES + ("requirements-gpu.txt",):
        require(members[shared.PILOT + name] == (ROOT / name).read_bytes(),
                "TYPED_PACKAGING_SOURCE_NOT_COMMITTED:" + name)
    for row in rows:
        raw = members[row["path"]]
        require(len(raw) == row["bytes"] and digest(raw) == row["sha256"],
                "TYPED_INPUT_NOT_COMMITTED:" + row["path"])
    source = render_worker()
    transport = run_evidence.unified_transport(source)
    members[WORKER_NAME] = run_evidence.unified_worker_source(source).encode("utf-8")
    require(all(len(raw) <= shared.MAX_MEMBER_BYTES for raw in members.values()), "TYPED_MEMBER_BOUND")
    manifest = shared.manifest_for(members, source_sha, worker_name=WORKER_NAME,
        experiment=EXPERIMENT, package_schema="cncm.typed-matched-package/0.1", design=DESIGN)
    manifest["frozen_budget"] = {**BOUNDS, "main_updates": 160, "interference_updates": 16, "validation_replay_updates": 2}
    manifest["typed_design"] = DESIGN
    manifest["inputs"] = rows
    manifest["inputs_sha256"] = digest(canonical(rows))
    manifest["transport"] = {"implementation": "aws.run_evidence.render_transport",
        "replaced_functions": transport["replaced"], "publisher_wired": transport["publisher_wired"],
        "marker_last": True, "predeclared_contract_sha256": run_evidence.contract_digest(evidence_contract())}
    members[shared.MANIFEST_NAME] = canonical(manifest)
    require(len(members) <= shared.MAX_MEMBER_COUNT and all(len(raw) <= shared.MAX_MEMBER_BYTES for raw in members.values())
            and sum(map(len, members.values())) <= shared.MAX_EXPANDED_BYTES, "TYPED_PACKAGE_BOUND")
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, raw in sorted(members.items()):
            info = ZipInfo(name, date_time=(2026, 9, 16, 0, 0, 0))
            info.compress_type, info.external_attr = ZIP_DEFLATED, 0o100644 << 16
            archive.writestr(info, raw)
    raw = buffer.getvalue()
    require(len(raw) <= shared.MAX_ARCHIVE_BYTES, "TYPED_ARCHIVE_BOUND")
    output.mkdir()
    (output / "source.zip").write_bytes(raw)
    receipt = {"schema": "cncm.typed-matched-package-receipt/0.1", "status": "SOURCE_ONLY_NO_LAUNCH",
        "source_sha": source_sha, "archive": str(output / "source.zip"), "archive_sha256": digest(raw),
        "archive_bytes": len(raw), "manifest_sha256": digest(members[shared.MANIFEST_NAME]),
        "member_count": len(members), "manifest": manifest}
    (output / "receipt.json").write_bytes(canonical(receipt))
    return receipt


class TypedMatchedProvider(lifecycle.CandidateProvider):
    def reservation_plan(self):
        require(hasattr(self, "bound_config"), "MATCHED_RESERVATION_CONFIG_REQUIRED")
        plan = shared.reservation_plan()
        plan["task_scope"] = "cncm_typed_matched_development_001"
        plan["frozen_budget"] = json.loads(canonical(self.bound_config["design"]))
        return plan

    def reserve(self, amount):
        """Bind the descriptive reservation plan to this actual study arm."""
        require(hasattr(self, "bound_config"), "MATCHED_RESERVATION_CONFIG_REQUIRED")
        require(not self._reserved and amount == "7.00", "MATCHED_RESERVATION_FROZEN")
        self.calls.append("reserve")
        self._event("budget_reservation", "REQUESTED", amount=amount)
        plan = self.reservation_plan()
        receipt = self.budget.reserve_budget(self.job, self.source_sha, self.archive_sha256,
            amount, plan, self.ledger_path)
        self._reserved = True
        return {**receipt, "aws_side_reservation": self._record_aws_side_reservation(receipt)}

    def _effect(self, operation, callback, **arguments):
        if operation == "run_instances":
            def observed_launch(**supplied):
                # Mark the actual callback boundary, not earlier setup effects.
                # A transport error may arrive after EC2 accepted the request.
                self._instance_launch_attempted = True
                return callback(**supplied)
            return super()._effect(operation, observed_launch, **arguments)
        return super()._effect(operation, callback, **arguments)

    def preflight(self):
        """Retain the actual quote observed by the inherited identity checks."""
        pricing = self.clients["pricing"]
        observed = []
        class ObservedPricing:
            def get_products(_observer, **request):
                require(not observed, "TYPED_MULTIPLE_PRICING_QUERIES")
                response = pricing.get_products(**request)
                observed.append((request, response))
                return response
        self.clients["pricing"] = ObservedPricing()
        try:
            facts = super().preflight()
        finally:
            self.clients["pricing"] = pricing
        require(len(observed) == 1, "TYPED_PRICING_OBSERVATION_REQUIRED")
        request, response = observed[0]
        fields = {"instanceType": BOUNDS["instance_type"], "location": "US West (Oregon)",
            "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA",
            "capacitystatus": "Used", "marketoption": "OnDemand", "operation": "RunInstances"}
        expected = {"ServiceCode": "AmazonEC2", "Filters": [
            {"Type": "TERM_MATCH", "Field": key, "Value": value} for key, value in fields.items()]}
        require(canonical(request) == canonical(expected), "TYPED_PRICING_QUERY_MISMATCH")
        rates = []
        for raw in response.get("PriceList", []):
            for term in json.loads(raw).get("terms", {}).get("OnDemand", {}).values():
                for dimension in term.get("priceDimensions", {}).values():
                    if dimension.get("unit") == "Hrs":
                        try:
                            value = Decimal(str(dimension["pricePerUnit"]["USD"]))
                        except (InvalidOperation, KeyError, ValueError) as error:
                            raise ValueError("TYPED_INVALID_OBSERVED_HOURLY_RATE") from error
                        require(value.is_finite() and value > 0
                                and value <= Decimal(shared.RESOURCE_PLAN["on_demand_rate_ceiling_usd"]),
                                "TYPED_INVALID_OBSERVED_HOURLY_RATE")
                        rates.append(str(value))
        require(rates and not response.get("NextToken"), "TYPED_OBSERVED_HOURLY_RATE_REQUIRED")
        request_id = response.get("ResponseMetadata", {}).get("RequestId")
        require(type(request_id) is str and bool(request_id), "TYPED_PRICING_REQUEST_ID_REQUIRED")
        return {**facts, "observed_on_demand_hourly_usd": sorted(rates),
            "pricing_request_id": request_id, "pricing_query": request,
            "pricing_boundary": "Observed hourly compute quote; reservation includes declared ancillary allowance and is not a provider invoice."}

    def _user_data(self, bucket):
        """Arm a guest-owned deadline before the inherited download/worker path.

        A responsive systemd guest survives loss of the local supervisor. This
        cannot guard failure before cloud-init, guest/host freezes, or promise
        an exact provider invoice. EC2 shutdown behavior remains terminate.
        Normal worker uploads finish before EXIT schedules poweroff with a
        one-minute receiver grace; the independent boot deadline stays armed.
        """
        require(re.fullmatch(JOB_PATTERN, self.job) is not None, "TYPED_WATCHDOG_JOB")
        require(hasattr(self, "bound_config") and self.bound_config["bucket"] == bucket, "TYPED_CONFIG_BUCKET")
        original = super()._user_data(bucket)
        anchor = "PY=''"
        require(original.count(anchor) == 1, "TYPED_BOOTSTRAP_CONFIG_ANCHOR")
        checks = ("echo '" + digest(canonical(self.bound_config)) + "  /opt/cas-graph6curr/package/config.json' | sha256sum -c -\n"
                  "echo '" + self.manifest_sha256 + "  /opt/cas-graph6curr/package/" + shared.MANIFEST_NAME + "' | sha256sum -c -\n")
        original = original.replace(anchor, checks + anchor)
        delimiter = "CNCM_TYPED_BOOTSTRAP_BODY"
        require(delimiter not in original.splitlines(), "TYPED_BOOTSTRAP_DELIMITER")
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
            # Monotonic boot-relative deadline leaves five minutes inside the
            # inherited 7,200-second resource plan. Never cancel this timer.
            '"$cas_typed_systemd_run" --unit="$cas_typed_unit" --on-boot=6900s '
            '--timer-property=AccuracySec=1s --property=Type=oneshot '
            '"$cas_typed_shutdown" --poweroff now',
            '"$cas_typed_systemctl" is-active --quiet "$cas_typed_unit.timer"',
            '"$cas_typed_systemctl" show "$cas_typed_unit.timer" --no-pager '
            '--property=ActiveState --property=NextElapseUSecMonotonic',
            'echo "CNCM_GUEST_WATCHDOG_ARMED unit=$cas_typed_unit boot_deadline_seconds=6900"',
            # Bound setup, worker, and its normal evidence publisher together.
            # The numeric child has a 3,300s cap; setup and publication fit inside
            # this 4,200s bound, still below the existing 6,900s boot watchdog.
            '"$cas_typed_timeout" --signal=TERM --kill-after=30s 4200s /bin/bash <<\'' + delimiter + "'",
            original.rstrip("\n"), delimiter, "",
        ]
        return "\n".join(lines)

    def cleanup(self, job, **kwargs):
        """Keep pending/unknown termination distinct from observed termination."""
        status = dict(super().cleanup(job, **kwargs))
        status["instances"] = dict(status.get("instances", {}))
        failures = list(status.get("failures", []))
        pending = list(status.get("instances_termination_pending", []))
        observations = {}
        identity_unknown = getattr(self, "_instance_launch_attempted", False) and not self._instance_ids
        status["compute_identity_uncertain"] = identity_unknown
        if identity_unknown:
            failures.append("INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT")
        for instance_id in self._instance_ids:
            if instance_id in pending:
                status["instances"][instance_id] = "TERMINATION_PENDING"
                failures.append("INSTANCE_TERMINATION_PENDING:" + instance_id)
                continue
            try:
                response = self.clients["ec2"].describe_instances(InstanceIds=[instance_id])
                instances = [item for reservation in response.get("Reservations", [])
                             for item in reservation.get("Instances", [])]
                require(len(instances) == 1 and instances[0].get("InstanceId") == instance_id,
                        "TYPED_TERMINATION_OBSERVATION_SCOPE")
                state = instances[0].get("State", {}).get("Name")
                observations[instance_id] = {"state": state}
                if state == "terminated":
                    status["instances"][instance_id] = "CONFIRMED_TERMINATED"
                else:
                    status["instances"][instance_id] = "TERMINATION_NOT_CONFIRMED"
                    pending.append(instance_id)
                    failures.append("INSTANCE_TERMINATION_NOT_CONFIRMED:" + instance_id)
            except Exception as error:
                # A transient NotFound response is not proof that compute is gone.
                observations[instance_id] = {"error": type(error).__name__, "detail": str(error)[:500]}
                status["instances"][instance_id] = "TERMINATION_NOT_CONFIRMED"
                pending.append(instance_id)
                failures.append("INSTANCE_TERMINATION_OBSERVATION_FAILED:" + instance_id)
        status["post_cleanup_observations"] = observations
        status["instances_termination_pending"] = sorted(set(pending))
        status["failures"] = failures
        status["complete"] = status.get("complete") is True and not failures and not pending
        return status

    def bind_authority(self, authority):
        validate_authority(authority)
        for key in ("job", "source_sha", "archive_sha256", "manifest_sha256"):
            require(getattr(self, key) == authority[key], "TYPED_PROVIDER_BINDING:" + key)
        self.bound_config = json.loads(canonical(authority["worker_config"]))
        self.worker_name, self.result_schema = WORKER_NAME, RESULT_SCHEMA
        self.failure_statuses = ("WORKER_FAILED", "REMOTE_WORKER_FAILED", "TYPED_MATCHED_FAILED")

    def _worker_config(self, bucket):
        require(hasattr(self, "bound_config"), "TYPED_AUTHORITY_NOT_BOUND")
        require(self.region == BOUNDS["region"], "TYPED_PROVIDER_REGION")
        require(bucket == self.bound_config["bucket"], "TYPED_PROVIDER_BUCKET")
        return json.loads(canonical(self.bound_config))


def execute(request, authority, provider, *, receipt_dir, owner_authorization_path,
            ledger_path):
    validate_request(request)
    validate_authority(authority)
    validate_owner(owner_authorization_path, authority)
    ledger_path = validate_ledger_path(ledger_path)
    require(Path(provider.ledger_path).resolve() == ledger_path, "TYPED_PROVIDER_LEDGER_MISMATCH")
    provider.bind_authority(authority)
    return lifecycle.execute(request, authority, provider, ledger_path=ledger_path,
        receipt_dir=receipt_dir, owner_authorization_path=owner_authorization_path,
        validate_request_fn=validate_request, validate_authority_fn=validate_authority,
        evidence_contract=evidence_contract(), validate_reserved_transition_fn=lambda before, after, receipt, request:
            shared.validate_reserved_transition(before, after, receipt, request, expected_plan=provider.reservation_plan()))


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--package")
    parser.add_argument("--source-sha")
    for field in ("request", "request-sha256", "authority", "authority-sha256", "receipt-dir", "owner-authorization", "ledger-path"):
        parser.add_argument("--" + field)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    if args.package:
        require(not args.execute and args.source_sha, "TYPED_PACKAGE_ARGUMENTS")
        print(json.dumps(build_matched_package(args.package, source_sha=args.source_sha)))
        return 0
    if not args.execute:
        print(json.dumps({"status": "PLAN_ONLY", "design": DESIGN, "inputs": frozen_inputs(),
                          "provider_calls": 0, "reservation_created": False}))
        return 0
    require(all(getattr(args, key) for key in ("request", "request_sha256", "authority", "authority_sha256",
        "receipt_dir", "owner_authorization", "ledger_path")), "TYPED_EXPLICIT_INPUTS")
    request_raw, authority_raw = Path(args.request).read_bytes(), Path(args.authority).read_bytes()
    require(digest(request_raw) == args.request_sha256 and digest(authority_raw) == args.authority_sha256,
            "TYPED_REQUEST_AUTHORITY_FILE_HASH")
    request, authority = json.loads(request_raw), json.loads(authority_raw)
    validate_request(request)
    validate_authority(authority)
    validate_owner(args.owner_authorization, authority)
    ledger_path = validate_ledger_path(args.ledger_path)
    provider = TypedMatchedProvider(job=request["job"], source_sha=request["source_sha"],
        archive_sha256=request["archive_sha256"], manifest_sha256=request["manifest_sha256"],
        ledger_path=ledger_path, clients=lifecycle._clients(args.profile),
        client_error=lifecycle._client_error(), source_archive=lifecycle._locate_archive(request["archive_sha256"]))
    result = execute(request, authority, provider, receipt_dir=args.receipt_dir,
                     owner_authorization_path=args.owner_authorization, ledger_path=ledger_path)
    print(json.dumps({"status": result["status"], "completed_deliverable": result["completed_deliverable"],
                      "stages": result["stages"]}))
    return 0 if result["completed_deliverable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
