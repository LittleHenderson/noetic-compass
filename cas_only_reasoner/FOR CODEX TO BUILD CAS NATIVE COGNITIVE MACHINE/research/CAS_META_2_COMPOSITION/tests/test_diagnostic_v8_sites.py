"""Pure synthetic decision-site tests; no model, provider, or native execution."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_meta2 import codec, grammar_v3
from cas_meta2.ir import Limits
from cas_meta2.selection_v3 import target_token_roles
from cas_meta2.diagnostic_v8 import sites


def run(cjt="A", source="arg", output="v0"):
    return {"kind": "RUN", "cjt_id": cjt, "input": source, "output": output}


def call(child="p0", source="v0", output="v2"):
    return {"kind": "CALL", "procedure": child, "input": source, "output": output}


def procedure(steps, returned, scope=("A", "B", "C")):
    return {"input": "arg", "allowed_cjts": list(scope), "steps": steps, "return": returned}


def example():
    return {"binding": 0, "program": {"schema": codec.SCHEMA, "entry": "main", "procedures": {
        "main": procedure([run(), run("B", output="v1"), call(),
                           call("p1", "v2", "v3")], "v3"),
        "p0": procedure([run("C")], "v0"),
        "p1": procedure([run("B")], "v0"),
    }}}


def ids(action):
    return codec.action_to_ids(action, max_length=256)


def compare(reference, generated):
    return sites.compare_sites(ids(reference), ids(generated))


def row_for(result, role, procedure="main", instruction=None):
    found = [row for row in result["rows"]
             if row["reference_site"]["role"] == role
             and row["reference_site"]["procedure"] == procedure
             and (instruction is None or row["reference_site"]["instruction_index"] == instruction)]
    if len(found) != 1:
        raise AssertionError((role, procedure, instruction, len(found)))
    return found[0]


class DecisionSiteTests(unittest.TestCase):
    def test_identical_complete_program_all_sites(self):
        result = compare(example(), example())
        self.assertEqual(result["reference"]["termination"], "COMPLETE")
        self.assertEqual(result["generated"]["termination"], "COMPLETE")
        self.assertEqual(result["totals"]["reference_sites"], 12)
        self.assertEqual(result["totals"]["correct"], 12)
        self.assertEqual(result["totals"]["scored_identical_prefix"], 12)
        self.assertEqual(result["totals"]["scored_after_prefix_divergence"], 0)
        self.assertEqual(result["totals"]["single_option_scored"], 3)
        self.assertEqual(result["totals"]["multi_option_scored"], 9)
        self.assertEqual(set(result["summaries"]), set(sites.ROLES))

    def test_site_prefix_excludes_choice_and_includes_bos(self):
        stream = ids(example())
        target_roles = target_token_roles(example(), max_length=256)
        extracted = sites.extract_sites(stream)
        for site in extracted["sites"]:
            self.assertEqual(site["prefix_ids"], stream[:site["token_index"]])
            self.assertEqual(stream[site["token_index"]], site["chosen_token_id"])
            self.assertEqual(site["prefix_ids"][0], codec.BOS_ID)
            state = grammar_v3.GrammarState.from_ids(site["prefix_ids"], max_length=256)
            self.assertEqual(site["allowed_ids"], list(state.allowed_ids()))
            training_role = {"call_input": "step_input", "run_input": "step_input",
                             "parent_return": "return_value", "child_return": "return_value"}.get(
                                 site["role"], site["role"])
            self.assertEqual(target_roles[site["token_index"]], training_role)
        binding = extracted["sites"][0]
        self.assertEqual(binding["token_index"], 1)
        self.assertEqual(binding["role"], "observation_binding")

    def test_changed_binding_does_not_score_later_context_as_same(self):
        generated = example()
        generated["binding"] = 1
        result = compare(example(), generated)
        self.assertEqual(result["totals"]["scored"], 1)
        self.assertEqual(result["totals"]["wrong"], 1)
        self.assertEqual(result["totals"]["context_changed"], 11)

    def test_changed_child_is_local_error_then_binding_context_changed(self):
        generated = example()
        steps = generated["program"]["procedures"]["main"]["steps"]
        steps[2]["procedure"], steps[3]["procedure"] = "p1", "p0"
        result = compare(example(), generated)
        target = row_for(result, "call_target", instruction=2)
        binding = row_for(result, "call_input", instruction=2)
        self.assertEqual(target["correspondence"], "MATCHED")
        self.assertFalse(target["correct"])
        self.assertEqual(binding["correspondence"], "CONTEXT_CHANGED")
        self.assertIsNone(binding["correct"])
        self.assertIn("partial_instruction", binding["context_differences"])

    def test_same_v0_after_different_producer_is_changed_context(self):
        generated = example()
        generated["program"]["procedures"]["main"]["steps"][0]["cjt_id"] = "B"
        result = compare(example(), generated)
        row = row_for(result, "call_input", instruction=2)
        self.assertEqual(row["correspondence"], "CONTEXT_CHANGED")
        self.assertIn("procedures", row["context_differences"])
        self.assertIsNone(row["correct"])

    def test_unique_output_rename_maps_definition_not_literal_name(self):
        generated = example()
        main = generated["program"]["procedures"]["main"]
        for step in main["steps"]:
            for key in ("input", "output"):
                if step[key] == "v0":
                    step[key] = "v31"
        result = compare(example(), generated)
        row = row_for(result, "call_input", instruction=2)
        self.assertEqual(row["correspondence"], "MATCHED")
        self.assertTrue(row["correct"])
        self.assertEqual(row["expected_token_id"], codec.ACTION_TO_ID["v31"])
        self.assertTrue(row["preceding_tokens_differ"])
        self.assertGreater(result["totals"]["scored_after_prefix_divergence"], 0)
        self.assertEqual(result["totals"]["correct"], 12)

    def test_equal_looking_runs_remain_distinct_definitions(self):
        reference = example()
        reference["program"]["procedures"]["main"]["steps"][1]["cjt_id"] = "A"
        generated = deepcopy(reference)
        generated["program"]["procedures"]["main"]["steps"][2]["input"] = "v1"
        result = compare(reference, generated)
        row = row_for(result, "call_input", instruction=2)
        self.assertEqual(row["correspondence"], "MATCHED")
        self.assertFalse(row["correct"])
        self.assertNotEqual(row["generated_site"]["value_definitions"]["v0"],
                            row["generated_site"]["value_definitions"]["v1"])

    def test_extra_instruction_does_not_pair_nth_call(self):
        generated = example()
        generated["program"]["procedures"]["main"]["steps"].insert(2, run("C", output="v31"))
        result = compare(example(), generated)
        row = row_for(result, "call_target", instruction=2)
        self.assertEqual(row["correspondence"], "SITE_MISSING")
        self.assertIsNone(row["correct"])
        self.assertGreater(result["totals"]["generated_extra_sites"], 0)
        self.assertEqual(result["totals"]["reference_sites"], 12)

    def test_early_return_preserves_missing_calls_and_changed_return(self):
        generated = example()
        generated["program"]["procedures"] = {
            "main": procedure([run()], "v0")}
        result = compare(example(), generated)
        self.assertEqual(row_for(result, "call_target", instruction=2)["correspondence"], "SITE_MISSING")
        returned = row_for(result, "parent_return")
        self.assertEqual(returned["correspondence"], "CONTEXT_CHANGED")
        self.assertIsNone(returned["correct"])
        self.assertEqual(result["totals"]["reference_sites"], 12)

    def test_procedure_rename_is_not_semantic_child_equivalence(self):
        generated = example()
        procedures = generated["program"]["procedures"]
        procedures["p2"] = procedures.pop("p1")
        procedures["main"]["steps"][3]["procedure"] = "p2"
        result = compare(example(), generated)
        child = row_for(result, "child_return", procedure="p1")
        self.assertEqual(child["correspondence"], "SITE_MISSING")
        self.assertTrue(any(site["procedure"] == "p2" for site in result["extra_generated_sites"]))

    def test_changed_scope_and_prefix_length_recorded(self):
        generated = example()
        for proc in generated["program"]["procedures"].values():
            proc["allowed_cjts"].append("R")
        result = compare(example(), generated)
        row = row_for(result, "call_target", instruction=2)
        self.assertEqual(row["correspondence"], "CONTEXT_CHANGED")
        self.assertEqual(row["reason"], "PREFIX_LENGTH_OR_TOKEN_BUDGET_CHANGED")
        self.assertIn("prefix_length", row["context_differences"])

    def test_unemitted_terminal_site_not_scored(self):
        reference = ids(example())
        target = next(site for site in sites.extract_sites(reference)["sites"]
                      if site["role"] == "call_target")
        result = sites.compare_sites(reference, target["prefix_ids"])
        row = row_for(result, "call_target", instruction=2)
        self.assertEqual(row["correspondence"], "MATCHED")
        self.assertFalse(row["generated_site"]["observed"])
        self.assertIsNone(row["correct"])
        self.assertEqual(result["totals"]["matched_without_emitted_choice"], 1)
        self.assertGreater(result["totals"]["missing"], 0)

    def test_mask_empty_site_remains_unscored(self):
        prefix = ["[BOS]", "BIND0", "PROC", "main", "ALLOW", "A", "ENDALLOW",
                  "RUN", "A", "arg", "v0", "CALL", "p9", "arg", "v1",
                  "RETURN", "v1", "ENDPROC", "PROC", "p9", "ALLOW", "A",
                  "ENDALLOW", "CALL"]
        result = sites.extract_sites([codec.ACTION_TO_ID[t] for t in prefix])
        self.assertEqual(result["termination"], "GRAMMAR_DEAD_END")
        self.assertEqual(result["sites"][-1]["role"], "call_target")
        self.assertEqual(result["sites"][-1]["allowed_ids"], [])
        self.assertFalse(result["sites"][-1]["observed"])

    def test_illegal_emitted_choice_recorded_without_advancing(self):
        result = sites.extract_sites([codec.BOS_ID, codec.ACTION_TO_ID["RUN"]])
        self.assertEqual(result["termination"], "INVALID_EMITTED_TOKEN")
        self.assertEqual(result["consumed_token_count"], 1)
        self.assertFalse(result["sites"][0]["chosen_token_allowed"])

    def test_malformed_ids_do_not_become_sites(self):
        for values in ([True], [-1], [999], ["1"], None):
            with self.subTest(values=values):
                result = sites.extract_sites(values)
                self.assertEqual(result["termination"], "INVALID_TOKEN_IDS")
                self.assertEqual(result["sites"], [])

    def test_dummy_eos_after_completion_not_silently_trimmed(self):
        result = sites.extract_sites(ids(example()) + [codec.EOS_ID])
        self.assertEqual(result["termination"], "INVALID_EMITTED_TOKEN")
        self.assertEqual(result["error"]["grammar_role"], "complete")
        self.assertFalse(result["complete"])

    def test_budget_stop_separate_from_grammar_dead_end(self):
        result = sites.extract_sites([codec.BOS_ID], max_length=2)
        self.assertEqual(result["termination"], "TOKEN_BUDGET_STOP")
        self.assertFalse(result["sites"][0]["observed"])
        self.assertEqual(result["sites"][0]["allowed_ids"], [])

    def test_correct_reference_required(self):
        with self.assertRaisesRegex(ValueError, "REFERENCE_COMPLETE_VALID_PROGRAM_REQUIRED"):
            sites.compare_sites([codec.BOS_ID], ids(example()))

    def test_partial_call_not_yet_in_committed_edges(self):
        extracted = sites.extract_sites(ids(example()))
        row = next(site for site in extracted["sites"]
                   if site["role"] == "call_input" and site["instruction_index"] == 2)
        self.assertEqual(row["context"]["partial_instruction"]["target"], "p0")
        self.assertEqual(row["context"]["edges"]["main"], [])
        self.assertEqual(row["instruction_index"], 2)

    def test_illegal_expected_choice_and_ambiguous_definition_are_explicit(self):
        row = row_for(compare(example(), example()), "call_input", instruction=2)
        reference, generated = row["reference_site"], deepcopy(row["generated_site"])
        generated["allowed_ids"] = [codec.ACTION_TO_ID["arg"]]
        self.assertEqual(sites._expected_choice(reference, generated)[1], "ILLEGAL")
        generated["value_definitions"]["v31"] = generated["value_definitions"]["v0"]
        self.assertEqual(sites._expected_choice(reference, generated)[1], "AMBIGUOUS_MAPPING")
        generated["value_definitions"].pop("v0")
        generated["value_definitions"].pop("v31")
        self.assertEqual(sites._expected_choice(reference, generated)[1], "MISSING_DEFINITION")

    def test_totals_cover_reference_and_option_denominators(self):
        generated = example()
        generated["program"]["procedures"]["main"]["steps"].insert(2, run("C", output="v31"))
        result = compare(example(), generated)
        for group in [result["totals"], *result["summaries"].values()]:
            self.assertEqual(group["reference_sites"], sum(group[key] for key in
                             ("matched", "context_changed", "missing", "ambiguous")))
            self.assertEqual(group["scored"], group["correct"] + group["wrong"])
            self.assertEqual(group["scored"],
                             group["single_option_scored"] + group["multi_option_scored"])
            self.assertEqual(group["scored"],
                             group["scored_identical_prefix"] + group["scored_after_prefix_divergence"])

    def test_inputs_and_limits_not_mutated_or_aliased(self):
        reference, generated, limits = ids(example()), ids(example()), Limits()
        before = deepcopy((reference, generated, limits))
        result = sites.compare_sites(reference, generated, limits=limits)
        self.assertEqual((reference, generated, limits), before)
        result["rows"][0]["reference_site"]["context"]["limits"]["max_instructions"] = 1
        self.assertEqual(limits.max_instructions, 256)

    def test_role_scope_is_static_main_vs_other_procedure(self):
        result = sites.extract_sites(ids(example()))
        self.assertEqual([site["procedure"] for site in result["sites"]
                          if site["role"] == "parent_return"], ["main"])
        self.assertEqual([site["procedure"] for site in result["sites"]
                          if site["role"] == "child_return"], ["p0", "p1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
