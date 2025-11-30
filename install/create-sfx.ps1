# Create Self-Extracting Archive for CMMS
# This script packages CMMS into a single executable installer

param(
    [string]$OutputPath = "F:\SteamRIP\CMMS_Installer.exe"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CMMS Self-Extracting Archive Creator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceDir = Split-Path -Parent $ScriptDir

# Create temp directory
$tempDir = Join-Path $env:TEMP "CMMS_SFX_Build"
if (Test-Path $tempDir) {
    Remove-Item -Path $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

$archiveDir = Join-Path $tempDir "CMMS"
New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null

Write-Host "Copying files..." -ForegroundColor Yellow

# Copy backend (excluding venv and cache)
Write-Host "  Copying backend..." -ForegroundColor Gray
$backendDest = Join-Path $archiveDir "backend"
Copy-Item -Path (Join-Path $SourceDir "backend") -Destination $backendDest -Recurse
# Remove excluded items
Get-ChildItem -Path $backendDest -Directory -Recurse -Filter "venv" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $backendDest -Directory -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $backendDest -Directory -Recurse -Filter ".pytest_cache" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $backendDest -File -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue

# Copy frontend (excluding node_modules and dist)
Write-Host "  Copying frontend..." -ForegroundColor Gray
$frontendDest = Join-Path $archiveDir "frontend"
Copy-Item -Path (Join-Path $SourceDir "frontend") -Destination $frontendDest -Recurse
# Remove excluded items
Get-ChildItem -Path $frontendDest -Directory -Filter "node_modules" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $frontendDest -Directory -Filter "dist" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $frontendDest -Directory -Filter ".vite" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Copy install scripts
Write-Host "  Copying install scripts..." -ForegroundColor Gray
$installDest = Join-Path $archiveDir "install"
New-Item -ItemType Directory -Path $installDest -Force | Out-Null
Copy-Item -Path (Join-Path $ScriptDir "*.ps1") -Destination $installDest -Force
Copy-Item -Path (Join-Path $ScriptDir "*.bat") -Destination $installDest -Force
Copy-Item -Path (Join-Path $ScriptDir "*.txt") -Destination $installDest -Force -ErrorAction SilentlyContinue

Write-Host "  [OK] Files copied" -ForegroundColor Green

# Create the ZIP archive
Write-Host ""
Write-Host "Creating ZIP archive..." -ForegroundColor Yellow
$zipPath = Join-Path $tempDir "CMMS.zip"
Compress-Archive -Path $archiveDir -DestinationPath $zipPath -CompressionLevel Optimal
$zipSize = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
Write-Host "  [OK] ZIP created ($zipSize MB)" -ForegroundColor Green

# Create self-extracting PowerShell script
Write-Host ""
Write-Host "Creating self-extracting installer..." -ForegroundColor Yellow

# Read ZIP as base64
$zipBytes = [System.IO.File]::ReadAllBytes($zipPath)
$zipBase64 = [System.Convert]::ToBase64String($zipBytes)

# Create the SFX script
$sfxScript = @'
# CMMS Self-Extracting Installer
# Generated automatically - do not edit

$ErrorActionPreference = "Stop"

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CMMS Self-Extracting Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Create temp extraction directory
$extractDir = Join-Path $env:TEMP "CMMS_Extract_$([System.Guid]::NewGuid().ToString('N').Substring(0,8))"
New-Item -ItemType Directory -Path $extractDir -Force | Out-Null

Write-Host "Extracting files..." -ForegroundColor Yellow

# Embedded ZIP data (base64)
$zipBase64 = @"
__ZIP_DATA_PLACEHOLDER__
"@

try {
    # Decode and save ZIP
    $zipPath = Join-Path $extractDir "CMMS.zip"
    $zipBytes = [System.Convert]::FromBase64String($zipBase64)
    [System.IO.File]::WriteAllBytes($zipPath, $zipBytes)

    # Extract ZIP
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
    Write-Host "  [OK] Files extracted" -ForegroundColor Green

    # Run the installer
    Write-Host ""
    Write-Host "Starting installation..." -ForegroundColor Yellow
    $installerPath = Join-Path $extractDir "CMMS\install\install.ps1"

    if (Test-Path $installerPath) {
        & $installerPath
    } else {
        Write-Host "ERROR: Installer not found at: $installerPath" -ForegroundColor Red
        Write-Host "Contents of extract directory:" -ForegroundColor Yellow
        Get-ChildItem -Path $extractDir -Recurse -Depth 2 | ForEach-Object { Write-Host $_.FullName }
    }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    # Cleanup
    Write-Host ""
    Write-Host "Cleaning up temporary files..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
    Remove-Item -Path $extractDir -Recurse -Force -ErrorAction SilentlyContinue
}
'@

# Insert the ZIP data
$sfxScript = $sfxScript -replace '__ZIP_DATA_PLACEHOLDER__', $zipBase64

# Save as PS1
$ps1Path = Join-Path $tempDir "CMMS_Installer.ps1"
$sfxScript | Out-File -FilePath $ps1Path -Encoding UTF8

Write-Host "  [OK] Self-extracting script created" -ForegroundColor Green

# Create a batch launcher that works from network drives
Write-Host ""
Write-Host "Creating launcher batch file..." -ForegroundColor Yellow

$batchLauncher = @"
@echo off
title CMMS Installer
echo.
echo ========================================
echo   CMMS Self-Extracting Installer
echo ========================================
echo.
echo This installer will:
echo   1. Extract CMMS files
echo   2. Install Python 3.12 (if needed)
echo   3. Install Node.js 20 (if needed)
echo   4. Install CMMS to C:\CMMS
echo.
echo Press any key to continue or close this window to cancel...
pause > nul

:: Copy to temp and run from there (required for network drives)
set "TEMP_PS1=%TEMP%\CMMS_Installer_%RANDOM%.ps1"
copy "%~dp0CMMS_Installer.ps1" "%TEMP_PS1%" > nul

:: Run with admin privileges
powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%TEMP_PS1%\"' -Verb RunAs -Wait"

:: Cleanup
del "%TEMP_PS1%" 2>nul

echo.
echo Installation complete. You can close this window.
pause
"@

$batchPath = Join-Path $tempDir "CMMS_Installer.bat"
$batchLauncher | Out-File -FilePath $batchPath -Encoding ASCII

Write-Host "  [OK] Batch launcher created" -ForegroundColor Green

# Copy final files to output location
Write-Host ""
Write-Host "Copying to output location..." -ForegroundColor Yellow

$outputDir = Split-Path -Parent $OutputPath
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# Copy both files
$finalPs1 = $OutputPath -replace '\.exe$', '.ps1'
$finalBat = $OutputPath -replace '\.exe$', '.bat'

Copy-Item -Path $ps1Path -Destination $finalPs1 -Force
Copy-Item -Path $batchPath -Destination $finalBat -Force

# Get file sizes
$ps1Size = [math]::Round((Get-Item $finalPs1).Length / 1MB, 2)

Write-Host "  [OK] Files created:" -ForegroundColor Green
Write-Host "       $finalBat (launcher)" -ForegroundColor White
Write-Host "       $finalPs1 ($ps1Size MB)" -ForegroundColor White

# Cleanup temp
Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Self-Extracting Archive Created!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To install from a network drive:" -ForegroundColor Yellow
Write-Host "  1. Copy both files to your network share" -ForegroundColor White
Write-Host "  2. Double-click CMMS_Installer.bat" -ForegroundColor White
Write-Host ""
Write-Host "The batch file handles network drive limitations" -ForegroundColor Gray
Write-Host "by copying to temp before running." -ForegroundColor Gray
Write-Host ""
