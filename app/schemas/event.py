"""
Схемы для работы с событиями
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class EventCreateRequest(BaseModel):
    """Схема запроса создания события"""
    title: str = Field(..., min_length=3, description="Название события")
    description: Optional[str] = Field(None, description="Описание события")
    cost: float = Field(default=0.0, ge=0, description="Стоимость участия")
    max_participants: Optional[int] = Field(None, gt=0, description="Максимальное количество участников")
    event_date: Optional[datetime] = Field(None, description="Дата и время события")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Python Workshop",
                "description": "Learn Python programming basics",
                "cost": 50.0,
                "max_participants": 20,
                "event_date": "2024-02-15T14:00:00"
            }
        }


class EventUpdateRequest(BaseModel):
    """Схема запроса обновления события"""
    title: Optional[str] = Field(None, min_length=3)
    description: Optional[str] = None
    cost: Optional[float] = Field(None, ge=0)
    max_participants: Optional[int] = Field(None, gt=0)
    event_date: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Advanced Python Workshop",
                "cost": 75.0,
                "max_participants": 15
            }
        }


class EventResponse(BaseModel):
    """Схема ответа с данными события"""
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
    can_join: bool = True

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
                "created_at": "2024-01-15T10:30:00",
                "can_join": True
            }
        }


class JoinEventResponse(BaseModel):
    """Схема ответа при присоединении к событию"""
    message: str
    event_id: int
    event_title: str
    cost: float
    new_balance: float
    current_participants: int

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Successfully joined event",
                "event_id": 1,
                "event_title": "Python Workshop",
                "cost": 50.0,
                "new_balance": 100.0,
                "current_participants": 6
            }
        }


class PredictionRequest(BaseModel):
    """Схема запроса предсказания участия"""
    event_id: int
    user_features: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные характеристики пользователя")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": 1,
                "user_features": {
                    "interest_level": 0.8,
                    "past_participation": 0.6,
                    "event_type_preference": 0.7
                }
            }
        }


class PredictionResponse(BaseModel):
    """Схема ответа предсказания"""
    prediction: str
    confidence: float
    event_id: int
    cost: float
    recommendation: str

    class Config:
        json_schema_extra = {
            "example": {
                "prediction": "likely_to_join",
                "confidence": 0.75,
                "event_id": 1,
                "cost": 50.0,
                "recommendation": "This event seems perfect for you! Join now."
            }
        }


class EventSearchRequest(BaseModel):
    """Схема запроса поиска событий"""
    query: str = Field(..., min_length=3)
    limit: int = Field(default=10, le=50)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "python workshop",
                "limit": 10
            }
        }


class EventSearchResponse(BaseModel):
    """Схема ответа поиска событий"""
    query: str
    total_found: int
    events: List[EventResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "query": "python",
                "total_found": 3,
                "events": []
            }
        }


class EventParticipantsResponse(BaseModel):
    """Схема ответа со списком участников"""
    event_id: int
    event_title: str
    current_participants: int
    max_participants: Optional[int]
    participants: List[Dict[str, Any]]  # В реальном приложении будет список участников

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": 1,
                "event_title": "Python Workshop",
                "current_participants": 5,
                "max_participants": 20,
                "participants": []
            }
        }


class EventsOverviewResponse(BaseModel):
    """Схема ответа с общей статистикой событий"""
    total_events: int
    active_events: int
    status_breakdown: Dict[str, int]
    free_events: int
    paid_events: int
    total_participants: int
    average_participants_per_event: float
    total_revenue: float
    most_popular_events: List[Dict[str, Any]]

    class Config:
        json_schema_extra = {
            "example": {
                "total_events": 10,
                "active_events": 5,
                "status_breakdown": {
                    "active": 5,
                    "draft": 2,
                    "completed": 3
                },
                "free_events": 3,
                "paid_events": 7,
                "total_participants": 45,
                "average_participants_per_event": 4.5,
                "total_revenue": 750.0,
                "most_popular_events": []
            }
        }


class PredictionHistoryEntry(BaseModel):
    """Схема записи истории предсказаний"""
    id: int
    event_name: str
    requested_at: datetime
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "event_name": "Python Workshop",
                "requested_at": "2024-01-15T10:30:00",
                "status": "completed"
            }
        }


class PredictionHistoryResponse(BaseModel):
    """Схема ответа истории предсказаний"""
    total_predictions: int
    unique_events: int
    predictions_by_event: Dict[str, List[Dict[str, Any]]]
    recent_predictions: List[PredictionHistoryEntry]

    class Config:
        json_schema_extra = {
            "example": {
                "total_predictions": 5,
                "unique_events": 3,
                "predictions_by_event": {},
                "recent_predictions": []
            }
        }


class EventActivationResponse(BaseModel):
    """Схема ответа активации события"""
    message: str
    event_id: int
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Event 'Python Workshop' activated successfully",
                "event_id": 1,
                "status": "active"
            }
        }
