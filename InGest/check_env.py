import os
from dotenv import load_dotenv

# Load .env
load_dotenv("d:/projects/OmegaKG/InGest-LLM.as/.env")

secret = os.getenv("GITHUB_WEBHOOK_SECRET")
print(f"GITHUB_WEBHOOK_SECRET found: {bool(secret)}")
if secret:
    print(f"Secret length: {len(secret)}")
    print(f"Secret start: {secret[:2]}...")

dsn = os.getenv("POSTGRES_DSN")
print(f"POSTGRES_DSN found: {bool(dsn)}")
