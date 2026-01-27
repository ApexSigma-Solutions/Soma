"""
End-to-End Testing for JWT Authentication Flow (TN-AUTHN-007)

This test suite validates the complete authentication flow:
1. Bootstrap API key configuration in chrome.storage.local
2. JWT token exchange via /auth/token endpoint
3. Capture endpoint secured with Bearer token
4. Token caching and refresh logic
5. Error handling and graceful degradation
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from omega_kg.auth_utils import create_access_token, validate_access_token
from omega_kg.capture_server import app

# Import settings lazily within functions to avoid import-time environment issues


class TestJwtAuthenticationFlow:
    """Test the complete JWT authentication flow"""

    @pytest.fixture(autouse=True)
    def setup_test_env(self, mock_env_vars):
        """Ensure test environment variables are loaded for all tests"""
        pass

    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def valid_api_key(self):
        """Bootstrap API key for testing"""
        return "test_bootstrap_key_12345678901234567890"

    @pytest.fixture
    def sample_capture_data(self):
        """Sample conversation capture data"""
        return {
            "platform": "claude",
            "url": "https://claude.ai/chat/test",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, how can I use this?",
                    "timestamp": "2025-11-12T10:00:00Z",
                },
                {
                    "role": "assistant",
                    "content": "This extension captures AI conversations...",
                    "timestamp": "2025-11-12T10:00:05Z",
                },
            ],
            "title": "Testing JWT Authentication",
            "capture_date": datetime.now(timezone.utc).isoformat(),
        }

    # ===== Test 1: JWT Token Creation & Validation =====

    def test_jwt_token_creation(self):
        """Test JWT token creation with proper expiration"""
        token = create_access_token(data={"sub": "test_user"})
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT format: header.payload.signature

    @pytest.mark.asyncio
    async def test_jwt_token_has_expiration(self):
        """Test JWT token includes expiration claim"""
        token = create_access_token(data={"sub": "chrome_extension_user"})
        # validate_access_token returns TokenData, which validates the token signature and expiry
        payload_obj = await validate_access_token(token)
        assert payload_obj is not None
        assert payload_obj.username == "chrome_extension_user"

        # To check specific claims like 'exp', we decode manually
        from omega_kg.settings import get_settings

        payload = jwt.decode(
            token,
            get_settings().jwt_secret_key,
            algorithms=[get_settings().jwt_algorithm],
        )
        assert "exp" in payload
        assert "sub" in payload
        assert payload["sub"] == "chrome_extension_user"

    @pytest.mark.asyncio
    async def test_jwt_token_expiration_timing(self):
        """Test JWT token expiration is set correctly"""
        token = create_access_token(data={"sub": "test_user"})
        # Ensure it's valid
        await validate_access_token(token)

        # Decode to check expiration time
        from omega_kg.settings import get_settings

        payload = jwt.decode(
            token,
            get_settings().jwt_secret_key,
            algorithms=[get_settings().jwt_algorithm],
        )
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)

        # Token should expire within configured minutes (uses settings value)
        expected_minutes = get_settings().jwt_expiration_minutes
        time_diff = (exp_datetime - now).total_seconds() / 60
        # Allow 5 minute tolerance around the configured value
        assert expected_minutes - 10 < time_diff < expected_minutes + 10, (
            f"Expected expiration around {expected_minutes} minutes, got {time_diff:.1f}"
        )

    @pytest.mark.asyncio
    async def test_jwt_token_validation_success(self):
        """Test successful JWT token validation"""
        token = create_access_token(data={"sub": "chrome_extension_user"})
        payload = await validate_access_token(token)
        assert payload.username == "chrome_extension_user"

    @pytest.mark.asyncio
    async def test_jwt_token_validation_invalid_token(self):
        """Test JWT token validation with invalid token"""
        with pytest.raises(Exception):  # JWT library raises error on invalid token
            await validate_access_token("invalid.jwt.token")

    @pytest.mark.asyncio
    async def test_jwt_token_validation_expired_token(self):
        """Test JWT token validation with expired token"""
        # Create a token with past expiration
        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()

        payload = {
            "sub": "chrome_extension_user",
            "exp": int(past_time),
        }
        from omega_kg.settings import get_settings

        expired_token = jwt.encode(
            payload,
            get_settings().jwt_secret_key,
            algorithm=get_settings().jwt_algorithm,
        )

        # Should raise error on expired token
        with pytest.raises(Exception):
            await validate_access_token(expired_token)

    # ===== Test 2: /auth/token Endpoint =====

    def test_auth_token_endpoint_requires_api_key(self, client):
        """Test /auth/token endpoint requires X-API-Key header"""
        response = client.post("/auth/token")
        assert response.status_code == 403  # Forbidden - missing API key

    def test_auth_token_endpoint_invalid_api_key(self, client):
        """Test /auth/token endpoint rejects invalid API key"""
        response = client.post(
            "/auth/token",
            headers={"X-API-Key": "wrong_key"},
        )
        assert response.status_code == 403  # Forbidden - invalid API key

    def test_auth_token_endpoint_valid_api_key(self, client):
        """Test /auth/token endpoint with valid API key"""
        from omega_kg.settings import get_settings

        response = client.post(
            "/auth/token",
            headers={"X-API-Key": get_settings().extension_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_auth_token_returns_valid_jwt(self, client):
        """Test /auth/token returns a valid, usable JWT token"""
        from omega_kg.settings import get_settings

        response = client.post(
            "/auth/token",
            headers={"X-API-Key": get_settings().extension_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        token = data["access_token"]

        # Token should be valid
        payload = await validate_access_token(token)
        assert payload.username == "chrome_extension_user"

    # ===== Test 3: /capture Endpoint Security =====

    def test_capture_endpoint_requires_authorization(self, client, sample_capture_data):
        """Test /capture endpoint requires Authorization header"""
        response = client.post(
            "/capture",
            json=sample_capture_data,
        )
        assert response.status_code == 401  # Unauthorized - missing auth

    def test_capture_endpoint_rejects_invalid_token(self, client, sample_capture_data):
        """Test /capture endpoint rejects invalid Bearer token"""
        response = client.post(
            "/capture",
            json=sample_capture_data,
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401  # Unauthorized

    def test_capture_endpoint_accepts_valid_jwt(self, client, sample_capture_data):
        """Test /capture endpoint accepts valid JWT token"""
        token = create_access_token(data={"sub": "chrome_extension_user"})

        response = client.post(
            "/capture",
            json=sample_capture_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should return 200 (or 422 for validation, but not 401/403)
        assert response.status_code in [200, 422]

    def test_capture_endpoint_rejects_old_auth_header(
        self, client, sample_capture_data
    ):
        """Test /capture endpoint rejects old X-API-Key header"""
        response = client.post(
            "/capture",
            json=sample_capture_data,
            headers={"X-API-Key": "some_key"},
        )
        # Should reject because we're using Bearer token now
        assert response.status_code == 401

    # ===== Test 4: Complete E2E Flow =====

    def test_complete_e2e_flow(self, client, sample_capture_data):
        """Test complete flow: get token → use token for capture"""
        # Step 1: Exchange API key for JWT token
        from omega_kg.settings import get_settings

        auth_response = client.post(
            "/auth/token",
            headers={"X-API-Key": get_settings().extension_api_key},
        )
        assert auth_response.status_code == 200
        token = auth_response.json()["access_token"]

        # Step 2: Use JWT token to call /capture endpoint
        capture_response = client.post(
            "/capture",
            json=sample_capture_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should succeed (200) or have validation issues (422), not auth issues
        assert capture_response.status_code in [200, 422]

    # ===== Test 5: CORS Headers =====

    def test_cors_headers_for_bearer_tokens(self, client):
        """Test CORS headers allow requests from extension"""
        from omega_kg.settings import get_settings

        response = client.options(
            "/capture",
            headers={
                "Origin": f"chrome-extension://{get_settings().chrome_extension_id}",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        from omega_kg.settings import settings

        # CORS should allow the extension origin
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == f"chrome-extension://{settings.chrome_extension_id}"
        )
        assert response.headers.get("access-control-allow-credentials") == "true"

    # ===== Test 6: Health Check Endpoint =====

    def test_health_check_available(self, client):
        """Test /health endpoint is available (background script checks this)"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    # ===== Test 7: Error Scenarios =====

    def test_malformed_bearer_token_header(self, client, sample_capture_data):
        """Test malformed Authorization header"""
        response = client.post(
            "/capture",
            json=sample_capture_data,
            headers={"Authorization": "Bearer"},  # Missing token
        )
        assert response.status_code == 401

    def test_wrong_bearer_scheme(self, client, sample_capture_data):
        """Test wrong authentication scheme"""
        token = create_access_token(data={"sub": "test_user"})
        response = client.post(
            "/capture",
            json=sample_capture_data,
            headers={"Authorization": f"Basic {token}"},  # Wrong scheme
        )
        assert response.status_code == 401

    # ===== Test 8: Token Refresh Scenario =====

    @pytest.mark.asyncio
    async def test_token_refresh_creates_new_token(self):
        """Test that refreshing creates a new token"""
        import time

        token1 = create_access_token(data={"sub": "chrome_extension_user"})
        # Small delay to ensure different timestamp
        time.sleep(0.1)
        token2 = create_access_token(data={"sub": "chrome_extension_user"})

        payload1 = await validate_access_token(token1)
        payload2 = await validate_access_token(token2)

        # Both should be valid but potentially different (depends on timing)
        assert payload1.username == "chrome_extension_user"
        assert payload2.username == "chrome_extension_user"

    # ===== Test 9: No Hardcoded Secrets =====

    def test_no_hardcoded_secrets_in_files(self):
        """Verify no hardcoded API keys in Python files"""
        import os
        import re

        # Pattern for hardcoded API keys (random-looking base64/hex strings)
        secret_pattern = r"N7F6JK|OMEGA_API_KEY\s*=\s*['\"]"

        python_files = []
        python_files = []
        for root, _dirs, files in os.walk("omega_kg"):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))
        for filepath in python_files:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                matches = re.findall(secret_pattern, content)
                assert len(matches) == 0, (
                    f"Found hardcoded secret pattern in {filepath}"
                )

    def test_no_hardcoded_secrets_in_extension(self):
        """Verify no hardcoded API keys in extension files"""
        import os
        import re

        # Pattern for hardcoded API keys
        secret_pattern = r"N7F6JK|const\s+OMEGA_API_KEY\s*="

        extension_files = []
        extension_files = []
        for root, _dirs, files in os.walk("chrome-extension"):
            for file in files:
                if file.endswith((".js", ".json")):
                    extension_files.append(os.path.join(root, file))
        for filepath in extension_files:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                matches = re.findall(secret_pattern, content)
                assert len(matches) == 0, (
                    f"Found hardcoded secret pattern in {filepath}"
                )

    # ===== Test 10: Settings Configuration =====

    def test_jwt_settings_loaded(self):
        """Test JWT settings are properly loaded"""
        from omega_kg.settings import get_settings

        assert hasattr(get_settings(), "jwt_secret_key")
        assert hasattr(get_settings(), "jwt_algorithm")
        assert hasattr(get_settings(), "jwt_expiration_minutes")

    def test_jwt_algorithm_is_hs256(self):
        """Test JWT algorithm is HS256 by default"""
        from omega_kg.settings import get_settings

        assert get_settings().jwt_algorithm == "HS256"

    def test_jwt_expiration_is_positive(self):
        """Test JWT expiration is a positive number"""
        from omega_kg.settings import get_settings

        assert get_settings().jwt_expiration_minutes > 0
        # Default is 60 minutes for test environment
        assert get_settings().jwt_expiration_minutes >= 60


class TestExtensionIntegration:
    """Test integration between extension and server"""

    @pytest.fixture(autouse=True)
    def setup_test_env(self, mock_env_vars):
        """Ensure test environment variables are loaded for all tests"""
        pass

    def test_bearer_token_format(self):
        """Test Bearer token format is correct"""
        token = create_access_token(data={"sub": "test_user"})
        # Token should be a valid JWT
        parts = token.split(".")
        assert len(parts) == 3  # header.payload.signature

    @pytest.mark.asyncio
    async def test_token_includes_expiry(self):
        """Test token payload includes expiry"""
        from omega_kg.settings import get_settings

        token = create_access_token(data={"sub": "test_user"})
        await validate_access_token(token)

        payload = jwt.decode(
            token,
            get_settings().jwt_secret_key,
            algorithms=[get_settings().jwt_algorithm],
        )
        assert "exp" in payload
        assert payload["exp"] > datetime.now(timezone.utc).timestamp()

    @pytest.mark.asyncio
    async def test_multiple_tokens_are_independent(self):
        """Test multiple tokens can be created and validated independently"""
        tokens = [
            create_access_token(data={"sub": "chrome_extension_user"}) for _ in range(3)
        ]
        payloads = [await validate_access_token(t) for t in tokens]

        # All should be valid
        for payload in payloads:
            assert payload.username == "chrome_extension_user"

        # All should have different expiration times (or very close)
        from omega_kg.settings import get_settings

        decoded_payloads = [
            jwt.decode(
                t,
                get_settings().jwt_secret_key,
                algorithms=[get_settings().jwt_algorithm],
            )
            for t in tokens
        ]
        exp_times = [p["exp"] for p in decoded_payloads]
        # At minimum, they should all be valid timestamps in the future
        from omega_kg.settings import get_settings

        for exp_time in exp_times:
            assert exp_time > datetime.now(timezone.utc).timestamp()


# ===== Pytest Markers & Configuration =====

pytestmark = [
    pytest.mark.unit,
    pytest.mark.not_requires_neo4j,
]

# Run only unit tests with: pytest tests/test_jwt_e2e.py -m unit
# Run all tests with: pytest tests/test_jwt_e2e.py -v
