"""Restore the four test functions my 2026-09-21 merge deleted while they were passing.

Found by the peer audit (codex/helm-peer-audit-20260922 @ 0922f339, merge/REPORT.md). The bodies are copied
byte-for-byte from d50abbbc and inserted where they stood: after test_defect_7, before test_defect_8.
The script refuses to write unless every restored function's source is identical to the original.
"""
import ast
import pathlib
import sys

NL = chr(10)
original_path = pathlib.Path(sys.argv[1])      # git show d50abbbc:<file>
current_path = pathlib.Path(sys.argv[2])       # the working-tree file to restore into

NAMES = [
    "test_review_a_deep_flat_chain_fails_cleanly_and_still_serialises",
    "test_review_fn_names_are_not_reserved_but_let_names_and_parameters_are",
    "test_review_no_cross_domain_warning_when_a_side_has_no_known_domain_at_typecheck",
    "test_review_the_worlds_warning_comes_from_the_alias_not_from_the_word",
]
ANCHOR = "def test_defect_8_the_parse_tree_survives_a_typecheck_failure():"


def function_sources(text):
    tree = ast.parse(text)
    return {n.name: ast.get_source_segment(text, n) for n in tree.body if isinstance(n, ast.FunctionDef)}


orig = original_path.read_text(encoding="utf-8")
cur = current_path.read_text(encoding="utf-8")
assert "\r" not in orig and "\r" not in cur, "expected LF files"
orig_src = function_sources(orig)
cur_src = function_sources(cur)
assert all(n in orig_src for n in NAMES), "original is missing a function"
assert not any(n in cur_src for n in NAMES), "already restored"
assert cur.count(ANCHOR) == 1

# The original block runs from the first restored def to the def that followed it, blank lines included.
start = orig.index("def " + NAMES[0] + "(")
end = orig.index(ANCHOR)
block = orig[start:end]
assert all(("def " + n + "(") in block for n in NAMES) and block.endswith(NL + NL + NL)

new = cur.replace(ANCHOR, block + ANCHOR)
new_src = function_sources(new)
for n in NAMES:
    assert new_src[n] == orig_src[n], n + " differs from the original"
for n, s in cur_src.items():
    assert new_src[n] == s, n + " was disturbed"
assert len(new_src) == len(cur_src) + 4

current_path.write_bytes(new.encode("utf-8"))
print("restored %d functions; file now has %d top-level functions (was %d)" % (len(NAMES), len(new_src), len(cur_src)))
