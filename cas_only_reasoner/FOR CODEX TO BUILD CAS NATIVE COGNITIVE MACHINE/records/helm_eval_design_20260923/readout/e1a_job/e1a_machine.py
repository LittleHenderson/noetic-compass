"""E1a machine program: the stages that run on the ONE AWS T4 machine (readout plan item 9). CLAUDE_BUILT_CLAUDE_CHECKED.

NOT RUN YET. Its torch parts run only on the AWS machine. The pure parts are unit-tested on the laptop with stand-ins
(test_e1a_job.py). It never trains, never writes a checkpoint, reads no TEST data and prints no analogy number.

Subcommands (job.sh.template calls them in this order):
  anchors   --root PKG                       every bundled file against anchors.json (sha256), and no unlisted file
  smoke     --out OUT --expect-torch V       torch build, CUDA, a T4
  preflight --tree T --spec S --out OUT --job-start EPOCH --budget-seconds N
            loads the course, times real probe calls and fixture calls, projects the whole job; exit 5 when the
            projection is over the wall budget or a harness process would pass its own 3,600 s wall
  route     --tree T --spec S --out OUT      stage 1: the smoke ON final.pt and the six study finals through the
            e05889ee route (`larger_question_learner.predict_packet`): repaired and smoke with the switch ON, unchanged
            with the switch OFF; the switch is read back and asserted; the 37 public gradable fixtures go read ->
            forward -> decode -> grade with no error and the 4 refusal fixtures refuse before any forward. NO
            right/wrong, answer digest or check digest is written (prereg A5.1: no repaired analogy number).
  reads     --tree T --spec S --out OUT --job-start EPOCH --budget-seconds N [--python PY]
            stage 3: the 18 probe v0.3 reads (3 seeds x 6 checkpoints), in two waves of three harness processes
            (3 models each). It FIRST re-derives the stage-2 validation from the raw tables with the frozen metric;
            without VALIDATION_PASS it starts nothing (READS_NOT_STARTED.json, exit 3).
  matched   --tree T --spec S --out OUT      stage 4: matched_start.py --self-test (Helm 2.0 files), then, only after
            MATCHED_START_SELF_TEST:PASS, the A5.5 reading on the three repaired starts
  roster    --tree T --spec S --out OUT      stage 5: check_roster.py --arm repaired on each repaired receipt
  inputs    --tree T --spec S --out OUT      ITEM2_INPUTS.json for item2_reader.py: every checkpoint sha256 and update
            count comes from the receipt through the roster checker (inventory-verified), never from the harness
  decide    --out OUT                        E1A_RESULT.json: the verdict WORDS of every stage; exit 0 when every stage
            produced its reading (whatever it says), else 1

Exit codes: 0 ok; 1 a stage failed or is incomplete; 2 GPU_REQUIRED / tool stop; 3 reads not started (validation did
not pass); 5 PREFLIGHT_OVER_WALL_LIMIT.
"""
import argparse
import hashlib
import importlib
import io
import json
import os
import pathlib
import subprocess
import sys
import time

SPEC_SCHEMA = "claude.e1a-spec/0.1"
RESULT_SCHEMA = "claude.e1a-result/0.1"
SWITCH_ATTR = "analogy_focus_comparison"
# records/typed_pointer_001/admission_analogy_on_001/MIGRATION_ON_SHAPES.json (commit afccbcb9): switch ON 53 state
# keys / 203,424 parameters; switch OFF (Helm 2.0) 48 keys / 174,303 (ON minus the five analogy_head tensors, 29,121).
PARAMETERS = {True: 203424, False: 174303}
STATE_KEYS = {True: 53, False: 48}
HARNESS_WALL_SECONDS = 3600          # probe_v0_3_harness.WALL_SECONDS (v0.2's limit, unchanged)
PREFLIGHT_MARGIN = 1.15
TAIL_SECONDS = 300                   # inputs, ITEM2 reader, decide, tar and upload
VALIDATION_TABLES = 5                # V1-V5 raw tables (V6, V7 are arithmetic on them)
MODELS_PER_PROCESS = 3               # probe_v0_3_harness.MAX_MODELS
LABELS = ["CLAUDE_BUILT_CLAUDE_CHECKED", "EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT"]
# The decide step prints ONLY these words. A score, a correctness count or an analogy accuracy never appears here.
STAGES = ("smoke", "preflight", "route", "validation", "reads", "item2", "matched_start_self_test",
          "matched_start", "roster")


class Stop(Exception):
    def __init__(self, code, detail=""):
        super().__init__("%s:%s" % (code, detail))
        self.code, self.detail = code, detail


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def write_create_only(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(obj, indent=1, sort_keys=True) + "\n")
    return sha256_file(path)


def read_json(path):
    try:
        return json.loads(pathlib.Path(path).read_bytes().decode("utf-8"))
    except (OSError, ValueError):
        return None


def load_spec(path):
    spec = read_json(path)
    if not isinstance(spec, dict) or spec.get("schema") != SPEC_SCHEMA:
        raise Stop("SPEC_UNREADABLE", str(path))
    if spec.get("receipts_missing"):
        raise Stop("SPEC_HAS_MISSING_RECEIPTS", spec["receipts_missing"])
    return spec


def import_from(folder, name):
    folder = str(pathlib.Path(folder).resolve())
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return importlib.import_module(name)


# ================================================================ anchors
def check_anchors(root):
    root = pathlib.Path(root)
    anchors = json.loads((root / "anchors.json").read_bytes())["files"]
    bad = [n for n, row in anchors.items() if not (root / n).is_file() or sha256_file(root / n) != row["sha256"]]
    present = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    extra = [p for p in present if p != "anchors.json" and p not in anchors]
    print("bundled files checked: %d; bad or missing: %d; unlisted: %d" % (len(anchors), len(bad), len(extra)))
    for name in (bad + extra)[:10]:
        print("  %s" % name)
    return 0 if not bad and not extra else 1


# ================================================================ smoke (torch, GPU)
def smoke(out, expect_torch):
    problems, record = [], {"schema": "claude.e1a-smoke/0.1"}
    import torch
    record.update(torch=torch.__version__, cuda_available=torch.cuda.is_available(), cuda_runtime=torch.version.cuda,
                  cudnn=torch.backends.cudnn.version(), python=sys.version.split()[0])
    if torch.__version__ != expect_torch:
        problems.append("TORCH_VERSION:" + torch.__version__)
    if torch.cuda.is_available():
        record["device_name"] = torch.cuda.get_device_name(0)
        record["cuda_sum"] = float(torch.ones(8, device="cuda").sum().item())
        if "T4" not in record["device_name"] or record["cuda_sum"] != 8.0:
            problems.append("GPU:" + record["device_name"])
    else:
        problems.append("NO_CUDA")
    record["problems"], record["verdict"] = problems, ("SMOKE_PASS" if not problems else "SMOKE_FAIL")
    write_create_only(pathlib.Path(out) / "smoke.json", record)
    print(json.dumps(record, sort_keys=True))
    return 0 if not problems else 1


# ================================================================ preflight (pure projection + torch measurement)
def contention(processes):
    """A conservative slowdown for `processes` probe processes sharing one T4 and 8 vCPU: only two run at full speed."""
    return max(1.0, processes / 2.0)


def project(m, budget_seconds, harness_wall=HARNESS_WALL_SECONDS, margin=PREFLIGHT_MARGIN, tail=TAIL_SECONDS):
    """The whole job's projected end, in seconds after JOB START. Pure.

    m: elapsed_s (JOB START to the end of the preflight), load_s (one process's setup + course load), call_s (seconds
    per probe score call), calls_per_table, table_prep_s, fixture_s (seconds per route fixture call), containers,
    fixtures_per_container, waves, processes_per_wave.
    Stage group 1 runs the validation (5 tables, one process) beside the route stage; then the reads run in `waves`
    waves of `processes_per_wave` harness processes of MODELS_PER_PROCESS models each."""
    t_table = m["calls_per_table"] * m["call_s"] + m["table_prep_s"]
    validation = m["load_s"] + VALIDATION_TABLES * t_table * contention(2)
    route = m["load_s"] + m["containers"] * (m["fixtures_per_container"] * m["fixture_s"] + 5.0) * contention(2)
    read_process = m["load_s"] + MODELS_PER_PROCESS * t_table * contention(m["processes_per_wave"])
    reads = m["waves"] * read_process
    total = m["elapsed_s"] + margin * (max(validation, route) + reads) + tail
    problems = []
    if total > budget_seconds:
        problems.append("PROJECTED_END_%ds_OVER_BUDGET_%ds" % (total, budget_seconds))
    if margin * validation > 0.9 * harness_wall:
        problems.append("VALIDATION_PROCESS_%ds_OVER_HARNESS_WALL" % (margin * validation))
    if margin * read_process > 0.9 * harness_wall:
        problems.append("READ_PROCESS_%ds_OVER_HARNESS_WALL" % (margin * read_process))
    return {"t_table_s": t_table, "validation_s": validation, "route_s": route, "read_process_s": read_process,
            "reads_s": reads, "projected_end_s": total, "budget_s": budget_seconds, "margin": margin, "tail_s": tail,
            "problems": problems, "verdict": "PREFLIGHT_PASS" if not problems else "PREFLIGHT_OVER_WALL_LIMIT"}


def _harness_env(tree, spec):
    """Import the probe harness beside its side files and run its own `_setup` (GPU admission, course load)."""
    import types
    H = import_from(pathlib.Path(tree) / spec["probe_dir"], "probe_v0_3_harness")
    started = time.monotonic()
    env = H._setup(types.SimpleNamespace(package_root=str(tree)))
    return H, env, time.monotonic() - started


def preflight(tree, spec_path, out, job_start, budget_seconds):
    spec = load_spec(spec_path)
    tree = pathlib.Path(tree)
    H, env, load_s = _harness_env(tree, spec)
    torch = env.torch
    # (a) the exact number of score calls one full table makes: the same builder with a stand-in scorer that returns
    # the real candidate set (no forward pass).
    candidates = {}
    for rid in env.analogy_ids:
        packet = env.packets[rid]
        slot = [s for s in env.slots.compile_slots(packet)["slots"] if s["field"] == "world_id"][0]
        reading = env.pointer_inputs.read_packet(packet)
        candidates[rid] = sorted({env.PL._world_alias_table_for(reading, s) for s in slot["symbols"] if s != "NO_MATCH"})
    counted = [0]

    def counting(rid, packet, changed):
        counted[0] += 1
        return {c: 0.0 for c in candidates[rid]}
    H.build_score_table(env.packets, env.analogy_ids, counting, env.pointer_inputs._node_index, model={},
                        provenance={}, witnesses=H.metric.RULES["witnesses"])
    # (b) real probe calls on a fresh switch-ON container: one focus, all its counterfactuals.
    model, _info = H._build_model(env, "preflight_on", spec["seeds"][0], None, spec["read_container_kwargs"],
                                  spec["switch_attr"], "true")
    t0 = time.monotonic()
    real = H._score_fn(env, model)
    table_prep_s = time.monotonic() - t0
    timed = [0]

    def timing(rid, packet, changed):
        timed[0] += 1
        return real(rid, packet, changed)
    t0 = time.monotonic()
    H.build_score_table(env.packets, env.analogy_ids[:1], timing, env.pointer_inputs._node_index, model={},
                        provenance={}, witnesses=H.metric.RULES["witnesses"])
    call_s = (time.monotonic() - t0) / max(1, timed[0])
    del model
    # (c) route fixture calls on a fresh switch-OFF container.
    from eval_paths import larger_question_scope as scope
    scope.verify_source_pins()
    from eval_paths import larger_question_fixtures as FX, larger_question_learner as LL
    document, fixtures = FX.load()
    larger = sorted(r["fixture_id"] for r in document["fixtures"] if "expected_refusal" not in r)
    off = env.PL._build_container(torch, env._framework(torch, env.device, spec["seeds"][0]), env.device,
                                  **{SWITCH_ATTR: False})
    off.eval()
    tagger = env.PL.role_tagger(str(tree))
    t0 = time.monotonic()
    for key in larger[:3]:
        LL.predict_packet(torch, off, fixtures[key], env.device, tagger=tagger)
    fixture_s = (time.monotonic() - t0) / 3
    measured = {"elapsed_s": time.time() - job_start, "load_s": load_s, "call_s": call_s,
                "calls_per_table": counted[0], "table_prep_s": table_prep_s, "fixture_s": fixture_s,
                "timed_calls": timed[0], "containers": len(spec["route_containers"]),
                "fixtures_per_container": len(larger), "waves": len(spec["waves"]),
                "processes_per_wave": len(spec["seeds"])}
    result = project(measured, budget_seconds)
    record = {"schema": "claude.e1a-preflight/0.1", "measured": measured, "projection": result,
              "verdict": result["verdict"], "gpu": H.gpu_telemetry(), "labels": LABELS}
    write_create_only(pathlib.Path(out) / "PREFLIGHT.json", record)
    print(json.dumps({"verdict": result["verdict"], "projected_end_s": round(result["projected_end_s"]),
                      "budget_s": budget_seconds, "problems": result["problems"]}))
    return 0 if result["verdict"] == "PREFLIGHT_PASS" else 5


# ================================================================ route (stage 1; torch, GPU)
def route_verdict(rows, expected_count):
    """ROUTE_RECEIPT_PASS only when every listed container read back its switch, loaded strictly, had no fixture
    error and refused every refusal fixture before any forward."""
    failed = [r["label"] for r in rows if r.get("problems")]
    if len(rows) != expected_count:
        failed.append("CONTAINER_COUNT:%d/%d" % (len(rows), expected_count))
    return ("ROUTE_RECEIPT_PASS" if not failed else "ROUTE_RECEIPT_FAIL"), failed


def route(tree, spec_path, out):
    spec = load_spec(spec_path)
    tree, out = pathlib.Path(tree), pathlib.Path(out) / "route"
    receipt_path, rows_path = out / "ROUTE_RECEIPT.json", out / "route_rows.jsonl"
    if receipt_path.exists() or rows_path.exists():
        raise Stop("OUTPUT_EXISTS", str(receipt_path))
    out.mkdir(parents=True, exist_ok=True)
    import torch
    if not torch.cuda.is_available():
        print("GPU_REQUIRED")
        return 2
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark = True, False
    device = torch.device("cuda", 0)
    for path in (tree, tree / "research" / "CAS_META_2_COMPOSITION"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    sys.dont_write_bytecode = True
    from eval_paths import larger_question_scope as scope
    pins = scope.verify_source_pins()                      # the route's own entry-point pin check, before any load
    from eval_paths import larger_question_fixtures as FX, larger_question_learner as LL
    from cas_meta2.typed_teaching import answers, pointer_learner as PL
    from cncm.typed_matched_worker import _framework
    tagger = PL.role_tagger(str(tree))
    document, fixtures = FX.load()
    fixture_rows = {row["fixture_id"]: row for row in document["fixtures"]}
    larger = sorted(k for k, r in fixture_rows.items() if "expected_refusal" not in r)
    refused = sorted(k for k, r in fixture_rows.items() if "expected_refusal" in r)
    original_forward, calls = LL.GraphForward, [0]

    def counting(*args, **kwargs):
        calls[0] += 1
        return original_forward(*args, **kwargs)

    rows = []
    with open(rows_path, "x", encoding="utf-8", newline="\n") as stream:
        def emit(row):
            stream.write(canonical(row) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

        for c in spec["route_containers"]:
            row = {k: c.get(k) for k in ("label", "arm", "seed", "checkpoint", "sha256", "switch")}
            row["problems"] = []
            try:
                raw = (tree / c["checkpoint"]).read_bytes()
                row["observed_sha256"] = sha256_bytes(raw)
                if row["observed_sha256"] != c["sha256"]:
                    raise Stop("CHECKPOINT_SHA256_MISMATCH")
                model = PL._build_container(torch, _framework(torch, device, int(c["seed"])), device,
                                            **{SWITCH_ATTR: bool(c["switch"])})
                payload = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
                if type(payload) is not dict or "model_state" not in payload:
                    raise Stop("CHECKPOINT_PAYLOAD_HAS_NO_MODEL_STATE")
                model.load_state_dict(payload["model_state"], strict=True)
                model.eval()
                value = getattr(model, SWITCH_ATTR, None)
                row["switch_read_back"] = value if type(value) is bool else repr(value)
                if type(value) is not bool or value is not bool(c["switch"]):
                    row["problems"].append("SWITCH_STATE_MISMATCH")
                row["state_tensors"] = len(payload["model_state"])
                row["parameter_count"] = int(sum(p.numel() for p in model.parameters()))
                if row["parameter_count"] != PARAMETERS[bool(c["switch"])]:
                    row["problems"].append("PARAMETER_COUNT")
                if row["state_tensors"] != STATE_KEYS[bool(c["switch"])]:
                    row["problems"].append("STATE_KEY_COUNT")
            except Stop as stop:
                row["problems"].append(stop.code)
                rows.append(row)
                emit({"row": "container", **row})
                continue
            except Exception as error:  # noqa: BLE001 -- recorded, the container fails
                row["problems"].append("LOAD_ERROR:%s:%s" % (type(error).__name__, str(error)[:300]))
                rows.append(row)
                emit({"row": "container", **row})
                continue
            errors = 0
            for key in larger:
                packet = fixtures[key]
                try:
                    result = LL.predict_packet(torch, model, packet, device, tagger=tagger)
                    if result["route"] != scope.LARGER:
                        raise ValueError("ROUTE:" + result["route"])
                    if canonical(result["plan"]) != canonical(scope.compile_plan(packet)[1]):
                        raise ValueError("PLAN_DIFFERS_FROM_SCOPE_PLAN")
                    answers.validate_answer(packet["source"], packet["record"]["query"], result["answer"])
                    grade = scope.grade(packet, result["answer"])
                    if type(grade.get("correct")) is not bool:
                        raise ValueError("GRADE_NOT_BOOLEAN")
                    # Deliberately NOT written: correct, the answer, an answer digest, the check digest (A5.1).
                    fixture = {"fixture_id": key, "kind": fixture_rows[key].get("kind"), "route": result["route"],
                               "slots": len(result["plan"]["slots"]),
                               "plan_sha256": sha256_bytes(canonical(result["plan"]).encode()),
                               "logit_bits": LL.logit_bits_digest(torch, result["rows"]),
                               "graded_by": grade.get("checker_module"), "graded": True}
                except Exception as error:  # noqa: BLE001 -- every error is recorded and fails the container
                    errors += 1
                    fixture = {"fixture_id": key, "error": {"type": type(error).__name__, "message": str(error)[:300]}}
                emit({"row": "fixture", "container": c["label"], **fixture})
            refusals_ok = 0
            for key in refused:
                before = calls[0]
                LL.GraphForward = counting
                try:
                    LL.predict_packet(torch, model, fixtures[key], device, tagger=tagger)
                    outcome = {"refused": False}
                except scope.LargerPathRefusal as error:
                    outcome = {"refused": True, "code": error.code}
                except Exception as error:  # noqa: BLE001
                    outcome = {"refused": False, "error": type(error).__name__}
                finally:
                    LL.GraphForward = original_forward
                expected = fixture_rows[key]["expected_refusal"]
                ok = outcome["refused"] and outcome.get("code") == expected and calls[0] == before
                refusals_ok += bool(ok)
                emit({"row": "refusal", "container": c["label"], "fixture_id": key, "expected_code": expected,
                      "graph_forward_calls": calls[0] - before, "ok": ok, **outcome})
            row.update(fixtures=len(larger), fixture_errors=errors, refusals=len(refused), refusals_ok=refusals_ok)
            if errors:
                row["problems"].append("FIXTURE_ERRORS:%d" % errors)
            if refusals_ok != len(refused):
                row["problems"].append("REFUSALS_OK:%d/%d" % (refusals_ok, len(refused)))
            rows.append(row)
            emit({"row": "container", **row})
            del model
            torch.cuda.empty_cache()
    verdict, failed = route_verdict(rows, len(spec["route_containers"]))
    receipt = {"schema": "claude.e1a-route-receipt/0.1", "verdict": verdict, "failed": failed, "containers": rows,
               "route_source_commit": spec.get("source_commit"), "protected_source_lf_sha256": pins,
               "fixture_file_sha256": sha256_file(pathlib.Path(FX.FIXTURE_PATH)),
               "fixtures_gradable": len(larger), "fixtures_refusal": len(refused),
               "rows_sha256": sha256_file(rows_path), "torch": torch.__version__,
               "device": torch.cuda.get_device_name(0),
               "boundary": ("Route plumbing only: forward passes under no_grad; no right/wrong, answer digest or check "
                            "digest is written, so no analogy number of any arm can be read from this receipt."),
               "labels": LABELS}
    write_create_only(receipt_path, receipt)
    print(json.dumps({"route": verdict, "failed": failed}))
    return 0 if verdict == "ROUTE_RECEIPT_PASS" else 1


# ================================================================ reads (stage 3)
def validation_passed(summary_path, probe_dir):
    """(passed, words). Re-derives the stage-2 validation from the raw tables with the FROZEN metric (as
    item2_reader.py does); the harness's own printed verdict is not trusted."""
    summary_path = pathlib.Path(summary_path)
    summary = read_json(summary_path)
    if not isinstance(summary, dict) or not isinstance(summary.get("tables"), dict):
        return False, "VALIDATION_SUMMARY_MISSING_OR_MALFORMED"
    tables = {}
    for case, row in sorted(summary["tables"].items()):
        path = summary_path.parent / str(row.get("file"))
        if not path.is_file():
            return False, "VALIDATION_TABLE_MISSING:" + case
        raw = path.read_bytes()
        if sha256_bytes(raw) != row.get("sha256"):
            return False, "VALIDATION_TABLE_SHA256_MISMATCH:" + case
        tables[case] = json.loads(raw.decode("utf-8"))
    metric = import_from(probe_dir, "probe_v0_3_metric")
    before, after = (summary.get("pointer_learner_sha256_lf_before_after") or [None, None])[:2]
    verdict = metric.evaluate_validation(tables, before, after)
    words = verdict["validation"] + ("" if not verdict.get("failed") else ":" + ",".join(verdict["failed"]))
    return verdict["validation"] == "VALIDATION_PASS", words


def harness_command(py, probe_dir, tree, out_dir, spec, seed, models):
    cmd = [py, "-B", str(pathlib.Path(probe_dir) / "probe_v0_3_harness.py"), "read", "--out-dir", str(out_dir),
           "--container-kwargs", json.dumps(spec["read_container_kwargs"], sort_keys=True),
           "--switch-attr", spec["switch_attr"], "--switch-expect", "true", "--package-root", str(tree)]
    for model in models:
        # The harness splits LABEL:SEED:CHECKPOINT on the first two colons only, so only the label must be colon-free.
        if ":" in model["label"] or not model["label"]:
            raise Stop("MODEL_LABEL", model["label"])
        cmd += ["--model", "%s:%d:%s" % (model["label"], int(seed), pathlib.Path(tree) / model["checkpoint"])]
    return cmd


def run_reads(spec, tree, out, py, job_start, budget_seconds, popen=subprocess.Popen, clock=time.time):
    tree, probe_out = pathlib.Path(tree), pathlib.Path(out) / "probe"
    probe_dir = tree / spec["probe_dir"]
    record_path = probe_out / "READS_RECORD.json"
    if record_path.exists() or (probe_out / "READS_NOT_STARTED.json").exists():
        raise Stop("OUTPUT_EXISTS", str(record_path))
    ok, words = validation_passed(probe_out / "validation" / "validation_summary.json", probe_dir)
    if not ok:
        write_create_only(probe_out / "READS_NOT_STARTED.json",
                          {"schema": "claude.e1a-reads/0.1", "verdict": "READS_NOT_STARTED_VALIDATION_NOT_PASSED",
                           "validation": words, "rule": "PREREG v0.3 section 6: the 18 reads do not start"})
        print(json.dumps({"reads": "NOT_STARTED", "validation": words}))
        return 3
    reads_dir, logs = probe_out / "reads", probe_out / "logs"
    reads_dir.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    record = {"schema": "claude.e1a-reads/0.1", "validation": words, "waves": [], "stopped": None}
    for number, indices in enumerate(spec["waves"], 1):
        if record["waves"]:
            last = record["waves"][-1]["seconds"]
            if clock() - job_start + 1.1 * last + TAIL_SECONDS > budget_seconds:
                record["stopped"] = "WALL_BUDGET_WOULD_BE_EXCEEDED_BEFORE_WAVE_%d" % number
                break
        started, running = clock(), []
        for seed in spec["seeds"]:
            models = [spec["reads"][str(seed)][i] for i in indices]
            cmd = harness_command(py, probe_dir, tree, reads_dir, spec, seed, models)
            log = open(logs / ("read_%s_wave%d.log" % (seed, number)), "w", encoding="utf-8")
            running.append((str(seed), [m["label"] for m in models], popen(cmd, stdout=log, stderr=subprocess.STDOUT), log))
        codes = {}
        for seed, labels, proc, log in running:
            codes[seed] = {"exit": proc.wait(), "labels": labels}
            log.close()
        record["waves"].append({"wave": number, "processes": codes, "seconds": clock() - started})
    complete = (record["stopped"] is None and len(record["waves"]) == len(spec["waves"])
                and all(p["exit"] == 0 for w in record["waves"] for p in w["processes"].values()))
    record["verdict"] = "READS_COMPLETE" if complete else "READS_INCOMPLETE"
    write_create_only(record_path, record)
    print(json.dumps({"reads": record["verdict"], "stopped": record["stopped"],
                      "exits": [{s: p["exit"] for s, p in w["processes"].items()} for w in record["waves"]]}))
    return 0 if complete else 1


# ================================================================ stage 4 (matched start) and stage 5 (roster)
def matched_commands(spec, tree, out, py):
    """The two matched_start.py runs: the real-file self-test (Helm 2.0 files only), then the A5.5 reading."""
    tree, folder = pathlib.Path(tree), pathlib.Path(out) / "matched_start"
    program = str(tree / spec["matched_start_dir"] / "matched_start.py")
    helm2 = [a for s in spec["seeds"] for a in ("--helm2", "%s=%s" % (s, tree / spec["helm2_initial"][str(s)]))]
    on = [a for s in spec["seeds"] for a in ("--on", "%s=%s" % (s, tree / spec["matched_start_on_dirs"][str(s)]))]
    return ([py, "-B", program, "--self-test"] + helm2 + ["--out", str(folder / "SELF_TEST.json")],
            [py, "-B", program] + on + helm2 + ["--out", str(folder / "MATCHED_START_READING.json")])


def run_matched(spec, tree, out, py, run=subprocess.run):
    """Self-test first; the reading runs only after MATCHED_START_SELF_TEST:PASS (exit 0). Returns 0 when the reading
    was produced (whatever it says), 1 otherwise; every exit code is kept in EXITS.json."""
    folder = pathlib.Path(out) / "matched_start"
    folder.mkdir(parents=True, exist_ok=True)
    self_test, reading = matched_commands(spec, tree, out, py)
    exits = {}
    with open(folder / "self_test.log", "w", encoding="utf-8") as log:
        exits["self_test"] = run(self_test, stdout=log, stderr=subprocess.STDOUT).returncode
    if exits["self_test"] == 0:
        with open(folder / "reading.log", "w", encoding="utf-8") as log:
            exits["reading"] = run(reading, stdout=log, stderr=subprocess.STDOUT).returncode
    else:
        exits["reading"] = "NOT_RUN_SELF_TEST_DID_NOT_PASS"
    write_create_only(folder / "EXITS.json", exits)
    print(json.dumps({"matched_start_exits": exits}))
    return 0 if exits["reading"] in (0, 3) else 1


def run_roster(spec, tree, out, py, run=subprocess.run):
    """check_roster.py --arm repaired --json on each repaired receipt -> roster/roster_<seed>.json."""
    tree, folder = pathlib.Path(tree), pathlib.Path(out) / "roster"
    folder.mkdir(parents=True, exist_ok=True)
    program = str(tree / spec["roster_dir"] / "check_roster.py")
    exits = {}
    for seed in spec["seeds"]:
        target = folder / ("roster_%s.json" % seed)
        with open(target, "x", encoding="utf-8") as stream:
            exits[str(seed)] = run([py, "-B", program, "--arm", "repaired", "--json",
                                    str(tree / spec["repaired_receipts"][str(seed)])],
                                   stdout=stream, stderr=subprocess.DEVNULL).returncode
    print(json.dumps({"roster_exits": exits}))
    return 0 if all(code in (0, 1, 3) for code in exits.values()) else 1


# ================================================================ ITEM2 inputs
def item2_inputs(spec, tree, out, roster):
    """ITEM2_INPUTS.json (schema claude.item2-inputs/0.3). The checkpoint sha256 and the update count of each of the
    18 entries come from the receipt, through `roster.check_receipt` (inventory-verified); a problem leaves them
    None, which the ITEM2 reader reads as a failure, never a skip."""
    tree, probe_out = pathlib.Path(tree), pathlib.Path(out) / "probe"
    target = probe_out / "ITEM2_INPUTS.json"
    if target.exists():
        raise Stop("OUTPUT_EXISTS", str(target))
    entries = []
    for seed in spec["seeds"]:
        folder = spec["repaired_receipts"][str(seed)]
        report = roster.check_receipt(str(tree / folder), "repaired")
        rows = {row["label"]: row for row in report["rows"]}
        for read in spec["reads"][str(seed)]:
            row = rows.get(read["roster_label"]) or {}
            counts = row.get("updates") or {}
            values = {canonical(v) for v in counts.values()}
            updates = next(iter(counts.values())) if counts and len(values) == 1 else None
            table_rel = "reads/%s.score_table.json" % read["label"]
            table = probe_out / table_rel
            entries.append({"model_seed": int(seed), "checkpoint_relative_path": read["checkpoint_relative_path"],
                            "main_updates": updates, "checkpoint_sha256": row.get("sha256"),
                            "receipt_root": "%s@%s" % (folder, spec["repaired_commit"]),
                            "roster_row_status": row.get("status"), "roster_verdict": report.get("verdict"),
                            "score_table": table_rel,
                            "score_table_sha256": sha256_file(table) if table.is_file() else None})
    summary = probe_out / "validation" / "validation_summary.json"
    acceptance = None
    if spec.get("acceptance_record"):
        source = tree.parent / spec["acceptance_record"]
        if source.is_file():
            (probe_out / "acceptance_record.json").write_bytes(source.read_bytes())
            acceptance = "acceptance_record.json"
    inputs = {"schema": "claude.item2-inputs/0.3", "entries": entries,
              "validation_summary": "validation/validation_summary.json",
              "validation_summary_sha256": sha256_file(summary) if summary.is_file() else None,
              "acceptance_record": acceptance}
    write_create_only(target, inputs)
    print(json.dumps({"item2_inputs": len(entries), "acceptance_record": acceptance}))
    return 0


# ================================================================ decide
def _words(value, limit=200):
    return None if value is None else str(value)[:limit]


def decide(out):
    """The job's own summary: verdict WORDS per stage. Reads only the stage records; prints no number from any
    score table, harness reading or ITEM2 entry (only the ITEM2 outcome, gate and reasons, which are words)."""
    out = pathlib.Path(out)
    target = out / "E1A_RESULT.json"
    if target.exists():
        raise Stop("OUTPUT_EXISTS", str(target))
    smoke_rec = read_json(out / "smoke.json") or {}
    pre = read_json(out / "PREFLIGHT.json") or {}
    route_rec = read_json(out / "route" / "ROUTE_RECEIPT.json") or {}
    item2 = read_json(out / "probe" / "ITEM2_READING.json") or {}
    reads = read_json(out / "probe" / "READS_RECORD.json") or read_json(out / "probe" / "READS_NOT_STARTED.json") or {}
    self_test = read_json(out / "matched_start" / "SELF_TEST.json") or {}
    matched = read_json(out / "matched_start" / "MATCHED_START_READING.json") or {}
    rosters = {p.stem: (read_json(p) or {}).get("verdict") for p in sorted((out / "roster").glob("roster_*.json"))}
    validation = (item2.get("validation") or {}).get("validation") or reads.get("validation")
    stages = {
        "smoke": _words(smoke_rec.get("verdict")),
        "preflight": _words(pre.get("verdict")),
        "route": _words(route_rec.get("verdict")),
        "validation": _words(validation),
        "reads": _words(reads.get("verdict")),
        "item2": _words(item2.get("outcome"), 2000),
        "matched_start_self_test": _words(self_test.get("verdict")),
        "matched_start": _words(matched.get("verdict")),
        "roster": ",".join("%s=%s" % kv for kv in sorted(rosters.items())) if len(rosters) == 3 else None,
    }
    missing = [name for name in STAGES if not stages[name]]
    result = {"schema": RESULT_SCHEMA, "stages": stages, "missing_stage_readings": missing,
              "mechanism_gate": _words(item2.get("mechanism_gate")),
              "gate_open_reasons": [_words(r, 400) for r in item2.get("gate_open_reasons") or []],
              "historical_gate_on_repaired_arm": _words(item2.get("historical_gate_on_repaired_arm")),
              "route_failed": route_rec.get("failed"), "matched_start_reasons": matched.get("reasons"),
              "overall": "E1A_STAGES_COMPLETE" if not missing else "E1A_INCOMPLETE",
              "not_in_this_job": ["any analogy accuracy number", "any TEST or sealed item", "the HSET-2 readout (E1b)"],
              "labels": LABELS}
    write_create_only(target, result)
    print(json.dumps({k: result[k] for k in ("overall", "stages", "mechanism_gate", "missing_stage_readings")},
                     sort_keys=True))
    return 0 if not missing else 1


# ================================================================ main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("anchors")
    p.add_argument("--root", required=True)
    p = sub.add_parser("smoke")
    p.add_argument("--out", required=True)
    p.add_argument("--expect-torch", required=True)
    for name in ("preflight", "route", "reads", "matched", "roster", "inputs"):
        p = sub.add_parser(name)
        p.add_argument("--tree", required=True)
        p.add_argument("--spec", required=True)
        p.add_argument("--out", required=True)
        if name in ("preflight", "reads"):
            p.add_argument("--job-start", type=float, required=True)
            p.add_argument("--budget-seconds", type=int, required=True)
        if name in ("reads", "matched", "roster"):
            p.add_argument("--python", default=sys.executable)
    p = sub.add_parser("decide")
    p.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        if args.command == "anchors":
            return check_anchors(args.root)
        if args.command == "smoke":
            return smoke(args.out, args.expect_torch)
        if args.command == "decide":
            return decide(args.out)
        if args.command == "preflight":
            return preflight(args.tree, args.spec, args.out, args.job_start, args.budget_seconds)
        if args.command == "route":
            return route(args.tree, args.spec, args.out)
        spec = load_spec(args.spec)
        if args.command == "reads":
            return run_reads(spec, args.tree, args.out, args.python, args.job_start, args.budget_seconds)
        if args.command == "matched":
            return run_matched(spec, args.tree, args.out, args.python)
        if args.command == "roster":
            return run_roster(spec, args.tree, args.out, args.python)
        roster = import_from(pathlib.Path(args.tree) / spec["roster_dir"], "check_roster")
        return item2_inputs(spec, args.tree, args.out, roster)
    except Stop as stop:
        print("TOOL_STOP:%s:%s" % (stop.code, stop.detail))
        return 2


if __name__ == "__main__":
    sys.exit(main())
