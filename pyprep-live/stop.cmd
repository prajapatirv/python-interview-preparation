@echo off
rem Stops whatever start.cmd started: the native server (by PID, whole process tree) and/or the Docker container.
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set STOPPED=0

if exist ".run\app.pid" (
  set /p PID=<".run\app.pid"
  tasklist /FI "PID eq !PID!" 2>nul | find " !PID! " >nul && (
    taskkill /F /T /PID !PID! >nul 2>&1
    echo Stopped native server ^(PID !PID!^).
    set STOPPED=1
  )
  del ".run\app.pid" >nul 2>&1
)

docker info >nul 2>&1 && (
  for /f %%C in ('docker compose ps -q 2^>nul') do set HASDOCKER=1
)
if defined HASDOCKER (
  docker compose down
  echo Stopped Docker container.
  set STOPPED=1
)

if "%STOPPED%"=="0" echo Nothing was running.
exit /b 0
