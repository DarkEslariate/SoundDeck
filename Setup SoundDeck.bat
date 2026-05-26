@echo off
title SoundDeck Setup
cd /d "%~dp0"

echo ==========================================
echo SoundDeck Setup
echo ==========================================
echo.
echo SoundDeck requires VB-Audio Virtual Cable for Discord/OBS routing.
echo.
echo After installing VB-Cable:
echo 1. Restart your PC.
echo 2. Open SoundDeck.exe.
echo 3. In Discord/OBS, set Microphone/Input to CABLE Output.
echo.
pause

echo Opening VB-Audio Virtual Cable page...
start https://vb-audio.com/Cable/

pause
