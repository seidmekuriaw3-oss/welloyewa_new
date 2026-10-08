# ============================
# WOLLOYEWA STORE BOT - USERS API ENDPOINTS
# ============================
"""REST API endpoints for user management."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas import MessageResponse, PaginatedResponse
from apps.users.schemas import (
    ChangePasswordRequest,
    PasswordResetStartRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
    VendorCreate,
    VendorResponse,
    VendorUpdate,
)
from apps.users.password_recovery import PasswordRecoveryService
from apps.users.services import AuthService, UserService, VendorService
from core.config import settings
from core.logger import logger
from core.dependencies import (
    get_current_admin,
    get_current_user,
    get_db_session,
)
from core.exceptions import (
    AuthenticationError,
    DuplicateRecordError,
    NotFoundError,
    ValidationError,
)

router = APIRouter()


def _verified_telegram_identity(init_data: str | None) -> dict | None:
    """Validate signed Telegram Mini App data without exposing the bot token."""
    if not init_data:
        return None

    from bot.web_app.router import _verify_telegram_init_data

    return _verify_telegram_init_data(init_data, settings.TELEGRAM_BOT_TOKEN)


# ============================
# Authentication Endpoints
# ============================


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_password_reset(
    data: PasswordResetStartRequest,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Request an OTP; the response does not disclose whether the phone is registered."""
    try:
        await PasswordRecoveryService(db).request_code(data.phone_number)
    except Exception as exc:
        logger.warning("Password recovery request unavailable (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password recovery is temporarily unavailable",
        ) from exc

    return MessageResponse(
        message=(
            "If the phone number is registered, a code will be sent to a linked "
            "Telegram account or email address when available."
        )
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Verify a single-use OTP and set a new password."""
    try:
        await PasswordRecoveryService(db).reset_password(
            data.phone_number,
            data.otp,
            data.new_password,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired recovery code",
        ) from exc
    except Exception as exc:
        logger.warning("Password recovery confirmation unavailable (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password recovery is temporarily unavailable",
        ) from exc

    return MessageResponse(message="Password updated. You can now log in.")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    data: UserRegister,
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Register a new user.

    Creates a new user account with the provided information.
    """
    auth_service = AuthService(db)

    try:
        if settings.ENVIRONMENT != "testing" or data.init_data:
            telegram_user = _verified_telegram_identity(data.init_data)
            if not telegram_user or telegram_user.get("id") != data.telegram_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Valid Telegram authentication is required",
                )
            # Use signed identity fields, not client-supplied profile values.
            data = data.model_copy(
                update={
                    "username": telegram_user.get("username"),
                    "first_name": telegram_user.get("first_name") or "User",
                    "last_name": telegram_user.get("last_name"),
                }
            )

        user = await auth_service.register(data)
        return UserResponse.model_validate(user)
    except DuplicateRecordError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e


@router.post("/login", response_model=TokenResponse)
async def login_user(
    data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Login user and get access token.

    Authenticates user and returns JWT token for API access.
    """
    auth_service = AuthService(db)

    # Get client IP
    client_ip = request.client.host if request.client else None
    data.ip_address = client_ip

    try:
        if data.telegram_id and (settings.ENVIRONMENT != "testing" or data.init_data):
            telegram_user = _verified_telegram_identity(data.init_data)
            if not telegram_user or telegram_user.get("id") != data.telegram_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Valid Telegram authentication is required",
                )

        user, token = await auth_service.login(data)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRY_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Change user password.

    Requires current password for verification.
    """
    auth_service = AuthService(db)

    try:
        await auth_service.change_password(current_user["id"], data)
        return MessageResponse(message="Password changed successfully")
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e


# ============================
# User Profile Endpoints
# ============================


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user profile.

    Returns the authenticated user's profile information.
    """
    return UserResponse(**current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Update current user profile.

    Updates the authenticated user's information.
    """
    user_service = UserService(db)

    try:
        user = await user_service.update_user(current_user["id"], data)
        return UserResponse.model_validate(user)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e


# ============================
# Admin User Management Endpoints
# ============================


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = Query(None, description="Filter by role"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by name or email"),
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[UserResponse]:
    """
    Get all users (admin only).

    Returns paginated list of users with optional filters.
    """
    user_service = UserService(db)

    # Implementation would go here
    users, total = await user_service.user_repo.get_all(
        filters={"role": role} if role else None,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    return PaginatedResponse.create(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Get user by ID (admin only).
    """
    user_service = UserService(db)

    try:
        user = await user_service.get_user(user_id)
        return UserResponse.model_validate(user)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Update user by ID (admin only).
    """
    user_service = UserService(db)

    try:
        user = await user_service.update_user(user_id, data)
        return UserResponse.model_validate(user)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Delete user by ID (admin only).

    Soft deletes the user account.
    """
    user_service = UserService(db)

    try:
        user = await user_service.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        await user_service.user_repo.delete(user_id, soft=True)
        return MessageResponse(message=f"User {user_id} deleted successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# ============================
# Vendor Management Endpoints
# ============================


@router.post("/vendor/register", response_model=VendorResponse)
async def register_vendor(
    data: VendorCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> VendorResponse:
    """
    Register as a vendor.

    Converts a customer account to a vendor profile.
    """
    vendor_service = VendorService(db)

    try:
        vendor = await vendor_service.create_vendor(current_user["id"], data)
        return VendorResponse.model_validate(vendor)
    except (NotFoundError, ValidationError, DuplicateRecordError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/vendor/me", response_model=VendorResponse)
async def get_my_vendor_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> VendorResponse:
    """
    Get current user's vendor profile.
    """
    vendor_service = VendorService(db)

    vendor = await vendor_service.get_vendor_by_user(current_user["id"])
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found"
        )

    return VendorResponse.model_validate(vendor)


@router.put("/vendor/me", response_model=VendorResponse)
async def update_my_vendor_profile(
    data: VendorUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> VendorResponse:
    """
    Update current user's vendor profile.
    """
    vendor_service = VendorService(db)

    vendor = await vendor_service.get_vendor_by_user(current_user["id"])
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found"
        )

    try:
        updated = await vendor_service.update_vendor(vendor.id, data)
        return VendorResponse.model_validate(updated)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


__all__ = ["router"]
