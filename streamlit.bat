@if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    @"%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" -m streamlit %*
) else if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    @"%LOCALAPPDATA%\Python\bin\python.exe" -m streamlit %*
) else (
    @"%LOCALAPPDATA%\Programs\Python\Python315\python.exe" -m streamlit %*
)
