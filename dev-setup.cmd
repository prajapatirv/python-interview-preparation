@echo off
rem Creates .venv at the workspace root with everything every Python check needs, then runs them all.
rem Same steps as CI (.github/workflows/ci.yml). Usage: dev-setup.cmd [--no-checks]
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    py -3.14 -m venv .venv || py -m venv .venv || exit /b 1
)
.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements-dev.txt || exit /b 1
if "%~1"=="--no-checks" exit /b 0

set PY=%cd%\.venv\Scripts\python.exe
set FAIL=0
echo == ruff & "%PY%" -m ruff check . || set FAIL=1
echo == prepkit & pushd shared\prepkit & "%PY%" -m pytest -q || set FAIL=1
popd
echo == interview-coach & pushd interview-coach & "%PY%" -m pytest -q || set FAIL=1
popd
echo == pyprep-live & pushd python\pyprep-live & "%PY%" -m pytest -q || set FAIL=1
popd
echo == python-interview-prep & pushd python\python-interview-prep & "%PY%" -m pytest -q || set FAIL=1
popd
echo == examples & "%PY%" scripts\verify_examples.py || set FAIL=1
echo == QUESTION_INDEX links & "%PY%" scripts\check_content.py || set FAIL=1
if %FAIL%==1 (echo. & echo SOME CHECKS FAILED & exit /b 1)
echo. & echo all checks passed
