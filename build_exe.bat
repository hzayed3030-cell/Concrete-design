@echo off
title Building ECP 203 Dashboard EXE...
echo ====================================================
echo  Building ECP 203 Concrete Design Dashboard EXE
echo ====================================================
python -m PyInstaller --clean ECP203_Dashboard.spec
echo.
if exist "dist\ECP203_Dashboard.exe" (
    echo [SUCCESS] ECP203_Dashboard.exe was generated successfully in dist folder!
) else (
    echo [ERROR] Build failed. Please check the output above.
)
pause
