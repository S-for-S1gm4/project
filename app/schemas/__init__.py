"""
API Schemas package - Pydantic модели для запросов и ответов
"""

from .auth import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    UserResponse as AuthUserResponse
)
from .user import (
    UserResponse, BalanceRequest, BalanceResponse,
    TransactionResponse, EventResponse as UserEventResponse
)
from .event import (
    EventCreateRequest, EventUpdateRequest, EventResponse,
    JoinEventResponse, PredictionRequest, PredictionResponse
)

__all__ = [
    # Auth schemas
    'UserRegisterRequest', 'UserLoginRequest', 'TokenResponse', 'AuthUserResponse',
    # User schemas
    'UserResponse', 'BalanceRequest', 'BalanceResponse', 'TransactionResponse', 'UserEventResponse',
    # Event schemas
    'EventCreateRequest', 'EventUpdateRequest', 'EventResponse',
    'JoinEventResponse', 'PredictionRequest', 'PredictionResponse'
]
