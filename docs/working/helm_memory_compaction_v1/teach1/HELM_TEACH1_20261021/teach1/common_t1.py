"""Shared constants and helpers for TEACH-1 (standard library only).

TEACH-1 teaches HELM a made-up subject through its live chat (`helm_chat.HELMConversationalSession.handle_turn`), squeezes
its working memory to a turn budget of 12 so that it must compact, and reads how much it recalls under seven arms
(PREREGISTRATION_MEMORY_COMPACTION_V1.precode.md section 3). Every number here is frozen; FROZEN_TEACH1.json repeats them
and a test checks they agree. HELM's code is this package's own `helm_now/` cut (contract/HELM_CUT_TEACH1.json), cut by
`git show` at the pinned commit; the wave-1 brain package is a neighbour shipped beside (checked by its freeze).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

PKG = Path(__file__).resolve().parents[1]
LABEL = "TEACH1"
PACKAGE_VERSION = "v1"
PACKAGE_DIR = "HELM_TEACH1_20261021"
PRECODE_SHA256 = "7eef0edc7d342bb0438e4052db646528442badefa92d6bdf31e8485914073bf1"
WORDS = ("INCONCLUSIVE", "COMPACTION_HARMED", "COMPACTION_NO_GAIN", "COMPACTION_EARNED_KEEP")
LABELS_PRINTED = ("SYNTHETIC_ONLY", "LLM_WRITTEN_ONLY", "RULE_CAPSULES_V1", "EYE_REPORT_ONLY")

# ---- the arms (pre-code section 3): one switch set each; HELM files are the same bytes ----
ARMS = ("COMPACT_ON", "VERBATIM_ONLY", "FIFO_DROP", "SUMMARY_TEXT", "NO_REFRESH", "RANDOM_REFRESH", "REPLAY")
COMPACTING_ARMS = ("COMPACT_ON", "SUMMARY_TEXT", "NO_REFRESH", "RANDOM_REFRESH", "REPLAY")
CAS_ARMS = ("COMPACT_ON", "NO_REFRESH", "RANDOM_REFRESH", "REPLAY")
TURN_BUDGET_B = 12
VERBATIM_BUDGET = 10_000
ARM_SWITCH = {   # the chat's own switch HELM_MEMORY_COMPACT, and the turn budget (helm_memory max_turns)
    "COMPACT_ON": {"HELM_MEMORY_COMPACT": "1", "budget": TURN_BUDGET_B},
    "VERBATIM_ONLY": {"HELM_MEMORY_COMPACT": "1", "budget": VERBATIM_BUDGET},   # nothing leaves the budget: nothing compacted
    "FIFO_DROP": {"HELM_MEMORY_COMPACT": "0", "budget": TURN_BUDGET_B},         # today's helm_memory: the oldest turn dropped
    "SUMMARY_TEXT": {"HELM_MEMORY_COMPACT": "1", "budget": TURN_BUDGET_B},      # the text-note writer (arms_t1.TextNoteCompactor)
    "NO_REFRESH": {"HELM_MEMORY_COMPACT": "1", "budget": TURN_BUDGET_B},        # never asks (arms_t1.NoRefreshCompactor)
    "RANDOM_REFRESH": {"HELM_MEMORY_COMPACT": "1", "budget": TURN_BUDGET_B},    # asks about a random item (arms_t1.RandomRefreshCompactor)
    "REPLAY": {"HELM_MEMORY_COMPACT": "1", "budget": TURN_BUDGET_B},            # COMPACT_ON again, fresh process, same seeds
}

# ---- the exam (pre-code section 4) ----
WORLDS = 16
FACTS_PER_WORLD = 24
UNKNOWN_PER_WORLD = 4
TEACHING_TURNS = 32
FLOOR_KEYED_TURNS = 20
FLOOR_SMALL_TURNS = 4
FLOOR_FIX_TURNS = 2
QUIZ_QUESTIONS = 16
QUIZ_TAUGHT = 12
QUIZ_UNKNOWN = 2
QUIZ_NEVER = 2
QUIZZES = ("Q_TAUGHT", "Q_SQUEEZED", "Q_REFRESHED")
PERSON_RIGHT_SHARE = 0.75            # the scripted person answers right with this probability, else "I don't remember"
PLANTED_DAMAGE_PER_WORLD = 2         # OPEN_QUESTIONS Q10 (b), adopted by amendment A-TEACH1-1: 1 copy deleted, 1 corrupted
FLOOR_COMPACTIONS_PER_WORLD = 8      # I14: fewer than this in a budgeted arm = the squeeze did not bite
FLOOR_REFRESH_WORLDS = 8             # I14: COMPACT_ON asked at least one refresh question in at least this many worlds
MAX_TURN_WORDS = 60
SPLIT_NGRAM = 8

# ---- marks (pre-code section 8) ----
U1_MIN_RIGHT_T_AVG = 10
R1_MIN_OVER_FIFO = 8
R2_MIN_OVER_SUMMARY = 4
R3_MIN_OVER_RANDOM = 4
R4_MAX_LOST_VS_VERBATIM = 2            # A-TEACH1-2: counted on the undamaged quiz items only
R4_HARM_LOST_VS_VERBATIM = 4
R4_SCORED_ON = "UNDAMAGED_ITEMS_ONLY"  # the owner's ruling 2026-10-21 (A-TEACH1-2)
R5_MIN_OVER_NO_REFRESH = 2
F1_CONFIRMED_SHARE = 0.6
S1_RECIPE_SPEAK_PER_48 = 2
S2_PLAIN_LOSS_PER_QUIZ = 2
S3_UNKNOWN_MARKER_SLACK = 1
S4_SAID_BACK_SHARE = 0.9

# ---- seeds (pre-code section 12 as moved by A-TEACH1-1: wave 7 v7 / v8 / v9 took 2,024-2,041 M first) ----
BANDS = {"WORLD": (2_042_000_001, 2_043_000_000), "QUIZ": (2_044_000_001, 2_045_000_000),
         "PERSON": (2_046_000_001, 2_047_000_000), "RANDOM_REFRESH": (2_048_000_001, 2_049_000_000)}
HEX_SLICES = {"WORLD": (0, 16), "QUIZ": (16, 32), "PERSON": (32, 48), "RANDOM_REFRESH": (48, 64)}
SLOTS = 1_000_000
SEED_GAP = 1_000_000
INT32_MAX = 2 ** 31 - 1
USED_RANGES = (("every earlier band and derivation (wave 7 v9 used up to 2,041,000,000; whole range)", 1, 2_041_000_000),)
OWNER_LINES = {"COMPACT EXAM at 0 USD": {"cap_usd": 0.0, "host": "laptop"},
               "COMPACT EXAM at 1 USD": {"cap_usd": 1.0, "host": "one m6i.xlarge-class CPU host"}}
PRACTICE_SEED_TEXTS = {"WORLD": "teach1-practice-world", "QUIZ": "teach1-practice-quiz",
                       "PERSON": "teach1-practice-person", "RANDOM_REFRESH": "teach1-practice-random"}

# ---- HELM under test ----
HELM_TESTS_UNITTEST = ("test_helm_brain_wide", "test_helm_end_to_end_loop", "test_helm_english_in",
                       "test_helm_english_in_stock_frame", "test_helm_voice", "test_helm_faces_in", "test_helm_triad",
                       "test_helm_wide_alongside", "test_helm_cas_address", "test_helm_units_note", "test_helm_pin_hygiene",
                       "test_helm_reader_gap")
HELM_TESTS_PYTEST = ("test_helm_memory.py", "test_helm_memory_compact.py", "test_helm_chat_nuance.py")
WAVE1_BRAIN = {"zip": "HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip", "dir": "HELM_R1_W1_20261015_v3",
               "freeze_sha256": "8c55c4136e1b24bc322779160ffed666f9eb9ee21512c1972101263a243c039b"}
BRAIN_DIR_ENV = "HELM_CANONICAL_BRAIN_DIR"

# ---- the frozen clock of every unit (D-TEACH1-5): receipts hash over turn timestamps, so replay needs a fixed clock ----
FROZEN_CLOCK_UTC = (2026, 10, 21, 0, 0, 0, 2, 294, 0)
FROZEN_CLOCK_START = 1_792_972_800.0   # 2026-10-21T00:00:00Z as a float; time.time() counts up by TICK per call
FROZEN_CLOCK_TICK = 0.001


class PinRefused(RuntimeError):
    pass


# ============================================================================================ hashing and JSON
def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("ascii")


def sha256_obj(obj: Any) -> str:
    return sha256_bytes(canonical(obj))


def json_bytes(obj, *, indent=1) -> bytes:
    return (json.dumps(obj, sort_keys=True, indent=indent, default=str, ensure_ascii=True) + "\n").encode("ascii")


def write_json(path, obj, *, indent=1) -> str:
    """Sorted, LF JSON via .partial + fsync + rename (the CRLF trap and the half-written-file trap); returns its sha256."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json_bytes(obj, indent=indent)
    partial = path.with_name(path.name + ".partial")
    with open(partial, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)
    return sha256_bytes(data)


def read_json(path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_doc(path, want_sha256: str) -> Any:
    got = sha256_file(path)
    if got != want_sha256:
        raise PinRefused(f"{Path(path).name} sha256 {got} != pin {want_sha256}")
    return read_json(path)


def tree_listing(root) -> Dict[str, str]:
    root = Path(root)
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            out[p.relative_to(root).as_posix()] = sha256_file(p)
    return out


def package_seal(pkg, expected_freeze_sha256) -> Dict[str, Any]:
    path = Path(pkg) / "PACKAGE_FREEZE.json"
    out: Dict[str, Any] = {"expected": expected_freeze_sha256, "present": path.is_file(), "sha256_ok": False,
                           "members_ok": False, "bad_members": [], "members": 0}
    if not path.is_file() or not isinstance(expected_freeze_sha256, str):
        return out
    raw = path.read_bytes()
    out["sha256"] = sha256_bytes(raw)
    out["sha256_ok"] = out["sha256"] == expected_freeze_sha256
    members = json.loads(raw).get("members") or {}
    bad = [rel for rel, pin in sorted(members.items())
           if not (Path(pkg) / rel).is_file() or sha256_file(Path(pkg) / rel) != (pin or {}).get("sha256")]
    out["members"] = len(members)
    out["members_ok"] = bool(members) and not bad
    out["bad_members"] = bad[:20]
    return out


# ============================================================================================ words
NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
                "seventeen": 17, "eighteen": 18, "nineteen": 19}
MONTHS = ("january", "february", "march", "april", "june", "july", "august", "september", "october", "november",
          "december")   # "may" is three letters: never a clue word, so never a value


def norm(text: str) -> str:
    """The house normalisation of pre-code 4.3: case, whitespace, and the voice's number forms (words -> digits)."""
    t = (text or "").lower()
    t = re.sub(r"[^a-z0-9'\s-]", " ", t)
    return " ".join(str(NUMBER_WORDS[w]) if w in NUMBER_WORDS else w for w in t.split())


def words_of(text: str) -> List[str]:
    return re.findall(r"[a-z][a-z'\-]*", (text or "").lower())


def ngrams(text: str, n: int = SPLIT_NGRAM) -> List[str]:
    w = words_of(text)
    return [" ".join(w[i:i + n]) for i in range(0, max(0, len(w) - n + 1))]


# ============================================================================================ HELM from helm_now/
def helm_now_dir() -> Path:
    return PKG / "helm_now"


def helm_cut() -> Dict[str, Any]:
    return read_json(PKG / "contract" / "HELM_CUT_TEACH1.json")


def check_helm_cut() -> Dict[str, Any]:
    """helm_now/ equals the recorded cut: every file's sha256 (I1, I3)."""
    cut = helm_cut()
    hn = helm_now_dir()
    bad = [rel for rel, pin in sorted(cut["files"].items())
           if not (hn / rel).is_file() or sha256_file(hn / rel) != pin["sha256"]]
    on_disk = set(tree_listing(hn)) - {"SOURCE_CUT.json"}
    extra = sorted(on_disk - set(cut["files"]))
    pins_ok = all((hn / rel).is_file() and sha256_file(hn / rel) == sha for rel, sha in cut["pinned"].items())
    source_cut_equal = (hn / "SOURCE_CUT.json").is_file() and \
        (hn / "SOURCE_CUT.json").read_bytes() == (PKG / "contract" / "HELM_CUT_TEACH1.json").read_bytes()
    return {"commit": cut.get("commit"), "files": len(cut["files"]), "bad": bad[:20], "extra": extra[:20],
            "pinned_ok": pins_ok, "source_cut_equals_contract": source_cut_equal,
            "ok": not bad and not extra and pins_ok and source_cut_equal}


def import_helm_now(check: bool = True):
    """Put helm_now/ first on sys.path and import the chat from there (and nothing of HELM from anywhere else)."""
    hn = helm_now_dir()
    if check:
        hc = check_helm_cut()
        if not hc["ok"]:
            raise PinRefused(f"helm_now/ does not equal the recorded cut: {hc}")
    for name in list(sys.modules):
        if name.startswith("helm_") or name in ("tks_meta_valve_controller",):
            raise PinRefused(f"a HELM module was imported before helm_now/: {name}")
    sys.path.insert(0, str(hn))
    import helm_chat  # noqa: F401
    import helm_memory  # noqa: F401
    import helm_memory_compact  # noqa: F401
    import helm_voice  # noqa: F401
    for m in (helm_chat, helm_memory, helm_memory_compact, helm_voice):
        if not Path(m.__file__).resolve().is_relative_to(hn.resolve()):
            raise PinRefused(f"{m.__name__} came from {m.__file__}, not helm_now/")
    return {"helm_chat": helm_chat, "helm_memory": helm_memory, "helm_memory_compact": helm_memory_compact,
            "helm_voice": helm_voice}


def frozen() -> Dict[str, Any]:
    return read_json(PKG / "FROZEN_TEACH1.json")
