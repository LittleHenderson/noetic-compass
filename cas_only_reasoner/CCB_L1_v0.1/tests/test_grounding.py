"""Grounding: English -> kernel reasoning -> English (charter test 6)."""

from conftest import load_fixture
from lang.l1 import CCB_L1


def _l1():
    return CCB_L1(load_fixture("seed_lexicon.json"))


def test_kernel_answers_yes_and_decodes():
    l1 = _l1()
    result = l1.ask("is the cat gray?")
    assert result["kernel_status"] == "CONCLUDED"
    assert result["answer"] == "yes, the cat is gray."


def test_kernel_answers_unknown_and_decodes():
    l1 = _l1()
    result = l1.ask("is the dog gray?")
    assert result["kernel_status"] == "NEEDS_INFORMATION"
    assert result["answer"] == "i do not know whether the dog is gray."


def test_question_flow_is_one_way():
    # CCB-L1 calls the kernel; the kernel never calls CCB-L1. The kernel
    # package has no import of lang.* (conformance by construction).
    import os
    kernel_root = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "CAS_RRK_v0.1")
    for dirpath, _, files in os.walk(os.path.join(kernel_root, "kernel")):
        for name in files:
            if name.endswith(".py"):
                with open(os.path.join(dirpath, name), "r",
                          encoding="utf-8") as fh:
                    assert "lang" not in fh.read(), name
