@echo off
rem ============================================================
rem  CAS Forex - one-click start (owner-friendly)
rem  Starts the backend API (:8765) and the installable app (:4173).
rem  Safe to double-click twice: a second copy of a server that is
rem  already running just exits on the port conflict.
rem ============================================================
cd /d "%~dp0"

echo Starting CAS Forex backend (port 8765)...
start "CAS Forex API" /min C:\Python314\python.exe -m uvicorn api.server:app --host 0.0.0.0 --port 8765

echo Starting CAS Forex app server (port 4173)...
start "CAS Forex App" /min cmd /c "npm --prefix ui run preview -- --host 0.0.0.0 --port 4173"

timeout /t 6 >nul
echo.
echo  On this PC   : http://localhost:4173
echo  On your phone: http://10.0.0.6:4173   (same Wi-Fi; if the PC's
echo                 Wi-Fi address changed, run: ipconfig)
echo.
start http://localhost:4173
