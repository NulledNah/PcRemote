@echo off
title PcRemote Server v2
echo.
echo ==================================================
echo   PcRemote Server v2 - Experimental Windows Build
echo ==================================================
echo.

cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3 is not installed or not in PATH.
    echo         Download from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)

if not exist "pcremote\" (
    echo [ERROR] pcremote package not found. Run from the companion/ directory.
    pause
    exit /b 1
)

echo [INFO] Installing dependencies...
pip install -r requirements.txt -r requirements-windows.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [INFO] Starting PcRemote Server...
echo.
python server.py %*

pause
