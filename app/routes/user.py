from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import jwt
from services.user_service import UserService
from services.event_service import EventService
from database.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()

user_router = APIRouter(prefix="/api/users", tags=["User Profile"])

# =============================================================================
# МОДЕЛИ
# =============================================================================

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    balance: float
    role: str
    is_active: bool
    created_at: datetime

class BalanceRequest(BaseModel):
    amount: float
    description: Optional[str] = "Balance top-up"

class BalanceResponse(BaseModel):
    message: str
    amount: float
    new_balance: float

class TransactionResponse(BaseModel):
    id: int
    amount: float
    transaction_type: str
    status: str
    description: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

class EventResponse(BaseModel):
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

# =============================================================================
# АУТЕНТИФИКАЦИЯ
# =============================================================================

def verify_jwt_token(token: str) -> dict:
    """Проверка JWT токена"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
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

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Получение текущего пользователя из токена"""
    payload = verify_jwt_token(credentials.credentials)
    user = UserService.get_user_by_id(payload['user_id'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

# =============================================================================
# МАРШРУТЫ ПРОФИЛЯ
# =============================================================================

@user_router.get("/profile", response_model=UserResponse)
async def get_profile(current_user = Depends(get_current_user)):
    """Получение профиля текущего пользователя"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        balance=current_user.balance,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )

@user_router.put("/profile")
async def update_profile(
    full_name: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Обновление профиля пользователя"""
    try:
        # В реальном приложении здесь была бы функция обновления в UserService
        # Пока просто возвращаем успешный ответ
        return {
            "message": "Profile updated successfully",
            "user_id": current_user.id,
            "updated_fields": {"full_name": full_name} if full_name else {}
        }
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

# =============================================================================
# БАЛАНС И ТРАНЗАКЦИИ
# =============================================================================

@user_router.get("/balance")
async def get_balance(current_user = Depends(get_current_user)):
    """Получение баланса пользователя"""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "balance": current_user.balance,
        "currency": "USD",
        "last_updated": current_user.updated_at
    }

@user_router.post("/balance", response_model=BalanceResponse)
async def add_balance(
    balance_data: BalanceRequest,
    current_user = Depends(get_current_user)
):
    """Пополнение баланса"""
    try:
        if balance_data.amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be positive"
            )

        if balance_data.amount > 10000:  # Лимит пополнения
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount exceeds maximum limit of $10,000"
            )

        success = UserService.add_balance(
            current_user.id,
            balance_data.amount,
            balance_data.description
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add balance"
            )

        # Получаем обновленного пользователя
        updated_user = UserService.get_user_by_id(current_user.id)

        logger.info(f"Balance added: {balance_data.amount} to user {current_user.id}")

        return BalanceResponse(
            message="Balance added successfully",
            amount=balance_data.amount,
            new_balance=updated_user.balance
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Balance addition error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add balance"
        )

@user_router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """Получение истории транзакций пользователя"""
    try:
        if limit > 100:
            limit = 100  # Максимальный лимит

        transactions = UserService.get_user_transactions(current_user.id)

        # Ограничиваем количество результатов
        limited_transactions = transactions[:limit]

        return [
            TransactionResponse(
                id=t.id,
                amount=t.amount,
                transaction_type=t.transaction_type,
                status=t.status,
                description=t.description,
                created_at=t.created_at,
                completed_at=t.completed_at
            )
            for t in limited_transactions
        ]

    except Exception as e:
        logger.error(f"Get transactions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get transactions"
        )

@user_router.get("/transactions/summary")
async def get_transactions_summary(current_user = Depends(get_current_user)):
    """Получение сводки по транзакциям"""
    try:
        transactions = UserService.get_user_transactions(current_user.id)

        total_deposits = sum(t.amount for t in transactions if t.transaction_type == "deposit")
        total_withdrawals = sum(t.amount for t in transactions if t.transaction_type == "withdrawal")
        total_event_payments = sum(t.amount for t in transactions if t.transaction_type == "event_payment")

        return {
            "total_transactions": len(transactions),
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "total_event_payments": total_event_payments,
            "current_balance": current_user.balance,
            "net_flow": total_deposits - total_withdrawals - total_event_payments
        }

    except Exception as e:
        logger.error(f"Get transaction summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get transaction summary"
        )

# =============================================================================
# СОБЫТИЯ ПОЛЬЗОВАТЕЛЯ
# =============================================================================

@user_router.get("/events", response_model=List[EventResponse])
async def get_my_events(current_user = Depends(get_current_user)):
    """Получение событий, созданных пользователем"""
    try:
        events = EventService.get_events_by_creator(current_user.id)

        return [
            EventResponse(
                id=e.id,
                title=e.title,
                description=e.description,
                cost=e.cost,
                max_participants=e.max_participants,
                current_participants=e.current_participants,
                status=e.status,
                creator_id=e.creator_id,
                event_date=e.event_date,
                created_at=e.created_at
            )
            for e in events
        ]

    except Exception as e:
        logger.error(f"Get my events error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get events"
        )

@user_router.get("/events/stats")
async def get_events_stats(current_user = Depends(get_current_user)):
    """Получение статистики по событиям пользователя"""
    try:
        events = EventService.get_events_by_creator(current_user.id)

        total_events = len(events)
        active_events = len([e for e in events if e.status == "active"])
        completed_events = len([e for e in events if e.status == "completed"])
        total_participants = sum(e.current_participants for e in events)
        total_revenue = sum(e.cost * e.current_participants for e in events)

        return {
            "total_events": total_events,
            "active_events": active_events,
            "completed_events": completed_events,
            "total_participants": total_participants,
            "total_revenue": total_revenue,
            "average_participants": total_participants / max(total_events, 1)
        }

    except Exception as e:
        logger.error(f"Get events stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get events statistics"
        )

# =============================================================================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

@user_router.delete("/profile")
async def delete_account(current_user = Depends(get_current_user)):
    """Удаление аккаунта пользователя"""
    try:
        # В реальном приложении здесь была бы логика удаления/деактивации
        # Пока просто возвращаем сообщение
        logger.warning(f"Account deletion requested by user {current_user.id}")

        return {
            "message": "Account deletion requested",
            "user_id": current_user.id,
            "note": "This action requires manual approval"
        }

    except Exception as e:
        logger.error(f"Account deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )

@user_router.get("/activity")
async def get_activity_log(
    days: int = 30,
    current_user = Depends(get_current_user)
):
    """Получение журнала активности пользователя"""
    try:
        if days > 90:
            days = 90  # Максимум 90 дней

        # В реальном приложении здесь был бы сервис логирования активности
        # Пока используем транзакции как активность
        transactions = UserService.get_user_transactions(current_user.id)

        # Фильтруем по дням
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_transactions = [
            t for t in transactions
            if t.created_at and t.created_at >= cutoff_date
        ]

        activity_log = [
            {
                "timestamp": t.created_at,
                "action": f"{t.transaction_type}: {t.amount}",
                "description": t.description,
                "status": t.status
            }
            for t in recent_transactions
        ]

        return {
            "period_days": days,
            "total_activities": len(activity_log),
            "activities": activity_log
        }

    except Exception as e:
        logger.error(f"Get activity log error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get activity log"
        )
