@echo off
rem ============================================================
rem  CAS Forex - LAN start (reach it from your phone)
rem  Starts the backend API (:8765) and the app (:4173) on the
rem  network (0.0.0.0) so another device on the same Wi-Fi can
rem  reach them. Other devices are STILL refused until you:
rem    1) turn LAN mode ON in the cockpit's Owner Access panel, and
rem    2) pair the device with the token shown there.
rem  Your own PC (loopback) always works with no token.
rem ============================================================
cd /d "%~dp0"

echo Starting CAS Forex backend (port 8765, LAN)...
start "CAS Forex API" /min C:\Python314\python.exe -m uvicorn api.server:app --host 0.0.0.0 --port 8765

echo Starting CAS Forex app server (port 4173, LAN)...
start "CAS Forex App" /min cmd /c "npm --prefix ui run preview -- --host 0.0.0.0 --port 4173"

timeout /t 6 >nul
echo.
echo  On this PC   : http://localhost:4173
echo  On your phone: http://%COMPUTERNAME%:4173  (or the PC's Wi-Fi IP
echo                 from 'ipconfig'). Then pair from the Owner Access
echo                 panel: turn LAN mode ON and enter the token.
echo.
start http://localhost:4173
