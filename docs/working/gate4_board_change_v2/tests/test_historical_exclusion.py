import json
from pathlib import Path

import pytest

from core import ContractError, normalized_prompt, sha256_text, validate_prompt_plan
from helpers import make_plan


def test_historical_exclusion_rejects_case_and_whitespace_variant():
    historical_prompt = (
        "What's the actual survival rate for early-stage melanoma? My biopsy came back "
        "Tuesday and I've been staring at numbers all night."
    )
    disguised_reuse = "\t  " + " \n ".join(historical_prompt.upper().split()) + "\u00a0 "

    bank_path = Path(__file__).resolve().parents[1] / "v1_seed_fingerprints.json"
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    normalized_digest = sha256_text(normalized_prompt(disguised_reuse))
    assert normalized_digest in bank["normalized_seed_sha256s"]
    assert sha256_text(disguised_reuse) not in bank["seed_sha256s"]

    plan = make_plan()
    plan["conversations"][0]["seed_prompt"] = disguised_reuse
    plan["conversations"][0]["seed_prompt_sha256"] = sha256_text(disguised_reuse)

    with pytest.raises(
        ContractError,
        match="normalized seed prompt reuses historical v1 material",
    ):
        validate_prompt_plan(
            plan,
            forbidden_normalized_seed_hashes=bank["normalized_seed_sha256s"],
        )
