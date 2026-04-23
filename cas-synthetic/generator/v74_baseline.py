"""v7.4 baseline generator — noetic × domain × drive, no register.

Produces examples with:
- cas_expression using CO-{n}^{D}_{{F{k}}} notation
- scores field populated with operator/domain score vectors
- prompt/response text constructed from v74_templates.yaml phrases
- NO register_labels, NO omega_labels, NO production_target
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import yaml

from .base import BaseGenerator, GeneratedExample


_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "v74_templates.yaml"


class V74BaselineGenerator(BaseGenerator):
    BUCKET = "v74_baseline"

    def __init__(
        self,
        seed: int | None = None,
        llm_provider: Any = None,
        template_path: Path | None = None,
    ) -> None:
        super().__init__(seed=seed, llm_provider=llm_provider)
        path = template_path or _TEMPLATE_PATH
        with open(path, encoding="utf-8") as f:
            self.templates = yaml.safe_load(f)

    def _generate_one(self) -> GeneratedExample:
        scenarios = self.templates["scenarios"]
        noetic_phrases = self.templates["noetic_phrases"]
        domain_phrases = self.templates["domain_phrases"]
        drive_phrases = self.templates["drive_phrases"]

        # Choose complexity: 40% single state, 40% two-state same-domain,
        # 20% two-state domain descent.
        roll = self.rng.random()
        if roll < 0.4:
            noetic = self.rng.choice(self.NOETICS)
            domain = self.rng.choice(self.DOMAINS)
            drive = self.rng.choice(self.DRIVES)
            expression = f"^{noetic}^{domain}_{{F{drive}}}"
            states = [(noetic, domain)]
        elif roll < 0.8:
            domain = self.rng.choice(self.DOMAINS)
            n1 = self.rng.choice(self.NOETICS)
            n2 = self.rng.choice([n for n in self.NOETICS if n != n1])
            drive = self.rng.choice(self.DRIVES)
            expression = f"^{n1}^{domain}_{{F{drive}}} * ^{n2}^{domain}_{{F{drive}}}"
            states = [(n1, domain), (n2, domain)]
        else:
            # Domain descent P > C > E > O
            d1_idx = self.rng.randint(0, 2)
            d2_idx = self.rng.randint(d1_idx + 1, 3)
            d1, d2 = self.DOMAINS[d1_idx], self.DOMAINS[d2_idx]
            n1 = self.rng.choice(self.NOETICS)
            n2 = self.rng.choice(self.NOETICS)
            drive = self.rng.choice(self.DRIVES)
            expression = f"^{n1}^{d1}_{{F{drive}}} -> ^{n2}^{d2}_{{F{drive}}}"
            states = [(n1, d1), (n2, d2)]

        scenario = self.rng.choice(scenarios)
        prompt = f"{scenario} is asked to give their perspective."

        # Build response from noetic + domain + drive phrases for first state
        noetic_key = str(states[0][0]) if str(states[0][0]) in noetic_phrases else states[0][0]
        np = self.rng.choice(noetic_phrases[noetic_key])
        dp = self.rng.choice(domain_phrases[states[0][1]])
        drv_key = drive if drive in drive_phrases else str(drive)
        drp = self.rng.choice(drive_phrases[drv_key])
        response_parts = [f"{scenario} {np}, {dp}, {drp}."]

        for noetic, domain in states[1:]:
            noetic_key2 = str(noetic) if str(noetic) in noetic_phrases else noetic
            np2 = self.rng.choice(noetic_phrases[noetic_key2])
            dp2 = self.rng.choice(domain_phrases[domain])
            response_parts.append(f"They also {np2}, {dp2}.")

        response = " ".join(response_parts)

        return GeneratedExample(
            prompt=prompt,
            response=response,
            cas_expression=expression,
            scores=self._scores_from_states(states),
            register_labels=[],
            omega_labels=[],
            production_target=None,
            bucket=self.BUCKET,
            is_valid=True,
            violation_type=None,
            distance_to_valid=0.0,
        )
