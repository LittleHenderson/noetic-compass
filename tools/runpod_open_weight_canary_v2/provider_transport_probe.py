"""Option A' — time the provider transport leg. UNAUTHENTICATED. No side effect.

Gate 1 item 1 needs `observed_provider_stop_execution_milliseconds`. The real
guardian STOP path cannot be reached under `INERT`, and reaching it needs a real
pod to stop, which sits behind Gate 4. See `STOP_MEASUREMENT_OPTIONS_v2.md`.

This measures the transport leg instead: DNS resolution, TLS handshake, and the
HTTP round trip to the exact host, port and path root the guardian uses. It
sends **no credential**, so the provider answers `401` — and that response is
the measurement.

**What makes this safe, and none of it is incidental:**

* No `Authorization` header is ever constructed. There is no code path that
  reads a secret, so none can leak.
* No pod ID appears anywhere. `STOP` targets `/v1/pods/{id}`; this probe touches
  only the collection root, so it cannot address a pod even by accident.
* The method is `GET`. A `401` on a `GET` to a collection root mutates nothing.

**What this is NOT, and must never be reported as:** the guardian executing a
STOP. It excludes the guardian's own dispatch after the activation gate — which
is small, in-process, and already visible in the recovery Lambda's measured
durations — and it excludes everything that requires a real authorisation
against a real pod.

Deployed to preproduction only, at the guardian's exact runtime, architecture,
memory and region, so the network characteristics are comparable.
"""

from __future__ import annotations

import http.client
import json
import socket
import ssl
import time

PROVIDER_HOST = "rest.runpod.io"
PROVIDER_PORT = 443
PROVIDER_ROOT = "/v1/pods"

# The provider must answer with an auth challenge. Anything else means the probe
# did not measure what it claims -- including a success, which would imply a
# credential leaked in from somewhere.
EXPECTED_STATUS = {401, 403}


def _timed_probe() -> dict:
    result: dict = {
        "host": PROVIDER_HOST,
        "port": PROVIDER_PORT,
        "path": PROVIDER_ROOT,
        "method": "GET",
        "authenticated": False,
    }

    t0 = time.perf_counter()
    address = socket.getaddrinfo(PROVIDER_HOST, PROVIDER_PORT, proto=socket.IPPROTO_TCP)[0][4]
    t_dns = time.perf_counter()

    context = ssl.create_default_context()
    raw = socket.create_connection(address, timeout=5)
    t_tcp = time.perf_counter()

    tls = context.wrap_socket(raw, server_hostname=PROVIDER_HOST)
    t_tls = time.perf_counter()

    connection = http.client.HTTPSConnection(PROVIDER_HOST, PROVIDER_PORT, timeout=5)
    connection.sock = tls
    # Deliberately no Authorization header. There is no branch that adds one.
    connection.request("GET", PROVIDER_ROOT, headers={"Accept": "application/json"})
    response = connection.getresponse()
    status = response.status
    response.read(1)  # first byte only; the body is not the measurement
    t_first_byte = time.perf_counter()
    connection.close()

    ceil_ms = lambda a, b: max(1, int((b - a) * 1000 + 0.999))
    result.update(
        {
            "status": status,
            "status_is_auth_challenge": status in EXPECTED_STATUS,
            "dns_milliseconds": ceil_ms(t0, t_dns),
            "tcp_milliseconds": ceil_ms(t_dns, t_tcp),
            "tls_milliseconds": ceil_ms(t_tcp, t_tls),
            "request_to_first_byte_milliseconds": ceil_ms(t_tls, t_first_byte),
            "total_transport_milliseconds": ceil_ms(t0, t_first_byte),
        }
    )
    return result


def handler(event, context):  # noqa: ANN001, ARG001
    """Return one timed transport sample, or the failure that prevented it."""
    try:
        result = _timed_probe()
    except Exception as error:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"{type(error).__name__}: {error}",
            "note": "No measurement. A failed probe is not a zero.",
        }

    if not result["status_is_auth_challenge"]:
        return {
            "ok": False,
            "measurement": result,
            "error": (
                f"status {result['status']} is not an auth challenge. The probe "
                "must be unauthenticated; any other status means it did not "
                "measure what it claims."
            ),
        }
    result["ok"] = True
    result["claim_boundary"] = (
        "Transport leg only: DNS + TLS + HTTP round trip to the provider host. "
        "NOT the guardian executing STOP, and NOT a real authorised STOP against "
        "a real pod."
    )
    return result


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(handler(None, None), indent=2))
