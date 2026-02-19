@echo off
title CMC AI Setup
color 0B

echo.
echo  =============================================================
echo   CMC AI Setup  ^|  Ollama Model Installer
echo  =============================================================
echo.

:: ── Check Ollama ─────────────────────────────────────────────
where ollama >nul 2>&1
if errorlevel 1 (
    echo  [!] Ollama is not installed on this system.
    echo.
    echo      Download from: https://ollama.com/download
    echo      After installing, run this script again.
    echo.
    pause
    exit /b 1
)
echo  [OK] Ollama found.
echo.

:: ── Model menu ───────────────────────────────────────────────
:MENU
echo  Which model do you want to download?
echo.
echo    [1]  llama3.1:8b            Light  ^|  ~5 GB  ^|  Fast, everyday tasks  (default)
echo    [2]  qwen2.5:14b-instruct   Heavy  ^|  ~9 GB  ^|  More capable, better reasoning
echo    [3]  Both models
echo    [4]  Exit
echo.
set /p CHOICE="  Enter choice (1/2/3/4): "

if "%CHOICE%"=="1" goto PULL_LIGHT
if "%CHOICE%"=="2" goto PULL_HEAVY
if "%CHOICE%"=="3" goto PULL_BOTH
if "%CHOICE%"=="4" goto END
echo.
echo  [!] Invalid choice. Please enter 1, 2, 3 or 4.
echo.
goto MENU

:: ── Pull light ───────────────────────────────────────────────
:PULL_LIGHT
echo.
echo  -------------------------------------------------------------
echo   Downloading: llama3.1:8b  (~5 GB)
echo  -------------------------------------------------------------
echo.
ollama pull llama3.1:8b
if errorlevel 1 (
    echo.
    echo  [!] Download failed. Check your connection and try again.
    echo.
) else (
    echo.
    echo  [OK] llama3.1:8b ready.
)
goto DONE_MSG

:: ── Pull heavy ───────────────────────────────────────────────
:PULL_HEAVY
echo.
echo  -------------------------------------------------------------
echo   Downloading: qwen2.5:14b-instruct  (~9 GB)
echo  -------------------------------------------------------------
echo.
ollama pull qwen2.5:14b-instruct
if errorlevel 1 (
    echo.
    echo  [!] Download failed. Check your connection and try again.
    echo.
) else (
    echo.
    echo  [OK] qwen2.5:14b-instruct ready.
)
goto DONE_MSG

:: ── Pull both ────────────────────────────────────────────────
:PULL_BOTH
echo.
echo  -------------------------------------------------------------
echo   Downloading: llama3.1:8b  (~5 GB)
echo  -------------------------------------------------------------
echo.
ollama pull llama3.1:8b
if errorlevel 1 (
    echo  [!] llama3.1:8b download failed.
) else (
    echo  [OK] llama3.1:8b ready.
)

echo.
echo  -------------------------------------------------------------
echo   Downloading: qwen2.5:14b-instruct  (~9 GB)
echo  -------------------------------------------------------------
echo.
ollama pull qwen2.5:14b-instruct
if errorlevel 1 (
    echo  [!] qwen2.5:14b-instruct download failed.
) else (
    echo  [OK] qwen2.5:14b-instruct ready.
)
goto DONE_MSG

:: ── Done ─────────────────────────────────────────────────────
:DONE_MSG
echo.
echo  =============================================================
echo   Setup complete.
echo  =============================================================
echo.
echo   Switch models inside CMC:
echo     ai-model set llama3.1:8b
echo     ai-model set qwen2.5:14b-instruct
echo.
echo   Make sure Ollama is running before using "ai" commands.
echo.
:END
pause
