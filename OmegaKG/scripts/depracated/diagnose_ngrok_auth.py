import os

# 1. Inspect the raw environment (Shell/OS level)
print("--- SHELL ENVIRONMENT ---")
raw_token = os.environ.get("NGROK_API_KEY")
print(f"os.environ['NGROK_API_KEY']: '{raw_token}'")

# 2. Inspect Pydantic/Settings (App level)
print("\n--- APP SETTINGS ---")
try:
    # Try to load the settings module exactly as the app does
    # (Adjusting import path based on your package structure)
    from omega_kg.config import settings

    print(f"settings.enable_ngrok: {settings.enable_ngrok}")
    print(f"settings.ngrok_api_key: '{settings.ngrok_api_key}'")
except ImportError:
    try:
        from omega_kg.settings import settings

        print(f"settings.enable_ngrok: {settings.enable_ngrok}")
        print(f"settings.ngrok_api_key: '{settings.ngrok_api_key}'")
    except Exception as e:
        print(f"Could not load settings module: {e}")

# 3. Search for the zombie file
print("\n--- FILE SYSTEM ---")
env_path = os.path.join(os.getcwd(), ".env")
print(f"Checking {env_path}...")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
        if "your_token" in content:
            print("⚠️ FOUND 'your_token' in .env file!")
        else:
            print("✅ .env file looks clean (no 'your_token' found).")
else:
    print("❌ No .env file found in current directory.")

print("\n--- DIAGNOSIS COMPLETE ---")
