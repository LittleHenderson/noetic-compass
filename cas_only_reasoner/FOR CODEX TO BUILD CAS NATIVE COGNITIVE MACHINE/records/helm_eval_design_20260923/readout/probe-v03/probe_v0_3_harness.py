"""Analogy wiring probe v0.3 -- the TORCH HARNESS that writes raw score tables. AWS GPU only; never on the laptop.

Rules: PREREG_ANALOGY_WIRING_PROBE_v0_3.md (status PROPOSED). Label: CLAUDE_BUILT_CLAUDE_CHECKED;
EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT. NOT RUN YET: its first real run is the E1a job on a T4.

It runs forward passes only and writes, per model, one RAW SCORE TABLE: every analogy-slot logit (float64) for every
analogy record (twice, for the noise gate) and for every counterfactual the prereg requires. It computes no metric of
its own. It calls the frozen pure function `probe_v0_3_metric.evaluate` on the table it just wrote, for convenience
only; the verdict that counts is the one `item2_reader.py` re-derives from the table.

Counterfactual construction, slot plan, reader, determinism settings, device admission and limits are v0.2's
(`../../analogy_wiring_probe/analogy_wiring_probe_v0_2.py` with its amendment A1), unchanged: the slot plan comes
from the UNMODIFIED packet; the counterfactual reading comes from the learner's own `pointer_inputs.read_packet`;
every focus copy in a focus-changed reading is asserted consistent.

  read      python -B probe_v0_3_harness.py read --model LABEL:SEED[:CHECKPOINT] [--model ...] --out-dir DIR
                [--container-kwargs JSON] [--switch-attr NAME --switch-expect true|false] [--package-root DIR]
  validate  python -B probe_v0_3_harness.py validate --seed SEED --out-dir DIR
                [--container-kwargs JSON] [--switch-attr NAME --switch-expect true|false] [--package-root DIR]

`validate` wraps `GraphForward._world_scores` IN MEMORY (the source file is hashed before and after and must not
change) with the four v0.2 self-test style controls plus the unwrapped control, and writes five raw tables and a
summary. Cases V6 and V7 are derived from V1 and V2 in pure Python by `probe_v0_3_metric.evaluate_validation`.

SIDE FILES that must travel with this file (a launcher must bundle them): probe_v0_3_metric.py and
PREREG_ANALOGY_WIRING_PROBE_v0_3.md. Both are checked before torch is imported (exit 7 if missing).
Exit codes: 2 GPU_REQUIRED, 3 GPU_UNAVAILABLE, 4 WALL_LIMIT_REACHED, 5 GPU_TEMPERATURE_STOP, 6 TOO_MANY_MODELS,
7 SIDE_FILE_MISSING, 8 SWITCH_ATTRIBUTE_NOT_BOOL / SWITCH_STATE_MISMATCH / CHECKPOINT_PAYLOAD, 9 OUTPUT_EXISTS.
"""
import argparse
import copy
import hashlib
import io
import json
import os
import pathlib
import subprocess
import sys
import time
import types

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import probe_v0_3_metric as metric  # noqa: E402  (standard library only)

DEFAULT_PACKAGE = HERE.parents[3]
MAX_START_C, STOP_C, MIN_FREE_MIB, WALL_SECONDS, MAX_MODELS = 75, 80, 2048, 3600, 3
POINTER_LEARNER = "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py"
SOURCE_FILES = ["research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/" + f for f in
                ("pointer_learner.py", "pointer_inputs.py", "slots.py", "pointer_contract.py")] + \
               ["cncm/typed_matched_worker.py"]
WRAPPER_OF_CASE = {"V1_CONTROL_UNWRAPPED": None, "V2_POSITIVE_COMPARISON": "POSITIVE_COMPARISON",
                   "V3_ANTI_COMPARISON": "ANTI_COMPARISON", "V4_NEGATIVE_UNIFORM": "NEGATIVE_UNIFORM",
                   "V5_NEGATIVE_COUPLED": "NEGATIVE_COUPLED"}
assert tuple(WRAPPER_OF_CASE) == metric.VALIDATION_RAW_CASES


# ================================================================= pure part (unit-tested without torch)
def rewire(world, edges, node_index):
    """v0.2: a copy of `world` whose contains-graph is `edges` (canonical indices), node 0 on the declared whole."""
    idx = node_index(world)
    refs = sorted(idx, key=idx.get)
    whole = world["declared_whole"]
    order = [whole] + [r for r in refs if r != whole]
    new = copy.deepcopy(world)
    new["contains"] = [{"ref": "%s/probe_e%d" % (world["world_id"], k), "source": order[a], "target": order[b]}
                       for k, (a, b) in enumerate(edges)]
    return new


def world_shape(world, node_index):
    idx = node_index(world)
    return metric.canon(len(world["nodes"]), [(idx[e["source"]], idx[e["target"]]) for e in world["contains"]])


def with_world(packet, world_id, new_world):
    """v0.2: a deep copy of `packet` with one bank world replaced."""
    p = copy.deepcopy(packet)
    worlds = p["source"]["worlds"]
    worlds[[w["world_id"] for w in worlds].index(world_id)] = new_world
    return p


def with_domain(packet, world_id, domain):
    world = [w for w in packet["source"]["worlds"] if w["world_id"] == world_id][0]
    new = copy.deepcopy(world)
    new["declarations"]["domain"] = domain
    return with_world(packet, world_id, new)


def analogy_ids_of(packets):
    return sorted(rid for rid, pk in packets.items() if pk["record"]["query"]["kind"] == "analogy")


def world_meta(packet, node_index):
    return {w["world_id"]: {"domain": w["declarations"]["domain"], "nodes": len(w["nodes"]),
                            "shape": metric.shape_json(world_shape(w, node_index))}
            for w in packet["source"]["worlds"]}


def build_score_table(packets, analogy_ids, score_fn, node_index, *, model, provenance, witnesses, tick=None):
    """The raw v0.3 score table. `score_fn(record_id, packet, changed_world_or_None) -> {world_id: float}`."""
    tick = tick or (lambda: None)
    ids = sorted(analogy_ids)
    focus_of = {rid: packets[rid]["source"]["focus_world_id"] for rid in ids}
    rep = {}
    for rid in ids:
        rep.setdefault(focus_of[rid], rid)
    records = {}
    for rid in ids:
        tick()
        packet = packets[rid]
        first = score_fn(rid, packet, None)
        second = score_fn(rid, packet, None)
        worlds = {w["world_id"]: w for w in packet["source"]["worlds"]}
        records[rid] = {"focus": focus_of[rid],
                        "candidate_domains": {c: worlds[c]["declarations"]["domain"] for c in first},
                        "base": first, "base_repeat": second}
    foci = {}
    for f, rid in sorted(rep.items()):
        packet = packets[rid]
        worlds = {w["world_id"]: w for w in packet["source"]["worlds"]}
        meta = world_meta(packet, node_index)
        plan = metric.plan_focus(f, meta, set(records[rid]["base"]))
        graph = []
        for edges in plan["graph"]:
            tick()
            changed = with_world(packet, f, rewire(worlds[f], edges, node_index))
            graph.append({"edges": edges, "scores": score_fn(rid, changed, f)})
        bystander = None
        if plan["bystander"] is not None:
            b, runs = plan["bystander"], []
            for edges in plan["bystander_runs"]:
                tick()
                changed = with_world(packet, b, rewire(worlds[b], edges, node_index))
                runs.append({"edges": edges, "scores": score_fn(rid, changed, b)})
            bystander = {"world": b, "runs": runs}
        domains = []
        for other in plan["domains"]:
            tick()
            domains.append({"domain": other, "scores": score_fn(rid, with_domain(packet, f, other), f)})
        foci[f] = {"record": rid, "worlds": meta, "graph": graph, "bystander": bystander, "domain": domains}
    return {"schema": metric.SCHEMA_TABLE, "model": model, "provenance": provenance, "witnesses": list(witnesses),
            "records": records, "foci": foci}


def write_create_only(path, obj):
    path = pathlib.Path(path)
    if path.exists():
        print("OUTPUT_EXISTS", str(path))
        sys.exit(9)
    with open(path, "x", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(obj, indent=1, sort_keys=True))
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ================================================================= torch part (AWS GPU only)
def gpu_telemetry():
    out = subprocess.run(["nvidia-smi", "--query-gpu=uuid,name,temperature.gpu,memory.free,utilization.gpu",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=20)
    uuid, name, temp, free, util = [v.strip() for v in out.stdout.strip().splitlines()[0].split(",")]
    return {"uuid": uuid, "name": name, "temperature_c": int(temp), "memory_free_mib": int(free),
            "utilization_percent": int(util)}


def _setup(args):
    for name in ("probe_v0_3_metric.py", metric.PREREG_NAME):
        if not (HERE / name).is_file():
            print("SIDE_FILE_MISSING", name)
            sys.exit(7)
    started = time.monotonic()
    import torch
    if not torch.cuda.is_available():
        print("GPU_REQUIRED")
        sys.exit(2)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark = True, False
    admission = gpu_telemetry()
    if admission["temperature_c"] > MAX_START_C or admission["memory_free_mib"] < MIN_FREE_MIB:
        print("GPU_UNAVAILABLE", admission)
        sys.exit(3)
    package = pathlib.Path(args.package_root).resolve()
    sys.dont_write_bytecode = True
    for p in (package, package / "research" / "CAS_META_2_COMPOSITION"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from cas_meta2.typed_teaching import pointer_contract as contract, pointer_inputs, pointer_learner as PL, slots
    from cncm.typed_matched_worker import _framework
    t0 = time.monotonic()
    frozen = contract.load_material(package)[0]
    packets = dict(contract.public_packets(frozen))
    env = types.SimpleNamespace(torch=torch, device=torch.device("cuda", 0), PL=PL, slots=slots,
                                pointer_inputs=pointer_inputs, _framework=_framework, packets=packets,
                                analogy_ids=analogy_ids_of(packets), frozen=frozen, package=package,
                                admission=admission, started=started, load_seconds=time.monotonic() - t0,
                                last_temperature=None, ticks=0)
    env.hashes = metric.frozen_hashes()
    env.source_sha = {f: metric.lf_sha(package / f) for f in SOURCE_FILES}
    return env


def _tick(env):
    def tick():
        if time.monotonic() - env.started > WALL_SECONDS:
            print("WALL_LIMIT_REACHED")
            sys.exit(4)
        if env.ticks % 10 == 0:
            env.last_temperature = gpu_telemetry()["temperature_c"]
            if env.last_temperature >= STOP_C:
                print("GPU_TEMPERATURE_STOP", env.last_temperature)
                sys.exit(5)
        env.ticks += 1
    return tick


def _build_model(env, label, init_seed, checkpoint, kwargs, switch_attr, switch_expect):
    torch = env.torch
    framework = env._framework(torch, env.device, init_seed)
    model = env.PL._build_container(torch, framework, env.device, **kwargs)
    checkpoint_sha = None
    if checkpoint:
        raw = pathlib.Path(checkpoint).read_bytes()
        checkpoint_sha = hashlib.sha256(raw).hexdigest()
        payload = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
        if type(payload) is not dict or "model_state" not in payload:
            print("CHECKPOINT_PAYLOAD_HAS_NO_MODEL_STATE", checkpoint)
            sys.exit(8)
        model.load_state_dict(payload["model_state"], strict=True)
    model.eval()
    switch = "NOT_A_REPAIRED_CONTAINER"
    if switch_attr:
        value = getattr(model, switch_attr)
        if type(value) is not bool:
            print("SWITCH_ATTRIBUTE_NOT_BOOL")
            sys.exit(8)
        if switch_expect is not None and value != (switch_expect == "true"):
            print("SWITCH_STATE_MISMATCH", value)
            sys.exit(8)
        switch = value
    info = {"label": label, "init_seed": init_seed, "checkpoint": checkpoint, "checkpoint_sha256": checkpoint_sha,
            "container_kwargs": kwargs, "switch_attr": switch_attr, "switch": switch,
            "parameter_count": sum(int(p.numel()) for p in model.parameters())}
    return model, info


def _score_fn(env, model):
    """v0.2's `scores_for`, unchanged in substance: slot plan from the unmodified packet, float64 logits."""
    torch, PL = env.torch, env.PL
    base_plan = {rid: env.slots.compile_slots(env.packets[rid]) for rid in env.analogy_ids}
    base_read = {rid: env.pointer_inputs.read_packet(env.packets[rid]) for rid in env.analogy_ids}

    def score(rid, packet, changed_world):
        plan = base_plan[rid]
        slot = [s for s in plan["slots"] if s["field"] == "world_id"]
        if len(slot) != 1:
            raise RuntimeError("ANALOGY_SLOT_COUNT:" + rid)
        if changed_world is None:
            reading = copy.deepcopy(base_read[rid])
        else:
            reading = env.pointer_inputs.read_packet(packet)
            if changed_world == reading["focus_world_id"] and (
                    reading["focus_world"]["contains"] != reading["worlds"][changed_world]["contains"]):
                raise RuntimeError("FOCUS_COPIES_DISAGREE:" + rid)
        reading["_device"] = env.device
        with torch.no_grad():
            forward = PL.GraphForward(torch, model, reading, env.device)
            rows = forward.head_logits(plan, [0] * PL.CLAUSE_COUNT)
            values = rows[slot[0]["slot_id"]].detach().double().cpu().tolist()
        return {PL._world_alias_table_for(reading, sym): float(v)
                for sym, v in zip(slot[0]["symbols"], values) if sym != "NO_MATCH"}
    return score


def _provenance(env, extra=None):
    torch = env.torch
    out = dict(env.hashes)
    out.update({"source_sha256_lf": env.source_sha, "course_digest": env.frozen["course_digest"],
                "package_root": str(env.package), "material_load_seconds": env.load_seconds,
                "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
                "cudnn": torch.backends.cudnn.version(), "python": sys.version.split()[0],
                "determinism": {"CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
                                "deterministic_algorithms": torch.are_deterministic_algorithms_enabled()},
                "gpu": {"admission": env.admission, "end": gpu_telemetry(),
                        "last_checked_temperature_c": env.last_temperature},
                "wall_seconds": time.monotonic() - env.started,
                "work": "forward passes only under torch.no_grad(); no optimizer, no update, no checkpoint written"})
    out.update(extra or {})
    return out


def _table_for(env, model, info, extra=None):
    table = build_score_table(env.packets, env.analogy_ids, _score_fn(env, model), env.pointer_inputs._node_index,
                              model=info, provenance={}, witnesses=metric.RULES["witnesses"], tick=_tick(env))
    table["provenance"] = _provenance(env, extra)
    return table


def read_mode(args):
    if len(args.model) > MAX_MODELS:
        print("TOO_MANY_MODELS")
        sys.exit(6)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = _setup(args)
    kwargs = json.loads(args.container_kwargs)
    for spec in args.model:
        label, seed, *ck = spec.split(":", 2)
        model, info = _build_model(env, label, int(seed), ck[0] if ck else None, kwargs, args.switch_attr,
                                   args.switch_expect)
        table = _table_for(env, model, info)
        sha = write_create_only(out_dir / (label + ".score_table.json"), table)
        try:
            result = metric.evaluate(table)
        except metric.TableRefused as err:
            result = {"verdict": None, "table_refused": err.code}
        result["score_table_sha256"] = sha
        write_create_only(out_dir / (label + ".harness_reading.json"), result)
        print(json.dumps({"label": label, "verdict": result["verdict"], "switch": info["switch"],
                          "score_table_sha256": sha}))
        del model
        env.torch.cuda.empty_cache()


# ---- validation controls, wrapped around GraphForward._world_scores IN MEMORY (v0.2 self-test style)
def _degree_hist(torch, adjacency, steps=5):
    ind = torch.clamp(adjacency.sum(dim=0).to(torch.int64), max=steps - 1)
    outd = torch.clamp(adjacency.sum(dim=1).to(torch.int64), max=steps - 1)
    hist = torch.zeros(steps * steps, dtype=torch.float32, device=adjacency.device)
    for a, b in zip(ind.tolist(), outd.tolist()):
        hist[a * steps + b] += 1.0
    return hist


def _variant(torch, PL, original, kind):
    """POSITIVE: -2*L1(hist focus, hist c) - 2*[same domain]; ANTI: the same terms with the sign flipped;
    UNIFORM: 3*(focus edges + focus nodes) for every candidate; COUPLED: 0.5*<mean hist over ALL worlds, hist c>.
    Added in float64 to the float64 copy of the float32 logits (a float32 add would perturb every logit)."""
    def wrapped(self, field, symbols):
        rows = original(self, field, symbols)
        hists = {row[0]: _degree_hist(torch, row[3]) for row in self.blocks}
        focus = self.focus_world_id
        dom = {w: tuple(self.reading["worlds"][w]["declaration_ids"]["domain"]) for w in self.world_ids}
        extras = []
        for symbol in symbols:
            if symbol == "NO_MATCH":
                extras.append(0.0)
                continue
            c = PL._world_alias_table_for(self.reading, symbol)
            compare = float((hists[focus] - hists[c]).abs().sum()) + (1.0 if dom[c] == dom[focus] else 0.0)
            if kind == "POSITIVE_COMPARISON":
                extras.append(-2.0 * compare)
            elif kind == "ANTI_COMPARISON":
                extras.append(2.0 * compare)
            elif kind == "NEGATIVE_UNIFORM":
                block = [row for row in self.blocks if row[0] == focus][0]
                extras.append(float(3.0 * (block[3].sum() + block[1])))
            elif kind == "NEGATIVE_COUPLED":
                pool = torch.stack(list(hists.values())).mean(dim=0)
                extras.append(float(0.5 * torch.dot(pool, hists[c])))
            else:
                raise ValueError(kind)
        return rows.double() + torch.tensor(extras, dtype=torch.float64, device=rows.device)
    return wrapped


def validate_mode(args):
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = _setup(args)
    kwargs = json.loads(args.container_kwargs)
    model, info = _build_model(env, "validation_%d" % args.seed, args.seed, None, kwargs, args.switch_attr,
                               args.switch_expect)
    original = env.PL.GraphForward._world_scores
    before = metric.lf_sha(env.package / POINTER_LEARNER)
    tables, files = {}, {}
    for case, kind in WRAPPER_OF_CASE.items():
        if kind is not None:
            env.PL.GraphForward._world_scores = _variant(env.torch, env.PL, original, kind)
        try:
            table = _table_for(env, model, dict(info, label=case), {"validation_case": case, "wrapper": kind})
        finally:
            env.PL.GraphForward._world_scores = original
        name = case + ".score_table.json"
        files[case] = {"file": name, "sha256": write_create_only(out_dir / name, table)}
        tables[case] = table
        print(json.dumps({"case": case, "written": name}))
    after = metric.lf_sha(env.package / POINTER_LEARNER)
    verdict = metric.evaluate_validation(tables, before, after)
    summary = {"schema": "claude.analogy-wiring-probe-validation-summary/0.3", "tables": files,
               "pointer_learner_sha256_lf_before_after": [before, after], "model": info,
               "harness_validation_reading": verdict, "provenance": _provenance(env)}
    write_create_only(out_dir / "validation_summary.json", summary)
    print(json.dumps({"validation": verdict["validation"], "failed": verdict["failed"]}))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    for name in ("read", "validate"):
        p = sub.add_parser(name)
        p.add_argument("--out-dir", required=True)
        p.add_argument("--container-kwargs", default="{}")
        p.add_argument("--switch-attr", default=None)
        p.add_argument("--switch-expect", default=None, choices=[None, "true", "false"])
        p.add_argument("--package-root", default=str(DEFAULT_PACKAGE))
        if name == "read":
            p.add_argument("--model", action="append", required=True)
        else:
            p.add_argument("--seed", type=int, default=20260917)
    args = ap.parse_args(argv)
    (read_mode if args.mode == "read" else validate_mode)(args)


if __name__ == "__main__":
    main()
