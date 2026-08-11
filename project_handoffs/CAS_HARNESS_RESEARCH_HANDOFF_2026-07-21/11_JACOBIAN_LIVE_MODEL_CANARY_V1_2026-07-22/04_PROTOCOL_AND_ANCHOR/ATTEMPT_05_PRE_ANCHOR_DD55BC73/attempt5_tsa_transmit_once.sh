#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="/workspace/cas-jlcv1-official-f72b89cd-dd55bc73"
CONTROL="${ROOT}/control"
OPERATOR="${ROOT}/operator"
QUERY="${CONTROL}/jacobian_lens_canary_v1_anchor_request.tsq"
RESPONSE="${CONTROL}/jacobian_lens_canary_v1_anchor_response.tsr"
HEADERS="${CONTROL}/jacobian_lens_canary_v1_anchor_response_headers.txt"
STARTED="${OPERATOR}/TSA_TRANSMISSION_STARTED.json"
FINISHED="${OPERATOR}/TSA_TRANSMISSION_FINISHED.json"
CURL_STDERR="${OPERATOR}/TSA_TRANSMISSION_CURL.stderr.txt"
CURL_STATUS="${OPERATOR}/TSA_TRANSMISSION_CURL.status.txt"
FAILURE_BODY="${OPERATOR}/TSA_TRANSMISSION_FAILED_RESPONSE_BODY.bin"
FAILURE_HEADERS="${OPERATOR}/TSA_TRANSMISSION_FAILED_RESPONSE_HEADERS.txt"

EXPECTED_QUERY_BYTES="104"
EXPECTED_QUERY_SHA256="e73850302dc31015af2cd5624eed70d445ef553a7de9acca640d5ba9cca9a846"
EXPECTED_RUN_ID="jlcv1-rfc3161-dd55bc73ab446ccc794d26c2aeaa2eec2b0997d1384db9752e0f7615d804c380"
ENDPOINT="http://timestamp.digicert.com"
CURL="/usr/bin/curl"

test -d "${CONTROL}"
test -d "${OPERATOR}"
test -f "${QUERY}"
test -x "${CURL}"
test "$(stat -c %s "${QUERY}")" = "${EXPECTED_QUERY_BYTES}"
test "$(sha256sum "${QUERY}" | awk '{print $1}')" = "${EXPECTED_QUERY_SHA256}"

for path in \
  "${RESPONSE}" \
  "${HEADERS}" \
  "${STARTED}" \
  "${FINISHED}" \
  "${CURL_STDERR}" \
  "${CURL_STATUS}" \
  "${FAILURE_BODY}" \
  "${FAILURE_HEADERS}"; do
  test ! -e "${path}"
done

test -z "$(
  pgrep -af \
    'run_jacobian_lens_canary_v1_seccomp|run_jacobian_lens_canary_v1.py|jacobian_lens_canary_v1.py' \
    || true
)"
test -z "$(find "${ROOT}/output" -mindepth 1 -maxdepth 1 -print -quit)"
test -z "$(find "${ROOT}/runlog" -mindepth 1 -maxdepth 1 -print -quit)"
test -z "$(find "${ROOT}/environment_post" -mindepth 1 -maxdepth 1 -print -quit)"

publish_once() {
  local source="$1"
  local destination="$2"
  test -f "${source}"
  test ! -e "${destination}"
  chmod 0400 "${source}"
  ln "${source}" "${destination}"
  sync
  rm "${source}"
  sync
}

STARTED_TMP="${OPERATOR}/.tsa-transmission-started.$$.tmp"
BODY_TMP="${OPERATOR}/.tsa-response-body.$$.tmp"
HEADERS_TMP="${OPERATOR}/.tsa-response-headers.$$.tmp"
STDERR_TMP="${OPERATOR}/.tsa-curl-stderr.$$.tmp"
STATUS_TMP="${OPERATOR}/.tsa-curl-status.$$.tmp"
FINISHED_TMP="${OPERATOR}/.tsa-transmission-finished.$$.tmp"

trap 'rm -f "${STARTED_TMP}" "${BODY_TMP}" "${HEADERS_TMP}" "${STDERR_TMP}" "${STATUS_TMP}" "${FINISHED_TMP}"' EXIT

: > "${BODY_TMP}"
: > "${HEADERS_TMP}"
: > "${STDERR_TMP}"
: > "${STATUS_TMP}"

STARTED_AT_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STARTED_UNIX_MS="$(date -u +%s%3N)"
CURL_SHA256="$(sha256sum "${CURL}" | awk '{print $1}')"
printf '{"attempt":5,"curl_executable":"%s","curl_executable_sha256":"%s","endpoint":"%s","http_redirects_allowed":0,"query_byte_count":104,"query_sha256":"%s","retry_count":0,"run_id":"%s","started_at_utc":"%s","started_unix_ms":%s,"transmission_invocation_count":1}\n' \
  "${CURL}" \
  "${CURL_SHA256}" \
  "${ENDPOINT}" \
  "${EXPECTED_QUERY_SHA256}" \
  "${EXPECTED_RUN_ID}" \
  "${STARTED_AT_UTC}" \
  "${STARTED_UNIX_MS}" \
  > "${STARTED_TMP}"
publish_once "${STARTED_TMP}" "${STARTED}"

set +e
"${CURL}" \
  --disable \
  --silent \
  --show-error \
  --http1.1 \
  --noproxy '*' \
  --proto '=http' \
  --max-redirs 0 \
  --retry 0 \
  --connect-timeout 20 \
  --max-time 90 \
  --request POST \
  --header 'Content-Type: application/timestamp-query' \
  --header 'Accept: application/timestamp-reply' \
  --data-binary "@${QUERY}" \
  --dump-header "${HEADERS_TMP}" \
  --output "${BODY_TMP}" \
  --write-out '%{http_code}\n' \
  "${ENDPOINT}" \
  > "${STATUS_TMP}" \
  2> "${STDERR_TMP}"
CURL_EXIT_CODE=$?
set -e

FINISHED_AT_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FINISHED_UNIX_MS="$(date -u +%s%3N)"
HTTP_CODE="$(tr -d '\r\n' < "${STATUS_TMP}")"
BODY_BYTES="$(stat -c %s "${BODY_TMP}")"
BODY_SHA256="$(sha256sum "${BODY_TMP}" | awk '{print $1}')"
HEADERS_BYTES="$(stat -c %s "${HEADERS_TMP}")"
HEADERS_SHA256="$(sha256sum "${HEADERS_TMP}" | awk '{print $1}')"
STDERR_BYTES="$(stat -c %s "${STDERR_TMP}")"
STDERR_SHA256="$(sha256sum "${STDERR_TMP}" | awk '{print $1}')"
QUERY_SHA256_AFTER="$(sha256sum "${QUERY}" | awk '{print $1}')"

SUCCESS="false"
if \
  test "${CURL_EXIT_CODE}" -eq 0 \
  && test "${HTTP_CODE}" = "200" \
  && test "${BODY_BYTES}" -gt 0 \
  && test "${QUERY_SHA256_AFTER}" = "${EXPECTED_QUERY_SHA256}" \
  && tr -d '\r' < "${HEADERS_TMP}" \
    | grep -Eiq '^Content-Type:[[:space:]]*application/timestamp-reply([[:space:]]*;.*)?$'; then
  SUCCESS="true"
  publish_once "${BODY_TMP}" "${RESPONSE}"
  publish_once "${HEADERS_TMP}" "${HEADERS}"
else
  publish_once "${BODY_TMP}" "${FAILURE_BODY}"
  publish_once "${HEADERS_TMP}" "${FAILURE_HEADERS}"
fi

publish_once "${STDERR_TMP}" "${CURL_STDERR}"
publish_once "${STATUS_TMP}" "${CURL_STATUS}"

printf '{"attempt":5,"curl_exit_code":%s,"endpoint":"%s","finished_at_utc":"%s","finished_unix_ms":%s,"http_code":"%s","query_sha256_after":"%s","response_byte_count":%s,"response_headers_byte_count":%s,"response_headers_sha256":"%s","response_sha256":"%s","retry_count":0,"run_id":"%s","stderr_byte_count":%s,"stderr_sha256":"%s","success":%s,"transmission_invocation_count":1}\n' \
  "${CURL_EXIT_CODE}" \
  "${ENDPOINT}" \
  "${FINISHED_AT_UTC}" \
  "${FINISHED_UNIX_MS}" \
  "${HTTP_CODE}" \
  "${QUERY_SHA256_AFTER}" \
  "${BODY_BYTES}" \
  "${HEADERS_BYTES}" \
  "${HEADERS_SHA256}" \
  "${BODY_SHA256}" \
  "${EXPECTED_RUN_ID}" \
  "${STDERR_BYTES}" \
  "${STDERR_SHA256}" \
  "${SUCCESS}" \
  > "${FINISHED_TMP}"
publish_once "${FINISHED_TMP}" "${FINISHED}"

if test "${SUCCESS}" != "true"; then
  printf 'attempt5_tsa_transmission=FAILED_NO_RETRY\n' >&2
  exit 2
fi

printf 'attempt5_tsa_transmission=PASS\n'
printf 'response_byte_count=%s\n' "${BODY_BYTES}"
printf 'response_sha256=%s\n' "${BODY_SHA256}"
printf 'headers_byte_count=%s\n' "${HEADERS_BYTES}"
printf 'headers_sha256=%s\n' "${HEADERS_SHA256}"
