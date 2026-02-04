@echo off
echo ========================================
echo   Neatify - Nuitka Build
echo ========================================
echo.

cd /d "%~dp0"

echo Activating Python environment...
call .venv\Scripts\activate.bat

echo.
echo Cleaning old build folders...
if exist "neatify.dist" rmdir /s /q "neatify.dist"
if exist "neatify.build" rmdir /s /q "neatify.build"
if exist "Neatify.exe" del /f "Neatify.exe"

echo.
echo Compiling with Nuitka (this may take 5-10 minutes)...
echo.

python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=asistan.ico ^
    --enable-plugin=tk-inter ^
    --include-data-files=asistan.ico=asistan.ico ^
    --company-name="Neatify" ^
    --product-name="Neatify" ^
    --file-version=1.0.0 ^
    --product-version=1.0.0 ^
    --file-description="PC Cleaning and Optimization Tool" ^
    --copyright="2026" ^
    --output-filename=Neatify.exe ^
    neatify.py

echo.
if exist "Neatify.exe" (
    echo ========================================
    echo   SUCCESS! Neatify.exe created
    echo ========================================
) else (
    echo ========================================
    echo   ERROR! EXE could not be created
    echo ========================================
)

echo.
pause
