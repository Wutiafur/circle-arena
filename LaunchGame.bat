@echo off
setlocal
cd /d "%~dp0"

if not exist "main.py" (
    echo Could not find main.py in:
    echo %~dp0
    pause
    exit /b 1
)

set "PY_LAUNCHER="
py -3 -c "import sys" >nul 2>&1 && set "PY_LAUNCHER=py -3"
if not defined PY_LAUNCHER python -c "import sys" >nul 2>&1 && set "PY_LAUNCHER=python"

if not defined PY_LAUNCHER (
    echo Python 3 is not installed or is not available on PATH.
    echo Install Python, then run this launcher again.
    pause
    exit /b 1
)

for /f "usebackq delims=" %%I in (`%PY_LAUNCHER% -c "import pathlib, sys; print(pathlib.Path(sys.executable).resolve())"`) do set "PY_EXE=%%I"
for /f "usebackq delims=" %%I in (`%PY_LAUNCHER% -c "import pathlib, sys; print(pathlib.Path(sys.executable).with_name('pythonw.exe'))"`) do set "PYW_EXE=%%I"

if not exist "%PYW_EXE%" (
    echo Could not find pythonw.exe next to:
    echo %PY_EXE%
    pause
    exit /b 1
)

"%PY_EXE%" -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo pygame not found. Installing now...
    "%PY_EXE%" -m pip install pygame
    if errorlevel 1 (
        echo Failed to install pygame.
        pause
        exit /b 1
    )
)

start "" "%PYW_EXE%" "%~dp0main.py"
exit /b 0
