"""Scratch helper (build of reader v7.3, design 2.6): write the machine-neutral canon (helm_test_pins.canon) of
test_helm_cas_address.fixture_records() with HELM_CAS_ADDRESS=0 and HELM_WIDE_UNITS_NOTE unset -- exactly the records
test_off_is_byte_identical_to_the_pre_change_code pins -- to <out>.json, and print its sha256.
usage: python -X utf8 -B -I dump_off_canon.py <helm tree> <out.json>"""
import hashlib
import os
import sys

tree, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, tree)
os.environ["HELM_CAS_ADDRESS"] = "0"
os.environ.pop("HELM_WIDE_UNITS_NOTE", None)
import helm_test_pins as PINS  # noqa: E402
import test_helm_cas_address as T  # noqa: E402

text = PINS.canon(T.fixture_records())
with open(out, "w", encoding="utf-8", newline="") as fh:
    fh.write(text)
print("sha256", hashlib.sha256(text.encode("utf-8")).hexdigest())
print("pinned", T.PINNED_OFF_SHA256)
