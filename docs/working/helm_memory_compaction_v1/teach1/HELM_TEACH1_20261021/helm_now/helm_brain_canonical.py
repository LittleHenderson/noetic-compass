"""helm_brain_canonical.py -- loads HELM's ONE official brain, the licensed recipe brain, by path.

WHAT THIS IS
------------
A small adapter. It does not contain the brain. It loads the brain's pure-Python sources from the sealed
HELM-R1 wave-1 package, checks every loaded file against that package's own PACKAGE_FREEZE.json, and gives the
live loop four calls: which ingredients a product needs, how much of it the stock can make (and which
ingredient runs out first), teach it from a witnessed batch, and replay witnessed batches on a fresh copy.

Owner approval (2026-10-18, "recipe brain is canonical"): the licensed HELM-R1 wave-1 recipe brain
(c34 PASS R1_BEATS_GB3) is HELM's one official brain. `helm_brain_22x40.py` is a demo stand-in only.

WHICH PART OF THE PACKAGE IS LOADED
-----------------------------------
The Task B recipe book `rb2.brain_b.RecipeBookBrain` with its writer `rb2.writer_b.teach_step_b`
(witnessed_lr_ratio_v1 + the eta/epsilon receipt + the memory check) and its algebra `rb2.compose`
(exact Fractions, Limiting Reagent, gate G1-G5, depth cap 5). That is the part the wave-1 claim credits with
"named the Limiting Reagent of fresh held-out compositions". It imports `rb` (the RB-A sources), which
installs the package's own torch/numpy blocker (`rb.no_torch`), and the vendored LSR engines lsr_t1..lsr_t4.

Loaded members (all stdlib-only, each checked by sha256 against PACKAGE_FREEZE.json before import):
    rb/__init__.py rb/no_torch.py rb/common.py rb/brain.py rb/writer.py
    rb2/__init__.py rb2/brain_b.py rb2/compose.py rb2/writer_b.py
    vendor/lsr_t1..lsr_t4 (__init__.py, engine.py)

TORCH
-----
Nothing loaded here needs torch. The torch-only parts of the package are the world generator
`make_worlds.py`, `t_on_b/`, `t_task_a/score_t.py` and `r1/t_gb_check.py` (the GB3 / T transformer side). They are
NOT imported, and `TORCH_ONLY_MEMBERS` lists them so a test can prove it. Side effect, stated plainly: importing
`rb` installs the package's import blocker, so after this adapter loads, the same Python process refuses
`import torch` and `import numpy`. If torch is already loaded when the adapter starts, it refuses to load
(`CanonicalBrainRefused`, code TORCH_ALREADY_LOADED) instead of breaking the blocker.

THE NAMING MAP (OUR_CONVENTION, labeled)
----------------------------------------
The brain has 8 stock cells and 4 recipes with a FIXED programmed support
(compose.CATALOG = {0: (0, 1), 1: (2, 3), 2: (4, 5, 6), 3: (2, 5, 7)}). The brain knows only cell numbers.
`DEFAULT_BINDING` gives the cells and recipes everyday names so a person can talk to it. Renaming changes
nothing inside the brain; the binding and its sha256 are written into every receipt. A product whose
ingredients do not match one of the four fixed supports cannot be represented: that is a real limit of the
licensed brain, not something this adapter papers over.

WHAT THE BRAIN IS NEVER TOLD
----------------------------
A requirement number. It learns each requirement only from a witnessed batch: the stock before the batch, how
much was made, and which ingredient ran out first (a[R][i] := x_i / y, exact). A stated recipe ("use 2 of
Flour") is not a witnessed batch and is not taught.

CLAIM CEILING: SYNTHETIC-WORLD LICENSE ONLY. Wiring the licensed brain into the loop does not extend its
license: nothing here shows it beats anything on real kitchens or real data.
"""
from __future__ import annotations

import copy
import hashlib
import importlib
import json
import os
import sys
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Tuple

CLAIM_CEILING = (
    "SYNTHETIC-WORLD LICENSE ONLY. THE LICENSED BRAIN IS WIRED INTO THE LIVE LOOP; "
    "THE WIRING DOES NOT EXTEND ITS LICENSE TO REAL DATA."
)

#: Default location of the sealed wave-1 package (owner approval 2026-10-18 names this folder).
DEFAULT_BRAIN_DIR = r"C:\Users\wakil\Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_v3"
#: Environment variable that overrides the location.
BRAIN_DIR_ENV = "HELM_CANONICAL_BRAIN_DIR"
#: sha256 of the package's PACKAGE_FREEZE.json as read on 2026-10-18. The adapter refuses a different freeze file
#: unless the caller passes `expected_freeze_sha256=None` on purpose (recorded in provenance).
EXPECTED_FREEZE_SHA256 = "8c55c4136e1b24bc322779160ffed666f9eb9ee21512c1972101263a243c039b"

LOADED_MEMBERS = (
    "rb/__init__.py", "rb/no_torch.py", "rb/common.py", "rb/brain.py", "rb/writer.py",
    "rb2/__init__.py", "rb2/brain_b.py", "rb2/compose.py", "rb2/writer_b.py",
    "vendor/lsr_t1/__init__.py", "vendor/lsr_t1/engine.py",
    "vendor/lsr_t2/__init__.py", "vendor/lsr_t2/engine.py",
    "vendor/lsr_t3/__init__.py", "vendor/lsr_t3/engine.py",
    "vendor/lsr_t4/__init__.py", "vendor/lsr_t4/engine.py",
)
#: Never imported by this adapter (they need torch; AWS only).
TORCH_ONLY_MEMBERS = ("make_worlds.py", "t_on_b/t_b.py", "t_task_a/score_t.py", "r1/t_gb_check.py")
_MODULES = ("rb", "rb.no_torch", "rb.common", "rb.brain", "rb.writer", "rb2", "rb2.brain_b", "rb2.compose",
            "rb2.writer_b", "lsr_t1.engine", "lsr_t2.engine", "lsr_t3.engine", "lsr_t4.engine")

#: OUR_CONVENTION naming map. Cells 0-7 and the four fixed recipe supports, named.
DEFAULT_BINDING: Dict[str, Any] = {
    "cells": ["Flour", "Water", "Sugar", "Butter", "Milk", "Egg", "Yeast", "Salt"],
    "products": {"Bread": 0, "Frosting": 1, "Starter": 2, "Meringue": 3},
    "note": "OUR_CONVENTION names for the brain's fixed cells and recipe supports; renaming changes nothing inside",
}

ABSENT = "ABSENT"
EVALUATED = "EVALUATED"
UNDETERMINED = "UNDETERMINED"


class CanonicalBrainRefused(RuntimeError):
    """The adapter refuses to load or to answer. Carries a stable code."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def frac_text(v: Optional[Fraction]) -> Optional[str]:
    if v is None:
        return None
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def exact_amount(value: Any) -> Fraction:
    """An amount as an exact Fraction. Floats are refused (no silent rounding)."""
    if isinstance(value, bool) or isinstance(value, float):
        raise CanonicalBrainRefused("AMOUNT_NOT_EXACT", f"{value!r}: pass text, int, Decimal or Fraction")
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise CanonicalBrainRefused("AMOUNT_NOT_A_NUMBER", f"{value!r}") from exc


def _board_value(amount: Fraction) -> float:
    """The brain's boards are binary64. Amendment A1: accept only amounts that name exactly one binary64."""
    as_float = float(amount)
    if Fraction(as_float) != amount:
        raise CanonicalBrainRefused("AMOUNT_NOT_BINARY64_EXACT", f"{frac_text(amount)} has no exact binary64 form")
    return as_float


def load_package(brain_dir: Optional[str] = None,
                 expected_freeze_sha256: Optional[str] = EXPECTED_FREEZE_SHA256) -> Dict[str, Any]:
    """Check every loaded member against PACKAGE_FREEZE.json, then import. Returns the provenance record."""
    brain_dir = os.path.abspath(brain_dir or os.environ.get(BRAIN_DIR_ENV) or DEFAULT_BRAIN_DIR)
    freeze_path = os.path.join(brain_dir, "PACKAGE_FREEZE.json")
    if not os.path.isfile(freeze_path):
        raise CanonicalBrainRefused("PACKAGE_NOT_FOUND", freeze_path)
    freeze_sha = sha256_file(freeze_path)
    if expected_freeze_sha256 is not None and freeze_sha != expected_freeze_sha256:
        raise CanonicalBrainRefused("FREEZE_SHA256_MISMATCH", f"{freeze_sha} != {expected_freeze_sha256}")
    with open(freeze_path, "r", encoding="utf-8") as fh:
        members = json.load(fh).get("members", {})
    checked = {}
    for rel in LOADED_MEMBERS:
        want = (members.get(rel) or {}).get("sha256")
        got = sha256_file(os.path.join(brain_dir, *rel.split("/")))
        if want is None or got != want:
            raise CanonicalBrainRefused("MEMBER_SHA256_MISMATCH", f"{rel}: {got} != {want}")
        checked[rel] = got
    if "torch" in sys.modules or "numpy" in sys.modules:
        raise CanonicalBrainRefused("TORCH_ALREADY_LOADED",
                                    "the licensed brain's process must not hold torch or numpy")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    mods = {name: importlib.import_module(name) for name in _MODULES}
    for name, mod in mods.items():
        origin = os.path.abspath(getattr(mod, "__file__", "") or "")
        if not origin.startswith(brain_dir):
            raise CanonicalBrainRefused("MODULE_SHADOWED", f"{name} loaded from {origin}, not {brain_dir}")
    return {
        "brain_dir": brain_dir,
        "package_freeze_sha256": freeze_sha,
        "freeze_pinned": expected_freeze_sha256 is not None,
        "members_sha256": checked,
        "torch_blocker": mods["rb.no_torch"].report(),
        "torch_only_members_not_imported": list(TORCH_ONLY_MEMBERS),
        "modules": mods,
    }


class CanonicalRecipeBrain:
    """The live loop's handle on the licensed recipe brain (RB-B). Decides nothing the brain does not decide."""

    kind = "canonical_rb_b"

    def __init__(self, brain_dir: Optional[str] = None, binding: Optional[Dict[str, Any]] = None,
                 expected_freeze_sha256: Optional[str] = EXPECTED_FREEZE_SHA256) -> None:
        pkg = load_package(brain_dir, expected_freeze_sha256)
        mods = pkg.pop("modules")
        self._C = mods["rb2.compose"]
        self._B = mods["rb2.brain_b"]
        self._W = mods["rb2.writer_b"]
        self._labels = mods["rb.common"].LABELS
        self.package = pkg
        self.binding = copy.deepcopy(binding or DEFAULT_BINDING)
        cells = list(self.binding["cells"])
        if len(cells) != self._C.CELLS or len(set(cells)) != len(cells):
            raise CanonicalBrainRefused("BINDING_INVALID", "need 8 distinct cell names")
        products = dict(self.binding["products"])
        if sorted(products.values()) != list(range(len(self._C.CATALOG))):
            raise CanonicalBrainRefused("BINDING_INVALID", "each of the 4 fixed recipes needs exactly one name")
        self.ingredients: List[str] = cells
        self.products: Dict[str, int] = products
        self.binding_sha256 = hashlib.sha256(_canon(self.binding)).hexdigest()
        self.brain = self._B.RecipeBookBrain()
        self.group: Dict[int, Any] = {}
        self.witness_log: List[Dict[str, Any]] = []
        self._seed = 0

    # ------------------------------------------------------------------ names
    def provenance(self) -> Dict[str, Any]:
        return {"brain": "HELM-R1 wave-1 recipe brain, Task B recipe book (rb2.brain_b.RecipeBookBrain)",
                "license": "c34 PASS R1_BEATS_GB3 (synthetic worlds only)",
                "claim_ceiling": CLAIM_CEILING,
                "brain_dir": self.package["brain_dir"],
                "package_freeze_sha256": self.package["package_freeze_sha256"],
                "members_sha256": dict(self.package["members_sha256"]),
                "torch_blocker": dict(self.package["torch_blocker"]),
                "binding_sha256": self.binding_sha256,
                "learned_digest": self.brain.learned_digest()}

    def product_of(self, name: str) -> Optional[str]:
        clean = name[2:] if name.startswith("Ω_") else name
        for p in self.products:
            if p.lower() == clean.lower():
                return p
        return None

    def ingredient_of(self, name: str) -> Optional[str]:
        clean = name[2:] if name.startswith("Ω_") else name
        for c in self.ingredients:
            if c.lower() == clean.lower():
                return c
        return None

    def support_of(self, product: str) -> List[str]:
        """The product's prerequisite list: the recipe's own programmed support, named."""
        k = self.products[product]
        return [self.ingredients[i] for i in self._C.CATALOG[k]]

    def unlearned(self, product: str) -> List[str]:
        """Ingredients whose requirement for `product` is still ABSENT (never witnessed as limiting)."""
        k = self.products[product]
        return [self.ingredients[i] for i in self._C.CATALOG[k] if self.brain.book[k][i] is None]

    def requirements(self, product: str) -> Dict[str, Optional[str]]:
        k = self.products[product]
        return {self.ingredients[i]: frac_text(self.brain.book[k][i]) for i in self._C.CATALOG[k]}

    def _board(self, product: str, stock: Dict[str, Fraction]) -> Tuple[List[float], List[float], List[str]]:
        """Board 1 (stock) + board 2 (order). Every support cell MUST be present: an absent support cell is
        refused here, never filled. Cells outside the support are never read by the brain's recipe algebra;
        they carry the recorded stock if there is one, else 0 as board padding, and are listed as padding."""
        support = self.support_of(product)
        missing = [c for c in support if c not in stock]
        if missing:
            raise CanonicalBrainRefused("ABSENT_SUPPORT_CELL", ", ".join(missing))
        board1, padding = [], []
        for name in self.ingredients:
            if name in stock:
                board1.append(_board_value(stock[name]))
            else:
                board1.append(0.0)
                padding.append(name)
        order = (self._C.SINGLE, self.products[product])
        return board1, self._C.order_code(order), padding

    # ------------------------------------------------------------------ answering
    def evaluate(self, product: str, stock: Dict[str, Fraction]) -> Dict[str, Any]:
        """How much of `product` the stock can make, and which ingredient runs out first. Behind the brain's own
        gate: UNDETERMINED is not wrong. Also performs the eta/epsilon read-back through the brain's memory:
        board 1 is written into M (eta) and the answer is read back from M (epsilon); both must agree."""
        board1, code, padding = self._board(product, stock)
        order = (self._C.SINGLE, self.products[product])
        label, res = self._C.answer(order, self.brain.book, board1, dirty=self.brain.dirty)
        direct = self.brain.readout(board1 + code)
        self.brain.write_board1(board1)                    # eta: the programmed memory write (copy of board 1)
        from_memory = self.brain.read_board2(code)          # epsilon: the readout reads M and the order only
        read_back_ok = (from_memory.label == direct.label == label
                        and from_memory.limiting == direct.limiting
                        and [frac_text(v) for v in from_memory.yields] == [frac_text(v) for v in direct.yields])
        record = {
            "product": product, "label": label, "gate": res.gate,
            "yield": frac_text(res.value), "limiting_cell": res.lr,
            "limiting_reagent": None if res.lr is None else self.ingredients[res.lr],
            "result": self._C.result_record(res), "padding_cells_not_read": padding,
            "eta_eps_read_back": {"via": "MemoryBase.write_board1 -> read_board2", "pass": bool(read_back_ok),
                                  "label_direct": direct.label, "label_from_memory": from_memory.label},
            "learned_digest": self.brain.learned_digest(),
        }
        record["status"] = EVALUATED if (label != UNDETERMINED and read_back_ok) else UNDETERMINED
        return record

    # ------------------------------------------------------------------ teaching
    def _gold(self, product: str, ran_out: str) -> Tuple[str, int]:
        k = self.products[product]
        if ran_out not in self.ingredients:
            raise CanonicalBrainRefused("RAN_OUT_UNKNOWN", f"{ran_out!r} is not one of the brain's ingredients")
        cell = self.ingredients.index(ran_out)
        inputs = self._C.order_inputs((self._C.SINGLE, k))
        if cell not in inputs:
            raise CanonicalBrainRefused("RAN_OUT_NOT_A_PREREQUISITE", f"{ran_out} is not in {product}'s recipe")
        return self._labels[inputs.index(cell)], cell

    def _teach(self, brain, group, product, stock_before, made, ran_out, seed):
        board1, code, padding = self._board(product, stock_before)
        gold, cell = self._gold(product, ran_out)
        feedback = {"yield": frac_text(exact_amount(made)), "lr_cell": cell}
        after, record = self._W.teach_step_b(brain, board1 + code, gold, seed, group, feedback, exposure=False)
        record = copy.deepcopy(record)
        record.update({"product": product, "ran_out": ran_out, "made": feedback["yield"], "gold": gold,
                       "padding_cells_not_read": padding})
        return after, record

    def witness(self, product: str, stock_before: Dict[str, Fraction], made: Any, ran_out: str) -> Dict[str, Any]:
        """One witnessed batch through the brain's OWN writer (candidate, eta/epsilon receipt, memory check).
        Admitted only if the writer admits it. A refusal is the writer's, recorded verbatim."""
        self._seed += 1
        row = {"seed": self._seed, "product": product, "made": frac_text(exact_amount(made)), "ran_out": ran_out,
               "stock_before": {k: frac_text(v) for k, v in stock_before.items()}}
        self.brain, record = self._teach(self.brain, self.group, product, stock_before, made, ran_out, self._seed)
        row["admitted"] = record["admitted"]
        row["reason"] = record["reason"]
        self.witness_log.append(row)
        record["learned_digest_after"] = self.brain.learned_digest()
        return record

    def replay(self, rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Replay witnessed rows, in order, on a FRESH brain through the same writer. Changes nothing here."""
        brain, group, out = self._B.RecipeBookBrain(), {}, []
        for row in rows:
            stock = {k: Fraction(v) for k, v in row["stock_before"].items()}
            brain, record = self._teach(brain, group, row["product"], stock, Fraction(row["made"]),
                                        row["ran_out"], row["seed"])
            out.append({"seed": row["seed"], "admitted": record["admitted"], "reason": record["reason"],
                        "detail": record.get("detail")})
        return out
