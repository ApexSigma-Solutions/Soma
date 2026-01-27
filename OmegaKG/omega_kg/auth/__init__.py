"""Authentication package for OmegaKG"""

from .validation_auth import validate_service_token, ValidatedToken

__all__ = ["validate_service_token", "ValidatedToken"]
