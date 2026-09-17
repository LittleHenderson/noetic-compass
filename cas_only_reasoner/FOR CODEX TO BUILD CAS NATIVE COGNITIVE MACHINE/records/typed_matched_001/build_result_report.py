"""Build the human-readable result from completed, independently audited records."""
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "records/typed_matched_001"
def read(path): return json.loads(path.read_bytes())
def frac(row): return Fraction(row["numerator"], row["denominator"])
def pct(value): return f"{100 * float(value):.4f}%"
audit = read(BASE / "independent_complete_audit_001.json")
provider = read(BASE / "completion_provider_observation_001.json")
assert audit["status"] == provider["status"] == "PASS"
arms = audit["arms"]
conditions = ["ALT_COMPONENT_WHOLE", "MIXED_SAME_ITEMS"]
means = {}
analyses = {}
for a in arms:
    suffix = "a" if a["condition"] == conditions[0] else "m"
    analyses[(a["model_seed"], a["condition"])] = read(BASE / f"receipt_{a['model_seed']}_{suffix}/matched_analysis.json")
for condition in conditions:
    selected = [a for a in arms if a["condition"] == condition]
    means[condition] = {
        "speed_auc": sum((frac(a["speed_auc"]) for a in selected), Fraction()) / 3,
        "transfer": sum((frac(a["transfer"]) for a in selected), Fraction()) / 3,
        "development_before": sum((frac(a["family_balanced_curve"]["0"]) for a in selected), Fraction()) / 3,
        "raw_final": sum(a["raw_development_final_correct"] for a in selected),
        "exposed_before": sum(a["exposed_before"] for a in selected),
        "exposed_after": sum(a["exposed_after"] for a in selected),
    }
alt, mixed = (means[c] for c in conditions)
assert alt["speed_auc"] - mixed["speed_auc"] == frac(audit["mean_speed_auc_difference"])
assert alt["transfer"] - mixed["transfer"] == frac(audit["mean_transfer_difference"])
assert alt["raw_final"] == 4 and mixed["raw_final"] == 1
assert alt["development_before"] == mixed["development_before"]
bykind = {}
for condition in conditions:
    totals = {}
    for seed in (20260917, 20260918, 20260919):
        for kind, row in analyses[(seed, condition)]["exposed"]["by_kind"].items():
            value = totals.setdefault(kind, {"before": 0, "after": 0, "total": 0})
            for name in ("before", "after"): value[name] += row[name]["correct"]
            value["total"] += row["after"]["total"]
    bykind[condition] = totals

lines = [
"# Completed matched teaching comparison",
"",
"All six GPU runs completed and passed the independent evidence audit. Component-first teaching scored higher than the mixed control in two of three matched pairs and tied in one. The differences are small and absolute performance on unfamiliar graphs is poor. Both methods finished below their shared pre-teaching development score. A useful, durable learning advantage has not been established.",
"",
"## What was compared",
"",
"Three model seeds each ran both teaching methods. ALT_COMPONENT_WHOLE teaches components before whole tasks; MIXED_SAME_ITEMS mixes the same lessons within batches. The learner, encoder, information, corrections, initial model/optimizer/random state and measured work match within every pair. Only the grouping/order of 256 supplementary presentations changes; the other 896 presentations remain fixed.",
"",
"This is one controlled teaching-order comparison. It does not compare CAS architecture with all usual teaching methods. The ordinary dependency-graph schedule is identical to the component-first schedule, so it is not counted as a distinct third method.",
"",
"## Main results",
"",
"| Prespecified development measure | Component-first | Mixed control | Component-first minus control |",
"| --- | ---: | ---: | ---: |",
f"| Mean learning-curve score | {pct(alt['speed_auc'])} | {pct(mixed['speed_auc'])} | +{100*float(alt['speed_auc']-mixed['speed_auc']):.4f} percentage points |",
f"| Mean final transfer score | {pct(alt['transfer'])} | {pct(mixed['transfer'])} | +{100*float(alt['transfer']-mixed['transfer']):.4f} percentage points |",
"| Eligible retention comparisons | 0 of 3 pairs | 0 of 3 pairs | Unassessed |",
"",
f"Both methods started at {pct(alt['development_before'])} on the family-balanced development measure. The final transfer scores are below that starting point. The observed relative advantage therefore does not establish improved unfamiliar-problem performance over the initial learner.",
"",
"Raw final answers were **4/177 for component-first versus 1/177 for the control**, down from **21/177 in each method before teaching**. This is the same 59-question panel repeated with three model initializations, not 177 different problems. The panel contains six development topologies (8–10 nodes) after training on 3–4-node worlds. Development answers supplied no training corrections; the protected final panel was not opened for this study.",
"",
"The primary score gives equal weight to six topology families and, within each, equal weight to the parts question and the mean reach score. One correct parts answer can therefore move the balanced score more than one correct reach answer. The raw counts above remain essential context.",
"",
"The learning-curve score is the normalized trapezoid across updates 0, 40, 80, 120 and 160: (A0 + 2*A40 + 2*A80 + 2*A120 + A160) / 8. A higher value is better accuracy along this fixed training schedule. It is not a measured percentage speedup or proof that a threshold was reached in fewer steps.",
"",
"## Every run",
"",
"| Model seed | Method | Exposed course before → after /564 | Development correct at updates 0 / 40 / 80 / 120 / 160 (each /59) | Curve score | Final transfer score | Retention before → after /96 |",
"| --- | --- | --- | --- | ---: | ---: | --- |",
]
for a in arms:
    analysis = analyses[(a["model_seed"], a["condition"])]
    label = "Component-first" if a["condition"] == conditions[0] else "Mixed control"
    curve = " / ".join(str(analysis["development_curve"][str(u)]["raw"]["correct"]) for u in (0,40,80,120,160))
    lines.append(f"| {a['model_seed']} | {label} | {a['exposed_before']} → {a['exposed_after']} | {curve} | {pct(frac(a['speed_auc']))} | {pct(frac(a['transfer']))} | {a['retention_before']} → {a['retention_after']} |")
lines += [
"",
"All six runs improved fit to exposed course questions. Totals after teaching are 589/1692 versus 584/1692: five additional correct answers for component-first across the same 564 questions repeated in three runs. These exposed results do not establish transfer.",
"",
"Retention used 96 probes without worked-answer supports, before and after 16 updates teaching definition/context questions. The frozen competence threshold is at least 48/96 before that interval in both arms of a pair. Only the seed-20260918 control reached it; no component-first arm did. All six raw probe scores declined. Retention remains unassessed under the preset rule; this is not evidence that the methods retain equally well. Public facts remain visible, and this is an intervening-teaching test, not a long elapsed-time test.",
"",
"## Saved-output diagnosis and next action",
"",
"The following is descriptive diagnosis after the completed comparison, not an added primary endpoint. Each denominator combines three runs of the same exposed question bank.",
"",
"| Exposed question kind | Component-first before → after | Mixed control before → after |",
"| --- | ---: | ---: |",
]
for kind in sorted(bykind[conditions[0]]):
    a, m = (bykind[c][kind] for c in conditions)
    lines.append(f"| {kind} | {a['before']} → {a['after']} / {a['total']} | {m['before']} → {m['after']} / {m['total']} |")
assert all(bykind[c][kind]["after"] == 0 for c in conditions for kind in ("context", "definition", "edge_account"))
lines += [
"",
"Context, definition and edge-account answers remain at zero after main teaching in both methods across all three seeds. The next research step is to inspect the saved predictions for these failures, the unfamiliar-graph collapse and the losses during intervening teaching, then freeze a targeted correction and a fresh matched test. Causal explanations are still hypotheses. More seeds alone would not repair the low competence. Keep the protected final panel untouched while developing the fix.",
"",
"## Execution and verification",
"",
"- All six runs used worker source e6bdf30524c0cea3da05e8c39899ca6fc059553d and the same pinned source archive.",
"- Each run executed 160 main teaching updates, 16 intervening-teaching updates and two separately counted verification replays: 178 actual updates, 1,296 training presentations, 71,922 core forward calls and 2,951 predictions.",
"- Across the study: 1,068 actual updates, 7,776 presentations, 431,532 core forward calls and 17,706 predictions. Counted work matches between arms; elapsed time need not match exactly.",
"- Independent file checks passed 3,504 collected files, 2,364 worker artifacts, 2,382 required delivery objects, 18 checkpoint reconstructions and 12 exact last-update replays.",
"- All three paired initializations match in model, optimizer, encoder and random state. The three model seeds produce distinct initial model identities.",
"- These final audits read saved JSON and bytes with the Python standard library. No local model execution or checkpoint tensor decoding was used.",
"",
f"Cleanup observation: {provider['observed_utc']}. All six lifecycle receipts confirm instance termination, role removal and security-group cleanup. A fresh scoped EC2 query returned the final two instances as terminated and did not return the four older IDs; absence alone is not treated as proof of termination. Private evidence buckets are retained.",
"",
f"Budget: six $7 reservations, $42 total for this study, no automatic retries. The campaign ledger is revision {provider['budget']['revision']}, with $501 reserved and $4,499 unreserved of the $5,000 authorized cap. Reservations are bounds, not invoices.",
"",
"## Evidence",
"",
"- [Frozen paired result](admission_001/paired_result.json)",
"- [Independent complete audit](independent_complete_audit_001.json)",
"- [Provider and budget observation](completion_provider_observation_001.json)",
"- [Frozen study admission](admission_001/study.json)",
"- [Independent work plan](independent_work_plan_001.json)",
"- [Supervisor log](supervisor_001.log)",
"",
"| Record | SHA-256 |",
"| --- | --- |",
]
for rel in ("admission_001/study.json", "admission_001/paired_result.json", "independent_complete_audit_001.json", "completion_provider_observation_001.json"):
    lines.append(f"| {rel} | {sha256((BASE/rel).read_bytes()).hexdigest()} |")
lines += [
"",
"Source archive SHA-256: 2feff28c52fbbe5a230d4f1f32c936c9d9434bc514d5cf92d998fc917cbc72fc.",
"",
"The earlier negative three-seed recurrence result remains unchanged. The full CNCM vision remains active and incomplete. These three development pairs, conditional on one encoder and one course, do not establish general CAS superiority, recursive learning from the viewer, a final-set result, or completion of the machine.",
"",
]
with (BASE / "MATCHED_STUDY_RESULT.md").open("x", encoding="utf-8", newline="\n") as stream:
    stream.write("\n".join(lines))
summary = {
    "schema": "cncm.typed-matched-human-report-summary/0.1",
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "mean_scores": {c: {k: float(v) if isinstance(v, Fraction) else v for k,v in row.items()} for c,row in means.items()},
    "exposed_by_kind": bykind,
    "report_sha256": sha256((BASE/"MATCHED_STUDY_RESULT.md").read_bytes()).hexdigest(),
}
with (BASE/"human_report_summary_001.json").open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(summary, stream, indent=2, sort_keys=True); stream.write("\n")
print(json.dumps({k:v for k,v in summary.items() if k!="exposed_by_kind"}))

