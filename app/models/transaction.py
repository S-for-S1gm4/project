from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    DEPOSIT = "deposit"        # Пополнение баланса
    WITHDRAWAL = "withdrawal"  # Списание
    EVENT_PAYMENT = "event_payment"  # Оплата события
    REFUND = "refund"         # Возврат средств


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    transaction_type: TransactionType
    status: TransactionStatus = Field(default=TransactionStatus.PENDING)
    description: Optional[str] = None
    reference_id: Optional[str] = None  # Для связи с внешними системами
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Внешние ключи
    user_id: int = Field(foreign_key="users.id")
    event_id: Optional[int] = Field(default=None, foreign_key="events.id")

    # Связи
    user: "User" = Relationship(back_populates="transactions")

    def __str__(self) -> str:
        return f"Transaction(id={self.id}, type={self.transaction_type}, amount={self.amount}, user_id={self.user_id})"

    def complete(self) -> None:
        """Отметить транзакцию как завершенную"""
        self.status = TransactionStatus.COMPLETED
        self.completed_at = datetime.utcnow()

    def fail(self, reason: Optional[str] = None) -> None:
        """Отметить транзакцию как неудачную"""
        self.status = TransactionStatus.FAILED
        if reason:
            self.description = f"{self.description or ''} Failed: {reason}"
