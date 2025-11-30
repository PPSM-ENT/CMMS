# CMMS Installation Script for Windows 11
# Fully automated - installs Python, Node.js, and all dependencies
# Run: Right-click -> Run as Administrator

param(
    [string]$InstallPath = "C:\CMMS"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

function Write-Step($message) {
    Write-Host ""
    Write-Host ">>> $message" -ForegroundColor Cyan
    Write-Host ("-" * 60) -ForegroundColor DarkGray
}

function Write-OK($message) {
    Write-Host "  [OK] $message" -ForegroundColor Green
}

function Write-Warn($message) {
    Write-Host "  [WARN] $message" -ForegroundColor Yellow
}

function Write-Err($message) {
    Write-Host "  [FAIL] $message" -ForegroundColor Red
}

function Write-Info($message) {
    Write-Host "  $message" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CMMS Full Installation Script" -ForegroundColor Cyan
Write-Host "  Target: $InstallPath" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Err "This script must be run as Administrator!"
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "  1. Right-click PowerShell or Terminal" -ForegroundColor White
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

# Refresh PATH
function Update-SessionPath {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# Find Python
function Find-Python {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $paths = @(
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

# Find Node
function Find-Node {
    $cmd = Get-Command node -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $paths = @(
        "C:\Program Files\nodejs\node.exe",
        "$env:LOCALAPPDATA\Programs\nodejs\node.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

# Find npm
function Find-Npm {
    $cmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $node = Find-Node
    if ($node) {
        $npm = Join-Path (Split-Path $node) "npm.cmd"
        if (Test-Path $npm) { return $npm }
    }
    return $null
}

# Download file
function Download-File($url, $output) {
    Write-Info "Downloading: $url"
    try {
        Start-BitsTransfer -Source $url -Destination $output -DisplayName "Downloading..." -ErrorAction Stop
    } catch {
        Write-Info "Using WebClient fallback..."
        (New-Object System.Net.WebClient).DownloadFile($url, $output)
    }
}

# Install Python
function Install-Python {
    Write-Step "Installing Python 3.12"

    $url = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    $installer = Join-Path $tempDir "python-3.12.7-amd64.exe"

    Download-File $url $installer

    Write-Info "Running Python installer (2-3 minutes)..."

    $proc = Start-Process -FilePath $installer -ArgumentList @(
        "/quiet", "InstallAllUsers=1", "PrependPath=1",
        "Include_test=0", "Include_pip=1", "Include_launcher=1"
    ) -Wait -PassThru -NoNewWindow

    if ($proc.ExitCode -eq 0) {
        Write-OK "Python installed"
    } else {
        Write-Warn "Installer returned: $($proc.ExitCode)"
    }

    Update-SessionPath
    Start-Sleep -Seconds 3

    $python = Find-Python
    if ($python) {
        $dir = Split-Path $python
        if ($env:Path -notlike "*$dir*") {
            $env:Path = "$dir;$dir\Scripts;$env:Path"
        }
        return $python
    }
    return $null
}

# Install Node.js
function Install-NodeJS {
    Write-Step "Installing Node.js 20 LTS"

    $url = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-x64.msi"
    $installer = Join-Path $tempDir "node-v20.18.0-x64.msi"

    Download-File $url $installer

    Write-Info "Running Node.js installer (2-3 minutes)..."

    $proc = Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", "`"$installer`"", "/quiet", "/norestart" -Wait -PassThru -NoNewWindow

    if ($proc.ExitCode -eq 0) {
        Write-OK "Node.js installed"
    } else {
        Write-Warn "Installer returned: $($proc.ExitCode)"
    }

    Update-SessionPath
    Start-Sleep -Seconds 3

    $node = Find-Node
    if ($node) {
        $dir = Split-Path $node
        if ($env:Path -notlike "*$dir*") {
            $env:Path = "$dir;$env:Path"
        }
        return $node
    }
    return $null
}

# ============================================
# STEP 1: Check Prerequisites
# ============================================
Write-Step "Checking Prerequisites"

$pythonExe = Find-Python
$nodeExe = Find-Node

if ($pythonExe) {
    $ver = & $pythonExe --version 2>&1
    Write-OK "Python: $ver"
} else {
    Write-Warn "Python not found - installing..."
    $pythonExe = Install-Python
    if (-not $pythonExe) {
        Write-Err "Python installation failed!"
        Write-Host "Install manually from https://python.org" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
}

if ($nodeExe) {
    $ver = & $nodeExe --version 2>&1
    Write-OK "Node.js: $ver"
} else {
    Write-Warn "Node.js not found - installing..."
    $nodeExe = Install-NodeJS
    if (-not $nodeExe) {
        Write-Err "Node.js installation failed!"
        Write-Host "Install manually from https://nodejs.org" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
}

$npmExe = Find-Npm
if (-not $npmExe) {
    Write-Err "npm not found!"
    exit 1
}
Write-OK "npm: $(& $npmExe --version 2>&1)"

# ============================================
# STEP 2: Copy Files
# ============================================
Write-Step "Copying Application Files"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceDir = Split-Path -Parent $ScriptDir

if (-not (Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
}

$backendSrc = Join-Path $SourceDir "backend"
$frontendSrc = Join-Path $SourceDir "frontend"
$backendDest = Join-Path $InstallPath "backend"
$frontendDest = Join-Path $InstallPath "frontend"

if (-not (Test-Path $backendSrc)) {
    Write-Err "Backend not found: $backendSrc"
    exit 1
}

# Backup .env
$envBackup = $null
if (Test-Path (Join-Path $backendDest ".env")) {
    $envBackup = Get-Content (Join-Path $backendDest ".env") -Raw
}

# Copy backend
Write-Info "Copying backend..."
if (Test-Path $backendDest) { Remove-Item $backendDest -Recurse -Force }
Copy-Item $backendSrc $backendDest -Recurse
Get-ChildItem $backendDest -Directory -Recurse -Filter "venv" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $backendDest -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-OK "Backend copied"

if ($envBackup) {
    $envBackup | Out-File (Join-Path $backendDest ".env") -Encoding utf8 -NoNewline
    Write-Info "Restored .env"
}

# Copy frontend
Write-Info "Copying frontend..."
if (Test-Path $frontendDest) { Remove-Item $frontendDest -Recurse -Force }
Copy-Item $frontendSrc $frontendDest -Recurse
Get-ChildItem $frontendDest -Directory -Filter "node_modules" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $frontendDest -Directory -Filter "dist" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-OK "Frontend copied"

# Copy scripts
Copy-Item (Join-Path $ScriptDir "*.ps1") $InstallPath -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $ScriptDir "*.bat") $InstallPath -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $ScriptDir "*.txt") $InstallPath -Force -ErrorAction SilentlyContinue
Write-OK "Scripts copied"

# ============================================
# STEP 3: Python Virtual Environment
# ============================================
Write-Step "Setting Up Python Environment"

Set-Location $backendDest

if (Test-Path "venv") {
    Write-Info "Removing old venv..."
    Remove-Item "venv" -Recurse -Force
}

Write-Info "Creating virtual environment..."
& $pythonExe -m venv venv

$venvPython = Join-Path $backendDest "venv\Scripts\python.exe"
$venvPip = Join-Path $backendDest "venv\Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Err "Failed to create venv"
    exit 1
}
Write-OK "Virtual environment created"

# Upgrade pip
Write-Info "Upgrading pip..."
& $venvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null
Write-OK "pip upgraded"

# ============================================
# STEP 4: Install Python Packages
# ============================================
Write-Step "Installing Python Packages (3-5 min)"

Write-Host ""
& $venvPip install -r requirements.txt 2>&1 | ForEach-Object {
    if ($_ -match "Successfully installed") {
        Write-Host $_ -ForegroundColor Green
    } elseif ($_ -match "error|Error|ERROR") {
        Write-Host $_ -ForegroundColor Red
    } else {
        Write-Host $_ -ForegroundColor Gray
    }
}

# Verify
$packages = @("fastapi", "uvicorn", "sqlalchemy", "pydantic", "aiosqlite")
$allOK = $true
Write-Host ""
foreach ($pkg in $packages) {
    $check = & $venvPip show $pkg 2>&1
    if ($check -match "Name:") {
        Write-OK "$pkg"
    } else {
        Write-Err "$pkg NOT INSTALLED"
        $allOK = $false
    }
}

if (-not $allOK) {
    Write-Warn "Some packages missing - trying again..."
    & $venvPip install -r requirements.txt
}

# ============================================
# STEP 5: Install Node Packages
# ============================================
Write-Step "Installing Node.js Packages (3-5 min)"

Set-Location $frontendDest

Write-Host ""
& $npmExe install 2>&1 | ForEach-Object {
    if ($_ -match "added|packages") {
        Write-Host $_ -ForegroundColor Green
    } elseif ($_ -match "WARN") {
        Write-Host $_ -ForegroundColor Yellow
    } elseif ($_ -match "ERR") {
        Write-Host $_ -ForegroundColor Red
    } else {
        Write-Host $_ -ForegroundColor Gray
    }
}

if (Test-Path "node_modules") {
    $count = (Get-ChildItem "node_modules" -Directory).Count
    Write-OK "node_modules: $count packages"
} else {
    Write-Err "node_modules not created!"
}

# ============================================
# STEP 6: Build Frontend
# ============================================
Write-Step "Building Frontend"

& $npmExe run build 2>&1 | ForEach-Object { Write-Host $_ -ForegroundColor Gray }

if (Test-Path "dist") {
    Write-OK "Frontend built"
} else {
    Write-Warn "Build may have failed - will use dev mode"
}

# ============================================
# STEP 7: Configuration
# ============================================
Write-Step "Creating Configuration"

$dataDir = Join-Path $InstallPath "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}
Write-OK "Data directory: $dataDir"

$envFile = Join-Path $backendDest ".env"
if (-not (Test-Path $envFile)) {
    $secret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    $dbPath = ($dataDir -replace '\\', '/') + "/cmms.db"

    @"
# CMMS Configuration
SECRET_KEY=$secret
DATABASE_URL=sqlite+aiosqlite:///$dbPath
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
ENVIRONMENT=production
"@ | Out-File $envFile -Encoding utf8
    Write-OK "Created .env"
} else {
    Write-Info ".env exists - keeping"
}

# ============================================
# STEP 8: Desktop Shortcuts
# ============================================
Write-Step "Creating Shortcuts"

try {
    $shell = New-Object -ComObject WScript.Shell

    $s = $shell.CreateShortcut("$env:USERPROFILE\Desktop\Start CMMS.lnk")
    $s.TargetPath = "powershell.exe"
    $s.Arguments = "-ExecutionPolicy Bypass -File `"$InstallPath\start.ps1`""
    $s.WorkingDirectory = $InstallPath
    $s.Save()
    Write-OK "Start CMMS shortcut"

    $s = $shell.CreateShortcut("$env:USERPROFILE\Desktop\Stop CMMS.lnk")
    $s.TargetPath = "powershell.exe"
    $s.Arguments = "-ExecutionPolicy Bypass -File `"$InstallPath\stop.ps1`""
    $s.WorkingDirectory = $InstallPath
    $s.Save()
    Write-OK "Stop CMMS shortcut"
} catch {
    Write-Warn "Could not create shortcuts"
}

# ============================================
# STEP 9: Cleanup
# ============================================
Write-Step "Cleanup"
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
Write-OK "Done"

# ============================================
# COMPLETE
# ============================================
Set-Location $InstallPath

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  INSTALLATION COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Installed to: $InstallPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "TO START:" -ForegroundColor Yellow
Write-Host "  Double-click 'Start CMMS' on Desktop" -ForegroundColor White
Write-Host ""
Write-Host "URL: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "LOGIN:" -ForegroundColor Yellow
Write-Host "  Email:    admin@example.com" -ForegroundColor White
Write-Host "  Password: admin123" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to close"
