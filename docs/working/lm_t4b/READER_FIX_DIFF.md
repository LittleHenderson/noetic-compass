# READER_FIX_DIFF: merge_t4b.py against the two LM-T4 readers

Written before any part ran. `merge_t4b.py` is built by `tools/make_reader.py` from `merge_t4.sealed.py` (the byte-exact
original LM-T4 sealed reader) by applying exactly the two reader fixes of LM-T4 amendment LMT4-A3, and nothing else.

| File | sha256 |
|---|---|
| merge_t4.sealed.py (LM-T4 original sealed reader) | `37f4a0e09fe325ec80c4e0993431a9486c26fa29649cd83c21c56eb8b064e6b2` |
| merge_t4.py (LM-T4 corrected reader, edited after the run; reference only) | `ddb3d22ad9d197f8592b9c7adf1682196297e69a6ec4dc658862a5e26d88910a` |
| merge_t4b.py (this run's reader, sealed before the run) | `382033ca52735f9b3a6dfedfd1316a716bc01360e8c794d8681328470a0d0db5` |

## Fix 1 (gates H2 and H10): a digit inside a copied outcome name is not a value
The sealed reader flagged a question as carrying a value if any character of any slot was a digit. Outcome names such
as `Ω_zz0` and `Ω_decision_11` carry digits, so 192 questions were flagged although 0 carried an amount. The fixed rule
removes every `Ω_<name>` token from the slot first and only then looks for a digit.

## Fix 2 (mark EYE-R1): the twin brain's eye events count with their rows
The sealed reader required every eye event to have a stored complete row. The untaught twin's rows are not stored, so its
280 events could never be complete. The fixed rule counts a twin event whose eta/epsilon receipt passed (the receipt
re-reads the ingredients, the theoretical yield and the limiting reagent).

## NOT applied: the per-brain breakdown of provenance mismatches
LM-T4's post-run `merge_t4.py` also added a `mismatch_by_brain` report inside mark CONT-3. That is extra reporting, not a
defect fix, so it is left out. CONT-3 is read exactly as the sealed reader read it (the run-time code's CREATED vs
ATTEMPTED key defect is in the run code, which is byte-identical in this rerun, so CONT-3 reads whatever it reads).

## Unified diff: merge_t4.sealed.py -> merge_t4b.py
```diff
--- merge_t4.sealed.py
+++ merge_t4b.py
@@ -6,4 +6,5 @@
 import hashlib
 import json
+import re
 import sys
 from decimal import Decimal
@@ -273,5 +274,6 @@
                     tot[k] += ic[k]
                 for q in it["questions"]:
-                    if q.get("carries_value") or any(ch.isdigit() for sl in q.get("slots", []) for ch in sl):
+                    # an AMOUNT is a number token outside an Ω identifier; Ω names (Ω_zz0, Ω_judgment_89) are copied, not values
+                    if q.get("carries_value") or any(re.search(r"\d", re.sub(r"Ω_[A-Za-z0-9_]+", "", sl)) for sl in q.get("slots", [])):
                         h2["question_values"] += 1
                 for i in it["inject"]:
@@ -570,5 +572,5 @@
     for r in EYE_RUNS:
         e = {"reads": 0, "reads_digest_equal": 0, "events": 0, "receipt_fail": 0, "door_calls_by_eye": 0, "gates": {}, "limiting": {},
-             "would": {}, "events_complete": 0, "would_on_clean": {"nowalk_dialogues": {}, "task_b": {}}}
+             "would": {}, "events_complete": 0, "twin_events_verified_by_receipt": 0, "would_on_clean": {"nowalk_dialogues": {}, "task_b": {}}}
         for kind, _, it in all_items((r,) if r != "A5" else (), (r,)):
             for key in (("eye", "eye_twin") if kind == "TB" else ("eye",)):
@@ -581,4 +583,7 @@
                     for k, v in s[dct].items():
                         e[dct][k] = e[dct].get(k, 0) + v
+                if key == "eye_twin":
+                    # the twin's rows are not stored; an event whose eta/epsilon receipt passed had its ingredients, Y_T and limiting re-read
+                    e["twin_events_verified_by_receipt"] += s["events"] - s["receipt_fail"]
                 if key == "eye":
                     for ev in it.get("eye_events", []):
@@ -590,6 +595,8 @@
                                 tgt[pk] = tgt.get(pk, 0) + 1
         eye[r] = e
-    marks["EYE_R1"] = {r: {"events": eye[r]["events"], "complete": eye[r]["events_complete"]} for r in EYE_RUNS}
-    marks["EYE_R1"]["pass"] = all(eye[r]["events"] > 0 and eye[r]["events"] == eye[r]["events_complete"] for r in EYE_RUNS)
+    marks["EYE_R1"] = {r: {"events": eye[r]["events"], "complete_rows": eye[r]["events_complete"],
+                           "twin_events_verified_by_receipt": eye[r]["twin_events_verified_by_receipt"]} for r in EYE_RUNS}
+    marks["EYE_R1"]["pass"] = all(eye[r]["events"] > 0 and eye[r]["events"] == eye[r]["events_complete"] + eye[r]["twin_events_verified_by_receipt"]
+                                  for r in EYE_RUNS)
     marks["EYE_R2"] = {r: frac(eye[r]["reads_digest_equal"], eye[r]["reads"]) for r in EYE_RUNS}
     marks["EYE_R2"]["pass"] = all(eye[r]["reads"] > 0 and eye[r]["reads"] == eye[r]["reads_digest_equal"] for r in EYE_RUNS)
```

## Unified diff: merge_t4.py (corrected, post-run) -> merge_t4b.py
```diff
--- merge_t4.py
+++ merge_t4b.py
@@ -543,6 +543,5 @@
     marks["CONT_2_drift"] = {"walks_caught": frac(c1["walk_hit"], c1["walks"]), "nowalk_false_fires": frac(c1["nowalk_fired"], c1["nowalks"]),
                              "pass": c1["walk_hit"] == c1["walks"] == 24 and c1["nowalk_fired"] == 0}
-    pv = {"crossings": 0, "mismatch": 0, "FOLLOWED": 0, "CREATED": 0, "ATTEMPTED": 0,
-          "mismatch_by_brain": {"task_b_taught": 0, "task_b_twin": 0, "dialogues": 0}}
+    pv = {"crossings": 0, "mismatch": 0, "FOLLOWED": 0, "CREATED": 0, "ATTEMPTED": 0}
     for kind, r, it in all_items(("A1",), ("A1",)):
         for key in (("provenance", "provenance_twin") if kind == "TB" else ("provenance",)):
@@ -550,9 +549,7 @@
             pv["crossings"] += p["crossings"]
             pv["mismatch"] += p["key_mismatch"]
-            pv["mismatch_by_brain"]["dialogues" if kind == "DL" else ("task_b_twin" if key == "provenance_twin" else "task_b_taught")] += p["key_mismatch"]
             for k in ("FOLLOWED", "CREATED", "ATTEMPTED"):
                 pv[k] += p[k]
     marks["CONT_3_provenance"] = {"agree": frac(pv["crossings"] - pv["mismatch"], pv["crossings"]), "labels": {k: pv[k] for k in ("FOLLOWED", "CREATED", "ATTEMPTED")},
-                                  "mismatch_by_brain": pv["mismatch_by_brain"],
                                   "A5_inject_CREATED": h6["a5_inject_created"], "pass": pv["crossings"] > 0 and pv["mismatch"] == 0 and h6["a5_inject_created"] == 0}
     marks["CONT_4_restlessness"] = {"S2_steps": sum(r["n"] for r in rest), "S2_mean_of_means": (sum(r["mean"] for r in rest) / len(rest)) if rest else None,
```
