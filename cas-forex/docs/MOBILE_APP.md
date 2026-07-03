# CAS Forex Mobile App / APK Deployment

## Fastest path — install on your phone right now (verified 2026-07-01)

With the two servers running on the PC (`cas-forex-api` on 8765 and
`cas-forex-mobile` on 4173 — both defined in `.claude/launch.json`), on a phone
connected to the **same Wi-Fi**:

1. Open **`http://10.0.0.6:4173`** in the phone browser
   (10.0.0.6 is this PC's Wi-Fi address; if it ever changes, run `ipconfig`
   and use the new "Wireless LAN adapter Wi-Fi" IPv4 address).
2. Install it:
   - **Android (Chrome/Edge)**: menu (⋮) → **Add to Home screen** / **Install app**.
   - **iPhone (Safari)**: Share → **Add to Home Screen**.
3. Done. The icon opens CAS Forex full-screen like a native app.

No API URL setup is needed on this path: port 4173 serves the built app AND
proxies `/api/forex/*` to the backend on the same origin (verified: manifest,
service worker controlling the page, API healthy through the proxy, zero
horizontal overflow at 375px phone width). The phone must be able to reach the
PC (same Wi-Fi / VPN), and the PC firewall must allow inbound TCP 4173/8765 on
the private network.

Port 4173 is the **installable production build** (fast first paint, offline
app shell). Port 5174 is the developer server (live reload) — usable from the
phone too, but it does not register the service worker, so installs from 5174
are plain bookmarks. Rebuild the production app after UI changes with
`cd ui && npm run build`, then restart `cas-forex-mobile`.

---

CAS Forex can run on a phone in two layers. The phone app exposes the owner-controlled cockpit; it does not bypass the backend runtime gates:

1. **Installable web app (PWA) — ready now.**
   - Android Chrome / Edge: open the cockpit URL, then **Add to Home screen** / **Install app**.
   - iPhone Safari: open the cockpit URL, then **Share → Add to Home Screen**.
   - This uses `ui/public/manifest.webmanifest`, generated app icons, and the
     service worker generated at build time by `vite-plugin-pwa` (`dist/sw.js`).

2. **Android APK wrapper — scaffolded with Capacitor.**
   - Uses the same React cockpit and bundles `ui/dist` into an Android WebView.
   - Config: `ui/capacitor.config.json`.
   - Requires Android Studio/JDK and Capacitor packages/tooling installed before the APK can be built.

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

From the repo root:

```bash
cd cas-forex
PYTHONPATH=.pydeps:. python3 -m uvicorn api.server:app --host 0.0.0.0 --port 8765
```

Then from another terminal, find your WSL/PC LAN IP:

```bash
hostname -I
```

If Windows Firewall blocks the phone, allow inbound TCP `8765` only on your private network.

## Run the mobile/PWA UI for phone install

From the repo root:

```bash
cd cas-forex/ui
npm run mobile:pwa
npm run mobile:preview
```

Open this on the phone:

```text
http://<YOUR-PC-LAN-IP>:5174
```

Then install it from the browser menu.

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

Then build:

```bash
npm run mobile:pwa
```

The in-app Settings override still takes priority after the user saves an API URL.

## APK path with Capacitor

Prereqs on the machine building the APK:

- Node/npm already working for `cas-forex/ui`
- Android Studio installed
- Android SDK installed
- JDK installed
- Capacitor CLI and Android platform packages available

One-time setup, from `cas-forex/ui`:

```bash
npm install --save-dev @capacitor/cli
npm install @capacitor/core @capacitor/android
npx cap add android
```

Sync web assets into Android:

```bash
npm run mobile:apk:sync
```

Build debug APK:

```bash
npm run mobile:apk:debug
```

Expected output path after Gradle succeeds:

```text
cas-forex/ui/android/app/build/outputs/apk/debug/app-debug.apk
```

Install on a connected Android phone:

```bash
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

## Notes for live-money use from phone

- The APK/PWA can expose controls, evidence, settings, and gates.
- Broker/payment movement still requires configured backend credentials and owner enable flags.
- If the app shows fixture data, the phone cannot reach the API. Fix the API base URL in Settings.
- For provider APIs and frontier LLMs, store API keys on the backend/config side, not in the phone UI.
