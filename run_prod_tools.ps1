$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath
Start-Process ".\.venv\Scripts\python.exe" ".\browser_blocker.pyw"
Start-Process ".\.venv\Scripts\python.exe" ".\shutdown_enforcer.pyw"
Start-Process ".\.venv\Scripts\python.exe" ".\daily_opener.pyw"
