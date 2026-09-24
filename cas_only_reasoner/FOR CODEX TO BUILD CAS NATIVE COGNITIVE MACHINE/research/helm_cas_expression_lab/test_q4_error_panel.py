"""Static checks of q4_error_panel.py. NO torch, NO model, NO GPU: only its pure-Python parts run here.

The neural stages (Stage 0, Q3-Q6) run only on AWS. These tests check what can be checked without them:
panel selection and its digest, compiler-derived one-field edits, matched partners, the tie-break rule, custody
(eval/sealed names refused), fail-closed GPU_REQUIRED before any torch import, and source hygiene (no optimizer,
no step, no evaluator door). They also re-derive the known first-error split of the 16 saved dev predictions,
and run the Stage 0, Q3, Q4 and Q5 code end to end on a pure-Python FAKE model (not Q4; only a wiring check).

Run (small, local):  python -B -m pytest test_q4_error_panel.py -q -p no:cacheprovider
"""
import collections
from pathlib import Path
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import q4_error_panel as ep  # noqa: E402
import q4_sdg_curriculum as sdg  # noqa: E402
from learner_q4_decoder import ast_to_tokens  # noqa: E402

RUN = HERE.parents[1] / "records" / "q4_authorized_20260922" / "run_001"
DATA = HERE / "data" / "q3_v0_7"


@pytest.fixture(scope="module")
def selected():
    records = ep.read_run(RUN)
    train, dev = ep.visible_rows(DATA, records["plan"])
    compiler = sdg.Compiler()
    rows, selection = ep.select_panels(train, dev, compiler)
    return records, train, dev, compiler, rows, selection


def test_module_imports_no_torch_and_has_no_training_step():
    assert "torch" not in sys.modules
    source = (HERE / "q4_error_panel.py").read_text(encoding="utf-8")
    for forbidden in ("torch.optim", ".step(", "load_split", "load_dataset", "save_checkpoint", "read_text("):
        assert forbidden not in source, forbidden
    assert source.count("read_bytes(") == 1          # only inside guarded_read
    assert source.count(".open(") == 1                # only write_once, create-only ("xb")


def test_gpu_required_fails_before_torch_or_any_write(tmp_path):
    out = tmp_path / "out"
    for device in ("cpu", "cuda", "", None, "cuda:x"):
        with pytest.raises(ep.PanelError, match="GPU_REQUIRED"):
            ep.run(RUN, DATA, out, device=device)
    assert not out.exists() and "torch" not in sys.modules


def test_custody_refuses_eval_and_sealed_names(tmp_path):
    for name in ("sealed_G_dev.jsonl", "visible_G_eval.jsonl", "SEALED_notes.txt"):
        folder = tmp_path / name.replace(".", "_")
        folder.mkdir()
        (folder / name).write_bytes(b"")               # never read; only its NAME is checked
        with pytest.raises(ep.PanelError, match="CUSTODY_REFUSED"):
            ep.check_data_custody(folder)
        with pytest.raises(ep.PanelError, match="CUSTODY_REFUSED"):
            ep.guarded_read(folder / name)
    ep.check_data_custody(DATA)                         # the worktree's Q3 folder holds no such file


def test_panel_selection_is_declared_and_stable(selected):
    records, train, dev, compiler, rows, selection = selected
    assert selection["counts"] == {"old_dev16": 16, "public64": 64, "teaching16": 16}
    by_panel = collections.defaultdict(list)
    for row in rows:
        by_panel[row["panel"]].append(row)
    assert [r["record_id"] for r in by_panel["old_dev16"]] == [r["record_id"] for r in dev[:16]]
    consumed = ep.consumed_positions(len(train))
    assert [r["origin"]["index"] for r in by_panel["teaching16"]] == consumed[:16]
    public_train = [r for r in by_panel["public64"] if r["origin"]["split"] == "train"]
    public_dev = [r for r in by_panel["public64"] if r["origin"]["split"] == "dev"]
    assert len(public_train) == 32 and len(public_dev) == 32
    assert not {r["origin"]["index"] for r in public_train} & set(consumed)
    assert collections.Counter(r["q3_tree_shape_key"] for r in public_train) == {k: 2 for k in sdg.G_TRAIN_SHAPES}
    assert all(r["origin"]["index"] >= 16 for r in public_dev)
    dev_counts = collections.Counter(r["q3_tree_shape_key"] for r in public_dev)
    assert set(dev_counts) <= set(sdg.G_DEV_SHAPES) and max(dev_counts.values()) - min(dev_counts.values()) <= 4
    again, selection_again = ep.select_panels(train, dev, compiler)
    assert selection_again["digest"] == selection["digest"] and again == rows
    for row in rows:
        assert row["target_source"].startswith("RECOMPILED_FROM_VISIBLE_TEXT")
        assert list(ast_to_tokens(row["target_ast"])) == row["target_tokens"]


def test_saved_predictions_first_errors_match_the_recovery(selected):
    """10/16 lost branch at position 2, 5/16 wrong Noetic at 3, 1/16 PLUS for TIMES at 1 (ownership record)."""
    records, train, dev, compiler, rows, selection = selected
    targets = {r["record_id"]: r["target_tokens"] for r in rows if r["panel"] == "old_dev16"}
    kinds = collections.Counter()
    for saved in records["predictions"]:
        wrong = sdg.first_wrong_decision(ast_to_tokens(saved["ast"]), targets[saved["record_id"]])
        kinds[(wrong["mistake"], wrong["index"])] += 1
    assert kinds == {("LOST_BRANCH", 2): 10, ("WRONG_NOETIC", 3): 5, ("PLUS_FOR_TIMES", 1): 1}


def test_one_field_edits_change_exactly_one_token(selected):
    records, train, dev, compiler, rows, selection = selected
    sample = [next(r for r in rows if r["panel"] == panel) for panel in ("old_dev16", "teaching16", "public64")]
    for row in sample:
        edits, why = ep.one_field_edits(row, compiler)
        assert why is None
        assert len(edits) == 4 * row["leaf_count"]
        for edit in edits:
            if edit.get("to") is None:
                continue
            artifact = compiler.compile_expression(edit["observation"]).to_dict()
            tokens = ast_to_tokens(sdg.q3.to_lab_spelling(artifact["ast"]))
            diff = [i for i, (a, b) in enumerate(zip(tokens, row["target_tokens"])) if a != b]
            assert diff == [edit["position"]] and row["slot_kinds"][edit["position"]] == edit["field"]
            assert sdg.is_canonical_surface(edit["observation"])


def test_matched_partners_share_shape_and_length(selected):
    records, train, dev, compiler, rows, selection = selected
    partners = ep.matched_partners(rows)
    by_id = {r["record_id"]: r for r in rows}
    shape_counts = collections.Counter(r["q3_tree_shape_key"] for r in rows)
    for row in rows:
        if row["record_id"] not in partners:
            assert shape_counts[row["q3_tree_shape_key"]] == 1
            continue
        other = by_id[partners[row["record_id"]]]
        assert other["q3_tree_shape_key"] == row["q3_tree_shape_key"]
        assert len(other["target_tokens"]) == len(row["target_tokens"])
        assert other["content_sha256"] != row["content_sha256"]


def test_choice_rule_matches_free_decoding_tie_break():
    assert ep.choose([1.0, 1.0, 0.0]) == 0
    assert ep.choose([1.0, 1.0, 0.0], (1, 2)) == 1
    probabilities = ep.softmax([0.0, 0.0, 0.0], (0, 2))
    assert set(probabilities) == {0, 2} and abs(sum(probabilities.values()) - 1.0) < 1e-12


class FakeModel:
    """A pure-Python stand-in with the model's public inference surface. NOT Q4 and NOT neural: it only lets the
    stage code (Stage 0, Q3, Q4, Q5) run end to end here, so a key or type error cannot first appear on AWS."""

    def encode(self, observation):
        from learner_q4_representation import Bottleneck
        ids = observation.byte_ids
        return Bottleneck(tuple(float(sum(ids[i::8]) % 97) / 97.0 for i in range(8)))

    def next_logits(self, bottleneck, generated):
        from learner_q4_decoder import TOKENS
        seed = sum(bottleneck.values) + 0.37 * len(generated) + 0.011 * sum(generated)
        return tuple(((seed * (k + 3)) % 1.0) for k in range(len(TOKENS)))

    def generate(self, observation):
        from learner_q4_decoder import free_decode
        return free_decode(self.encode(observation), self.next_logits)


def test_stage_code_runs_end_to_end_on_a_fake_model(selected, monkeypatch):
    records, train, dev, compiler, rows, selection = selected
    from learner_q4_representation import encode_observation
    model = FakeModel()
    reproduced, mismatches = ep.stage0(model, records, dev)
    assert len(reproduced) == 16 and len(mismatches) == 16          # a fake model must NOT reproduce the saved run

    def fake_teacher(model, row):
        b = model.encode(encode_observation(row["observation"]))
        return [list(model.next_logits(b, tuple(row["target_tokens"][:i]))) for i in range(len(row["target_tokens"]))]
    monkeypatch.setattr(ep, "teacher_logits", fake_teacher)
    subset = [r for r in rows if r["panel"] == "old_dev16"][:6] + [r for r in rows if r["panel"] == "teaching16"][:2]
    bottlenecks = {r["record_id"]: model.encode(encode_observation(r["observation"])) for r in subset}
    q3_result, stepwise = ep.run_q3(model, subset, bottlenecks, lambda: None)
    assert q3_result["summary"]["all"]["rows"] == len(subset)
    assert all(r["crosscheck"]["max_abs_logit_gap_stepwise_vs_full_sequence"] == 0.0 for r in q3_result["per_row"])
    q4_result = ep.run_q4(model, subset[:3], bottlenecks, compiler, lambda: None)
    assert q4_result["summary"]["all/noetic"]["edits"] >= 3
    q5_result = ep.run_q5(model, subset, bottlenecks, stepwise, lambda: None)
    assert q5_result["summary"]["rows_with_partner"] >= 2
    assert all(r["max_abs_delta_p_gold_control"] == 0.0 for r in q5_result["per_row"] if "partner" in r)
    for value in (q3_result, q4_result, q5_result):
        ep.canonical(value)                                          # finite and JSON-serialisable
