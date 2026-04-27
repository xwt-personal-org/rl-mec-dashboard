@echo off
chcp 65001 >nul
set "PYTHON=C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [ERROR] Python not found at %PYTHON%
    pause
    exit /b 1
)

"%PYTHON%" -c "import fastapi, uvicorn" 2>nul
if errorlevel 1 (
    "%PYTHON%" -m pip install fastapi uvicorn --quiet
)

set "CHROME="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

if defined CHROME (
    start "" "%CHROME%" --new-window "http://127.0.0.1:8088"
) else (
    start http://127.0.0.1:8088
)

"%PYTHON%" "C:\Users\22003\paper2\web_dashboard\serve_dashboard.py" --logs-dir "C:\Users\22003\paper2\paper2\logs" --benchmark-json "C:\Users\22003\paper2\paper2\results\benchmark.json" --host 127.0.0.1 --port 8088