import pytest
from services.user_service import UserService
from services.event_service import EventService

class TestEventCreation:
    """Тесты создания событий"""

    def test_create_event_with_defaults(self, created_user):
        """Тест создания события со значениями по умолчанию"""
        event = EventService.create_event(
            title="Default Event",
            description="Test with defaults",
            creator_id=created_user.id,
            max_participants=100
        )
        assert event.cost == 0.0
        assert event.max_participants == 100

    def test_create_event_with_invalid_creator(self, clean_db):
        """Тест создания события с несуществующим создателем"""
        with pytest.raises(ValueError) as exc_info:
            EventService.create_event(
                title="Test Event",
                description="Test",
                creator_id=99999,  # Несуществующий ID
                cost=50.0
            )

        assert "not found" in str(exc_info.value).lower()

    def test_create_event_with_future_date(self, created_user):
        """Тест создания события с будущей датой"""
        from datetime import datetime, timedelta

        future_date = datetime.utcnow() + timedelta(days=30)

        event = EventService.create_event(
            title="Future Event",
            description="Event in the future",
            creator_id=created_user.id,
            cost=75.0,
            event_date=future_date
        )

        assert event.event_date == future_date

    def test_create_multiple_events_same_creator(self, created_user):
        """Тест создания нескольких событий одним создателем"""
        events = []
        for i in range(3):
            event = EventService.create_event(
                title=f"Event {i+1}",
                description=f"Description for event {i+1}",
                creator_id=created_user.id,
                cost=50.0 * (i+1)
            )
            events.append(event)

        assert len(events) == 3
        assert all(e.creator_id == created_user.id for e in events)
        assert all(e.id is not None for e in events)


class TestEventRetrieval:
    """Тесты получения событий"""

    def test_get_event_by_id_exists(self, created_event):
        """Тест получения существующего события по ID"""
        retrieved_event = EventService.get_event_by_id(created_event.id)

        assert retrieved_event is not None
        assert retrieved_event.id == created_event.id
        assert retrieved_event.title == created_event.title
        assert retrieved_event.creator_id == created_event.creator_id

    def test_get_event_by_id_not_exists(self, clean_db):
        """Тест получения несуществующего события по ID"""
        retrieved_event = EventService.get_event_by_id(99999)

        assert retrieved_event is None

    def test_get_all_events(self, multiple_events):
        """Тест получения всех событий"""
        all_events = EventService.get_all_events()

        assert len(all_events) >= 3  # Минимум созданные события
        assert all(event.id is not None for event in all_events)

    def test_get_all_events_empty_db(self, clean_db):
        """Тест получения событий из пустой БД"""
        all_events = EventService.get_all_events()

        assert all_events == []

    def test_get_active_events(self, multiple_events):
        """Тест получения активных событий"""
        active_events = EventService.get_active_events()

        assert len(active_events) >= 3  # Все события в фикстуре активированы
        assert all(event.status == "active" for event in active_events)

    def test_get_events_by_creator(self, multiple_events, created_user):
        """Тест получения событий по создателю"""
        creator_events = EventService.get_events_by_creator(created_user.id)

        assert len(creator_events) >= 3
        assert all(event.creator_id == created_user.id for event in creator_events)

    def test_get_events_by_nonexistent_creator(self, clean_db):
        """Тест получения событий несуществующего создателя"""
        creator_events = EventService.get_events_by_creator(99999)

        assert creator_events == []


class TestEventActivation:
    """Тесты активации событий"""

    def test_activate_event_success(self, created_event):
        """Тест успешной активации события"""
        success = EventService.activate_event(created_event.id)

        assert success == True

        # Проверяем, что статус изменился
        updated_event = EventService.get_event_by_id(created_event.id)
        assert updated_event.status == "active"
        assert updated_event.updated_at is not None

    def test_activate_nonexistent_event(self, clean_db):
        """Тест активации несуществующего события"""
        with pytest.raises(ValueError) as exc_info:
            EventService.activate_event(99999)

        assert "not found" in str(exc_info.value).lower()

    def test_activate_already_active_event(self, active_event):
        """Тест активации уже активного события"""
        # Повторная активация должна быть успешной
        success = EventService.activate_event(active_event.id)

        assert success == True

        # Событие должно остаться активным
        updated_event = EventService.get_event_by_id(active_event.id)
        assert updated_event.status == "active"


class TestEventParticipation:
    """Тесты участия в событиях"""

    def test_join_free_event_success(self, multiple_users, multiple_events):
        """Тест успешного присоединения к бесплатному событию"""
        user = multiple_users[0]
        free_event = next(e for e in multiple_events if e.cost == 0.0)

        initial_balance = user.balance
        initial_participants = free_event.current_participants

        success = EventService.join_event(user.id, free_event.id)

        assert success == True

        # Проверяем событие
        updated_event = EventService.get_event_by_id(free_event.id)
        assert updated_event.current_participants == initial_participants + 1

        # Проверяем, что баланс не изменился (бесплатное событие)
        updated_user = UserService.get_user_by_id(user.id)
        assert updated_user.balance == initial_balance

    def test_join_paid_event_success(self, multiple_users, multiple_events):
        """Тест успешного присоединения к платному событию"""
        user = multiple_users[0]  # У него есть баланс 100
        paid_event = next(e for e in multiple_events if e.cost > 0 and e.cost <= 100)

        initial_balance = user.balance
        initial_participants = paid_event.current_participants

        success = EventService.join_event(user.id, paid_event.id)

        assert success == True

        # Проверяем событие
        updated_event = EventService.get_event_by_id(paid_event.id)
        assert updated_event.current_participants == initial_participants + 1

        # Проверяем списание средств
        updated_user = UserService.get_user_by_id(user.id)
        assert updated_user.balance == initial_balance - paid_event.cost

        # Проверяем создание транзакций
        transactions = UserService.get_user_transactions(user.id)
        event_payments = [t for t in transactions if t.transaction_type == "event_payment"]
        assert len(event_payments) >= 1

    def test_join_event_insufficient_balance(self, multiple_users, multiple_events):
        """Тест присоединения к событию при недостаточном балансе"""
        user = multiple_users[0]  # У него баланс 100
        expensive_event = next(e for e in multiple_events if e.cost > 200)

        success = EventService.join_event(user.id, expensive_event.id)

        assert success == False

        # Проверяем, что ничего не изменилось
        updated_event = EventService.get_event_by_id(expensive_event.id)
        updated_user = UserService.get_user_by_id(user.id)

        assert updated_event.current_participants == expensive_event.current_participants
        assert updated_user.balance == user.balance

    def test_join_event_at_capacity(self, limited_event, multiple_users):
        """Тест присоединения к событию на пределе вместимости"""
        # Заполняем событие до предела
        successful_joins = 0

        for user in multiple_users:
            if successful_joins >= limited_event.max_participants:
                break

            success = EventService.join_event(user.id, limited_event.id)
            if success:
                successful_joins += 1

        # Проверяем, что присоединилось ровно max_participants
        final_event = EventService.get_event_by_id(limited_event.id)
        assert final_event.current_participants == limited_event.max_participants

        # Попытка добавить еще одного участника должна провалиться
        if len(multiple_users) > limited_event.max_participants:
            extra_user = multiple_users[limited_event.max_participants]
            success = EventService.join_event(extra_user.id, limited_event.id)
            assert success == False

    def test_join_nonexistent_event(self, multiple_users):
        """Тест присоединения к несуществующему событию"""
        user = multiple_users[0]

        with pytest.raises(ValueError) as exc_info:
            EventService.join_event(user.id, 99999)

        assert "not found" in str(exc_info.value).lower()

    def test_join_event_nonexistent_user(self, multiple_events):
        """Тест присоединения несуществующего пользователя к событию"""
        event = multiple_events[0]

        with pytest.raises(ValueError) as exc_info:
            EventService.join_event(99999, event.id)

        assert "not found" in str(exc_info.value).lower()

    def test_join_inactive_event(self, created_event, multiple_users):
        """Тест присоединения к неактивному событию"""
        user = multiple_users[0]

        # Событие в статусе DRAFT (не активировано)
        success = EventService.join_event(user.id, created_event.id)

        assert success == False

        # Проверяем, что участники не добавились
        updated_event = EventService.get_event_by_id(created_event.id)
        assert updated_event.current_participants == 0


class TestEventServiceEdgeCases:
    """Тесты граничных случаев EventService"""

    def test_multiple_joins_same_user_same_event(self, user_with_balance, active_event):
        """Тест множественного присоединения одного пользователя к одному событию"""
        # Первое присоединение должно быть успешным
        success1 = EventService.join_event(user_with_balance.id, active_event.id)
        assert success1 == True

        initial_participants = EventService.get_event_by_id(active_event.id).current_participants
        initial_balance = UserService.get_user_by_id(user_with_balance.id).balance

        # Второе присоединение к тому же событию
        # (в реальной системе нужна проверка на дубликаты, но пока система это позволяет)
        success2 = EventService.join_event(user_with_balance.id, active_event.id)

        # Проверяем результат (зависит от бизнес-логики)
        final_event = EventService.get_event_by_id(active_event.id)
        final_user = UserService.get_user_by_id(user_with_balance.id)

        # Если система позволяет дубликаты
        if success2:
            assert final_event.current_participants == initial_participants + 1
            assert final_user.balance == initial_balance - active_event.cost
        else:
            # Если система предотвращает дубликаты
            assert final_event.current_participants == initial_participants
            assert final_user.balance == initial_balance

    def test_join_event_exact_balance(self, created_user, clean_db):
        """Тест присоединения к событию с точным балансом"""
        # Создаем событие стоимостью 100
        event = EventService.create_event(
            title="Exact Balance Event",
            description="Event for exact balance test",
            creator_id=created_user.id,
            cost=100.0
        )
        EventService.activate_event(event.id)

        # Создаем пользователя с точным балансом
        participant = UserService.create_user(
            email="exact@example.com",
            username="exactuser",
            password="password123"
        )
        UserService.add_balance(participant.id, 100.0, "Exact balance")

        # Присоединяемся к событию
        success = EventService.join_event(participant.id, event.id)
        assert success == True

        # Проверяем, что баланс стал нулевым
        updated_user = UserService.get_user_by_id(participant.id)
        assert updated_user.balance == 0.0

    def test_concurrent_joins_limited_event(self, limited_event, clean_db):
        """Тест одновременного присоединения к событию с ограниченной вместимостью"""
        # Создаем больше пользователей, чем мест
        users = []
        for i in range(limited_event.max_participants + 2):
            user = UserService.create_user(
                email=f"concurrent{i}@example.com",
                username=f"concurrent{i}",
                password="password123"
            )
            UserService.add_balance(user.id, 100.0, "Test balance")
            users.append(user)

        # Все пытаются присоединиться
        successful_joins = 0
        for user in users:
            success = EventService.join_event(user.id, limited_event.id)
            if success:
                successful_joins += 1

        # Должно присоединиться не больше максимума
        final_event = EventService.get_event_by_id(limited_event.id)
        assert final_event.current_participants <= limited_event.max_participants
        assert successful_joins <= limited_event.max_participants

    def test_zero_cost_event_operations(self, created_user, multiple_users):
        """Тест операций с бесплатными событиями"""
        # Создаем бесплатное событие
        free_event = EventService.create_event(
            title="Free Community Event",
            description="Completely free event",
            creator_id=created_user.id,
            cost=0.0,
            max_participants=100
        )
        EventService.activate_event(free_event.id)

        # Все пользователи присоединяются (даже без баланса)
        for user in multiple_users:
            initial_balance = user.balance
            success = EventService.join_event(user.id, free_event.id)

            assert success == True

            # Баланс не должен измениться
            updated_user = UserService.get_user_by_id(user.id)
            assert updated_user.balance == initial_balance

        # Проверяем финальное количество участников
        final_event = EventService.get_event_by_id(free_event.id)
        assert final_event.current_participants == len(multiple_users)

    def test_large_participant_numbers(self, created_user, clean_db):
        """Тест с большим количеством участников"""
        # Создаем событие с большой вместимостью
        large_event = EventService.create_event(
            title="Large Scale Event",
            description="Event for many participants",
            creator_id=created_user.id,
            cost=10.0,
            max_participants=1000
        )
        EventService.activate_event(large_event.id)

        # Создаем много пользователей и добавляем их
        num_participants = 100  # Меньшее число для тестов
        for i in range(num_participants):
            user = UserService.create_user(
                email=f"large{i}@example.com",
                username=f"large{i}",
                password="password123"
            )
            UserService.add_balance(user.id, 20.0, "Test balance")

            success = EventService.join_event(user.id, large_event.id)
            assert success == True

        # Проверяем финальное состояние
        final_event = EventService.get_event_by_id(large_event.id)
        assert final_event.current_participants == num_participants


class TestEventServicePerformance:
    """Тесты производительности EventService"""

    def test_bulk_event_creation(self, created_user):
        """Тест массового создания событий"""
        import time

        start_time = time.time()

        # Создаем много событий
        events = []
        for i in range(50):
            event = EventService.create_event(
                title=f"Bulk Event {i}",
                description=f"Description for bulk event {i}",
                creator_id=created_user.id,
                cost=10.0 + i
            )
            events.append(event)

        end_time = time.time()
        creation_time = end_time - start_time

        # Проверяем, что все события созданы
        assert len(events) == 50
        assert all(e.id is not None for e in events)

        # Производительность: не больше 5 секунд на 50 событий
        assert creation_time < 5.0

        print(f"Created 50 events in {creation_time:.2f} seconds")

    def test_bulk_event_retrieval(self, multiple_events):
        """Тест производительности получения событий"""
        import time

        start_time = time.time()

        # Многократные запросы
        for _ in range(100):
            all_events = EventService.get_all_events()
            active_events = EventService.get_active_events()

        end_time = time.time()
        retrieval_time = end_time - start_time

        # Производительность: не больше 2 секунд на 100 запросов
        assert retrieval_time < 2.0

        print(f"100 retrieval operations in {retrieval_time:.2f} seconds")


class TestEventServiceIntegration:
    """Интеграционные тесты EventService"""

    def test_full_event_lifecycle(self, created_user, clean_db):
        """Тест полного жизненного цикла события"""
        # 1. Создание события
        event = EventService.create_event(
            title="Lifecycle Test Event",
            description="Testing full lifecycle",
            creator_id=created_user.id,
            cost=50.0,
            max_participants=5
        )

        assert event.status == "draft"
        assert event.current_participants == 0

        # 2. Активация события
        EventService.activate_event(event.id)

        activated_event = EventService.get_event_by_id(event.id)
        assert activated_event.status == "active"

        # 3. Создание участников и присоединение
        participants = []
        for i in range(3):
            participant = UserService.create_user(
                email=f"lifecycle{i}@example.com",
                username=f"lifecycle{i}",
                password="password123"
            )
            UserService.add_balance(participant.id, 100.0, "Test balance")
            participants.append(participant)

        # 4. Участники присоединяются
        for participant in participants:
            success = EventService.join_event(participant.id, event.id)
            assert success == True

        # 5. Проверка финального состояния
        final_event = EventService.get_event_by_id(event.id)
        assert final_event.current_participants == len(participants)
        assert final_event.status == "active"

        # 6. Проверка транзакций участников
        for participant in participants:
            updated_participant = UserService.get_user_by_id(participant.id)
            assert updated_participant.balance == 50.0  # 100 - 50

            transactions = UserService.get_user_transactions(participant.id)
            event_payments = [t for t in transactions if t.transaction_type == "event_payment"]
            assert len(event_payments) == 1

    def test_multi_creator_events(self, clean_db):
        """Тест событий от разных создателей"""
        # Создаем нескольких создателей
        creators = []
        for i in range(3):
            creator = UserService.create_user(
                email=f"creator{i}@example.com",
                username=f"creator{i}",
                password="password123"
            )
            creators.append(creator)

        # Каждый создает события
        all_created_events = []
        for i, creator in enumerate(creators):
            for j in range(2):
                event = EventService.create_event(
                    title=f"Creator {i} Event {j}",
                    description=f"Event by creator {i}",
                    creator_id=creator.id,
                    cost=25.0 * (i + 1)
                )
                EventService.activate_event(event.id)
                all_created_events.append(event)

        # Проверяем получение по создателям
        for i, creator in enumerate(creators):
            creator_events = EventService.get_events_by_creator(creator.id)
            assert len(creator_events) == 2
            assert all(e.creator_id == creator.id for e in creator_events)

        # Проверяем общее количество
        all_events = EventService.get_all_events()
        assert len(all_events) >= len(all_created_events)

    def test_events_with_different_costs(self, created_user, clean_db):
        """Тест событий с разной стоимостью"""
        costs = [0.0, 25.50, 100.0, 999.99]
        events = []

        # Создаем события с разной стоимостью
        for i, cost in enumerate(costs):
            event = EventService.create_event(
                title=f"Cost Test Event {cost}",
                description=f"Event with cost {cost}",
                creator_id=created_user.id,
                cost=cost
            )
            EventService.activate_event(event.id)
            events.append(event)

        # Создаем участника с ограниченным балансом
        participant = UserService.create_user(
            email="costtest@example.com",
            username="costtest",
            password="password123"
        )
        UserService.add_balance(participant.id, 200.0, "Limited balance")

        # Пытаемся присоединиться ко всем событиям
        successful_joins = 0
        total_spent = 0.0

        for event in events:
            current_balance = UserService.get_user_by_id(participant.id).balance

            if current_balance >= event.cost:
                success = EventService.join_event(participant.id, event.id)
                if success:
                    successful_joins += 1
                    total_spent += event.cost

        # Проверяем логику присоединения
        final_participant = UserService.get_user_by_id(participant.id)
        expected_balance = 200.0 - total_spent

        assert abs(final_participant.balance - expected_balance) < 0.01
        assert successful_joins <= len(events)

        # Должен присоединиться к бесплатному и недорогим событиям
        assert successful_joins >= 2  # Минимум к бесплатному и 25.50
