# Diagnose Extension Loading Issues
# Helps identify why the manifest file is missing or unreadable

param(
    [string]$ExtensionPath = "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\chrome-extension"
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Extension Diagnostic Script" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. Check if path exists
Write-Host "1️⃣  Checking extension path..." -ForegroundColor Yellow
Write-Host "   Path: $ExtensionPath" -ForegroundColor Gray

if (Test-Path $ExtensionPath) {
    Write-Host "   ✅ Path exists" -ForegroundColor Green
    $fullPath = Resolve-Path $ExtensionPath
    Write-Host "   Full path: $fullPath" -ForegroundColor Green
} else {
    Write-Host "   ❌ Path does not exist!" -ForegroundColor Red
    exit 1
}

# 2. Check manifest file
Write-Host "`n2️⃣  Checking manifest.json..." -ForegroundColor Yellow
$manifestPath = Join-Path $ExtensionPath "manifest.json"
Write-Host "   Path: $manifestPath" -ForegroundColor Gray

if (Test-Path $manifestPath) {
    Write-Host "   ✅ File exists" -ForegroundColor Green

    # Check file readable
    try {
        $content = Get-Content $manifestPath -Raw -ErrorAction Stop
        Write-Host "   ✅ File is readable" -ForegroundColor Green
        Write-Host "   📄 File size: $((Get-Item $manifestPath).Length) bytes" -ForegroundColor Gray

        # Validate JSON
        try {
            $json = $content | ConvertFrom-Json -ErrorAction Stop
            Write-Host "   ✅ Valid JSON" -ForegroundColor Green
            Write-Host "   📋 Name: $($json.name)" -ForegroundColor Gray
            Write-Host "   📋 Version: $($json.version)" -ForegroundColor Gray
        } catch {
            Write-Host "   ❌ Invalid JSON: $_" -ForegroundColor Red
        }
    } catch {
        Write-Host "   ❌ File not readable: $_" -ForegroundColor Red
    }
} else {
    Write-Host "   ❌ File not found!" -ForegroundColor Red
    Write-Host "   Expected: $manifestPath" -ForegroundColor Red
}

# 3. List extension files
Write-Host "`n3️⃣  Extension files:" -ForegroundColor Yellow
Get-ChildItem $ExtensionPath -File | ForEach-Object {
    Write-Host "   📄 $($_.Name) ($($_.Length) bytes)" -ForegroundColor Gray
}

# 4. Check permissions
Write-Host "`n4️⃣  Checking file permissions..." -ForegroundColor Yellow
try {
    $acl = Get-Acl $ExtensionPath
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $access = $acl.Access | Where-Object { $_.IdentityReference -match $currentUser.Value }

    if ($access) {
        Write-Host "   ✅ Current user has access" -ForegroundColor Green
        Write-Host "   Permissions: $($access.FileSystemRights)" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠️  Current user may not have direct access" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️  Could not determine permissions: $_" -ForegroundColor Yellow
}

# 5. Chrome extension loading info
Write-Host "`n5️⃣  Extension loading information:" -ForegroundColor Yellow
Write-Host "   To manually load the extension:" -ForegroundColor Gray
Write-Host "   1. Open Chrome" -ForegroundColor Gray
Write-Host "   2. Go to chrome://extensions/" -ForegroundColor Gray
Write-Host "   3. Enable 'Developer mode' (top right)" -ForegroundColor Gray
Write-Host "   4. Click 'Load unpacked'" -ForegroundColor Gray
Write-Host "   5. Select: $fullPath" -ForegroundColor Cyan

# 6. Check other extension files
Write-Host "`n6️⃣  Checking required extension files..." -ForegroundColor Yellow
$requiredFiles = @("manifest.json", "content.js", "background.js")
foreach ($file in $requiredFiles) {
    $filePath = Join-Path $ExtensionPath $file
    if (Test-Path $filePath) {
        $size = (Get-Item $filePath).Length
        Write-Host "   ✅ $file ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $file - MISSING!" -ForegroundColor Red
    }
}

# 7. Validate manifest structure
Write-Host "`n7️⃣  Validating manifest.json structure..." -ForegroundColor Yellow
try {
    $manifest = Get-Content $manifestPath | ConvertFrom-Json

    $checks = @(
        @{ Name = "manifest_version"; Required = $true }
        @{ Name = "name"; Required = $true }
        @{ Name = "version"; Required = $true }
        @{ Name = "permissions"; Required = $true }
        @{ Name = "host_permissions"; Required = $true }
        @{ Name = "background"; Required = $true }
        @{ Name = "content_scripts"; Required = $true }
    )

    foreach ($check in $checks) {
        $property = $manifest | Select-Object -ExpandProperty $check.Name -ErrorAction SilentlyContinue
        if ($property -or -not $check.Required) {
            Write-Host "   ✅ $($check.Name): $property" -ForegroundColor Green
        } else {
            Write-Host "   ❌ $($check.Name): MISSING" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "   ❌ Error validating manifest: $_" -ForegroundColor Red
}

# 8. Check content.js and background.js
Write-Host "`n8️⃣  Checking script files..." -ForegroundColor Yellow
$scripts = @("content.js", "background.js")
foreach ($script in $scripts) {
    $scriptPath = Join-Path $ExtensionPath $script
    if (Test-Path $scriptPath) {
        $lines = (Get-Content $scriptPath | Measure-Object -Line).Lines
        Write-Host "   ✅ $script ($lines lines)" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $script - NOT FOUND" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Diagnostic Complete" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "• Extension path: $fullPath" -ForegroundColor Gray
Write-Host "• All files present: $(if ((Test-Path (Join-Path $ExtensionPath 'manifest.json')) -and (Test-Path (Join-Path $ExtensionPath 'content.js')) -and (Test-Path (Join-Path $ExtensionPath 'background.js'))) { '✅' } else { '❌' })" -ForegroundColor Gray
Write-Host "• Manifest valid: $(if ($json) { '✅' } else { '❌' })" -ForegroundColor Gray
Write-Host "`nIf you see any ❌ errors above, those need to be fixed before loading the extension." -ForegroundColor Yellow
