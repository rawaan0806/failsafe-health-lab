@echo off
setlocal
cd /d "%~dp0"
title FAILSAFE v1.2 - Outpatient Lab

echo.
echo =================================================
echo          FAILSAFE v1.2 - OUTPATIENT LAB
 echo =================================================
echo.
echo This demo only uses fictional patient scenarios.
echo The local server does not send patient data online.
echo.

rem Check the Python launcher first, and verify version rather than existence only.
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
  if not errorlevel 1 (
    echo Starting with Python launcher...
    goto :start_py
  )
)

rem Check python on PATH; Windows may have a nonfunctional Store alias.
where python >nul 2>&1
if not errorlevel 1 (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
  if not errorlevel 1 (
    echo Starting with Python...
    goto :start_python
  )
)

rem uv can manage/download Python 3.12 and run the standard-library local server.
where uv >nul 2>&1
if not errorlevel 1 (
  echo Python not found on PATH. Trying uv with Python 3.12...
  echo uv may download Python the first time it runs.
  goto :start_uv
)

echo.
echo Python 3.10+ and uv could not be found.
echo.
echo OPTION 1: Install Python 3.12 from https://www.python.org/downloads/
echo            Enable "Add python.exe to PATH" if shown.
echo OPTION 2: Install uv from https://docs.astral.sh/uv/getting-started/installation/
echo.
echo After installation, close this window and double-click this file again.
echo You can preview just the homepage by opening index.html directly.
echo.
pause
exit /b 1

:start_py
call :open_browser
py -3 server.py
goto :finished

:start_python
call :open_browser
python server.py
goto :finished

:start_uv
call :open_browser
uv run --no-project --python 3.12 server.py
goto :finished

:open_browser
echo Opening http://127.0.0.1:8765 in your browser...
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8765"
exit /b 0

:finished
if errorlevel 1 (
  echo.
  echo FAILSAFE did not start. Copy the error shown above.
  echo If port 8765 is already in use, close the other FAILSAFE window.
)
echo.
echo Press any key to close this window.
pause >nul
