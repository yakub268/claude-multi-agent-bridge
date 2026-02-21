# Install Claude Multi-Agent Bridge Extension

Write-Host "Claude Multi-Agent Bridge - Extension Installer" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""

# Check if extension directory exists
$extensionPath = "C:\Users\yakub\.claude-shared\multi_claude_bus\browser_extension"
if (-not (Test-Path $extensionPath)) {
    Write-Host "[ERROR] Extension directory not found: $extensionPath" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Extension directory found" -ForegroundColor Green
Write-Host "     Path: $extensionPath" -ForegroundColor Gray
Write-Host ""

# Check if message bus is running
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5001/api/status" -TimeoutSec 2
    Write-Host "[OK] Message bus is running" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Message bus not running on port 5001" -ForegroundColor Yellow
    Write-Host "       Start with: powershell -File start_server.ps1" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Opening installation instructions..." -ForegroundColor Cyan

# Open instruction page
$instructionPage = "C:\Users\yakub\.claude-shared\multi_claude_bus\INSTALL_EXTENSION.html"
Start-Process $instructionPage

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Extension Path:" -ForegroundColor Yellow
Write-Host $extensionPath -ForegroundColor White
Write-Host ""

# Copy to clipboard
Set-Clipboard -Value $extensionPath
Write-Host "[OK] Path copied to clipboard!" -ForegroundColor Green
Write-Host ""

Write-Host "Quick Install Steps:" -ForegroundColor Cyan
Write-Host "  1. Go to chrome://extensions/" -ForegroundColor Gray
Write-Host "  2. Enable 'Developer mode' (toggle in top-right)" -ForegroundColor Gray
Write-Host "  3. Click 'Load unpacked'" -ForegroundColor Gray
Write-Host "  4. Paste path (Ctrl+V) or browse to folder" -ForegroundColor Gray
Write-Host "  5. Navigate to claude.ai to test" -ForegroundColor Gray
Write-Host ""

# Wait for user
Write-Host "Press Enter when installation is complete..." -ForegroundColor Yellow
Read-Host

# Test connection
Write-Host ""
Write-Host "Testing extension..." -ForegroundColor Cyan

try {
    $messages = Invoke-RestMethod -Uri "http://localhost:5001/api/messages" -TimeoutSec 2
    $browserMessages = $messages.messages | Where-Object { $_.from -eq "browser" }

    if ($browserMessages.Count -gt 0) {
        Write-Host "[OK] Extension is communicating!" -ForegroundColor Green
        Write-Host "     Browser messages: $($browserMessages.Count)" -ForegroundColor Gray
    } else {
        Write-Host "[INFO] No messages from browser yet" -ForegroundColor Yellow
        Write-Host "       Make sure you navigated to claude.ai" -ForegroundColor Gray
    }
} catch {
    Write-Host "[WARN] Could not test (bus may be offline)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[OK] Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  - Open claude.ai" -ForegroundColor White
Write-Host "  - Check DevTools (F12) for [Claude Bridge] logs" -ForegroundColor White
Write-Host "  - Run: python demo.py" -ForegroundColor White
Write-Host ""
