import os
import unittest
from unittest.mock import patch

from helm_quantum.admission import admit_offline_fixture
from helm_quantum.backends.offline import OfflineBackend
from helm_quantum.wire import ContractError


class BackendTest(unittest.TestCase):
    def test_capabilities_and_estimate_do_not_claim_readiness(self):
        backend = OfflineBackend()
        problem = admit_offline_fixture().problem()
        self.assertFalse(backend.capabilities().submit_available)
        estimate = backend.estimate(problem)
        self.assertIsNone(estimate["qubits"])
        self.assertIsNone(estimate["quote"])

    def test_every_mode_and_fake_grant_refused_without_network(self):
        backend = OfflineBackend()
        with patch("socket.socket", side_effect=AssertionError("network attempted")):
            for mode in ("disabled", "shadow", "research"):
                problem = admit_offline_fixture(mode=mode).problem()
                for grant in (None, True, {"approved": True}, "TRUSTED_GRANT"):
                    with self.subTest(mode=mode, grant=grant), self.assertRaisesRegex(ContractError, "SUBMISSION_REFUSED"):
                        backend.submit(problem, grant)

    def test_environment_does_not_grant_authority(self):
        with patch.dict(os.environ, {"Q1_APPROVED": "1", "Q1_VENUE": "aws"}):
            with self.assertRaises(ContractError):
                OfflineBackend().submit(None, {"budget": 10})

    def test_compile_poll_cancel_decode_refuse_honestly(self):
        backend = OfflineBackend()
        problem = admit_offline_fixture().problem()
        for call in (lambda: backend.compile(problem), lambda: backend.poll("fake"),
                     lambda: backend.cancel("fake"), lambda: backend.decode(problem, {"valid": True})):
            with self.assertRaises(ContractError):
                call()
