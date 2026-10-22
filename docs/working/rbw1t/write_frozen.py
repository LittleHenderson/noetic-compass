"""Builder tool: write FROZEN_RBW1T.json from rbw1t/common_rbw1t.py (a unit test checks they agree)."""
import sys
from pathlib import Path
pkg = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(pkg))
from rbw1t import common_rbw1t as C
doc = {"schema": "helm.rbw1t.frozen/1", "label": C.LABEL, "package_version": C.PACKAGE_VERSION, "commit_now": C.COMMIT_NOW, "commit_base": C.COMMIT_BASE, "base_loop_commit": C.BASE_LOOP_COMMIT,
       "frames": C.FRAMES, "frame_recipes": C.FRAME_RECIPES, "count_strata": [list(x) for x in C.COUNT_STRATA],
       "forms": list(C.FORMS), "quotas": C.QUOTAS, "n_items": C.N_ITEMS, "multipliers": list(C.MULTIPLIERS),
       "surplus_factor": C.SURPLUS_FACTOR, "templates": {"teach": C.TEACH, "stock": C.STOCK, "question": C.QUESTION},
       "representable": {"max_lines": C.REPRESENTABLE_MAX_LINES, "exact_forms": list(C.SURVEY_EXACT_FORMS),
                         "top20_units": list(C.SURVEY_TOP20)},
       "marks": {"K1_learn_ratio": "9/10", "K3_safe": "0 WRONG answers and 0 WRONG lessons (WIDE)",
                 "K4_honest": "0 unexplained asks (WIDE)", "NH_OFF": "OFF_NOW == OFF_BASE byte for byte, 4 files",
                 "NH_ON_max_lost": C.NH_ON_MAX_LOST},
       "vacuity_min": C.VACUITY_MIN, "words_frozen_order": list(C.WORDS),
       "owner_line": C.OWNER_LINE, "owner_line_source": C.OWNER_LINE_SOURCE, "cap_usd": C.CAP_USD,
       "attempts": C.ATTEMPTS, "band": C.BAND, "used_ranges": [list(r) for r in C.USED_RANGES], "gap": C.SEED_GAP,
       "practice_seed_text": C.PRACTICE_SEED_TEXT, "nh_files": C.NH_FILES, "main_arms": list(C.MAIN_ARMS),
       "nh_arms": list(C.NH_ARMS), "vendor": C.VENDOR,
       "neighbours": {"w3": [C.W3_ZIP_SHA256, C.W3_FREEZE_SHA256], "w3b": [C.W3B_ZIP_SHA256, C.W3B_FREEZE_SHA256],
                      "w1": [C.W1_ZIP_SHA256, C.W1_FREEZE_SHA256]}}
print(C.write_json(pkg / "FROZEN_RBW1T.json", doc))
