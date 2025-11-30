@echo off
title CMMS Launcher
echo ========================================
echo        CMMS Application Launcher
echo ========================================
echo.

:: Check if backend venv exists
if not exist "backend\venv\Scripts\activate.bat" (
    echo [ERROR] Backend virtual environment not found!
    echo Please run: cd backend ^&^& python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Check if frontend node_modules exists
if not exist "frontend\node_modules" (
    echo [ERROR] Frontend dependencies not installed!
    echo Please run: cd frontend ^&^& npm install
    pause
    exit /b 1
)

echo Starting Backend Server...
start "CMMS Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: Wait a moment for backend to start
timeout /t 3 /nobreak > nul

echo Starting Frontend Server...
start "CMMS Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

:: Wait a moment for frontend to start
timeout /t 3 /nobreak > nul

echo.
echo ========================================
echo CMMS is starting up!
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Opening browser in 5 seconds...
timeout /t 5 /nobreak > nul

:: Open the browser
start http://localhost:3000

echo.
echo Press any key to close this window (servers will keep running)
pause > nul
