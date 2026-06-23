"""Compiler Bridge — connects CAS Forex to the real CAS compiler.

Uses api.notation.compiler to validate CAS expressions produced
from market conditions. The compiler is the authority on whether
a CAS expression is valid, admissible, and domain-descent-correct.

CAS Executable Notation (from Programming in CAS):
  State:  ^k^D_{Fd}|R   e.g., ^2^P_{F2}|A
  Relation: state -> state, state <-> state
  Recipe (v7.6):  Θ(Ω) = a₁·X₁ + a₂·X₂ → Ω

For Forex:
  Market trend    → ^2^P_{F2}|A  (Abstractification/Principial/Wisdom/Analytical)
  Price action    → ^3^C_{F3}|E  (Concretization/Cognitive/Vitality/Embodied)
  Breakout        → ^8^E_{F6}|A  (Expansion/Evaluative/Structure/Analytical)
  Reversal        → ^7^O_{F5}|f  (DirectedFocus/Operational/Agency/Affective)
  Consolidation   → ^0^C_{F6}|T  (Identity/Cognitive/Structure/Transcendent)
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cas_forex.schemas.forecast import Direction, ForecastProposal
from cas_forex.schemas.market import MarketSnapshot


# ---- Market → CAS Expression Mapping ----

# Each market condition maps to a valid CAS state literal in executable notation.
# Format: ^k^D_{Fd}|R = Noetic k, Domain D, Drive Fd, Register R
MARKET_CAS_MAP: Dict[str, Dict[str, str]] = {
    # Directional states
    "trend_bullish": {
        "state": "^2^P_{F2}|A",
        "meaning": "Abstractification in Principled driven by Wisdom (Analytical) — seeing the bigger trend",
    },
    "trend_bearish": {
        "state": "^3^C_{F3}|A",
        "meaning": "Concretization in Cognitive driven by Vitality (Analytical) — seeing the specific decline",
    },
    # Momentum states
    "momentum_strong": {
        "state": "^6^E_{F5}|E",
        "meaning": "Critical Evaluation in Evaluative driven by Agency (Embodied) — strong conviction",
    },
    "momentum_weak": {
        "state": "^0^E_{F6}|T",
        "meaning": "Identity in Evaluative driven by Structure (Transcendent) — waiting, no conviction",
    },
    # Volatility states
    "volatility_high": {
        "state": "^4^O_{F3}|f",
        "meaning": "Integration in Operational driven by Vitality (Affective) — processing chaos",
    },
    "volatility_low": {
        "state": "^7^C_{F6}|A",
        "meaning": "Directed Focus in Cognitive driven by Structure (Analytical) — calm, methodical",
    },
    # Breakout/Reversal
    "breakout": {
        "state": "^8^E_{F5}|E",
        "meaning": "Expansion in Evaluative driven by Agency (Embodied) — breaking boundaries",
    },
    "reversal": {
        "state": "^9^O_{F7}|f",
        "meaning": "Contraction in Operational driven by Purpose (Affective) — turning back",
    },
    # Risk states
    "safe_entry": {
        "state": "^1^C_{F2}|A",
        "meaning": "Differentiation in Cognitive driven by Wisdom (Analytical) — clean setup identified",
    },
    "risky_entry": {
        "state": "^4^E_{F5}|f",
        "meaning": "Integration in Evaluative driven by Agency (Affective) — rushing, unclear",
    },
}


def market_to_cas_state(
    snapshot: MarketSnapshot,
    direction: Direction,
    atr: Optional[float] = None,
) -> str:
    """Convert current market conditions into a CAS state expression.

    Returns a compilable CAS state literal like '^2^P_{F2}|A'.
    """
    # Determine primary condition
    if snapshot.spread > 5.0:
        condition = "volatility_high"
    elif atr and atr > 0.002:
        condition = "momentum_strong"
    elif direction == Direction.LONG:
        condition = "trend_bullish"
    else:
        condition = "trend_bearish"

    entry = MARKET_CAS_MAP.get(condition, MARKET_CAS_MAP["safe_entry"])
    return entry["state"]


def market_to_cas_relation(
    snapshot: MarketSnapshot,
    direction: Direction,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    atr: Optional[float] = None,
) -> str:
    """Build a CAS relation expression linking market state to trade action.

    Returns a compilable CAS relation like '^2^P_{F2}|A -> ^2^C_{F2}|T'.
    The arrow (→) means "leads to" / "dependency."

    For LONG trades:
      Source = the market condition state
      Target = the desired outcome state
    For SHORT trades:
      Same structure, but the Noetics reflect the downward direction.
    """
    source_state = market_to_cas_state(snapshot, direction, atr)

    # Target state depends on trade direction
    if direction == Direction.LONG:
        target = "^2^C_{F2}|T"  # Abstractification in Cognitive driven by Wisdom (Transcendent) — "profit insight"
    else:
        target = "^3^C_{F3}|T"  # Concretization in Cognitive driven by Vitality (Transcendent) — "cashing the decline"

    return f"{source_state} -> {target}"


def market_to_cas_recipe(
    snapshot: MarketSnapshot,
    direction: Direction,
    confidence: float,
    atr: Optional[float] = None,
) -> Optional[str]:
    """Build a CAS v7.6 recipe (production semantics) for the trade.

    Recipe format: Θ(Ω_trade_profit) = a·X₁ + b·X₂ + c·X₃ → Ω_trade_profit

    Where:
      Θ = recipe function for trade profit
      Ω_trade_profit = the named production target (profit outcome)
      X₁, X₂, X₃ = prerequisite states (market conditions)
      a, b, c = coefficients (confidence weights)

    Returns None if not enough evidence for a recipe.
    """
    parts = []

    # Trend component
    trend_state = market_to_cas_state(snapshot, direction, atr)
    trend_weight = round(confidence * 0.4, 3)
    parts.append(f"{trend_weight}·{trend_state}")

    # Volatility component
    if atr and atr > 0:
        vol_weight = round(confidence * 0.2, 3)
        parts.append(f"{vol_weight}·^4^O_{{F3}}|f")

    # Structure/setup component
    setup_weight = round(confidence * 0.3, 3)
    parts.append(f"{setup_weight}·^1^C_{{F2}}|A")

    # Conviction component
    conviction_weight = round(confidence * 0.1, 3)
    parts.append(f"{conviction_weight}·^6^E_{{F5}}|E")

    prereqs = " + ".join(parts)
    target = "Ω_trade_profit"
    return f"Θ({target}) = {prereqs} → {target}"


# ---- Compiler Bridge ----


class CompilerResult:
    """Structured result from compiling a CAS expression."""

    def __init__(
        self,
        expression: str,
        valid: bool = False,
        error: Optional[str] = None,
        admissible: Optional[bool] = None,
        domain_descent_ok: Optional[bool] = None,
        relation: Optional[str] = None,
        raw_result: Optional[Dict] = None,
    ):
        self.expression = expression
        self.valid = valid
        self.error = error
        self.admissible = admissible
        self.domain_descent_ok = domain_descent_ok
        self.relation = relation
        self.raw_result = raw_result or {}

    @property
    def is_clean(self) -> bool:
        """Expression compiles AND is admissible AND domain descent is valid."""
        return (
            self.valid
            and (self.admissible is None or self.admissible)
            and (self.domain_descent_ok is None or self.domain_descent_ok)
        )

    def to_dict(self) -> dict:
        return {
            "expression": self.expression,
            "valid": self.valid,
            "error": self.error,
            "admissible": self.admissible,
            "domain_descent_ok": self.domain_descent_ok,
            "relation": self.relation,
            "is_clean": self.is_clean,
        }


class CASCompilerBridge:
    """Bridge to the real CAS compiler in api/notation/compiler.py.

    Falls back gracefully if the compiler module is not importable
    (e.g., when running cas-forex standalone without noetic-compass in path).
    """

    def __init__(self):
        self._available = False
        self._compile_fn = None
        self._compiler_path: Optional[Path] = None
        self._load_compiler()

    def _load_compiler(self) -> None:
        """Load the sibling Noetic Compass CAS compiler robustly.

        CAS Forex also has a top-level ``api`` package for its FastAPI app, so
        ``from api.notation.compiler import ...`` is fragile: if the local API
        package is already on ``sys.path`` (or cached in ``sys.modules``), the
        import resolves to the wrong package and the compiler appears missing.
        The bridge therefore loads the compiler by absolute file path under a
        private module name while still adding the Noetic root to ``sys.path`` so
        optional helpers such as ``cas_engine`` can be found.
        """

        errors: list[str] = []
        for compiler_path in _candidate_compiler_paths():
            try:
                compiler_path = compiler_path.resolve()
                noetic_root = compiler_path.parents[2]
                noetic_root_text = str(noetic_root)
                if noetic_root_text not in sys.path:
                    sys.path.insert(0, noetic_root_text)

                spec = importlib.util.spec_from_file_location(
                    "_cas_forex_noetic_compiler",
                    compiler_path,
                )
                if spec is None or spec.loader is None:
                    errors.append(f"{compiler_path}: no import spec")
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules["_cas_forex_noetic_compiler"] = module
                spec.loader.exec_module(module)
                compile_fn = getattr(module, "compile_expression", None)
                if compile_fn is None:
                    errors.append(f"{compiler_path}: compile_expression missing")
                    continue
                self._compile_fn = compile_fn
                self._compiler_path = compiler_path
                self._available = True
                return
            except Exception as exc:  # pragma: no cover - diagnostic fallback
                errors.append(f"{compiler_path}: {exc}")

        # Keep the bridge safely disabled but expose why in compile errors.
        self._available = False
        self._load_error = "; ".join(errors) or "no candidate compiler.py found"

    @property
    def available(self) -> bool:
        return self._available

    def compile_expression(self, expression: str) -> CompilerResult:
        """Compile a CAS expression through the real compiler.

        Returns CompilerResult with validation details.
        If compiler unavailable, returns valid=False with error message.
        """
        if not self._available or not self._compile_fn:
            return CompilerResult(
                expression=expression,
                valid=False,
                error=(
                    "CAS compiler not available "
                    f"({getattr(self, '_load_error', 'noetic-compass not in path')})"
                ),
            )

        try:
            artifact = self._compile_fn(expression)
            result_dict = artifact.to_dict()

            # Extract structured fields
            valid = result_dict.get("valid", False)
            error = result_dict.get("error")

            # The result field contains runtime evaluation
            runtime = result_dict.get("result") or {}
            admissible = runtime.get("admissible") if isinstance(runtime, dict) else None
            descent_ok = runtime.get("domain_descent_ok") if isinstance(runtime, dict) else None
            relation = runtime.get("relation") if isinstance(runtime, dict) else None

            return CompilerResult(
                expression=expression,
                valid=valid,
                error=error,
                admissible=admissible,
                domain_descent_ok=descent_ok,
                relation=relation,
                raw_result=result_dict,
            )

        except Exception as e:
            return CompilerResult(
                expression=expression,
                valid=False,
                error=str(e),
            )

    def validate_trade_expression(
        self,
        snapshot: MarketSnapshot,
        direction: Direction,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        confidence: float = 0.7,
        atr: Optional[float] = None,
    ) -> Tuple[CompilerResult, Optional[CompilerResult]]:
        """Validate a trade through the CAS compiler.

        Returns:
            (relation_result, recipe_result) — recipe_result may be None
            if not enough evidence for a recipe.
        """
        # 1. Simple state check
        state_expr = market_to_cas_state(snapshot, direction, atr)
        state_result = self.compile_expression(state_expr)

        # 2. Relation check
        relation_expr = market_to_cas_relation(
            snapshot, direction, entry_price, stop_loss, take_profit, atr
        )
        relation_result = self.compile_expression(relation_expr)

        # 3. Recipe check (v7.6 production semantics)
        recipe_result = None
        if confidence >= 0.4:
            recipe_expr = market_to_cas_recipe(snapshot, direction, confidence, atr)
            if recipe_expr:
                recipe_result = self.compile_expression(recipe_expr)

        return relation_result, recipe_result


# ---- Singleton ----

_bridge: Optional[CASCompilerBridge] = None


def get_bridge() -> CASCompilerBridge:
    global _bridge
    if _bridge is None:
        _bridge = CASCompilerBridge()
    return _bridge


def _candidate_compiler_paths() -> list[Path]:
    """Return plausible CAS compiler locations for Windows, WSL, and bundles."""

    here = Path(__file__).resolve()
    cas_forex_root = here.parents[1]
    workspace_root = here.parents[2]
    candidates: list[Path] = []

    env_root = os.environ.get("CAS_COMPILER_ROOT") or os.environ.get("NOETIC_COMPASS_ROOT")
    if env_root:
        candidates.append(Path(env_root) / "api" / "notation" / "compiler.py")

    candidates.extend(
        [
            workspace_root / "noetic-compass-scaffold" / "noetic-compass" / "api" / "notation" / "compiler.py",
            workspace_root / "dist" / "cas-offline" / "api" / "notation" / "compiler.py",
            workspace_root / "dist" / "_cas-offline-build" / "api" / "notation" / "compiler.py",
            cas_forex_root / "api" / "notation" / "compiler.py",
            Path.cwd() / "noetic-compass-scaffold" / "noetic-compass" / "api" / "notation" / "compiler.py",
        ]
    )

    # Preserve the old absolute Windows intent, but make it usable from WSL by
    # including the mounted path. These are only tried if present.
    candidates.extend(
        [
            Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass\api\notation\compiler.py"),
            Path("/mnt/c/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/notation/compiler.py"),
        ]
    )

    seen: set[str] = set()
    existing: list[Path] = []
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            existing.append(path)
    return existing
