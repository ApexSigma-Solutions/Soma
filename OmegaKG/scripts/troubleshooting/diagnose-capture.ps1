#!/usr/bin/env pwsh
# Omega_KG Capture Diagnostic Tool
# Identifies why extension stopped capturing on platforms that worked yesterday

Write-Host "`n" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   Ω OMEGA_KG CAPTURE DIAGNOSTICS" -ForegroundColor White
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$extensionPath = "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\chrome-extension"
$localPath = "C:\Omega_KG_Extension"

# 1. Check if files exist
Write-Host "📂 Checking Extension Files..." -ForegroundColor Yellow
$files = @("manifest.json", "content.js", "background.js")
$allFilesExist = $true

foreach ($file in $files) {
    $sourcePath = Join-Path $extensionPath $file
    $localFilePath = Join-Path $localPath $file

    if (Test-Path $sourcePath) {
        Write-Host "   ✓ Source: $file" -ForegroundColor Green

        # Check if local copy exists
        if (Test-Path $localFilePath) {
            # Compare file sizes
            $sourceSize = (Get-Item $sourcePath).Length
            $localSize = (Get-Item $localFilePath).Length

            if ($sourceSize -eq $localSize) {
                Write-Host "   ✓ Local copy: $file (in sync)" -ForegroundColor Green
            } else {
                Write-Host "   ⚠️  Local copy: $file (OUT OF SYNC - Source: $sourceSize bytes, Local: $localSize bytes)" -ForegroundColor Red
                $allFilesExist = $false
            }
        } else {
            Write-Host "   ⚠️  Local copy missing: $file" -ForegroundColor Red
            $allFilesExist = $false
        }
    } else {
        Write-Host "   ✗ Missing: $file" -ForegroundColor Red
        $allFilesExist = $false
    }
}

# 2. Check manifest.json validity
Write-Host "`n🔍 Validating manifest.json..." -ForegroundColor Yellow
$manifestPath = Join-Path $extensionPath "manifest.json"
try {
    $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
    Write-Host "   ✓ Manifest is valid JSON" -ForegroundColor Green
    Write-Host "   ✓ Version: $($manifest.version)" -ForegroundColor Green
    Write-Host "   ✓ Manifest Version: $($manifest.manifest_version)" -ForegroundColor Green

    # Check content_scripts
    if ($manifest.content_scripts) {
        $platforms = $manifest.content_scripts[0].matches.Count
        Write-Host "   ✓ Content scripts configured for $platforms platforms" -ForegroundColor Green
        foreach ($match in $manifest.content_scripts[0].matches) {
            Write-Host "      • $match" -ForegroundColor Gray
        }
    } else {
        Write-Host "   ✗ No content_scripts found!" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Manifest JSON is invalid: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Check content.js for platform detection
Write-Host "`n🎯 Checking Platform Detection..." -ForegroundColor Yellow
$contentPath = Join-Path $extensionPath "content.js"
$contentJs = Get-Content $contentPath -Raw

# Extract detectPlatform function
if ($contentJs -match "detectPlatform\(\)\s*\{([^}]+)\}") {
    Write-Host "   ✓ detectPlatform() function found" -ForegroundColor Green

    # Count platforms
    $platforms = @('claude', 'chatgpt', 'gemini', 'perplexity', 'github_copilot', 'qwen', 'microsoft_copilot')
    foreach ($platform in $platforms) {
        if ($contentJs -match "return\s+'$platform'") {
            Write-Host "      ✓ $platform detection present" -ForegroundColor Green
        } else {
            Write-Host "      ✗ $platform detection MISSING" -ForegroundColor Red
        }
    }
} else {
    Write-Host "   ✗ detectPlatform() function NOT FOUND" -ForegroundColor Red
}

# 4. Check selectors for ChatGPT and Gemini
Write-Host "`n🔎 Checking Critical Selectors..." -ForegroundColor Yellow

# ChatGPT selectors
if ($contentJs -match "chatgpt:\s*\{[^}]*container:\s*['\`"]([^'\`"]+)['\`"]") {
    Write-Host "   ✓ ChatGPT container selector: $($matches[1])" -ForegroundColor Green
} else {
    Write-Host "   ✗ ChatGPT container selector MISSING" -ForegroundColor Red
}

if ($contentJs -match "chatgpt:[^}]*userMsg:\s*['\`"]([^'\`"]+)['\`"]") {
    Write-Host "   ✓ ChatGPT user message selector: $($matches[1])" -ForegroundColor Green
} else {
    Write-Host "   ✗ ChatGPT user message selector MISSING" -ForegroundColor Red
}

# Gemini selectors
if ($contentJs -match "gemini:\s*\{[^}]*container:\s*['\`"]([^'\`"]+)['\`"]") {
    Write-Host "   ✓ Gemini container selector: $($matches[1])" -ForegroundColor Green
} else {
    Write-Host "   ✗ Gemini container selector MISSING" -ForegroundColor Red
}

if ($contentJs -match "gemini:[^}]*userMsg:\s*['\`"]([^'\`"]+)['\`"]") {
    Write-Host "   ✓ Gemini user message selector: $($matches[1])" -ForegroundColor Green
} else {
    Write-Host "   ✗ Gemini user message selector MISSING" -ForegroundColor Red
}

# 5. Check background.js
Write-Host "`n📡 Checking Background Script..." -ForegroundColor Yellow
$backgroundPath = Join-Path $extensionPath "background.js"
$backgroundJs = Get-Content $backgroundPath -Raw

if ($backgroundJs -match "localhost:8765") {
    Write-Host "   ✓ Capture server endpoint: localhost:8765" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Capture server endpoint not found (expected localhost:8765)" -ForegroundColor Yellow
}

if ($backgroundJs -match "chrome\.runtime\.onMessage") {
    Write-Host "   ✓ Message listener registered" -ForegroundColor Green
} else {
    Write-Host "   ✗ Message listener NOT registered" -ForegroundColor Red
}

# 6. Check if capture server is running
Write-Host "`n🚀 Checking Capture Server..." -ForegroundColor Yellow
$captureProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "capture" }
if ($captureProcess) {
    Write-Host "   ✓ Capture server is running (PID: $($captureProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "   ✗ Capture server is NOT running!" -ForegroundColor Red
    Write-Host "      Run: poetry run capture-server" -ForegroundColor Yellow
}

# Test connection to server
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8765/health" -TimeoutSec 2 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✓ Server health check: OK" -ForegroundColor Green
    }
} catch {
    Write-Host "   ✗ Server health check FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# 7. Suggest fixes
Write-Host "`n" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   🔧 RECOMMENDED ACTIONS" -ForegroundColor White
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan

if (-not $allFilesExist) {
    Write-Host "`n1️⃣  SYNC LOCAL EXTENSION COPY:" -ForegroundColor Yellow
    Write-Host "   .\scripts\copy-extension-local.ps1" -ForegroundColor White
}

if (-not $captureProcess) {
    Write-Host "`n2️⃣  START CAPTURE SERVER:" -ForegroundColor Yellow
    Write-Host "   poetry run capture-server" -ForegroundColor White
}

Write-Host "`n3️⃣  RELOAD EXTENSION IN CHROME:" -ForegroundColor Yellow
Write-Host "   1. Open chrome://extensions/" -ForegroundColor White
Write-Host "   2. Find 'Omega_KG Chat Capture'" -ForegroundColor White
Write-Host "   3. Click the reload icon (↻)" -ForegroundColor White

Write-Host "`n4️⃣  REFRESH ALL AI CHAT TABS:" -ForegroundColor Yellow
Write-Host "   • ChatGPT: Press F5" -ForegroundColor White
Write-Host "   • Gemini: Press F5" -ForegroundColor White
Write-Host "   • Claude: Press F5" -ForegroundColor White
Write-Host "   (Must refresh after reloading extension)" -ForegroundColor Gray

Write-Host "`n5️⃣  TEST CAPTURE:" -ForegroundColor Yellow
Write-Host "   1. Open DevTools (F12)" -ForegroundColor White
Write-Host "   2. Go to Console tab" -ForegroundColor White
Write-Host "   3. Look for: [Omega_KG] Started capturing: <platform>" -ForegroundColor White
Write-Host "   4. Send a test message" -ForegroundColor White
Write-Host "   5. Look for: [Omega_KG] ✅ Captured X messages" -ForegroundColor White

Write-Host "`n6️⃣  IF STILL NOT WORKING - CHECK SELECTORS:" -ForegroundColor Yellow
Write-Host "   Platforms update their DOM frequently. Run:" -ForegroundColor Gray
Write-Host "   .\scripts\test-selectors.ps1" -ForegroundColor White

Write-Host "`n════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan
