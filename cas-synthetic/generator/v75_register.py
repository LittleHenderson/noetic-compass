"""v7.5 register-annotated generator.

Produces examples where each CAS state carries a register annotation
(|T, |A, |f, |E) per Clarification 8. Emits register_labels per the
data_format.md schema — one entry per register-annotated position.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .base import BaseGenerator, GeneratedExample


_V74_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "v74_templates.yaml"
_V75_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "v75_templates.yaml"


class V75RegisterGenerator(BaseGenerator):
    BUCKET = "v75_register"

    def __init__(
        self,
        seed: int | None = None,
        llm_provider: Any = None,
        template_path: Path | None = None,
        v74_template_path: Path | None = None,
    ) -> None:
        super().__init__(seed=seed, llm_provider=llm_provider)
        with open(template_path or _V75_TEMPLATES, encoding="utf-8") as f:
            self.templates = yaml.safe_load(f)
        with open(v74_template_path or _V74_TEMPLATES, encoding="utf-8") as f:
            self.v74_templates = yaml.safe_load(f)

    def _generate_one(self) -> GeneratedExample:
        scenarios = self.templates["scenarios"]
        register_phrases = self.templates["register_phrases"]
        noetic_phrases = self.v74_templates["noetic_phrases"]
        domain_phrases = self.v74_templates["domain_phrases"]

        # 50% single-state register, 50% two-state register
        single = self.rng.random() < 0.5
        if single:
            noetic = self.rng.choice(self.NOETICS)
            domain = self.rng.choice(self.DOMAINS)
            drive = self.rng.choice(self.DRIVES)
            register = self.rng.choice(self.REGISTERS)
            expression = f"^{noetic}^{domain}|{register}_{{F{drive}}}"
            states = [(noetic, domain)]
            register_labels = [{"position": 0, "register": register}]
        else:
            domain = self.rng.choice(self.DOMAINS)
            n1 = self.rng.choice(self.NOETICS)
            n2 = self.rng.choice([n for n in self.NOETICS if n != n1])
            drive = self.rng.choice(self.DRIVES)
            r1 = self.rng.choice(self.REGISTERS)
            r2 = self.rng.choice(self.REGISTERS)
            expression = (
                f"^{n1}^{domain}|{r1}_{{F{drive}}} * ^{n2}^{domain}|{r2}_{{F{drive}}}"
            )
            states = [(n1, domain), (n2, domain)]
            register_labels = [
                {"position": 0, "register": r1},
                {"position": 1, "register": r2},
            ]

        scenario = self.rng.choice(scenarios)
        prompt = f"{scenario} must act with a clear register."

        response_parts: list[str] = []
        for idx, (noetic, dom) in enumerate(states):
            noetic_key = str(noetic) if str(noetic) in noetic_phrases else noetic
            np = self.rng.choice(noetic_phrases[noetic_key])
            dp = self.rng.choice(domain_phrases[dom])
            reg = register_labels[idx]["register"]
            rp = self.rng.choice(register_phrases[reg])
            response_parts.append(f"{'They' if idx > 0 else scenario} {np}, {dp}, {rp}.")

        response = " ".join(response_parts)

        return GeneratedExample(
            prompt=prompt,
            response=response,
            cas_expression=expression,
            scores=self._scores_from_states(states),
            register_labels=register_labels,
            omega_labels=[],
            production_target=None,
            bucket=self.BUCKET,
            is_valid=True,
            violation_type=None,
            distance_to_valid=0.0,
        )
