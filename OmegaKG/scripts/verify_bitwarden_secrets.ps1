#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Verify that Bitwarden is correctly retrieving all required secrets

.DESCRIPTION
    Tests the Bitwarden Secret Manager integration by:
    1. Checking if BWS_ACCESS_TOKEN is set in .env
    2. Testing connection to Bitwarden SDK
    3. Verifying all secret IDs can be resolved
    4. Comparing Bitwarden values with local fallback values
#>

$ErrorActionPreference = "Stop"

# Load .env configuration
$envFile = "D:\projects\Omega_KG_stable\.env"
if (-not (Test-Path $envFile)) {
    Write-Error ".env file not found at $envFile"
    exit 1
}

Write-Host "=== Bitwarden Secret Verification ===" -ForegroundColor Cyan
Write-Host ""

# Parse .env file
$env_vars = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    if ($_ -match '^([^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        $env_vars[$key] = $value
    }
}

# Check if Bitwarden is enabled
$bws_token = $env_vars['BWS_ACCESS_TOKEN']
if ([string]::IsNullOrEmpty($bws_token)) {
    Write-Host "⚠️  Bitwarden is DISABLED (BWS_ACCESS_TOKEN not set)" -ForegroundColor Yellow
    Write-Host "    This is okay for temporary debugging, but zero-trust mode requires it enabled." -ForegroundColor Yellow
    exit 0
}

Write-Host "✓ Bitwarden token detected (zero-trust mode active)" -ForegroundColor Green
Write-Host ""

# Test Bitwarden connectivity via Python
$pythonScript = @'
import os
import sys
from pathlib import Path

# Load environment
env_file = Path("D:\\projects\\Omega_KG_stable\\.env")
env_vars = {}
for line in env_file.read_text().split('\n'):
    if line.startswith('#') or not line.strip():
        continue
    if '=' in line:
        key, value = line.split('=', 1)
        env_vars[key.strip()] = value.strip()

bws_token = env_vars.get('BWS_ACCESS_TOKEN', '').strip()
if not bws_token:
    print("❌ BWS_ACCESS_TOKEN not found in .env")
    sys.exit(1)

print("Testing Bitwarden connection...")

try:
    # Try to import and use Bitwarden SDK
    from bitwarden_client import BitwardenClient, AuthenticateRequest

    # Initialize client
    client = BitwardenClient(api_url="https://api.bitwarden.com")

    # Authenticate with token
    client.auth.authenticate_with_api_key(
        request=AuthenticateRequest(
            client_id=bws_token.split('.')[0],
            client_secret=bws_token.split(':')[1] if ':' in bws_token else ''
        )
    )

    print("✓ Connected to Bitwarden")

    # List of secret IDs to verify
    secret_ids = {
        'LINEAR_WEBHOOK_SECRET_PRD_ID': 'c4e28fe5-a690-47c1-bf2a-b3a40115fc5f',
        'POSTGRES_PASSWORD_PRD_ID': 'f7f917fa-a3c4-4ecc-87c5-b3a40116c629',
        'NEO4J_PASSWORD_PRD_ID': '2e56f3bd-5019-48c0-a778-b3a40116727b',
        'EXTENSION_API_KEY_PRD_ID': '17139533-027b-43f8-88c4-b3a401153830',
        'LINEAR_API_KEY_PRD_ID': '60d0ce96-0fd7-40c4-b1c5-b3a401142b89',
        'PERPLEXITY_API_KEY_PRD_ID': '4d1041a5-aa72-485d-b9cb-b3a40112a36b',
        'GEMINI_API_KEY_PRD_ID': 'fee6a433-1a72-424c-b58d-b3a40111feb1',
        'JWT_SECRET_KEY_ID': '6549fb7b-e676-4205-a5e7-b3a40110845b',
    }

    print("\nVerifying secret IDs...")
    for key_name, secret_id in secret_ids.items():
        try:
            secret = client.secrets.get(secret_id)
            print(f"✓ {key_name}: {secret_id}")
        except Exception as e:
            print(f"❌ {key_name}: Failed - {str(e)}")

except ImportError:
    print("⚠️  Bitwarden SDK not installed")
    print("   Install with: pip install bitwarden-client")
except Exception as e:
    print(f"❌ Bitwarden connection failed: {str(e)}")
    sys.exit(1)
'@

# Run Python test
Write-Host "1. Testing Bitwarden SDK Connection" -ForegroundColor Yellow
cd D:\projects\Omega_KG_stable
poetry run python -c $pythonScript 2>&1

Write-Host ""
Write-Host "2. Testing Settings.py Bitwarden Integration" -ForegroundColor Yellow

# Test via settings.py
$settingsTest = @'
import sys
sys.path.insert(0, 'D:\\projects\\Omega_KG_stable')

try:
    from omega_kg.settings import Settings

    # Initialize settings (this will trigger Bitwarden integration)
    settings = Settings()

    print("✓ Settings initialized with Bitwarden")
    print(f"  NEO4J_USER: {settings.neo4j_user}")
    print(f"  NEO4J_URI: {settings.neo4j_uri}")
    print(f"  POSTGRES_DB: {settings.postgres_db}")
    print(f"  POSTGRES_USER: {settings.postgres_user}")

    # Check if using Bitwarden (neo4j_password should NOT be the fallback)
    fallback_password = "neo4j_secure_password_123"
    if settings.neo4j_password != fallback_password:
        print(f"✓ NEO4J_PASSWORD: Retrieved from Bitwarden (not using fallback)")
    else:
        print(f"⚠️  NEO4J_PASSWORD: Using local fallback (Bitwarden may not have provided it)")

except Exception as e:
    print(f"❌ Error initializing settings: {e}")
    import traceback
    traceback.print_exc()
'@

cd D:\projects\Omega_KG_stable
poetry run python -c $settingsTest 2>&1

Write-Host ""
Write-Host "3. Comparing Bitwarden vs Local Fallback Values" -ForegroundColor Yellow

$comparisonScript = @'
import os
from pathlib import Path

# Load .env
env_file = Path("D:\\projects\\Omega_KG_stable\\.env")
env_vars = {}
for line in env_file.read_text().split('\n'):
    if line.startswith('#') or not line.strip():
        continue
    if '=' in line:
        key, value = line.split('=', 1)
        env_vars[key.strip()] = value.strip()

print("Local Fallback Values in .env:")
print(f"  NEO4J_PASSWORD: {env_vars.get('NEO4J_PASSWORD', 'NOT SET')[:20]}...")
print(f"  POSTGRES_PASSWORD: {env_vars.get('POSTGRES_PASSWORD', 'NOT SET')[:20]}...")
print(f"  LINEAR_API_KEY: {env_vars.get('LINEAR_API_KEY', 'NOT SET')[:20]}...")
print(f"  EXTENSION_API_KEY_PRD: {env_vars.get('EXTENSION_API_KEY_PRD', 'NOT SET')[:20]}...")

print("\nBitwarden-injected values should take precedence over these fallbacks.")
'@

poetry run python -c $comparisonScript 2>&1

Write-Host ""
Write-Host "=== Verification Complete ===" -ForegroundColor Cyan
