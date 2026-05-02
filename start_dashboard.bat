@echo off
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
set "PYTHON=C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe"
set "URL=http://127.0.0.1:8088"
set "HIDDEN=0"
if /i "%~1"=="--hidden" set "HIDDEN=1"

if "%HIDDEN%"=="0" (
    echo ============================================
    echo   RL-MEC Dashboard Server
    echo ============================================
    echo.
    echo This window runs the dashboard server.
    echo Close this window to stop the dashboard server.
    echo.
)

if not exist "%PYTHON%" (
    echo [ERROR] Python not found at %PYTHON%
    if "%HIDDEN%"=="0" pause
    exit /b 1
)

"%PYTHON%" -c "import fastapi, uvicorn" 2>nul
if errorlevel 1 (
    if "%HIDDEN%"=="0" echo Installing dependencies...
    "%PYTHON%" -m pip install fastapi uvicorn --quiet
)

if "%HIDDEN%"=="0" (
    echo Starting server at %URL% ...
    echo Press Ctrl+C or close this window to stop.
    echo.
    echo Opening browser after server starts...
)
start "" "%ComSpec%" /c timeout /t 2 /nobreak ^>nul ^& start "" "%URL%"

"%PYTHON%" "%SCRIPT_DIR%serve_dashboard.py" --experiments-dir "C:\Users\22003\paper2\paper2\experiments" --results-dir "C:\Users\22003\paper2\paper2\results" --figures-dir "C:\Users\22003\paper2\paper2\figures" --backup-scan-dir "C:\Users\22003\paper2\paper2" --logs-dir "C:\Users\22003\paper2\paper2\logs" --benchmark-json "C:\Users\22003\paper2\paper2\results\benchmark.json" --host 127.0.0.1 --port 8088

if "%HIDDEN%"=="0" (
    echo.
    echo Server stopped. Press any key to close.
    pause >nul
)
