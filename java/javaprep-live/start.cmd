@echo off
rem Starts Java Prep Live (JDK 21+ only; no Maven, no pip) and opens the browser.
rem   start.cmd            -> http://127.0.0.1:8090
rem   start.cmd 9000       -> choose a port
rem   start.cmd --check    -> run every example headless, print ok/FAIL, exit 1 on failure
rem Env: JAVAPREP_ROOT (path to java-interview-prep), JAVAPREP_TIMEOUT (seconds per run, default 60)
setlocal
cd /d "%~dp0"
where java >nul 2>nul
if errorlevel 1 (
  echo ERROR: java not found on PATH. Install JDK 21 ^(e.g. Temurin^) and reopen the terminal.
  exit /b 1
)
if /i "%~1"=="--check" (
  java JavaPrepLive.java --check
  exit /b %errorlevel%
)
set PORT=%~1
if "%PORT%"=="" set PORT=8090
echo Starting Java Prep Live on http://127.0.0.1:%PORT%  ^(Ctrl+C to stop^)
start "" "http://127.0.0.1:%PORT%"
java JavaPrepLive.java --port %PORT%
