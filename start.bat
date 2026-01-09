@echo off
REM ===================================================
REM Sub-auto - Automated MKV Subtitle Translator
REM Batch file untuk memulai aplikasi
REM ===================================================

echo.
echo ========================================
echo   Sub-auto - Subtitle Translator
echo ========================================
echo.

REM Pindah ke direktori aplikasi
cd /d "%~dp0"

REM Cek apakah virtual environment ada
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment tidak ditemukan!
    echo.
    echo Silakan jalankan instalasi terlebih dahulu:
    echo   1. python -m venv .venv
    echo   2. .venv\Scripts\activate
    echo   3. pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Aktifkan virtual environment
echo [INFO] Mengaktifkan virtual environment...
call .venv\Scripts\activate.bat

REM Cek apakah Python tersedia
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    echo Pastikan Python sudah terinstall dan ada di PATH
    echo.
    pause
    exit /b 1
)

REM Jalankan aplikasi
echo [INFO] Memulai Sub-auto...
echo.
python main.py

REM Jika aplikasi berhenti dengan error
if errorlevel 1 (
    echo.
    echo [ERROR] Aplikasi berhenti dengan error!
    echo.
    pause
)

REM Deaktivasi virtual environment
deactivate
