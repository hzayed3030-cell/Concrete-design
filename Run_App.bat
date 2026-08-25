@echo off
title ECP 203 Dashboard Launcher
if exist "dist\ECP203_Dashboard.exe" (
    echo Launching Standalone EXE...
    start "" "dist\ECP203_Dashboard.exe"
) else (
    echo Running with Python Streamlit...
    streamlit run app.py
)
