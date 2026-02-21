# Start Multi-Claude Message Bus Server
# Run with: powershell -File start_server.ps1

$ErrorActionPreference = "Stop"

# Check if already running
$existing = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*server.py*"
}

if ($existing) {
    Write-Host "⚠️  Server already running (PID: $($existing.Id))"
    Write-Host "   Use stop_server.ps1 to stop it first"
    exit 0
}

# Start server
Write-Host "🚀 Starting Multi-Claude Message Bus..."
$serverPath = Join-Path $PSScriptRoot "server.py"

Start-Process python -ArgumentList $serverPath -NoNewWindow -RedirectStandardOutput (Join-Path $PSScriptRoot "server.log") -RedirectStandardError (Join-Path $PSScriptRoot "server.error.log")

# Wait for startup
Start-Sleep -Seconds 2

# Test connection
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5001/api/status" -TimeoutSec 3
    Write-Host "✅ Server started successfully!"
    Write-Host "   Status: $($response.status)"
    Write-Host "   URL: http://localhost:5001"
    Write-Host "   Logs: $PSScriptRoot\server.log"
} catch {
    Write-Host "❌ Server failed to start. Check logs:"
    Write-Host "   $PSScriptRoot\server.log"
    Write-Host "   $PSScriptRoot\server.error.log"
    exit 1
}
