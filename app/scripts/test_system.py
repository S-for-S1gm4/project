"""
Скрипт для тестирования работоспособности системы
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.user_service import UserService
from services.event_service import EventService
from models import UserRole
from datetime import datetime, timedelta
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_user_operations():
    """Тестирование операций с пользователями"""
    logger.info("=== TESTING USER OPERATIONS ===")

    try:
        # Тест 1: Создание пользователя
        logger.info("Test 1: Creating a new user")
        user = UserService.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            full_name="Test User"
        )
        logger.info(f"✓ Created user: {user}")

        # Тест 2: Получение пользователя по ID
        logger.info("Test 2: Getting user by ID")
        retrieved_user = UserService.get_user_by_id(user.id)
        assert retrieved_user is not None
        assert retrieved_user.email == user.email
        logger.info(f"✓ Retrieved user: {retrieved_user}")

        # Тест 3: Получение пользователя по email
        logger.info("Test 3: Getting user by email")
        user_by_email = UserService.get_user_by_email("test@example.com")
        assert user_by_email is not None
        assert user_by_email.id == user.id
        logger.info(f"✓ Retrieved user by email: {user_by_email}")

        # Тест 4: Пополнение баланса
        logger.info("Test 4: Adding balance")
        initial_balance = user.balance
        UserService.add_balance(user.id, 500.0, "Test deposit")
        updated_user = UserService.get_user_by_id(user.id)
        assert updated_user.balance == initial_balance + 500.0
        logger.info(f"✓ Balance updated: {initial_balance} -> {updated_user.balance}")

        # Тест 5: Списание баланса (успешное)
        logger.info("Test 5: Deducting balance (sufficient funds)")
        success = UserService.deduct_balance(user.id, 200.0, "Test withdrawal")
        assert success == True
        updated_user = UserService.get_user_by_id(user.id)
        logger.info(f"✓ Balance after deduction: {updated_user.balance}")

        # Тест 6: Списание баланса (недостаточно средств)
        logger.info("Test 6: Deducting balance (insufficient funds)")
        success = UserService.deduct_balance(user.id, 1000.0, "Test large withdrawal")
        assert success == False
        logger.info("✓ Correctly rejected withdrawal due to insufficient funds")

        # Тест 7: История транзакций
        logger.info("Test 7: Getting transaction history")
        transactions = UserService.get_user_transactions(user.id)
        assert len(transactions) >= 2  # Должно быть минимум 2 транзакции
        logger.info(f"✓ Retrieved {len(transactions)} transactions")
        for i, transaction in enumerate(transactions[:3], 1):
            logger.info(f"  Transaction {i}: {transaction.transaction_type} - {transaction.amount}")

        return user.id

    except Exception as e:
        logger.error(f"✗ User operations test failed: {e}")
        raise


def test_event_operations(test_user_id):
    """Тестирование операций с событиями"""
    logger.info("=== TESTING EVENT OPERATIONS ===")

    try:
        # Тест 1: Создание события
        logger.info("Test 1: Creating a new event")
        event = EventService.create_event(
            title="Test Workshop",
            description="A test workshop for system testing",
            creator_id=test_user_id,
            cost=150.0,
            max_participants=10,
            event_date=datetime.now() + timedelta(days=7)
        )
        logger.info(f"✓ Created event: {event}")

        # Тест 2: Получение события по ID
        logger.info("Test 2: Getting event by ID")
        retrieved_event = EventService.get_event_by_id(event.id)
        assert retrieved_event is not None
        assert retrieved_event.title == event.title
        logger.info(f"✓ Retrieved event: {retrieved_event}")

        # Тест 3: Активация события
        logger.info("Test 3: Activating event")
        success = EventService.activate_event(event.id)
        assert success == True
        activated_event = EventService.get_event_by_id(event.id)
        logger.info(f"✓ Event activated, status: {activated_event.status}")

        # Тест 4: Получение активных событий
        logger.info("Test 4: Getting active events")
        active_events = EventService.get_active_events()
        assert len(active_events) > 0
        logger.info(f"✓ Found {len(active_events)} active events")

        # Тест 5: Создание второго пользователя для тестирования участия
        logger.info("Test 5: Creating second user for participation test")
        participant = UserService.create_user(
            email="participant@example.com",
            username="participant",
            password="pass123",
            full_name="Event Participant"
        )
        # Добавляем баланс участнику
        UserService.add_balance(participant.id, 300.0, "Initial balance")
        logger.info(f"✓ Created participant: {participant}")

        # Тест 6: Присоединение к событию (успешное)
        logger.info("Test 6: Joining event (sufficient balance)")
        success = EventService.join_event(participant.id, event.id)
        assert success == True
        updated_event = EventService.get_event_by_id(event.id)
        logger.info(f"✓ Successfully joined event. Participants: {updated_event.current_participants}")

        # Проверяем, что баланс участника уменьшился
        updated_participant = UserService.get_user_by_id(participant.id)
        logger.info(f"✓ Participant balance after payment: {updated_participant.balance}")

        # Тест 7: Попытка присоединения к событию (недостаточно средств)
        logger.info("Test 7: Creating user with insufficient balance")
        poor_user = UserService.create_user(
            email="poor@example.com",
            username="pooruser",
            password="pass123",
            full_name="Poor User"
        )
        UserService.add_balance(poor_user.id, 50.0, "Small balance")  # Меньше стоимости события

        success = EventService.join_event(poor_user.id, event.id)
        assert success == False
        logger.info("✓ Correctly rejected joining due to insufficient balance")

        # Тест 8: Получение событий по создателю
        logger.info("Test 8: Getting events by creator")
        creator_events = EventService.get_events_by_creator(test_user_id)
        assert len(creator_events) > 0
        logger.info(f"✓ Found {len(creator_events)} events by creator")

        return event.id

    except Exception as e:
        logger.error(f"✗ Event operations test failed: {e}")
        raise


def test_integration_scenarios():
    """Тестирование интеграционных сценариев"""
    logger.info("=== TESTING INTEGRATION SCENARIOS ===")

    try:
        # Сценарий 1: Создание админа и управление системой
        logger.info("Scenario 1: Admin management")
        admin = UserService.create_user(
            email="admin@test.com",
            username="testadmin",
            password="admin123",
            full_name="Test Administrator",
            role=UserRole.ADMIN
        )
        logger.info(f"✓ Created admin: {admin}")

        # Сценарий 2: Массовые операции
        logger.info("Scenario 2: Bulk operations")

        # Создаем несколько пользователей
        bulk_users = []
        for i in range(3):
            user = UserService.create_user(
                email=f"bulk{i}@test.com",
                username=f"bulkuser{i}",
                password="pass123",
                full_name=f"Bulk User {i}"
            )
            UserService.add_balance(user.id, 100.0 * (i + 1), "Initial balance")
            bulk_users.append(user)

        logger.info(f"✓ Created {len(bulk_users)} bulk users")

        # Создаем бесплатное событие
        free_event = EventService.create_event(
            title="Free Event",
            description="A free event for testing",
            creator_id=admin.id,
            cost=0.0,
            max_participants=5
        )
        EventService.activate_event(free_event.id)

        # Все пользователи присоединяются к бесплатному событию
        for user in bulk_users:
            success = EventService.join_event(user.id, free_event.id)
            assert success == True

        updated_free_event = EventService.get_event_by_id(free_event.id)
        logger.info(f"✓ Free event has {updated_free_event.current_participants} participants")

        # Сценарий 3: Проверка ограничений
        logger.info("Scenario 3: Testing limits")

        # Создаем событие с ограничением на 1 участника
        limited_event = EventService.create_event(
            title="Limited Event",
            description="Event with participant limit",
            creator_id=admin.id,
            cost=0.0,
            max_participants=1
        )
        EventService.activate_event(limited_event.id)

        # Первый пользователь присоединяется успешно
        success1 = EventService.join_event(bulk_users[0].id, limited_event.id)
        assert success1 == True

        # Второй пользователь не может присоединиться (лимит достигнут)
        success2 = EventService.join_event(bulk_users[1].id, limited_event.id)
        assert success2 == False

        logger.info("✓ Participant limit correctly enforced")

    except Exception as e:
        logger.error(f"✗ Integration scenarios test failed: {e}")
        raise


def generate_test_report():
    """Генерация отчета о тестировании"""
    logger.info("=== TEST REPORT ===")

    # Статистика пользователей
    all_users = UserService.get_all_users()
    logger.info(f"Total users in system: {len(all_users)}")

    total_balance = sum(user.balance for user in all_users)
    logger.info(f"Total balance in system: {total_balance}")

    admin_count = len([user for user in all_users if user.role == UserRole.ADMIN])
    logger.info(f"Admin users: {admin_count}")

    # Статистика событий
    all_events = EventService.get_all_events()
    active_events = EventService.get_active_events()

    logger.info(f"Total events: {len(all_events)}")
    logger.info(f"Active events: {len(active_events)}")

    total_participants = sum(event.current_participants for event in all_events)
    logger.info(f"Total event participants: {total_participants}")

    # Статистика транзакций (примерная)
    sample_transactions = UserService.get_user_transactions(all_users[0].id) if all_users else []
    logger.info(f"Sample user transactions: {len(sample_transactions)}")


def main():
    """Основная функция тестирования"""
    logger.info("Starting system functionality tests...")

    try:
        # Запускаем тесты
        test_user_id = test_user_operations()
        test_event_id = test_event_operations(test_user_id)
        test_integration_scenarios()

        # Генерируем отчет
        generate_test_report()

        logger.info("✓ All tests passed successfully!")
        return True

    except Exception as e:
        logger.error(f"✗ Tests failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
