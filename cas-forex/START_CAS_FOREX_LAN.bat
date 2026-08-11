@echo off
rem ============================================================
rem  CAS Forex - LAN/mobile start
rem  Starts or reuses the backend API (:8765) and installable app
rem  preview (:4173), waits for them, then writes mobile readiness
rem  evidence under evidence_runs\mobile_stack\latest.
rem
rem  Other devices are still refused until Owner Access LAN mode is
rem  ON and the phone is paired with the owner token/link.
rem ============================================================
cd /d "%~dp0"

set "CAS_FOREX_PYTHON=%CAS_FOREX_PYTHON%"
if "%CAS_FOREX_PYTHON%"=="" set "CAS_FOREX_PYTHON=python"

echo Starting/reusing CAS Forex mobile stack...
"%CAS_FOREX_PYTHON%" scripts\run_mobile_stack_readiness.py
if errorlevel 1 (
  echo.
  echo Mobile stack readiness failed. Check evidence_runs\mobile_stack\latest logs.
  pause
  exit /b 1
)

echo.
echo On this PC   : http://localhost:4173/?page=quick-start
set "CAS_FOREX_PHONE_QUICK_START=http://YOUR-WIFI-IP:4173/?page=quick-start"
for /f "usebackq delims=" %%I in (`"%CAS_FOREX_PYTHON%" -c "import json, pathlib; p=pathlib.Path('evidence_runs/mobile_stack/latest/mobile_release_readiness.json'); data=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}; phone=(data.get('phone_quick_start_url') or '').strip(); base=(data.get('web_base') or '').strip().rstrip('/'); print(phone or ((base + '/?page=quick-start') if base else ''))" 2^>nul`) do if not "%%I"=="" set "CAS_FOREX_PHONE_QUICK_START=%%I"
echo On your phone: %CAS_FOREX_PHONE_QUICK_START%
echo                If that URL does not load, use the LAN URL shown in Owner Access
echo                or run ipconfig and use the Wi-Fi IPv4 address.
echo.
echo Pair from Owner Access: turn LAN mode ON, then use the pairing link
echo or enter the token.
echo.
echo Starting a phone-proof watcher in a separate window...
echo Watcher command:
echo   "%CAS_FOREX_PYTHON%" scripts\watch_mobile_phone_proof.py --timeout-seconds 600 --exit-code-on-missing
start "CAS Forex Phone Proof Watcher" cmd /k ""%CAS_FOREX_PYTHON%" scripts\watch_mobile_phone_proof.py --timeout-seconds 600 --exit-code-on-missing"
echo.
echo When the phone opens Quick Start over LAN, the watcher should report VERIFIED.
echo.
start http://localhost:4173/?page=quick-start
