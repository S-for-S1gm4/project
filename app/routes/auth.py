from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import jwt
import hashlib
from services.user_service import UserService
from database.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# =============================================================================
# МОДЕЛИ
# =============================================================================

class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str = None
    balance: float
    role: str
    is_active: bool
    created_at: datetime

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def create_jwt_token(user_id: int, email: str) -> str:
    """Создание JWT токена"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRATION_DELTA)
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')

def hash_password(password: str) -> str:
    """Хэширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(password: str) -> bool:
    """Валидация пароля"""
    if len(password) < 6:
        return False
    return True

# =============================================================================
# МАРШРУТЫ
# =============================================================================

@auth_router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegisterRequest):
    """Регистрация нового пользователя"""
    try:
        # Валидация пароля
        if not validate_password(user_data.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )

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

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
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
        # Получаем пользователя по email
        user = UserService.get_user_by_email(login_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Проверяем пароль
        if user.hashed_password != hash_password(login_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Проверяем активность аккаунта
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@auth_router.post("/refresh")
async def refresh_token(current_token: str):
    """Обновление токена"""
    try:
        # Декодируем текущий токен
        payload = jwt.decode(current_token, settings.JWT_SECRET_KEY, algorithms=['HS256'])

        # Проверяем, что пользователь еще существует
        user = UserService.get_user_by_id(payload['user_id'])
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Создаем новый токен
        new_token = create_jwt_token(user.id, user.email)

        return {
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_EXPIRATION_DELTA
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@auth_router.post("/logout")
async def logout():
    """Выход из системы"""
    # В реальном приложении здесь можно добавить токен в blacklist
    return {"message": "Successfully logged out"}
