@echo off
title Install Requirements via Python
cd /d "%~dp0"

echo ======================================================
echo  Detecting Python installation...
echo ======================================================

set PYTHON_EXEC=

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PYTHON_EXEC=python
) else if exist "C:\Users\Mohamed\anaconda3\python.exe" (
    set PYTHON_EXEC="C:\Users\Mohamed\anaconda3\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set PYTHON_EXEC="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set PYTHON_EXEC="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set PYTHON_EXEC="%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
)

if "%PYTHON_EXEC%"=="" (
    echo [ERROR] Python was not found in PATH or standard paths!
    echo Please install Python or specify its path.
    pause
    exit /b 1
)

echo Using Python: %PYTHON_EXEC%
echo.
echo Installing packages line by line from requirements.txt...
echo ------------------------------------------------------

for /f "usebackq tokens=* delims=" %%i in ("requirements.txt") do (
    echo Installing %%i ...
    %PYTHON_EXEC% -m pip install "%%i"
    echo ------------------------------------------------------
)

echo.
echo ======================================================
echo  Installation finished!
echo ======================================================
pause
