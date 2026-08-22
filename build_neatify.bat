@echo off
setlocal

echo ========================================
echo   Neatify - Nuitka Windows Build
echo ========================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo Building Neatify with Nuitka...
echo.

%PYTHON% -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=neatify.ico ^
    --enable-plugin=tk-inter ^
    --include-data-files=neatify.ico=neatify.ico ^
    --company-name="Neatify" ^
    --product-name="Neatify" ^
    --file-version=1.3.0 ^
    --product-version=1.3.0 ^
    --file-description="PC Cleaning and Optimization Tool" ^
    --copyright="2026" ^
    --output-filename=Neatify.exe ^
    --output-dir=dist ^
    neatify.py

if errorlevel 1 (
    echo.
    echo Build failed.
    exit /b 1
)

echo.
echo Build completed: dist\Neatify.exe
endlocal
