# install_watchdog.ps1
# Run once as Administrator (or as your own user – no admin required).
# Registers watchdawg.pyw as a Task Scheduler job that starts at logon
# and runs silently in the background (no console window).
#
# Usage:
#   Right-click → "Run with PowerShell"
#   OR from an elevated prompt:
#       powershell -ExecutionPolicy Bypass -File install_watchdog.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths ──────────────────────────────────────────────────────────────────────
$ScriptSource = Join-Path $PSScriptRoot "src\watchdawg.pyw"
$InstallDir   = Join-Path $env:APPDATA "Watchdawg"
$ScriptDest   = Join-Path $InstallDir  "watchdawg.pyw"

# Locate pythonw.exe (suppresses the console window)
$PythonW = (Get-Command pythonw.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
if (-not $PythonW) {
    # Fall back: derive from python.exe path
    $Python  = (Get-Command python.exe -ErrorAction Stop).Source
    $PythonW = Join-Path (Split-Path $Python) "pythonw.exe"
    if (-not (Test-Path $PythonW)) {
        Write-Error "pythonw.exe not found alongside python.exe at $Python"
        exit 1
    }
}

$TaskName = "Watchdawg"

# ── Copy script to install dir ─────────────────────────────────────────────────
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item -Path $ScriptSource -Destination $ScriptDest -Force
Write-Host "Installed script to: $ScriptDest"

# ── Register Task Scheduler job ────────────────────────────────────────────────
$Action  = New-ScheduledTaskAction `
               -Execute $PythonW `
               -Argument "`"$ScriptDest`""

# Trigger: at logon of the current user
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"

$Settings = New-ScheduledTaskSettingsSet `
                -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
                -StartWhenAvailable

# Remove any previous registration silently
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $Action `
    -Trigger   $Trigger `
    -Settings  $Settings `
    -RunLevel  Limited `
    -Force | Out-Null

Write-Host "Task '$TaskName' registered. It will start at your next logon."
Write-Host "To start it right now without rebooting, run:"
Write-Host "    Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Logs will appear at: $InstallDir\watchdog.log"