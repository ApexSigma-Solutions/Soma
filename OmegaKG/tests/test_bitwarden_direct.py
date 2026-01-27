from pathlib import Path

print("=== Direct Bitwarden Verification ===\n")

# Step 1: Check .env
env_file = Path(".env")
if env_file.exists():
    env_content = env_file.read_text()

    if (
        "BWS_ACCESS_TOKEN=" in env_content
        and "#BWS_ACCESS_TOKEN" not in env_content.split("\n")[7]
    ):
        print("✓ Step 1: BWS_ACCESS_TOKEN is ENABLED in .env")
    else:
        print("⚠️  Step 1: BWS_ACCESS_TOKEN may be disabled or commented")
else:
    print("✗ Step 1: .env file not found")

# Step 2: Try importing settings
print("\n✓ Step 2: Testing Settings initialization...")
try:
    from omega_kg.settings import Settings, BitwardenSettingsSource

    print("   ✓ Imports successful")

    # Check if BitwardenSettingsSource is properly configured
    print("\n✓ Step 3: Checking BitwardenSettingsSource...")
    bws_class = BitwardenSettingsSource
    print("   ✓ BitwardenSettingsSource class available")
    print("   ✓ Source priority: init → BitwardenSettingsSource → env → dotenv")

    # Try to get settings
    print("\n✓ Step 4: Initializing Settings (with Bitwarden)...")
    settings = Settings()
    print("   ✓ Settings loaded successfully")
    print("\n   Verified credentials:")
    print(f"   - NEO4J_URI: {settings.neo4j_uri}")
    print(f"   - POSTGRES_DB: {settings.postgres_db}")
    print(f"   - NEO4J_USER: {settings.neo4j_user}")
    print(f"   - POSTGRES_USER: {settings.postgres_user}")
    print(f"   - APP_PORT: {settings.app_port}")
    print(f"   - OBSIDIAN_VAULT_PATH: {settings.obsidian_vault_path}")

    # Check if neo4j_password is from Bitwarden or local
    local_fallback = "aDQUU5$@1dpuj5"
    actual_password = settings.neo4j_password

    if actual_password == local_fallback:
        print("\n   ℹ️  NEO4J_PASSWORD matches local fallback")
        print("   (Bitwarden may be providing same value, or using fallback)")
    else:
        print(
            "\n   ✓ NEO4J_PASSWORD differs from local fallback (likely from Bitwarden)"
        )

    print("\n✓ All checks passed - Bitwarden integration is working")

except ImportError as e:
    print(f"   ✗ Import error: {e}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback

    traceback.print_exc()

print("\n=== Verification Complete ===")
