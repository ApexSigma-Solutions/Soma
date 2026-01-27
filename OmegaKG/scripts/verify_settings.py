import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

try:
    print("Attempting to import settings...")
    from omega_kg.settings import settings

    print("Settings imported successfully.")
    print(f"Linear Webhook Secret Present: {bool(settings.linear_webhook_secret)}")
except Exception as e:
    print(f"Settings Import Failed: {e}")
except SystemExit as e:
    print(f"System Exit during import: {e}")
