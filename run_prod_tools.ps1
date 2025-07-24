$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Start-Process ".\.venv\Scripts\pythonw.exe" ".\browser_blocker.pyw" -WindowStyle Hidden
Start-Process ".\.venv\Scripts\pythonw.exe" ".\shutdown_enforcer.pyw" -WindowStyle Hidden
Start-Process ".\.venv\Scripts\pythonw.exe" ".\daily_opener.pyw" -WindowStyle Hidden
