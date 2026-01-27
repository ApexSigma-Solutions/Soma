"""
Authentication Router

FastAPI router for user authentication endpoints including login and registration.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from omega_kg.auth_utils import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    validate_access_token,
)
from omega_kg.database.session import get_db
from omega_kg.models.user import User
from omega_kg.models.user_schemas import (
    PasswordChange,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from omega_kg.models.capture import Token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserCreate,
    db_session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Register a new user.

    Args:
        user_data: User registration data
        db_session: Database session

    Returns:
        UserResponse: Created user data

    Raises:
        HTTPException: If email or username already exists
    """
    # Check if email already exists
    result = await db_session.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Check if username already exists
    result = await db_session.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role="user",  # Default role
        is_active=True,
        is_verified=False,  # Require email verification in production
    )

    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)

    logger.info(f"New user registered: {new_user.email} (ID: {new_user.id})")

    return UserResponse.model_validate(new_user)


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db_session: AsyncSession = Depends(get_db),
) -> Token:
    """
    Login with email and password to receive a JWT token.

    Args:
        credentials: User login credentials
        db_session: Database session

    Returns:
        Token: JWT access token

    Raises:
        HTTPException: If credentials are invalid
    """
    user = await authenticate_user(db_session, credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    await db_session.commit()

    # Create JWT token with user ID as subject
    access_token = create_access_token(data={"sub": str(user.id)})

    logger.info(f"User logged in: {user.email} (ID: {user.id})")

    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user (from JWT token)
        db_session: Database session

    Returns:
        UserResponse: Current user data
    """
    # If current_user is TokenData (no db_session), fetch full user
    if not isinstance(current_user, User):
        result = await db_session.execute(
            select(User).where(User.id == int(current_user.username))
        )
        current_user = result.scalar_one_or_none()

        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update current user information.

    Args:
        user_update: User update data
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        UserResponse: Updated user data
    """
    # Update fields if provided
    if user_update.email is not None:
        # Check if email is already taken
        result = await db_session.execute(
            select(User).where(
                User.email == user_update.email, User.id != current_user.id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
            )
        current_user.email = user_update.email

    if user_update.username is not None:
        # Check if username is already taken
        result = await db_session.execute(
            select(User).where(
                User.username == user_update.username, User.id != current_user.id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )
        current_user.username = user_update.username

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.password is not None:
        current_user.hashed_password = get_password_hash(user_update.password)

    current_user.updated_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(current_user)

    logger.info(f"User updated: {current_user.email} (ID: {current_user.id})")

    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Change user password.

    Args:
        password_change: Password change data
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        dict: Success message
    """
    from omega_kg.auth_utils import verify_password

    # Verify current password
    if not verify_password(
        password_change.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    current_user.updated_at = datetime.now(timezone.utc)

    await db_session.commit()

    logger.info(
        f"Password changed for user: {current_user.email} (ID: {current_user.id})"
    )

    return {"message": "Password changed successfully"}


__all__ = ["router", "validate_access_token"]
