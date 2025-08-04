from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
from enum import Enum


class EventStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: Optional[str] = None
    image: Optional[str] = None
    cost: float = Field(default=0.0)  # Стоимость участия в событии
    max_participants: Optional[int] = None
    current_participants: int = Field(default=0)
    status: EventStatus = Field(default=EventStatus.DRAFT)
    event_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Внешние ключи
    creator_id: int = Field(foreign_key="users.id")

    # Связи
    creator: "User" = Relationship(back_populates="events")

    def __str__(self) -> str:
        return f"Event(id={self.id}, title={self.title}, cost={self.cost}, creator={self.creator_id})"

    def can_join(self) -> bool:
        """Проверка возможности присоединения к событию"""
        if self.status != EventStatus.ACTIVE:
            return False
        if self.max_participants and self.current_participants >= self.max_participants:
            return False
        return True

    def join_event(self) -> bool:
        """Присоединение к событию"""
        if self.can_join():
            self.current_participants += 1
            self.updated_at = datetime.utcnow()
            return True
        return False
