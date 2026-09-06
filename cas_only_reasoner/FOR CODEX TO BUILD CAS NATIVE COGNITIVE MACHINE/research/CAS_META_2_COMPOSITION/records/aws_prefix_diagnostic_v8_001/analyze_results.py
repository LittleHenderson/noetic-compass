"""Offline, standard-library analysis of the saved-prefix diagnostic JSON packet.

No tensor loading, neural imports, AWS access, native execution or task-outcome
verification. Existing archives and source files are never modified.
"""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "cas-meta2-prefix-json-analysis/8"
WORKER_SHA = "13f424981d7434b1a92815d1ad5759d543bbd3be"
BUNDLE_SHA = "b4d7970ca59c07342942584e4752ad8c129c3125e25ecc241e3d76c9ddd1c629"
CHECKPOINTS = {
    "cas_initial": "ad8c80bf3d3ed7111e118957066ac3f0ec0509681fa2aa00e44d1592403b43fd",
    "cas_selected": "bf709539d8a462fe73909553659ad046305e75428a15d80e83124bc28ee84b46",
    "generic_initial": "20669d0470a583ab172bbb06451c0b6bcbbf190ea10b3e725e7a73c5c046b051",
    "generic_selected": "53e2acdd4635d843210a7aa0a5b194e395f57c0b7f71ca59b1a64dbeae4ca532",
}
ROLES = ("observation_binding", "call_target", "call_input", "run_input", "parent_return", "child_return")
CONDITIONS = ("correct_prefix", "self_generated_prefix")
KINDS = ("raw_full_vocabulary", "grammar_masked")
COHORT_TASKS = {"train_probe": 24, "validation": 96}
# Counts from the frozen bundle manifest b4d7970c...; depth is reference-task depth.
EXPECTED = {
    "train_probe": {1: (8, 0, 0, 64, 8, 0), 2: (8, 32, 32, 90, 8, 24), 3: (8, 32, 32, 86, 8, 24)},
    "validation": {1: (32, 0, 0, 266, 32, 0), 2: (32, 128, 128, 322, 32, 96), 3: (32, 128, 128, 324, 32, 96)},
}
BOUNDARY = (
    "Existing development checkpoints and tasks only. No new training, fresh held-out generalization, "
    "native task correctness, rule-arm measurement, or CAS-specific advantage is established. "
    "Unmatched contexts have no assigned local correctness. Grammar-complete output is not task success."
)


def require(value, reason):
    if not value:
        raise ValueError(reason)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    result = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))
    canonical(result)
    return result


def digest(raw):
    return sha256(raw).hexdigest()


def no_links(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (path, *path.parents)), "PATH_LINK_REFUSED")
    return path


def safe_member(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name and "\x00" not in name
        and not PurePosixPath(name).is_absolute() and PurePosixPath(name).as_posix() == name
        and all(part not in ("", ".", "..") for part in name.split("/")), "UNSAFE_ZIP_PATH")
    return name


def read_packet(archive_path, expected_sha256=None):
    path = no_links(archive_path)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= 256 * 1024**2, "ARCHIVE_SIZE_OR_TYPE")
    with path.open("rb") as stream:
        raw = stream.read(256 * 1024**2 + 1)
    after = path.stat()
    require(len(raw) == before.st_size and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "ARCHIVE_CHANGED_DURING_READ")
    observed_sha = digest(raw)
    if expected_sha256 is not None:
        require(re.fullmatch("[0-9a-f]{64}", expected_sha256) and observed_sha == expected_sha256,
                "EXTERNAL_ARCHIVE_PIN_MISMATCH")
    with ZipFile(io.BytesIO(raw)) as zipped:
        infos = zipped.infolist()
        names = [safe_member(info.filename) for info in infos]
        require(0 < len(names) <= 2048 and len(names) == len(set(names)) == len({n.casefold() for n in names}),
                "ZIP_DUPLICATE_OR_MEMBER_BOUND")
        require(all(info.orig_filename == info.filename and not info.is_dir()
                    and not stat.S_ISLNK(info.external_attr >> 16) and not info.flag_bits & 1
                    and info.file_size <= 64 * 1024**2 for info in infos), "ZIP_LINK_DIRECTORY_ENCRYPTION_OR_FILE_BOUND")
        require(sum(info.file_size for info in infos) <= 512 * 1024**2, "ZIP_EXPANDED_SIZE_BOUND")
        members = {info.filename: zipped.read(info) for info in infos}
    return members, {"path": str(path), "sha256": observed_sha, "bytes": len(raw),
        "external_pin_checked": expected_sha256 is not None, "members": len(members),
        "expanded_bytes": sum(map(len, members.values()))}


def check_score(score, site, *, self_prefix):
    require(type(score) is dict and type(score.get("single_option")) is bool
        and type(score.get("allowed_count")) is int and score["allowed_count"] >= 1
        and score["single_option"] == (score["allowed_count"] == 1), "SCORE_OPTION_COUNT_INVALID")
    context = site["generated_site"] if self_prefix else site["reference_site"]
    target = site["expected_token_id"] if self_prefix else context["chosen_token_id"]
    require(score["target_token_id"] == target and score["allowed_count"] == len(context["allowed_ids"])
            and target in context["allowed_ids"], "SCORE_TARGET_OR_ALLOWED_SET_MISMATCH")
    for kind in KINDS:
        item = score[kind]
        require(type(item["correct"]) is bool and type(item["top1_token_id"]) is int
            and item["top1_token_id"] >= 0 and item["correct"] == (item["top1_token_id"] == target)
            and type(item["nll"]) in (int, float) and math.isfinite(item["nll"]) and item["nll"] >= -1e-9,
            "SCORE_VALUE_INVALID")
    require(score["grammar_masked"]["top1_token_id"] in context["allowed_ids"], "MASKED_CHOICE_NOT_ALLOWED")
    if self_prefix:
        require(score["grammar_masked"]["correct"] == site["correct"], "GENERATED_CHOICE_SCORE_MISMATCH")


def validate_row(row, filename):
    checkpoint, cohort, index = row["checkpoint"], row["cohort"], row["cohort_index"]
    require(checkpoint in CHECKPOINTS and row["checkpoint_sha256"] == CHECKPOINTS[checkpoint]
        and cohort in COHORT_TASKS and type(index) is int and 0 <= index < COHORT_TASKS[cohort]
        and type(row["depth"]) is int and row["depth"] in (1, 2, 3), "ROW_IDENTITY_INVALID")
    require(filename == f"{checkpoint}_{cohort}_{index:03d}.json", "ROW_FILENAME_IDENTITY_MISMATCH")
    require(type(row["task_id"]) is str and row["task_id"] and type(row["matches_saved_development_action"]) is bool,
            "ROW_TASK_OR_SAVED_MATCH_INVALID")
    seen = set()
    for site in row["decision_rows"]:
        ref = site["reference_site"]
        require(ref["role"] in ROLES and ref["key"] not in seen, "REFERENCE_SITE_ROLE_OR_DUPLICATE")
        seen.add(ref["key"])
        require(site["correspondence"] in ("MATCHED", "CONTEXT_CHANGED", "SITE_MISSING", "AMBIGUOUS_MAPPING"),
                "UNRECOGNIZED_CORRESPONDENCE")
        check_score(site["correct_prefix"], site, self_prefix=False)
        comparable = (site["correspondence"] == "MATCHED" and site["expected_choice"] == "LEGAL"
                      and site["generated_site"]["observed"])
        require((site["self_generated_prefix"] is not None) == comparable, "SELF_PREFIX_SCORING_BOUNDARY_CHANGED")
        if comparable:
            check_score(site["self_generated_prefix"], site, self_prefix=True)
    return checkpoint, cohort, index


def scores(sites, condition, singleton=None):
    scored = [site for site in sites if site[condition] is not None
              and (singleton is None or site[condition]["single_option"] is singleton)]
    return {"scored": len(scored),
        "prefix_relation": dict(Counter("identical" if s["preceding_tokens_differ"] is False else
            "different" if s["preceding_tokens_differ"] is True else "unpaired" for s in scored)),
        **{kind: {"correct": sum(site[condition][kind]["correct"] for site in scored),
                  "attempted": len(scored), "mean_nll": None if not scored else
                  math.fsum(site[condition][kind]["nll"] for site in scored) / len(scored)} for kind in KINDS}}


def aggregate(rows):
    grouped = defaultdict(list)
    task_grouped = defaultdict(list)
    first_errors = []
    for row in rows:
        task_grouped[(row["checkpoint"], row["cohort"], row["depth"])].append(row)
        for site in row["decision_rows"]:
            grouped[(row["checkpoint"], row["cohort"], row["depth"], site["reference_site"]["role"])].append(site)
        wrong = sorted([site for site in row["decision_rows"] if site["correct"] is False],
                       key=lambda s: s["generated_site"]["token_index"])
        if wrong:
            site = wrong[0]
            first_errors.append({"checkpoint": row["checkpoint"], "cohort": row["cohort"], "depth": row["depth"],
                "task_id": row["task_id"], "role": site["reference_site"]["role"],
                "generated_token_index": site["generated_site"]["token_index"],
                "expected_token_id": site["expected_token_id"], "chosen_token_id": site["generated_site"]["chosen_token_id"],
                "preceding_tokens_differ": site["preceding_tokens_differ"],
                "not_proven_first_error_in_entire_trajectory": True})
    groups, tasks = [], []
    for checkpoint in CHECKPOINTS:
        for cohort in COHORT_TASKS:
            for depth in (1, 2, 3):
                selected = task_grouped[(checkpoint, cohort, depth)]
                tasks.append({"checkpoint": checkpoint, "cohort": cohort, "depth": depth,
                    "completed_task_rows": len(selected), "scheduled_tasks": COHORT_TASKS[cohort] // 3,
                    "termination": dict(Counter(row["generation_termination"] for row in selected)),
                    "saved_development_matches": sum(row["matches_saved_development_action"] for row in selected),
                    "saved_development_mismatches": [row["task_id"] for row in selected if not row["matches_saved_development_action"]],
                    "extra_generated_sites": sum(len(row["extra_generated_sites"]) for row in selected)})
                for role, expected in zip(ROLES, EXPECTED[cohort][depth], strict=True):
                    sites = grouped[(checkpoint, cohort, depth, role)]
                    forced = (COHORT_TASKS[cohort] // 3) * (1 if depth == 1 else 4) if role == "run_input" else 0
                    groups.append({"checkpoint": checkpoint, "cohort": cohort, "depth": depth, "role": role,
                        "reference_sites_present": len(sites), "reference_sites_scheduled": expected,
                        "reference_single_option_scheduled": forced, "reference_multiple_options_scheduled": expected - forced,
                        "correspondence": dict(Counter(site["correspondence"] for site in sites)),
                        "expected_choice": dict(Counter(site["expected_choice"] for site in sites)),
                        "matched_without_emitted_choice": sum(site["correspondence"] == "MATCHED"
                            and not site["generated_site"]["observed"] for site in sites),
                        **{condition: {"all": scores(sites, condition),
                            "single_option": scores(sites, condition, True),
                            "multiple_options": scores(sites, condition, False)} for condition in CONDITIONS}})
    return groups, tasks, first_errors


def analyze(archive, *, expected_archive_sha256=None):
    members, identity = read_packet(archive, expected_archive_sha256)
    report = {"schema": SCHEMA, "archive": identity, "boundary": BOUNDARY,
        "status": "NO_DIAGNOSTIC_RECEIPT", "scheduled_task_rows": 480, "scheduled_reference_opportunities": 9088,
        "task_rows_analyzed": 0, "diagnostic_hashes_all_verified": False, "groups": [], "task_groups": [],
        "earliest_comparable_wrong_decisions": [], "limitations": [
            "Depth is reference-task depth, not achieved generated nesting.",
            "Validation tasks were already used for historical checkpoint selection.",
            "Accuracy denominators contain scored sites; coverage denominators retain scheduled reference opportunities.",
            "Different lexical prefixes can preserve comparable meaning; changed contexts have no assigned correctness.",
            "Earliest comparable wrong decisions need not be the first structural or semantic error in the entire stream.",
            "Correct-prefix prefix_relation labels describe the paired generated stream, not a non-gold assisted prefix.",
            "Raw and grammar-masked likelihoods are separate; forced choices are not evidence of child-call skill."]}
    collection = decode(members["artifact_collection_receipt.json"]) if "artifact_collection_receipt.json" in members else None
    report["artifact_collection"] = collection
    if "diagnostic/diagnostic_receipt.json" not in members:
        return report
    receipt = decode(members["diagnostic/diagnostic_receipt.json"])
    require(receipt["schema"] == "cas-meta2-assisted-prefix-diagnostic/8" and receipt["source_sha"] == WORKER_SHA
        and receipt["bundle_manifest_sha256"] == BUNDLE_SHA and receipt["neural_training"] is False
        and receipt["native_execution"] is False and type(receipt["completed"]) is bool,
        "DIAGNOSTIC_RECEIPT_IDENTITY_OR_SCOPE")
    mapping = receipt["files_sha256"]
    require(type(mapping) is dict and len(mapping) <= 480, "DIAGNOSTIC_FILE_INDEX_BOUND")
    missing = []
    # Verify every declared byte digest before JSON-decoding any task row.
    for name, expected in mapping.items():
        require(safe_member(name) == name and "/" not in name
            and re.fullmatch(r"(?:cas|generic)_(?:initial|selected)_(?:train_probe|validation)_[0-9]{3}\.json", name)
            and type(expected) is str and re.fullmatch("[0-9a-f]{64}", expected), "DIAGNOSTIC_FILE_INDEX_INVALID")
        key = "diagnostic/" + name
        if key not in members:
            missing.append(key)
        else:
            require(digest(members[key]) == expected, "DIAGNOSTIC_ROW_HASH_MISMATCH:" + key)
    available = {name.removeprefix("diagnostic/") for name in members
                 if name.startswith("diagnostic/") and name != "diagnostic/diagnostic_receipt.json"}
    require(available <= set(mapping), "UNINDEXED_DIAGNOSTIC_FILE")
    report.update(diagnostic_receipt=receipt, diagnostic_receipt_sha256=digest(members["diagnostic/diagnostic_receipt.json"]),
                  missing_indexed_files=missing)
    if missing:
        report["status"] = "INCOMPLETE_PACKET_DIAGNOSTIC_INDEX_NOT_FULLY_VERIFIABLE"
        return report
    report["diagnostic_hashes_all_verified"] = True
    rows, seen = [], set()
    for name in sorted(mapping):
        row = decode(members["diagnostic/" + name])
        key = validate_row(row, name)
        require(key not in seen, "DUPLICATE_TASK_ROW")
        seen.add(key); rows.append(row)
    require(len(rows) == receipt["task_rows_completed"], "COMPLETED_ROW_COUNT_MISMATCH")
    groups, tasks, first = aggregate(rows)
    opportunities = sum(len(row["decision_rows"]) for row in rows)
    if receipt["completed"]:
        require(len(rows) == 480 and opportunities == 9088 and len(mapping) == 480,
                "SUCCESS_DENOMINATORS_INCOMPLETE")
        require(all(group["reference_sites_present"] == group["reference_sites_scheduled"]
                    and group["correct_prefix"]["single_option"]["scored"] == group["reference_single_option_scheduled"]
                    for group in groups), "SUCCESS_DEPTH_ROLE_DENOMINATORS_CHANGED")
    total_matches = sum(row["matches_saved_development_action"] for row in rows)
    require(total_matches == receipt["saved_development_action_matches"], "SAVED_MATCH_SUM_MISMATCH")
    report.update(status="COMPLETE_DIAGNOSTIC_JSON_ANALYZED" if receipt["completed"] else "PARTIAL_DIAGNOSTIC_JSON_ANALYZED",
        task_rows_analyzed=len(rows), reference_opportunities_present=opportunities, groups=groups, task_groups=tasks,
        earliest_comparable_wrong_decisions=first, saved_development_action_matches=total_matches,
        saved_development_action_mismatches=len(rows) - total_matches,
        correspondence=dict(Counter(site["correspondence"] for row in rows for site in row["decision_rows"])),
        termination=dict(Counter(row["generation_termination"] for row in rows)),
        integrity_crosscheck="All indexed task-row bytes verified before parsing; counts recomputed from task rows.")
    return report


def fraction(score):
    return f"{score['correct']}/{score['attempted']}" if score["attempted"] else "N/A (0)"


def markdown(report):
    lines = ["# Saved-prefix diagnostic: offline JSON report", "", report["status"], "", BOUNDARY, "",
        f"Archive SHA-256: `{report['archive']['sha256']}`", "",
        f"Task rows analyzed: {report['task_rows_analyzed']}/480. All diagnostic row hashes verified: {report['diagnostic_hashes_all_verified']}.", ""]
    if not report["groups"]:
        lines += ["No diagnostic decision scores are reported from this incomplete or missing index.", ""]
        return "\n".join(lines)
    lines += [f"Saved-development action agreement: {report['saved_development_action_matches']}/{report['task_rows_analyzed']}; "
              f"mismatches: {report['saved_development_action_mismatches']}.", "",
        "Scores below are correct/scored. Own-prefix coverage is scored/scheduled references. "
        "N/A means no scored opportunity, not zero accuracy. Depth is reference-task depth.", "",
        "## Child selection and CALL-input binding: multiple options only", "",
        "| Checkpoint | Partition | Depth | Role | Assisted raw | Assisted masked | Own raw | Own masked | Own coverage |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|"]
    def score_line(group):
        assisted = group["correct_prefix"]["multiple_options"]
        own = group["self_generated_prefix"]["multiple_options"]
        return "| " + " | ".join([group["checkpoint"], group["cohort"], str(group["depth"]), group["role"],
            fraction(assisted["raw_full_vocabulary"]), fraction(assisted["grammar_masked"]),
            fraction(own["raw_full_vocabulary"]), fraction(own["grammar_masked"]),
            f"{own['scored']}/{group['reference_multiple_options_scheduled']}"]) + " |"
    for group in report["groups"]:
        if group["role"] in ("call_target", "call_input") and group["reference_sites_scheduled"]:
            lines.append(score_line(group))
    lines += ["", "## Completion, reproduction and missing opportunities", "",
        "| Checkpoint | Partition | Depth | Rows | Saved matches | Mismatches | Termination | Extra sites |",
        "|---|---|---:|---:|---:|---:|---|---:|"]
    for group in report["task_groups"]:
        lines.append(f"| {group['checkpoint']} | {group['cohort']} | {group['depth']} | "
            f"{group['completed_task_rows']}/{group['scheduled_tasks']} | {group['saved_development_matches']} | "
            f"{len(group['saved_development_mismatches'])} | {json.dumps(group['termination'], sort_keys=True)} | {group['extra_generated_sites']} |")
    lines += ["", "Correspondence totals: " + json.dumps(report["correspondence"], sort_keys=True) + ".", "",
        "The JSON lists mismatching task IDs, correspondence/legality counts for every group, and each earliest comparable wrong decision. "
        "That decision is not automatically the first error in the full trajectory.", "",
        "<details><summary>All roles: multiple-option scores</summary>", "",
        "| Checkpoint | Partition | Depth | Role | Assisted raw | Assisted masked | Own raw | Own masked | Own coverage |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|"]
    lines += [score_line(group) for group in report["groups"] if group["reference_sites_scheduled"]]
    lines += ["", "</details>", "", "<details><summary>Grammar-forced choices, reported separately</summary>", "",
        "| Checkpoint | Partition | Depth | Scheduled | Assisted raw | Assisted masked | Own raw | Own masked | Own coverage |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for group in report["groups"]:
        if not group["reference_single_option_scheduled"]:
            continue
        assisted, own = (group[condition]["single_option"] for condition in CONDITIONS)
        lines.append("| " + " | ".join([group["checkpoint"], group["cohort"], str(group["depth"]),
            str(group["reference_single_option_scheduled"]), fraction(assisted["raw_full_vocabulary"]),
            fraction(assisted["grammar_masked"]), fraction(own["raw_full_vocabulary"]),
            fraction(own["grammar_masked"]), f"{own['scored']}/{group['reference_single_option_scheduled']}"]) + " |")
    lines += ["", "</details>", "", "Mean negative log-likelihood, all-score totals and complete subgroup counts are retained in analysis.json.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--archive-sha256")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = no_links(args.output)
    require(not output.exists() and output.resolve().is_relative_to((ROOT / "records").resolve())
            and output.resolve() != (ROOT / "records").resolve(), "NEW_IN_SCOPE_OUTPUT_REQUIRED")
    report = analyze(args.archive, expected_archive_sha256=args.archive_sha256)
    report["analysis_script_sha256"] = digest(Path(__file__).read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in (("analysis.json", canonical(report)), ("report.md", markdown(report).encode("utf-8"))):
        with (output / name).open("xb") as stream:
            stream.write(raw)
    print(json.dumps({"status": report["status"], "output": str(output), "archive_sha256": report["archive"]["sha256"],
        "task_rows_analyzed": report["task_rows_analyzed"], "diagnostic_hashes_all_verified": report["diagnostic_hashes_all_verified"]}, sort_keys=True))


if __name__ == "__main__":
    main()
