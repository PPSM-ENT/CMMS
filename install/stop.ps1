# CMMS Stop Script
# Stops backend and frontend servers

$ErrorActionPreference = "SilentlyContinue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Stopping CMMS Application" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Try to read saved PIDs
$pidFile = Join-Path $ScriptDir ".cmms_pids"
if (Test-Path $pidFile) {
    $pids = Get-Content $pidFile | ConvertFrom-Json

    if ($pids.Backend) {
        Write-Host "Stopping backend (PID: $($pids.Backend))..." -ForegroundColor Yellow
        Stop-Process -Id $pids.Backend -Force -ErrorAction SilentlyContinue
    }

    if ($pids.Frontend) {
        Write-Host "Stopping frontend (PID: $($pids.Frontend))..." -ForegroundColor Yellow
        Stop-Process -Id $pids.Frontend -Force -ErrorAction SilentlyContinue
    }

    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# Also kill any remaining processes by name pattern
Write-Host "Cleaning up any remaining processes..." -ForegroundColor Yellow

# Kill uvicorn/python backend processes
Get-Process -Name "python" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        if ($cmdLine -like "*uvicorn*app.main*") {
            Write-Host "  Stopping Python process (PID: $($_.Id))" -ForegroundColor Gray
            Stop-Process -Id $_.Id -Force
        }
    } catch {}
}

# Kill vite/node frontend processes
Get-Process -Name "node" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        if ($cmdLine -like "*vite*" -or $cmdLine -like "*esbuild*") {
            Write-Host "  Stopping Node process (PID: $($_.Id))" -ForegroundColor Gray
            Stop-Process -Id $_.Id -Force
        }
    } catch {}
}

# Kill any processes on our ports
$portsToCheck = @(8000, 5173)
foreach ($port in $portsToCheck) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        if ($conn.OwningProcess -gt 0) {
            Write-Host "  Freeing port $port (PID: $($conn.OwningProcess))" -ForegroundColor Gray
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  CMMS has been stopped" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to close..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
