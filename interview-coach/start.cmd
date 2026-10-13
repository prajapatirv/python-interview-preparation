@echo off
rem Starts the Interview Coach in the background and opens the browser.
rem   start.cmd              creates .venv, installs deps, runs uvicorn
rem   start.cmd --install    force re-install of dependencies
rem Env (or .env): PORT (8100), ANTHROPIC_API_KEY, AI_MODE (auto|claude|mock), ANTHROPIC_MODEL, AI_EFFORT.
rem With no API key the coach runs in offline mock mode.
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if "%PORT%"=="" set PORT=8100
set "URL=http://127.0.0.1:%PORT%"
set FORCE=0
for %%A in (%*) do if /i "%%A"=="--install" set FORCE=1

if not exist ".env" if exist ".env.example" (
  copy /y ".env.example" ".env" >nul
  echo Created .env from .env.example - put your ANTHROPIC_API_KEY there for the real AI coach.
)

if exist ".run\app.pid" (
  set /p OLDPID=<".run\app.pid"
  tasklist /FI "PID eq !OLDPID!" 2>nul | find " !OLDPID! " >nul && (
    echo Already running ^(PID !OLDPID!^): %URL%   -- run stop.cmd first to restart.
    exit /b 0
  )
)

set "PYEXE="
for %%P in (py python python3) do (
  if not defined PYEXE (
    %%P -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1 && set "PYEXE=%%P"
  )
)
if not defined PYEXE (
  echo ERROR: Python 3.10+ not found. Install it from python.org ^(tick "Add to PATH"^).
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PYEXE% -m venv .venv || (echo ERROR: could not create .venv & exit /b 1)
  set FORCE=1
)
if not exist ".venv\.deps-ok" set FORCE=1
if "%FORCE%"=="1" (
  echo Installing dependencies ^(first run takes a minute^)...
  ".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements-dev.txt || (echo ERROR: pip install failed & exit /b 1)
  echo ok> ".venv\.deps-ok"
)

if not exist ".run" mkdir ".run"
echo Starting server on %URL% ...
powershell -NoProfile -Command "$p = Start-Process -FilePath '.venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','%PORT%' -RedirectStandardOutput '.run\app.log' -RedirectStandardError '.run\app.err.log' -WindowStyle Hidden -PassThru; Set-Content -Path '.run\app.pid' -Value $p.Id"
powershell -NoProfile -Command "for($i=0;$i -lt 60;$i++){ try { Invoke-WebRequest -UseBasicParsing '%URL%/api/status' -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"
if errorlevel 1 (
  echo ERROR: server did not become ready. Last log lines:
  if exist ".run\app.err.log" powershell -NoProfile -Command "Get-Content '.run\app.err.log' -Tail 15"
  call "%~dp0stop.cmd" >nul 2>&1
  exit /b 1
)
echo.
echo Ready: %URL%   ^(logs: .run\app.log, stop with stop.cmd^)
start "" "%URL%"
exit /b 0
