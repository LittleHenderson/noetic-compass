"""Matched-start check, prereg A5.5 (PREREG_ANALOGY_WIRING_PROBE_v0_2.md, amendment commit d7023288).

Question: did each repaired (switch-ON) run start from Helm 2.0's exact starting weights?

For each study seed 20260917, 20260918, 20260919 it checks four things:
  1. the 48 tensors the ON initial.pt shares with Helm 2.0 equal Helm 2.0's initial.pt bit for bit
     (same dtype, same shape, torch.equal, and the same raw bytes);
  2. the 5 analogy_head tensors are identical across the three seeds, and equal a fresh build with head seed
     20260923 (the head block of pointer_learner.py `_build_container`, lines 861-868 at 3df31d96, rebuilt alone);
  3. the ON parameter count is 203,424;
  4. every one of the 1,470 main update rows (pass_01..pass_10_updates.jsonl) reports gradient_parameter_count 53.

Verdict words and exit codes:
  MATCHED_START_REPRODUCED      exit 0  every check passed;
  MATCHED_START_NOT_REPRODUCED  exit 3  at least one check failed; every failed check is listed in `reasons`;
  TOOL_STOP                     exit 1  an input could not be read, a Helm 2.0 reference file does not carry its
                                        pinned sha256, or the program was started on the Windows laptop.
A TOOL_STOP is not a reading. It says the inputs were wrong, not that the start failed to match.

Self-test mode (--self-test, Helm 2.0 files only, no ON file): plan item 6's real-file check. Helm 2.0's initial.pt
plus the fresh head, compared with itself, must read REPRODUCED, and a copy with one flipped bit must read
NOT_REPRODUCED. Prints MATCHED_START_SELF_TEST:PASS (exit 0) or MATCHED_START_SELF_TEST:FAIL (exit 4). Run it in
E1a before the real reading; it proves the torch comparison, the fresh head and the count on real files.

Reading order (prereg A5.1/A5.3/A5.5): this program reads no score, no loss and no analogy answer. From the update
rows it keeps `gradient_parameter_count` only; from the checkpoints it keeps `model_state` only.

Where it runs: AWS only (inside E1a). torch is imported lazily, only by `main`, and `main` refuses on Windows before
that import (owner rule: no torch on the laptop). The pure parts (`judge`, `self_test`, `read_gradient_counts`,
`check_pin`) are tested on the laptop with stand-in tensors: test_matched_start.py.

Usage (one --on and one --helm2 per seed; DIR holds the ON receipt's initial.pt and pass_NN_updates.jsonl, for
example receipt_analogy_on_<seed>/checkpoints or receipt_analogy_on_<seed>/collected/results/artifacts):
  python matched_start.py --on 20260917=DIR --on 20260918=DIR --on 20260919=DIR \
      --helm2 20260917=PATH --helm2 20260918=PATH --helm2 20260919=PATH [--out READING.json]
  python matched_start.py --self-test --helm2 20260917=PATH --helm2 20260918=PATH --helm2 20260919=PATH
The Helm 2.0 files are records/typed_pointer_001/receipt_<seed>/checkpoints/initial.pt; all three blobs are present
at commit 27fd5698 and later (seed 20260919's blob d90858ff is NOT in c8d5c430's tree).

Label: CLAUDE_BUILT_CLAUDE_CHECKED. EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = "helm.matched-start-reading/0.1"
REPRODUCED = "MATCHED_START_REPRODUCED"
NOT_REPRODUCED = "MATCHED_START_NOT_REPRODUCED"
TOOL_STOP = "TOOL_STOP"
SEEDS = (20260917, 20260918, 20260919)
HEAD_SEED = 20260923
SHARED_TENSORS = 48
HEAD_NAMES = ("analogy_head.0.weight", "analogy_head.2.weight", "analogy_head.2.bias",
              "analogy_head.3.weight", "analogy_head.3.bias")
PARAMETER_COUNT = 203424
GRADIENT_TENSORS = 53
MAIN_ROWS = 1470
PASSES = 10
# Pinned in records/typed_pointer_001/admission_analogy_on_001/MIGRATION_ON_SHAPES.json (matched_starts.per_seed),
# taken there from each Helm 2.0 receipt's collected_inventory.json and artifact_manifest.json.
HELM2_INITIAL_SHA256 = {
    20260917: "59dd46877bd7bf97dbb4059975051cc6102b374d5c387d3a183884048b71b004",
    20260918: "d3c6292f2c0d09e29952bfe353d47fff058741d42c0a8e8dbe7a80eaad8fd645",
    20260919: "93b84558c0123673eabcc462f68afe8ecb1537b598e297ee16f7a7458787ee9f",
}


class ToolStop(Exception):
    """An input could not be read or is not the pinned object. Not a reading."""


def judge(states, fresh_head, gradient_counts, same_bits, numel):
    """The A5.5 decision. Pure: no torch, no files.

    states: {seed: (on_state, helm2_state)}, each state a {name: tensor} dict.
    fresh_head: {name: tensor} built with HEAD_SEED.
    gradient_counts: {seed: [gradient_parameter_count of each main update row, in file order]}.
    same_bits(a, b) -> bool, numel(t) -> int: supplied by the caller (torch on AWS, stand-ins in the tests).
    """
    reasons, facts = [], {}
    if sorted(states) != list(SEEDS) or sorted(gradient_counts) != list(SEEDS):
        reasons.append("SEEDS_ARE_NOT_THE_THREE_STUDY_SEEDS:" + ",".join(str(s) for s in sorted(states)))
    if sorted(fresh_head) != sorted(HEAD_NAMES):
        reasons.append("FRESH_HEAD_NAMES_ARE_NOT_THE_5_ANALOGY_HEAD_NAMES")
    first = None
    for seed in sorted(states):
        on, helm2 = states[seed]
        tag = "%d:" % seed
        if len(helm2) != SHARED_TENSORS:
            reasons.append(tag + "HELM2_INITIAL_HAS_%d_TENSORS_NOT_%d" % (len(helm2), SHARED_TENSORS))
        missing = sorted(set(helm2) - set(on))
        if missing:
            reasons.append(tag + "SHARED_TENSORS_MISSING_FROM_ON:" + ",".join(missing))
        extra = sorted(set(on) - set(helm2))
        if extra != sorted(HEAD_NAMES):
            reasons.append(tag + "ON_EXTRA_TENSORS_ARE_NOT_THE_5_ANALOGY_HEAD_TENSORS:" + ",".join(extra))
        differ = [name for name in sorted(set(on) & set(helm2)) if not same_bits(on[name], helm2[name])]
        if differ:
            reasons.append(tag + "SHARED_TENSORS_NOT_BIT_EQUAL_TO_HELM2:" + ",".join(differ))
        count = sum(numel(tensor) for tensor in on.values())
        if count != PARAMETER_COUNT:
            reasons.append(tag + "PARAMETER_COUNT_%d_NOT_%d" % (count, PARAMETER_COUNT))
        head_bad = [name for name in HEAD_NAMES
                    if name not in on or name not in fresh_head or not same_bits(on[name], fresh_head[name])]
        if head_bad:
            reasons.append(tag + "ANALOGY_HEAD_NOT_EQUAL_TO_FRESH_BUILD_SEED_%d:" % HEAD_SEED + ",".join(head_bad))
        if first is None:
            first = (seed, on)
        else:
            across = [name for name in HEAD_NAMES
                      if name not in on or name not in first[1] or not same_bits(on[name], first[1][name])]
            if across:
                reasons.append(tag + "ANALOGY_HEAD_DIFFERS_FROM_SEED_%d:" % first[0] + ",".join(across))
        rows = list(gradient_counts.get(seed, ()))
        if len(rows) != MAIN_ROWS:
            reasons.append(tag + "MAIN_UPDATE_ROWS_%d_NOT_%d" % (len(rows), MAIN_ROWS))
        bad = [index for index, value in enumerate(rows, 1)
               if type(value) is not int or value != GRADIENT_TENSORS]
        if bad:
            reasons.append(tag + "MAIN_UPDATE_ROWS_NOT_%d_GRADIENT_TENSORS:%d_rows_first_row_%d"
                           % (GRADIENT_TENSORS, len(bad), bad[0]))
        facts[str(seed)] = {"on_tensors": len(on), "helm2_tensors": len(helm2), "shared_tensors_compared":
                            len(set(on) & set(helm2)), "on_parameter_count": count, "main_update_rows": len(rows)}
    return (NOT_REPRODUCED if reasons else REPRODUCED), reasons, facts


def self_test(helm2_states, fresh_head, same_bits, numel, flip_one_bit):
    """Plan item 6 check on the real Helm 2.0 files, with no ON file: Helm 2.0's start plus the fresh head, compared
    with itself, must read REPRODUCED; the same with one bit flipped in one shared tensor must read NOT_REPRODUCED
    with exactly that one reason. Returns (passed, facts)."""
    counts = {seed: [GRADIENT_TENSORS] * MAIN_ROWS for seed in SEEDS}
    states = {seed: ({**helm2_states[seed], **fresh_head}, helm2_states[seed]) for seed in SEEDS}
    clean, clean_reasons, _ = judge(states, fresh_head, counts, same_bits, numel)
    seed, name = SEEDS[1], sorted(helm2_states[SEEDS[1]])[0]
    on = dict(states[seed][0])
    on[name] = flip_one_bit(on[name])
    flipped, reasons, _ = judge({**states, seed: (on, states[seed][1])}, fresh_head, counts, same_bits, numel)
    passed = (clean == REPRODUCED and flipped == NOT_REPRODUCED
              and reasons == ["%d:SHARED_TENSORS_NOT_BIT_EQUAL_TO_HELM2:%s" % (seed, name)])
    return passed, {"self_compare": clean, "self_compare_reasons": clean_reasons,
                    "one_flipped_bit": flipped, "one_flipped_bit_reasons": reasons}


def read_gradient_counts(directory):
    """gradient_parameter_count of every main update row, pass 1 to 10 in order. Nothing else is kept."""
    counts = []
    for number in range(1, PASSES + 1):
        path = Path(directory) / ("pass_%02d_updates.jsonl" % number)
        if not path.is_file():
            raise ToolStop("UPDATE_FILE_MISSING:" + str(path))
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                row = json.loads(line)
            except ValueError:
                raise ToolStop("UPDATE_ROW_NOT_JSON:%s:%d" % (path.name, line_number)) from None
            counts.append(row.get("gradient_parameter_count") if type(row) is dict else None)
    return counts


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_pin(seed, path):
    """The Helm 2.0 reference must be the pinned file. A wrong file is a tool stop, not a failed start."""
    if not Path(path).is_file():
        raise ToolStop("HELM2_INITIAL_MISSING:%d:%s" % (seed, path))
    digest = sha256_of(path)
    if digest != HELM2_INITIAL_SHA256[seed]:
        raise ToolStop("HELM2_INITIAL_SHA256_NOT_PINNED:%d:%s" % (seed, digest))
    return digest


def torch_load_state(torch, path):
    """torch.load(weights_only=True) on CPU; the checkpoint's model_state only."""
    payload = torch.load(str(path), map_location="cpu", weights_only=True)
    state = payload.get("model_state") if isinstance(payload, dict) else None
    if not isinstance(state, dict) or not all(isinstance(value, torch.Tensor) for value in state.values()):
        raise ToolStop("NO_MODEL_STATE:" + str(path))
    return dict(state)


def torch_fresh_head(torch, seed=HEAD_SEED):
    """The analogy head exactly as `_build_container` builds it (pointer_learner.py 861-868 at 3df31d96), alone."""
    with torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(seed)
        head = torch.nn.Sequential(
            torch.nn.Linear(452, 64, bias=False), torch.nn.GELU(),
            torch.nn.LayerNorm(64), torch.nn.Linear(64, 1, bias=True))
    return {"analogy_head." + name: value.detach().clone() for name, value in head.state_dict().items()}


def torch_same_bits(torch):
    def same(a, b):
        return (a.dtype == b.dtype and tuple(a.shape) == tuple(b.shape) and bool(torch.equal(a, b))
                and bool(torch.equal(a.detach().reshape(-1).view(torch.uint8),
                                     b.detach().reshape(-1).view(torch.uint8))))
    return same


def torch_flip_one_bit(torch):
    def flip(tensor):
        copy = tensor.detach().clone().contiguous()
        raw = copy.reshape(-1).view(torch.uint8)
        raw[0] = raw[0] ^ 1
        return copy
    return flip


def _seed_map(values, flag):
    out = {}
    for value in values or ():
        seed_text, _, path = value.partition("=")
        if not seed_text.isdigit() or not path or int(seed_text) in out:
            raise ToolStop("BAD_ARGUMENT:%s %s" % (flag, value))
        out[int(seed_text)] = Path(path)
    if sorted(out) != list(SEEDS):
        raise ToolStop("ARGUMENT_SEEDS_NOT_THE_THREE_STUDY_SEEDS:" + flag)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prereg A5.5 matched-start check (AWS only).")
    parser.add_argument("--on", action="append", help="SEED=DIR with the ON initial.pt and pass_NN_updates.jsonl")
    parser.add_argument("--helm2", action="append", help="SEED=PATH to Helm 2.0's initial.pt for that seed")
    parser.add_argument("--out", help="write the reading here too (create-only)")
    parser.add_argument("--self-test", action="store_true",
                        help="Helm 2.0 files only (--helm2): self-compare must pass, one flipped bit must fail")
    args = parser.parse_args(argv)
    try:
        if sys.platform == "win32":
            raise ToolStop("AWS_ONLY_NOT_ON_THE_LAPTOP")
        if args.out and Path(args.out).exists():
            raise ToolStop("OUT_ALREADY_EXISTS:" + args.out)
        helm2_paths = _seed_map(args.helm2, "--helm2")
        on_dirs = {} if args.self_test else _seed_map(args.on, "--on")
        inputs = {str(seed): {"helm2_initial_sha256": check_pin(seed, helm2_paths[seed])} for seed in SEEDS}
        for seed in on_dirs:
            initial = on_dirs[seed] / "initial.pt"
            if not initial.is_file():
                raise ToolStop("ON_INITIAL_MISSING:%d:%s" % (seed, initial))
            inputs[str(seed)]["on_initial_sha256"] = sha256_of(initial)
        gradient_counts = {seed: read_gradient_counts(on_dirs[seed]) for seed in on_dirs}
        import torch
        helm2_states = {seed: torch_load_state(torch, helm2_paths[seed]) for seed in SEEDS}
        numel = lambda tensor: int(tensor.numel())  # noqa: E731
        if args.self_test:
            passed, facts = self_test(helm2_states, torch_fresh_head(torch), torch_same_bits(torch), numel,
                                      torch_flip_one_bit(torch))
            verdict, reasons = "MATCHED_START_SELF_TEST:" + ("PASS" if passed else "FAIL"), []
        else:
            states = {seed: (torch_load_state(torch, on_dirs[seed] / "initial.pt"), helm2_states[seed])
                      for seed in SEEDS}
            verdict, reasons, facts = judge(states, torch_fresh_head(torch), gradient_counts,
                                            torch_same_bits(torch), numel)
    except ToolStop as stop:
        print(json.dumps({"schema": SCHEMA, "verdict": TOOL_STOP, "reason": str(stop)}, indent=1))
        print(TOOL_STOP + ":" + str(stop))
        return 1
    reading = {"schema": SCHEMA, "prereg": "PREREG_ANALOGY_WIRING_PROBE_v0_2.md A5.5 (d7023288)",
               "verdict": verdict, "reasons": reasons, "facts": facts, "inputs": inputs,
               "torch": torch.__version__, "label": "CLAUDE_BUILT_CLAUDE_CHECKED"}
    text = json.dumps(reading, indent=1, sort_keys=True)
    if args.out:
        with open(args.out, "x", encoding="utf-8", newline="\n") as stream:
            stream.write(text + "\n")
    print(text)
    print(verdict)
    if args.self_test:
        return 0 if verdict.endswith(":PASS") else 4
    return 0 if verdict == REPRODUCED else 3


if __name__ == "__main__":
    sys.exit(main())
