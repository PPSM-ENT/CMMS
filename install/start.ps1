# CMMS Startup Script
# Starts both backend and frontend servers

$ErrorActionPreference = "SilentlyContinue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting CMMS Application" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verify installation
$backendPath = Join-Path $ScriptDir "backend"
$frontendPath = Join-Path $ScriptDir "frontend"
$venvPython = Join-Path $backendPath "venv\Scripts\python.exe"
$nodeModules = Join-Path $frontendPath "node_modules"

Write-Host "Checking installation..." -ForegroundColor Yellow

# Check backend venv
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Python virtual environment not found!" -ForegroundColor Red
    Write-Host "Expected: $venvPython" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Please run the installer first: install\install.ps1" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  [OK] Python venv found" -ForegroundColor Green

# Check node_modules
if (-not (Test-Path $nodeModules)) {
    Write-Host "[ERROR] Node modules not found!" -ForegroundColor Red
    Write-Host "Expected: $nodeModules" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Please run the installer first: install\install.ps1" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  [OK] Node modules found" -ForegroundColor Green

# Check .env
$envFile = Join-Path $backendPath ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "[WARN] .env not found, creating default..." -ForegroundColor Yellow
    $dataDir = Join-Path $ScriptDir "data"
    if (-not (Test-Path $dataDir)) {
        New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    }
    $secret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    $dbPath = ($dataDir -replace '\\', '/') + "/cmms.db"
    @"
SECRET_KEY=$secret
DATABASE_URL=sqlite+aiosqlite:///$dbPath
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
ENVIRONMENT=production
"@ | Out-File $envFile -Encoding utf8
    Write-Host "  [OK] Created .env" -ForegroundColor Green
}

Write-Host ""

# Check if already running
$backendRunning = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" }
$frontendRunning = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vite*" }

if ($backendRunning -or $frontendRunning) {
    Write-Host "CMMS appears to already be running." -ForegroundColor Yellow
    Write-Host "Run stop.ps1 first if you want to restart." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press any key to continue anyway or Ctrl+C to cancel..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Start Backend
Write-Host "Starting backend server..." -ForegroundColor Yellow
$backendProcess = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$backendPath'; .\venv\Scripts\Activate.ps1; Write-Host 'Backend starting on http://localhost:8000' -ForegroundColor Green; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
) -PassThru -WindowStyle Normal

Write-Host "  [OK] Backend starting (PID: $($backendProcess.Id))" -ForegroundColor Green

# Wait a moment for backend to initialize
Start-Sleep -Seconds 3

# Start Frontend
Write-Host "Starting frontend server..." -ForegroundColor Yellow
$frontendPath = Join-Path $ScriptDir "frontend"
$frontendProcess = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendPath'; Write-Host 'Frontend starting on http://localhost:5173' -ForegroundColor Green; npm run dev"
) -PassThru -WindowStyle Normal

Write-Host "  [OK] Frontend starting (PID: $($frontendProcess.Id))" -ForegroundColor Green

# Save PIDs for stop script
$pidFile = Join-Path $ScriptDir ".cmms_pids"
@{
    Backend = $backendProcess.Id
    Frontend = $frontendProcess.Id
} | ConvertTo-Json | Out-File $pidFile

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  CMMS is starting up!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Please wait a few seconds for servers to initialize..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Application URL: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "API URL: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Default login:" -ForegroundColor Yellow
Write-Host "  Email: admin@example.com" -ForegroundColor White
Write-Host "  Password: admin123" -ForegroundColor White
Write-Host ""

# Wait and open browser
Start-Sleep -Seconds 5
Write-Host "Opening browser..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "To stop CMMS, run stop.ps1 or close both PowerShell windows." -ForegroundColor Gray
Write-Host ""
