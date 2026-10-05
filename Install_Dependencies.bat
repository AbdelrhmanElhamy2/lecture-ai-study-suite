@echo off
title Install LectureAI Dependencies
cd /d "%~dp0"

echo ========================================================
echo       LectureAI - Installing Python Dependencies
echo ========================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found on your system PATH!
    echo Please install Python 3.10 or newer from https://www.python.org/
    echo Make sure to check "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo Python detected:
python --version
echo.
echo Installing required packages from requirements.txt...
echo.
pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  [SUCCESS] All dependencies installed successfully!
    echo  You can now double-click "Launch_LectureAI.bat" to start.
    echo ========================================================
) else (
    echo.
    echo [ERROR] Encountered an error installing packages.
)

echo.
pause
