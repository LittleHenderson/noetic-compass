"""HSET-2 pre-salt manifest (CLAUDE_BUILT_CLAUDE_CHECKED): the record A2.7 asks for before the protected key is made.

A2.7 (Codex, c3a128ee), last paragraph: "Before protected-key creation, Claude supplies the reviewed comparator manifest,
digest, complete throwaway feasibility ranges including groups/components, exact tie rules and public split/exposure
attestation." This program writes PRESALT_MANIFEST_HSET2.json from the build's own constants and the committed stage-0
files, plus a throwaway-ranges summary made by `hset2_throwaway_ranges.py --summarize` (counts only; no class key).
No salt is read, no tree is needed, nothing sealed is opened.

    python -B hset2_presalt_manifest.py --ranges RANGES_SUMMARY.json [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.dont_write_bytecode = True
MANIFEST_FILE = "PRESALT_MANIFEST_HSET2.json"
UV_CHECKSUM_URL = "https://github.com/astral-sh/uv/releases/download/0.12.7/uv-x86_64-unknown-linux-gnu.tar.gz.sha256"
UV_CROSS_CHECK_URL = "https://api.github.com/repos/astral-sh/uv/releases/tags/0.12.7"


def lf_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def modules():
    for p in (str(HERE), str(HERE.parent / "hset1a"), str(HERE.parent / "d1_acceptance"), str(HERE.parent / "hset2_aws_job")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import hset2_build as H
    import hset2_stage0_public as S0
    import hset_worlds as hw
    import launch
    return H, S0, hw, launch


# Every place this build differs from A2.7's text (and from the rest of A2 it names), listed; none removes a bar.
DIFFERENCES_FROM_A2_7 = [
    {"item": "DEGREE_FLAGS_TIEBREAK_GUESS_THEN_CHECK", "state": "CONFORMED_IN_THIS_ROUND",
     "note": "the build called it FLAGS_TIEBREAK_GUESS_THEN_CHECK until this round; renamed to A2.7 D2's name, word for word"},
    {"item": "R1 whole-child rule, both sort directions (DEGREE_WHOLE_CHILD_FLAGS_GUESS_THEN_CHECK_CHILDREN_LAST and "
             "..._CHILDREN_FIRST)", "state": "ADDED_BEYOND_A2_7",
     "note": ("Claude's default Q-A (bus claude-0024), pending Codex or the owner; A2.7 does not name this rule. It only "
              "adds bars. Switch R1_ANALOGY_SCOPE_DECISION: a (default), b_widen_scope, c (refused)")},
    {"item": "FIXED_ALIAS_W0..W7", "state": "KEPT_BEYOND_A2_1",
     "note": ("the pre-A2 BEST_FIXED_POSITION table (focus included), kept as eight untuned bars so no bar of the first "
              "version is dropped; A2.1 names only FIXED_POSITION_1..7. They never bind (review R6)")},
    {"item": "'check all required relations and flags' (A2.7 D2)", "state": "READ_AS_CHECKER_V2",
     "note": ("the one-guess rules check every edge (and the node count), which is checker v2's own analogy and "
              "correspondence condition ('node labels, root choice and archetypes do not vote'); the declared domain is "
              "the candidate filter. Declared flags order the guess but are not checked: checker v2 does not require "
              "them, and with fresh flags a flag check would reject most true partners. Codex may rule otherwise")},
    {"item": "the flag-key direction of DEGREE_FLAGS_TIEBREAK_GUESS_THEN_CHECK", "state": "PINNED_ONE_DIRECTION",
     "note": ("pinned ascending (whole, second participant, third participant, then every other node), then rank "
              "ascending, as N1 defined it and as the other one-guess rules sort; the reverse flag order is not "
              "registered. Q-C's 'both directions where the direction changes answers' is applied to the whole-child "
              "key (R1), whose direction no text fixes")},
    {"item": "A2.7 D3 'reprint actual DEV counts, labelled'", "state": "CONFORMED_IN_THIS_ROUND",
     "note": "STAGE0_SUMMARY.json dev_counts_labelled_A2_7_D3 labels foci, eligible decoys and targets, and fillers"},
    {"item": "A2.7 'exact-search ceiling retained separately'", "state": "CONFORMED",
     "note": "never a bar; printed as the full colour-refinement diagnostic (design s6)"},
    {"item": "A2.7 D1 reach claim wording", "state": "CONFORMED_IN_THIS_ROUND",
     "note": "both reach claims print A2.7's two limit sentences verbatim (claim_limits_A2_7)"},
    {"item": "the confirmatory caption (A2.3)", "state": "CONFORMED_IN_THIS_ROUND",
     "note": "REPAIR_IMPROVES_ANALOGY_6 prints A2.3's caption verbatim, only for use if every condition passes"},
]


def manifest(ranges_doc):
    H, S0, hw, launch = modules()
    reg = H.registered_comparators()
    pe1 = json.loads((HERE / S0.PUBLIC_EXCLUDED_V1_FILE).read_text(encoding="utf-8"))
    pe2 = json.loads((HERE / S0.PUBLIC_EXCLUDED_FILE).read_text(encoding="utf-8"))
    stage0 = json.loads((HERE / S0.SUMMARY_FILE).read_text(encoding="utf-8"))
    t5 = json.loads((HERE / "PROPOSED_T5_OLDER_PUBLIC_TEST_SIDE.json").read_text(encoding="utf-8"))
    return {
        "schema": "claude.hset2-presalt-manifest/0.1", "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
        "state": ("PRE_SALT: the bar set, tie rules, pins and exposure attestation fixed before the HSET-2 salt exists. "
                  "Not reviewed by Codex yet. No salt was made or read; no sealed file was opened; no model was run."),
        "design_source": {"branch": "codex/helm-controlled-prelaunch-20260924", "commit": H.DESIGN_SOURCE_COMMIT,
                          "EVALUATION_DESIGN_v0_4_md_sha256": H.DESIGN_V0_4_SHA256_AT_SOURCE,
                          "STATISTICAL_POLICY_json_sha256": H.STATISTICAL_POLICY_SHA256_AT_SOURCE,
                          "what": "A2.7, the single A2 specification (D1-D4), plus A2.1-A2.6 that it completes"},
        "defaults_applied": {
            "Q-A": "R1: register the whole-child rule as bars in BOTH sort directions (R1_ANALOGY_SCOPE_DECISION = a)",
            "Q-B": "T5: PUBLIC_EXCLUDED version 2 = version 1 + the 24 TEST-side older HSET-1B DEV classes",
            "Q-C": "flag-key order and tie rule pinned (tie_rules_pinned) and checked by public toy examples",
            "source": "bus message claude-0024 (Claude to Codex, 2026-09-24T13:40:35Z); silence keeps them; an objection "
                      "reverts them before the salt"},
        "registered_comparators": reg,
        "registered_comparators_digest": hw.sha(reg),
        "tie_rules_pinned": dict(H.TIE_RULES),
        "differences_from_A2_7": DIFFERENCES_FROM_A2_7,
        "pins": {"HSET1A_SALT_SHA256": H.HSET1A_SALT_SHA256,
                 "HSET2_SALT_SHA256": H.HSET2_SALT_SHA256,
                 "HSET2_SALT_SHA256_note": "None on purpose: the custodian alone makes the salt and commits only this",
                 "SOURCE_COMMIT": H.SOURCE_COMMIT,
                 "EXPECTED_TEST5_SHAPES_DIGEST": launch.EXPECTED_TEST5_SHAPES_DIGEST,
                 "EXPECTED_TEST5_SHAPES_DIGEST_source": ("records/helm_eval_design_20260923/hset1a_aws_job/"
                                                         "RESULTS_READING.json test_shapes_digest (salt_sha256 33f9d350...); "
                                                         "unchanged by PUBLIC_EXCLUDED v2, which adds no 5-node class"),
                 "UV_VERSION": launch.UV_VERSION, "UV_TARBALL_SHA256": launch.UV_TARBALL_SHA256,
                 "UV_TARBALL_SHA256_source": UV_CHECKSUM_URL, "UV_TARBALL_SHA256_cross_check": UV_CROSS_CHECK_URL,
                 "PYTHON_VERSION": launch.PYTHON_VERSION},
        "public_excluded": {"version": 2, "file": S0.PUBLIC_EXCLUDED_FILE, "counts_by_nodes": pe2["counts_by_nodes"],
                            "class_digests_digest": pe2["class_digests_digest"],
                            "version_1": {"file": S0.PUBLIC_EXCLUDED_V1_FILE, "counts_by_nodes": pe1["counts_by_nodes"],
                                          "class_digests_digest": pe1["class_digests_digest"]},
                            "rule": pe2["version_2_rule"]},
        "stage0_files_sha256": stage0["files_sha256"],
        "stage0_counts": {"six_node_universe": stage0["six_node_universe"],
                          "sides": {s: {k: v for k, v in stage0["sides"][s].items() if k != "group_size_histogram"}
                                    for s in ("DEV", "TEST")},
                          "groups_digests": stage0["groups_digests"],
                          "dev_new_6_digest": stage0["dev_new_6"]["digest"],
                          "dev_decoys_6_digest": stage0["dev_decoys_6"]["digest"],
                          "dev_counts_labelled_A2_7_D3": stage0["dev_counts_labelled_A2_7_D3"]},
        "split_and_exposure_attestation": {
            "what_is_attested": [
                "The DEV/TEST side of every 6-node degree group is fixed by the public rule of A1 D1; the TEST side is "
                "the public forbidden set; which TEST-side classes become TEST_NEW_6 foci is decided only by the HSET-2 "
                "salt, which does not exist yet.",
                "PUBLIC_EXCLUDED version 2 removes, before the salt, every 5- or 6-node class of the larger-question "
                "fixture file (version 1) and the 24 older public HSET-1B DEV_NEW_6 classes that fall on the TEST side.",
                "TEST_NEW_5 is HSET-1A's split (salt sha256 33f9d350...), never re-drawn; the build checks its public "
                "digest before any item is built.",
                "The DEV side, DEV_NEW_6 and DEV_DECOYS_6 are unchanged by version 2 (digests in stage0_counts)."],
            "exposure_search_scope_from_the_T5_record": t5["exposure_found_in_public_files"],
            "limit": ("A2.7: do not assert clean novelty from stage-0 counts alone. This attests only the searched scope "
                      "above; the not_searched list stays unsearched. Label EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT.")},
        "throwaway_ranges": ranges_doc,
        "files_sha256_lf": {name: lf_sha(HERE / name) for name in (
            "hset2_build.py", "hset2_stage0_public.py", "hset2_throwaway_ranges.py", "hset2_presalt_manifest.py",
            "test_hset2.py")} | {"../hset2_aws_job/" + name: lf_sha(HERE.parent / "hset2_aws_job" / name)
                                  for name in ("launch.py", "job.sh.template", "watch.py", "JOB_LIMITS.md")},
    }


def dump(value):
    return (json.dumps(value, indent=1, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranges", required=True, help="output of hset2_throwaway_ranges.py --summarize")
    parser.add_argument("--check", action="store_true", help="exit 1 unless the committed manifest is identical")
    args = parser.parse_args()
    ranges_doc = json.loads(pathlib.Path(args.ranges).read_text(encoding="utf-8"))
    if not ranges_doc.get("state", "").startswith("THROWAWAY"):
        raise SystemExit("REFUSED: the ranges file is not a throwaway-ranges summary")
    data = dump(manifest(ranges_doc))
    if args.check:
        same = (HERE / MANIFEST_FILE).read_bytes().replace(b"\r\n", b"\n") == data
        print("PRESALT_MANIFEST_CHECK:%s" % ("IDENTICAL" if same else "DIFFERS"))
        return 0 if same else 1
    (HERE / MANIFEST_FILE).write_bytes(data)
    print("%s written: registered_comparators_digest %s" % (MANIFEST_FILE, json.loads(data)["registered_comparators_digest"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
