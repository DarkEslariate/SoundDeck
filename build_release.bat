@echo off
title Building SoundDeck
cd /d "%~dp0"

echo Starting SoundDeck build... > build_log.txt
echo Folder: %cd% >> build_log.txt
echo. >> build_log.txt

echo ==========================================
echo Checking required files...
echo ==========================================
echo.

if not exist "SoundDeck.py" (
    echo ERROR: SoundDeck.py is missing.
    echo ERROR: SoundDeck.py is missing. >> build_log.txt
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo ERROR: requirements.txt is missing.
    echo ERROR: requirements.txt is missing. >> build_log.txt
    pause
    exit /b 1
)

if not exist "ffmpeg\ffmpeg.exe" (
    echo ERROR: ffmpeg\ffmpeg.exe is missing.
    echo ERROR: ffmpeg\ffmpeg.exe is missing. >> build_log.txt
    echo.
    echo FFmpeg is not included in the source repo.
    echo Create a folder called ffmpeg and put ffmpeg.exe inside it.
    echo See README.md for instructions.
    pause
    exit /b 1
)

if not exist "ffmpeg\ffprobe.exe" (
    echo ERROR: ffmpeg\ffprobe.exe is missing.
    echo ERROR: ffmpeg\ffprobe.exe is missing. >> build_log.txt
    echo.
    echo FFmpeg is not included in the source repo.
    echo Create a folder called ffmpeg and put ffprobe.exe inside it.
    echo See README.md for instructions.
    pause
    exit /b 1
)

if not exist "README.md" (
    echo ERROR: README.md is missing.
    echo ERROR: README.md is missing. >> build_log.txt
    pause
    exit /b 1
)

if not exist "LICENSE" (
    echo ERROR: LICENSE is missing.
    echo ERROR: LICENSE is missing. >> build_log.txt
    pause
    exit /b 1
)

if not exist "assets\SoundDeck.ico" (
    echo ERROR: assets\SoundDeck.ico is missing.
    echo ERROR: assets\SoundDeck.ico is missing. >> build_log.txt
    pause
    exit /b 1
)

if not exist "licenses" mkdir "licenses"

if not exist "licenses\FFMPEG_NOTICE.txt" (
    echo FFmpeg Notice > "licenses\FFMPEG_NOTICE.txt"
    echo FFmpeg license info: https://ffmpeg.org/legal.html >> "licenses\FFMPEG_NOTICE.txt"
)

if not exist "sounddeck_config.json" (
    copy /Y "sounddeck_config.example.json" "sounddeck_config.json" >nul
)

echo All required files found.
echo All required files found. >> build_log.txt

echo.
echo ==========================================
echo Installing packages...
echo ==========================================
echo.

python -m pip install --upgrade -r requirements.txt >> build_log.txt 2>&1

if errorlevel 1 (
    echo.
    echo ERROR: Package install failed.
    echo Open build_log.txt and send me the bottom part.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Cleaning old build...
echo ==========================================
echo.

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist SoundDeck.spec del SoundDeck.spec

echo.
echo ==========================================
echo Building EXE folder...
echo ==========================================
echo.

python -m PyInstaller ^
  --noconsole ^
  --onedir ^
  --name SoundDeck ^
  --icon "assets\SoundDeck.ico" ^
  --add-binary "ffmpeg\ffmpeg.exe;ffmpeg" ^
  --add-binary "ffmpeg\ffprobe.exe;ffmpeg" ^
  --add-data "assets\SoundDeck.ico;." ^
  --add-data "licenses\FFMPEG_NOTICE.txt;licenses" ^
  SoundDeck.py >> build_log.txt 2>&1

if errorlevel 1 (
    echo.
    echo ==========================================
    echo BUILD FAILED
    echo ==========================================
    echo.
    echo Open this file:
    echo build_log.txt
    echo.
    echo Send me the last 30-ish lines from it.
    echo.
    pause
    exit /b 1
)

if not exist "dist\SoundDeck\SoundDeck.exe" (
    echo.
    echo ERROR: Build finished but SoundDeck.exe was not created.
    echo ERROR: Build finished but SoundDeck.exe was not created. >> build_log.txt
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Copying user-facing files next to EXE...
echo ==========================================
echo.

copy /Y "sounddeck_config.example.json" "dist\SoundDeck\sounddeck_config.json" >nul
copy /Y "README.md" "dist\SoundDeck\README.md" >nul
copy /Y "LICENSE" "dist\SoundDeck\LICENSE" >nul
copy /Y "VERSION.txt" "dist\SoundDeck\VERSION.txt" >nul
copy /Y "assets\SoundDeck.ico" "dist\SoundDeck\SoundDeck.ico" >nul

if exist "Setup SoundDeck.bat" (
    copy /Y "Setup SoundDeck.bat" "dist\SoundDeck\Setup SoundDeck.bat" >nul
)

if exist "licenses" (
    xcopy /E /I /Y "licenses" "dist\SoundDeck\licenses" >nul
)

echo.
echo ==========================================
echo DONE
echo ==========================================
echo.
echo Your portable app is here:
echo %cd%\dist\SoundDeck
echo.
echo Zip the SoundDeck folder inside dist.
echo.
pause