# READER FIX DIFF — wave 7 CHAT WAVE v3 -> v4 (A-R1W7-4)

Unified diff of every non-`helm_now/` file that differs between the v3 extract (zip `5063baba…`) and the v4 tree, before the v4 seal. `helm_now/` is byte-identical (`HELM_NOW_IDENTITY_V4.json`). New file: `kit/stage_check_w7.py`. The HG5 repair itself is the hunks in `r1w7/chat_harness.py` (the recorder unit hashes `helm_now/` before and after and writes `helm_now_files_changed` through the shared builder `recorder_doc`) and `r1w7/merge_r1w7.py` (HG5 names `units_missing_helm_now_files_changed` and refuses any missing list).

```diff
--- ../extract_v3/HELM_R1_W7_20261020/r1w7/merge_r1w7.py	2026-10-20 21:14:42.658773900 -0700
+++ r1w7/merge_r1w7.py	2026-10-20 21:20:19.334782700 -0700
@@ -26,7 +26,7 @@
 from r1w7 import score_w7 as SC        # noqa: E402
 from r1w7 import seed_rule_w7 as SR    # noqa: E402
 
-READER = "r1w7.merge_r1w7 v1 (2026-10-20)"
+READER = "r1w7.merge_r1w7 v2 (2026-10-20, A-R1W7-4: HG5 names the units missing helm_now_files_changed)"
 
 
 # ============================================================================================ unit summaries
@@ -256,10 +256,15 @@
     changed = {u: ((R.sm.get(u) or {}).get("unit") or {}).get("helm_now_files_changed") for u, *_x in C.unit_list()}
     sess = {u: ((R.sm.get(u) or {}).get("unit") or {}).get("session_files_under_scratch") for u, *_x in chat}
     canon = (inst.get("helm_cut") or {}).get("canonical_equals_base") is True and C.check_helm_cut()["canonical_equals_base"]
+    # A-R1W7-4: every one of the 14 units (the recorder unit too) must write the list; a unit that does not write it is
+    # named here and the gate reads false (belt: the recorder unit now writes it; braces: a missing list is still a failure).
+    missing = sorted(u for u, v in changed.items() if not isinstance(v, list))
     g["HG5_sandbox"] = {"holds": bool(sb.get("start")) and sb.get("start") == sb.get("end") and canon and
-                        all(v == [] for v in changed.values()) and all(v is True for v in sess.values()),
+                        not missing and all(v == [] for v in changed.values()) and all(v is True for v in sess.values()),
                         "wave1_tree_same": bool(sb.get("start")) and sb.get("start") == sb.get("end"),
                         "canonical_brain_equals_base": canon,
+                        "units_missing_helm_now_files_changed": missing,
+                        "units_with_the_list": len(changed) - len(missing), "units_planned": len(changed),
                         "helm_now_files_changed": {u: v for u, v in changed.items() if v},
                         "session_files_under_scratch": sess}
     crashed = {u: (R.sm.get(u) or {}).get("crashed") for u, *_x in C.unit_list()}
--- ../extract_v3/HELM_R1_W7_20261020/r1w7/chat_harness.py	2026-10-20 21:14:42.656762300 -0700
+++ r1w7/chat_harness.py	2026-10-20 21:20:19.308368300 -0700
@@ -349,14 +349,27 @@
              "cubes_written": list(t.cubes_written), "operation": t.operation} for t in mem.turns]
 
 
+def recorder_doc(rows: List[dict], all_equal: bool, helm_now_files_changed: List[str], *, wide_modules_imported,
+                 helm_outside, wide_env, seconds) -> Dict[str, Any]:
+    """The recorder unit's record. ONE builder for the real unit and for the test fixture (A-R1W7-4), so the fixture can
+    carry `helm_now_files_changed` only because the real code writes it. HG5 reads the field from every unit."""
+    return {"schema": "helm.r1w7.recorder-equality/1", "exam": "RECORDER", "arm": "EQUALITY", "rows": rows,
+            "items": len(rows), "all_equal": all_equal, "crashed": 0, "system_exit": 0,
+            "helm_now_files_changed": list(helm_now_files_changed),
+            "wide_modules_imported": wide_modules_imported, "helm_outside": helm_outside,
+            "wide_env": wide_env, "seconds": seconds}
+
+
 def run_recorder_equality(ns, items: List[dict], mode: str = "everyday") -> Dict[str, Any]:
     """On practice dialogues: (a) a wrapped session and an UNWRAPPED session give the same chat memory record, turn for
     turn; (b) two wrapped sessions give byte-identical recorded loop results once the tool receipts' wall-clock fields
     (receipt_id, elapsed_ms, timestamp_utc) are stripped (D-W7-17; the raw comparison and its differing paths are
     reported); (c) every stored copy equals the dict the chat received (the recorder returned the original). Raw
-    booleans; the reader reads I12 from them."""
+    booleans; the reader reads I12 from them. A-R1W7-4: helm_now/ is hashed before and after, exactly as the chat and
+    loop units do, and the changed-file list is written (HG5 demands it from every unit)."""
     HC = ns.m.HC
     t0 = time.time()
+    before = C.tree_listing(ns.helm_now)
     rows = []
     for k, it in enumerate(items):
         lines = [s["text"] for s in (it.get("setup") or []) if s.get("kind") != "new_session"] + list(it["turns"])
@@ -392,7 +405,8 @@
                      if not same_memory else None})
     ok = bool(rows) and all(r["wrapped_equals_unwrapped_memory"] and r["two_wrapped_runs_byte_identical"]
                             and r["stored_copies_equal_returned"] for r in rows)
-    return {"schema": "helm.r1w7.recorder-equality/1", "exam": "RECORDER", "arm": "EQUALITY", "rows": rows,
-            "items": len(rows), "all_equal": ok, "crashed": 0, "system_exit": 0,
-            "wide_modules_imported": C.wide_imported(), "helm_outside": C.helm_modules_outside(ns),
-            "wide_env": os.environ.get(C.WIDE_ENV), "seconds": round(time.time() - t0, 3)}
+    after = C.tree_listing(ns.helm_now)
+    changed = sorted(set(k for k in set(before) | set(after) if before.get(k) != after.get(k)))
+    return recorder_doc(rows, ok, changed, wide_modules_imported=C.wide_imported(),
+                        helm_outside=C.helm_modules_outside(ns), wide_env=os.environ.get(C.WIDE_ENV),
+                        seconds=round(time.time() - t0, 3))
--- ../extract_v3/HELM_R1_W7_20261020/tests_r1w7/fixture_run.py	2026-10-20 21:14:42.662770600 -0700
+++ tests_r1w7/fixture_run.py	2026-10-20 21:20:19.394329800 -0700
@@ -11,6 +11,7 @@
 from pathlib import Path
 from typing import Any, Dict, List, Optional
 
+from r1w7 import chat_harness as H
 from r1w7 import common_w7 as C
 from r1w7 import custody_w7 as CU
 from r1w7 import noise_w7 as NW
@@ -255,10 +256,12 @@
     units: Dict[str, Dict[str, Any]] = {}
     for uid, exam_name, arm in C.unit_list():
         if uid == C.RECORDER_UNIT:
-            units[uid] = {"schema": "helm.r1w7.recorder-equality/1", "exam": "RECORDER", "arm": "EQUALITY", "items": 3,
-                          "all_equal": plant != "I12", "rows": [], "crashed": 0, "system_exit": 0, "items_sha256": "f" * 64,
-                          "netguard": {"installed": True, "attempts": 0}, "wide_modules_imported": WIDE, "helm_outside": [],
-                          "wide_env_after": None, "helm_now_files_changed": [], "seconds": 1.0, "synthetic_fixture": True}
+            # A-R1W7-4: the real builder writes the record (helm_now_files_changed included); the fixture adds only what
+            # units_w7.main adds after the unit ran. The fixture never names the field itself.
+            units[uid] = dict(H.recorder_doc([], plant != "I12", [], wide_modules_imported=WIDE, helm_outside=[],
+                                             wide_env=None, seconds=1.0),
+                              items=3, items_sha256="f" * 64, netguard={"installed": True, "attempts": 0},
+                              wide_env_after=None, synthetic_fixture=True)
             continue
         spec = C.arm_spec(arm)
         if exam_name == "X7_REAL":
@@ -325,6 +328,10 @@
         units["W7_X7_NOISE_CHAT_OFF"]["netguard"] = {"installed": True, "attempts": 1}
     elif plant == "HG5b":
         units["W7_X7_CONV_CHAT_DIAG"]["helm_now_files_changed"] = ["math_utils.py"]
+    elif plant == "HG5c":                                   # A-R1W7-4: the recorder unit does not write the list (c51)
+        del units[C.RECORDER_UNIT]["helm_now_files_changed"]
+    elif plant == "HG5d":                                   # A-R1W7-4: the recorder unit changed a file under helm_now/
+        units[C.RECORDER_UNIT]["helm_now_files_changed"] = ["helm_chat.py"]
     elif plant == "HG6":
         units["W7_X7_CONV_LOOP_ON"]["crashed"] = 1
     elif plant == "HG7":
--- ../extract_v3/HELM_R1_W7_20261020/tests_r1w7/test_units_w7.py	2026-10-20 21:14:42.664770000 -0700
+++ tests_r1w7/test_units_w7.py	2026-10-20 21:23:52.686271600 -0700
@@ -42,7 +42,7 @@
     def test_frozen_file_agrees_with_code(self):
         f = json.loads((PKG / "FROZEN_R1W7.json").read_text(encoding="utf-8"))
         self.assertEqual(f["owner_line"], C.OWNER_LINE)
-        self.assertEqual(f["owner_line_utf8_bytes"], 18)
+        self.assertEqual(f["owner_line_utf8_bytes"], 20)
         self.assertEqual(f["cap_usd"], "1.00")
         self.assertEqual(f["seed_rule"]["bands"], {k: list(v) for k, v in C.BANDS.items()})
         self.assertEqual(f["seed_rule"]["hex_slices"], {k: list(v) for k, v in C.HEX_SLICES.items()})
@@ -71,11 +71,13 @@
 
     def test_bands_above_everything_used_and_below_int32(self):
         for lo, hi in C.BANDS.values():
-            self.assertGreater(lo, 1_989_000_000 + C.SEED_GAP)
+            self.assertGreater(lo, 1_999_000_000 + C.SEED_GAP)       # A-R1W7-4: above v3's bands and the 1,996-1,999 M reservation
             self.assertLess(hi, C.INT32_MAX)
             self.assertEqual(hi - lo + 1, C.SLOTS)
-        self.assertEqual(C.USED_RANGES[0][2], 1_989_000_000)
-        self.assertEqual(C.OWNER_LINE, "CHAT WAVE at 1 USD")
+        self.assertEqual(C.USED_RANGES[0][2], 1_999_000_000)
+        self.assertEqual(C.BANDS, {"REAL": (2_000_000_001, 2_001_000_000), "CONV": (2_002_000_001, 2_003_000_000),
+                                   "NOISE": (2_004_000_001, 2_005_000_000)})
+        self.assertEqual(C.OWNER_LINE, "CHAT WAVE 2 at 1 USD")
 
     def test_helm_cut_contract(self):
         hc = C.check_helm_cut()
@@ -88,7 +90,8 @@
         d = json.loads((PKG / "contract" / "EXCLUDE_R1W7_PRIOR_USED.json").read_text(encoding="utf-8"))
         want = {"xreal_used": 128, "c46_used": 128, "c47_used": 128, "x6_real": 128, "x6_conv": 64, "x6_pairw": 64,
                 "x6v3_real": 128, "x6v3_conv": 64, "x6v3_pairw": 64, "rbw1t_practice_v1": 128, "rbw1t_practice_v2": 128,
-                "w6_practice_conv": 64, "w6_practice_pairw": 64, "w6_practice_real": 128}
+                "w6_practice_conv": 64, "w6_practice_pairw": 64, "w6_practice_real": 128,
+                "X7_c51_real": 128, "X7_c51_conv": 64}                       # A-R1W7-4: X7's ids (job c51)
         self.assertEqual({k: len(v) for k, v in d["lists"].items()}, want)
         for k, src in d["sources"].items():
             self.assertNotIn("exam", src["folder"].replace("<", "").split("\\"))
@@ -103,8 +106,14 @@
         ex = set(CU.real_exclusions())
         self.assertTrue(set(pp["conv_pool_ids"]) <= ex and set(pp["real_practice_ids"]) <= ex)
         self.assertTrue(set(d["lists"]["x6v3_real"]) <= ex and set(d["lists"]["c47_used"]) <= ex)
-        self.assertFalse(set(d["lists"]["x6_conv"]) <= ex)          # section 4.1 lists REAL ids only for the REAL draw
-        self.assertTrue(set(d["lists"]["x6_conv"]) <= set(CU.conv_exclusions([])))
+        # A-R1W7-4: every list applies to BOTH pools (c51's custodian flag: 3 REAL ids sat in old CONV lists)
+        for name in ("x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv"):
+            self.assertTrue(set(d["lists"][name]) <= ex, name)
+            self.assertTrue(set(d["lists"][name]) <= set(CU.conv_exclusions([])), name)
+        self.assertEqual((len(d["lists"]["X7_c51_real"]), len(d["lists"]["X7_c51_conv"])), (128, 64))
+        self.assertEqual(d["blocks"]["X7_c51"]["lists"], ["X7_c51_real", "X7_c51_conv"])
+        self.assertEqual(set(CU.REAL_EXCLUDE_LISTS), set(d["lists"]))
+        self.assertEqual(CU.CONV_EXTRA_LISTS, ())
 
     def test_recorder_fixture_is_practice(self):
         d = json.loads((PKG / "tests_r1w7" / "fixtures" / "RECORDER_PRACTICE_TURNS.json").read_text(encoding="utf-8"))
@@ -138,8 +147,8 @@
 
     def test_blocked_table(self):
         self.assertTrue(SR.blocked(1_989_000_000))
-        self.assertTrue(SR.blocked(1_990_000_000))
-        self.assertFalse(SR.blocked(1_990_000_001))
+        self.assertTrue(SR.blocked(2_000_000_000))
+        self.assertFalse(SR.blocked(2_000_000_001))
 
 
 class Noise(unittest.TestCase):
@@ -235,7 +244,8 @@
 
     def test_every_hard_gate_can_fail(self):
         for plant, gate in (("HG1", "HG1_receipts"), ("HG1b", "HG1_receipts"), ("HG2", "HG2_replay"), ("HG3", "HG3_key_blind"),
-                            ("HG4", "HG4_no_network"), ("HG5", "HG5_sandbox"), ("HG5b", "HG5_sandbox"), ("HG6", "HG6_no_crash"),
+                            ("HG4", "HG4_no_network"), ("HG5", "HG5_sandbox"), ("HG5b", "HG5_sandbox"),
+                            ("HG5c", "HG5_sandbox"), ("HG5d", "HG5_sandbox"), ("HG6", "HG6_no_crash"),
                             ("HG7", "HG7_voice_changes_no_answer"), ("HG8", "HG8_switch_hygiene"), ("HG8b", "HG8_switch_hygiene"),
                             ("HG9", "HG9_same_inputs"), ("HG10", "HG10_chat_never_exits"), ("NEVER_SENT", "HG10_chat_never_exits")):
             with self.subTest(plant=plant):
@@ -243,6 +253,34 @@
                 self.assertEqual(r["failing_gates"], [gate], (plant, r["failing_gates"]))
                 self.assertEqual(r["verdict"], "INSTRUMENT_ERROR")      # the synthetic run is never an instrument pass
 
+    def test_hg5_holds_when_all_fourteen_units_write_empty_lists(self):
+        """A-R1W7-4: the c51 defect. The clean fixture's 14 units (the recorder unit through the real builder) all carry
+        helm_now_files_changed == [], so HG5 reads TRUE; the missing-unit list is empty; the count is 14."""
+        r = M.read(FX.make_run(Path(self.tmp.name) / "clean_hg5")["merge_input"])
+        hg5 = r["hard_gates"]["HG5_sandbox"]
+        self.assertIs(hg5["holds"], True, hg5)
+        self.assertEqual(hg5["units_missing_helm_now_files_changed"], [])
+        self.assertEqual((hg5["units_with_the_list"], hg5["units_planned"]), (14, 14))
+        self.assertNotIn("HG5_sandbox", r["failing_gates"])
+        units = FX.make_run(Path(self.tmp.name) / "clean_hg5_units")["units"]
+        self.assertEqual(len(units), 14)
+        self.assertTrue(all(u["helm_now_files_changed"] == [] for u in units.values()))
+
+    def test_hg5_reads_false_when_the_recorder_unit_lacks_the_list_or_lists_a_file(self):
+        """A-R1W7-4: the two recorder-unit plants, each alone, each read HG5 false and nothing else."""
+        r = self.planted("HG5c")
+        hg5 = r["hard_gates"]["HG5_sandbox"]
+        self.assertIs(hg5["holds"], False)
+        self.assertEqual(hg5["units_missing_helm_now_files_changed"], [C.RECORDER_UNIT])
+        self.assertEqual(hg5["units_with_the_list"], 13)
+        self.assertEqual(r["failing_gates"], ["HG5_sandbox"])
+        r = self.planted("HG5d")
+        hg5 = r["hard_gates"]["HG5_sandbox"]
+        self.assertIs(hg5["holds"], False)
+        self.assertEqual(hg5["units_missing_helm_now_files_changed"], [])
+        self.assertEqual(hg5["helm_now_files_changed"], {C.RECORDER_UNIT: ["helm_chat.py"]})
+        self.assertEqual(r["failing_gates"], ["HG5_sandbox"])
+
     def test_every_mark_can_miss(self):
         for plant, mark, also in (("NH_CHAT", "NH_CHAT", ("K4_HONEST",)), ("K1", "K1_LEARNS", ()), ("K3", "K3_SAFE", ()),
                                   ("K3b", "K3_SAFE", ()), ("K4", "K4_HONEST", ()), ("P", "P_PLAIN", ()),
@@ -350,6 +388,7 @@
         out = H.run_recorder_equality(self.ns, d["items"][:2])
         self.assertTrue(out["all_equal"], out["rows"])
         self.assertEqual(out["items"], 2)
+        self.assertEqual(out["helm_now_files_changed"], [])           # A-R1W7-4: the real recorder unit writes the list
 
     def test_a_never_sent_word_is_refused_and_recorded_as_a_crash(self):
         from r1w7 import chat_harness as H
--- ../extract_v3/HELM_R1_W7_20261020/tests_r1w7/test_kit_w7.py	2026-10-20 21:14:42.664770000 -0700
+++ tests_r1w7/test_kit_w7.py	2026-10-20 21:20:19.548474200 -0700
@@ -32,7 +32,26 @@
         stage = json.loads((KIT / "STAGE_R1W7.json").read_text(encoding="utf-8"))
         out = pc.check(stage, KIT / "run_r1w7.py")
         self.assertEqual(out["verdict"], "PASS", out["problems"])
-        self.assertEqual(stage["pythonpath"], [])
+        self.assertEqual(stage["pythonpath"], ["HELM_R1_W7_20261020"])    # A-R1W7-4: what c51 attempt 2 ran (D-OP-C51-1)
+
+    def test_stage_check_refuses_an_empty_pythonpath(self):
+        """A-R1W7-4: c51 attempt 1 died on PLAN_INVALID:r1w7_host_run:pythonpath. The sealed stage must pass the
+        supervisor's own rule and the package's stage check; an empty list must be refused by both."""
+        sc = load("stage_check_w7")
+        sup = load("job_supervisor")
+        stage = json.loads((KIT / "STAGE_R1W7.json").read_text(encoding="utf-8"))
+        out = sc.check_stage(stage, KIT / "run_r1w7.py", PKG.parent)
+        self.assertEqual(out["verdict"], "PASS", out["problems"])
+        sup.validate_plan(sc.minimal_plan(stage))
+        bad = dict(stage, pythonpath=[])
+        out = sc.check_stage(bad, KIT / "run_r1w7.py", PKG.parent)
+        self.assertEqual(out["verdict"], "FAIL")
+        self.assertTrue(any("pythonpath" in p for p in out["problems"]), out["problems"])
+        with self.assertRaises(ValueError) as cm:
+            sup.validate_plan(sc.minimal_plan(bad))
+        self.assertEqual(str(cm.exception), "PLAN_INVALID:r1w7_host_run:pythonpath")
+        out = sc.check_stage(dict(stage, pythonpath=["NO_SUCH_FOLDER"]), KIT / "run_r1w7.py", PKG.parent)
+        self.assertEqual(out["verdict"], "FAIL")
 
     def test_byte_copies(self):
         self.assertEqual(C.sha256_file(KIT / "job_supervisor.py"),
--- ../extract_v3/HELM_R1_W7_20261020/r1w7/custody_w7.py	2026-10-20 21:14:42.658773900 -0700
+++ r1w7/custody_w7.py	2026-10-20 21:20:19.549472600 -0700
@@ -43,9 +43,13 @@
                "SEED_DERIVATION_X7.json")
 EXCLUDE = C.PKG / "contract" / "EXCLUDE_R1W7_PRIOR_USED.json"
 PRACTICE_POOLS = C.PKG / "practice" / "PRACTICE_POOLS_W7.json"
+# A-R1W7-4: EVERY list applies to BOTH pools (the REAL draw and the conversation pool). c51's custodian flagged 3 REAL ids
+# that also sat in X6 / X6v3 CONV lists (allowed by the v3 contract, which applied those lists to the conversation pool only).
+# From v4 on, nothing drawn or pooled in any earlier exam or practice set can be drawn again in either pool.
 REAL_EXCLUDE_LISTS = ("xreal_used", "c46_used", "c47_used", "x6_real", "x6v3_real", "rbw1t_practice_v1",
-                      "rbw1t_practice_v2", "w6_practice_conv", "w6_practice_pairw", "w6_practice_real")
-CONV_EXTRA_LISTS = ("x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw")
+                      "rbw1t_practice_v2", "w6_practice_conv", "w6_practice_pairw", "w6_practice_real",
+                      "x6_conv", "x6_pairw", "x6v3_conv", "x6v3_pairw", "X7_c51_real", "X7_c51_conv")
+CONV_EXTRA_LISTS = ()                 # nothing is conversation-pool-only any more (A-R1W7-4)
 
 
 def read_json(p) -> Any:
--- ../extract_v3/HELM_R1_W7_20261020/r1w7/common_w7.py	2026-10-20 21:14:42.657764600 -0700
+++ r1w7/common_w7.py	2026-10-20 21:20:19.677102900 -0700
@@ -28,7 +28,7 @@
 
 PKG = Path(__file__).resolve().parents[1]
 LABEL = "R1W7"
-PACKAGE_VERSION = "v3"
+PACKAGE_VERSION = "v4"
 PACKAGE_DIR = "HELM_R1_W7_20261020"
 CLAIM_CEILING_NOW = "SYNTHETIC_ONLY"
 CLAIM_CEILING_IF_EARNED = "NAMED_CORPORA_ONLY (the real recipes) + SYNTHETIC_ONLY (dialogue and small-talk sentences)"
@@ -55,7 +55,7 @@
 ENV_DIR = {k: "R1W7_" + k.upper() + "_DIR" for k in NEIGHBOURS}
 
 # ---- HELM under test ----
-HELM_CUT_COMMIT = "dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6"       # v3 (A-R1W7-3): FIX FIRST round 2, PR #416 (2 commits on 974fe36c, PR #414: wide brain ON by default)
+HELM_CUT_COMMIT = "dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6"       # v3 (A-R1W7-3), unchanged in v4 (A-R1W7-4): FIX FIRST round 2, PR #416 (2 commits on 974fe36c, PR #414: wide brain ON by default)
 HELM_THREAD_BRANCH = "claude/helm-r1w7-chat-wave-packet-20261020 (PR #416 to claude/project-thread-pmbzd6)"
 #: helm_brain_canonical.py must equal its scored base (RB-W1T's BASE_LOOP_COMMIT d4488f2a); pinned bytes (HG5)
 HELM_BRAIN_CANONICAL_BASE = {"commit": "d4488f2a4a32992f6d8f80f24ea8cefe045ac9d7",
@@ -80,20 +80,21 @@
 C50_READING_SHA256 = "d6a855f179bfba3b39b1cf75e431b169aa63b0b0fd6b788a5570bd8f444ff055"
 
 # ---- governance: the owner's line (PROPOSED; section 8 of the preregistration; not yet signed) ----
-OWNER_LINE = "CHAT WAVE at 1 USD"
-OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8); the approval record is written only after the owner signs"
+OWNER_LINE = "CHAT WAVE 2 at 1 USD"
+OWNER_LINE_STATUS = "PROPOSED (PREREGISTRATION_R1W7.md section 8 and amendment A-R1W7-4, section 16); the approval record is written only after the owner signs"
 CAP_USD = "1.00"
 ATTEMPTS = "one attempt + one plumbing retry"
 
 # ---- seeds (PREREGISTRATION_R1W7.md section 10) ----
-BANDS = {"REAL": (1_990_000_001, 1_991_000_000), "CONV": (1_992_000_001, 1_993_000_000),
-         "NOISE": (1_994_000_001, 1_995_000_000)}
+BANDS = {"REAL": (2_000_000_001, 2_001_000_000), "CONV": (2_002_000_001, 2_003_000_000),
+         "NOISE": (2_004_000_001, 2_005_000_000)}          # A-R1W7-4: above v3's 1,990-1,995 M and the continuity packet's proposed 1,996-1,999 M
 HEX_SLICES = {"REAL": (0, 16), "CONV": (16, 32), "NOISE": (32, 48)}
 SLOTS = 1_000_000
 SEED_GAP = 1_000_000
 INT32_MAX = 2 ** 31 - 1
-USED_RANGES = (("every earlier band and derivation (wave 6 v3 used up to 1,989,000,000; whole range)", 1,
-                1_989_000_000),)
+USED_RANGES = (("every earlier band, derivation and reservation (wave 6 v3 up to 1,989,000,000; wave 7 v3 / c51 bands "
+                "1,990,000,001-1,995,000,000; the continuity packet's proposed 1,996,000,001-1,999,000,000; whole range)", 1,
+                1_999_000_000),)
 CONV_POOL_PREFIX = "R1W7-CONVPOOL"
 PRACTICE_REAL_SEED_TEXT = "RBW1-DISHNAME-FIX-PRACTICE-V2-20261020-builder-published"   # RB-W1T's practice draw v2
 PRACTICE_CONVPOOL_PREFIX = "R1W6-CONVPOOL"                                            # wave 6's published pool
--- ../extract_v3/HELM_R1_W7_20261020/kit/run_r1w7.py	2026-10-20 21:14:42.654733400 -0700
+++ kit/run_r1w7.py	2026-10-20 21:20:19.677102900 -0700
@@ -43,7 +43,7 @@
 CARRIER_FILES = ('INPUTS_CONV_X7.json', 'INPUTS_NOISE_X7.json', 'INPUTS_REAL_X7.json', 'X7_PINS.json')
 FORBIDDEN_IN_CARRIER = ('KEYS_REAL_X7.json', 'KEYS_CONV_X7.json', 'SAMPLE_REAL_X7.json', 'SAMPLE_CONV_X7.json',
                         'POOLS_X7.json', 'SEED_DERIVATION_X7.json')
-HELM_CUT_COMMIT = 'dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6'   # v3 (A-R1W7-3)
+HELM_CUT_COMMIT = 'dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6'   # v3 (A-R1W7-3), unchanged in v4 (A-R1W7-4)
 HELM_BRAIN_CANONICAL_BASE_SHA256 = '24df53c9b3abeeafa2c38a0d8aa808537055ab29a7eaffd235031cbfb430980a'
 HELM_TESTS = ['test_helm_brain_wide', 'test_helm_end_to_end_loop', 'test_helm_english_in',
               'test_helm_english_in_stock_frame', 'test_helm_voice', 'test_helm_faces_in', 'test_helm_triad',
--- ../extract_v3/HELM_R1_W7_20261020/kit/STAGE_R1W7.json	2026-10-20 21:14:42.652734700 -0700
+++ kit/STAGE_R1W7.json	2026-10-20 21:20:19.713828500 -0700
@@ -27,10 +27,12 @@
  "create_output_dir": true,
  "cwd": "HELM_R1_W7_20261020",
  "env": {},
- "layout_note": "sources/<name>/ is each archive extracted: r1w7 = this zip (top folder HELM_R1_W7_20261020, holds helm_now/, the HELM code under test, cut at dfc7158d (v3)); w1 = wave-1 v3 zip 31f97d67 (HELM_R1_W1_20261015); r1w3 = wave-3 v3 zip 152bca2a (HELM_R1_W3_20261019); r1w3b = wave-3b zip a4f82556 (HELM_R1_W3B_20261019); r1w6 = wave-6 v3 zip f1b64a5e (HELM_R1_W6_20261019); rbw1t = RB-W1T v3 zip 3a8ae37e (HELM_RBW1T_20261019); x7 = the custodian's X7 carrier X7_CARRIER_V1.zip (top folder x7: the three input files + X7_PINS.json ONLY; no key file). Paths in argv are relative to cwd sources/r1w7/HELM_R1_W7_20261020. Every python process is `python -X utf8 -B -I` (isolated; no PYTHONPATH).",
+ "layout_note": "sources/<name>/ is each archive extracted: r1w7 = this zip (top folder HELM_R1_W7_20261020, holds helm_now/, the HELM code under test, cut at dfc7158d (v3, unchanged in v4)); w1 = wave-1 v3 zip 31f97d67 (HELM_R1_W1_20261015); r1w3 = wave-3 v3 zip 152bca2a (HELM_R1_W3_20261019); r1w3b = wave-3b zip a4f82556 (HELM_R1_W3B_20261019); r1w6 = wave-6 v3 zip f1b64a5e (HELM_R1_W6_20261019); rbw1t = RB-W1T v3 zip 3a8ae37e (HELM_RBW1T_20261019); x7 = the custodian's X7 carrier X7_CARRIER_V1.zip (top folder x7: the three input files + X7_PINS.json ONLY; no key file). Paths in argv are relative to cwd sources/r1w7/HELM_R1_W7_20261020. Every python process is `python -X utf8 -B -I` (isolated: -I ignores PYTHONPATH, so the supervisor's PYTHONPATH export from `pythonpath` reaches no process; the supervisor still refuses an empty `pythonpath` list, which is why c51 attempt 1 died: A-R1W7-4, D-OP-C51-1).",
  "limit": 3000,
  "name": "r1w7_host_run",
- "pythonpath": [],
+ "pythonpath": [
+  "HELM_R1_W7_20261020"
+ ],
  "required_outputs": [
   "r1w7_out/R1_W7_HOST.json",
   "r1w7_out/R1_W7_HOST.json.sha256"
--- ../extract_v3/HELM_R1_W7_20261020/RUN_LIMITS_R1W7.json	2026-10-20 21:14:42.532075900 -0700
+++ RUN_LIMITS_R1W7.json	2026-10-20 21:20:19.714632700 -0700
@@ -49,7 +49,7 @@
  },
  "ledger": "Documents/Codex/AWS_COMBINED_ALLOCATION_CURRENT.json is the operator's; NO hold placed by the builder.",
  "package": "HELM_R1_W7_20261020",
- "package_version": "v3",
+ "package_version": "v4",
  "schema": "helm.run-limits/1",
  "sources_on_host": "none of the public sources: the host gets the custodian's X7 carrier (top folder x7) and the five neighbour zips beside this zip",
  "status": "NOT APPROVED, NOT LAUNCHED: the owner has not signed 'CHAT WAVE at 1 USD'; the builder wrote no approval record and ran no custodian seal; nothing is held or launched by the builder"
```

Files not shown as a diff (regenerated or appended by program): `FROZEN_R1W7.json` (re-derived from the constants), `contract/EXCLUDE_R1W7_PRIOR_USED.json` (block `X7_c51` added by `build_v4/build/add_x7_exclusions_v4.py`), `PREREGISTRATION_R1W7.md` (section 16 appended), `README_R1W7.md`, `contract/CUSTODIAN_PROCEDURE_R1W7.md`, `kit/stage_check_w7.py` (new).
