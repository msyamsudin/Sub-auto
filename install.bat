@echo off
REM ===================================================
REM Sub-auto - Automated MKV Subtitle Translator
REM Batch file untuk instalasi dependencies
REM ===================================================

echo.
echo ========================================
echo   Sub-auto - Installation Script
echo ========================================
echo.

REM Pindah ke direktori aplikasi
cd /d "%~dp0"

REM Cek apakah Python tersedia
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    echo Silakan install Python 3.10+ terlebih dahulu
    echo Download dari: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [INFO] Python ditemukan:
python --version
echo.

REM Buat virtual environment jika belum ada
if not exist ".venv" (
    echo [INFO] Membuat virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Gagal membuat virtual environment!
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment berhasil dibuat
    echo.
) else (
    echo [INFO] Virtual environment sudah ada
    echo.
)

REM Aktifkan virtual environment
echo [INFO] Mengaktifkan virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo [INFO] Mengupgrade pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo [INFO] Menginstall dependencies dari requirements.txt...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Gagal menginstall dependencies!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Instalasi Selesai!
echo ========================================
echo.
echo Untuk menjalankan aplikasi, gunakan:
echo   start.bat
echo.
echo Atau secara manual:
echo   .venv\Scripts\activate
echo   python main.py
echo.
echo CATATAN: Pastikan MKVToolNix sudah terinstall
echo Download dari: https://mkvtoolnix.download/
echo.

REM Deaktivasi virtual environment
deactivate

pause
