@echo off
chcp 65001 >nul
echo ============================================
echo   RL-MEC Dashboard Server
echo ============================================
echo.
echo This window runs the dashboard server.
echo Close this window to stop all background processes.
echo.
set "PYTHON=C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [ERROR] Python not found at %PYTHON%
    pause
    exit /b 1
)

"%PYTHON%" -c "import fastapi, uvicorn" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    "%PYTHON%" -m pip install fastapi uvicorn --quiet
)

echo Starting server at http://127.0.0.1:8088 ...
echo Press Ctrl+C or close this window to stop.
echo.

set "CHROME="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

if defined CHROME (
    echo Opening Chrome...
    "%CHROME%" --new-window "http://127.0.0.1:8088"
) else (
    echo Chrome not found, using default browser...
    start http://127.0.0.1:8088
)

"%PYTHON%" "C:\Users\22003\paper2\web_dashboard\serve_dashboard.py" --logs-dir "C:\Users\22003\paper2\paper2\logs" --benchmark-json "C:\Users\22003\paper2\paper2\results\benchmark.json" --host 127.0.0.1 --port 8088

echo.
echo Server stopped. Press any key to close.
pause >nul
