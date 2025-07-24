$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath
& ".\.venv\Scripts\python.exe" ".\browser_blocker.pyw"
& ".\.venv\Scripts\python.exe" ".\shutdown_enforcer.pyw"
& ".\.venv\Scripts\python.exe" ".\daily_opener.pyw"