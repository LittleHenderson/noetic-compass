"""E1b machine driver: the sealed HSET-2 TEST readout on ONE AWS T4 (readout plan item 10). BUILT, NOT RUN ON AWS.

Label: CLAUDE_BUILT_CLAUDE_CHECKED; EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT.

STAGES (each stops the job by name; nothing later runs):
  0  custody manifest check (design s8; custody_manifest.py): every touched world against the whole forbidden set, two
     isomorphism methods, fail closed. Exit 3 CUSTODY_STOP.
  1  rebuild every needed TEST packet from the custodian's sealed file with the builder's own `build_packet`, and
     require each packet's sha256 and record id to equal what the sealed build recorded. Exit 6 on any mismatch.
  2  timing preflight: a FRESH switch-ON container answers a few PUBLIC DEV packets (no TEST packet, no trained weight);
     the whole run is projected; exit 5 PREFLIGHT_OVER_WALL_LIMIT if it would not fit.
  3  predictions: both presentations of every claim-cell item, for every run the reading rules admit
     (e1b_scorer.reading_plan), through the accepted route (eval_paths at e05889ee: `predict_packet`), graded by
     checker v2 (`larger_question_scope.grade`). Several processes share the one T4 (the per-packet time is mostly
     CPU validation). An exception on any item makes that run's reading INVALID (Codex R3-B: a fault is not a model
     difference); its type is counted in public, its message is sealed.
  4  scoring (e1b_scorer.score): every label, printed and written.

TWO ENGINES. `RouteEngine` (real): torch is imported only inside it, so the laptop never imports torch; it refuses a
non-CUDA machine (exit 2 GPU_REQUIRED). `StandInEngine` (--stand-in-seed): ONLY for a throwaway fixture (the sealed
file's mode must be THROWAWAY_SALTS_NOT_A_BUILD); it answers from a public seed string and grades by comparing with the
item's admissible values. It exists so the whole program can be run end to end on the laptop without a model.

CUSTODY. Both output folders must be outside every git work tree. The public folder gets aggregates and labels only
(see e1b_scorer). In real mode an uncaught exception's traceback goes to the sealed folder only; the log gets its type.

    python -B e1b_machine.py --hset2-dir D --sealed-file F --build-summary F --public-cells F --runs F \
        --item2-reading F --matched-start F --reproduction-reading F [--inference-ruling F] [--h1h2 SEED=F ...] \
        --touched KIND=PATH|KIND=NONE:reason ... --out-public D --out-sealed D \
        (--package-root D | --stand-in-seed STRING) [--processes N] [--wall-seconds S]
Exit: 0 readout written (whatever the labels say); 1 failed; 2 GPU_REQUIRED; 3 CUSTODY_STOP; 4 SETUP_REFUSED;
5 PREFLIGHT_OVER_WALL_LIMIT; 6 PACKET_REBUILD_MISMATCH.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import concurrent.futures.process
import hashlib
import io
import json
import multiprocessing
import os
import pathlib
import platform
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import custody_manifest as CM  # noqa: E402
import e1b_scorer as S  # noqa: E402

EXIT_DONE, EXIT_FAILED, EXIT_GPU, EXIT_CUSTODY, EXIT_SETUP, EXIT_PREFLIGHT, EXIT_REBUILD = 0, 1, 2, 3, 4, 5, 6
WALL_SECONDS = 95 * 60                 # the readout's own budget inside the 120-minute machine timer
PREFLIGHT_PACKETS = 8
PREFLIGHT_MARGIN = 1.25
PARALLEL_EFFICIENCY = 0.75             # assumed speed-up per extra process (the GPU is shared); a projection only
TASK_ITEMS = 12
THROWAWAY = "THROWAWAY_SALTS_NOT_A_BUILD"


class Stop(Exception):
    def __init__(self, code, word):
        super().__init__(word)
        self.code, self.word = code, word


def inside_git(path):
    p = pathlib.Path(path).resolve()
    return any((q / ".git").exists() for q in [p] + list(p.parents))


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=repr)


def keyed_unit(*parts):
    """A number in [0, 1) from public strings (the stand-in's only source of chance)."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:13], 16) / float(16 ** 13)


# ================================================================================================ engines
class StandInEngine:
    """Throwaway only. strength: {run_id: {cell: {"p": probability a cluster is right, "key": draw key}}}. Two runs
    with the same key give the same answers (so a fixture can make both arms identical on a cell)."""

    def __init__(self, seed, strength):
        self.seed, self.strength = seed, strength

    def predict(self, run_id, packet):
        spec = self.strength.get(run_id, {}).get(packet["cell"], {"p": 0.5, "key": run_id})
        if spec.get("fault"):                              # tests only: an engine fault on this cell
            raise RuntimeError("STAND_IN_FAULT %s" % packet["item_id"])
        right = keyed_unit(self.seed, spec["key"], packet["cluster_id"]) < spec["p"]
        return packet["admissible_values"][0] if right else {"stand_in_wrong_answer": packet["kind"]}

    def grade(self, packet, answer):
        return canon(answer) in {canon(a) for a in packet["admissible_values"]}


class RouteEngine:
    """The accepted larger-question route (eval_paths at e05889ee) on a CUDA device. AWS only."""

    def __init__(self, config):
        import torch                                        # the ONLY torch import in this job's code
        if not torch.cuda.is_available():
            raise Stop(EXIT_GPU, "GPU_REQUIRED")
        self.torch, self.device = torch, "cuda"
        root = pathlib.Path(config["package_root"]).resolve()
        for p in (root, root / "research" / "CAS_META_2_COMPOSITION"):
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
        from eval_paths import larger_question_scope as scope
        scope.verify_source_pins()                         # SOURCE_DRIFT refusal before the learner half is imported
        from cas_meta2.typed_teaching import pointer_learner as PL
        from cncm.typed_matched_worker import _framework
        from eval_paths import larger_question_learner as LL
        self.scope, self.LL, self.tagger = scope, LL, PL.role_tagger(str(root))
        self.models = {}
        for run in config["load_runs"]:
            model = PL._build_container(torch, _framework(torch, self.device, run["seed"]), self.device,
                                        analogy_focus_comparison=run["switch"])
            if run.get("checkpoint"):
                raw = pathlib.Path(run["checkpoint"]).read_bytes()
                if hashlib.sha256(raw).hexdigest() != run["checkpoint_sha256"]:
                    raise Stop(EXIT_SETUP, "CHECKPOINT_PIN:%s" % run["run_id"])
                state = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)["model_state"]
                model.load_state_dict(state, strict=True)
            model.eval()
            if model.analogy_focus_comparison is not run["switch"]:
                raise Stop(EXIT_SETUP, "SWITCH_STATE:%s" % run["run_id"])
            self.models[run["run_id"]] = model

    def predict(self, run_id, packet):
        result = self.LL.predict_packet(self.torch, self.models[run_id], packet, self.device, tagger=self.tagger)
        if result["route"] != self.scope.LARGER:
            raise ValueError("E1B_ROUTE_NOT_LARGER")
        return result["answer"]

    def grade(self, packet, answer):
        return bool(self.scope.grade(packet, answer)["correct"])


_W = {}


def _worker_init(config):
    sys.dont_write_bytecode = True
    for p in config["sys_path"]:
        if p not in sys.path:
            sys.path.insert(0, p)
    _W["engine"] = (StandInEngine(config["stand_in_seed"], config["strength"]) if config["stand_in_seed"] is not None
                    else RouteEngine(config))


def _worker_task(task):
    """task: [(item_id, packet, [run ids])]. One row per (run, item); an exception is recorded, never raised."""
    engine, rows = _W["engine"], []
    for item_id, packet, run_ids in task:
        for run_id in run_ids:
            try:
                answer = engine.predict(run_id, packet)
                rows.append({"run_id": run_id, "item_id": item_id, "correct": bool(engine.grade(packet, answer)),
                             "answer": json.loads(canon(answer))})
            except Exception as error:  # noqa: BLE001 -- recorded per item; the run's reading becomes INVALID
                rows.append({"run_id": run_id, "item_id": item_id, "correct": None,
                             "error_type": type(error).__name__, "error": str(error)[:300]})
    return rows


# ================================================================================================ stages
def stage1_packets(B, sealed, needed, package_root, stand_in):
    """{item_id: packet}. Real: the builder's build_packet, checked against the sealed build's own record."""
    items = {it["item_id"]: it for it in sealed["items"]}
    if stand_in:
        return {i: {"stand_in": True, "item_id": i, "cluster_id": items[i]["cluster_id"], "cell": items[i]["cell"]
                    if "/" in items[i]["cell"] else "%s/%s" % (items[i]["split"], items[i]["cell"]),
                    "kind": items[i]["kind"], "admissible_values": items[i]["evaluation"]["admissible_values"]}
                for i in needed}, {"state": "STAND_IN_NOT_REBUILT", "items": len(needed)}
    B._init(str(package_root))
    import hset_worlds as hw
    packets, mismatched = {}, 0
    for i in needed:
        packet = B.build_packet(items[i])
        ev = items[i]["evaluation"]
        if hw.sha(packet) != ev["packet_sha256"] or packet["record"]["record_id"] != ev["record_id"]:
            mismatched += 1
        packets[i] = packet
    if mismatched:
        raise Stop(EXIT_REBUILD, "PACKET_REBUILD_MISMATCH:%d_of_%d" % (mismatched, len(needed)))
    return packets, {"state": "REBUILT_AND_EQUAL_TO_THE_SEALED_BUILD", "items": len(needed)}


def stage2_preflight(B, public_cells, package_root, work, processes, wall, started, stand_in):
    """Seconds per (packet, run) from a fresh switch-ON container on PUBLIC DEV packets; refuse if over the wall."""
    if stand_in:
        return {"state": "STAND_IN_NOT_TIMED", "predictions_planned": work}
    dev = [it for it in public_cells["items"] if it.get("split") == "DEV_NEW_6"
           and it.get("cell") in ("ANALOGY", "CORRESPONDENCE", "REACH_FIRST_DIRECT", "REACH_BFS")]
    by_cell = collections.defaultdict(list)
    for it in dev:
        by_cell[it["cell"]].append(it)
    chosen = [it for i in range(PREFLIGHT_PACKETS) for c in sorted(by_cell) for it in by_cell[c][i:i + 1]][:PREFLIGHT_PACKETS]
    if len(chosen) < 4:
        raise Stop(EXIT_SETUP, "PREFLIGHT_TOO_FEW_PUBLIC_DEV_PACKETS")
    engine = RouteEngine({"package_root": package_root,
                          "load_runs": [{"run_id": "FRESH_ON", "seed": S.SEEDS[0], "switch": True, "checkpoint": None}]})
    packets = [B.build_packet(it) for it in chosen]
    engine.grade(packets[0], engine.predict("FRESH_ON", packets[0]))           # warm-up, not timed
    t0 = time.monotonic()
    for packet in packets:
        engine.grade(packet, engine.predict("FRESH_ON", packet))
    per = (time.monotonic() - t0) / len(packets)
    speed = max(1.0, processes * PARALLEL_EFFICIENCY)
    elapsed = time.monotonic() - started
    projected = elapsed + PREFLIGHT_MARGIN * work * per / speed
    row = {"state": "TIMED", "packets_timed": len(packets), "seconds_per_prediction": round(per, 4),
           "predictions_planned": work, "processes": processes, "assumed_speedup": speed, "margin": PREFLIGHT_MARGIN,
           "elapsed_seconds": round(elapsed, 1), "projected_total_seconds": round(projected, 1), "wall_seconds": wall,
           "source": "a fresh switch-ON container on public DEV_NEW_6 packets; no TEST packet, no trained weight"}
    del engine
    if projected > wall:
        row["state"] = "PREFLIGHT_OVER_WALL_LIMIT"
    return row


def stage3_predict(packets, todo, config, processes, deadline):
    """[(row)] for every (run, item) in todo; stops collecting at the deadline (missing rows make a run INVALID)."""
    runs_of_item = collections.defaultdict(list)
    for run_id, items in todo.items():
        for i in items:
            runs_of_item[i].append(run_id)
    order = sorted(runs_of_item)
    tasks = [[(i, packets[i], runs_of_item[i]) for i in order[k:k + TASK_ITEMS]] for k in range(0, len(order), TASK_ITEMS)]
    rows, note = [], "COMPLETE"
    if processes <= 1:
        _worker_init(config)
        for task in tasks:
            if time.monotonic() > deadline:
                note = "WALL_LIMIT_REACHED"
                break
            rows += _worker_task(task)
        return rows, note
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=processes, mp_context=multiprocessing.get_context("spawn"),
                                                      initializer=_worker_init, initargs=(config,))
    try:
        for part in executor.map(_worker_task, tasks, timeout=max(1.0, deadline - time.monotonic())):
            rows += part
    except (concurrent.futures.process.BrokenProcessPool, TimeoutError) as error:
        note = "WALL_LIMIT_REACHED" if isinstance(error, TimeoutError) else "WORKER_POOL_BROKEN"
        executor.shutdown(wait=False, cancel_futures=True)
        return rows, note
    executor.shutdown(wait=True)
    return rows, note


# ================================================================================================ main
def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for name in ("--hset2-dir", "--sealed-file", "--build-summary", "--public-cells", "--runs", "--out-public",
                 "--out-sealed"):
        p.add_argument(name, required=True)
    for name in ("--item2-reading", "--matched-start", "--reproduction-reading", "--inference-ruling"):
        p.add_argument(name, default=None)
    p.add_argument("--h1h2", action="append", default=[], help="SEED=PATH, one per seed pair")
    p.add_argument("--touched", action="append", default=[], help="KIND=PATH or KIND=NONE:reason (design s8)")
    engine = p.add_mutually_exclusive_group(required=True)
    engine.add_argument("--package-root", help="real mode: the CNCM root holding the e05889ee route")
    engine.add_argument("--stand-in-seed", help="THROWAWAY fixture only: answer from this public string, no model")
    p.add_argument("--stand-in-strength", default=None, help="throwaway only: {run_id: {cell: p}}")
    p.add_argument("--processes", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 2)))
    p.add_argument("--wall-seconds", type=int, default=WALL_SECONDS)
    return p.parse_args(argv)


def read_optional(path):
    return None if path is None else pathlib.Path(path).read_bytes()


def run(args):
    started = time.monotonic()
    stand_in = args.stand_in_seed is not None
    for folder in (args.out_public, args.out_sealed):
        if inside_git(folder):
            raise Stop(EXIT_SETUP, "OUTPUT_FOLDER_INSIDE_A_GIT_WORK_TREE")
    out_pub, out_sealed = pathlib.Path(args.out_public), pathlib.Path(args.out_sealed)
    out_pub.mkdir(parents=True, exist_ok=True)
    out_sealed.mkdir(parents=True, exist_ok=True)
    try:
        B, A = S.load_builder(args.hset2_dir)
        sealed_bytes, summary_bytes = pathlib.Path(args.sealed_file).read_bytes(), pathlib.Path(args.build_summary).read_bytes()
        sealed, summary, mode = S.load_sealed_and_summary(B, sealed_bytes, summary_bytes)
        if stand_in != (mode == THROWAWAY):
            raise S.Refused("STAND_IN_ONLY_WITH_A_THROWAWAY_FIXTURE_AND_REAL_ONLY_WITH_THE_SEALED_BUILD")
        builder = S.check_builder_identity(B, sealed["identity"])
    except S.Refused as refusal:
        raise Stop(EXIT_SETUP, refusal.code)
    prefix = "THROWAWAY_" if stand_in else ""
    names = {"public": prefix + "E1B_READOUT_PUBLIC.json", "sealed": prefix + "E1B_READOUT_SEALED.json",
             "predictions": prefix + "E1B_PREDICTIONS_SEALED.jsonl"}
    identity = {"scorer_sha256_lf": S.lf_sha256(S.__file__), "machine_sha256_lf": S.lf_sha256(__file__),
                "custody_sha256_lf": S.lf_sha256(CM.__file__), "builder": builder,
                "build_summary_sha256": S.sha256_bytes(summary_bytes), "python": platform.python_version(),
                "engine": "STAND_IN_THROWAWAY_ONLY" if stand_in else "ROUTE_e05889ee_predict_packet_checker_v2"}
    public = {"schema": S.SCHEMA_PUBLIC, "label": S.LABEL, "custody_label": S.CUSTODY_LABEL,
              "readout_mode": S.MODES[mode], "identity": identity,
              "throwaway_warning": ("THROWAWAY: public-salt fixture and stand-in answers; never a result about Helm"
                                    if stand_in else None)}

    def write(extra_public, extra_sealed):
        doc = dict(public, **extra_public)
        data = json.dumps(doc, indent=1, sort_keys=True).encode("utf-8")
        (out_pub / names["public"]).write_bytes(data)
        sealed_doc = dict({"schema": S.SCHEMA_SEALED, "custody": "CLAUDE_ONLY_NEVER_COMMIT", "label": S.LABEL,
                           "public_document_sha256": S.sha256_bytes(data)}, **extra_sealed)
        (out_sealed / names["sealed"]).write_bytes(json.dumps(sealed_doc, indent=1, sort_keys=True, default=repr).encode())
        return doc

    # ---- stage 0: custody manifest (design s8)
    import hset2_stage0_public as S0
    import oracle_isomorphism as oracle
    try:
        touched = CM.parse_touched(args.touched)
    except (ValueError, OSError) as error:
        raise Stop(EXIT_SETUP, "TOUCHED_SPEC_%s" % type(error).__name__)
    stage0, stage0_sealed = CM.check(touched, S.forbidden_keys(sealed), oracle, S0.class_key)
    print("STAGE 0 %s (%d touched shapes; matches M1 %d, M2 %d)" % (stage0["status"], stage0["distinct_touched_shapes"],
                                                                     stage0["matches_m1"], stage0["matches_m2"]), flush=True)
    stage0_label = {"label": "STAGE0_CUSTODY_MANIFEST", "status": stage0["status"], "reasons": stage0["reasons"]}
    if stage0["status"] != CM.PASS_WORD:
        write({"stage0_custody": stage0, "labels": [stage0_label], "status": "CUSTODY_STOP_NO_TEST_READ"},
              {"stage0_detail": stage0_sealed})
        raise Stop(EXIT_CUSTODY, "CUSTODY_STOP")

    # ---- runs, prerequisites and the reading plan
    try:
        runs_bytes = pathlib.Path(args.runs).read_bytes()
        runs = S.read_runs(runs_bytes)
        three, _ = B.reach_claim_names()
        members, items_of = S.cell_members(sealed, summary, three)
    except S.Refused as refusal:
        raise Stop(EXIT_SETUP, refusal.code)
    identity["runs_record_sha256"] = S.sha256_bytes(runs_bytes)
    runs_dir = pathlib.Path(args.runs).resolve().parent
    for run in runs:
        run["checkpoint_path"] = str(runs_dir / run["checkpoint"]) if run.get("checkpoint") else None
        if not stand_in and (run["checkpoint_path"] is None or S.sha256_bytes(
                pathlib.Path(run["checkpoint_path"]).read_bytes()) != run["checkpoint_sha256"]):
            raise Stop(EXIT_SETUP, "CHECKPOINT_PIN:%s" % run["run_id"])
    prereq = {"item2": S.read_item2(read_optional(args.item2_reading), runs),
              "matched_start": S.read_verdict(read_optional(args.matched_start), S.SCHEMA_MATCHED_START, S.MATCHED,
                                              "MATCHED_START"),
              "reproduction": S.read_verdict(read_optional(args.reproduction_reading), S.SCHEMA_REPRODUCTION,
                                             S.REPRODUCED_U17, "U17_REPRODUCTION"),
              "inference": S.read_inference_ruling(read_optional(args.inference_ruling))}
    h1h2_paths = {}
    for spec in args.h1h2:
        seed, _, path = spec.partition("=")
        h1h2_paths[int(seed)] = path
    h1h2 = {seed: S.read_h1h2(read_optional(h1h2_paths.get(seed)), seed) for seed in S.SEEDS}
    plan = S.reading_plan(runs, prereq)
    todo = S.items_to_predict(plan, members, items_of)
    needed = sorted({i for items in todo.values() for i in items})
    work = sum(len(v) for v in todo.values())
    print("reading plan: %s" % ", ".join("%s=%s" % (k, v["status"]) for k, v in plan.items()), flush=True)

    # ---- stage 1: packets
    packets, stage1 = stage1_packets(B, sealed, needed, args.package_root, stand_in)
    print("STAGE 1 %s (%d packets)" % (stage1["state"], stage1["items"]), flush=True)
    # ---- stage 2: preflight
    public_cells = json.loads(pathlib.Path(args.public_cells).read_bytes())
    stage2 = stage2_preflight(B, public_cells, args.package_root, work, args.processes, args.wall_seconds, started,
                              stand_in)
    print("STAGE 2 %s" % json.dumps(stage2, sort_keys=True), flush=True)
    if stage2["state"] == "PREFLIGHT_OVER_WALL_LIMIT":
        write({"stage0_custody": stage0, "stage1_packets": stage1, "stage2_preflight": stage2,
               "labels": [stage0_label], "status": "PREFLIGHT_OVER_WALL_LIMIT_NO_TEST_READ"}, {})
        raise Stop(EXIT_PREFLIGHT, "PREFLIGHT_OVER_WALL_LIMIT")

    # ---- stage 3: predictions
    strength = json.loads(pathlib.Path(args.stand_in_strength).read_bytes()) if (stand_in and args.stand_in_strength) else {}
    config = {"sys_path": [str(HERE)] + [p for p in sys.path if "hset" in p or "d1_acceptance" in p],
              "stand_in_seed": args.stand_in_seed, "strength": strength, "package_root": args.package_root,
              "load_runs": [{"run_id": r["run_id"], "seed": r["seed"], "switch": r["switch"],
                             "checkpoint": r["checkpoint_path"], "checkpoint_sha256": r["checkpoint_sha256"]}
                            for r in runs if plan[r["run_id"]]["read"]]}
    t3 = time.monotonic()
    rows, note = stage3_predict(packets, todo, config, args.processes, started + args.wall_seconds)
    item_right, invalid, errors = collections.defaultdict(dict), collections.defaultdict(list), collections.Counter()
    for row in rows:
        if row["correct"] is None:
            invalid[row["run_id"]].append("ITEM_ERROR:%s" % row["error_type"])
            errors[row["error_type"]] += 1
        else:
            item_right[row["run_id"]][row["item_id"]] = row["correct"]
    if note != "COMPLETE":
        for run_id in todo:
            invalid[run_id].append("STAGE3_%s" % note)
    stage3 = {"state": note, "predictions_planned": work, "predictions_returned": len(rows),
              "errors_by_type": dict(errors), "processes": args.processes, "seconds": round(time.monotonic() - t3, 1)}
    print("STAGE 3 %s" % json.dumps(stage3, sort_keys=True), flush=True)

    # ---- stage 4: scoring
    try:
        part, sealed_part = S.score(B, A, sealed, summary, runs, plan, dict(item_right), dict(invalid), prereq, h1h2)
    except S.Refused as refusal:
        raise Stop(EXIT_SETUP, refusal.code)
    labels = [stage0_label] + part.pop("labels")
    with open(out_sealed / names["predictions"], "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    doc = write({"stage0_custody": stage0, "stage1_packets": stage1, "stage2_preflight": stage2, "stage3_predictions": stage3,
                 "prerequisites": prereq, "h1h2_readings": {str(k): {x: v.get(x) for x in ("state", "view", "reasons",
                                                                                            "record_sha256")}
                                                             for k, v in h1h2.items()},
                 **part, "labels": labels, "status_vocabulary": S.STATUS_VOCABULARY,
                 "forbidden_wording": list(S.FORBIDDEN_WORDING), "status": "READOUT_WRITTEN"},
                {"stage0_detail": stage0_sealed, **sealed_part, "item_errors": [r for r in rows if r["correct"] is None]})
    print("\n".join(S.label_table(doc["labels"])), flush=True)
    print("READOUT_WRITTEN %d labels; public %s; sealed folder only for per-item results" % (len(labels), names["public"]),
          flush=True)
    return EXIT_DONE


def expand_args_file(argv):
    """`--args-file PATH` is replaced by the JSON list of arguments in PATH (the launcher writes the variable readout
    arguments into the bundle, where the anchors check covers them, so they never count against the user-data limit)."""
    argv = list(argv)
    while "--args-file" in argv:
        i = argv.index("--args-file")
        extra = json.loads(pathlib.Path(argv[i + 1]).read_text(encoding="utf-8"))
        if not isinstance(extra, list) or not all(isinstance(a, str) for a in extra):
            raise SystemExit("E1B_STOP ARGS_FILE_NOT_A_LIST_OF_STRINGS")
        argv[i:i + 2] = extra
    return argv


def main(argv=None):
    args = parse_args(expand_args_file(sys.argv[1:] if argv is None else argv))
    try:
        return run(args)
    except Stop as stop:
        print("E1B_STOP %s (exit %d)" % (stop.word, stop.code), flush=True)
        return stop.code
    except BaseException as error:  # noqa: BLE001 -- custody: nothing but the type may reach the public log
        written = False
        try:
            sealed = pathlib.Path(args.out_sealed)
            if not inside_git(sealed):
                sealed.mkdir(parents=True, exist_ok=True)
                (sealed / "e1b_traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
                written = True
        except BaseException:  # noqa: BLE001
            pass
        print("E1B_FAILED_UNCAUGHT %s (traceback %s)" % (type(error).__name__,
                                                          "in the sealed folder only" if written else "NOT written"))
        return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
