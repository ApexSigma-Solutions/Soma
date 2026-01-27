import os
from dotenv import load_dotenv

load_dotenv("d:/projects/OmegaKG/InGest-LLM.as/.env")
dsn = os.getenv("POSTGRES_DSN")
print(f"Loaded POSTGRES_DSN: {dsn}")

# Parse identifying parts
if dsn:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(dsn)
        print(f"Scheme: {parsed.scheme}")
        print(f"Hostname: {parsed.hostname}")
        print(f"Port: {parsed.port}")
    except Exception as e:
        print(f"Parsing failed: {e}")
