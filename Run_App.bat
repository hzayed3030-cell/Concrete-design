@echo off
title ECP 203 Concrete Design Dashboard
cd /d "%~dp0"
echo Launching ECP 203 Concrete Design Dashboard...

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" -m streamlit run app.py
) else if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    "%LOCALAPPDATA%\Python\bin\python.exe" -m streamlit run app.py
) else if exist "%LOCALAPPDATA%\Programs\Python\Python315\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python315\python.exe" -m streamlit run app.py
) else if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" -m streamlit run app.py
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m streamlit run app.py
) else (
    python -m streamlit run app.py
)
pause
