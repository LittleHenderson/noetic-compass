"""Deterministic Q4 interface example. No neural model and no measured learning."""
import json

from learner_q4_representation import Bottleneck, R0NearestNeighbor, encode_observation, token_row_sum
from learner_q4_decoder import TOKENS, ast_to_tokens, free_decode


def main():
    first = encode_observation("(^2^C + ^3^C)")
    second = encode_observation("(^3^C + ^2^C)")
    control = R0NearestNeighbor(((first, "left2-right3"), (second, "left3-right2")))
    fixture = {"node": "StateLiteral", "operator": "^2", "domain": "C", "drive": None}
    scripted_tokens = ast_to_tokens(fixture)

    def scripted_fixture_only(_vector, generated):
        # This intentionally scripted source is NOT a model or an evaluation.
        desired = scripted_tokens[len(generated)]
        return tuple(1.0 if index == desired else 0.0 for index in range(len(TOKENS)))

    result = free_decode(Bottleneck((0.0,)), scripted_fixture_only)
    print(json.dumps({
        "engineering_status": "DETERMINISTIC_INTERFACE_DEMO",
        "representation_status": "NEURAL_NOT_EXECUTED",
        "operation_status": "NOT_IMPLEMENTED_IN_T14",
        "benefit_status": "NOT_EVALUATED",
        "r0_same_bag_collision": token_row_sum(first) == token_row_sum(second),
        "ordered_input_distinguishes_pair": first != second,
        "r0_ambiguous_training_positions": control.predict(second).tied_training_positions,
        "decoder": {"mechanism": "SCRIPTED_FIXTURE_NOT_A_LEARNED_RESULT",
                    "outcome": result.outcome, "ast": result.ast, "steps": result.steps},
    }, indent=2))


if __name__ == "__main__":
    main()
