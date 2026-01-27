"""Authentication utilities for validation API.

This module provides Zero Trust authentication for the validation API gateway.
All requests must include a valid BWS_ACCESS_TOKEN to prevent unauthorized writes.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..settings import Settings, get_settings


# HTTP Bearer security scheme
security = HTTPBearer()


async def validate_service_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Validate service authentication token.

    This dependency validates that the request includes a valid service token
    (BWS_ACCESS_TOKEN or STATIC_SERVICE_TOKEN for local development).

    Args:
        credentials: HTTP Bearer credentials from request
        settings: Application settings

    Returns:
        str: Validated token value

    Raises:
        HTTPException: 401 if token is invalid or missing
    """
    token = credentials.credentials

    # Check against BWS_ACCESS_TOKEN (production)
    if settings.bws_access_token and token == settings.bws_access_token:
        return token

    # Check against STATIC_SERVICE_TOKEN (local development)
    if settings.static_service_token and token == settings.static_service_token:
        return token

    # Token is invalid
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing service authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Type alias for dependency injection
ValidatedToken = Annotated[str, Depends(validate_service_token)]
