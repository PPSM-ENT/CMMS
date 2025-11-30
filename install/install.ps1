# CMMS Installation Script for Windows 11
# Run as Administrator: Right-click PowerShell -> Run as Administrator
# Then: Set-ExecutionPolicy Bypass -Scope Process -Force; .\install.ps1

param(
    [string]$InstallPath = "C:\CMMS",
    [switch]$SkipPrerequisites
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CMMS Installation Script" -ForegroundColor Cyan
Write-Host "  Target: $InstallPath" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "  1. Right-click PowerShell" -ForegroundColor White
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "  3. Run this script again" -ForegroundColor White
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Create temp directory for downloads
$tempDir = Join-Path $env:TEMP "CMMS_Install"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
}

# Function to check if a command exists
function Test-Command($command) {
    try {
        Get-Command $command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Function to refresh PATH in current session
function Update-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# Function to download file with progress
function Download-File($url, $output) {
    Write-Host "  Downloading from: $url" -ForegroundColor Gray
    try {
        # Use BITS for better download experience
        Start-BitsTransfer -Source $url -Destination $output -DisplayName "Downloading..." -ErrorAction Stop
    } catch {
        # Fallback to WebClient
        Write-Host "  Using fallback download method..." -ForegroundColor Gray
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($url, $output)
    }
}

# Function to install Python
function Install-Python {
    Write-Host ""
    Write-Host "Installing Python 3.12..." -ForegroundColor Yellow

    $pythonUrl = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    $pythonInstaller = Join-Path $tempDir "python-installer.exe"

    Download-File $pythonUrl $pythonInstaller

    Write-Host "  Running Python installer (this may take a few minutes)..." -ForegroundColor Gray

    # Silent install with PATH
    $process = Start-Process -FilePath $pythonInstaller -ArgumentList @(
        "/quiet",
        "InstallAllUsers=1",
        "PrependPath=1",
        "Include_test=0",
        "Include_pip=1",
        "Include_launcher=1"
    ) -Wait -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Host "  [WARNING] Python installer returned code: $($process.ExitCode)" -ForegroundColor Yellow
    }

    # Refresh PATH
    Update-Path
    Start-Sleep -Seconds 2

    # Verify installation
    if (Test-Command "python") {
        $version = python --version 2>&1
        Write-Host "  [OK] Python installed: $version" -ForegroundColor Green
        return $true
    } else {
        # Try to find Python in default location
        $pythonPath = "C:\Program Files\Python312"
        if (Test-Path "$pythonPath\python.exe") {
            $env:Path = "$pythonPath;$pythonPath\Scripts;$env:Path"
            [Environment]::SetEnvironmentVariable("Path", "$pythonPath;$pythonPath\Scripts;" + [Environment]::GetEnvironmentVariable("Path", "Machine"), "Machine")
            Write-Host "  [OK] Python installed and PATH updated" -ForegroundColor Green
            return $true
        }
        Write-Host "  [ERROR] Python installation may have failed" -ForegroundColor Red
        return $false
    }
}

# Function to install Node.js
function Install-NodeJS {
    Write-Host ""
    Write-Host "Installing Node.js 20 LTS..." -ForegroundColor Yellow

    $nodeUrl = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-x64.msi"
    $nodeInstaller = Join-Path $tempDir "node-installer.msi"

    Download-File $nodeUrl $nodeInstaller

    Write-Host "  Running Node.js installer (this may take a few minutes)..." -ForegroundColor Gray

    # Silent install
    $process = Start-Process -FilePath "msiexec.exe" -ArgumentList @(
        "/i",
        "`"$nodeInstaller`"",
        "/quiet",
        "/norestart"
    ) -Wait -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Host "  [WARNING] Node.js installer returned code: $($process.ExitCode)" -ForegroundColor Yellow
    }

    # Refresh PATH
    Update-Path
    Start-Sleep -Seconds 2

    # Verify installation
    if (Test-Command "node") {
        $version = node --version 2>&1
        Write-Host "  [OK] Node.js installed: $version" -ForegroundColor Green
        return $true
    } else {
        # Try to find Node in default location
        $nodePath = "C:\Program Files\nodejs"
        if (Test-Path "$nodePath\node.exe") {
            $env:Path = "$nodePath;$env:Path"
            [Environment]::SetEnvironmentVariable("Path", "$nodePath;" + [Environment]::GetEnvironmentVariable("Path", "Machine"), "Machine")
            Write-Host "  [OK] Node.js installed and PATH updated" -ForegroundColor Green
            return $true
        }
        Write-Host "  [ERROR] Node.js installation may have failed" -ForegroundColor Red
        return $false
    }
}

# Check and install prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

$needsRestart = $false

# Check Python
$hasPython = $false
if (Test-Command "python") {
    $pythonVersion = python --version 2>&1
    Write-Host "  [OK] Python found: $pythonVersion" -ForegroundColor Green
    $hasPython = $true
} else {
    Write-Host "  [MISSING] Python not found" -ForegroundColor Red
    if (-not $SkipPrerequisites) {
        $response = Read-Host "  Install Python automatically? (Y/n)"
        if ($response -ne 'n' -and $response -ne 'N') {
            $hasPython = Install-Python
            $needsRestart = $true
        }
    }
}

# Check Node.js
$hasNode = $false
if (Test-Command "node") {
    $nodeVersion = node --version 2>&1
    Write-Host "  [OK] Node.js found: $nodeVersion" -ForegroundColor Green
    $hasNode = $true
} else {
    Write-Host "  [MISSING] Node.js not found" -ForegroundColor Red
    if (-not $SkipPrerequisites) {
        $response = Read-Host "  Install Node.js automatically? (Y/n)"
        if ($response -ne 'n' -and $response -ne 'N') {
            $hasNode = Install-NodeJS
            $needsRestart = $true
        }
    }
}

# Check npm (comes with Node)
$hasNpm = $false
if (Test-Command "npm") {
    $npmVersion = npm --version 2>&1
    Write-Host "  [OK] npm found: v$npmVersion" -ForegroundColor Green
    $hasNpm = $true
} elseif ($hasNode) {
    # npm should be available if Node was just installed
    Update-Path
    if (Test-Command "npm") {
        $npmVersion = npm --version 2>&1
        Write-Host "  [OK] npm found: v$npmVersion" -ForegroundColor Green
        $hasNpm = $true
    }
}

# Final check
if (-not $hasPython -or -not $hasNode) {
    Write-Host ""
    Write-Host "ERROR: Missing required prerequisites!" -ForegroundColor Red
    Write-Host ""
    if (-not $hasPython) {
        Write-Host "  - Python 3.11+ is required" -ForegroundColor Yellow
        Write-Host "    Download from: https://www.python.org/downloads/" -ForegroundColor White
    }
    if (-not $hasNode) {
        Write-Host "  - Node.js 18+ is required" -ForegroundColor Yellow
        Write-Host "    Download from: https://nodejs.org/" -ForegroundColor White
    }
    Write-Host ""

    if ($needsRestart) {
        Write-Host "Some components were installed but may require a restart." -ForegroundColor Yellow
        Write-Host "Please restart your computer and run this installer again." -ForegroundColor Yellow
    }

    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host ""

# Create installation directory
Write-Host "Creating installation directory..." -ForegroundColor Yellow
if (Test-Path $InstallPath) {
    Write-Host "  Directory already exists. Updating..." -ForegroundColor Yellow
} else {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    Write-Host "  Created $InstallPath" -ForegroundColor Green
}

# Get the script's directory (where the source files are)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceDir = Split-Path -Parent $ScriptDir

Write-Host "  Source: $SourceDir" -ForegroundColor Gray

# Copy backend
Write-Host ""
Write-Host "Copying backend files..." -ForegroundColor Yellow
$backendSource = Join-Path $SourceDir "backend"
$backendDest = Join-Path $InstallPath "backend"

if (-not (Test-Path $backendSource)) {
    Write-Host "  [ERROR] Backend source not found at: $backendSource" -ForegroundColor Red
    exit 1
}

if (Test-Path $backendDest) {
    # Preserve .env and data
    $envBackup = $null
    $envFile = Join-Path $backendDest ".env"
    if (Test-Path $envFile) {
        $envBackup = Get-Content $envFile -Raw
    }

    Remove-Item -Path $backendDest -Recurse -Force
}

Copy-Item -Path $backendSource -Destination $backendDest -Recurse -Exclude @("venv", "__pycache__", "*.pyc", ".pytest_cache")

# Restore .env if it existed
if ($envBackup) {
    $envBackup | Out-File -FilePath (Join-Path $backendDest ".env") -Encoding utf8 -NoNewline
    Write-Host "  [OK] Backend copied (preserved existing config)" -ForegroundColor Green
} else {
    Write-Host "  [OK] Backend copied" -ForegroundColor Green
}

# Copy frontend
Write-Host "Copying frontend files..." -ForegroundColor Yellow
$frontendSource = Join-Path $SourceDir "frontend"
$frontendDest = Join-Path $InstallPath "frontend"

if (-not (Test-Path $frontendSource)) {
    Write-Host "  [ERROR] Frontend source not found at: $frontendSource" -ForegroundColor Red
    exit 1
}

if (Test-Path $frontendDest) {
    Remove-Item -Path $frontendDest -Recurse -Force
}
Copy-Item -Path $frontendSource -Destination $frontendDest -Recurse -Exclude @("node_modules", "dist", ".vite")
Write-Host "  [OK] Frontend copied" -ForegroundColor Green

# Copy install scripts
Write-Host "Copying scripts..." -ForegroundColor Yellow
Get-ChildItem -Path $ScriptDir -File | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $InstallPath -Force
}
Write-Host "  [OK] Scripts copied" -ForegroundColor Green

# Setup backend virtual environment
Write-Host ""
Write-Host "Setting up Python virtual environment..." -ForegroundColor Yellow
Set-Location $backendDest

if (Test-Path "venv") {
    Remove-Item -Path "venv" -Recurse -Force
}

python -m venv venv
if (-not (Test-Path "venv\Scripts\pip.exe")) {
    Write-Host "  [ERROR] Failed to create virtual environment" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Virtual environment created" -ForegroundColor Green

# Activate and install dependencies
Write-Host "Installing Python dependencies (this may take a few minutes)..." -ForegroundColor Yellow
& ".\venv\Scripts\pip.exe" install --upgrade pip -q 2>$null
& ".\venv\Scripts\pip.exe" install -r requirements.txt -q 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [WARNING] Some packages may have had issues, retrying..." -ForegroundColor Yellow
    & ".\venv\Scripts\pip.exe" install -r requirements.txt
}
Write-Host "  [OK] Python dependencies installed" -ForegroundColor Green

# Setup frontend
Write-Host ""
Write-Host "Installing Node.js dependencies (this may take a few minutes)..." -ForegroundColor Yellow
Set-Location $frontendDest
npm install 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [WARNING] Retrying npm install..." -ForegroundColor Yellow
    npm install
}
Write-Host "  [OK] Node.js dependencies installed" -ForegroundColor Green

# Build frontend for production
Write-Host "Building frontend for production..." -ForegroundColor Yellow
npm run build 2>$null
Write-Host "  [OK] Frontend built" -ForegroundColor Green

# Create data directory
$dataDir = Join-Path $InstallPath "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}

# Create .env file if it doesn't exist
$envFile = Join-Path $backendDest ".env"
if (-not (Test-Path $envFile)) {
    Write-Host ""
    Write-Host "Creating default configuration..." -ForegroundColor Yellow
    $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    $dbPath = ($dataDir -replace '\\', '/') + "/cmms.db"
    @"
# CMMS Configuration
SECRET_KEY=$secretKey
DATABASE_URL=sqlite+aiosqlite:///$dbPath
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
ENVIRONMENT=production
"@ | Out-File -FilePath $envFile -Encoding utf8
    Write-Host "  [OK] Configuration created" -ForegroundColor Green
}

# Create desktop shortcuts
Write-Host ""
Write-Host "Creating shortcuts..." -ForegroundColor Yellow

$WshShell = New-Object -ComObject WScript.Shell

# Start CMMS shortcut
$shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Start CMMS.lnk")
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$InstallPath\start.ps1`""
$shortcut.WorkingDirectory = $InstallPath
$shortcut.Description = "Start CMMS Application"
$shortcut.Save()
Write-Host "  [OK] Desktop shortcut created: Start CMMS" -ForegroundColor Green

# Stop CMMS shortcut
$shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Stop CMMS.lnk")
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$InstallPath\stop.ps1`""
$shortcut.WorkingDirectory = $InstallPath
$shortcut.Description = "Stop CMMS Application"
$shortcut.Save()
Write-Host "  [OK] Desktop shortcut created: Stop CMMS" -ForegroundColor Green

# Cleanup temp files
Write-Host ""
Write-Host "Cleaning up..." -ForegroundColor Yellow
if (Test-Path $tempDir) {
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host "  [OK] Cleanup complete" -ForegroundColor Green

Set-Location $InstallPath

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "CMMS has been installed to: $InstallPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start CMMS:" -ForegroundColor Yellow
Write-Host "  1. Double-click 'Start CMMS' on your Desktop" -ForegroundColor White
Write-Host "  2. Or run: $InstallPath\start.ps1" -ForegroundColor White
Write-Host ""
Write-Host "The application will be available at:" -ForegroundColor Yellow
Write-Host "  http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Default login credentials:" -ForegroundColor Yellow
Write-Host "  Email: admin@example.com" -ForegroundColor White
Write-Host "  Password: admin123" -ForegroundColor White
Write-Host ""
Write-Host "To stop CMMS:" -ForegroundColor Yellow
Write-Host "  Double-click 'Stop CMMS' on your Desktop" -ForegroundColor White
Write-Host ""

if ($needsRestart) {
    Write-Host "NOTE: New software was installed. A restart is recommended." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Press any key to close..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
