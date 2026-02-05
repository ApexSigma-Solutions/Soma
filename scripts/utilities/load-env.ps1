# Load .env file into current PowerShell session
param(
    [Parameter(Mandatory=$true)]
    [string]$EnvFilePath
)

if (-not (Test-Path $EnvFilePath)) {
    Write-Error "Environment file not found: $EnvFilePath"
    exit 1
}

Write-Host "Loading environment from: $EnvFilePath" -ForegroundColor Cyan

Get-Content $EnvFilePath | ForEach-Object {
    $line = $_.Trim()
    
    # Skip empty lines and comments
    if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) {
        return
    }
    
    # Parse key=value
    if ($line -match '^([^=]+)=(.*)$') {
        $key = $Matches[1].Trim()
        $value = $Matches[2].Trim()
        
        # Remove quotes if present
        if ($value -match '^"(.*)"$' -or $value -match "^'(.*)'$") {
            $value = $Matches[1]
        }
        
        # Set environment variable
        [System.Environment]::SetEnvironmentVariable($key, $value, [System.EnvironmentVariableTarget]::Process)
        Write-Host "  Set: $key" -ForegroundColor Green
    }
}

Write-Host "Environment loaded successfully!" -ForegroundColor Green
