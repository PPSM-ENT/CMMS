@echo off
title CMMS Installer
echo.
echo ========================================
echo   CMMS Installer
echo ========================================
echo.
echo This will install CMMS to C:\CMMS
echo.
echo PREREQUISITES:
echo   - Python 3.11+ (with PATH)
echo   - Node.js 18+ (with PATH)
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause > nul

echo.
echo Starting installation...
echo (This requires Administrator privileges)
echo.

powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0install.ps1\"' -Verb RunAs -Wait"

echo.
echo Installation process started in a new window.
echo.
pause
