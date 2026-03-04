@echo off
setlocal EnableExtensions
title CMC AI Setup
color 0B

set "ROOT=%~dp0"
set "CMC_CFG=%ROOT%src\CMC_Config.json"
set "KEYS_PATH=%USERPROFILE%\.ai_helper\api_keys.json"
set "PS_SET_CFG=%TEMP%\cmc_set_config.ps1"
set "PS_SET_KEY=%TEMP%\cmc_set_api_key.ps1"

call :EnsureFiles
call :EnsureScripts

:MAIN_MENU
cls
echo.
echo  =============================================================
echo   CMC AI Setup
echo  =============================================================
echo.
echo   [1] Quick setup wizard (recommended)
echo   [2] Install Ollama models
echo   [3] Configure backend/API keys
echo   [4] Configure Claude Code model/effort
echo   [5] Show current AI setup
echo   [6] Exit
echo.
set /p CHOICE="  Enter choice (1/2/3/4/5/6): "

if "%CHOICE%"=="1" goto QUICK_WIZARD
if "%CHOICE%"=="2" (call :OLLAMA_MENU & goto MAIN_MENU)
if "%CHOICE%"=="3" (call :BACKEND_MENU & goto MAIN_MENU)
if "%CHOICE%"=="4" (call :CLAUDE_MENU & goto MAIN_MENU)
if "%CHOICE%"=="5" goto SHOW_STATUS
if "%CHOICE%"=="6" goto END
goto MAIN_MENU

:QUICK_WIZARD
cls
echo.
echo  -------------------------------------------------------------
echo   Quick setup
echo  -------------------------------------------------------------
echo.
echo   Pick your primary AI route:
echo     [1] Ollama local (no API key)
echo     [2] Claude Code CLI (no API key)
echo     [3] OpenAI API
echo     [4] Anthropic API
echo     [5] OpenRouter API
echo     [6] Back
echo.
set /p WIZ="  Choice (1/2/3/4/5/6): "

if "%WIZ%"=="1" (
    call :SetConfig "ai.backend" "ollama"
    call :OLLAMA_MENU
    goto MAIN_MENU
)
if "%WIZ%"=="2" (
    call :SetConfig "ai.backend" "claude-code"
    call :CLAUDE_MENU
    goto MAIN_MENU
)
if "%WIZ%"=="3" (
    call :OPENAI_KEY_FLOW
    goto MAIN_MENU
)
if "%WIZ%"=="4" (
    call :API_KEY_FLOW "anthropic" "claude-sonnet-4-6"
    goto MAIN_MENU
)
if "%WIZ%"=="5" (
    call :API_KEY_FLOW "openrouter" "meta-llama/llama-3.1-8b-instruct"
    goto MAIN_MENU
)
goto MAIN_MENU

:OLLAMA_MENU
cls
echo.
echo  -------------------------------------------------------------
echo   Ollama model installer
echo  -------------------------------------------------------------
echo.
where ollama >nul 2>&1
if errorlevel 1 (
    echo   [!] Ollama is not installed.
    echo       Download: https://ollama.com/download
    echo.
    pause
    goto :eof
)
echo   [OK] Ollama found.
echo.
echo   [1] llama3.1:8b
echo   [2] qwen2.5:14b-instruct
echo   [3] Both
echo   [4] Skip install, just set default model
echo   [5] Back
echo.
set /p OCH="  Choice (1/2/3/4/5): "

if "%OCH%"=="1" (
    ollama pull llama3.1:8b
    call :SetConfig "ai.model" "llama3.1:8b"
    call :SetConfig "ai.backend" "ollama"
    goto OLLAMA_DONE
)
if "%OCH%"=="2" (
    ollama pull qwen2.5:14b-instruct
    call :SetConfig "ai.model" "qwen2.5:14b-instruct"
    call :SetConfig "ai.backend" "ollama"
    goto OLLAMA_DONE
)
if "%OCH%"=="3" (
    ollama pull llama3.1:8b
    ollama pull qwen2.5:14b-instruct
    call :SetConfig "ai.model" "llama3.1:8b"
    call :SetConfig "ai.backend" "ollama"
    goto OLLAMA_DONE
)
if "%OCH%"=="4" (
    echo.
    echo   [1] llama3.1:8b
    echo   [2] qwen2.5:14b-instruct
    set /p ODM="  Default model (1/2): "
    if "%ODM%"=="2" (
        call :SetConfig "ai.model" "qwen2.5:14b-instruct"
    ) else (
        call :SetConfig "ai.model" "llama3.1:8b"
    )
    call :SetConfig "ai.backend" "ollama"
    goto OLLAMA_DONE
)
if "%OCH%"=="5" goto :eof
goto OLLAMA_MENU

:OLLAMA_DONE
echo.
echo   [OK] Ollama setup updated.
pause
goto :eof

:BACKEND_MENU
cls
echo.
echo  -------------------------------------------------------------
echo   Backend/API key setup
echo  -------------------------------------------------------------
echo.
echo   [1] OpenAI
echo   [2] Anthropic
echo   [3] OpenRouter
echo   [4] Back
echo.
set /p BCH="  Choice (1/2/3/4): "
if "%BCH%"=="1" (
    call :OPENAI_KEY_FLOW
    goto BACKEND_MENU
)
if "%BCH%"=="2" (
    call :API_KEY_FLOW "anthropic" "claude-sonnet-4-6"
    goto BACKEND_MENU
)
if "%BCH%"=="3" (
    call :API_KEY_FLOW "openrouter" "meta-llama/llama-3.1-8b-instruct"
    goto BACKEND_MENU
)
if "%BCH%"=="4" goto :eof
goto BACKEND_MENU

:OPENAI_KEY_FLOW
call :API_KEY_FLOW "openai" "gpt-5.2"
if errorlevel 1 goto :eof
echo.
echo   OpenAI effort:
echo     [1] default
echo     [2] low
echo     [3] medium
echo     [4] high
set /p OEFF="  Choice (1/2/3/4): "
if "%OEFF%"=="2" (
    call :SetConfig "ai.openai_effort" "low"
) else if "%OEFF%"=="3" (
    call :SetConfig "ai.openai_effort" "medium"
) else if "%OEFF%"=="4" (
    call :SetConfig "ai.openai_effort" "high"
) else (
    call :SetConfig "ai.openai_effort" ""
)
goto :eof

:API_KEY_FLOW
set "BNAME=%~1"
set "DEFAULT_MODEL=%~2"
cls
echo.
echo  -------------------------------------------------------------
echo   %BNAME% setup
echo  -------------------------------------------------------------
echo.
echo   Paste your %BNAME% API key (hidden input is not available in .cmd).
echo   Leave blank to cancel.
echo.
set "API_KEY_INPUT="
set /p API_KEY_INPUT="  Key: "
if not defined API_KEY_INPUT (
    echo.
    echo   [!] Cancelled.
    pause
    exit /b 1
)
set "API_BACKEND=%BNAME%"
call :SaveApiKey
if errorlevel 1 (
    echo.
    echo   [!] Could not save key.
    pause
    exit /b 1
)
call :SetConfig "ai.backend" "%BNAME%"
call :SetConfig "ai.model" "%DEFAULT_MODEL%"
echo.
echo   [OK] Saved key and selected backend/model.
pause
exit /b 0

:CLAUDE_MENU
cls
echo.
echo  -------------------------------------------------------------
echo   Claude Code setup
echo  -------------------------------------------------------------
echo.
where claude >nul 2>&1
if errorlevel 1 (
    where claude.cmd >nul 2>&1
    if errorlevel 1 (
        echo   [!] Claude Code CLI not found in PATH.
        echo       Install Claude Code and re-run this setup.
        echo.
        pause
        goto :eof
    )
)
echo   [OK] Claude CLI found.
echo.
echo   Select model:
echo     [1] default (CLI decides)
echo     [2] claude-haiku-4-5
echo     [3] claude-sonnet-4-6
echo     [4] claude-opus-4-6
set /p CMOD="  Choice (1/2/3/4): "
if "%CMOD%"=="2" (
    call :SetConfig "ai.claude_code_model" "claude-haiku-4-5"
    call :SetConfig "ai.model" "claude-code"
) else if "%CMOD%"=="3" (
    call :SetConfig "ai.claude_code_model" "claude-sonnet-4-6"
    call :SetConfig "ai.model" "claude-code"
) else if "%CMOD%"=="4" (
    call :SetConfig "ai.claude_code_model" "claude-opus-4-6"
    call :SetConfig "ai.model" "claude-code"
) else (
    call :SetConfig "ai.claude_code_model" ""
    call :SetConfig "ai.model" "claude-code"
)
call :SetConfig "ai.backend" "claude-code"

call :ClaudeEffortSupported
if "%CLAUDE_EFFORT_SUPPORTED%"=="1" (
    echo.
    echo   Claude effort:
    echo     [1] default
    echo     [2] low
    echo     [3] medium
    echo     [4] high
    set /p CEFF="  Choice (1/2/3/4): "
    if "%CEFF%"=="2" (
        call :SetConfig "ai.claude_code_effort" "low"
    ) else if "%CEFF%"=="3" (
        call :SetConfig "ai.claude_code_effort" "medium"
    ) else if "%CEFF%"=="4" (
        call :SetConfig "ai.claude_code_effort" "high"
    ) else (
        call :SetConfig "ai.claude_code_effort" ""
    )
) else (
    call :SetConfig "ai.claude_code_effort" ""
    echo.
    echo   [i] This Claude CLI does not expose --effort. Skipping effort setup.
)
echo.
echo   [OK] Claude setup updated.
pause
goto :eof

:SHOW_STATUS
cls
echo.
echo  -------------------------------------------------------------
echo   Current AI setup
echo  -------------------------------------------------------------
echo.
powershell -NoProfile -Command ^
  "$cfgPath = '%CMC_CFG%';" ^
  "$keysPath = '%KEYS_PATH%';" ^
  "$cfg = @{};" ^
  "if (Test-Path $cfgPath) { try { $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json } catch {} };" ^
  "$ai = if ($cfg.ai) { $cfg.ai } else { @{} };" ^
  "$backend = if ($ai.backend) { $ai.backend } else { 'ollama' };" ^
  "$model = if ($ai.model) { $ai.model } else { 'llama3.1:8b' };" ^
  "$ccModel = if ($ai.claude_code_model) { $ai.claude_code_model } else { '(default)' };" ^
  "$ccEff = if ($ai.claude_code_effort -ne $null -and $ai.claude_code_effort -ne '') { $ai.claude_code_effort } else { 'default' };" ^
  "$oaEff = if ($ai.openai_effort -ne $null -and $ai.openai_effort -ne '') { $ai.openai_effort } else { 'default' };" ^
  "$keys = @{};" ^
  "if (Test-Path $keysPath) { try { $obj = Get-Content $keysPath -Raw | ConvertFrom-Json; if ($obj) { $obj.psobject.properties | ForEach-Object { $keys[$_.Name] = $_.Value } } } catch {} };" ^
  "Write-Host ('  Backend:             ' + $backend);" ^
  "Write-Host ('  Model:               ' + $model);" ^
  "Write-Host ('  Claude CLI model:    ' + $ccModel);" ^
  "Write-Host ('  Claude CLI effort:   ' + $ccEff);" ^
  "Write-Host ('  OpenAI effort:       ' + $oaEff);" ^
  "Write-Host ('  OpenAI key saved:    ' + ($(if ($keys.ContainsKey('openai')) { 'yes' } else { 'no' })));" ^
  "Write-Host ('  Anthropic key saved: ' + ($(if ($keys.ContainsKey('anthropic')) { 'yes' } else { 'no' })));" ^
  "Write-Host ('  OpenRouter key saved:' + ($(if ($keys.ContainsKey('openrouter')) { 'yes' } else { 'no' })));"
echo.
pause
goto MAIN_MENU

:EnsureFiles
if not exist "%ROOT%src" (
    echo [!] Could not find src\ folder next to this script.
    echo     Run this script from your CMC folder.
    pause
    exit /b 1
)
if not exist "%CMC_CFG%" (
    >"%CMC_CFG%" (
        echo {
        echo   "batch": false,
        echo   "dry_run": false,
        echo   "ssl_verify": true,
        echo   "ai": {
        echo     "model": "llama3.1:8b",
        echo     "backend": "ollama",
        echo     "claude_code_model": "",
        echo     "claude_code_effort": "",
        echo     "openai_effort": ""
        echo   }
        echo }
    )
)
if not exist "%USERPROFILE%\.ai_helper" mkdir "%USERPROFILE%\.ai_helper" >nul 2>&1
if not exist "%KEYS_PATH%" (
    >"%KEYS_PATH%" echo {}
)
goto :eof

:EnsureScripts
>"%PS_SET_CFG%" (
  echo param([string]$Path,[string]$Key,[string]$Value^)
  echo $utf8NoBom = New-Object System.Text.UTF8Encoding($false^)
  echo if (!(Test-Path $Path^)^) { [System.IO.File]::WriteAllText($Path, '{}', $utf8NoBom^) }
  echo try { $cfg = Get-Content $Path -Raw ^| ConvertFrom-Json } catch { $cfg = $null }
  echo if (-not $cfg^) { $cfg = [pscustomobject]@{} }
  echo $oldAi = $cfg.ai
  echo $model = if ($oldAi -and $oldAi.model -ne $null^) { [string]$oldAi.model } else { 'llama3.1:8b' }
  echo $backend = if ($oldAi -and $oldAi.backend -ne $null^) { [string]$oldAi.backend } else { 'ollama' }
  echo $ccModel = if ($oldAi -and $oldAi.claude_code_model -ne $null^) { [string]$oldAi.claude_code_model } else { '' }
  echo $ccEff = if ($oldAi -and $oldAi.claude_code_effort -ne $null^) { [string]$oldAi.claude_code_effort } else { '' }
  echo $oaEff = if ($oldAi -and $oldAi.openai_effort -ne $null^) { [string]$oldAi.openai_effort } else { '' }
  echo switch ($Key^) {
  echo   'ai.model' { $model = $Value }
  echo   'ai.backend' { $backend = $Value }
  echo   'ai.claude_code_model' { $ccModel = $Value }
  echo   'ai.claude_code_effort' { $ccEff = $Value }
  echo   'ai.openai_effort' { $oaEff = $Value }
  echo   default { }
  echo }
  echo $cfg ^| Add-Member -NotePropertyName ai -NotePropertyValue ([pscustomobject]@{ model = $model; backend = $backend; claude_code_model = $ccModel; claude_code_effort = $ccEff; openai_effort = $oaEff }^) -Force
  echo $jsonOut = $cfg ^| ConvertTo-Json -Depth 50
  echo [System.IO.File]::WriteAllText($Path, $jsonOut, $utf8NoBom^)
)
>"%PS_SET_KEY%" (
  echo param([string]$Path,[string]$Backend,[string]$ApiKeyFile^)
  echo $utf8NoBom = New-Object System.Text.UTF8Encoding($false^)
  echo $apiKey = ''
  echo if ($ApiKeyFile -and (Test-Path -LiteralPath $ApiKeyFile^)^) { $apiKey = [System.IO.File]::ReadAllText($ApiKeyFile, [System.Text.Encoding]::UTF8^) }
  echo if ([string]::IsNullOrWhiteSpace($apiKey^)^) { exit 2 }
  echo $dir = Split-Path -Parent $Path
  echo if (!(Test-Path $dir^)^) { New-Item -ItemType Directory -Path $dir -Force ^| Out-Null }
  echo if (Test-Path $Path^) {
  echo   try { $obj = Get-Content $Path -Raw ^| ConvertFrom-Json } catch { $obj = $null }
  echo } else { $obj = $null }
  echo if (-not $obj^) { $obj = [pscustomobject]@{} }
  echo $obj ^| Add-Member -NotePropertyName $Backend -NotePropertyValue $apiKey -Force
  echo $jsonOut = $obj ^| ConvertTo-Json -Depth 20
  echo [System.IO.File]::WriteAllText($Path, $jsonOut, $utf8NoBom^)
)
goto :eof

:SetConfig
set "CFG_KEY=%~1"
set "CFG_VAL=%~2"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SET_CFG%" -Path "%CMC_CFG%" -Key "%CFG_KEY%" -Value "%CFG_VAL%"
if errorlevel 1 exit /b 1
exit /b 0

:SaveApiKey
set "API_KEY_TEMP=%TEMP%\cmc_key_%RANDOM%%RANDOM%.txt"
set "CMC_API_KEY_RAW=%API_KEY_INPUT%"
powershell -NoProfile -Command "$enc = New-Object System.Text.UTF8Encoding($false); [System.IO.File]::WriteAllText('%API_KEY_TEMP%', $env:CMC_API_KEY_RAW, $enc)"
if errorlevel 1 (
    set "CMC_API_KEY_RAW="
    if exist "%API_KEY_TEMP%" del /f /q "%API_KEY_TEMP%" >nul 2>&1
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SET_KEY%" -Path "%KEYS_PATH%" -Backend "%API_BACKEND%" -ApiKeyFile "%API_KEY_TEMP%"
set "CMC_API_KEY_RAW="
if exist "%API_KEY_TEMP%" del /f /q "%API_KEY_TEMP%" >nul 2>&1
if errorlevel 1 exit /b 1
exit /b 0

:ClaudeEffortSupported
set "CLAUDE_EFFORT_SUPPORTED=0"
powershell -NoProfile -Command ^
  "$cmd = Get-Command claude -ErrorAction SilentlyContinue;" ^
  "if (-not $cmd) { $cmd = Get-Command claude.cmd -ErrorAction SilentlyContinue };" ^
  "if (-not $cmd) { exit 1 };" ^
  "try { $h = & $cmd.Source --help 2>&1 | Out-String; if ($h.ToLower().Contains('--effort')) { exit 0 } else { exit 2 } } catch { exit 3 }"
if errorlevel 1 (
    set "CLAUDE_EFFORT_SUPPORTED=0"
) else (
    set "CLAUDE_EFFORT_SUPPORTED=1"
)
goto :eof

:END
echo.
echo  =============================================================
echo   Done.
echo  =============================================================
echo.
echo   In CMC use:
echo     ai-model pick
echo     ai-model list
echo     ai-model current
echo.
pause
endlocal
exit /b 0
