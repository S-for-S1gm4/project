"""
Маршруты аутентификации и авторизации
"""
from fastapi import APIRouter, HTTPException, status
import logging

from schemas.auth import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    UserResponse, LogoutResponse
)
from services.user_service import UserService
from core.auth import (
    create_jwt_token, validate_password, verify_user_credentials
)
from core.exceptions import (
    InvalidCredentialsException, DuplicateUserException,
    ValidationException
)
from database.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@auth_router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegisterRequest):
    """Регистрация нового пользователя"""
    try:
        # Валидация пароля
        if not validate_password(user_data.password):
            raise ValidationException("password", "Password must be at least 6 characters long")

        # Создаем пользователя
        user = UserService.create_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name
        )

        logger.info(f"New user registered: {user.email}")

        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            balance=user.balance,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except DuplicateUserException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@auth_router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLoginRequest):
    """Авторизация пользователя"""
    try:
        # Проверяем учетные данные
        user = verify_user_credentials(login_data.email, login_data.password)

        # Создаем JWT токен
        token = create_jwt_token(user.id, user.email)

        logger.info(f"User logged in: {user.email}")

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRATION_DELTA,
            user={
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role": user.role,
                "balance": user.balance
            }
        )

    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_token: str):
    """Обновление токена"""
    try:
        # В реальном приложении здесь была бы логика refresh токенов
        # Пока используем простую схему перевыпуска токена
        from core.auth import verify_jwt_token

        payload = verify_jwt_token(current_token)

        # Проверяем, что пользователь еще существует
        user = UserService.get_user_by_id(payload['user_id'])
        if not user or not user.is_active:
            raise InvalidCredentialsException("User not found or inactive")

        # Создаем новый токен
        new_token = create_jwt_token(user.id, user.email)

        return TokenResponse(
            access_token=new_token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRATION_DELTA,
            user={
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role": user.role,
                "balance": user.balance
            }
        )

    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@auth_router.post("/logout", response_model=LogoutResponse)
async def logout():
    """Выход из системы"""
    # В реальном приложении здесь можно добавить токен в blacklist
    logger.info("User logout request")
    return LogoutResponse(message="Successfully logged out")
