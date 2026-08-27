@echo off
TITLE ESCAPE THE ROOM: THE FINAL 60 - HOST SERVER
COLOR 0A
cls

echo ============================================================
echo   ESCAPE THE ROOM: "THE FINAL 60" — EVENT CONTROL SYSTEM
echo ============================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.9+ and try again.
    pause
    exit /b 1
)

if not exist venv (
    echo [1/3] Creating Python Virtual Environment...
    python -m venv venv
)

echo [2/3] Activating virtual environment & installing dependencies...
call venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt

echo [3/3] Starting Escape Room Host Server...
echo.
python app.py

pause
