"""Per-version generators for CAS synthetic training data.

Each generator emits examples conforming to
`noetic-compass-scaffold/noetic-compass/cas-native/training/data_format.md`.
"""

from .base import BaseGenerator, GeneratedExample
from .v74_baseline import V74BaselineGenerator
from .v75_register import V75RegisterGenerator
from .v77_rule_four import V77RuleFourGenerator
from .v77_omega import V77OmegaGenerator
from .v76_production import V76ProductionGenerator
from .meta_logic import MetaLogicGenerator

__all__ = [
    "BaseGenerator",
    "GeneratedExample",
    "V74BaselineGenerator",
    "V75RegisterGenerator",
    "V77RuleFourGenerator",
    "V77OmegaGenerator",
    "V76ProductionGenerator",
    "MetaLogicGenerator",
]
