@echo off
title LectureAI Launcher
cd /d "%~dp0"
where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw launcher.py
) else (
    start "" python launcher.py
)
exit
