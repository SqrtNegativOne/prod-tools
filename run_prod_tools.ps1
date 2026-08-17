$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Start-Process ".\.venv\Scripts\pythonw.exe" ".\src\window_limiter.pyw" -WindowStyle Hidden