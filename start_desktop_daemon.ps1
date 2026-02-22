# Auto-start Desktop Claude Client Daemon
# Run this script to start the desktop client in background

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "desktop_client_v2.py"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Starting Desktop Claude Client Daemon" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Claude Desktop is running
$claudeProcess = Get-Process | Where-Object {$_.ProcessName -like "*Claude*" -or $_.MainWindowTitle -like "*Claude*"}

if (-not $claudeProcess) {
    Write-Host "WARNING: Claude Desktop doesn't appear to be running" -ForegroundColor Yellow
    Write-Host "Please start Claude Desktop first, then run this script again." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Found Claude Desktop process: $($claudeProcess.ProcessName)" -ForegroundColor Green
Write-Host ""

# Check if server is running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5001/api/status" -UseBasicParsing -TimeoutSec 2
    Write-Host "Message bus server is running" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "ERROR: Message bus server not running on http://localhost:5001" -ForegroundColor Red
    Write-Host "Please start the server first:" -ForegroundColor Yellow
    Write-Host "  python server_ws.py" -ForegroundColor Cyan
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Start daemon
Write-Host "Starting desktop client daemon..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

python $PythonScript --daemon
