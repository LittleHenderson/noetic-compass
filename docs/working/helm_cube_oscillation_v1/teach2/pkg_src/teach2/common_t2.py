"""Shared constants and helpers for TEACH-2 (standard library only).

TEACH-2 teaches HELM a made-up subject through its live chat and reads whether keeping each fact as a cube at its
Atlas node -- only after the CTT's proposal and the brain side's check and say-back agree in rounds -- with the
size-limit memory (Eye capsules, move-off, folding, every-line clues, a stand-in cloud) recalls more and states fewer
wrong current values than today's quote memory, a plain table, one reader alone and never forgetting
(PREREGISTRATION_TEACH2.precode.md f7b6183b..., amendments A-TEACH2-1 to -18). Every number here is frozen;
FROZEN_TEACH2.json repeats them and a package test checks they agree. HELM's code is this package's own `helm_now/`
cut (contract/HELM_CUT_TEACH2.json); the CTT is `ctt/` with its weights pinned by sha256 (I16).
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
LABEL = "TEACH2"
PACKAGE_VERSION = "v1"
PACKAGE_DIR = "HELM_TEACH2_20261022"
PRECODE_SHA256 = "f7b6183bba5f8a1a241e3c64c8930f6a2c6df06fbe8c5845c0207f6d2a84c855"
WORDS = ("INCONCLUSIVE", "CUBES_HARMED", "CUBES_NO_GAIN", "CUBES_EARNED_KEEP")
LABELS_PRINTED = ("SYNTHETIC_ONLY", "LLM_WRITTEN_ONLY", "CTT_RETRAINED_V1", "EYE_REPORT_ONLY")

# ---- the arms (pre-code section 3 as amended by A-TEACH2-3, -15 T4, -18 P5) ----
ARMS = ("VERBATIM_ONLY", "CUBE_OSC", "REPLAY", "QUOTE_ONLY", "TABLE", "TABLE_OSC", "ONE_READER", "CTT_ONLY",
        "EYE_OFF", "FIRST8", "FIFO_DROP")
CUBE_ARMS = ("CUBE_OSC", "REPLAY", "ONE_READER", "CTT_ONLY", "EYE_OFF", "FIRST8")       # the size-limit memory
CTT_ARMS = ("CUBE_OSC", "REPLAY", "TABLE_OSC", "CTT_ONLY", "EYE_OFF", "FIRST8")          # the CTT reads the lines
RULE_ARMS = ("TABLE", "ONE_READER")                                                     # the exam's rule reader
REPORTED_ARMS = ("TABLE_OSC", "EYE_OFF", "FIRST8")
TURN_BUDGET_B = 12
VERBATIM_BUDGET = 10_000
#: arm -> (HELM_MEMORY_COMPACT, turn budget, cube mode or None, eye_off, first8)
ARM_SET = {
    "VERBATIM_ONLY": {"compact": "1", "budget": VERBATIM_BUDGET, "mode": None},
    "CUBE_OSC": {"compact": "1", "budget": TURN_BUDGET_B, "mode": "OSC"},
    "REPLAY": {"compact": "1", "budget": TURN_BUDGET_B, "mode": "OSC"},
    "QUOTE_ONLY": {"compact": "1", "budget": TURN_BUDGET_B, "mode": None},
    "TABLE": {"compact": "0", "budget": TURN_BUDGET_B, "mode": "TABLE"},
    "TABLE_OSC": {"compact": "0", "budget": TURN_BUDGET_B, "mode": "TABLE_OSC"},
    "ONE_READER": {"compact": "1", "budget": TURN_BUDGET_B, "mode": "ONE_READER"},
    "CTT_ONLY": {"compact": "1", "budget": TURN_BUDGET_B, "mode": "CTT_ONLY"},
    "EYE_OFF": {"compact": "1", "budget": TURN_BUDGET_B, "mode": "OSC", "eye_off": True},
    "FIRST8": {"compact": "1", "budget": TURN_BUDGET_B, "mode": "OSC", "first8": True},
    "FIFO_DROP": {"compact": "0", "budget": TURN_BUDGET_B, "mode": None},
}
VOTING_COPIES = ("A4-s1", "A4-s2", "A4-s3")
TWIN_COPY = "A5-s1"
CTT_CONFIGS = {"A4-s1": "A4_9p6M", "A4-s2": "A4_9p6M", "A4-s3": "A4_9p6M", "A5-s1": "A5_2p5M"}
#: I16: the c57 final weights (spec 7.125 follow-up 17), pinned by sha256
CTT_WEIGHTS_SHA256 = {
    "A4-s1": "c39eafb6db92845a463a0c6bc711c73d45ddcb482b5e5eaffad466f337d7a69a",
    "A4-s2": "3bfbf1f064e4dd96980bfa971cbd089706a4b99cfdaba0b84324f4a4b3a883ee",
    "A4-s3": "6418ef1e27ffd18df9f571e9f5410af1afae6843d9d56cbcb01d31ccf947564b",
    "A5-s1": "07a54adcdb58cfb746f35e0d4350a9bde536eb72f97d6b29451960313fca4bc1",
}
CUBE_TRAIN_ZIP_SHA256 = "706e1fa6f3ce77ae4fee7a21cbb05b820c87f8a01c5df237858f81545eb2e899"

# ---- the exam (pre-code section 4; A-TEACH2-18 P6) ----
WORLDS = 16
FACTS_PER_WORLD = 24
UNKNOWN_PER_WORLD = 4
TEACHING_TURNS = 32
PLAN_COUNTS = {"FACT": 18, "UNKNOWN": 4, "TRAP": 4, "FIX": 2, "RESTATE": 2, "SMALL": 2}
TRAP_FIRST = 2                       # TRAP slots that are a fact's first statement (they replace FACT slots)
TRAP_RESTATE = 2                     # TRAP slots that restate an earlier fact with a decoy (they replace SMALL slots)
FLOOR_FACT_TURNS = 18
FLOOR_FIX_TURNS = 2
FLOOR_SMALL_TURNS = 2
QUIZ_QUESTIONS = 16
QUIZ_TAUGHT = 12
QUIZ_UNKNOWN = 2
QUIZ_NEVER = 2
QUIZZES = ("Q_TAUGHT", "Q_SQUEEZED", "Q_REFRESHED")
PERSON_RIGHT_SHARE = 0.75
PLANTED_DAMAGE_PER_WORLD = 2
MAX_TURN_WORDS = 60
SPLIT_NGRAM = 8

# ---- instrument floors (pre-code section 6; A-TEACH2-15 T5) ----
I18_MIN_CUBES = 64                   # CUBE_OSC cubes kept over 16 worlds, else NOT_EXERCISED
I19_MIN_BATCHES = 32                 # CUBE_OSC batches written over 16 worlds
I19_MIN_MOVED_OFF = 16               # CUBE_OSC capsules moved off working memory over 16 worlds
ROUND_CAP = 3

# ---- marks (pre-code section 8; A-TEACH2-15 T6) ----
U1_MIN_RIGHT_T_AVG = 10
C1_MIN_OVER_QUOTE = 8
C2_MIN_OVER_TABLE = 4
C2_MIN_FEWER_WRONG = 4
C3_MIN_WRONG_ELSEWHERE = 2
C3_MIN_OVER_ONE = 4
C4_MAX_LOST_VS_VERBATIM = 2
C4_HARM_LOST_VS_VERBATIM = 4
S_SPACE_SHARE = (1, 2)

# ---- the limits rule (A-TEACH2-15 T2, A-TEACH2-18 P7) ----
LIMIT_ROUND_TO = 100

# ---- seeds (pre-code section 12; A-TEACH2-18 P11) ----
BANDS = {"WORLD": (2_053_000_001, 2_054_000_000), "QUIZ": (2_055_000_001, 2_056_000_000),
         "PERSON": (2_057_000_001, 2_058_000_000), "TRAP": (2_059_000_001, 2_060_000_000)}
HEX_SLICES = {"WORLD": (0, 16), "QUIZ": (16, 32), "PERSON": (32, 48), "TRAP": (48, 64)}
SLOTS = 1_000_000
SEED_GAP = 1_000_000
INT32_MAX = 2 ** 31 - 1
USED_RANGES = (("every earlier band and derivation (CUBE TRAIN used 2,050 M and 2,051 M; whole range)", 1, 2_052_000_000),)
OWNER_LINES = {"CUBE EXAM at 1 USD": {"cap_usd": 1.0, "host": "one GPU host (g4dn.xlarge; g5.xlarge on refused capacity)"}}
PRACTICE_SEED_TEXTS = {"WORLD": "teach2-practice-world", "QUIZ": "teach2-practice-quiz",
                       "PERSON": "teach2-practice-person", "TRAP": "teach2-practice-trap"}

# ---- HELM under test ----
HELM_TESTS_UNITTEST = ("test_helm_brain_wide", "test_helm_end_to_end_loop", "test_helm_english_in",
                       "test_helm_english_in_stock_frame", "test_helm_voice", "test_helm_faces_in", "test_helm_triad",
                       "test_helm_wide_alongside", "test_helm_cas_address", "test_helm_units_note", "test_helm_pin_hygiene",
                       "test_helm_reader_gap")
HELM_TESTS_PYTEST = ("test_helm_memory.py", "test_helm_memory_compact.py", "test_helm_chat_nuance.py",
                     "test_helm_eye_act.py", "test_helm_cube_osc.py", "test_helm_cube_tiers.py", "test_helm_cube_lean.py",
                     "test_helm_cube_offload.py", "test_helm_cube_fold.py", "test_helm_cube_everyline.py",
                     "test_helm_cube_cloudsearch.py", "test_helm_cube_cloudbatch.py", "test_helm_cube_reach_memory.py",
                     "test_helm_cold_cloud_direct.py", "test_helm_ctt_adapter.py")
WAVE1_BRAIN = {"dir": "HELM_R1_W1_20261015_v3",
               "freeze_sha256": "8c55c4136e1b24bc322779160ffed666f9eb9ee21512c1972101263a243c039b"}
BRAIN_DIR_ENV = "HELM_CANONICAL_BRAIN_DIR"

# ---- the frozen clock of every unit (TEACH-1 D-TEACH1-5) ----
FROZEN_CLOCK_UTC = (2026, 10, 22, 0, 0, 0, 3, 295, 0)
FROZEN_CLOCK_START = 1_793_059_200.0   # 2026-10-22T00:00:00Z
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
    """Sorted, LF JSON via .partial + fsync + rename; returns its sha256."""
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
    """Case, whitespace, and the voice's number forms (words -> digits)."""
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


def brain_dir() -> Path:
    return PKG / "brain" / WAVE1_BRAIN["dir"]


def ctt_dir() -> Path:
    return PKG / "ctt"


def helm_cut() -> Dict[str, Any]:
    return read_json(PKG / "contract" / "HELM_CUT_TEACH2.json")


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
        (hn / "SOURCE_CUT.json").read_bytes() == (PKG / "contract" / "HELM_CUT_TEACH2.json").read_bytes()
    return {"commit": cut.get("commit"), "files": len(cut["files"]), "bad": bad[:20], "extra": extra[:20],
            "pinned_ok": pins_ok, "source_cut_equals_contract": source_cut_equal,
            "ok": not bad and not extra and pins_ok and source_cut_equal}


def check_ctt() -> Dict[str, Any]:
    """I16: every CTT weight file equals its pinned sha256."""
    got = {}
    for copy, want in CTT_WEIGHTS_SHA256.items():
        p = ctt_dir() / "weights" / f"{copy}.pt"
        got[copy] = sha256_file(p) if p.is_file() else None
    return {"weights": got, "ok": all(got[c] == CTT_WEIGHTS_SHA256[c] for c in CTT_WEIGHTS_SHA256)}


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
    if brain_dir().is_dir():
        os.environ[BRAIN_DIR_ENV] = str(brain_dir())
    sys.path.insert(0, str(hn))
    import helm_chat  # noqa: F401
    import helm_memory  # noqa: F401
    import helm_memory_compact  # noqa: F401
    import helm_voice  # noqa: F401
    import helm_cube_osc  # noqa: F401
    import helm_cold_cloud  # noqa: F401
    import helm_eye_act  # noqa: F401
    mods = (helm_chat, helm_memory, helm_memory_compact, helm_voice, helm_cube_osc, helm_cold_cloud, helm_eye_act)
    for m in mods:
        if not Path(m.__file__).resolve().is_relative_to(hn.resolve()):
            raise PinRefused(f"{m.__name__} came from {m.__file__}, not helm_now/")
    return {m.__name__: m for m in mods}


def frozen() -> Dict[str, Any]:
    return read_json(PKG / "FROZEN_TEACH2.json")
