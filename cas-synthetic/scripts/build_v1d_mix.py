"""Build v1d mix: aggregate all cleanup artifacts into final corpus.

Per user directive 2026-05-10 (post register-policy + k7/k8
follow-up): aggregate everything, drop genuinely-broken rows,
emit stratified 90/5/5 splits + manifest + sanity report +
review pack.

Inputs (all in cas-synthetic/data/path_d/):
  v1_mix_nlgen_{train,val,test}.jsonl        — original v1 corpus
  v1d_regen_clean_<ts>.jsonl                 — initial regen (230 rows)
  v1d_regen_recovered_<ts>_revalidated.jsonl — vocab-patch recoveries (4)
  v1d_regen_recovered_<ts>_recipe_register_recovered.jsonl — register policy (122)
  v1d_infill_long_fractal_clean_<ts1>.jsonl  — infill round 1 (44 fractal)
  v1d_infill_long_fractal_clean_<ts2>.jsonl  — infill round 2 (21 fractal)

Aggregation rules:
  1. Each row in original v1 mix:
     - If task_type != "cas_to_english" -> KEEP as-is
     - If grammar_category not in {fractal_sequence, recipe,
       meta_logic_relation} -> KEEP as-is (wasn't audited)
     - Else (audited category):
       - re-audit with the latest patched validator
       - PASS -> KEEP as-is
       - FAIL but original_id has a regen/recovered replacement
         in any of the cleanup files -> REPLACE reply_text with
         the cleanup file's reply
       - FAIL and no replacement -> DROP
  2. Append all infill rows (greenfield long-fractal additions)
  3. Stratified 90/5/5 split by:
      task_type + grammar_category + (for fractal) k-length

Outputs:
  v1d_mix_nlgen_train.jsonl
  v1d_mix_nlgen_val.jsonl
  v1d_mix_nlgen_test.jsonl
  v1d_mix_manifest_<ts>.json
  v1d_mix_sanity_<ts>.md
  v1d_mix_review_pack_<ts>.md     (30-row human spot-check pack)
"""
from __future__ import annotations

import importlib.util
import json
import random
import re
import sys
import types
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "cas-synthetic" / "scripts"
SCAFFOLD_ROOT = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"
DATA_DIR = REPO_ROOT / "cas-synthetic" / "data" / "path_d"

pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(SCAFFOLD_ROOT / "cas-native")]
sys.modules.setdefault("cas_native", pkg)
sys.path.insert(0, str(SCAFFOLD_ROOT))


def _load(name: str, fname: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / fname)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def _latest(prefix: str) -> Optional[Path]:
    candidates = sorted(DATA_DIR.glob(f"{prefix}*.jsonl"))
    return candidates[-1] if candidates else None


# ---------------------------------------------------------------------------
# Load original v1 mix + cleanup artifacts
# ---------------------------------------------------------------------------

def load_v1_mix() -> list[dict]:
    """Concatenate v1 train + val + test and tag each row with the
    original split for downstream lineage tracking."""
    rows: list[dict] = []
    for split in ("train", "val", "test"):
        path = DATA_DIR / f"v1_mix_nlgen_{split}.jsonl"
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                row["__v1_split"] = split
                rows.append(row)
    return rows


def load_replacement_map() -> dict[str, dict]:
    """Build original_id -> replacement_record map from all cleanup
    artifacts. When the same original_id appears in multiple files,
    the LATEST file wins (recovery > regen > revalidated)."""
    rep_map: dict[str, dict] = {}
    sources_in_priority_order = [
        # priority: most recent / register-recovery first, then regen
        ("recovered_via_register_policy",
         _latest("v1d_regen_recovered_20260510T185000Z_recipe_register_recovered")),
        ("recovered_via_vocab_patch",
         _latest("v1d_regen_recovered_20260510T165742Z_revalidated")),
        ("regen_initial",
         _latest("v1d_regen_clean_20260510T165742")),
    ]
    for source_label, path in sources_in_priority_order:
        if path is None:
            continue
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                orig_id = rec.get("original_id")
                if not orig_id:
                    continue
                # Don't overwrite if a higher-priority source already
                # has this id.
                if orig_id in rep_map:
                    continue
                rep_map[orig_id] = {
                    "reply_text": rec["reply_text"],
                    "source": source_label,
                    "regen_id": rec["id"],
                }
    return rep_map


def load_infill_rows() -> list[dict]:
    """Load long-fractal infill rows from both rounds."""
    paths = sorted(DATA_DIR.glob("v1d_infill_long_fractal_clean_*.jsonl"))
    paths = [p for p in paths if "_dryrun" not in p.name]
    rows: list[dict] = []
    for p in paths:
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------------------
# Re-audit helpers
# ---------------------------------------------------------------------------

def make_audit_check():
    af = _load("af_v1d_mix", "audit_fractal_targets.py")
    ar = _load("ar_v1d_mix", "audit_recipe_targets.py")
    am = _load("am_v1d_mix", "audit_meta_logic_targets.py")

    def check(row: dict) -> Optional[bool]:
        """Return True if row passes patched strict gate, False if
        fails, None if not in an audited category."""
        task = row.get("v1mix_task_type") or ""
        cat = row.get("v1mix_grammar_category_or_error_class") or ""
        if task != "cas_to_english":
            return None
        synthetic = {
            "id": row.get("id", ""),
            "cas_expression": row["cas_expression"],
            "reply_text": row.get("reply_text", ""),
            "v1mix_task_type": "cas_to_english",
        }
        if cat == "fractal_sequence":
            r = af.audit_one_record(synthetic)
            if r is None:
                return None
            return r["sequence_matches"]
        if cat == "recipe":
            r = ar.audit_one_record(synthetic)
            if r is None:
                return None
            return r["strict_match"]
        if cat == "meta_logic_relation":
            r = am.audit_one_record(synthetic)
            if r is None:
                return None
            return r["strict_match"]
        return None  # not audited
    return check


# ---------------------------------------------------------------------------
# Stratified split
# ---------------------------------------------------------------------------

_FRACTAL_K_RX = re.compile(r"(?:Φ|Phi)\s*<\s*([\d:]+)\s*>")


def _stratification_key(row: dict) -> str:
    task = row.get("v1mix_task_type") or "unknown"
    cat = row.get("v1mix_grammar_category_or_error_class") or "unknown"
    if cat == "fractal_sequence":
        m = _FRACTAL_K_RX.search(row.get("cas_expression", ""))
        if m:
            k = len([p for p in m.group(1).split(":") if p.strip()])
            # Bucket k-length into coarse bins so small buckets don't
            # over-fragment the split.
            if k <= 3:
                kbucket = "k_2_3"
            elif k <= 5:
                kbucket = "k_4_5"
            else:
                kbucket = "k_6_plus"
            return f"{task}|{cat}|{kbucket}"
    return f"{task}|{cat}"


def stratified_90_5_5_split(
    rows: list[dict], *, seed: int = 42,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (train, val, test) at 90/5/5 stratified by stratification_key.
    Each stratum gets at least 1 in val and 1 in test if it has >=20 rows."""
    rng = random.Random(seed)
    by_key: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_key[_stratification_key(row)].append(row)
    train: list[dict] = []
    val: list[dict] = []
    test: list[dict] = []
    for key in sorted(by_key.keys()):
        bucket = by_key[key][:]
        rng.shuffle(bucket)
        n = len(bucket)
        n_val = max(1, int(round(n * 0.05))) if n >= 20 else (1 if n >= 4 else 0)
        n_test = max(1, int(round(n * 0.05))) if n >= 20 else (1 if n >= 4 else 0)
        n_train = n - n_val - n_test
        train.extend(bucket[:n_train])
        val.extend(bucket[n_train:n_train + n_val])
        test.extend(bucket[n_train + n_val:n_train + n_val + n_test])
    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


# ---------------------------------------------------------------------------
# Main aggregation
# ---------------------------------------------------------------------------

def main() -> int:
    print("=== Building v1d mix ===")
    print()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # 1. Load inputs
    v1_rows = load_v1_mix()
    print(f"Loaded v1 mix: {len(v1_rows)} rows total "
          f"({sum(1 for r in v1_rows if r['__v1_split']=='train')} train + "
          f"{sum(1 for r in v1_rows if r['__v1_split']=='val')} val + "
          f"{sum(1 for r in v1_rows if r['__v1_split']=='test')} test)")
    rep_map = load_replacement_map()
    print(f"Loaded replacement map: {len(rep_map)} replacements available")
    infill_rows = load_infill_rows()
    print(f"Loaded infill rows: {len(infill_rows)} long-fractal additions")
    print()

    # 2. Apply rules: keep / replace / drop
    check = make_audit_check()
    kept: list[dict] = []
    replaced: list[dict] = []
    dropped: list[dict] = []
    not_audited_kept: list[dict] = []
    audited_pass_kept: list[dict] = []
    for row in v1_rows:
        verdict = check(row)
        if verdict is None:
            # Not in audited category — keep as-is
            kept.append(row)
            not_audited_kept.append(row)
            continue
        if verdict is True:
            kept.append(row)
            audited_pass_kept.append(row)
            continue
        # verdict is False: row failed re-audit
        rid = row.get("id", "")
        if rid in rep_map:
            new_row = dict(row)
            new_row["reply_text"] = rep_map[rid]["reply_text"]
            new_row["__v1d_replaced"] = True
            new_row["__v1d_replacement_source"] = rep_map[rid]["source"]
            new_row["__v1d_replacement_id"] = rep_map[rid]["regen_id"]
            replaced.append(new_row)
            kept.append(new_row)
        else:
            dropped.append(row)

    # 3. Append infill (greenfield additions)
    infill_normalized: list[dict] = []
    for row in infill_rows:
        normalized = {
            "id": row["id"],
            "cas_expression": row["cas_expression"],
            "reply_text": row["reply_text"],
            "v1mix_task_type": row.get("v1mix_task_type", "cas_to_english"),
            "v1mix_grammar_category_or_error_class": row.get(
                "v1mix_grammar_category_or_error_class", "fractal_sequence"
            ),
            "register": row.get("register", "T"),
            "__v1_split": "infill_new",
            "__v1d_infill": True,
            "__v1d_infill_k": row.get("v1d_infill_k"),
        }
        infill_normalized.append(normalized)
    final_rows = kept + infill_normalized
    print(f"Aggregation:")
    print(f"  v1 rows total:                {len(v1_rows)}")
    print(f"  not-audited kept as-is:       {len(not_audited_kept)}")
    print(f"  audited pass kept as-is:      {len(audited_pass_kept)}")
    print(f"  audited fail replaced:        {len(replaced)}")
    print(f"  audited fail dropped:         {len(dropped)}")
    print(f"  infill (greenfield):          {len(infill_normalized)}")
    print(f"  v1d total rows:               {len(final_rows)}")
    print()

    # 4. Stratified split
    train, val, test = stratified_90_5_5_split(final_rows)
    print(f"Stratified 90/5/5 split:")
    print(f"  train: {len(train)} ({100*len(train)/len(final_rows):.1f}%)")
    print(f"  val:   {len(val)} ({100*len(val)/len(final_rows):.1f}%)")
    print(f"  test:  {len(test)} ({100*len(test)/len(final_rows):.1f}%)")
    print()

    # 5. Write splits
    out_paths = {
        "train": DATA_DIR / "v1d_mix_nlgen_train.jsonl",
        "val":   DATA_DIR / "v1d_mix_nlgen_val.jsonl",
        "test":  DATA_DIR / "v1d_mix_nlgen_test.jsonl",
    }
    for split, rows in zip(("train", "val", "test"), (train, val, test)):
        with out_paths[split].open("w", encoding="utf-8") as fh:
            for row in rows:
                clean = {k: v for k, v in row.items() if not k.startswith("__")}
                fh.write(json.dumps(clean, ensure_ascii=False) + "\n")

    # 6. Write manifest
    manifest = {
        "timestamp": timestamp,
        "v1_mix_input_rows": {
            "train": sum(1 for r in v1_rows if r["__v1_split"]=="train"),
            "val": sum(1 for r in v1_rows if r["__v1_split"]=="val"),
            "test": sum(1 for r in v1_rows if r["__v1_split"]=="test"),
            "total": len(v1_rows),
        },
        "cleanup_artifacts_consumed": {
            "regen_clean_files": [str(p.name) for p in
                sorted(DATA_DIR.glob("v1d_regen_clean_*.jsonl"))
                if "dryrun" not in p.name],
            "recovered_files": [str(p.name) for p in
                sorted(DATA_DIR.glob("v1d_regen_recovered_*.jsonl"))],
            "infill_files": [str(p.name) for p in
                sorted(DATA_DIR.glob("v1d_infill_long_fractal_clean_*.jsonl"))
                if "dryrun" not in p.name],
        },
        "aggregation_counts": {
            "v1_rows_total": len(v1_rows),
            "not_audited_kept": len(not_audited_kept),
            "audited_pass_kept": len(audited_pass_kept),
            "audited_fail_replaced": len(replaced),
            "audited_fail_dropped": len(dropped),
            "infill_added": len(infill_normalized),
            "v1d_total": len(final_rows),
        },
        "split_sizes": {
            "train": len(train), "val": len(val), "test": len(test),
        },
        "stratification_key": "v1mix_task_type | grammar_category | fractal_k_bucket",
        "split_seed": 42,
        "split_ratio": "90/5/5 (deterministic, stratified)",
        "replacement_sources_used": Counter(
            r.get("__v1d_replacement_source") for r in replaced
        ),
    }
    manifest_path = DATA_DIR / f"v1d_mix_manifest_{timestamp}.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8",
    )
    print(f"Wrote manifest: {manifest_path}")

    # 7. Sanity report
    sanity_lines = ["# v1d mix sanity report", "", f"Timestamp: {timestamp}", ""]
    by_cat_train = Counter(r.get("v1mix_grammar_category_or_error_class","unk") for r in train)
    by_cat_val = Counter(r.get("v1mix_grammar_category_or_error_class","unk") for r in val)
    by_cat_test = Counter(r.get("v1mix_grammar_category_or_error_class","unk") for r in test)
    by_task_train = Counter(r.get("v1mix_task_type","unk") for r in train)
    by_task_val = Counter(r.get("v1mix_task_type","unk") for r in val)
    by_task_test = Counter(r.get("v1mix_task_type","unk") for r in test)
    sanity_lines.append("## Split sizes")
    sanity_lines.append(f"- train: {len(train)}")
    sanity_lines.append(f"- val: {len(val)}")
    sanity_lines.append(f"- test: {len(test)}")
    sanity_lines.append("")
    sanity_lines.append("## By task_type (train / val / test)")
    sanity_lines.append("| task | train | val | test |")
    sanity_lines.append("|---|---:|---:|---:|")
    all_tasks = set(by_task_train) | set(by_task_val) | set(by_task_test)
    for t in sorted(all_tasks):
        sanity_lines.append(f"| {t} | {by_task_train[t]} | {by_task_val[t]} | {by_task_test[t]} |")
    sanity_lines.append("")
    sanity_lines.append("## By grammar category (train / val / test)")
    sanity_lines.append("| category | train | val | test |")
    sanity_lines.append("|---|---:|---:|---:|")
    all_cats = set(by_cat_train) | set(by_cat_val) | set(by_cat_test)
    for c in sorted(all_cats):
        sanity_lines.append(f"| {c} | {by_cat_train[c]} | {by_cat_val[c]} | {by_cat_test[c]} |")
    sanity_lines.append("")
    # ID uniqueness check
    all_ids = [r.get("id","") for r in final_rows]
    dup_ids = [i for i,c in Counter(all_ids).items() if c > 1]
    sanity_lines.append("## ID uniqueness")
    sanity_lines.append(f"- total rows: {len(final_rows)}")
    sanity_lines.append(f"- unique IDs: {len(set(all_ids))}")
    sanity_lines.append(f"- duplicate IDs: {len(dup_ids)} {'(WARNING)' if dup_ids else 'OK'}")
    sanity_lines.append("")
    # Empty fields check
    empty_cas = sum(1 for r in final_rows if not r.get("cas_expression","").strip())
    empty_reply = sum(1 for r in final_rows if not r.get("reply_text","").strip())
    sanity_lines.append("## Empty-field check")
    sanity_lines.append(f"- empty cas_expression: {empty_cas} {'(WARNING)' if empty_cas else 'OK'}")
    sanity_lines.append(f"- empty reply_text: {empty_reply} {'(WARNING)' if empty_reply else 'OK'}")
    sanity_path = DATA_DIR / f"v1d_mix_sanity_{timestamp}.md"
    sanity_path.write_text("\n".join(sanity_lines), encoding="utf-8")
    print(f"Wrote sanity report: {sanity_path}")

    # 8. Review pack: 30 sample rows from regen/recovered/infill subset
    rng = random.Random(99)
    review_pool: list[dict] = []
    review_pool += [r for r in replaced if r.get("__v1d_replacement_source") == "regen_initial"][:10]
    review_pool += [r for r in replaced if r.get("__v1d_replacement_source") == "recovered_via_register_policy"][:10]
    review_pool += infill_normalized[:10]
    review_lines = ["# v1d mix human review pack", "", f"Timestamp: {timestamp}", ""]
    review_lines.append(
        "Spot-check sample from regen / recovered / infill subset. "
        "Manual scan: do the reply_text values render the source CAS faithfully?"
    )
    review_lines.append("")
    for i, row in enumerate(review_pool, 1):
        src = row.get("__v1d_replacement_source") or ("infill" if row.get("__v1d_infill") else "?")
        review_lines.append(f"## Row {i} — source: {src}")
        review_lines.append("")
        review_lines.append(f"- id: `{row.get('id')}`")
        review_lines.append(f"- task: {row.get('v1mix_task_type')}, category: {row.get('v1mix_grammar_category_or_error_class')}")
        review_lines.append(f"- cas_expression: `{row.get('cas_expression', '')[:200]}`")
        review_lines.append(f"- reply_text: {row.get('reply_text','')[:400]}")
        review_lines.append("")
    review_path = DATA_DIR / f"v1d_mix_review_pack_{timestamp}.md"
    review_path.write_text("\n".join(review_lines), encoding="utf-8")
    print(f"Wrote review pack: {review_path}")
    print()
    print("=== v1d mix build complete ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
