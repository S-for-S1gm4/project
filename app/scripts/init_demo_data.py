"""
Скрипт для инициализации базы данных демо-данными
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import init_db, test_connection
from services.user_service import UserService
from services.event_service import EventService
from models import UserRole, EventStatus
from datetime import datetime, timedelta
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_demo_users():
    """Создание демо пользователей"""
    logger.info("Creating demo users...")

    users_data = [
        {
            'email': 'admin@example.com',
            'username': 'admin',
            'password': 'admin123',
            'full_name': 'System Administrator',
            'role': UserRole.ADMIN
        },
        {
            'email': 'john.doe@example.com',
            'username': 'johndoe',
            'password': 'password123',
            'full_name': 'John Doe',
            'role': UserRole.USER
        },
        {
            'email': 'jane.smith@example.com',
            'username': 'janesmith',
            'password': 'password123',
            'full_name': 'Jane Smith',
            'role': UserRole.USER
        },
        {
            'email': 'bob.wilson@example.com',
            'username': 'bobwilson',
            'password': 'password123',
            'full_name': 'Bob Wilson',
            'role': UserRole.USER
        }
    ]

    created_users = []

    for user_data in users_data:
        try:
            user = UserService.create_user(**user_data)
            created_users.append(user)
            logger.info(f"Created user: {user.username} ({user.email})")
        except ValueError as e:
            logger.warning(f"User creation failed: {e}")

    return created_users


def add_demo_balance(users):
    """Добавление демо баланса пользователям"""
    logger.info("Adding demo balance to users...")

    balance_data = [
        {'user_id': 2, 'amount': 1000.0, 'description': 'Initial demo balance'},
        {'user_id': 3, 'amount': 750.0, 'description': 'Initial demo balance'},
        {'user_id': 4, 'amount': 500.0, 'description': 'Initial demo balance'},
    ]

    for balance_info in balance_data:
        try:
            UserService.add_balance(**balance_info)
            logger.info(f"Added balance {balance_info['amount']} to user {balance_info['user_id']}")
        except Exception as e:
            logger.error(f"Failed to add balance: {e}")


def create_demo_events():
    """Создание демо событий"""
    logger.info("Creating demo events...")

    # Получаем пользователей для создания событий
    users = UserService.get_all_users()
    if len(users) < 2:
        logger.error("Not enough users to create events")
        return []

    events_data = [
        {
            'title': 'Python Workshop',
            'description': 'Intensive Python programming workshop for beginners',
            'creator_id': users[1].id,  # John Doe
            'cost': 100.0,
            'max_participants': 20,
            'event_date': datetime.now() + timedelta(days=7)
        },
        {
            'title': 'Free Community Meetup',
            'description': 'Monthly community meetup for developers',
            'creator_id': users[2].id,  # Jane Smith
            'cost': 0.0,
            'max_participants': 50,
            'event_date': datetime.now() + timedelta(days=14)
        },
        {
            'title': 'Web Development Bootcamp',
            'description': 'Comprehensive web development course',
            'creator_id': users[1].id,  # John Doe
            'cost': 250.0,
            'max_participants': 15,
            'event_date': datetime.now() + timedelta(days=21)
        },
        {
            'title': 'Database Design Workshop',
            'description': 'Learn database design principles and best practices',
            'creator_id': users[3].id,  # Bob Wilson
            'cost': 150.0,
            'max_participants': 25,
            'event_date': datetime.now() + timedelta(days=30)
        }
    ]

    created_events = []

    for event_data in events_data:
        try:
            event = EventService.create_event(**event_data)
            created_events.append(event)
            logger.info(f"Created event: {event.title}")
        except Exception as e:
            logger.error(f"Failed to create event: {e}")

    return created_events


def activate_demo_events(events):
    """Активация демо событий"""
    logger.info("Activating demo events...")

    for event in events[:3]:  # Активируем первые 3 события
        try:
            EventService.activate_event(event.id)
            logger.info(f"Activated event: {event.title}")
        except Exception as e:
            logger.error(f"Failed to activate event {event.id}: {e}")


def simulate_event_participation():
    """Симуляция участия в событиях"""
    logger.info("Simulating event participation...")

    # Пользователь Jane Smith присоединяется к бесплатному мероприятию
    try:
        success = EventService.join_event(user_id=3, event_id=2)  # Jane -> Free Meetup
        if success:
            logger.info("Jane Smith joined Free Community Meetup")
    except Exception as e:
        logger.error(f"Failed to join event: {e}")

    # Пользователь Bob Wilson присоединяется к платному мероприятию
    try:
        success = EventService.join_event(user_id=4, event_id=1)  # Bob -> Python Workshop
        if success:
            logger.info("Bob Wilson joined Python Workshop")
    except Exception as e:
        logger.error(f"Failed to join event: {e}")


def perform_demo_transactions():
    """Выполнение демо транзакций"""
    logger.info("Performing demo transactions...")

    # Дополнительные пополнения баланса
    try:
        UserService.add_balance(2, 200.0, "Bonus payment")
        logger.info("Added bonus to John Doe")
    except Exception as e:
        logger.error(f"Failed to add bonus: {e}")

    # Списание средств (например, штраф)
    try:
        success = UserService.deduct_balance(3, 50.0, "Service fee")
        if success:
            logger.info("Deducted service fee from Jane Smith")
    except Exception as e:
        logger.error(f"Failed to deduct service fee: {e}")


def print_demo_data_summary():
    """Вывод сводки по созданным демо-данным"""
    logger.info("=== DEMO DATA SUMMARY ===")

    # Пользователи
    users = UserService.get_all_users()
    logger.info(f"Created {len(users)} users:")
    for user in users:
        logger.info(f"  - {user.username} ({user.email}) - Balance: {user.balance} - Role: {user.role}")

    # События
    events = EventService.get_all_events()
    logger.info(f"Created {len(events)} events:")
    for event in events:
        logger.info(f"  - {event.title} - Cost: {event.cost} - Status: {event.status} - Participants: {event.current_participants}")

    # Транзакции (для первого пользователя)
    if users:
        transactions = UserService.get_user_transactions(users[1].id)
        logger.info(f"User {users[1].username} has {len(transactions)} transactions:")
        for transaction in transactions[:5]:  # Показываем первые 5
            logger.info(f"  - {transaction.transaction_type}: {transaction.amount} - {transaction.status}")


def main():
    """Основная функция инициализации"""
    logger.info("Starting demo data initialization...")

    try:
        # Проверяем подключение к БД
        if not test_connection():
            logger.error("Database connection failed!")
            return False

        # Инициализируем БД
        init_db(drop_all=True)  # Пересоздаем таблицы

        # Создаем демо-данные
        users = create_demo_users()
        if not users:
            logger.error("Failed to create users!")
            return False

        add_demo_balance(users)

        events = create_demo_events()
        if not events:
            logger.error("Failed to create events!")
            return False

        activate_demo_events(events)
        simulate_event_participation()
        perform_demo_transactions()

        # Выводим сводку
        print_demo_data_summary()

        logger.info("Demo data initialization completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Demo data initialization failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
