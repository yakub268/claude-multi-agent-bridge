# Stop Multi-Claude Message Bus Server

$processes = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*server.py*"
}

if ($processes) {
    Write-Host "🛑 Stopping server (PID: $($processes.Id))..."
    $processes | Stop-Process -Force
    Write-Host "✅ Server stopped"
} else {
    Write-Host "ℹ️  No server process found"
}
