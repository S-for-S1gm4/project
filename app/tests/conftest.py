"""
Конфигурация для pytest тестов Event Planner API
"""
import pytest
import sys
import os
from datetime import datetime, timedelta

# Добавляем путь к приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from database.database import get_database_engine, init_db
from database.config import get_settings
from services.user_service import UserService
from services.event_service import EventService
from models import User, Event, Transaction, UserRole, EventStatus
from sqlmodel import SQLModel, Session, create_engine


@pytest.fixture(scope="session")
def test_engine():
    """Создание тестового движка базы данных"""
    settings = get_settings()

    # Создаем тестовую базу данных в памяти
    test_db_url = "sqlite:///:memory:"
    engine = create_engine(test_db_url, echo=False)

    # Создаем все таблицы
    SQLModel.metadata.create_all(engine)

    return engine


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Создание тестовой сессии для каждого теста"""
    with Session(test_engine) as session:
        yield session
        # Очищаем данные после каждого теста
        session.rollback()


@pytest.fixture(scope="function")
def clean_db(test_engine):
    """Очистка базы данных перед каждым тестом"""
    # Пересоздаем все таблицы
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    yield
    # Очистка после теста
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def sample_user_data():
    """Тестовые данные пользователя"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass123",
        "full_name": "Test User"
    }


@pytest.fixture
def sample_admin_data():
    """Тестовые данные администратора"""
    return {
        "email": "admin@example.com",
        "username": "testadmin",
        "password": "adminpass123",
        "full_name": "Test Admin",
        "role": UserRole.ADMIN
    }


@pytest.fixture
def sample_event_data():
    """Тестовые данные события"""
    return {
        "title": "Test Workshop",
        "description": "A test workshop for pytest",
        "cost": 100.0,
        "max_participants": 20,
        "event_date": datetime.utcnow() + timedelta(days=7)
    }


@pytest.fixture
def sample_free_event_data():
    """Тестовые данные бесплатного события"""
    return {
        "title": "Free Meetup",
        "description": "A free meetup for testing",
        "cost": 0.0,
        "max_participants": 50,
        "event_date": datetime.utcnow() + timedelta(days=14)
    }


@pytest.fixture
def created_user(clean_db, sample_user_data):
    """Фикстура для создания тестового пользователя"""
    user = UserService.create_user(**sample_user_data)
    return user


@pytest.fixture
def created_admin(clean_db, sample_admin_data):
    """Фикстура для создания тестового администратора"""
    admin = UserService.create_user(**sample_admin_data)
    return admin


@pytest.fixture
def user_with_balance(created_user):
    """Фикстура пользователя с балансом"""
    UserService.add_balance(created_user.id, 1000.0, "Initial test balance")
    return UserService.get_user_by_id(created_user.id)


@pytest.fixture
def created_event(clean_db, created_user, sample_event_data):
    """Фикстура для создания тестового события"""
    event = EventService.create_event(
        creator_id=created_user.id,
        **sample_event_data
    )
    return event


@pytest.fixture
def active_event(created_event):
    """Фикстура активного события"""
    EventService.activate_event(created_event.id)
    return EventService.get_event_by_id(created_event.id)


@pytest.fixture
def multiple_users(clean_db):
    """Фикстура для создания нескольких пользователей"""
    users = []
    for i in range(3):
        user_data = {
            "email": f"user{i}@example.com",
            "username": f"user{i}",
            "password": "password123",
            "full_name": f"User {i}"
        }
        user = UserService.create_user(**user_data)
        # Добавляем разный баланс
        UserService.add_balance(user.id, 100.0 * (i + 1), f"Initial balance for user {i}")
        users.append(user)
    return users


@pytest.fixture
def multiple_events(clean_db, created_user):
    """Фикстура для создания нескольких событий"""
    events = []

    # Платное событие
    paid_event = EventService.create_event(
        title="Paid Workshop",
        description="A paid workshop",
        creator_id=created_user.id,
        cost=150.0,
        max_participants=10
    )

    # Бесплатное событие
    free_event = EventService.create_event(
        title="Free Meetup",
        description="A free meetup",
        creator_id=created_user.id,
        cost=0.0,
        max_participants=30
    )

    # Дорогое событие
    expensive_event = EventService.create_event(
        title="Premium Course",
        description="An expensive premium course",
        creator_id=created_user.id,
        cost=500.0,
        max_participants=5
    )

    events = [paid_event, free_event, expensive_event]

    # Активируем все события
    for event in events:
        EventService.activate_event(event.id)

    return events


# Monkey patching для использования тестовой БД в сервисах
@pytest.fixture(autouse=True)
def patch_database_session(test_engine, monkeypatch):
    """Автоматическое переключение сервисов на тестовую БД"""
    from database.database import get_db_session

    def mock_get_db_session():
        with Session(test_engine) as session:
            yield session

    # Заменяем функцию получения сессии
    monkeypatch.setattr("services.user_service.get_db_session", mock_get_db_session)
    monkeypatch.setattr("services.event_service.get_db_session", mock_get_db_session)


@pytest.fixture
def transaction_history_user(clean_db, sample_user_data):
    """Пользователь с историей транзакций"""
    user = UserService.create_user(**sample_user_data)

    # Создаем несколько транзакций
    UserService.add_balance(user.id, 500.0, "Initial deposit")
    UserService.add_balance(user.id, 200.0, "Second deposit")
    UserService.deduct_balance(user.id, 150.0, "Test withdrawal")
    UserService.add_balance(user.id, 100.0, "Third deposit")

    return user


@pytest.fixture
def limited_event(clean_db, created_user):
    """Событие с ограниченным количеством участников"""
    event = EventService.create_event(
        title="Limited Event",
        description="Event with only 2 spots",
        creator_id=created_user.id,
        cost=50.0,
        max_participants=2
    )
    EventService.activate_event(event.id)
    return event
