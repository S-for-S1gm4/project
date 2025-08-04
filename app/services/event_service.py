from sqlmodel import Session, select
from typing import Optional, List
from models import Event, EventStatus, User, Transaction, TransactionType
from database.database import get_db_session
from services.user_service import UserService
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EventService:
    """Сервис для работы с событиями"""

    @staticmethod
    def create_event(title: str, description: str, creator_id: int,
                    cost: float = 0.0, max_participants: Optional[int] = None,
                    event_date: Optional[datetime] = None) -> Event:
        """Создание нового события"""
        with get_db_session() as session:
            # Проверяем, существует ли создатель
            creator = session.get(User, creator_id)
            if not creator:
                raise ValueError(f"Creator with id {creator_id} not found")

            event = Event(
                title=title,
                description=description,
                creator_id=creator_id,
                cost=cost,
                max_participants=max_participants,
                event_date=event_date
            )

            session.add(event)
            session.commit()
            session.refresh(event)

            logger.info(f"Created event: {event}")
            return event

    @staticmethod
    def get_event_by_id(event_id: int) -> Optional[Event]:
        """Получение события по ID"""
        with get_db_session() as session:
            return session.get(Event, event_id)

    @staticmethod
    def get_all_events() -> List[Event]:
        """Получение всех событий"""
        with get_db_session() as session:
            return list(session.exec(select(Event)).all())

    @staticmethod
    def get_active_events() -> List[Event]:
        """Получение активных событий"""
        with get_db_session() as session:
            return list(session.exec(
                select(Event).where(Event.status == EventStatus.ACTIVE)
            ).all())

    @staticmethod
    def activate_event(event_id: int) -> bool:
        """Активация события"""
        with get_db_session() as session:
            event = session.get(Event, event_id)
            if not event:
                raise ValueError(f"Event with id {event_id} not found")

            event.status = EventStatus.ACTIVE
            event.updated_at = datetime.utcnow()

            session.add(event)
            session.commit()

            logger.info(f"Activated event {event_id}")
            return True

    @staticmethod
    def join_event(user_id: int, event_id: int) -> bool:
        """Присоединение пользователя к событию"""
        with get_db_session() as session:
            user = session.get(User, user_id)
            event = session.get(Event, event_id)

            if not user:
                raise ValueError(f"User with id {user_id} not found")

            if not event:
                raise ValueError(f"Event with id {event_id} not found")

            # Проверяем возможность присоединения
            if not event.can_join():
                logger.warning(f"Cannot join event {event_id}: event is full or inactive")
                return False

            # Проверяем баланс, если событие платное
            if event.cost > 0:
                if not user.has_sufficient_balance(event.cost):
                    logger.warning(f"User {user_id} has insufficient balance for event {event_id}")
                    return False

                # Списываем средства
                success = UserService.deduct_balance(
                    user_id,
                    event.cost,
                    f"Payment for event: {event.title}"
                )

                if not success:
                    return False

                # Создаем транзакцию для оплаты события
                transaction = Transaction(
                    user_id=user_id,
                    event_id=event_id,
                    amount=event.cost,
                    transaction_type=TransactionType.EVENT_PAYMENT,
                    description=f"Payment for event: {event.title}"
                )
                transaction.complete()
                session.add(transaction)

            # Присоединяем к событию
            event.join_event()
            session.add(event)
            session.commit()

            logger.info(f"User {user_id} joined event {event_id}")
            return True

    @staticmethod
    def get_events_by_creator(creator_id: int) -> List[Event]:
        """Получение событий по создателю"""
        with get_db_session() as session:
            return list(session.exec(
                select(Event).where(Event.creator_id == creator_id)
            ).all())
