from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    hashed_password: str
    role: UserRole = Field(default=UserRole.USER)
    balance: float = Field(default=0.0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Связи
    events: List["Event"] = Relationship(back_populates="creator")
    transactions: List["Transaction"] = Relationship(back_populates="user")

    def __str__(self) -> str:
        return f"User(id={self.id}, email={self.email}, balance={self.balance})"

    def has_sufficient_balance(self, amount: float) -> bool:
        """Проверка достаточности баланса"""
        return self.balance >= amount

    def add_balance(self, amount: float) -> None:
        """Пополнение баланса"""
        if amount > 0:
            self.balance += amount
            self.updated_at = datetime.utcnow()

    def deduct_balance(self, amount: float) -> bool:
        """Списание с баланса. Возвращает True при успешном списании"""
        if self.has_sufficient_balance(amount):
            self.balance -= amount
            self.updated_at = datetime.utcnow()
            return True
        return False
