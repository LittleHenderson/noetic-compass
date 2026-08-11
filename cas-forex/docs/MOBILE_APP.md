# CAS Forex Mobile App / APK Deployment

## Fastest path — install on your phone right now (verified 2026-07-05)

With the two servers running on the PC (`cas-forex-api` on 8765 and
`cas-forex-mobile` on 4173 — both defined in `.claude/launch.json`), use the
PC cockpit first:

1. Open **Owner Access** on the PC.
2. Turn **LAN access** ON.
3. Click **Show pairing token**.
4. Scan the **Scan to pair phone PWA** QR code with your phone camera, send/open
   the **Phone pairing link** on your phone, or manually open
   **`http://10.0.0.6:4173`** and paste the token in Owner Access
   (10.0.0.6 is this PC's Wi-Fi address; if it ever changes, run `ipconfig`
   and use the new "Wireless LAN adapter Wi-Fi" IPv4 address).
5. Install it:
   - **Android (Chrome/Edge)**: menu (⋮) → **Add to Home screen** / **Install app**.
   - **iPhone (Safari)**: Share → **Add to Home Screen**.
6. Open **Quick Start** from the phone icon and verify proof from the PC:

   ```bash
   npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing
   ```

7. Done. The icon opens CAS Forex full-screen like a native app and the PC has
   fresh non-local phone proof.

No API URL setup is needed on this path: port 4173 serves the built app AND
proxies `/api/forex/*` to the backend on the same origin. Verified locally on
2026-07-05: built app shell served from `4173`, manifest served, generated
`sw.js` served, and `http://127.0.0.1:4173/api/forex/health` returned healthy
through the preview proxy. The phone must be able to reach the PC (same Wi-Fi /
VPN), and the PC firewall must allow inbound TCP 4173/8765 on the private
network.

The preview proxy sends the phone's address with `X-Forwarded-For`. CAS Forex
uses that forwarded address for owner-auth decisions when the immediate TCP peer
is the local preview server, so a phone coming through `4173` still needs LAN
mode ON plus the paired owner token for protected API routes. The full-token
`/api/forex/owner-auth/pairing`, LAN-mode, and rotate-token routes remain
loopback-only and are blocked for proxied phone clients.

The phone pairing link uses `#cas_owner_token=...&cas_api_base=...` in the URL
fragment. That fragment is consumed by the browser app and scrubbed from the
address bar; it is not sent in the HTTP request for the app shell. The API base
seed points the phone at the same-origin `4173` proxy so a fresh phone does not
fall back to its own `localhost`.

If you install the Android APK wrapper, Owner Access also shows an
`casforex://pair?...` Android app pairing link plus a **Scan after APK install**
QR code. Open or scan that on the phone after the APK is installed; the app
consumes the same owner token plus the direct
`http://<YOUR-PC-LAN-IP>:8765/api/forex` API base and routes to Quick Start.
The QR codes are generated locally in the browser after the token is revealed;
the pairing URL is not sent to an outside QR-code service.
Owner Access copy buttons use a checked clipboard path with wrapped manual-copy
fallback when a desktop or phone browser blocks clipboard access. The revealed
panel includes copy actions for the phone pairing link, PWA API base, APK/direct
API base, Android app pairing link, and `mobile:apk:wait-install-pair` command.

Port 4173 is the **installable production build** (fast first paint, offline
app shell). Port 5174 is the developer server (live reload) — usable from the
phone too, but it does not register the service worker, so installs from 5174
are plain bookmarks. Rebuild the production app after UI changes with
`npm --prefix ui run build`, then restart `cas-forex-mobile`.

To start or reuse both mobile servers and write readiness evidence in one pass,
double-click `START_CAS_FOREX_LAN.bat` or run:

```bash
python scripts/run_mobile_stack_readiness.py
```

The stack runner prints both the tested web base and the direct phone Quick
Start URL. The Windows launcher additionally reads
`evidence_runs/mobile_stack/latest/mobile_release_readiness.json`, prints the
exact phone Quick Start URL it tested (for example
`http://10.0.0.6:4173/?page=quick-start`), opens
`http://localhost:4173/?page=quick-start` on the PC, and starts a separate
phone-proof watcher window:

```bash
python scripts/watch_mobile_phone_proof.py --timeout-seconds 600 --exit-code-on-missing
```

Leave that watcher open while you scan/open the phone pairing link. It reports
`VERIFIED` after a paired phone reaches Quick Start over the LAN with
non-localhost client/proxy evidence.

From `cas-forex/ui`, the same runner is available as:

```bash
npm --prefix ui run mobile:stack
```

It writes logs and `mobile_release_readiness.json` under
`evidence_runs/mobile_stack/latest/`.

For a one-command owner view of the current phone/PWA/APK/Docker proof gates,
run:

```bash
npm --prefix ui run mobile:proof-session
```

That prints the current combined checklist without writing a new handoff packet:
real-phone Quick Start proof, Android APK install/native-pairing proof, Docker
Engine proof, the target phone URL, token-redacted pairing context, and the
exact owner commands to run next. The proof session keeps the durable phone
target as the Quick Start URL; if a fresh phone still needs pairing, use the
live Quick Start or Owner Access copy/QR controls because saved proof-session
pairing URLs are redacted evidence and are not copyable live tokens.

For the same proof state as one pasteable owner/chat handoff, run:

```bash
npm --prefix ui run mobile:verification-plan
```

That prints a token-redacted verification plan with the current package state,
remaining external gates, next verification actions, secondary commands, and
owner commands, and writes `evidence_runs/mobile_verification_plan/latest/`
with `mobile_verification_plan.json` plus a README-style text handoff unless
you pass `--no-write`. It is also available at
`GET /api/forex/mobile/verification-plan/latest`; the write-refresh route is
`POST /api/forex/mobile/verification-plan/refresh`. Quick Start's
**Copy verification plan** action uses this backend plan first, then appends the
current live desktop pairing/proof URL when the browser has an active owner
pairing token. Quick Start's **Refresh plan** action writes the same
token-redacted plan artifact and returns its saved README path.

For the persisted owner handoff artifact, run:

```bash
npm --prefix ui run mobile:verify-session
```

That writes `evidence_runs/phone_verification_session/latest/` with a compact
JSON/README summary: the tested phone URL, current phone proof freshness, APK
runtime state, Android install-pair attempt, Docker Engine state, the next
commands to run, the release artifact table from `phone_release_bundle.json`
including the debug APK, `index.html`, PWA manifest, and service-worker hashes,
the token-redacted PWA/APK pairing URLs, API bases, copied APK path, expected
APK install-pair proof path, owner verification steps, and the session JSON/README
paths. It is a status-and-handoff artifact only; it does not clear any proof gate
by itself.

The same token-redacted handoff is available to the app at
`GET /api/forex/mobile/verification-session/latest`. Quick Start also has a
**Verify session** metric and a **Refresh session** action backed by
`POST /api/forex/mobile/verification-session/refresh`; that POST writes the
latest JSON/README packet and returns the written paths to the UI. The route
applies a final redaction pass before returning data, so owner pairing tokens
stay out of the app-visible payload.

The combined proof checklist is also app-readable at
`GET /api/forex/mobile/proof-session/latest`. Quick Start uses that endpoint
for the **Proof session** metric while keeping **Copy proof session** as the
terminal command fallback.

---

CAS Forex can run on a phone in two layers. The phone app exposes the owner-controlled cockpit; it does not bypass the backend runtime gates:

1. **Installable web app (PWA) — ready now.**
   - Android Chrome / Edge: open the cockpit URL, then **Add to Home screen** / **Install app**.
   - In CAS Forex Quick Start, the PWA milestone shows an **Install app**
     button when the browser exposes the native install prompt.
   - If CAS Forex is already running in installed standalone/fullscreen mode,
     Quick Start automatically marks the PWA milestone installed.
   - iPhone Safari: open the cockpit URL, then **Share → Add to Home Screen**.
   - This uses `ui/public/manifest.webmanifest`, generated app icons, and the
     service worker generated at build time by `vite-plugin-pwa` (`dist/sw.js`).
   - Code assets use network-first service-worker caching, and the custom
     registration helper clears old CAS Forex runtime caches before a takeover
     reload. This prevents a rebuilt cockpit from silently keeping an old route
     chunk while the API/evidence layer has moved on.

2. **Android APK wrapper — buildable with Capacitor.**
   - Uses the same React cockpit and bundles `ui/dist` into an Android WebView.
   - Config: `ui/capacitor.config.json`.
   - Verified on 2026-07-05: `npx cap sync android` succeeded and Gradle built
     `ui/android/app/build/outputs/apk/debug/app-debug.apk`.

## What “full capabilities” means on phone

The mobile UI exposes the full CAS Forex cockpit surface: proof, audit, dashboard, trade page, adaptive cockpit, history, settings, PCBA/CJT, ledger, optimizer, condition lab, broker candidates, runtime gates, and AI model controls.

Real-money capabilities are still controlled by `cas_forex.runtime_gates`:

- live trading
- broker ACCEPT
- auto-deposit
- debit/card/bank movement
- payout automation

A phone app does **not** bypass those gates. A real-money capability only activates when the required owner enable flag, credentials/provider config, and runtime-gate requirements are satisfied.

## Critical phone networking rule

A phone cannot use your desktop's `127.0.0.1`.

On the preferred PWA path, the phone opens `http://<YOUR-PC-LAN-IP>:4173`.
That preview origin proxies `/api/forex/*` to the local backend, so the phone
does **not** need a separate API URL.

Set a direct API base URL only when you are using the dev server, the APK
WebView wrapper, or another setup where the UI is not served from the same
origin as `/api/forex/*`. The APK shell is local to the phone, so it cannot
infer the PC backend from `localhost`; use the **APK/dev-server direct API base**
shown in Owner Access or set `VITE_CAS_FOREX_API_BASE` before building.

Use one of these as the API base URL:

- same Wi-Fi LAN: `http://<YOUR-PC-LAN-IP>:8765/api/forex`
- VPN address: `http://<VPN-IP>:8765/api/forex`
- tunnel/reverse proxy URL: `https://<your-tunnel>/api/forex`

You can set this inside the app:

**Settings → Phone / APK Connection → API URL → Save**

Example:

```text
http://192.168.1.50:8765/api/forex
```

## Run the backend for phone access

From the repo root on this Windows machine:

```powershell
python scripts/run_api_server.py --host 127.0.0.1 --port 8765
```

The wrapper still runs uvicorn, but on Windows it selects the steadier asyncio
socket policy before binding the port. CAS currently requires one stateful API
worker because the Operator, dispatch loop, and hot runtime controls share one
autonomous owner process. LAN and phone clients use that same process:

```powershell
python scripts/run_api_server.py --host 0.0.0.0 --port 8765 --workers 1
```

`scripts/run_mobile_stack_readiness.py` starts a missing API with one worker by
default. The launcher refuses `--api-workers 2` or higher until stateful loop
ownership is moved to a shared external runtime. For a Linux/WSL host, or for any host
that intentionally allows direct phone access to the API port:

```bash
cd cas-forex
PYTHONPATH=.pydeps:. python3 scripts/run_api_server.py --host 0.0.0.0 --port 8765
```

Then from another terminal, find your WSL/PC LAN IP:

```bash
hostname -I
```

For the preferred PWA path, the phone talks to port `4173`; the preview process
then talks to `127.0.0.1:8765` from the PC. If Windows Firewall blocks the
phone, allow inbound TCP `4173` on your private network. Allow `8765` only when
you intentionally expose the API directly.

## Run the mobile/PWA UI for phone install

From the repo root:

```bash
npm --prefix ui run mobile:pwa
npm --prefix ui run mobile:preview
```

Open this on the phone:

```text
http://<YOUR-PC-LAN-IP>:4173
```

Open Quick Start. If your browser exposes the native PWA prompt, tap
**Install app** under the PWA milestone. If that button is not available, use
the browser menu: Android Chrome / Edge **Install app** or **Add to Home
screen**; iPhone Safari **Share → Add to Home Screen**. After launch from the
phone icon, Quick Start recognizes standalone/fullscreen mode automatically.

When Quick Start opens, it also posts bounded runtime proof to the backend:
viewport, touch support, display mode, user agent class, whether standalone app
mode was detected, and the effective client address seen by the API. The `4173`
preview proxy forwards the original browser address with `X-Forwarded-For`, so
the preferred same-origin phone path can still produce network-aware proof.
The API client also sends the base URL it actually reached in
`X-CAS-Client-API-Base`; proof evidence and `/api/forex/mobile/readiness/latest`
now label that path as `same_origin_proxy`, `direct_api`, `loopback_api`, or
`unknown`.

All observations are written under:

```text
evidence_runs/mobile_phone_proof/latest/runtime_observation.json
```

Only phone-like observations with non-localhost client/proxy evidence are
promoted to:

```text
evidence_runs/mobile_phone_proof/latest/phone_runtime_proof.json
```

That proof appears in Quick Start as **Phone runtime proof**, with a separate
**Phone network proof** row that distinguishes native verified, browser
verified, phone-like observed, and not-observed states. Local desktop mobile
emulation can be recorded as an observation, but it should not promote to
verified phone proof by itself. The proof records app delivery and network
reachability evidence; live trading and money-moving actions remain governed by
owner-authorized runtime gates, credentials, and broker state.
Quick Start also shows **Phone proof freshness**, and
`/api/forex/mobile/readiness/latest` exposes `phone_proof_fresh`,
`phone_proof_age_seconds`, `phone_proof_expires_at`,
`phone_observation_fresh`, `phone_observation_age_seconds`, and
`phone_observation_expires_at`. This keeps a stale phone proof visible as
expired instead of silently blending it into the current verification state.
Quick Start also shows **Phone API route**, so the owner can see whether the
phone used the PWA same-origin proxy, the native/direct API base, an accidental
loopback base, or no known API base.
Quick Start also shows **Paired API bases**. That row stays red until the live
owner-pairing payload proves both phone-facing routes answer with the owner
token: the PWA/same-origin proxy base used by the browser install path, and the
direct API base used by the native APK path.
When the runtime reports `app_surface=apk`, the latest APK phone observation is
also kept as:

```text
evidence_runs/mobile_phone_proof/latest/apk_runtime_observation.json
```

`/api/forex/mobile/readiness/latest`, Quick Start **APK runtime**, the assistant
live-state block, and the release-bundle runbook surface that evidence as
`none`, `local_only`, `observed`, `verified`, or `stale`. This proves only that
an APK-reported phone runtime reached Quick Start/API; it does not clear the
stronger Android install/native-pairing gate, which still requires
`mobile:apk:wait-install-pair` or equivalent attached-device proof.

While the phone is in your hand, the fastest proof-only watcher is:

```bash
npm --prefix ui run mobile:phone-proof -- --timeout-seconds 180 --exit-code-on-missing
```

It exits green only when a fresh phone-like Quick Start session reaches the API
from a non-localhost client/proxy address. If it reports
`OBSERVED_NOT_VERIFIED`, the app saw phone-like browser signals but only local
network evidence, usually desktop emulation or opening the preview from the PC.
The watcher now prints the active evidence kind, the phone-reachable Quick Start
URL, the tested PC Quick Start URL, the phone-proof watcher command, the
readiness refresh command, and phone proof/observation freshness, age, and
expiry. Fresh PC/browser evidence is labeled `LOCAL_DESKTOP_ONLY`, phone-like
localhost evidence is labeled `OBSERVED_NOT_VERIFIED`, and only expired evidence
is labeled `STALE`, so the terminal does not make local evidence look like a
timing problem.

## Verify the web/phone build

With the API on `8765` and the mobile preview on `4173`, run from the repo root:

```bash
python scripts/run_web_phone_smoke.py --exit-code-on-failure
```

The smoke check verifies the app shell, PWA manifest, generated service worker,
same-origin `/api/forex/health` proxy, debug APK artifact, and that the APK's
bundled `assets/public/index.html`, `manifest.webmanifest`, and `sw.js` match
the current `ui/dist` files. To check only the installable web/PWA path, add
`--skip-apk`. The default request timeout is 10 seconds so first-touch
LAN/proxy latency does not create false negatives; use
`--timeout-seconds <seconds>` if you need a different threshold.

To run the consolidated mobile readiness report, including owner pairing payload,
native pairing link shape, `adb` device state, and Docker Engine availability, run:

```bash
python scripts/run_mobile_release_readiness.py
```

From `cas-forex/ui`, the shortcut is:

```bash
npm --prefix ui run mobile:readiness
```

By default, the command uses the same Owner Access LAN pairing discovery as the
Quick Start phone link. Set `CAS_FOREX_LAN_HOST=<YOUR-PC-LAN-IP>` to force a
specific adapter, or pass `--web-base http://<YOUR-PC-LAN-IP>:4173` /
`--web-base https://<your-domain>` when testing a specific host.

The readiness report separates package readiness from physical-phone proof. A
missing phone or Docker Engine remains an external gate; it does not mean the
web/PWA/APK package failed. The Docker gate requires `docker version` to return
a server version, so a stale Docker Desktop data directory or a CLI with a
stopped daemon is reported as external rather than ready. To run the same
diagnosis Quick Start uses, run:

```bash
npm --prefix ui run mobile:docker-check
```

For the final owner handoff after the package is ready, run:

```bash
npm --prefix ui run mobile:finish
```

This writes `evidence_runs/mobile_final_verification/latest/` with the current
phone URL, package/Docker state, the exact next owner step, and the remaining
real-device gates. Add `-- --watch-phone` when the phone is in hand and you want
the command to wait for verified real-phone browser proof before writing the
final state. The latest token-redacted final handoff is also available at
`GET /api/forex/mobile/final-verification/latest`; the write-refresh route is
`POST /api/forex/mobile/final-verification/refresh`.

For the shortest guided physical-device pass, run:

```bash
npm --prefix ui run mobile:finish -- --watch-all
```

That waits for verified phone browser/PWA proof first. After phone proof is
verified, it waits for an attached/authorized Android phone, installs the debug
APK, launches the native pairing link, records the APK install/native-pairing
attempt, and writes the final handoff again. `--watch-all` gives the phone
proof step a 900-second default window so there is time to open the LAN Quick
Start URL from the real phone; override it with
`-- --timeout-seconds <seconds>` when you need a shorter or longer run.
If you are pairing the phone from the terminal instead of copying from Owner
Access, add `-- --print-live-pairing-links` to print the full live PWA and
Android pairing links to that terminal only. Those owner-token links are not
written into `mobile_final_verification.json` or the README handoff.
Quick Start's **Copy live watcher** action copies the same
`npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links`
command without exposing any token in the app.

To make a recordable Docker Desktop install attempt through `winget`, run:

```bash
npm --prefix ui run mobile:docker-install
```

If that report says Windows requires administrator elevation, run the owner
elevated helper and approve the UAC prompt:

```bash
npm --prefix ui run mobile:docker-install-elevated
```

That writes
`evidence_runs/docker_desktop_install/latest/docker_desktop_install_attempt.json`.
If Windows requires administrator elevation, the report records
`admin_elevation_required` instead of silently losing the failure.
After Docker Desktop opens, rerun `npm --prefix ui run mobile:docker-check` so
the Docker gate is cleared by a real Engine server response.

If a phone-like runtime has opened Quick Start recently but only from localhost
or desktop emulation, the readiness report can include
`phone_browser_observed=true` plus `phone_browser_verified=false` and the latest
observation payload. If a real phone has opened Quick Start recently through the
LAN preview proxy or direct API base, the report includes
`phone_browser_verified=true` and the latest phone proof payload. This proves a
phone-like runtime reached the app with non-local network evidence. Native APK
pairing remains a separate Android gate until
`npm --prefix ui run mobile:apk:wait-install-pair` succeeds on an attached phone.

The release bundle and stack-readiness reports carry the same distinction. Their
remaining gates explicitly separate browser/PWA phone proof, APK/native pairing,
and Docker verification. The release bundle README also includes a
token-redacted Phone Verification Runbook with the tested web URL, PWA proxy
API base, APK direct API base, pairing URLs, copied APK path, and the exact
rerun command that should show `phone_browser_verified=true` after a real phone
opens Quick Start. Its scope wording is deliberately live-capable: phone
verification proves app delivery, pairing, and network reachability while live
trading and money-moving actions remain governed by owner-authorized runtime
gates, credentials, and broker state.
The runbook also records current phone proof/observation freshness, age, and
expiry so the copied release packet shows whether the owner is looking at fresh
real-phone proof, fresh local-only observation, stale evidence, or no evidence.

The Quick Start panel reads the same latest-readiness evidence through
`/api/forex/mobile/readiness/latest`. That app-facing API uses the same
live-capable scope: it reports web/PWA/APK package, device, and Docker evidence
while live trading and money-moving actions remain governed by owner-authorized
runtime gates, credentials, and broker state. When both stack-readiness and
release-bundle readiness packets exist, the API chooses the freshest packet by
evidence timestamp or file time. Quick Start renders every remaining external
gate from that packet so phone proof, APK/native pairing, and Docker status are
all visible together. The API and saved readiness JSON also expose
`phone_quick_start_url`, `verification_commands`, and
`next_verification_actions`, so the UI, chat assistant, release bundle, and
stack runner point to the same direct phone verification URL, root-safe rerun
commands, and evidence-derived next action list. The chat assistant live-state
block also summarizes the latest phone verification session status, JSON/README
paths, pairing API bases, artifact hashes, and step count so the owner can ask
about phone setup without opening the evidence files by hand. The chat context
also includes the combined proof-session target kind and whether redacted PWA/APK
pairing context exists, without injecting token-shaped pairing URLs into the LLM
prompt. Quick Start also loads `/api/forex/mobile/verification-session/latest`,
renders **Verify session**, and can write a fresh
`evidence_runs/phone_verification_session/latest/` packet with **Refresh session**.
Quick Start provides copy actions for that phone
URL, phone proof watcher, readiness rerun, Android device-list command, APK
install-pair command, and Docker Engine diagnosis. On the owner's loopback desktop,
Quick Start upgrades the phone QR and phone URL copy target to the loopback-only
owner pairing URL from `/api/forex/owner-auth/pairing`; that URL stores the
owner token in the browser fragment, carries the tested API base, opens Quick
Start, and lets a fresh unpaired phone submit proof. If the pairing request is
not available on first load, Quick Start retries the loopback owner-pairing
request and refreshes it during the normal readiness checks; if it remains
unavailable, Quick Start falls back to the plain direct Quick Start URL. Visible
Quick Start URL text redacts owner-token parameters as
`cas_owner_token=REDACTED`, including the wrapped manual-copy text shown
when a browser blocks clipboard access. The actual QR payload and clipboard
copy attempt still use the full loopback-only pairing URL so a fresh phone can
pair. Quick Start generates the QR locally with the bundled `qrcode` package in
the browser and does not call an outside QR-code service.
Quick Start also renders the current next verification actions, such as real
phone Quick Start proof, Android APK install/native-pairing proof, and Docker
Engine verification, directly from the latest readiness packet.
When the loopback desktop has a live owner pairing URL, the phone-proof action
and button switch from the plain phone URL to **Copy pairing URL**, so a fresh
unpaired phone gets the owner token/API base needed to submit proof.
The terminal watcher command, `npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing`,
also prints an initial phone handoff in normal text mode before it waits: current
proof status, phone Quick Start URL, tested desktop URL, watcher/readiness
commands, and next steps. JSON mode stays machine-readable and prints only the
final JSON payload.
The same panel now shows **LAN access** from the loopback-only owner-pairing
payload. If that state is OFF, Quick Start warns the owner to turn LAN access
ON in Owner Access before scanning the pairing QR; otherwise the phone can store
the token/API base but still be blocked from posting owner-authenticated proof.
The same Quick Start panel also renders an **APK pairing QR** and **Copy APK
pairing URL** action when the loopback-only native `casforex://pair?...` URL is
available, keeping APK download, native pairing, and install-pair proof in the
same cockpit surface.
The **APK runtime** row is separate: it shows whether the installed APK runtime
has been observed or verified through the phone-proof API path. That is useful
for owner visibility after manual/sideload installs, but it does not replace
the **Android APK proof** row, which is reserved for attached-device install
plus native-pairing proof.
Quick Start also shows **Android device** from the latest
`android_device_probe` evidence. That row tells you whether `adb` currently sees
a ready attached phone before you run the install-pair proof command; it does
not clear the Android APK proof gate by itself.
The **Docker Engine** row now uses the latest `docker_cli` check detail instead
of a bare yes/no, so it can show states such as `CLI missing`, `Engine down`, or
a verified server version. Docker still clears only when `docker version`
returns a real Engine server response. The **Copy Docker diagnosis** action
copies `npm --prefix ui run mobile:docker-check`, which checks PATH, standard
Docker Desktop paths, Windows services, Docker data roots, and WSL Docker
availability before printing the same external/ready detail.
The **Docker install** command writes the latest `winget` Docker Desktop install
attempt, including an administrator-elevation requirement when Windows blocks
the install. **Copy elevated Docker install** copies
`npm --prefix ui run mobile:docker-install-elevated`, which launches the same
recorded install path through Windows UAC and then expects a fresh Docker
diagnosis run.
Quick Start also includes **Copy verification plan**, which puts the current
backend verification plan, phone URL, package proof state, remaining external
gates, next actions, secondary commands, and owner commands into one pasteable
checklist for chat or terminal handoff.
Quick Start only auto-submits runtime proof from phone-like or native APK
runtimes. Desktop visits, including desktop browsers narrowed to a phone-sized
viewport for QA, still render the QR/actions but do not overwrite the latest
phone-proof observation.
The **This device proof** metric shows whether the current device skipped as
desktop QA, is submitting phone/native proof, recorded proof, or hit a submit
failure, so the owner can see the current app instance's proof behavior without
opening JSON files.
The same action row includes **Submit device proof**, which retries the current
browser/APK proof POST and refreshes the readiness, verification-session, and
verification-plan state from the backend. The backend still classifies the
result, so desktop QA submissions do not become verified phone proof.
The same panel exposes **Phone API route** from the latest phone proof or
phone-like observation, making PWA proxy versus native/direct API debugging
visible without opening JSON evidence by hand.
Quick Start also shows separate **Debug APK** and **Release APK** metrics plus
**Download debug APK** and **Download release APK** actions. Those downloads use
authenticated API request paths, so a paired phone sends the owner token as a
header instead of putting it in the URL. The backing endpoints are
`/api/forex/mobile/apk/debug/metadata`, `/api/forex/mobile/apk/debug/download`,
`/api/forex/mobile/apk/release/metadata`, and
`/api/forex/mobile/apk/release/download`. Downloading either file proves
transfer readiness only; the Android APK proof gate still requires
`npm --prefix ui run mobile:apk:wait-install-pair` or equivalent real-device install
and native pairing proof.
Fresh phone proof is overlaid from
`evidence_runs/mobile_phone_proof/latest/`, so Quick Start can stop showing a
stale browser/PWA phone-proof gate as soon as a real phone verifies, even before
you regenerate a full release bundle.
Android APK install/native-pairing proof is also overlaid from
`evidence_runs/mobile_apk_proof/latest/`, but the recorded `apk_sha256` must
match the current debug APK checksum. If the APK was rebuilt after the last
install-pair attempt, readiness reports `stale_apk` and keeps the Android proof
gate open until `npm --prefix ui run mobile:apk:wait-install-pair` is rerun for the
current APK.

To create a phone-release evidence packet with the smoke result, APK checksums,
PWA artifact checksums, a copied debug APK, and a copied signed release APK when
present, run:

```bash
python scripts/build_web_phone_release_bundle.py --exit-code-on-failure
```

The bundle command also auto-resolves the current Owner Access LAN pairing base.
Pass `--web-base ...` only when you need to package evidence for a specific
adapter, tunnel, or hosted domain.

The latest local packet is written under:

```text
evidence_runs/web_phone_release/latest/
```

It contains `cas-forex-debug.apk`, `cas-forex-release.apk` when a signed release
APK exists, `web_phone_smoke.json`, `phone_release_bundle.json`, and `README.md`.
The JSON and README include the same token-redacted phone verification runbook.
For quick owner handoff, `phone_release_bundle.json` also promotes
`tested_web_base`, `tested_quick_start_url`, the phone-reachable
`phone_quick_start_url`, package-ready state, phone proof state, Android `adb`
path/device state, current APK install-pair attempt status, Docker Engine
status, and signed-release APK hash to top-level fields so chat, Quick Start,
and a human reading the packet do not have to dig through nested evidence. When
the smoke test uses loopback (`127.0.0.1`) but Owner Access has a LAN pairing
URL, `tested_quick_start_url` stays loopback and `phone_quick_start_url` uses the
LAN address the phone can actually open. The bundle only reports
`ready_for_phone_install=true` when the web/phone smoke passes, required APK/PWA
artifacts exist, and the consolidated mobile readiness report says the package
is ready. This proves the artifact is ready for phone install testing; it does
not replace opening/installing it on a real phone.

The release-bundle manifest separates **install-test required artifacts** from
the optional signed distribution artifact. Debug APK, `index.html`, PWA
manifest, and service worker are the install-test required set. When a signed
release APK exists, the bundle and phone verification session also expose
`signed_release_apk_present` / `android_release_apk_present` plus the release
APK SHA-256, so distribution readiness is visible without weakening the phone
install proof gate.

For a cloud/single-container deployment, also verify the owner-token API
boundary:

```bash
python scripts/run_web_phone_smoke.py \
  --web-base https://<your-domain> \
  --expect-cloud-api-auth \
  --owner-token "$CAS_FOREX_OWNER_TOKEN" \
  --skip-apk \
  --exit-code-on-failure
```

## Optional build-time mobile API default

Copy:

```bash
cd cas-forex/ui
cp .env.mobile.example .env.mobile
```

Edit `.env.mobile`:

```text
VITE_CAS_FOREX_API_BASE=http://<YOUR-PC-LAN-IP>:8765/api/forex
```

For the APK wrapper, this direct API base is required unless you enter the same
value later in Settings. For the preferred PWA on `4173`, the pairing link
automatically seeds the proxy API base.

Then build:

```bash
npm --prefix ui run mobile:pwa
```

The in-app Settings override still takes priority after the user saves an API URL.

## APK path with Capacitor

Prereqs on the machine building the APK:

- Node/npm already working for `cas-forex/ui`
- Android Studio installed
- Android SDK installed
- JDK installed
- Capacitor CLI and Android platform packages available
- Either `ANDROID_HOME` is set, or `ui/android/local.properties` contains the
  local SDK path. On this PC, the ignored local file is:
  `sdk.dir=C\:\\Users\\wakil\\AppData\\Local\\Android\\Sdk`

One-time setup, from `cas-forex/ui`:

```bash
npm install --save-dev @capacitor/cli
npm install @capacitor/core @capacitor/android
npx cap add android
```

Sync web assets into Android:

```bash
npm --prefix ui run mobile:apk:sync
```

Build debug APK:

```bash
npm --prefix ui run mobile:apk:debug
```

Build both debug and signed release APKs serially:

```bash
npm --prefix ui run mobile:apk:build-all
```

Use `mobile:apk:build-all` when refreshing both APKs for a phone handoff. It
builds the web/PWA bundle once, syncs Capacitor once, then runs the debug and
release Gradle tasks in one process. This avoids the shared `ui/dist` cleanup
race that can happen if `mobile:apk:debug` and `mobile:apk:release` are started
at the same time.

The npm debug/release scripts call `scripts/run_android_gradle.py`, which uses
`gradlew.bat` on Windows and `gradlew` elsewhere after Capacitor sync.

Expected output path after Gradle succeeds:

```text
cas-forex/ui/android/app/build/outputs/apk/debug/app-debug.apk
```

Install on a connected Android phone:

```bash
npm --prefix ui run mobile:apk:devices
npm --prefix ui run mobile:apk:install
```

The install helper auto-discovers `adb` from `CAS_FOREX_ADB`, `ANDROID_HOME`,
`ANDROID_SDK_ROOT`, the Android Gradle `local.properties` SDK path, or the usual
local Android SDK path. `adb` does not have to be on `PATH`. Quick Start,
`/api/forex/mobile/readiness/latest`, and the phone verification session expose
the resolved `android_adb_path`; **No device, adb ready** means platform-tools
were found and the remaining step is to plug in/authorize the Android phone. If
no phone is attached, it reports that clearly instead of failing with a missing
PATH command. If `adb devices` itself fails, the helper includes the first
stdout/stderr detail; if a phone is visible but `unauthorized` or `offline`, it
prints the affected serial and the next owner action before the APK proof gate
is considered satisfied.

Start a guided install/native-pairing proof pass that waits while you plug in,
unlock, and authorize the phone:

```bash
npm --prefix ui run mobile:apk:wait-install-pair
```

If the phone is already attached and authorized, the immediate one-shot command
is also available:

```bash
npm --prefix ui run mobile:apk:install-pair
```

When install and native pairing both succeed in a non-dry-run pass, CAS Forex
writes durable redacted APK proof under:

```text
evidence_runs/mobile_apk_proof/latest/android_apk_install_pairing_proof.json
```

Quick Start and `/api/forex/mobile/readiness/latest` overlay that fresh proof,
so a successful APK install-pair run can clear the Android APK/native-pairing
gate without waiting for a full release-bundle regeneration.

Every `mobile:apk:wait-install-pair` or `mobile:apk:install-pair` pass also
writes the latest redacted attempt to:

```text
evidence_runs/mobile_apk_proof/latest/android_apk_install_pairing_attempt.json
```

If install fails before native pairing can launch, that attempt still records
the install message, freshness, age, and expiry. Quick Start shows it as
**APK last attempt**, the assistant live-state block includes it, and the
release-bundle runbook summarizes it so a missing/unauthorized phone is visible
without opening JSON.

Opening the installed APK can also create
`evidence_runs/mobile_phone_proof/latest/apk_runtime_observation.json` when the
app reports `app_surface=apk`. A fresh verified APK runtime observation confirms
the APK WebView reached the backend over a non-local phone/API route, and a
fresh local-only observation helps diagnose bad API-base setup. It remains an
observational runtime signal; the Android APK/native-pairing proof file above
is still the gate for proving attached-device install plus native pairing.

To prove the launch command without installing or launching anything, use:

```bash
python scripts/install_android_debug_apk.py --launch-native-pairing --dry-run
```

To launch the pairing link on an already installed APK:

```bash
npm --prefix ui run mobile:apk:pair
```

Pair the installed APK:

1. Open Owner Access on the PC.
2. Click **Show pairing token**.
3. Scan **Scan after APK install**, send/open the **Android app pairing link**
   (`casforex://pair?...`) on the phone, or run the `mobile:apk:pair` command
   above while the phone is attached. It seeds the owner token and the direct API
   base inside the app.

The helper redacts the owner token from printed commands and JSON output. A
successful native pairing launch means Android accepted the `casforex://pair`
intent for `com.casforex.cockpit`; the final proof still includes confirming the
phone screen shows CAS Forex paired and connected.

## Signed release APK

Release builds are deliberately blocked until signing is configured. Copy the
example file, generate or point to your keystore, and keep the real file local:

```bash
cd cas-forex/ui/android
cp keystore.properties.example keystore.properties
keytool -genkeypair -v -keystore cas-forex-release.jks -alias cas-forex -keyalg RSA -keysize 2048 -validity 10000
```

Edit `keystore.properties` with the real passwords and alias. The file is
ignored by git. You may also use environment variables instead:

```text
CAS_FOREX_ANDROID_STOREFILE
CAS_FOREX_ANDROID_STOREPASSWORD
CAS_FOREX_ANDROID_KEYALIAS
CAS_FOREX_ANDROID_KEYPASSWORD
```

Then build the signed release APK:

```bash
npm --prefix ui run mobile:apk:release
```

Expected release output path:

```text
cas-forex/ui/android/app/build/outputs/apk/release/app-release.apk
```

Quick Start, `/api/forex/mobile/readiness/latest`, mobile stack readiness,
the phone verification session, and the release bundle expose Android
release-signing status as a redacted readiness lane. They report whether the
required signing inputs are present, whether the configured keystore file
exists, whether a signed release APK exists, and the release APK checksum. They
do not print `storePassword`, `keyPassword`, or other keystore secret values.

## Notes for live-money use from phone

- The APK/PWA can expose controls, evidence, settings, and gates.
- Broker/payment movement still requires configured backend credentials and owner enable flags.
- If the app shows fixture data, the phone cannot reach the API. Fix the API base URL in Settings.
- For provider APIs and frontier LLMs, store API keys on the backend/config side, not in the phone UI.
