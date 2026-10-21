# CONT3_FIX_DIFF — the LM-T4c run-code fix against the LM-T4b package, with the unit test run both ways

Written before any part ran. The LM-T4c package = a fresh extract of LM-T4b's sealed zip
(`LM_T4B_20261020_SOURCE.zip`, sha256 `f93ceba8601ccc579331d1a2c930ac44a857eeba87c3ff6591ac14e8e729efe2`, 28 members)
plus exactly the two edits below (applied by `tools/apply_cont3_fix.py`: exact string replacement, each old text found
exactly once; no regex; checked for stray backspace bytes), plus the LM-T4c record files (`PREREGISTRATION_LMT4C.md`,
`FROZEN_LMT4C.json`, `CONT3_DIAGNOSIS.md`, this file) and a regenerated `SOURCE_MANIFEST.json` (new extract paths and the
two new hashes; every other row unchanged). The reader `merge_t4b.py` is byte-identical
(`382033ca52735f9b3a6dfedfd1316a716bc01360e8c794d8681328470a0d0db5`). No threshold, seed, arm, part, mark or gate changed.

| File | LM-T4 / LM-T4b sha256 | LM-T4c sha256 | Change |
|---|---|---|---|
| `lm_t4/stations.py` | `64a2051bc17c200c570d7ea1f5428842a774ccb311d08cf7f9c4e0dc1c8fb8db` | `f9109b9d916a893c2a0e487c65828138430e24d622c6ad02290db35e7537622d` | 1 code line changed (split over 2 lines), 2 comment lines reworded to 3; +2 lines net |
| `lm_t4/test_lm_t4.py` | `c3590dd0427dd0efb78d9121c4abba11a20a87c59abe39e1121951ba47532056` | `b4eae8e710d4c3ee36841bdacf194d72367fd9ac105500e4a9ef2f66d91f3af8` | +9 lines: one new test `test_twin_provenance_keys_task_b` (13 tests per part instead of 12) |
| `lm_t4/merge_t4b.py` (reader) | `382033ca52735f9b3a6dfedfd1316a716bc01360e8c794d8681328470a0d0db5` | same | none |
| every other run-code file | as LM-T4b `PACKAGE_FREEZE.json` | same | none |

## Diff 1: `lm_t4/stations.py` (`TaskBThinker.s5`)

```diff
--- lm_t4b/lm_t4/stations.py
+++ lm_t4c/lm_t4/stations.py
@@ -515,9 +515,11 @@
                 asked_now.append([k, i])
         cas5["questions_asked"] = asked_now
         if asked_now:
-            # key: the world teaches every support slot in the end (c26: 10 of 10 filled), so the pointer is expected
-            # to be answered = CREATED; the label is finalized at the end of the draw (Q7)
-            rec = record(tid, "S5", None, cas5, cce5, gaps5, "ATTEMPTED", self.ds, key="CREATED",
+            # key: the world teaches the TAUGHT brain every support slot in the end (c26: 10 of 10 filled), so its pointer
+            # is expected to be answered = CREATED; the untaught twin is never taught, so its questions stay open =
+            # ATTEMPTED (CONT-3 run-code fix, LM-T4c); the label is finalized at the end of the draw (Q7)
+            rec = record(tid, "S5", None, cas5, cce5, gaps5, "ATTEMPTED", self.ds,
+                         key="CREATED" if self.tag == "taught" else "ATTEMPTED",
                          note="asking wrote open question pointers")
             rec["pointer"] = {"question": len(self.questions) - 1, "questions": list(range(len(self.questions) - len(asked_now), len(self.questions)))}
             rec["said_extra"] = [self.questions[-len(asked_now) + j]["content"] for j in range(len(asked_now))]
```

## Diff 2: `lm_t4/test_lm_t4.py` (one new test)

```diff
--- lm_t4b/lm_t4/test_lm_t4.py
+++ lm_t4c/lm_t4/test_lm_t4.py
@@ -161,6 +161,15 @@
         self.assertEqual(d["provenance"]["key_mismatch"], 0, d["provenance"])
         self.assertTrue(any(x["reply"] and x["reply"]["kind"] == "ANSWER" for x in d["released_answers"]))
 
+    def test_twin_provenance_keys_task_b(self):
+        # CONT-3 (LM-T4c): the untaught twin asks but is never taught, so its asking crossings end ATTEMPTED and
+        # their key must say so; the taught brain's keys must still match (its questions are answered = CREATED)
+        d = taskb("A1")
+        self.assertEqual(d["provenance"]["key_mismatch"], 0, d["provenance"])
+        self.assertEqual(d["provenance_twin"]["key_mismatch"], 0, d["provenance_twin"])
+        self.assertGreater(d["provenance_twin"]["ATTEMPTED"], 0, d["provenance_twin"])
+        self.assertEqual(d["provenance_twin"]["CREATED"], 0, d["provenance_twin"])
+
 
 QUICK = tuple(n for n in dir(TestLMT4) if n.startswith("test_"))
```

The test runs on the fixture draw (RB2c `FIXTURE_NOT_SEALED_WORLDS` draw 0, never a scored world), like every other test
in the file. It is not vacuous: it also requires the twin to have asked (`ATTEMPTED > 0`).

## The test run both ways (`tools/run_one_test.py`, `C:\Python314\python.exe -X utf8 -B -I`)

Old code = `old_code_test/` (LM-T4b's `stations.py`, byte-identical, with only the new test added; `TEST_OLD_CODE_OUTPUT.txt`):

```
test_twin_provenance_keys_task_b (lm_t4.test_lm_t4.TestLMT4.test_twin_provenance_keys_task_b) ... FAIL
AssertionError: 4 != 0 : {'FOLLOWED': 220, 'CREATED': 0, 'ATTEMPTED': 4, 'key_mismatch': 4, 'crossings': 224}
Ran 1 test in 7.782s
FAILED (failures=1)
fixture draw 0, arm A1: taught provenance {"FOLLOWED": 4672, "CREATED": 4, "ATTEMPTED": 0, "key_mismatch": 0, "crossings": 4676}
fixture draw 0, arm A1: twin provenance   {"FOLLOWED": 220, "CREATED": 0, "ATTEMPTED": 4, "key_mismatch": 4, "crossings": 224}
RESULT FAIL tests run 1 failures 1 errors 0
```

Fixed code = `package/` (`TEST_FIXED_CODE_OUTPUT.txt`):

```
test_twin_provenance_keys_task_b (lm_t4.test_lm_t4.TestLMT4.test_twin_provenance_keys_task_b) ... ok
Ran 1 test in 7.737s
OK
fixture draw 0, arm A1: taught provenance {"FOLLOWED": 4672, "CREATED": 4, "ATTEMPTED": 0, "key_mismatch": 0, "crossings": 4676}
fixture draw 0, arm A1: twin provenance   {"FOLLOWED": 220, "CREATED": 0, "ATTEMPTED": 4, "key_mismatch": 0, "crossings": 224}
RESULT PASS tests run 1 failures 0 errors 0
```

The labels are identical both ways (taught CREATED 4; twin ATTEMPTED 4); only the twin's `key_mismatch` moves 4 -> 0.
