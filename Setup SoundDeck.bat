@echo off
title SoundDeck Setup
cd /d "%~dp0"

echo ==========================================
echo SoundDeck Setup
echo ==========================================
echo.
echo This setup helper can open the VB-Audio Virtual Cable download page,
echo create a desktop shortcut, and launch SoundDeck.
echo.
echo VB-Cable is required for Discord/OBS routing.
echo After installing VB-Cable, restart your PC.
echo.
choice /C YN /M "Open the official VB-Audio Virtual Cable download page"
if errorlevel 2 goto shortcut
start https://vb-audio.com/Cable/

:shortcut
echo.
choice /C YN /M "Create a SoundDeck desktop shortcut"
if errorlevel 2 goto runapp
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell;$s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\SoundDeck.lnk');$s.TargetPath='%cd%\SoundDeck.exe';$s.WorkingDirectory='%cd%';$s.IconLocation='%cd%\SoundDeck.exe';$s.Save()"

:runapp
echo.
choice /C YN /M "Run SoundDeck now"
if errorlevel 2 goto done
if exist "SoundDeck.exe" start "" "%cd%\SoundDeck.exe"
if not exist "SoundDeck.exe" python SoundDeck.py

:done
echo.
echo Setup helper finished.
pause
