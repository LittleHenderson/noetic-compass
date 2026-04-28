"""CAS meta-logic / cluster / diagram-capable construct generator.

This bucket emits only compiler-admitted finite typed set, cluster,
coordinate, product, cover, partition, and finite-meet pullback examples.
`Pullback(...)` is represented honestly as the admitted finite
meet/intersection constructor over finite clusters, not as a general
categorical pullback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .base import BaseGenerator, GeneratedExample


_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "meta_logic_templates.yaml"


class MetaLogicGenerator(BaseGenerator):
    BUCKET = "meta_logic"

    def __init__(
        self,
        seed: int | None = None,
        llm_provider: Any = None,
        template_path: Path | None = None,
    ) -> None:
        super().__init__(seed=seed, llm_provider=llm_provider)
        with open(template_path or _TEMPLATE_PATH, encoding="utf-8") as f:
            self.templates = yaml.safe_load(f)
        self.constructs = self.templates["constructs"]
        if not self.constructs:
            raise RuntimeError("meta-logic templates contain no constructs")

    def _generate_one(self) -> GeneratedExample:
        construct = self.rng.choice(self.constructs)
        states = [(int(n), str(d)) for n, d in construct.get("states", [])]
        registers = list(construct.get("registers", []))

        register_labels = [
            {"position": i, "register": reg} for i, reg in enumerate(registers)
        ]

        family = construct["family"]
        response = f"{construct['response']} Construct family: {family}."

        return GeneratedExample(
            prompt=construct["prompt"],
            response=response,
            cas_expression=construct["expression"],
            scores=self._scores_from_states(states),
            register_labels=register_labels,
            omega_labels=[],
            production_target=None,
            bucket=self.BUCKET,
            is_valid=True,
            violation_type=None,
            distance_to_valid=0.0,
        )
