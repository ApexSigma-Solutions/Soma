from memos_mcp.config import settings
import os


def check():
    print(f"ENV NEO4J_PASSWORD: {os.environ.get('NEO4J_PASSWORD')}")
    print(f"SETTINGS NEO4J_PASSWORD: {settings.neo4j_password}")
    print(f"SETTINGS DB_TYPE: {settings.memos_db_type}")
    print(f"SETTINGS POSTGRES_DB: {settings.postgres_db}")


if __name__ == "__main__":
    check()
