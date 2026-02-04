@echo off
echo ========================================
echo   Temizlik Asistani EXE Olusturucu
echo ========================================
echo.

REM Virtual environment aktif et
call .venv\Scripts\activate.bat

REM PyInstaller yükle (yoksa)
pip install pyinstaller --quiet

echo.
echo EXE olusturuluyor...
echo.

pyinstaller --noconfirm --onefile --windowed ^
    --icon=asistan.ico ^
    --add-data "asistan.ico;." ^
    --name "Temizlik_Asistani" ^
    --version-file=version_info.txt ^
    temizlik_asistani.py

echo.
echo ========================================
if exist "dist\Temizlik_Asistani.exe" (
    echo   BASARILI! EXE olusturuldu.
    echo   Konum: dist\Temizlik_Asistani.exe
) else (
    echo   HATA! EXE olusturulamadi.
)
echo ========================================
pause
