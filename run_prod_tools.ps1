$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Start-Process ".\.venv\Scripts\pythonw.exe" ".\src\app_blocker.pyw" -WindowStyle Hidden
Start-Process ".\.venv\Scripts\pythonw.exe" ".\src\daily_opener.pyw" -WindowStyle Hidden
#Start-Process ".\.venv\Scripts\pythonw.exe" ".\src\shutdown_enforcer.pyw" -WindowStyle Hidden # should be run by the task scheduler instead