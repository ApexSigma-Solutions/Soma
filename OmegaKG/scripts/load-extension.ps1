# Load Chrome Extension Helper Script
# Loads the unpacked Omega_KG extension into Chrome and performs validation checks

# Requires: Chrome/Chromium browser, extension files in chrome-extension/

param(
    [string]$ExtensionPath = "./chrome-extension",
    [string]$BrowserPath = "C:\Program Files\Google\Chrome\Application\chrome.exe",
    [switch]$AutoReload,
    [switch]$ValidateOnly
)

function Write-Header {
    param([string]$Message)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Cyan
}

# Validate extension directory
Write-Header "Validating Extension Files"

if (-not (Test-Path $ExtensionPath)) {
    Write-Error "Extension path not found: $ExtensionPath"
    exit 1
}

Write-Success "Extension directory found: $(Resolve-Path $ExtensionPath)"

# Check for required files
$RequiredFiles = @("manifest.json", "content.js", "background.js")
foreach ($file in $RequiredFiles) {
    $filePath = Join-Path $ExtensionPath $file
    if (Test-Path $filePath) {
        Write-Success "$file exists"
    } else {
        Write-Error "$file missing!"
        exit 1
    }
}

# Validate manifest.json
Write-Info "Validating manifest.json..."
try {
    $manifestPath = Join-Path $ExtensionPath "manifest.json"
    $manifest = Get-Content $manifestPath | ConvertFrom-Json
    Write-Success "Manifest is valid JSON"
    Write-Info "Extension name: $($manifest.name)"
    Write-Info "Version: $($manifest.version)"
    Write-Info "Permissions: $($manifest.permissions -join ', ')"
} catch {
    Write-Error "Invalid manifest.json: $_"
    exit 1
}

# Validate manifest hosts
Write-Info "Checking host_permissions..."
$hosts = $manifest.host_permissions
$expectedHosts = @("claude.ai", "openai.com", "gemini.google.com", "perplexity.ai", "github.com", "qwen.ai", "microsoft.com", "copilot")
foreach ($hostPattern in $expectedHosts) {
    $found = $hosts | Where-Object { $_ -match $hostPattern }
    if ($found) {
        Write-Success "Host permission found: $hostPattern"
    } else {
        Write-Warning "Host permission missing: $hostPattern"
    }
}

# Check selectors in content.js
Write-Header "Validating Selectors in content.js"
$contentPath = Join-Path $ExtensionPath "content.js"
$contentJs = Get-Content $contentPath -Raw

$selectorChecks = @{
    "Gemini container" = "\[role=`"main`"\]"
    "Gemini user messages" = "data-blocks-role=`"message`".*data-message-role=`"user`""
    "Gemini assistant messages" = "data-message-role=`"model`""
    "ChatGPT selectors" = "data-message-author-role"
    "Claude selectors" = "data-is-streaming"
}

foreach ($label in $selectorChecks.Keys) {
    $selector = $selectorChecks[$label]
    if ($contentJs -match $selector) {
        Write-Success "$label found"
    } else {
        Write-Warning "$label not found in content.js"
    }
}

if ($ValidateOnly) {
    Write-Header "Validation Complete"
    Write-Info "Run without -ValidateOnly flag to load the extension"
    exit 0
}

# Load extension in Chrome
Write-Header "Loading Extension in Chrome"

if (-not (Test-Path $BrowserPath)) {
    Write-Warning "Chrome not found at default path: $BrowserPath"
    Write-Info "Please open Chrome manually and follow these steps:"
    Write-Info "1. Open chrome://extensions"
    Write-Info "2. Toggle 'Developer mode' ON (top right)"
    Write-Info "3. Click 'Load unpacked'"
    Write-Info "4. Select this directory: $(Resolve-Path $ExtensionPath)"
    exit 0
}

Write-Info "Chrome found at: $BrowserPath"

try {
    $extensionAbsPath = Resolve-Path $ExtensionPath
    Write-Info "Opening Chrome extensions page..."

    # Try to open extensions page (will open if Chrome is not already running)
    & "$BrowserPath" --new-window "chrome://extensions/" --profile-directory=Default

    Write-Success "Chrome opened to extensions page"
    Write-Header "Manual Steps Required"
    Write-Info "1. Toggle 'Developer mode' ON (top right corner)"
    Write-Info "2. Click 'Load unpacked'"
    Write-Info "3. Select this folder: $extensionAbsPath"
    Write-Info ""
    Write-Info "Extension path (copy-paste in dialog):"
    Write-Host $extensionAbsPath -ForegroundColor Yellow

} catch {
    Write-Error "Failed to open Chrome: $_"
    Write-Info "Please manually open chrome://extensions and load the unpacked extension from:"
    Write-Host $(Resolve-Path $ExtensionPath) -ForegroundColor Yellow
    exit 1
}

Write-Header "Next Steps"
Write-Info "1. In Chrome DevTools on the extension page, check 'Service worker' console"
Write-Info "2. Navigate to a target site (Gemini, ChatGPT, etc.)"
Write-Info "3. Open DevTools (F12) and check Console for [Omega_KG] messages"
Write-Info "4. Ensure capture-server is running: poetry run capture-server"
Write-Info "5. Test by starting a conversation and checking if messages are captured"

Write-Header "Troubleshooting"
Write-Info "If extension doesn't capture messages:"
Write-Info "  • Check content.js selectors in DevTools Console"
Write-Info "  • Verify manifest.json has correct host_permissions"
Write-Info "  • Ensure capture-server is running on localhost:8765"
Write-Info "  • Check background service worker console for errors"

Write-Info "Reload extension by clicking the reload icon on chrome://extensions"

Write-Success "Extension loader script completed!"
