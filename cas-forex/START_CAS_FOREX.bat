@echo off
rem ============================================================
rem  CAS Forex - one-click start (owner-friendly, LOOPBACK)
rem  Starts the backend API (:8765) and the installable app (:4173)
rem  bound to THIS PC only (127.0.0.1). Nothing on your network can
rem  reach it. This is the safe default.
rem
rem  Want it on your phone? Run START_CAS_FOREX_LAN.bat instead,
rem  then pair the phone from the cockpit (Owner Access panel).
rem  Safe to double-click twice: a second copy just exits on the
rem  port conflict.
rem ============================================================
cd /d "%~dp0"

echo Starting CAS Forex backend (port 8765, this PC only)...
start "CAS Forex API" /min C:\Python314\python.exe scripts\run_api_server.py --host 127.0.0.1 --port 8765 --workers 1

echo Starting CAS Forex app server (port 4173, this PC only)...
start "CAS Forex App" /min cmd /c "npm --prefix ui run preview -- --host 127.0.0.1 --port 4173"

timeout /t 6 >nul
echo.
echo  On this PC   : http://localhost:4173
echo  On your phone: run START_CAS_FOREX_LAN.bat, then pair from the
echo                 cockpit's Owner Access panel.
echo.
start http://localhost:4173
