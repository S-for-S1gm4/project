"""
Маршруты для работы с событиями
Обновленная версия для структурированной архитектуры
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
from datetime import datetime
import logging

from schemas.event import (
    EventCreateRequest, EventUpdateRequest, EventResponse, JoinEventResponse,
    PredictionRequest, PredictionResponse, EventSearchResponse, EventActivationResponse,
    EventsOverviewResponse, EventParticipantsResponse, PredictionHistoryResponse
)
from services.user_service import UserService
from services.event_service import EventService
from core.auth import get_current_user, get_current_user_optional
from core.exceptions import (
    EventNotFoundException, InsufficientBalanceException,
    EventFullException, EventNotActiveException, ValidationException,
    PermissionDeniedException
)

logger = logging.getLogger(__name__)

event_router = APIRouter(prefix="/api/events", tags=["Events"])


def check_event_creator_or_admin(event, current_user):
    """Вспомогательная функция для проверки прав на событие"""
    if event.creator_id != current_user.id and current_user.role != "admin":
        raise PermissionDeniedException(
            action="modify event",
            resource=f"event {event.id}"
        )


@event_router.get("/", response_model=List[EventResponse])
async def get_events(
    status_filter: Optional[str] = Query(None, description="Фильтр по статусу: active, draft, completed, cancelled"),
    cost_max: Optional[float] = Query(None, description="Максимальная стоимость"),
    search: Optional[str] = Query(None, description="Поиск по названию или описанию"),
    limit: int = Query(50, le=100, description="Количество событий"),
    current_user = Depends(get_current_user_optional)
):
    """Получение списка событий с фильтрами"""
    try:
        # Получаем события на основе фильтра статуса
        if status_filter == "active" or not status_filter:
            events = EventService.get_active_events()
        else:
            events = EventService.get_all_events()
            if status_filter:
                events = [e for e in events if e.status == status_filter]

        # Применяем фильтры
        if cost_max is not None:
            events = [e for e in events if e.cost <= cost_max]

        if search:
            search_lower = search.lower()
            events = [
                e for e in events
                if search_lower in e.title.lower() or
                (e.description and search_lower in e.description.lower())
            ]

        # Ограничиваем количество
        events = events[:limit]

        # Формируем ответ
        result = []
        for e in events:
            can_join = e.can_join()
            if current_user:
                can_join = can_join and current_user.has_sufficient_balance(e.cost)

            result.append(EventResponse(
                id=e.id,
                title=e.title,
                description=e.description,
                cost=e.cost,
                max_participants=e.max_participants,
                current_participants=e.current_participants,
                status=e.status,
                creator_id=e.creator_id,
                event_date=e.event_date,
                created_at=e.created_at,
                can_join=can_join
            ))

        return result

    except Exception as e:
        logger.error(f"Get events error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get events"
        )


@event_router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    current_user = Depends(get_current_user_optional)
):
    """Получение информации о конкретном событии"""
    try:
        event = EventService.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundException(event_id)

        can_join = event.can_join()
        if current_user:
            can_join = can_join and current_user.has_sufficient_balance(event.cost)

        return EventResponse(
            id=event.id,
            title=event.title,
            description=event.description,
            cost=event.cost,
            max_participants=event.max_participants,
            current_participants=event.current_participants,
            status=event.status,
            creator_id=event.creator_id,
            event_date=event.event_date,
            created_at=event.created_at,
            can_join=can_join
        )

    except EventNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Get event error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get event"
        )


@event_router.post("/", response_model=EventResponse)
async def create_event(
    event_data: EventCreateRequest,
    current_user = Depends(get_current_user)
):
    """Создание нового события"""
    try:
        # Валидация данных
        if event_data.cost < 0:
            raise ValidationException("cost", "Event cost cannot be negative")

        if event_data.max_participants is not None and event_data.max_participants <= 0:
            raise ValidationException("max_participants", "Maximum participants must be positive")

        if event_data.event_date and event_data.event_date <= datetime.utcnow():
            raise ValidationException("event_date", "Event date must be in the future")

        # Создаем событие
        event = EventService.create_event(
            title=event_data.title,
            description=event_data.description,
            creator_id=current_user.id,
            cost=event_data.cost,
            max_participants=event_data.max_participants,
            event_date=event_data.event_date
        )

        logger.info(f"Event created: {event.title} by user {current_user.id}")

        return EventResponse(
            id=event.id,
            title=event.title,
            description=event.description,
            cost=event.cost,
            max_participants=event.max_participants,
            current_participants=event.current_participants,
            status=event.status,
            creator_id=event.creator_id,
            event_date=event.event_date,
            created_at=event.created_at,
            can_join=event.can_join()
        )

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Create event error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create event"
        )


@event_router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventUpdateRequest,
    current_user = Depends(get_current_user)
):
    """Обновление события (только создатель или админ)"""
    try:
        # Получаем событие
        event = EventService.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundException(event_id)

        # Проверяем права
        check_event_creator_or_admin(event, current_user)

        # В реальном приложении здесь была бы функция обновления
        logger.info(f"Event update requested: {event_id} by user {current_user.id}")

        return EventResponse(
            id=event.id,
            title=event.title,
            description=event.description,
            cost=event.cost,
            max_participants=event.max_participants,
            current_participants=event.current_participants,
            status=event.status,
            creator_id=event.creator_id,
            event_date=event.event_date,
            created_at=event.created_at,
            can_join=event.can_join()
        )

    except (EventNotFoundException, PermissionDeniedException) as e:
        error_code = status.HTTP_404_NOT_FOUND if isinstance(e, EventNotFoundException) else status.HTTP_403_FORBIDDEN
        raise HTTPException(
            status_code=error_code,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Update event error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update event"
        )


@event_router.post("/{event_id}/join", response_model=JoinEventResponse)
async def join_event(
    event_id: int,
    current_user = Depends(get_current_user)
):
    """Присоединение к событию"""
    try:
        # Получаем событие
        event = EventService.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundException(event_id)

        # Проверяем, что пользователь не создатель события
        if event.creator_id == current_user.id:
            raise ValidationException("user", "Cannot join your own event")

        # Присоединяемся к событию
        success = EventService.join_event(current_user.id, event_id)

        if not success:
            # Определяем причину неудачи более точно
            if not event.can_join():
                if event.status != "active":
                    raise EventNotActiveException(event.title, event.status)
                elif event.max_participants and event.current_participants >= event.max_participants:
                    raise EventFullException(event.title)

            if event.cost > current_user.balance:
                raise InsufficientBalanceException(event.cost, current_user.balance)

            # Общая ошибка, если не можем определить причину
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot join event"
            )

        # Получаем обновленные данные
        updated_event = EventService.get_event_by_id(event_id)
        updated_user = UserService.get_user_by_id(current_user.id)

        logger.info(f"User {current_user.id} joined event {event_id}")

        return JoinEventResponse(
            message="Successfully joined event",
            event_id=event_id,
            event_title=updated_event.title,
            cost=updated_event.cost,
            new_balance=updated_user.balance,
            current_participants=updated_event.current_participants
        )

    except (EventNotFoundException, EventNotActiveException, EventFullException,
            InsufficientBalanceException, ValidationException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Join event error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join event"
        )


@event_router.post("/{event_id}/activate", response_model=EventActivationResponse)
async def activate_event(
    event_id: int,
    current_user = Depends(get_current_user)
):
    """Активация события (создатель или админ)"""
    try:
        # Получаем событие
        event = EventService.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundException(event_id)

        # Проверяем права
        check_event_creator_or_admin(event, current_user)

        # Активируем событие
        success = EventService.activate_event(event_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to activate event"
            )

        logger.info(f"Event {event_id} activated by user {current_user.id}")

        return EventActivationResponse(
            message=f"Event '{event.title}' activated successfully",
            event_id=event_id,
            status="active"
        )

    except (EventNotFoundException, PermissionDeniedException) as e:
        error_code = status.HTTP_404_NOT_FOUND if isinstance(e, EventNotFoundException) else status.HTTP_403_FORBIDDEN
        raise HTTPException(
            status_code=error_code,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Activate event error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate event"
        )


@event_router.post("/predict", response_model=PredictionResponse)
async def predict_event_participation(
    prediction_data: PredictionRequest,
    current_user = Depends(get_current_user)
):
    """Предсказание участия в событии на основе ML"""
    try:
        # Получаем информацию о событии
        event = EventService.get_event_by_id(prediction_data.event_id)
        if not event:
            raise EventNotFoundException(prediction_data.event_id)

        # Простая эвристическая модель предсказания
        user_balance = current_user.balance
        event_cost = event.cost

        # Базовые факторы
        can_afford = user_balance >= event_cost
        balance_ratio = user_balance / max(event_cost, 1)

        # Факторы из пользовательских данных
        interest_level = prediction_data.user_features.get('interest_level', 0.5)
        past_participation = prediction_data.user_features.get('past_participation', 0.5)
        event_type_preference = prediction_data.user_features.get('event_type_preference', 0.5)

        # Расчет вероятности с улучшенной логикой
        if not can_afford:
            prediction = "unlikely_to_join"
            confidence = 0.2 + (balance_ratio * 0.3)
            recommendation = f"Consider adding ${event_cost - user_balance:.2f} to your balance"
        elif balance_ratio >= 3 and interest_level > 0.7:
            prediction = "very_likely_to_join"
            confidence = 0.85 + min(0.1, (balance_ratio - 3) * 0.02)
            recommendation = "This event seems perfect for you! Join now."
        elif balance_ratio >= 2 and interest_level > 0.5:
            prediction = "likely_to_join"
            confidence = 0.65 + (interest_level * 0.2)
            recommendation = "You have good chances of enjoying this event."
        elif balance_ratio >= 1.5:
            prediction = "might_join"
            confidence = 0.45 + (past_participation * 0.2) + (event_type_preference * 0.15)
            recommendation = "Consider your schedule and interest level."
        else:
            prediction = "unlikely_to_join"
            confidence = 0.3 + (interest_level * 0.2)
            recommendation = "You might want to wait for events that better match your budget."

        # Учитываем заполненность события
        if event.max_participants:
            fill_rate = event.current_participants / event.max_participants
            if fill_rate > 0.8:
                confidence *= 1.1  # Популярное событие
                if prediction == "likely_to_join":
                    recommendation += " Hurry up, limited spots available!"

        # Ограничиваем confidence
        confidence = min(confidence, 0.95)

        # Записываем запрос в историю (с обработкой ошибок)
        try:
            UserService.add_balance(
                current_user.id,
                0.0,
                f"ML prediction request for event: {event.title}"
            )
        except Exception as log_error:
            logger.warning(f"Failed to log prediction request: {log_error}")

        logger.info(f"Prediction generated for user {current_user.id}, event {prediction_data.event_id}")

        return PredictionResponse(
            prediction=prediction,
            confidence=round(confidence, 3),
            event_id=prediction_data.event_id,
            cost=event.cost,
            recommendation=recommendation
        )

    except EventNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate prediction"
        )


@event_router.get("/predictions/history", response_model=PredictionHistoryResponse)
async def get_prediction_history(current_user = Depends(get_current_user)):
    """Получение истории запросов на предсказания"""
    try:
        # Получаем транзакции, связанные с предсказаниями
        transactions = UserService.get_user_transactions(current_user.id)

        prediction_transactions = [
            t for t in transactions
            if t.description and "ML prediction request" in t.description
        ]

        # Группируем по событиям
        predictions_by_event = {}
        for t in prediction_transactions:
            try:
                event_name = t.description.split(":")[-1].strip()
                if event_name not in predictions_by_event:
                    predictions_by_event[event_name] = []
                predictions_by_event[event_name].append({
                    "id": t.id,
                    "requested_at": t.created_at,
                    "status": t.status
                })
            except (IndexError, AttributeError):
                continue  # Пропускаем некорректные записи

        from schemas.event import PredictionHistoryEntry
        recent_predictions = []
        for t in prediction_transactions[:10]:  # Последние 10
            try:
                event_name = t.description.split(":")[-1].strip()
                recent_predictions.append(PredictionHistoryEntry(
                    id=t.id,
                    event_name=event_name,
                    requested_at=t.created_at,
                    status=t.status
                ))
            except (IndexError, AttributeError):
                continue  # Пропускаем некорректные записи

        return PredictionHistoryResponse(
            total_predictions=len(prediction_transactions),
            unique_events=len(predictions_by_event),
            predictions_by_event=predictions_by_event,
            recent_predictions=recent_predictions
        )

    except Exception as e:
        logger.error(f"Get prediction history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get prediction history"
        )


@event_router.get("/stats/overview", response_model=EventsOverviewResponse)
async def get_events_overview():
    """Общая статистика по событиям"""
    try:
        all_events = EventService.get_all_events()
        active_events = EventService.get_active_events()

        total_events = len(all_events)
        active_count = len(active_events)

        # Статистика по статусам
        status_stats = {}
        for event in all_events:
            status = event.status
            status_stats[status] = status_stats.get(status, 0) + 1

        # Статистика по стоимости
        free_events = len([e for e in all_events if e.cost == 0])
        paid_events = len([e for e in all_events if e.cost > 0])

        # Общая статистика участников
        total_participants = sum(e.current_participants for e in all_events)
        avg_participants = total_participants / max(total_events, 1)

        # Статистика по доходам
        total_revenue = sum(e.cost * e.current_participants for e in all_events)

        most_popular_events = [
            {
                "id": e.id,
                "title": e.title,
                "participants": e.current_participants,
                "cost": e.cost
            }
            for e in sorted(all_events, key=lambda x: x.current_participants, reverse=True)[:5]
        ]

        return EventsOverviewResponse(
            total_events=total_events,
            active_events=active_count,
            status_breakdown=status_stats,
            free_events=free_events,
            paid_events=paid_events,
            total_participants=total_participants,
            average_participants_per_event=round(avg_participants, 2),
            total_revenue=total_revenue,
            most_popular_events=most_popular_events
        )

    except Exception as e:
        logger.error(f"Get events overview error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get events overview"
        )


@event_router.get("/{event_id}/participants", response_model=EventParticipantsResponse)
async def get_event_participants(
    event_id: int,
    current_user = Depends(get_current_user)
):
    """Получение списка участников события (только для создателя или админа)"""
    try:
        # Получаем событие
        event = EventService.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundException(event_id)

        # Проверяем права доступа
        check_event_creator_or_admin(event, current_user)

        # В реальном приложении здесь был бы запрос к БД для получения участников
        return EventParticipantsResponse(
            event_id=event_id,
            event_title=event.title,
            current_participants=event.current_participants,
            max_participants=event.max_participants,
            participants=[]  # Здесь был бы список реальных участников
        )

    except (EventNotFoundException, PermissionDeniedException) as e:
        error_code = status.HTTP_404_NOT_FOUND if isinstance(e, EventNotFoundException) else status.HTTP_403_FORBIDDEN
        raise HTTPException(
            status_code=error_code,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Get event participants error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get event participants"
        )


@event_router.get("/search", response_model=EventSearchResponse)
async def search_events(
    query: str = Query(..., min_length=3, description="Поисковый запрос"),
    limit: int = Query(10, le=50, description="Количество результатов")
):
    """Поиск событий по названию и описанию"""
    try:
        all_events = EventService.get_active_events()

        # Простой поиск по названию и описанию
        query_lower = query.lower()
        matching_events = []

        for event in all_events:
            if (query_lower in event.title.lower() or
                (event.description and query_lower in event.description.lower())):
                matching_events.append(event)

        # Ограничиваем результаты
        matching_events = matching_events[:limit]

        events_response = [
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
                created_at=e.created_at,
                can_join=e.can_join()
            )
            for e in matching_events
        ]

        return EventSearchResponse(
            query=query,
            total_found=len(matching_events),
            events=events_response
        )

    except Exception as e:
        logger.error(f"Search events error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search events"
        )
