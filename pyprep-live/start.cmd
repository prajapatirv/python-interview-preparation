@echo off
rem Starts the Live Runner in the background and opens the browser.
rem   start.cmd              native: creates .venv, installs deps, runs uvicorn (default)
rem   start.cmd docker       local Docker: docker compose up -d --build
rem   start.cmd --install    force re-install of dependencies (native)
rem Env: PORT (8000), PREP_ROOT, PREP_ALLOW_EDIT (1 here: local tool), AI_MODE (auto|claude|mock),
rem      ANTHROPIC_API_KEY (or put it in .env). With no key the AI coach runs in mock mode.
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if "%PORT%"=="" set PORT=8000
if "%PREP_ALLOW_EDIT%"=="" set PREP_ALLOW_EDIT=1
set "URL=http://127.0.0.1:%PORT%"
set MODE=native
set FORCE=0
for %%A in (%*) do (
  if /i "%%A"=="docker" set MODE=docker
  if /i "%%A"=="--install" set FORCE=1
)

if not exist ".env" if exist ".env.example" (
  copy /y ".env.example" ".env" >nul
  echo Created .env from .env.example ^(no API key = mock AI mode^).
)
if not exist "..\python-interview-prep" (
  echo ERROR: ..\python-interview-prep not found. Set PREP_ROOT to the examples folder.
  if "%PREP_ROOT%"=="" exit /b 1
)

if /i "%MODE%"=="docker" goto :docker

rem ------------------------------------------------------------------ native
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
  echo ERROR: Python 3.10+ not found. Install it from python.org ^(tick "Add to PATH"^), or run: start.cmd docker
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
  ".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt -r requirements-examples.txt || (echo ERROR: pip install failed & exit /b 1)
  echo ok> ".venv\.deps-ok"
)

if not exist ".run" mkdir ".run"
echo Starting server on %URL% ...
powershell -NoProfile -Command "$p = Start-Process -FilePath '.venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','%PORT%' -RedirectStandardOutput '.run\app.log' -RedirectStandardError '.run\app.err.log' -WindowStyle Hidden -PassThru; Set-Content -Path '.run\app.pid' -Value $p.Id"
call :wait || (
  echo ERROR: server did not become ready. Last log lines:
  if exist ".run\app.err.log" powershell -NoProfile -Command "Get-Content '.run\app.err.log' -Tail 15"
  call "%~dp0stop.cmd" >nul 2>&1
  exit /b 1
)
echo.
echo Ready: %URL%   ^(logs: .run\app.log, stop with stop.cmd^)
start "" "%URL%"
exit /b 0

rem ------------------------------------------------------------------ docker
:docker
docker info >nul 2>&1 || (echo ERROR: Docker is not running. Start Docker Desktop, or run start.cmd without "docker". & exit /b 1)
echo Building and starting the container ^(first build takes a few minutes^)...
docker compose up -d --build || (echo ERROR: docker compose failed & exit /b 1)
call :wait || (
  echo ERROR: container did not become ready.
  docker compose logs --tail 30
  exit /b 1
)
echo.
echo Ready: %URL%   ^(Docker; stop with stop.cmd^)
start "" "%URL%"
exit /b 0

:wait
powershell -NoProfile -Command "for($i=0;$i -lt 60;$i++){ try { Invoke-WebRequest -UseBasicParsing '%URL%/api/catalog' -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"
exit /b %errorlevel%
