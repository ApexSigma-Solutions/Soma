param(
    [string]$TargetPath = "C:\Omega_KG_Extension",
    [switch]$OpenChrome,
    [switch]$Watch
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Omega_KG Extension Copy Tool" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$SourcePath = "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\chrome-extension"

# Verify source exists
if (-not (Test-Path $SourcePath)) {
    Write-Host "❌ Source not found: $SourcePath" -ForegroundColor Red
    exit 1
}

# Create/clear target directory
function Copy-ExtensionFiles {
    Write-Host "🔄 Copying Omega_KG Extension to local folder..." -ForegroundColor Cyan

    if (Test-Path $TargetPath) {
        Write-Host "⚠️  Target directory exists, updating..." -ForegroundColor Yellow
        Remove-Item "$TargetPath\*" -Recurse -Force
    } else {
        New-Item -ItemType Directory -Path $TargetPath -Force | Out-Null
    }

    Copy-Item "$SourcePath\*" -Destination $TargetPath -Recurse -Force
    Write-Host "✅ Files copied to: $TargetPath" -ForegroundColor Green

    # Verify
    $files = Get-ChildItem $TargetPath -File | Select-Object -ExpandProperty Name
    Write-Host "`n📂 Extension files:" -ForegroundColor Yellow
    $files | ForEach-Object {
        $size = (Get-Item "$TargetPath\$_").Length
        Write-Host "   • $_ ($size bytes)" -ForegroundColor Gray
    }
}

# Initial copy
Copy-ExtensionFiles

# Show next steps
Write-Host "`n🔗 Use this path in Chrome:" -ForegroundColor Yellow
Write-Host "   $TargetPath" -ForegroundColor Cyan

Write-Host "`n📖 To load in Chrome:" -ForegroundColor Yellow
Write-Host "   1. Open Chrome and go to chrome://extensions/" -ForegroundColor Gray
Write-Host "   2. Enable 'Developer mode' (top right)" -ForegroundColor Gray
Write-Host "   3. Click 'Load unpacked'" -ForegroundColor Gray
Write-Host "   4. Select: $TargetPath" -ForegroundColor Gray

# Open Chrome if requested
if ($OpenChrome) {
    Write-Host "`n🌐 Opening Chrome extensions page..." -ForegroundColor Cyan
    try {
        & "C:\Program Files\Google\Chrome\Application\chrome.exe" "chrome://extensions/" &
        Start-Sleep -Seconds 2
        Write-Host "✅ Chrome opened" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Could not open Chrome: $_" -ForegroundColor Yellow
    }
}

# Watch mode
if ($Watch) {
    Write-Host "`n👀 Watch mode enabled - monitoring for changes..." -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

    $lastCopy = Get-Date

    while ($true) {
        # Check if source files were modified
        $sourceFiles = Get-ChildItem $SourcePath -File -Recurse
        $anyChanged = $false

        foreach ($file in $sourceFiles) {
            if ($file.LastWriteTime -gt $lastCopy) {
                $anyChanged = $true
                break
            }
        }

        if ($anyChanged) {
            Write-Host "`n📝 Changes detected in source, syncing..." -ForegroundColor Yellow
            Copy-ExtensionFiles
            Write-Host "`n⚠️  Remember to reload the extension in Chrome (click the ↻ button)" -ForegroundColor Yellow
            $lastCopy = Get-Date
        }

        Start-Sleep -Seconds 2
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Copy Complete!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
