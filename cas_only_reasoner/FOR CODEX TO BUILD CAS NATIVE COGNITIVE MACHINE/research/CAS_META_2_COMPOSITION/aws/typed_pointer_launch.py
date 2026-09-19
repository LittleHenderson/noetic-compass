"""One pointer-study job through the bounded AWS lifecycle (owner-approved 2026-09-19, "Accept both, carry on").

Copies the practice study's proven launcher (`typed_practice_launch`) and changes only what the pointer
study needs (INTERFACE_SPEC_POINTER.md section 5, INTERFACE_SPEC_PIPELINE.md section C): this study's own
worker, schemas and job names; the new contract's own admission module, whose `MATERIAL` carries the
eighteen practice checkpoints so the packaged source scope admits them; a new probe, experiment profile
and `task_scope`; and a provider class renamed for this study with four methods replaced.

THE INSTANCE ENVELOPE AND THE RESERVATION ARE THE PRACTICE STUDY'S AND ARE NOT CHANGED. 4 h x $2.52 on
demand + $1.48 ancillary = $11.56, rounded up to $15.00; the owner cap is $45.00 for the three jobs.
`pointer_contract.RESERVATION_USD` is `practice_contract.RESERVATION_USD` by import, and this launcher
reads that constant rather than restating the number. The shared lifecycle modules are not modified: this
module replaces the provider's reservation, watchdog, bootstrap and authority methods instead.

Source/package admission is pure. Only explicit execute enters provider code.
"""
from __future__ import annotations

import ast
from hashlib import sha1
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
from cas_meta2.typed_teaching import pointer_contract as contract

require, canonical, digest = shared.require, shared.canonical, shared.digest
CANDIDATE = contract.CANDIDATE
CONFIG_SCHEMA = contract.CONFIG_SCHEMA
RESULT_SCHEMA = "cncm.typed-pointer-worker-result/0.1"
FAILURE_SCHEMA = "cncm.typed-pointer-failure/0.1"
REQUEST_SCHEMA = "cncm.typed-pointer-request/0.1"
AUTHORITY_SCHEMA = "cncm.typed-pointer-authority/0.1"
OWNER_SCHEMA = "cncm.typed-pointer-owner/0.1"
WORKER_NAME = "typed_pointer_worker.py"
JOB_PATTERN = contract.JOB_PATTERN
MAX_WALL_SECONDS = contract.MAX_WALL_SECONDS            # numeric child timeout, 12,600 s
OUTER_TIMEOUT_SECONDS = 13500                           # setup + worker + publication
BOOT_WATCHDOG_SECONDS = 14100                           # guest-owned poweroff, never cancelled
INSTANCE_SECONDS_MAX = contract.INSTANCE_SECONDS_MAX    # launcher wait budget, 14,400 s
RESERVATION_USD = contract.RESERVATION_USD              # "15.00" -- the practice study's envelope, unchanged
# ==================================================================================================================
# THE SHRUNKEN-SCHEDULE OPT-IN. `None` -- "no smoke was asked for" -- UNLESS `set_smoke_request()` is called.
#
# WHY THIS EXISTS. The pointer worker reads its shrunken schedule from the environment
# (`cncm/typed_pointer_worker.py:164`, `:306`: `os.environ.get(REDUCED_SCHEDULE_ENV)`), and until this opt-in
# existed NOTHING in this tree set that variable for the remote job: `bootstrap_source()` was
# `matched.bootstrap_source()` with a single `typed_matched_worker` -> `typed_pointer_worker` substitution and
# added no environment line, while `matched.bootstrap_source()` bakes its own `CAS_META2_RUN_TEACHING_CYCLE`
# into the generated source (`typed_matched_launch.py:171`). So every AWS pointer job ran the FULL registered
# plan -- 1,470 updates -- and the smoke job's 8-update schedule could not be requested at all.
# `pre_design/AWS_SMOKE_S10_PLAN.md` section 6 records that defect and this fix.
#
# WHY IT IS AN OPT-IN AND NOT `os.environ.get(...)` HERE. Reading the ambient environment at render time would
# let an operator's stray variable shrink a CLAIM-BEARING job's schedule -- a claim-bearing run that trains 8
# updates would then be written to the ledger and to the receipts as though it had trained 1,470. With the
# opt-in, asking for a shrunken schedule is an explicit act of this module's caller, and with `SMOKE_REQUEST`
# left at its `None` default the GENERATED SOURCE IS BYTE-FOR-BYTE IDENTICAL TO THIS FILE'S PREVIOUS REVISION
# -- `render_worker()` inserts nothing, so the package's `archive_sha256` and `manifest_sha256` do not move and
# the three claim-bearing jobs' existing `request.json`/`authority.json` pins stay valid.
#
# `prepare_smoke.py` is the intended caller: it sets this and then freezes the smoke's admission records, so the
# schedule the smoke will run is recorded in the same commit as the package it will install.
#
# The request is the WORKER'S OWN reduced-schedule form -- one of `cncm.typed_pointer_worker.REDUCED_SCHEDULE_KEYS`,
# already validated here at render time so a typo cannot silently bake a different schedule into an instance the
# operator is paying for:
#   {"passes": 1, "updates": 8, "evaluations": [0, 1], "phase_a": ["initial", "pass_01", "final"],
#    "reloads": true, "replays": true, "phase_b": false, "ablations": false, "retention": false,
#    "interference": false}
# Every key above is optional in form and taken from the worker's own key set. `reloads` is the PLURAL key and
# carries a BOOL (`cncm/typed_pointer_worker.py:165-166`, `:337-341`); the singular `reload` is NOT an accepted key,
# and a list of checkpoint names under the plural key is refused with `POINTER_PLAN_FLAGS`
# (`cncm/typed_pointer_worker.py:230-231`). `passes` with `updates` given must be the pass the truncated batches
# actually end in (`:322-323`, `:333`), and a reload-enabled plan must carry an evaluation at pass 0 AND at pass
# `passes` (`:234-236`). The emitted line sets ONE variable and nothing else: the worker records
# `claim_bearing = False` from a reduced request, and the frozen gate reader refuses such a receipt with
# `I1:<seed>:REDUCED_SCHEDULE:<mode>`, so a smoke job cannot print a learning label even by mistake.
# ==================================================================================================================
SMOKE_REQUEST = None
# The line of the WORKER TEMPLATE that the reduced-schedule assignment is inserted after. Derived from the
# template's own text, never indexed by line number: `matched.bootstrap_source()` is exactly this line's
# `CAS_META2_RUN_TEACHING_CYCLE` assignment plus the pointer study's worker-name substitution, and the worker's
# reload-evaluation rule (`cncm/typed_pointer_worker.py:234-236`) is inside the same generated function, so the two
# lines sit together. The count must be exactly 1 on BOTH sides of the substitution, so a template change fails the
# job instead of silently dropping the environment line.
BOOTSTRAP_ENV_ANCHOR = "os.environ['CAS_META2_RUN_TEACHING_CYCLE'] = '1'"
# The ten keys the worker's own `reduced_request()` accepts (`cncm/typed_pointer_worker.py:165`,
# `REDUCED_SCHEDULE_KEYS`). Held here so a typo is refused by the OPERATOR'S OWN call, before a request can be
# baked into an instance; `_probe()` re-checks this tuple against the worker's set on every package build, so the
# two can never drift apart silently. The worker re-applies its own key check at run time regardless.
SMOKE_REQUEST_KEYS = ("passes", "updates", "evaluations", "phase_a", "reloads", "phase_b", "ablations",
                      "retention", "interference", "replays")


def _smoke_request_form(request):
    """The cheap, local form check: a non-empty dict of keys the worker's own `reduced_request()` accepts.

    Refuses a request that is not a dict, an empty request, a key outside the worker's ten
    (`SMOKE_REQUEST_KEYS`), or a value the study's own JSON form cannot carry (`pointer_contract.canonical`
    refuses non-finite numbers), so a request the worker could never parse back is refused here rather than on a
    paid instance.
    """
    require(type(request) is dict, "POINTER_SMOKE_REQUEST_TYPE")
    require(set(request) <= set(SMOKE_REQUEST_KEYS), "POINTER_SMOKE_REQUEST_KEYS")
    require(bool(request), "POINTER_SMOKE_REQUEST_EMPTY")
    try:
        canonical(request)
    except (TypeError, ValueError) as error:
        raise ValueError("POINTER_SMOKE_REQUEST_NOT_JSON:" + type(error).__name__) from error
    # Canonical (sorted keys, same separators) so the literal embedded in the generated source is the same text
    # this file validated, whatever order the caller wrote the keys in.
    return canonical(request).decode("utf-8").rstrip("\n")


def smoke_request_literal(request=None):
    """The literal the generated source carries for an accepted request. `(literal, plan)` for an accepted one.

    Two checks, both before anything is emitted: the cheap local form check, then the WORKER'S OWN rules run
    through the worker's own `schedule_plan()`. `reloads` is the plural key and must carry a BOOL -- the worker
    enforces that in its `_plan` and a list of checkpoint names is refused with `POINTER_PLAN_FLAGS` -- and a
    reload-enabled plan must carry an evaluation at pass 0 AND at pass `passes`
    (`POINTER_PLAN_RELOAD_EVALUATIONS`). A request whose plan came back `claim_bearing` would mean the caller asked
    for the REGISTERED plan through the smoke path, which is refused outright. Returns the plan alongside the
    literal so a caller can record exactly what the instance will run.

    `request` is the parsed request dict -- the module global when omitted -- never a JSON string.
    """
    request = SMOKE_REQUEST if request is None else request
    require(request is not None, "POINTER_SMOKE_NOT_REQUESTED")
    literal = _smoke_request_form(request)
    plan, claim_bearing = _probe().schedule_plan(source=literal)
    require(not claim_bearing, "POINTER_SMOKE_REQUEST_CLAIM_BEARING")
    return literal, plan


def validated_smoke_request(request):
    """`(request, literal, plan)` for a request that is not yet module state. The checks, without the side effect."""
    literal, plan = smoke_request_literal(request)
    return request, literal, plan


def set_smoke_request(request=None):
    """The ONLY way `SMOKE_REQUEST` becomes anything but `None`. An explicit act of this module's caller.

    Ambient environment is deliberately NOT read anywhere on this path: an operator's stray variable must not be
    able to shrink a claim-bearing job's schedule. Called with no argument (or `None`) it clears the opt-in, which
    is the state that leaves the generated source -- and therefore the package bytes -- byte-for-byte unchanged.

    The request is validated BEFORE it becomes module state, so a refused request leaves the opt-in exactly as it
    was: a failed call must not be able to half-set the thing the next `bootstrap_source()` reads.
    """
    global SMOKE_REQUEST
    if request is None:
        SMOKE_REQUEST = None
        return SMOKE_REQUEST
    _, literal, _ = validated_smoke_request(request)     # both checks, before this call touches module state
    SMOKE_REQUEST = request
    return literal


def configure_reduced_schedule(literal=None):
    """THE ONE PROCESS-BOUNDARY ENTRY POINT for the shrunken-schedule request. `(literal, plan)` or `(None, None)`.

    WHY THIS EXISTS, AND WHAT IT COSTS TO GET WRONG. `set_smoke_request` sets an IN-PROCESS global, and a module
    global cannot cross a process boundary. `prepare_smoke.py` freezes a smoke authority whose
    `evidence_contract_sha256` is the SMOKE contract's digest, but the launch is a DIFFERENT process: with nothing
    having called `set_smoke_request` there, `job_evidence_contract()` resolved to the REGISTERED contract and
    `validate_authority` refused the smoke authority with `POINTER_AUTHORITY_BINDING:evidence_contract_sha256` --
    exactly the refusal the first real launch hit on 2026-09-19. The refusal was free (it precedes the reservation)
    but the launch could never have succeeded.

    This function is therefore the SINGLE path both callers use: `main()` with `--reduced-schedule <literal>`, and
    `prepare_smoke.py` when it validates what it is about to freeze. `literal` is the exact JSON `main()` accepts;
    `None` means "no smoke was asked for" and leaves every byte of the generated source and package unchanged.
    """
    if literal is None:
        set_smoke_request(None)
        return None, None
    try:
        request = json.loads(literal)
    except (TypeError, ValueError) as error:
        raise ValueError("POINTER_REDUCED_SCHEDULE_LITERAL:" + type(error).__name__) from error
    global SMOKE_REQUEST
    _, literal_returned, plan = validated_smoke_request(request)   # the caller's OWN refusal path, before state
    SMOKE_REQUEST = request                                       # now, and only now, module state
    return literal_returned, plan


def reduced_schedule_record():
    """What this process is running, for the run's own evidence: `None`, or the literal plus its plan."""
    if SMOKE_REQUEST is None:
        return None
    literal, plan = smoke_request_literal()
    return {"reduced_schedule_literal": literal, "claim_bearing": False,
            "plan": {key: plan[key] for key in (
                "passes", "updates", "prelast", "evaluations", "evaluation_phases", "phase_a", "phase_b",
                "ablations", "retention", "interference", "replays", "reload", "reloads", "checkpoints",
                "ablation_phases")}}


# THE BUCKET IS EXACTLY 63 CHARACTERS, the maximum `[a-z0-9][a-z0-9-]{1,61}[a-z0-9]` allows (RK4).
# Counted on a real name, `cas-meta2-tpntr-20260918234544-daeb6497-m-20260917-807562639912`:
#   "cas-meta2-" 10 + token "tpntr" 5 + "-" 1 + 14-digit stamp + "-" 1 + 8 hex + "-m-" 3 + date 8
#   = 10 + 5 + 1 + 14 + 1 + 8 + 3 + 8 = 50, plus the 13-character account suffix "-807562639912" = 63.
# The study token therefore cannot be longer: "tpoint" gives 64 and is refused, "tprac" also gives 63.
# The suffix is built from `shared.RESOURCE_PLAN["account"]` (="807562639912"), the same string the
# provider asserts against `self.bound_config["bucket"]`.
# The main-training update count, read off the contract's own registered schedule rather than restated:
# every pointer pass is 147 updates whether the pass is stratified or not (`pointer_contract.DESIGN`
# "schedule_stratified_updates_per_pass" and "schedule_unstratified_updates_per_pass" are both 147), so
# 10 passes give 1,470 main + 16 interference + 2 validation replays = 1,488, and a later pass-count
# change cannot silently desynchronise this bound from the schedule.
UPDATES_PER_PASS = contract.DESIGN["schedule_stratified_updates_per_pass"]
OPTIMIZER_UPDATES_MAX = (contract.PASSES * UPDATES_PER_PASS
                         + contract.INTERFERENCE_UPDATES + contract.REPLAY_UPDATES)
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
EXPERIMENT = {"profile": "typed_pointer_v1", "candidate": CANDIDATE, "entrypoint": "cncm.typed_pointer_worker.run"}
BOUNDS = {"training": True, "optimizer_updates_max": OPTIMIZER_UPDATES_MAX, "max_wall_seconds": MAX_WALL_SECONDS,
          "jobs": 1, "automatic_retries": 0, "reservation_usd": RESERVATION_USD,
          "instance_type": "g7.2xlarge", "region": "us-west-2", "instance_seconds_max": INSTANCE_SECONDS_MAX}
DESIGN = json.loads(canonical(contract.DESIGN))
# The ONE canonical budget ledger is the meta1 worktree's. The copy inside this CNCM tree
# (`research/CAS_META_2_COMPOSITION/records/budget/campaign_ledger.json`) is a STALE snapshot that
# `validate_ledger_path` refuses with `TYPED_CANONICAL_META1_LEDGER_REQUIRED`; nothing here reads it, and
# no ledger file is ever written or edited by hand -- the only writer is `budget.reserve_budget`.
CANONICAL_LEDGER = matched.CANONICAL_LEDGER
PACKAGING_SOURCES = tuple("aws/" + name + ".py" for name in (
    "typed_pointer_launch", "typed_practice_launch", "typed_matched_launch", "recurrent_cjt_launch",
    "graph_training_candidate_launch", "graph_training_curriculum_launch", "run_evidence", "budget", "__init__"))
require(shared.RESOURCE_PLAN["instance_seconds_max"] < BOOT_WATCHDOG_SECONDS < INSTANCE_SECONDS_MAX
        and contract.WORKER_DEADLINE_SECONDS < MAX_WALL_SECONDS < OUTER_TIMEOUT_SECONDS < BOOT_WATCHDOG_SECONDS,
        "POINTER_TIME_ORDER")


def _probe():
    import importlib
    probe = importlib.import_module("cncm.typed_pointer_worker")
    for name in ("CANDIDATE", "CONFIG_SCHEMA", "RESULT_SCHEMA", "FAILURE_SCHEMA"):
        require(getattr(probe, name) == globals()[name], "POINTER_PROBE_CONTRACT:" + name)
    return probe


# ==================================================================================================================
# THE INPUT INVENTORY IS READ FROM THE COMMIT, NOT FROM THE WORKING TREE (review R2, MAJOR 3).
#
# `contract.input_inventory(root)` reads the WORKING TREE, while `git_package_bytes` fetches every package member
# with `git show <commit>:<GIT_PREFIX><name>`. On a dirty tree those disagree, and the dangerous direction is
# silent: `authority["inputs_sha256"]` is bound at freeze time and re-derived by `validate_authority` from
# whatever the working tree says, while the packaged config carries the same rows -- so a manifest could admit
# working-tree hashes while the package carries `git show` bytes, and both would still validate.
#
# The rows below are therefore read out of GIT at the commit the package is built from, so "committed" and
# "admitted" are the same bytes BY CONSTRUCTION, and the authority, the worker config and the package manifest all
# come from this one source. `contract.input_inventory(PROJECT)` is still read for the ROW LIST (the material
# pins are the contract's own), and every row it claims is then verified against the commit: the blob must exist,
# and the commit's bytes must hash to the digest and length the inventory declares. A working-tree edit that
# changes an admitted file therefore CANNOT be admitted silently -- it fails here, before a package is written.
#
# The sha256 is computed over git's own object bytes (`blob <len>\0<content>`), which is what git hashes, so the
# check compares the object git stores against the digest the inventory declares rather than trusting either side.
# ==================================================================================================================
_INVENTORY_CACHE = {}
# Git resolves a PATHS PEC relative to the working directory, while `<commit>:<path>` is resolved from the
# repository root. `PROJECT` is this package's directory, three levels below the worktree root, so `ls-tree`
# run there matches nothing and would report every row as missing. The repository root is therefore resolved
# once, from git itself, and every inventory command runs there.
GIT_ROOT = Path(shared._run_git(["-c", "core.autocrlf=false", "rev-parse", "--show-toplevel"],
                                PROJECT).decode("utf-8").strip())
require(GIT_ROOT.is_dir(), "POINTER_GIT_ROOT")


def _git_object_id(raw):
    """Git's own object id for these bytes: SHA-1 over `blob <len>\\0<content>`. READ ONLY."""
    return sha1(b"blob %d\0" % len(raw) + raw).hexdigest()


def _committed_rows(source_sha, root=None, *, repository=None):
    """The input inventory of `source_sha`, with every row's bytes read from the COMMIT."""
    repository = GIT_ROOT if repository is None else repository
    rows = contract.input_inventory(PROJECT if root is None else root)
    names = [row["path"] for row in rows]
    require(len(set(names)) == len(names), "POINTER_INVENTORY_ROWS_NOT_UNIQUE")
    require(all(type(row["path"]) is str and type(row["bytes"]) is int and type(row["sha256"]) is str
                for row in rows), "POINTER_INVENTORY_ROW_SHAPE")
    blobs = {}
    for name in names:
        # ONE command does both jobs: it proves the commit CARRIES the row and returns the commit's bytes for it,
        # so a row the commit does not have is refused before any further work.
        try:
            blobs[name] = shared._run_git(["-c", "core.autocrlf=false", "show",
                                           source_sha + ":" + shared.GIT_PREFIX + name], repository)
        except ValueError as error:
            raise ValueError("POINTER_INVENTORY_BLOB_MISSING:%s:%s" % (name, str(error)[:200])) from error
    # Take the blob id and size from git's own tree rather than from the bytes just read, so one side of the
    # comparison is git's record of the commit and the other is the content that tree names. The pathspec is the
    # inventory's OWN top-level directories, derived rather than assumed, so a new directory cannot be missed.
    trees = tuple(sorted({name.split("/")[0] + "/" for name in names}))
    sizes = {}
    listing = shared._run_git(["-c", "core.autocrlf=false", "ls-tree", "-r", "-l", "-z", source_sha,
                               "--"] + [shared.GIT_PREFIX + tree for tree in trees], repository)
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        meta, _, path = entry.partition(b"\t")
        fields = meta.split()
        sizes[path.decode("utf-8").removeprefix(shared.GIT_PREFIX)] = (fields[2].decode("ascii"), int(fields[3]))
    out = []
    for row in rows:
        path = row["path"]
        require(path in blobs and path in sizes, "POINTER_INVENTORY_BLOB_MISSING:" + path)
        raw = blobs[path]
        object_id, size = sizes[path]
        # A row whose declared length is not the commit's is a WORKING-TREE edit that the tree would otherwise
        # admit: report it as that, with both numbers, instead of as a length mismatch.
        require(size == row["bytes"],
                "POINTER_INVENTORY_WORKING_TREE_DIVERGED:%s:inventory=%d,commit=%d"
                % (path, row["bytes"], size))
        require(len(raw) == size, "POINTER_INVENTORY_BLOB_LENGTH:" + path)
        require(_git_object_id(raw) == object_id, "POINTER_INVENTORY_OBJECT_ID_MISMATCH:" + path)
        require(digest(raw) == row["sha256"], "POINTER_INVENTORY_NOT_COMMITTED:" + path)
        out.append({**row, "committed_content_sha256": digest(raw)})
    return out


def frozen_inputs(source_sha=None):
    """The inventory rows for `source_sha` (default: the current HEAD), read from that commit.

    Called with no argument it is the inventory of HEAD, which is what a freeze binds; the return shape is
    unchanged from `contract.input_inventory`, plus the byte digest of the committed content.
    """
    commit = source_sha or shared._run_git(["-c", "core.autocrlf=false", "rev-parse", "HEAD"], PROJECT).decode().strip()
    require(type(commit) is str and shared.HEX40.fullmatch(commit), "POINTER_INVENTORY_COMMIT")
    if commit not in _INVENTORY_CACHE:
        _INVENTORY_CACHE[commit] = _committed_rows(commit)
    return [dict(row) for row in _INVENTORY_CACHE[commit]]


def frozen_inputs_hash(source_sha=None):
    """The number `contract.make_config` puts in `inputs_sha256`, computed over the COMMIT's bytes.

    THE PROJECTION MATTERS, and getting it wrong cost a real AWS job. `frozen_inputs()` returns
    `contract.input_inventory`'s rows PLUS `committed_content_sha256` -- the digest of the committed content,
    which is load-bearing evidence and must stay. But that extra field must NOT enter THIS digest:
    `pointer_contract.make_config` computes its `inputs_sha256` as `sha256(canonical(input_inventory(root)))`
    (`pointer_contract.py:970`, `:978`), with no such field in the rows.

    Hashing the enriched rows here produced a DIFFERENT number from the config's, and the worker's bootstrap
    compares exactly those two -- `MANIFEST['inputs_sha256'] == CONFIG['inputs_sha256']` in the generated
    `_inner_runner.py`. So a real smoke job booted a `g7.2xlarge`, installed the package, and refused at
    container line 12 with `TYPED_BOOTSTRAP:MANIFEST_INPUT_INDEX_HASH` -- before the encoder, before phase A,
    before any training. Both numbers mean the same thing; only this projection makes them equal in value.

    Do not "simplify" this back to `digest(canonical(frozen_inputs(source_sha)))`.
    """
    rows = [{key: value for key, value in row.items() if key != "committed_content_sha256"}
            for row in frozen_inputs(source_sha)]
    return digest(canonical(rows))


def inputs_hash_cross_check(source_sha=None):
    """`(config_hash, launcher_hash, authorities_agree)` -- the guard that was missing.

    Every internal check here was self-consistent while the two numbers disagreed: `validate_authority` compares
    the authority's `inputs_sha256` against `frozen_inputs_hash` (both the launcher's side) and PASSED, while the
    worker compared the packaged manifest against the CONFIG (the contract's side) and correctly REFUSED. Nothing
    tested that the two sides are the same number. This does, so a future divergence of this shape is caught at
    freeze time for $0 instead of on an instance for about $0.40 and a $15.00 cap commitment.
    """
    config_hash = worker_config("cas-meta2-tpntr-00000000000000-00000000-m-20260917",
                                source_sha=source_sha or "0" * 40)["inputs_sha256"]
    launcher_hash = frozen_inputs_hash(source_sha)
    require(config_hash == launcher_hash,
            "POINTER_CONFIG_INPUTS_HASH:%s!=%s" % (config_hash[:16], launcher_hash[:16]))
    return config_hash, launcher_hash, True


def worker_config(job, *, source_sha):
    _, model_seed = contract.parse_job(job)
    return contract.make_config(PROJECT, source_sha=source_sha, job=job, model_seed=model_seed,
                                bucket=job + "-" + shared.RESOURCE_PLAN["account"])


def validate_request(request):
    require(type(request) is dict and set(request) == {"schema", "job", "source_sha", "archive_sha256",
                                                       "manifest_sha256", "launch_authorized"}, "POINTER_REQUEST_FIELDS")
    require(request["schema"] == REQUEST_SCHEMA, "POINTER_REQUEST_SCHEMA")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]), "POINTER_REQUEST_JOB")
    for key, pattern in (("source_sha", shared.HEX40), ("archive_sha256", shared.HEX64), ("manifest_sha256", shared.HEX64)):
        require(type(request[key]) is str and pattern.fullmatch(request[key]), "POINTER_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "POINTER_REQUEST_INERT")
    return request


def _check_bounds(document, code):
    for key, expected in BOUNDS.items():
        require(type(document.get(key)) is type(expected) and document[key] == expected, code + ":" + key)


def validate_authority(authority, evidence_contract=None):
    """The authority's own fields, plus the three byte bindings RK9 requires.

    `evidence_contract` is the contract THIS job will run under, and it defaults to the registered 10-pass one.
    The smoke path passes its reduced contract (`smoke_evidence_contract()`), because the authority it froze
    carries that contract's digest; the three claim-bearing jobs keep the default, whose bytes are unchanged.
    """
    identity = {"job", "source_sha", "archive_sha256", "manifest_sha256"}
    fields = identity | set(BOUNDS) | {"schema", "candidate", "owner_authorization_sha256", "inputs_sha256",
                                       "design_sha256", "evidence_contract_sha256", "worker_config"}
    require(type(authority) is dict and set(authority) == fields, "POINTER_AUTHORITY_FIELDS")
    require(authority["schema"] == AUTHORITY_SCHEMA and authority["candidate"] == CANDIDATE, "POINTER_AUTHORITY_CANDIDATE")
    validate_request({**{key: authority[key] for key in identity}, "schema": REQUEST_SCHEMA, "launch_authorized": False})
    require(type(authority["owner_authorization_sha256"]) is str
            and shared.HEX64.fullmatch(authority["owner_authorization_sha256"]), "POINTER_OWNER_HASH")
    _check_bounds(authority, "POINTER_AUTHORITY_BOUND")
    # The three bindings that enforce RK9: the live code inventory (now including the eighteen
    # checkpoints through the pointer contract), the pointer design bytes, and the pointer evidence
    # contract, which is itself derived from the pointer worker's EXPECTED_ARTIFACTS.
    contract = evidence_contract if evidence_contract is not None else globals()["evidence_contract"]()
    for key, expected in (("inputs_sha256", frozen_inputs_hash(authority["source_sha"])),
                          ("design_sha256", digest(canonical(DESIGN))),
                          ("evidence_contract_sha256", run_evidence.contract_digest(contract))):
        require(authority[key] == expected, "POINTER_AUTHORITY_BINDING:" + key)
    expected = worker_config(authority["job"], source_sha=authority["source_sha"])
    require(type(authority["worker_config"]) is dict and canonical(authority["worker_config"]) == canonical(expected),
            "POINTER_AUTHORITY_CONFIG")
    return authority


def validate_owner(path, authority):
    raw = Path(path).read_bytes()
    require(digest(raw) == authority["owner_authorization_sha256"], "POINTER_OWNER_FILE_HASH")
    record = json.loads(raw)
    require(type(record) is dict and record.get("schema") == OWNER_SCHEMA and record.get("candidate") == CANDIDATE,
            "POINTER_OWNER_SCOPE")
    quote = record.get("owner_instruction_raw")
    require(type(quote) is str and bool(quote.strip()), "POINTER_OWNER_QUOTE")
    require(record.get("job") == authority["job"], "POINTER_OWNER_JOB")
    require(type(record.get("bounds")) is dict, "POINTER_OWNER_BOUNDS")
    _check_bounds(record["bounds"], "POINTER_OWNER_BOUND")
    return record


def validate_ledger_path(value):
    # There is one budget ledger and it is the meta1 worktree's; this delegates unchanged.
    return matched.validate_ledger_path(value)


def bootstrap_source():
    source = matched.bootstrap_source()
    require(source.count("typed_matched_worker") == 2, "POINTER_BOOTSTRAP_TEMPLATE_CHANGED")
    source = source.replace("typed_matched_worker", "typed_pointer_worker")
    # THE OPT-IN, AND ONLY THE OPT-IN. With `SMOKE_REQUEST is None` this function returns exactly what it returned
    # before the opt-in existed, byte for byte, so no package hash moves and the claim-bearing jobs keep the
    # `archive_sha256`/`manifest_sha256` their admission records pin. With it set, ONE line is inserted
    # immediately after the teaching-cycle line, carrying the caller's request as a literal.
    if SMOKE_REQUEST is not None:
        # The same two checks the setter runs, re-run on the state this function is about to emit: the literal and
        # the plan come from the WORKER's own `schedule_plan()`, so nothing is baked in that the instance would
        # then refuse.
        request, _ = smoke_request_literal()
        worker = _probe()
        require(worker.REDUCED_SCHEDULE_ENV == "CNCM_POINTER_REDUCED_SCHEDULE"
                and set(worker.REDUCED_SCHEDULE_KEYS) == set(SMOKE_REQUEST_KEYS),
                "POINTER_SMOKE_WORKER_CONTRACT_CHANGED")
        require(source.count(BOOTSTRAP_ENV_ANCHOR) == 1, "POINTER_BOOTSTRAP_SMOKE_ANCHOR")
        line, = [hold for hold in source.splitlines() if hold.strip() == BOOTSTRAP_ENV_ANCHOR]
        indent = line[:line.index(BOOTSTRAP_ENV_ANCHOR)]
        require(indent in ("", "    "), "POINTER_BOOTSTRAP_SMOKE_INDENT")
        assignment = indent + "os.environ[%r] = %r" % (worker.REDUCED_SCHEDULE_ENV, request)
        require(assignment.count("CNCM_POINTER_REDUCED_SCHEDULE") == 1 and "\n" not in assignment,
                "POINTER_BOOTSTRAP_SMOKE_ASSIGNMENT")
        source = source.replace(line, line + "\n" + assignment)
        require(source.count(worker.REDUCED_SCHEDULE_ENV) == 1, "POINTER_BOOTSTRAP_SMOKE_COUNT")
    else:
        require(source.count("CNCM_POINTER_REDUCED_SCHEDULE") == 0, "POINTER_BOOTSTRAP_SMOKE_LEAK")
    # Syntactic check on the generated source, whichever branch produced it: a bootstrap that does not parse would
    # otherwise be discovered on a paid instance, after the boot and package install.
    ast.parse(source)
    return source


def render_worker():
    # Its own module globals: a subclass of the practice launcher would render the practice worker here,
    # because `replacements` is read from this module's namespace.
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
    require(found == set(replacements) and timeouts == 1 and regions == 1, "POINTER_WORKER_TEMPLATE_CHANGED")
    tree.body[0] = ast.Expr(ast.Constant(CANDIDATE + ": pointer reading of one focus world with held-back "
                                         "questions; no learning claim is made by the worker."))
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def evidence_contract(plan=None, *, source=None):
    """The pre-run evidence contract for ONE plan. With `plan=None` this is the REGISTERED 10-pass contract.

    THE PLAN IS AN ARGUMENT BECAUSE A REDUCED RUN WRITES FEWER NAMES FROM THE DESIGN (review R2, B2). This
    function used to take no argument and list `_probe().EXPECTED_ARTIFACTS`, which is
    `expected_artifact_names(FULL_PLAN)` for the registered ten passes. A smoke job runs the reduced plan and
    writes only that plan's names, so `run_evidence.verify_byte_integrity` found the rest missing, set
    `INCOMPLETE`, and `completed_deliverable` came back false -- a PERFECT reduced run returned exit code 1 and
    `execute_study.py`'s `stop_unless(code == 0, 'INCOMPLETE_JOB')` stopped the study. The smoke plan's own
    section 5 had already corrected this on the WORKER side (the worker checks the plan it actually ran); this is
    the same correction on the LAUNCHER side.

    NOTHING IS RELAXED: the requirement list is still every name the plan produces, `verify_byte_integrity` still
    requires all of them, and `completed_deliverable` still requires `COMPLETE_VERIFIED`. The three claim-bearing
    jobs keep the no-argument form, whose bytes are unchanged: `plan=None` resolves to `_probe().FULL_PLAN`, which
    IS the plan `EXPECTED_ARTIFACTS` was derived from, and the note text is recomputed from the plan's own
    numbers, which reproduce the previously hard-coded ones exactly (1,470 main, 16 interference, 2 replay).

    `source` is the literal JSON request the generated bootstrap carries, when a smoke asked for one; it is
    recorded in the contract so the frozen requirement names the schedule it belongs to.
    """
    worker = _probe()
    plan = worker.FULL_PLAN if plan is None else plan
    names = {"results/result.json": "terminal envelope", "results/result.json.sha256": "envelope digest",
             "results/artifacts/manifest.json": "artifact inventory"}
    names.update({"results/artifacts/" + name: "complete typed-pointer worker evidence"
                  for name in worker.expected_artifact_names(plan)})
    parts = [plan["passes"] * contract.DESIGN["schedule_stratified_updates_per_pass"]
             - (contract.INTERFERENCE_UPDATES if plan["interference"] else 0)
             - (contract.REPLAY_UPDATES if plan["replays"] else 0),
             contract.INTERFERENCE_UPDATES if plan["interference"] else 0,
             contract.REPLAY_UPDATES if plan["replays"] else 0]
    document = run_evidence.contract(EXPERIMENT["profile"], [
        run_evidence.requirement(key, title, kind="json" if key.endswith(".json") else "file")
        for key, title in names.items()], notes=[
            "%d passes: %d main, %d interference and %d validation replay updates, %d actual total."
            % (plan["passes"], parts[0], parts[1], parts[2], parts[0] + parts[1] + parts[2]),
            "No held-back record enters a training batch; all declared checkpoints must arrive.",
            "One seed only; the three-seed gate reading is a separate deterministic program."])
    if source is not None:
        document["reduced_schedule_source"] = source
        document["claim_bearing"] = False
    return document


def smoke_plan(request=None):
    """`(plan, literal)` for the reduced schedule the smoke opt-in asks for. Refuses if no smoke was asked for."""
    literal, plan = smoke_request_literal(request)
    return plan, literal


def smoke_evidence_contract(request=None):
    """The SMOKE's own evidence contract: the names the REDUCED plan produces, and nothing else.

    Deliberately NOT the registered contract: the full name list is bound into the three claim-bearing jobs'
    authorities by `prepare_study.py`, and swapping it for them is exactly what must not happen. This contract is
    reached only while `SMOKE_REQUEST` is set, so a claim-bearing run cannot pick it up.

    `request` is the parsed request (the module global when omitted). It is NOT a JSON string -- `smoke_plan` and
    `smoke_request_literal` take the request dict, and `configure_reduced_schedule` is what turns a command-line
    literal into one.
    """
    plan, literal = smoke_plan(request)
    return evidence_contract(plan, source=literal)


def package_data_files(rows=None):
    """Every member name the package carries: the packaging sources, the wheel requirements and the input rows.

    The rows come from the SAME commit-read inventory the authority binds (`frozen_inputs`), so the file set and
    the admitted byte set cannot disagree.
    """
    rows = frozen_inputs() if rows is None else rows
    return tuple(sorted(set(shared.PILOT + name for name in PACKAGING_SOURCES)
                        | {shared.WORKER_REQUIREMENTS} | {item["path"] for item in rows}))


def git_package_bytes(root, commit, name):
    require(type(commit) is str and shared.HEX40.fullmatch(commit), "POINTER_SOURCE_COMMIT")
    shared.checked_names([name])
    # The eighteen checkpoint files under `records/typed_practice_001/receipt_<seed>/checkpoints/` are
    # admitted by the second clause alone: `pointer_contract.MATERIAL` is the practice MATERIAL plus
    # those eighteen rows (pointer_contract.py, "CHECKPOINT_PINS_MATERIAL"). Without them the build
    # refuses with POINTER_SOURCE_MEMBER_SCOPE (RK5). No third clause is added here.
    permitted = (name.startswith("research/") or name in contract.MATERIAL
                 or (name.startswith("cncm/") and name.endswith(".py")))
    require(permitted, "POINTER_SOURCE_MEMBER_SCOPE")
    return shared._run_git(["-c", "core.autocrlf=false", "show", commit + ":" + shared.GIT_PREFIX + name], root)


def build_pointer_package(output, *, source_sha, git_bytes_fn=None):
    """Exact committed member allowlist, as the practice package; this study's worker and manifest."""
    output = Path(output).absolute()
    require(not output.exists() and output.parent.is_dir() and output.is_relative_to(ROOT / "records")
            and output != ROOT / "records", "POINTER_FRESH_PACKAGE_PATH")
    require(type(source_sha) is str and shared.HEX40.fullmatch(source_sha), "POINTER_SOURCE_COMMIT")
    get_bytes = git_bytes_fn or git_package_bytes
    rows = frozen_inputs()
    names = package_data_files()
    shared.checked_names(list(names))
    members = {name: get_bytes(ROOT, source_sha, name) for name in names}
    for name in PACKAGING_SOURCES + ("requirements-gpu.txt",):
        require(members[shared.PILOT + name] == (ROOT / name).read_bytes(), "POINTER_PACKAGING_SOURCE_NOT_COMMITTED:" + name)
    for row in rows:
        raw = members[row["path"]]
        require(len(raw) == row["bytes"] and digest(raw) == row["sha256"], "POINTER_INPUT_NOT_COMMITTED:" + row["path"])
    source = render_worker()
    transport = run_evidence.unified_transport(source)
    members[WORKER_NAME] = run_evidence.unified_worker_source(source).encode("utf-8")
    require(all(len(raw) <= shared.MAX_MEMBER_BYTES for raw in members.values()), "POINTER_MEMBER_BOUND")
    manifest = shared.manifest_for(members, source_sha, worker_name=WORKER_NAME, experiment=EXPERIMENT,
                                   package_schema="cncm.typed-pointer-package/0.1", design=DESIGN)
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
            and sum(map(len, members.values())) <= shared.MAX_EXPANDED_BYTES, "POINTER_PACKAGE_BOUND")
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, raw in sorted(members.items()):
            info = ZipInfo(name, date_time=(2026, 9, 19, 0, 0, 0))
            info.compress_type, info.external_attr = ZIP_DEFLATED, 0o100644 << 16
            archive.writestr(info, raw)
    raw = buffer.getvalue()
    require(len(raw) <= shared.MAX_ARCHIVE_BYTES, "POINTER_ARCHIVE_BOUND")
    output.mkdir()
    (output / "source.zip").write_bytes(raw)
    receipt = {"schema": "cncm.typed-pointer-package-receipt/0.1", "status": "SOURCE_ONLY_NO_LAUNCH",
               "source_sha": source_sha, "archive": str(output / "source.zip"), "archive_sha256": digest(raw),
               "archive_bytes": len(raw), "manifest_sha256": digest(members[shared.MANIFEST_NAME]),
               "member_count": len(members), "manifest": manifest}
    (output / "receipt.json").write_bytes(canonical(receipt))
    return receipt


def reservation_plan_for(design):
    plan = shared.reservation_plan()
    plan["runtime_seconds_max"] = INSTANCE_SECONDS_MAX
    # The ledger row's own label. The practice study's "cncm_typed_practice_001" would silently
    # mislabel a pointer reservation (RK5).
    plan["task_scope"] = "cncm_typed_pointer_001"
    plan["frozen_budget"] = json.loads(canonical(design))
    return plan


class TypedPointerProvider(matched.TypedMatchedProvider):
    def reservation_plan(self):
        require(hasattr(self, "bound_config"), "POINTER_RESERVATION_CONFIG_REQUIRED")
        return reservation_plan_for(self.bound_config["design"])

    def reserve(self, amount):
        """The inherited lifecycle passes its own $7.00 constant; this study's frozen amount is $15.00."""
        require(hasattr(self, "bound_config"), "POINTER_RESERVATION_CONFIG_REQUIRED")
        require(not self._reserved and amount == shared.RESERVATION_USD, "POINTER_RESERVATION_CALLER")
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
        require(timeout == shared.RESOURCE_PLAN["instance_seconds_max"], "POINTER_WAIT_CALLER")
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
        require(re.fullmatch(JOB_PATTERN, self.job) is not None, "POINTER_WATCHDOG_JOB")
        require(hasattr(self, "bound_config") and self.bound_config["bucket"] == bucket, "POINTER_CONFIG_BUCKET")
        original = super(matched.TypedMatchedProvider, self)._user_data(bucket)
        anchor = "PY=''"
        require(original.count(anchor) == 1, "POINTER_BOOTSTRAP_CONFIG_ANCHOR")
        checks = ("echo '" + digest(canonical(self.bound_config)) + "  /opt/cas-graph6curr/package/config.json' | sha256sum -c -\n"
                  "echo '" + self.manifest_sha256 + "  /opt/cas-graph6curr/package/" + shared.MANIFEST_NAME + "' | sha256sum -c -\n")
        original = original.replace(anchor, checks + anchor)
        delimiter = "CNCM_POINTER_BOOTSTRAP_BODY"
        require(delimiter not in original.splitlines(), "POINTER_BOOTSTRAP_DELIMITER")
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

    def bind_authority(self, authority, evidence_contract=None):
        validate_authority(authority, evidence_contract)
        for key in ("job", "source_sha", "archive_sha256", "manifest_sha256"):
            require(getattr(self, key) == authority[key], "POINTER_PROVIDER_BINDING:" + key)
        self.bound_config = json.loads(canonical(authority["worker_config"]))
        self.worker_name, self.result_schema = WORKER_NAME, RESULT_SCHEMA
        # The new worker's FAILED result status, and the same tuple the collector reads at
        # `graph_training_curriculum_launch.py:1023` and `:1096`. Omitting it makes a failed job read as
        # REMOTE_FINISHED, and collection then demands an artifact manifest a failed worker cannot have
        # produced.
        self.failure_statuses = ("WORKER_FAILED", "REMOTE_WORKER_FAILED", "TYPED_POINTER_FAILED")

    def configure_evidence(self, directory, contract=None):
        """The inherited hook, plus THIS RUN's reduced-schedule record so the launch is reproducible.

        Overridden rather than reimplemented: the parent does the directory and contract work, and this adds one
        file to the same evidence directory -- written here because this is the one point every launch reaches
        before the reservation. A claim-bearing run records `None`, so its receipt says plainly that no shrunken
        schedule was requested.
        """
        state = super().configure_evidence(directory, contract)
        target = Path(directory).resolve()
        require(target.is_dir(), "POINTER_EVIDENCE_DIRECTORY")
        shared.write_evidence(target / "reduced_schedule.json", canonical({
            "schema": "cncm.typed-pointer-reduced-schedule/0.1", "job": self.job,
            "reduced_schedule": reduced_schedule_record(),
            "how_it_crossed_the_process_boundary": ("typed_pointer_launch.main(--reduced-schedule), which calls "
                                                    "configure_reduced_schedule() before any validation"),
            "ambient_environment_read": False}))
        return state

    def _worker_config(self, bucket):
        require(hasattr(self, "bound_config"), "POINTER_AUTHORITY_NOT_BOUND")
        require(self.region == BOUNDS["region"], "POINTER_PROVIDER_REGION")
        require(bucket == self.bound_config["bucket"], "POINTER_PROVIDER_BUCKET")
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
            "POINTER_RESERVATION_AMOUNT_FROZEN")
    require(entry["plan"] == expected_plan and entry["plan_sha256"] == budget.digest(budget.encoded(expected_plan)),
            "RESERVATION_RESOURCE_PLAN_MISMATCH")
    require(receipt.get("ledger_sha256") == after["ledger_sha256"], "RESERVATION_RECEIPT_HASH_MISMATCH")
    return receipt


def job_evidence_contract():
    """The contract THIS PROCESS's run will be held to.

    `SMOKE_REQUEST is None` -- the state every claim-bearing job runs in -- returns the REGISTERED 10-pass
    contract, byte for byte what this launcher has always built, so the three claim-bearing authorities' pinned
    `evidence_contract_sha256` values still validate. With the opt-in set, the smoke's own reduced contract is
    returned, and it is the ONLY thing that changes for a smoke: same `verify_byte_integrity`, same
    `completed_deliverable`, same `main()` exit-code rule.
    """
    return evidence_contract() if SMOKE_REQUEST is None else smoke_evidence_contract()


def execute(request, authority, provider, *, receipt_dir, owner_authorization_path, ledger_path):
    contract_for_this_job = job_evidence_contract()
    validate_request(request)
    validate_authority(authority, contract_for_this_job)
    validate_owner(owner_authorization_path, authority)
    ledger_path = validate_ledger_path(ledger_path)
    require(Path(provider.ledger_path).resolve() == ledger_path, "POINTER_PROVIDER_LEDGER_MISMATCH")
    require(isinstance(provider, TypedPointerProvider), "POINTER_PROVIDER_REQUIRED")
    provider.bind_authority(authority, contract_for_this_job)
    return lifecycle.execute(request, authority, provider, ledger_path=ledger_path,
        receipt_dir=receipt_dir, owner_authorization_path=owner_authorization_path,
        validate_request_fn=validate_request,
        validate_authority_fn=lambda document: validate_authority(document, contract_for_this_job),
        evidence_contract=contract_for_this_job,
        validate_reserved_transition_fn=lambda before, after, receipt, request:
            validate_reserved_transition(before, after, receipt, request, expected_plan=provider.reservation_plan()))


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--package")
    parser.add_argument("--source-sha")
    # THE CROSS-PROCESS CARRY FOR THE SHRUNKEN SCHEDULE. `prepare_smoke.py` prints this exact literal; nothing else
    # sets it, and ambient environment is read nowhere. Absent, every path behaves as if the opt-in did not exist.
    parser.add_argument("--reduced-schedule")
    for field in ("request", "request-sha256", "authority", "authority-sha256", "receipt-dir", "owner-authorization",
                  "ledger-path"):
        parser.add_argument("--" + field)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    if args.reduced_schedule is not None:
        # A package must be built with the opt-in UNSET: the generated source is one of its members, so building a
        # package under a reduced request would change the bytes every job installs.
        require(not args.package, "POINTER_REDUCED_SCHEDULE_WITH_PACKAGE")
        reduced_literal, reduced_plan = configure_reduced_schedule(args.reduced_schedule)
    else:
        reduced_literal, reduced_plan = configure_reduced_schedule(None)
    require(SMOKE_REQUEST is None or reduced_literal is not None, "POINTER_REDUCED_SCHEDULE_NOT_CONFIGURED")
    if args.package:
        require(not args.execute and args.source_sha, "POINTER_PACKAGE_ARGUMENTS")
        print(json.dumps(build_pointer_package(args.package, source_sha=args.source_sha)))
        return 0
    if not args.execute:
        print(json.dumps({"status": "PLAN_ONLY", "design": DESIGN, "bounds": BOUNDS, "provider_calls": 0,
                          "reservation_created": False, "reduced_schedule_literal": reduced_literal,
                          "reduced_schedule_plan": reduced_plan}))
        return 0
    require(all(getattr(args, key) for key in ("request", "request_sha256", "authority", "authority_sha256",
                                               "receipt_dir", "owner_authorization", "ledger_path")), "POINTER_EXPLICIT_INPUTS")
    request_raw, authority_raw = Path(args.request).read_bytes(), Path(args.authority).read_bytes()
    require(digest(request_raw) == args.request_sha256 and digest(authority_raw) == args.authority_sha256,
            "POINTER_REQUEST_AUTHORITY_FILE_HASH")
    request, authority = json.loads(request_raw), json.loads(authority_raw)
    contract_for_this_job = job_evidence_contract()
    validate_request(request)
    validate_authority(authority, contract_for_this_job)
    validate_owner(args.owner_authorization, authority)
    ledger_path = validate_ledger_path(args.ledger_path)
    provider = TypedPointerProvider(job=request["job"], source_sha=request["source_sha"],
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
