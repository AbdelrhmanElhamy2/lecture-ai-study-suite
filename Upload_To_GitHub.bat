@echo off
title Upload LectureAI to GitHub
cd /d "%~dp0"

echo ========================================================
echo          LectureAI - Push Repository to GitHub
echo ========================================================
echo.

:: Detect git executable
set "GIT_CMD=git"
git --version >nul 2>&1
if %errorlevel% neq 0 (
    if exist "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\TeamFoundation\Team Explorer\Git\cmd\git.exe" (
        set "GIT_CMD=C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\TeamFoundation\Team Explorer\Git\cmd\git.exe"
    ) else if exist "C:\Program Files\Git\cmd\git.exe" (
        set "GIT_CMD=C:\Program Files\Git\cmd\git.exe"
    ) else (
        echo [ERROR] Git was not found!
        echo Please make sure Git is installed from https://git-scm.com/
        pause
        exit /b 1
    )
)

echo Detected Git:
"%GIT_CMD%" --version
echo.

:: Check current git status
echo Checking repository status...
"%GIT_CMD%" status -s
echo.

:: Prompt for GitHub repository URL
echo Enter your GitHub repository URL:
echo (Example: https://github.com/your-username/lecture-ai-study-suite.git)
echo.
set /p REPO_URL="Repository URL: "

if "%REPO_URL%"=="" (
    echo [ERROR] No URL provided. Aborting.
    pause
    exit /b 1
)

:: Set remote origin
"%GIT_CMD%" remote remove origin >nul 2>&1
"%GIT_CMD%" remote add origin %REPO_URL%
"%GIT_CMD%" branch -M main

echo.
echo Pushing branch 'main' to GitHub...
echo.
"%GIT_CMD%" push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  [SUCCESS] Code successfully pushed to GitHub!
    echo ========================================================
) else (
    echo.
    echo [ERROR] Push failed. If this is a new repository, ensure you have
    echo permissions and follow the GitHub login prompt in your browser.
)

echo.
pause
