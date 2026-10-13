@echo off
rem Stops the server that start.cmd started (by PID, whole process tree).
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if exist ".run\app.pid" (
  set /p PID=<".run\app.pid"
  tasklist /FI "PID eq !PID!" 2>nul | find " !PID! " >nul && (
    taskkill /F /T /PID !PID! >nul 2>&1
    echo Stopped Interview Coach ^(PID !PID!^).
    del ".run\app.pid" >nul 2>&1
    exit /b 0
  )
  del ".run\app.pid" >nul 2>&1
)
echo Nothing was running.
exit /b 0
