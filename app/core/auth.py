"""
Модуль аутентификации и авторизации
"""
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import jwt
import hashlib
from typing import Optional
import logging

from services.user_service import UserService
from database.config import get_settings
from .exceptions import InvalidCredentialsException, UserNotFoundException

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()


def create_jwt_token(user_id: int, email: str) -> str:
    """
    Создание JWT токена для пользователя

    Args:
        user_id: ID пользователя
        email: Email пользователя

    Returns:
        str: JWT токен
    """
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRATION_DELTA),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')


def hash_password(password: str) -> str:
    """
    Хэширование пароля

    Args:
        password: Пароль в открытом виде

    Returns:
        str: Хэшированный пароль
    """
    return hashlib.sha256(password.encode()).hexdigest()


def validate_password(password: str) -> bool:
    """
    Валидация пароля

    Args:
        password: Пароль для проверки

    Returns:
        bool: True если пароль валиден
    """
    if len(password) < 6:
        return False
    # Можно добавить дополнительные проверки:
    # - наличие цифр
    # - наличие специальных символов
    # - наличие заглавных букв
    return True


def verify_jwt_token(token: str) -> dict:
    """
    Проверка и декодирование JWT токена

    Args:
        token: JWT токен

    Returns:
        dict: Payload токена

    Raises:
        InvalidCredentialsException: При неверном токене
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise InvalidCredentialsException("Token expired")
    except jwt.InvalidTokenError:
        raise InvalidCredentialsException("Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Получение текущего авторизованного пользователя

    Args:
        credentials: Авторизационные данные из заголовка

    Returns:
        User: Объект пользователя

    Raises:
        HTTPException: При ошибке авторизации
    """
    try:
        payload = verify_jwt_token(credentials.credentials)
        user = UserService.get_user_by_id(payload['user_id'])

        if not user:
            raise UserNotFoundException(f"User with id {payload['user_id']} not found")

        if not user.is_active:
            raise InvalidCredentialsException("User account is disabled")

        return user

    except (InvalidCredentialsException, UserNotFoundException) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Получение текущего пользователя (опционально)
    Не выбрасывает исключение при отсутствии авторизации

    Args:
        credentials: Авторизационные данные из заголовка

    Returns:
        User | None: Объект пользователя или None
    """
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


def verify_user_credentials(email: str, password: str):
    """
    Проверка учетных данных пользователя

    Args:
        email: Email пользователя
        password: Пароль пользователя

    Returns:
        User: Объект пользователя при успешной авторизации

    Raises:
        InvalidCredentialsException: При неверных учетных данных
    """
    user = UserService.get_user_by_email(email)

    if not user:
        raise InvalidCredentialsException("Invalid email or password")

    if user.hashed_password != hash_password(password):
        raise InvalidCredentialsException("Invalid email or password")

    if not user.is_active:
        raise InvalidCredentialsException("Account is disabled")

    return user


def require_admin_role(current_user):
    """
    Проверка прав администратора

    Args:
        current_user: Текущий пользователь

    Raises:
        HTTPException: При недостаточных правах
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin rights required"
        )


def require_event_creator_or_admin(event, current_user):
    """
    Проверка прав создателя события или администратора

    Args:
        event: Объект события
        current_user: Текущий пользователь

    Raises:
        HTTPException: При недостаточных правах
    """
    if event.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only event creator or admin can perform this action"
        )
