"""The validation error must never echo a credential back to the caller.

Observed in production: a bootstrap attempt with a malformed ``api_credential`` came back as
``detail[0].input`` containing the credential itself, because FastAPI's default handler includes
the offending input for every error. Anything that records a response — a proxy, browser
devtools, an error tracker, a screenshot while debugging — then holds the credential.

These tests use dummy values on purpose. They assert two things at once:

* the credential value never appears in the response, and
* validation itself is unchanged: same status, same error types, same locations.
"""

from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from api.errors import REDACTED, redacted_validation_errors
from api.main import app

# Deliberately fake. These values must never be real credentials, and the point of the test is
# that they do not come back in the response.
DUMMY_SHORT_CREDENTIAL = "casak_" + "A" * 10          # too short: the pattern needs 43+
DUMMY_BAD_PREFIX = "notacasak_" + "B" * 60            # wrong prefix
DUMMY_MISMATCHED = "casak_" + "C" * 60 + "!"          # illegal character


def _assert_no_dummy_value(test: unittest.TestCase, body: str, *values: str) -> None:
    for value in values:
        test.assertNotIn(value, body, "a submitted credential value was echoed in the response")


class ValidationRedactionTests(unittest.TestCase):
    def test_bootstrap_does_not_echo_a_short_credential(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/accounts/bootstrap",
                json={"email_or_username": "someone@example.com",
                      "api_credential": DUMMY_SHORT_CREDENTIAL},
                headers={"X-Account-Bootstrap-Secret": "irrelevant-for-validation"},
            )
        self.assertEqual(response.status_code, 422)
        _assert_no_dummy_value(self, response.text, DUMMY_SHORT_CREDENTIAL)
        self.assertIn(REDACTED, response.text)

    def test_bootstrap_does_not_echo_a_bad_prefix(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/accounts/bootstrap",
                json={"email_or_username": "someone@example.com",
                      "api_credential": DUMMY_BAD_PREFIX},
                headers={"X-Account-Bootstrap-Secret": "irrelevant-for-validation"},
            )
        self.assertEqual(response.status_code, 422)
        _assert_no_dummy_value(self, response.text, DUMMY_BAD_PREFIX)

    def test_redeem_does_not_echo_the_credential_or_the_code(self) -> None:
        dummy_code = "invite-code-that-must-not-be-echoed"
        with TestClient(app) as client:
            response = client.post(
                "/accounts/invite/redeem",
                json={"code": dummy_code, "email_or_username": "someone@example.com",
                      "api_credential": DUMMY_MISMATCHED},
            )
        self.assertEqual(response.status_code, 422)
        # `code` is short enough to be valid, so the credential is the field that fails. The
        # point is that neither value comes back.
        _assert_no_dummy_value(self, response.text, DUMMY_MISMATCHED, dummy_code)

    def test_validation_verdict_is_unchanged(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/accounts/bootstrap",
                json={"email_or_username": "someone@example.com",
                      "api_credential": DUMMY_SHORT_CREDENTIAL},
                headers={"X-Account-Bootstrap-Secret": "irrelevant-for-validation"},
            )
        detail = response.json()["detail"]
        self.assertEqual(len(detail), 1)
        error = detail[0]
        # Same error type, same location, same constraint information as before the change.
        self.assertEqual(error["type"], "string_too_short")
        self.assertEqual(error["loc"], ["body", "api_credential"])
        self.assertIn("min_length", error.get("ctx", {}))
        self.assertEqual(error["input"], REDACTED)

    def test_non_sensitive_inputs_are_still_reported(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/accounts/bootstrap",
                json={"email_or_username": "x" * 400, "api_credential": "casak_" + "D" * 60},
                headers={"X-Account-Bootstrap-Secret": "irrelevant-for-validation"},
            )
        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertEqual(detail[0]["loc"], ["body", "email_or_username"])

    def test_handler_redacts_every_sensitive_field_name(self) -> None:
        class FakeValidationError(Exception):
            def errors(self):  # noqa: ANN201
                return [
                    {"type": "string_too_short", "loc": ("body", "api_credential"), "input": "secret-1"},
                    {"type": "string_too_short", "loc": ("body", "password"), "input": "secret-2"},
                    {"type": "string_too_short", "loc": ("body", "code"), "input": "secret-3"},
                    {"type": "string_too_short", "loc": ("body", "mint_secret"), "input": "secret-4"},
                    {"type": "string_too_short", "loc": ("body", "email_or_username"), "input": "visible"},
                ]

        redacted = redacted_validation_errors(FakeValidationError())  # type: ignore[arg-type]
        for item in redacted[:4]:
            self.assertEqual(item["input"], REDACTED)
        self.assertEqual(redacted[4]["input"], "visible")

    def test_response_body_contains_no_credential_shaped_string(self) -> None:
        # A belt-and-braces check: nothing in the serialised error may look like a credential.
        with TestClient(app) as client:
            response = client.post(
                "/accounts/invite/redeem",
                json={"code": "c", "email_or_username": "someone@example.com",
                      "api_credential": "casak_" + "E" * 50},
            )
        body = json.dumps(response.json())
        self.assertNotIn("casak_", body)
        self.assertNotIn("E" * 50, body)


if __name__ == "__main__":
    unittest.main()
