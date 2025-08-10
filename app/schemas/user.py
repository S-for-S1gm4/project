"""
Схемы для работы с пользователями
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя"""
    id: int
    email: str
    username: str
    full_name: Optional[str]
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


class BalanceRequest(BaseModel):
    """Схема запроса пополнения баланса"""
    amount: float = Field(..., gt=0, description="Сумма пополнения")
    description: Optional[str] = Field(default="Balance top-up", description="Описание операции")

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 100.0,
                "description": "Monthly allowance"
            }
        }


class BalanceResponse(BaseModel):
    """Схема ответа после пополнения баланса"""
    message: str
    amount: float
    new_balance: float

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Balance added successfully",
                "amount": 100.0,
                "new_balance": 250.0
            }
        }


class TransactionResponse(BaseModel):
    """Схема ответа с данными транзакции"""
    id: int
    amount: float
    transaction_type: str
    status: str
    description: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "amount": 100.0,
                "transaction_type": "deposit",
                "status": "completed",
                "description": "Balance top-up",
                "created_at": "2024-01-15T10:30:00",
                "completed_at": "2024-01-15T10:30:01"
            }
        }


class EventResponse(BaseModel):
    """Схема ответа с данными события (для пользователя)"""
    id: int
    title: str
    description: Optional[str]
    cost: float
    max_participants: Optional[int]
    current_participants: int
    status: str
    creator_id: int
    event_date: Optional[datetime]
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Python Workshop",
                "description": "Learn Python basics",
                "cost": 50.0,
                "max_participants": 20,
                "current_participants": 5,
                "status": "active",
                "creator_id": 2,
                "event_date": "2024-02-01T14:00:00",
                "created_at": "2024-01-15T10:30:00"
            }
        }


class UserProfileUpdateRequest(BaseModel):
    """Схема запроса обновления профиля"""
    full_name: Optional[str] = None
    # Можно добавить другие поля для обновления

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Smith"
            }
        }


class UserBalanceInfo(BaseModel):
    """Схема информации о балансе"""
    user_id: int
    username: str
    balance: float
    currency: str = "USD"
    last_updated: Optional[datetime]

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "username": "johndoe",
                "balance": 150.0,
                "currency": "USD",
                "last_updated": "2024-01-15T10:30:00"
            }
        }


class TransactionSummary(BaseModel):
    """Схема сводки по транзакциям"""
    total_transactions: int
    total_deposits: float
    total_withdrawals: float
    total_event_payments: float
    current_balance: float
    net_flow: float

    class Config:
        json_schema_extra = {
            "example": {
                "total_transactions": 10,
                "total_deposits": 500.0,
                "total_withdrawals": 50.0,
                "total_event_payments": 200.0,
                "current_balance": 250.0,
                "net_flow": 250.0
            }
        }


class EventsStats(BaseModel):
    """Схема статистики событий пользователя"""
    total_events: int
    active_events: int
    completed_events: int
    total_participants: int
    total_revenue: float
    average_participants: float

    class Config:
        json_schema_extra = {
            "example": {
                "total_events": 5,
                "active_events": 2,
                "completed_events": 3,
                "total_participants": 45,
                "total_revenue": 750.0,
                "average_participants": 9.0
            }
        }


class ActivityLogEntry(BaseModel):
    """Схема записи журнала активности"""
    timestamp: datetime
    action: str
    description: Optional[str]
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-01-15T10:30:00",
                "action": "deposit: 100.0",
                "description": "Balance top-up",
                "status": "completed"
            }
        }


class ActivityLogResponse(BaseModel):
    """Схема ответа журнала активности"""
    period_days: int
    total_activities: int
    activities: List[ActivityLogEntry]

    class Config:
        json_schema_extra = {
            "example": {
                "period_days": 30,
                "total_activities": 15,
                "activities": [
                    {
                        "timestamp": "2024-01-15T10:30:00",
                        "action": "deposit: 100.0",
                        "description": "Balance top-up",
                        "status": "completed"
                    }
                ]
            }
        }
