"""
Test security fixes for TN-CORE-100:
1. Resource exhaustion (payload size limits)
2. Insecure token transport (HTTPS validation)
3. Token example security
"""

import pytest
from unittest.mock import Mock, patch
from ingest_llm_as.config import get_settings
from ingest_llm_as.services.omegakg_client import OmegaKGClient


def test_max_payload_size_config():
    """Test that max_payload_size configuration is available."""
    settings = get_settings()
    assert hasattr(settings, "max_payload_size")
    assert settings.max_payload_size > 0
    assert isinstance(settings.max_payload_size, int)


def test_omegakg_client_https_validation_development():
    """Test that HTTP URLs are allowed in development mode."""
    with patch("ingest_llm_as.services.omegakg_client.get_settings") as mock_settings:
        settings = Mock()
        settings.omegakg_api_url = "http://localhost:8765"
        settings.bws_access_token = "test-token"
        settings.static_service_token = None
        settings.debug = True  # Development mode
        mock_settings.return_value = settings

        # Should not raise an error
        client = OmegaKGClient()
        assert client.base_url == "http://localhost:8765"


def test_omegakg_client_https_validation_production_localhost():
    """Test that HTTP localhost URLs are allowed even in production."""
    with patch("ingest_llm_as.services.omegakg_client.get_settings") as mock_settings:
        settings = Mock()
        settings.omegakg_api_url = "http://127.0.0.1:8765"
        settings.bws_access_token = "test-token"
        settings.static_service_token = None
        settings.debug = False  # Production mode
        mock_settings.return_value = settings

        # Should not raise an error for localhost
        client = OmegaKGClient()
        assert client.base_url == "http://127.0.0.1:8765"


def test_omegakg_client_https_validation_production_http_fails():
    """Test that HTTP URLs (non-localhost) fail in production mode."""
    with patch("ingest_llm_as.services.omegakg_client.get_settings") as mock_settings:
        settings = Mock()
        settings.omegakg_api_url = "http://example.com:8765"
        settings.bws_access_token = "test-token"
        settings.static_service_token = None
        settings.debug = False  # Production mode
        mock_settings.return_value = settings

        # Should raise ValueError
        with pytest.raises(ValueError, match="SECURITY ERROR.*HTTPS"):
            client = OmegaKGClient()


def test_omegakg_client_https_validation_production_https_success():
    """Test that HTTPS URLs work in production mode."""
    with patch("ingest_llm_as.services.omegakg_client.get_settings") as mock_settings:
        settings = Mock()
        settings.omegakg_api_url = "https://example.com:8765"
        settings.bws_access_token = "test-token"
        settings.static_service_token = None
        settings.debug = False  # Production mode
        mock_settings.return_value = settings

        # Should not raise an error
        client = OmegaKGClient()
        assert client.base_url == "https://example.com:8765"


def test_omegakg_client_no_token_http_allowed():
    """Test that HTTP URLs without token don't trigger security validation."""
    with patch("ingest_llm_as.services.omegakg_client.get_settings") as mock_settings:
        settings = Mock()
        settings.omegakg_api_url = "http://example.com:8765"
        settings.bws_access_token = None
        settings.static_service_token = None
        settings.debug = False  # Production mode
        mock_settings.return_value = settings

        # Should not raise an error when no token is present
        client = OmegaKGClient()
        assert client.base_url == "http://example.com:8765"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
