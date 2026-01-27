from memos_mcp.database.postgres import PostgresDatabase
from memos_mcp.config import settings


def test_connect():
    print(
        f"Connecting via SQLAlchemy to {settings.postgres_host}:{settings.postgres_port}..."
    )
    try:
        db = PostgresDatabase()
        print("Initialized PostgresDatabase (SQLAlchemy) successfully!")

        # Test a query
        with db.get_session() as session:
            print("Session acquired.")
            # Check if tables exist by querying one
            from sqlalchemy import text

            result = session.execute(text("SELECT 1"))
            print(f"Query result: {result.scalar()}")

    except Exception as e:
        print(f"Connection/Init failed: {e}")


if __name__ == "__main__":
    test_connect()
