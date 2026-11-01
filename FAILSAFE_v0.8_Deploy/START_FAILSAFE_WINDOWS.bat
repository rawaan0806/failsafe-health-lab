@echo off
setlocal
cd /d "%~dp0"
echo.
echo ================================================
echo       FAILSAFE v0.7 - WEBSITE + LIVE LAB
 echo ================================================
echo.
echo All numbers are hypothetical. No clinical use.
echo This local server does not send data to the cloud.
echo.
where py >nul 2>&1
if %errorlevel%==0 (
  set "PYTHON_CMD=py -3"
) else (
  where python >nul 2>&1
  if %errorlevel%==0 (
    set "PYTHON_CMD=python"
  ) else (
    echo ERROR: Python 3.10+ is not found.
    echo Install Python from https://www.python.org/downloads/
    pause
    exit /b 1
  )
)
echo Opening http://127.0.0.1:8765 in your browser...
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8765"
%PYTHON_CMD% server.py
if errorlevel 1 (
  echo.
  echo Server could not start. Check that Python 3.10+ is installed
  echo and nothing else is already using port 8765.
)
pause
