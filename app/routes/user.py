"""
Маршруты для работы с пользователями
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List
import logging

from schemas.user import (
    UserResponse, BalanceRequest, BalanceResponse, TransactionResponse,
    EventResponse, UserProfileUpdateRequest, UserBalanceInfo,
    TransactionSummary, EventsStats, ActivityLogResponse
)
from services.user_service import UserService
from services.event_service import EventService
from core.auth import get_current_user
from core.exceptions import (
    UserNotFoundException, InsufficientBalanceException, ValidationException
)

logger = logging.getLogger(__name__)

user_router = APIRouter(prefix="/api/users", tags=["User Profile"])


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
    profile_data: UserProfileUpdateRequest,
    current_user = Depends(get_current_user)
):
    """Обновление профиля пользователя"""
    try:
        # В реальном приложении здесь была бы функция обновления в UserService
        logger.info(f"Profile update requested by user {current_user.id}")

        return {
            "message": "Profile updated successfully",
            "user_id": current_user.id,
            "updated_fields": profile_data.dict(exclude_unset=True)
        }

    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@user_router.get("/balance", response_model=UserBalanceInfo)
async def get_balance(current_user = Depends(get_current_user)):
    """Получение баланса пользователя"""
    return UserBalanceInfo(
        user_id=current_user.id,
        username=current_user.username,
        balance=current_user.balance,
        currency="USD",
        last_updated=current_user.updated_at
    )


@user_router.post("/balance", response_model=BalanceResponse)
async def add_balance(
    balance_data: BalanceRequest,
    current_user = Depends(get_current_user)
):
    """Пополнение баланса"""
    try:
        if balance_data.amount <= 0:
            raise ValidationException("amount", "Amount must be positive")

        if balance_data.amount > 10000:  # Лимит пополнения
            raise ValidationException("amount", "Amount exceeds maximum limit of $10,000")

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

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Balance addition error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add balance"
        )


@user_router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    limit: int = Query(50, le=100, description="Количество транзакций"),
    current_user = Depends(get_current_user)
):
    """Получение истории транзакций пользователя"""
    try:
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


@user_router.get("/transactions/summary", response_model=TransactionSummary)
async def get_transactions_summary(current_user = Depends(get_current_user)):
    """Получение сводки по транзакциям"""
    try:
        transactions = UserService.get_user_transactions(current_user.id)

        total_deposits = sum(t.amount for t in transactions if t.transaction_type == "deposit")
        total_withdrawals = sum(t.amount for t in transactions if t.transaction_type == "withdrawal")
        total_event_payments = sum(t.amount for t in transactions if t.transaction_type == "event_payment")

        return TransactionSummary(
            total_transactions=len(transactions),
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            total_event_payments=total_event_payments,
            current_balance=current_user.balance,
            net_flow=total_deposits - total_withdrawals - total_event_payments
        )

    except Exception as e:
        logger.error(f"Get transaction summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get transaction summary"
        )


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


@user_router.get("/events/stats", response_model=EventsStats)
async def get_events_stats(current_user = Depends(get_current_user)):
    """Получение статистики по событиям пользователя"""
    try:
        events = EventService.get_events_by_creator(current_user.id)

        total_events = len(events)
        active_events = len([e for e in events if e.status == "active"])
        completed_events = len([e for e in events if e.status == "completed"])
        total_participants = sum(e.current_participants for e in events)
        total_revenue = sum(e.cost * e.current_participants for e in events)

        return EventsStats(
            total_events=total_events,
            active_events=active_events,
            completed_events=completed_events,
            total_participants=total_participants,
            total_revenue=total_revenue,
            average_participants=total_participants / max(total_events, 1)
        )

    except Exception as e:
        logger.error(f"Get events stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get events statistics"
        )


@user_router.get("/activity", response_model=ActivityLogResponse)
async def get_activity_log(
    days: int = Query(30, le=90, description="Период в днях"),
    current_user = Depends(get_current_user)
):
    """Получение журнала активности пользователя"""
    try:
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

        from schemas.user import ActivityLogEntry
        activity_log = [
            ActivityLogEntry(
                timestamp=t.created_at,
                action=f"{t.transaction_type}: {t.amount}",
                description=t.description,
                status=t.status
            )
            for t in recent_transactions
        ]

        return ActivityLogResponse(
            period_days=days,
            total_activities=len(activity_log),
            activities=activity_log
        )

    except Exception as e:
        logger.error(f"Get activity log error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get activity log"
        )


@user_router.delete("/profile")
async def delete_account(current_user = Depends(get_current_user)):
    """Удаление аккаунта пользователя"""
    try:
        # В реальном приложении здесь была бы логика удаления/деактивации
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
