# --- OMEGA_KG CAPTURE HOOK ---
$OmegaServer = "http://localhost:8765/capture/terminal/"
$OmegaSession = [Guid]::NewGuid().ToString()

if (Get-Module PSReadLine) {
    Set-PSReadLineOption -AddToHistoryHandler {
        param($command)
        if ([string]::IsNullOrWhiteSpace($command) -or $command.Length -lt 2) { return }

        $payload = @{
            timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            cwd       = (Get-Location).Path
            command   = $command
            exit_code = $LASTEXITCODE
            session_id = $OmegaSession
            user      = $env:USERNAME
            host      = $env:COMPUTERNAME
        } | ConvertTo-Json -Compress

        Start-Job -ScriptBlock {
            param($json, $url)
            try {
                Invoke-RestMethod -Uri $url -Method Post -Body $json -ContentType "application/json" -TimeoutSec 1 -ErrorAction SilentlyContinue
            } catch {}
        } -ArgumentList $payload, $OmegaServer | Out-Null
        
        Get-Job | Where-Object State -ne 'Running' | Remove-Job
    }
    Write-Host "[OmegaKG] Terminal Capture Hook Active (Session: $OmegaSession)" -ForegroundColor Cyan
} else {
    Write-Warning "[OmegaKG] PSReadLine module not found. Capture disabled."
}
