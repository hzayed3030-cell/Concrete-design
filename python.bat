@if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    @"%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" %*
) else if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    @"%LOCALAPPDATA%\Python\bin\python.exe" %*
) else if exist "%LOCALAPPDATA%\Programs\Python\Python315\python.exe" (
    @"%LOCALAPPDATA%\Programs\Python\Python315\python.exe" %*
) else (
    @echo Python executable not found.
)
