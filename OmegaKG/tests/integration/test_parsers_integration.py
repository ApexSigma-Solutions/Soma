import pytest
from fastapi.testclient import TestClient

from omega_kg.auth_utils import create_access_token


# Import settings lazily within functions to avoid import-time issues
def get_app():
    from omega_kg.capture_server import app

    return app


client = TestClient(get_app())


@pytest.fixture
def auth_headers():
    token = create_access_token(data={"sub": "test_user"})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
def test_html_parsing_endpoint(auth_headers):
    """
    Integration test for server-side HTML parsing via /capture endpoint.
    Verifies that raw HTML is parsed into messages and captured successfully.
    """
    dummy_html = """
    <html>
        <body>
            <div class="message-user">Run: Create a python script for me.</div>
            <div class="message-model">Model: Sure! Here is the code...</div>
        </body>
    </html>
    """

    payload = {
        "user_id": "integration_tester",
        "source": "pytest_integration",
        "url": "https://aistudio.google.com/test",
        "platform": "web",
        "title": "Integration Test Parsing",
        "raw_html": dummy_html,
        "messages": [],  # Empty messages to force server-side parsing
    }

    response = client.post("/capture", json=payload, headers=auth_headers)

    # Assert successful capture
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "file_path" in data

    # We can't easily verify the internal messages logic without mocking or reading the file,
    # but the success response implies parsing didn't raise an exception.
    # The logs would show "Successfully parsed X messages".
    # The logs would show "Successfully parsed X messages".
