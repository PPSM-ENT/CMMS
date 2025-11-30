@echo off
title CMMS Stopper
echo ========================================
echo        Stopping CMMS Servers
echo ========================================
echo.

echo Stopping Backend (uvicorn on port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /PID %%a /F 2>nul
)

echo Stopping Frontend (node on port 3000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /PID %%a /F 2>nul
)

echo.
echo ========================================
echo All CMMS servers have been stopped.
echo ========================================
echo.
pause
