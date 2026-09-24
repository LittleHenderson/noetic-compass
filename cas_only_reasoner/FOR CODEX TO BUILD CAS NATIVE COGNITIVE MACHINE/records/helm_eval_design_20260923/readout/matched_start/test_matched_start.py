"""Laptop tests for matched_start.py with pure-Python stand-in tensors. No torch is imported.

Acceptance (readout plan item 6): self-compare passes; one flipped bit fails; wrong head seed fails; wrong count
fails. The stand-in tensors carry a dtype, a shape and raw bytes; `same_bits` compares all three. Shapes are the 48
shared tensors and the 5 head tensors declared in MIGRATION_ON_SHAPES.json (174,303 + 29,121 = 203,424).
Run: python -m unittest <this file>   (from C:\\, with an absolute path). Temp files go to the system temp folder.
"""
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matched_start as ms  # noqa: E402

SHARED_SHAPES = [
    ("round_mix", (3,)), ("round_rate", (1,)), ("declaration_table", (1024, 64)),
    ("directed_pair_embedding", (2, 8)), ("role_embedding", (6, 64)), ("node_encode.weight", (64, 18)),
    ("state_encode.weight", (64, 64)), ("match_key.weight", (64, 64)), ("query_projection.weight", (64, 21)),
    ("query_norm.weight", (64,)), ("query_norm.bias", (64,)), ("attention_key.weight", (1, 64)),
    ("world_projection.weight", (64, 196)), ("declaration_projection.weight", (32, 64)),
    ("node_head.0.weight", (64, 128)), ("node_head.2.weight", (64,)), ("node_head.2.bias", (64,)),
    ("node_head.3.weight", (2, 64)), ("node_head.3.bias", (2,)), ("edge_head.0.weight", (64, 136)),
    ("edge_head.2.weight", (64,)), ("edge_head.2.bias", (64,)), ("edge_head.3.weight", (2, 64)),
    ("edge_head.3.bias", (2,)), ("role_head.0.weight", (64, 198)), ("role_head.2.weight", (64,)),
    ("role_head.2.bias", (64,)), ("role_head.3.weight", (2, 64)), ("role_head.3.bias", (2,)),
    ("pointer_key.weight", (64, 64)), ("reach_option_head.0.weight", (64, 260)),
    ("reach_option_head.2.weight", (64,)), ("reach_option_head.2.bias", (64,)),
    ("reach_option_head.3.weight", (2, 64)), ("reach_option_head.3.bias", (2,)),
    ("mode_option_head.0.weight", (64, 192)), ("mode_option_head.2.weight", (64,)),
    ("mode_option_head.2.bias", (64,)), ("mode_option_head.3.weight", (2, 64)), ("mode_option_head.3.bias", (2,)),
    ("world_head.0.weight", (64, 38)), ("world_head.2.weight", (64,)), ("world_head.2.bias", (64,)),
    ("world_head.3.weight", (1, 64)), ("world_head.3.bias", (1,)), ("left.weight", (64, 64)),
    ("merge.weight", (64, 128)), ("right.weight", (64, 64))]
HEAD_SHAPES = [("analogy_head.0.weight", (64, 452)), ("analogy_head.2.weight", (64,)),
               ("analogy_head.2.bias", (64,)), ("analogy_head.3.weight", (1, 64)), ("analogy_head.3.bias", (1,))]


class Fake:
    """Stand-in tensor: float32 dtype name, shape, raw little-endian bytes."""

    def __init__(self, shape, data, dtype="float32"):
        self.shape, self.data, self.dtype = tuple(shape), bytes(data), dtype


def numel(tensor):
    total = 1
    for size in tensor.shape:
        total *= size
    return total


def same_bits(a, b):
    return a.dtype == b.dtype and a.shape == b.shape and a.data == b.data


def build(shapes, seed):
    rng = random.Random(seed)
    return {name: Fake(shape, rng.randbytes(4 * numel(Fake(shape, b"")))) for name, shape in shapes}


def fresh_head(seed):
    return build(HEAD_SHAPES, 7_000_000_000 + seed)


def flip_bit(tensor, byte_index=0, bit=0):
    data = bytearray(tensor.data)
    data[byte_index] ^= 1 << bit
    return Fake(tensor.shape, data, tensor.dtype)


def world(head_seed=ms.HEAD_SEED):
    """Helm 2.0 starts for the three seeds, the ON starts built from them, and 1,470 rows of 53 per seed."""
    helm2 = {seed: build(SHARED_SHAPES, seed) for seed in ms.SEEDS}
    states = {seed: ({**helm2[seed], **fresh_head(head_seed)}, helm2[seed]) for seed in ms.SEEDS}
    counts = {seed: [53] * 1470 for seed in ms.SEEDS}
    return states, counts


class JudgeTests(unittest.TestCase):
    def run_judge(self, states, counts, head=None):
        return ms.judge(states, fresh_head(ms.HEAD_SEED) if head is None else head, counts, same_bits, numel)

    def test_self_compare_passes(self):
        states, counts = world()
        verdict, reasons, facts = self.run_judge(states, counts)
        self.assertEqual((verdict, reasons), (ms.REPRODUCED, []))
        for seed in ms.SEEDS:
            self.assertEqual(facts[str(seed)]["on_parameter_count"], 203424)
            self.assertEqual(facts[str(seed)]["shared_tensors_compared"], 48)

    def test_one_flipped_bit_in_a_shared_tensor_fails(self):
        states, counts = world()
        on, helm2 = states[20260918]
        on = dict(on)
        on["declaration_table"] = flip_bit(on["declaration_table"], byte_index=1234, bit=5)
        states[20260918] = (on, helm2)
        verdict, reasons, _ = self.run_judge(states, counts)
        self.assertEqual(verdict, ms.NOT_REPRODUCED)
        self.assertEqual(reasons, ["20260918:SHARED_TENSORS_NOT_BIT_EQUAL_TO_HELM2:declaration_table"])

    def test_one_flipped_bit_in_the_head_fails(self):
        states, counts = world()
        on, helm2 = states[20260919]
        on = dict(on)
        on["analogy_head.3.bias"] = flip_bit(on["analogy_head.3.bias"], byte_index=3, bit=7)
        states[20260919] = (on, helm2)
        verdict, reasons, _ = self.run_judge(states, counts)
        self.assertEqual(verdict, ms.NOT_REPRODUCED)
        self.assertEqual(reasons, [
            "20260919:ANALOGY_HEAD_NOT_EQUAL_TO_FRESH_BUILD_SEED_20260923:analogy_head.3.bias",
            "20260919:ANALOGY_HEAD_DIFFERS_FROM_SEED_20260917:analogy_head.3.bias"])

    def test_wrong_head_seed_fails(self):
        states, counts = world(head_seed=20260924)  # identical across seeds, but not the seed-20260923 build
        verdict, reasons, _ = self.run_judge(states, counts)
        self.assertEqual(verdict, ms.NOT_REPRODUCED)
        self.assertEqual(len(reasons), 3)
        self.assertTrue(all("ANALOGY_HEAD_NOT_EQUAL_TO_FRESH_BUILD_SEED_20260923:" in r for r in reasons))

    def test_head_differing_across_seeds_fails(self):
        states, counts = world()
        on, helm2 = states[20260918]
        states[20260918] = ({**on, **fresh_head(20260925)}, helm2)
        verdict, reasons, _ = self.run_judge(states, counts)
        self.assertEqual(verdict, ms.NOT_REPRODUCED)
        self.assertEqual([r.split(":")[1] for r in reasons],
                         ["ANALOGY_HEAD_NOT_EQUAL_TO_FRESH_BUILD_SEED_20260923", "ANALOGY_HEAD_DIFFERS_FROM_SEED_20260917"])

    def test_wrong_parameter_count_fails(self):
        # Same bits on both sides and the right head, but a shared tensor one row larger: only the count fails.
        states, counts = world()
        on, helm2 = states[20260917]
        bigger = Fake((3, 2), bytes(24))
        on, helm2 = {**on, "round_mix": bigger}, {**helm2, "round_mix": bigger}
        states[20260917] = (on, helm2)
        verdict, reasons, _ = self.run_judge(states, counts)
        self.assertEqual(verdict, ms.NOT_REPRODUCED)
        self.assertEqual(reasons, ["20260917:PARAMETER_COUNT_203427_NOT_203424"])

    def test_wrong_gradient_count_fails(self):
        for bad_value in (52, 54, 53.0, True, None, "53"):
            states, counts = world()
            counts[20260919] = list(counts[20260919])
            counts[20260919][700] = bad_value
            verdict, reasons, _ = self.run_judge(states, counts)
            self.assertEqual(verdict, ms.NOT_REPRODUCED, bad_value)
            self.assertEqual(reasons, ["20260919:MAIN_UPDATE_ROWS_NOT_53_GRADIENT_TENSORS:1_rows_first_row_701"])

    def test_wrong_row_total_fails(self):
        states, counts = world()
        counts[20260918] = [53] * 1469
        verdict, reasons, _ = self.run_judge(states, counts)
        self.assertEqual((verdict, reasons), (ms.NOT_REPRODUCED, ["20260918:MAIN_UPDATE_ROWS_1469_NOT_1470"]))

    def test_wrong_tensor_sets_fail(self):
        states, counts = world()
        on, helm2 = states[20260917]
        helm2 = dict(helm2)
        del helm2["round_rate"]  # Helm 2.0 reference with 47 tensors
        states[20260917] = (on, helm2)
        verdict, reasons, _ = self.run_judge(states, counts)
        self.assertEqual(verdict, ms.NOT_REPRODUCED)
        self.assertIn("20260917:HELM2_INITIAL_HAS_47_TENSORS_NOT_48", reasons)
        self.assertIn("20260917:ON_EXTRA_TENSORS_ARE_NOT_THE_5_ANALOGY_HEAD_TENSORS:"
                      "analogy_head.0.weight,analogy_head.2.bias,analogy_head.2.weight,analogy_head.3.bias,"
                      "analogy_head.3.weight,round_rate", reasons)

    def test_missing_seed_fails(self):
        states, counts = world()
        del states[20260919]
        del counts[20260919]
        verdict, reasons, _ = self.run_judge(states, counts)
        self.assertEqual(verdict, ms.NOT_REPRODUCED)
        self.assertEqual(reasons, ["SEEDS_ARE_NOT_THE_THREE_STUDY_SEEDS:20260917,20260918"])


class SelfTestTests(unittest.TestCase):
    def helm2(self):
        return {seed: build(SHARED_SHAPES, seed) for seed in ms.SEEDS}

    def test_self_test_passes(self):
        passed, facts = ms.self_test(self.helm2(), fresh_head(ms.HEAD_SEED), same_bits, numel, flip_bit)
        self.assertTrue(passed)
        self.assertEqual((facts["self_compare"], facts["one_flipped_bit"]), (ms.REPRODUCED, ms.NOT_REPRODUCED))
        self.assertEqual(facts["one_flipped_bit_reasons"],
                         ["20260918:SHARED_TENSORS_NOT_BIT_EQUAL_TO_HELM2:attention_key.weight"])

    def test_self_test_catches_a_blind_comparison(self):
        blind = lambda a, b: a.dtype == b.dtype and a.shape == b.shape  # noqa: E731  (ignores the bytes)
        passed, facts = ms.self_test(self.helm2(), fresh_head(ms.HEAD_SEED), blind, numel, flip_bit)
        self.assertFalse(passed)
        self.assertEqual(facts["one_flipped_bit"], ms.REPRODUCED)

    def test_self_test_catches_a_wrong_count(self):
        helm2 = self.helm2()
        helm2[20260917] = {name: t for name, t in helm2[20260917].items() if name != "round_rate"}  # 47 tensors
        passed, facts = ms.self_test(helm2, fresh_head(ms.HEAD_SEED), same_bits, numel, flip_bit)
        self.assertFalse(passed)
        self.assertEqual(facts["self_compare"], ms.NOT_REPRODUCED)

    def test_self_test_catches_a_misnamed_fresh_head(self):
        head = {name.replace("analogy_head.", ""): t for name, t in fresh_head(ms.HEAD_SEED).items()}
        passed, _ = ms.self_test(self.helm2(), head, same_bits, numel, flip_bit)
        self.assertFalse(passed)


class FileTests(unittest.TestCase):
    def test_read_gradient_counts_reads_ten_passes_in_order(self):
        with tempfile.TemporaryDirectory() as folder:
            for number in range(1, 11):
                rows = [{"gradient_parameter_count": 53, "raw_batch_loss": 0.5, "cursor_committed": i}
                        for i in range(147)]
                rows[0]["gradient_parameter_count"] = number  # marks the file order
                Path(folder, "pass_%02d_updates.jsonl" % number).write_text(
                    "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            counts = ms.read_gradient_counts(folder)
        self.assertEqual(len(counts), 1470)
        self.assertEqual([counts[147 * k] for k in range(10)], list(range(1, 11)))

    def test_missing_update_file_is_a_tool_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "pass_01_updates.jsonl").write_text('{"gradient_parameter_count": 53}\n', encoding="utf-8")
            with self.assertRaises(ms.ToolStop):
                ms.read_gradient_counts(folder)

    def test_bad_json_is_a_tool_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            for number in range(1, 11):
                Path(folder, "pass_%02d_updates.jsonl" % number).write_text('{"gradient_parameter_count": 53}\n',
                                                                          encoding="utf-8")
            Path(folder, "pass_04_updates.jsonl").write_text('{"gradient_parameter_count": 5\n', encoding="utf-8")
            with self.assertRaises(ms.ToolStop):
                ms.read_gradient_counts(folder)

    def test_unpinned_helm2_file_is_a_tool_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "initial.pt")
            path.write_bytes(b"not the pinned Helm 2.0 start")
            with self.assertRaises(ms.ToolStop):
                ms.check_pin(20260917, path)
            with self.assertRaises(ms.ToolStop):
                ms.check_pin(20260917, Path(folder, "absent.pt"))

    def test_seed_arguments(self):
        good = ["20260917=a", "20260918=b", "20260919=c"]
        self.assertEqual(sorted(ms._seed_map(good, "--on")), list(ms.SEEDS))
        for bad in (good[:2], good + ["20260917=d"], ["x=a"] + good[1:], good[:2] + ["20260920=c"]):
            with self.assertRaises(ms.ToolStop):
                ms._seed_map(bad, "--on")

    @unittest.skipUnless(sys.platform == "win32", "laptop-only guard")
    def test_main_refuses_on_the_laptop_without_importing_torch(self):
        self.assertEqual(ms.main(["--on", "20260917=a"]), 1)
        self.assertEqual(ms.main(["--self-test", "--helm2", "20260917=a"]), 1)
        self.assertNotIn("torch", sys.modules)


if __name__ == "__main__":
    unittest.main()
