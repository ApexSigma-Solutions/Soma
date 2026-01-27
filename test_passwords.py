from neo4j import GraphDatabase

candidates = [
    "LMKXBmMtMMRnAdeotR81FEIZ2UFnD0Ec",
    "neo4j_dev_password",
    "password",
    "neo4j",
]

uri = "bolt://localhost:7687"
user = "neo4j"

print(f"Testing connectivity to {uri} with user {user}...")

for pwd in candidates:
    print(f"Testing password: {pwd[:5]}...{pwd[-2:] if len(pwd) > 2 else ''}")
    try:
        with GraphDatabase.driver(uri, auth=(user, pwd)) as driver:
            driver.verify_connectivity()
            print(f"SUCCESS! Password is: {pwd}")
            break
    except Exception as e:
        print(f"Failed: {e}")
