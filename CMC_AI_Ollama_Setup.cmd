@echo off
setlocal
title CMC AI Setup (compat launcher)
set "ROOT=%~dp0"
if exist "%ROOT%CMC_AI_Setup.cmd" (
    call "%ROOT%CMC_AI_Setup.cmd"
) else (
    echo.
    echo  [!] CMC_AI_Setup.cmd was not found next to this script.
    echo      Please re-download/update CMC.
    echo.
    pause
    exit /b 1
)
endlocal
exit /b 0
