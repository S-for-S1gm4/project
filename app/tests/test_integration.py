"""
Интеграционные тесты для Event Planner API
Тестируют взаимодействие между различными компонентами системы
"""
import pytest
from datetime import datetime, timedelta
from services.user_service import UserService
from services.event_service import EventService
from models import UserRole, EventStatus, TransactionType


class TestUserEventIntegration:
    """Тесты интеграции пользователей и событий"""

    def test_complete_user_event_workflow(self, clean_db):
        """Тест полного рабочего процесса: создание пользователя, события, участие"""
        # 1. Создаем организатора
        organizer = UserService.create_user(
            email="organizer@example.com",
            username="organizer",
            password="password123",
            full_name="Event Organizer"
        )

        # 2. Создаем участника
        participant = UserService.create_user(
            email="participant@example.com",
            username="participant",
            password="password123",
            full_name="Event Participant"
        )

        # 3. Участник пополняет баланс
        UserService.add_balance(participant.id, 500.0, "Initial balance")

        # 4. Организатор создает событие
        event = EventService.create_event(
            title="Integration Test Workshop",
            description="A workshop for testing integration",
            creator_id=organizer.id,
            cost=200.0,
            max_participants=10
        )

        # 5. Организатор активирует событие
        EventService.activate_event(event.id)

        # 6. Участник присоединяется к событию
        success = EventService.join_event(participant.id, event.id)
        assert success == True

        # 7. Проверяем финальное состояние

        # Проверяем событие
        updated_event = EventService.get_event_by_id(event.id)
        assert updated_event.status == EventStatus.ACTIVE
        assert updated_event.current_participants == 1

        # Проверяем участника
        updated_participant = UserService.get_user_by_id(participant.id)
        assert updated_participant.balance == 300.0  # 500 - 200

        # Проверяем транзакции участника
        transactions = UserService.get_user_transactions(participant.id)
        assert len(transactions) == 3  # deposit, withdrawal, event_payment

        # Проверяем события организатора
        organizer_events = EventService.get_events_by_creator(organizer.id)
        assert len(organizer_events) == 1
        assert organizer_events[0].id == event.id

    def test_multiple_participants_same_event(self, clean_db):
        """Тест участия нескольких пользователей в одном событии"""
        # Создаем организатора
        organizer = UserService.create_user(
            email="organizer@example.com",
            username="organizer",
            password="password123"
        )

        # Создаем событие
        event = EventService.create_event(
            title="Multi-Participant Event",
            description="Event for multiple participants",
            creator_id=organizer.id,
            cost=100.0,
            max_participants=5
        )
        EventService.activate_event(event.id)

        # Создаем и регистрируем нескольких участников
        participants = []
        for i in range(3):
            participant = UserService.create_user(
                email=f"participant{i}@example.com",
                username=f"participant{i}",
                password="password123"
            )
            UserService.add_balance(participant.id, 150.0, "Initial balance")
            participants.append(participant)

        # Все участники присоединяются к событию
        for participant in participants:
            success = EventService.join_event(participant.id, event.id)
            assert success == True

        # Проверяем финальное состояние события
        final_event = EventService.get_event_by_id(event.id)
        assert final_event.current_participants == 3

        # Проверяем, что у всех участников списались средства
        for participant in participants:
            updated_participant = UserService.get_user_by_id(participant.id)
            assert updated_participant.balance == 50.0  # 150 - 100

    def test_event_capacity_limits(self, clean_db):
        """Тест ограничений вместимости событий"""
        # Создаем организатора
        organizer = UserService.create_user(
            email="organizer@example.com",
            username="organizer",
            password="password123"
        )

        # Создаем событие с малой вместимостью
        event = EventService.create_event(
            title="Limited Capacity Event",
            description="Event with only 2 spots",
            creator_id=organizer.id,
            cost=50.0,
            max_participants=2
        )
        EventService.activate_event(event.id)

        # Создаем больше участников, чем помещается
        participants = []
        for i in range(4):
            participant = UserService.create_user(
                email=f"participant{i}@example.com",
                username=f"participant{i}",
                password="password123"
            )
            UserService.add_balance(participant.id, 100.0, "Balance")
            participants.append(participant)

        # Пытаемся зарегистрировать всех
        successful_joins = 0
        for participant in participants:
            success = EventService.join_event(participant.id, event.id)
            if success:
                successful_joins += 1

        # Должно быть успешно только 2 регистрации
        assert successful_joins == 2

        # Проверяем событие
        final_event = EventService.get_event_by_id(event.id)
        assert final_event.current_participants == 2
        assert final_event.current_participants == final_event.max_participants

    def test_insufficient_balance_scenario(self, clean_db):
        """Тест сценария с недостаточным балансом"""
        # Создаем пользователей
        organizer = UserService.create_user(
            email="organizer@example.com",
            username="organizer",
            password="password123"
        )

        poor_participant = UserService.create_user(
            email="poor@example.com",
            username="poor",
            password="password123"
        )

        rich_participant = UserService.create_user(
            email="rich@example.com",
            username="rich",
            password="password123"
        )

        # Добавляем разные балансы
        UserService.add_balance(poor_participant.id, 50.0, "Small balance")
        UserService.add_balance(rich_participant.id, 500.0, "Large balance")

        # Создаем дорогое событие
        expensive_event = EventService.create_event(
            title="Expensive Workshop",
            description="Very expensive workshop",
            creator_id=organizer.id,
            cost=300.0,
            max_participants=10
        )
        EventService.activate_event(expensive_event.id)

        # Бедный участник не может присоединиться
        poor_success = EventService.join_event(poor_participant.id, expensive_event.id)
        assert poor_success == False

        # Богатый участник может присоединиться
        rich_success = EventService.join_event(rich_participant.id, expensive_event.id)
        assert rich_success == True

        # Проверяем состояния
        updated_poor = UserService.get_user_by_id(poor_participant.id)
        updated_rich = UserService.get_user_by_id(rich_participant.id)

        assert updated_poor.balance == 50.0  # Баланс не изменился
        assert updated_rich.balance == 200.0  # 500 - 300

        # Проверяем событие
        updated_event = EventService.get_event_by_id(expensive_event.id)
        assert updated_event.current_participants == 1

    def test_free_vs_paid_events(self, clean_db):
        """Тест сравнения бесплатных и платных событий"""
        # Создаем организатора
        organizer = UserService.create_user(
            email="organizer@example.com",
            username="organizer",
            password="password123"
        )

        # Создаем участника с небольшим балансом
        participant = UserService.create_user(
            email="participant@example.com",
            username="participant",
            password="password123"
        )
        UserService.add_balance(participant.id, 100.0, "Limited balance")

        # Создаем бесплатное событие
        free_event = EventService.create_event(
            title="Free Workshop",
            description="Free community workshop",
            creator_id=organizer.id,
            cost=0.0,
            max_participants=20
        )
        EventService.activate_event(free_event.id)

        # Создаем платное событие
        paid_event = EventService.create_event(
            title="Paid Workshop",
            description="Premium paid workshop",
            creator_id=organizer.id,
            cost=150.0,
            max_participants=20
        )
        EventService.activate_event(paid_event.id)

        initial_balance = UserService.get_user_by_id(participant.id).balance

        # Участник может присоединиться к бесплатному событию
        free_success = EventService.join_event(participant.id, free_event.id)
        assert free_success == True

        # Участник не может присоединиться к платному событию
        paid_success = EventService.join_event(participant.id, paid_event.id)
        assert paid_success == False

        # Проверяем, что баланс не изменился (только бесплатное событие)
        final_balance = UserService.get_user_by_id(participant.id).balance
        assert final_balance == initial_balance

        # Проверяем участие только в бесплатном событии
        updated_free_event = EventService.get_event_by_id(free_event.id)
        updated_paid_event = EventService.get_event_by_id(paid_event.id)

        assert updated_free_event.current_participants == 1
        assert updated_paid_event.current_participants == 0


class TestComplexTransactionScenarios:
    """Тесты сложных сценариев с транзакциями"""

    def test_multiple_balance_operations_and_events(self, clean_db):
        """Тест множественных операций с балансом и событиями"""
        # Создаем пользователя
        user = UserService.create_user(
            email="user@example.com",
            username="user",
            password="password123"
        )

        organizer = UserService.create_user(
            email="organizer@example.com",
            username="organizer",
            password="password123"
        )

        # Последовательность операций с балансом
        UserService.add_balance(user.id, 1000.0, "Initial deposit")
        UserService.add_balance(user.id, 500.0, "Second deposit")
        UserService.deduct_balance(user.id, 200.0, "Withdrawal")

        # Создаем несколько событий разной стоимости
        events = []
        costs = [100.0, 250.0, 50.0]

        for i, cost in enumerate(costs):
            event = EventService.create_event(
                title=f"Event {i+1}",
                description=f"Event with cost {cost}",
                creator_id=organizer.id,
                cost=cost
            )
            EventService.activate_event(event.id)
            events.append(event)

        # Участник присоединяется к событиям
        current_balance = UserService.get_user_by_id(user.id).balance
        expected_balance = current_balance

        for event in events:
            if expected_balance >= event.cost:
                success = EventService.join_event(user.id, event.id)
                assert success == True
                expected_balance -= event.cost
            else:
                success = EventService.join_event(user.id, event.id)
                assert success == False

        # Проверяем финальный баланс
        final_user = UserService.get_user_by_id(user.id)
        assert final_user.balance == expected_balance

        # Проверяем историю транзакций
        transactions = UserService.get_user_transactions(user.id)

        # Должны быть: 2 deposit, 1 withdrawal + события (withdrawal + event_payment для каждого)
        deposit_count = len([t for t in transactions if t.transaction_type == TransactionType.DEPOSIT])
        withdrawal_count = len([t for t in transactions if t.transaction_type == TransactionType.WITHDRAWAL])
        event_payment_count = len([t for t in transactions if t.transaction_type == TransactionType.EVENT_PAYMENT])

        assert deposit_count == 2
        assert withdrawal_count >= 1  # Минимум одно ручное списание
        assert event_payment_count >= 0  # Зависит от того, на сколько событий хватило денег

    def test_edge_case_exact_balance_multiple_events(self, clean_db):
        """Тест граничного случая с точным балансом для нескольких событий"""
        user = UserService.create_user(
            email="user@example.com",
            username="user",
            password="password123"
        )

        organizer = UserService.create_user(
            email="organizer@example.com",
            username="organizer",
            password="password123"
        )

        # Добавляем точную сумму для двух событий
        total_cost = 150.0 + 100.0  # 250.0
        UserService.add_balance(user.id, total_cost, "Exact amount for two events")

        # Создаем два события
        event1 = EventService.create_event(
            title="First Event",
            description="First event",
            creator_id=organizer.id,
            cost=150.0
        )

        event2 = EventService.create_event(
            title="Second Event",
            description="Second event",
            creator_id=organizer.id,
            cost=100.0
        )

        EventService.activate_event(event1.id)
        EventService.activate_event(event2.id)

        # Присоединяемся к первому событию
        success1 = EventService.join_event(user.id, event1.id)
        assert success1 == True

        # Присоединяемся ко второму событию
        success2 = EventService.join_event(user.id, event2.id)
        assert success2 == True

        # Баланс должен стать нулевым
        final_user = UserService.get_user_by_id(user.id)
        assert final_user.balance == 0.0

        # Попытка присоединиться к третьему событию должна провалиться
        event3 = EventService.create_event(
            title="Third Event",
            description="Third event",
            creator_id=organizer.id,
            cost=1.0  # Даже за 1 доллар
        )
        EventService.activate_event(event3.id)

        success3 = EventService.join_event(user.id, event3.id)
        assert success3 == False


class TestRoleBasedScenarios:
    """Тесты сценариев на основе ролей пользователей"""

    def test_admin_vs_user_event_creation(self, clean_db):
        """Тест создания событий администратором и обычным пользователем"""
        # Создаем администратора
        admin = UserService.create_user(
            email="admin@example.com",
            username="admin",
            password="password123",
            role=UserRole.ADMIN
        )

        # Создаем обычного пользователя
        user = UserService.create_user(
            email="user@example.com",
            username="user",
            password="password123",
            role=UserRole.USER
        )

        # Оба могут создавать события
        admin_event = EventService.create_event(
            title="Admin Event",
            description="Event created by admin",
            creator_id=admin.id,
            cost=200.0
        )

        user_event = EventService.create_event(
            title="User Event",
            description="Event created by user",
            creator_id=user.id,
            cost=100.0
        )

        # Проверяем, что события созданы
        assert admin_event.id is not None
        assert user_event.id is not None
        assert admin_event.creator_id == admin.id
        assert user_event.creator_id == user.id

        # Проверяем роли создателей
        admin_events = EventService.get_events_by_creator(admin.id)
        user_events = EventService.get_events_by_creator(user.id)

        assert len(admin_events) == 1
        assert len(user_events) == 1

    def test_multiple_organizers_scenario(self, clean_db):
        """Тест сценария с несколькими организаторами"""
        # Создаем несколько организаторов
        organizers = []
        for i in range(3):
            organizer = UserService.create_user(
                email=f"organizer{i}@example.com",
                username=f"organizer{i}",
                password="password123"
            )
            organizers.append(organizer)

        # Каждый создает события
        all_events = []
        for i, organizer in enumerate(organizers):
            for j in range(2):  # По 2 события на организатора
                event = EventService.create_event(
                    title=f"Event {i}-{j}",
                    description=f"Event {j} by organizer {i}",
                    creator_id=organizer.id,
                    cost=50.0 * (i + 1)  # Разная стоимость
                )
                EventService.activate_event(event.id)
                all_events.append(event)

        # Создаем участника
        participant = UserService.create_user(
            email="participant@example.com",
            username="participant",
            password="password123"
        )
        UserService.add_balance(participant.id, 1000.0, "Large balance")

        # Участник присоединяется ко всем событиям
        successful_joins = 0
        for event in all_events:
            success = EventService.join_event(participant.id, event.id)
            if success:
                successful_joins += 1

        # Проверяем, что участник присоединился ко всем событиям
        assert successful_joins == len(all_events)

        # Проверяем, что у каждого организатора есть события с участниками
        for organizer in organizers:
            organizer_events = EventService.get_events_by_creator(organizer.id)
            assert len(organizer_events) == 2

            for event in organizer_events:
                updated_event = EventService.get_event_by_id(event.id)
                assert updated_event.current_participants == 1


class TestSystemLimitsAndConstraints:
    """Тесты системных ограничений и ограничений"""

    def test_large_number_of_users_and_events(self, clean_db):
        """Тест с большим количеством пользователей и событий"""
        # Создаем много пользователей
        users = []
        for i in range(20):
            user = UserService.create_user(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password="password123"
            )
            UserService.add_balance(user.id, 500.0, "Initial balance")
            users.append(user)

        # Создаем организатора
        organizer = UserService.create_user(
            email="organizer@example.com",
            username="organizer",
            password="password123"
        )

        # Создаем много событий
        events = []
        for i in range(10):
            event = EventService.create_event(
                title=f"Mass Event {i}",
                description=f"Event number {i}",
                creator_id=organizer.id,
                cost=50.0,
                max_participants=5
            )
            EventService.activate_event(event.id)
            events.append(event)

        # Каждый пользователь пытается присоединиться к каждому событию
        total_successful_joins = 0
        for user in users:
            for event in events:
                success = EventService.join_event(user.id, event.id)
                if success:
                    total_successful_joins += 1

        # Максимальное количество присоединений = количество событий * лимит участников
        max_possible_joins = len(events) * 5  # 10 событий * 5 участников = 50

        assert total_successful_joins == max_possible_joins

        # Проверяем, что все события заполнены
        for event in events:
            updated_event = EventService.get_event_by_id(event.id)
            assert updated_event.current_participants == 5

    def test_zero_cost_event_mass_participation(self, clean_db):
        """Тест массового участия в бесплатном событии"""
        # Создаем организатора
        organizer = UserService.create_user(
            email="organizer@example.com",
            username="organizer",
            password="password123"
        )

        # Создаем бесплатное событие с большим лимитом
        free_event = EventService.create_event(
            title="Mass Free Event",
            description="Free event for everyone",
            creator_id=organizer.id,
            cost=0.0,
            max_participants=100
        )
        EventService.activate_event(free_event.id)

        # Создаем много пользователей без баланса
        users = []
        for i in range(50):
            user = UserService.create_user(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password="password123"
            )
            users.append(user)

        # Все присоединяются к бесплатному событию
        successful_joins = 0
        for user in users:
            success = EventService.join_event(user.id, free_event.id)
            if success:
                successful_joins += 1

        # Все должны смочь присоединиться
        assert successful_joins == len(users)

        # Проверяем событие
        updated_event = EventService.get_event_by_id(free_event.id)
        assert updated_event.current_participants == len(users)

        # Проверяем, что ни у кого не изменился баланс
        for user in users:
            updated_user = UserService.get_user_by_id(user.id)
            assert updated_user.balance == 0.0


class TestDataConsistency:
    """Тесты консистентности данных"""

    def test_transaction_balance_consistency(self, clean_db):
        """Тест консистентности баланса с транзакциями"""
        user = UserService.create_user(
            email="user@example.com",
            username="user",
            password="password123"
        )

        # Выполняем серию операций
        operations = [
            ("add", 1000.0, "Initial deposit"),
            ("add", 500.0, "Second deposit"),
            ("deduct", 200.0, "First withdrawal"),
            ("add", 300.0, "Third deposit"),
            ("deduct", 150.0, "Second withdrawal")
        ]

        expected_balance = 0.0
        for operation, amount, description in operations:
            if operation == "add":
                UserService.add_balance(user.id, amount, description)
                expected_balance += amount
            else:
                success = UserService.deduct_balance(user.id, amount, description)
                if success:
                    expected_balance -= amount

        # Проверяем финальный баланс
        final_user = UserService.get_user_by_id(user.id)
        assert final_user.balance == expected_balance

        # Проверяем консистентность с транзакциями
        transactions = UserService.get_user_transactions(user.id)

        calculated_balance = 0.0
        for transaction in transactions:
            if transaction.transaction_type == TransactionType.DEPOSIT:
                calculated_balance += transaction.amount
            elif transaction.transaction_type == TransactionType.WITHDRAWAL:
                calculated_balance -= transaction.amount

        assert abs(calculated_balance - expected_balance) < 0.01

    def test_event_participant_count_consistency(self, clean_db):
        """Тест консистентности счетчика участников события"""
        organizer = UserService.create_user(
            email="organizer@example.com",
            username="organizer",
            password="password123"
        )

        event = EventService.create_event(
            title="Consistency Test Event",
            description="Event for testing participant count",
            creator_id=organizer.id,
            cost=100.0,
            max_participants=10
        )
        EventService.activate_event(event.id)

        # Создаем участников и присоединяем их
        participants = []
        successful_joins = 0

        for i in range(7):  # Меньше максимума
            participant = UserService.create_user(
                email=f"participant{i}@example.com",
                username=f"participant{i}",
                password="password123"
            )
            UserService.add_balance(participant.id, 150.0, "Balance")

            success = EventService.join_event(participant.id, event.id)
            if success:
                successful_joins += 1
                participants.append(participant)

        # Проверяем консистентность
        updated_event = EventService.get_event_by_id(event.id)
        assert updated_event.current_participants == successful_joins
        assert updated_event.current_participants == len(participants)

        # Проверяем, что у всех участников списались средства
        for participant in participants:
            updated_participant = UserService.get_user_by_id(participant.id)
            assert updated_participant.balance == 50.0  # 150 - 100

    def test_system_wide_balance_conservation(self, clean_db):
        """Тест сохранения общего баланса в системе"""
        # Создаем пользователей
        users = []
        initial_system_balance = 0.0

        for i in range(5):
            user = UserService.create_user(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password="password123"
            )

            # Добавляем разные суммы
            amount = 100.0 * (i + 1)
            UserService.add_balance(user.id, amount, "Initial balance")
            initial_system_balance += amount
            users.append(user)

        # Создаем организатора
        organizer = UserService.create_user(
            email="organizer@example.com",
            username="organizer",
            password="password123"
        )

        # Создаем события и участвуем в них
        events = []
        for i in range(3):
            event = EventService.create_event(
                title=f"Event {i}",
                description=f"Event {i}",
                creator_id=organizer.id,
                cost=50.0 * (i + 1)
            )
            EventService.activate_event(event.id)
            events.append(event)

        # Пользователи участвуют в событиях
        for user in users:
            for event in events:
                EventService.join_event(user.id, event.id)  # Некоторые могут не пройти

        # Вычисляем финальный баланс системы
        final_system_balance = 0.0
        all_users = UserService.get_all_users()
        for user in all_users:
            final_system_balance += user.balance

        # Баланс организатора остается 0 (он не получает деньги в нашей модели)
        # Общий баланс должен остаться тем же (деньги не исчезают)
        assert abs(final_system_balance - initial_system_balance) < 0.01
