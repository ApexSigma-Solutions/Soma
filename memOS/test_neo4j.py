from neo4j import GraphDatabase
from memos_mcp.config import settings


def test_conn():
    uri = settings.neo4j_uri
    user = settings.neo4j_user
    pwd = settings.neo4j_password
    print(f"Testing {uri} with user {user} and pwd {pwd}")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        with driver.session() as s:
            res = s.run("RETURN 1 as val")
            print(f"Success: {res.single()['val']}")
        driver.close()
    except Exception as e:
        print(f"Failed: {e}")


if __name__ == "__main__":
    test_conn()
