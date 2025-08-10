"""
Схемы для аутентификации и авторизации
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserRegisterRequest(BaseModel):
    """Схема запроса регистрации пользователя"""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "securepassword123",
                "full_name": "John Doe"
            }
        }


class UserLoginRequest(BaseModel):
    """Схема запроса авторизации"""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class TokenResponse(BaseModel):
    """Схема ответа с токеном"""
    access_token: str
    token_type: str
    expires_in: int
    user: dict

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": 1,
                    "email": "user@example.com",
                    "username": "johndoe",
                    "role": "user",
                    "balance": 100.0
                }
            }
        }


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя"""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    balance: float
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "balance": 150.0,
                "role": "user",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00"
            }
        }


class TokenRefreshRequest(BaseModel):
    """Схема запроса обновления токена"""
    refresh_token: str


class LogoutResponse(BaseModel):
    """Схема ответа при выходе"""
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Successfully logged out"
            }
        }
