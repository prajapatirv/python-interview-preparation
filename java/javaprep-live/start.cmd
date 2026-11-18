@echo off
rem Starts Java Prep Live (JDK 21+ only; no Maven, no pip) and opens the browser.
rem   start.cmd            -> http://127.0.0.1:8090
rem   start.cmd 9000       -> choose a port
rem   start.cmd --check    -> run every example headless, print ok/FAIL, exit 1 on failure
rem Env: JAVAPREP_ROOT (path to java-interview-prep), JAVAPREP_TIMEOUT (seconds per run, default 60)
setlocal
cd /d "%~dp0"
rem java: PATH, else JAVA_HOME, else the newest JDK IntelliJ installed under %USERPROFILE%\.jdks
set "JAVA="
where java >nul 2>nul && set "JAVA=java"
if not defined JAVA if defined JAVA_HOME if exist "%JAVA_HOME%\bin\java.exe" set "JAVA=%JAVA_HOME%\bin\java.exe"
if not defined JAVA for /f "delims=" %%D in ('dir /b /ad /o:n "%USERPROFILE%\.jdks" 2^>nul') do (
  if exist "%USERPROFILE%\.jdks\%%D\bin\java.exe" set "JAVA=%USERPROFILE%\.jdks\%%D\bin\java.exe"
)
if not defined JAVA (
  echo ERROR: Java not found ^(PATH, JAVA_HOME, %USERPROFILE%\.jdks^). Install JDK 21+ ^(e.g. Temurin^) and reopen the terminal.
  exit /b 1
)
if /i "%~1"=="--check" (
  "%JAVA%" JavaPrepLive.java --check
  exit /b %errorlevel%
)
rem port: the argument, else the PORT environment variable, else 8090 (same as start.sh)
if not "%~1"=="" set PORT=%~1
if "%PORT%"=="" set PORT=8090
echo Starting Java Prep Live on http://127.0.0.1:%PORT%  ^(Ctrl+C to stop^)
start "" "http://127.0.0.1:%PORT%"
"%JAVA%" JavaPrepLive.java --port %PORT%
