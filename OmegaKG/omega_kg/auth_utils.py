import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
import jwt
import bcrypt  # Replaced passlib
from pydantic import BaseModel

from omega_kg.rate_limiter import get_rate_limiter
from omega_kg.settings import settings

logger = logging.getLogger(__name__)

# SECURITY HARDENING: JWT Algorithm Validation (AUTH-001)
# Only allow secure algorithms - reject 'none' and weak algorithms
SECURE_JWT_ALGORITHMS: Set[str] = {
    "HS256",
    "HS384",
    "HS512",
    "RS256",
    "RS384",
    "RS512",
    "ES256",
    "ES384",
    "ES512",
    "EdDSA",
}
INSECURE_ALGORITHMS: Set[str] = {"none", "None", "NONE", "HS1", "HS224"}

# CONFIG
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expiration_minutes
EXTENSION_API_KEY = settings.extension_api_key

# Validate JWT algorithm at startup
if ALGORITHM not in SECURE_JWT_ALGORITHMS:
    raise ValueError(
        f"INSECURE JWT algorithm configured: {ALGORITHM}. Must be one of: {SECURE_JWT_ALGORITHMS}"
    )

# pwd_context removed, using bcrypt directly
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")


# MODELS
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# UTILS
def _check_rate_limit(client_ip: str) -> bool:
    """
    SECURITY HARDENING (AUTH-004): Check rate limiting for API key attempts.

    Uses production-ready distributed rate limiting:
    - Primary: Redis (for multi-process/distributed deployments)
    - Fallback: In-memory (for development/testing)

    Args:
        client_ip: Client IP address for rate limiting

    Returns:
        bool: True if request should be allowed, False if rate limited
    """
    rate_limiter = get_rate_limiter()
    return rate_limiter.check_limit(client_ip)


def get_static_api_key(
    request: Request,
    api_key_header: str = Security(API_KEY_HEADER),
) -> str:
    """
    SECURITY HARDENING (AUTH-004): Validates the static X-API-Key with rate limiting.

    Args:
        api_key_header: X-API-Key header value
        request: FastAPI request object for IP extraction

    Returns:
        str: Validated API key

    Raises:
        HTTPException: For invalid keys, missing headers, or rate limiting
    """
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limiting
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
        )

    # Validate API key configuration
    if not EXTENSION_API_KEY:
        # Log critical configuration error
        import logging

        logger = logging.getLogger(__name__)
        logger.critical("EXTENSION_API_KEY not configured - server misconfiguration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: Authentication unavailable",
        )

    # Validate header presence
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing authentication credentials",
        )

    # Use constant-time comparison to prevent timing attacks
    try:
        if hmac.compare_digest(api_key_header, EXTENSION_API_KEY):
            # Successful authentication - reset rate limit
            rate_limiter = get_rate_limiter()
            rate_limiter.reset(client_ip)
            return api_key_header
    except Exception:
        # Log validation error without leaking API key details
        logger.warning("API key validation error for IP: %s", client_ip)

    # Failed authentication - don't reveal specific error details
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid or missing authentication credentials",
    )


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    SECURITY HARDENING (AUTH-001): Create JWT token with strict algorithm validation.

    Args:
        data: Dictionary containing token payload
        expires_delta: Optional custom expiration time

    Returns:
        str: Encoded JWT token

    Raises:
        ValueError: If algorithm is insecure or data is invalid
    """
    # Create payload with expiration
    if data is None:
        raise ValueError("Data cannot be None")
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    # Double-check algorithm validation before encoding
    if ALGORITHM not in SECURE_JWT_ALGORITHMS:
        raise ValueError(f"INSECURE JWT algorithm: {ALGORITHM}")

    # Create token with secure algorithm
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def validate_access_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    SECURITY HARDENING (AUTH-001): Validate JWT token with strict algorithm validation.

    Args:
        token: JWT token to validate

    Returns:
        TokenData: Validated token data

    Raises:
        HTTPException: If token is invalid, expired, or uses insecure algorithm
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode with strict algorithm validation
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Extract and validate username/subject
        username = payload.get("sub")
        if username is None or not isinstance(username, str):
            raise credentials_exception

        # Additional validation: check for required fields
        if not payload.get("exp"):
            raise credentials_exception

        return TokenData(username=username)

    except jwt.PyJWTError as e:
        # Log failed validation attempt (security monitoring)
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("JWT validation failed: %s", str(e))
        raise credentials_exception from e


# USER AUTHENTICATION FUNCTIONS


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password from database

    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        # Check against pure bcrypt
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception as e:
        print(f"VERIFY CRASH: {e}")
        # Fallback logging if needed, but return False safely
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password for storage.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    # Generate bcrypt hash
    # Note: gensalt() handles salt generation automatically
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def authenticate_user(
    db_session: Any, email: str, password: str
) -> Optional[Any]:
    """
    Authenticate a user by email and password.

    Args:
        db_session: Database session
        email: User email
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    from sqlalchemy import select
    from omega_kg.models.user import User

    # Query user by email
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    if not user.is_active:
        return None

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme), db_session: Any = None
) -> Any:
    """
    Get the current authenticated user from JWT token.

    Args:
        token: JWT token
        db_session: Database session (injected by FastAPI)

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    # If no db_session provided, return token data only
    if db_session is None:
        return TokenData(username=user_id)

    # Query user from database
    from sqlalchemy import select
    from omega_kg.models.user import User

    try:
        user_id_int = int(user_id)
    except ValueError:
        raise credentials_exception

    result = await db_session.execute(select(User).where(User.id == user_id_int))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    return user
