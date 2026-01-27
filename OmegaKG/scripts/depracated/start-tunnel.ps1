# Start-NgrokTunnel.ps1
Write-Host "Starting Ngrok Tunnel on port 8765..." -ForegroundColor Cyan
Start-Process -FilePath "ngrok" -ArgumentList "http 8765" -NoNewWindow
Start-Sleep -Seconds 3
try {
    $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
    $publicUrl = $tunnels.tunnels[0].public_url
    Write-Host "Ngrok Tunnel Started!" -ForegroundColor Green
    Write-Host "Public URL: $publicUrl" -ForegroundColor Yellow
    Write-Host "Webhook URL: $publicUrl/webhooks/linear" -ForegroundColor Magenta
} catch {
    Write-Error "Failed to retrieve Ngrok URL. Is ngrok running?"
}
