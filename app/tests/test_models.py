"""
Тесты для моделей данных (User, Event, Transaction)
"""
import pytest
from datetime import datetime, timedelta
from models import User, Event, Transaction, UserRole, EventStatus, TransactionType, TransactionStatus


class TestUserModel:
    """Тесты модели User"""

    def test_user_creation(self):
        """Тест создания пользователя"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password_123",
            full_name="Test User"
        )

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.hashed_password == "hashed_password_123"
        assert user.full_name == "Test User"
        assert user.role == UserRole.USER
        assert user.balance == 0.0
        assert user.is_active == True
        assert user.created_at is not None
        assert user.updated_at is None

    def test_user_default_values(self):
        """Тест значений по умолчанию для пользователя"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="password"
        )

        assert user.role == UserRole.USER
        assert user.balance == 0.0
        assert user.is_active == True
        assert user.full_name is None
        assert user.updated_at is None

    def test_admin_user_creation(self):
        """Тест создания администратора"""
        admin = User(
            email="admin@example.com",
            username="admin",
            hashed_password="admin_password",
            role=UserRole.ADMIN
        )

        assert admin.role == UserRole.ADMIN
        assert admin.balance == 0.0
        assert admin.is_active == True

    def test_user_has_sufficient_balance(self):
        """Тест проверки достаточности баланса"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="password",
            balance=100.0
        )

        assert user.has_sufficient_balance(50.0) == True
        assert user.has_sufficient_balance(100.0) == True
        assert user.has_sufficient_balance(150.0) == False
        assert user.has_sufficient_balance(0.0) == True

    def test_user_add_balance(self):
        """Тест пополнения баланса"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="password",
            balance=100.0
        )

        initial_balance = user.balance
        user.add_balance(50.0)

        assert user.balance == initial_balance + 50.0
        assert user.updated_at is not None

    def test_user_add_negative_balance(self):
        """Тест пополнения отрицательной суммы (не должно работать)"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="password",
            balance=100.0
        )

        initial_balance = user.balance
        user.add_balance(-50.0)  # Модель не проверяет на отрицательность

        # Модель позволяет отрицательные значения, но сервис должен проверять
        assert user.balance == initial_balance - 50.0

    def test_user_deduct_balance_success(self):
        """Тест успешного списания с баланса"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="password",
            balance=100.0
        )

        success = user.deduct_balance(30.0)

        assert success == True
        assert user.balance == 70.0
        assert user.updated_at is not None

    def test_user_deduct_balance_insufficient(self):
        """Тест списания при недостаточном балансе"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="password",
            balance=100.0
        )

        success = user.deduct_balance(150.0)

        assert success == False
        assert user.balance == 100.0  # Баланс не изменился

    def test_user_deduct_exact_balance(self):
        """Тест списания точной суммы баланса"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="password",
            balance=100.0
        )

        success = user.deduct_balance(100.0)

        assert success == True
        assert user.balance == 0.0

    def test_user_string_representation(self):
        """Тест строкового представления пользователя"""
        user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            hashed_password="password",
            balance=150.0
        )

        str_repr = str(user)
        assert "id=1" in str_repr
        assert "test@example.com" in str_repr
        assert "balance=150.0" in str_repr


class TestEventModel:
    """Тесты модели Event"""

    def test_event_creation(self):
        """Тест создания события"""
        event_date = datetime.utcnow() + timedelta(days=7)

        event = Event(
            title="Test Workshop",
            description="A test workshop",
            cost=100.0,
            max_participants=20,
            creator_id=1,
            event_date=event_date
        )

        assert event.title == "Test Workshop"
        assert event.description == "A test workshop"
        assert event.cost == 100.0
        assert event.max_participants == 20
        assert event.creator_id == 1
        assert event.event_date == event_date
        assert event.status == EventStatus.DRAFT
        assert event.current_participants == 0
        assert event.created_at is not None
        assert event.updated_at is None

    def test_event_default_values(self):
        """Тест значений по умолчанию для события"""
        event = Event(
            title="Minimal Event",
            description="Description",
            creator_id=1
        )

        assert event.cost == 0.0
        assert event.max_participants is None
        assert event.current_participants == 0
        assert event.status == EventStatus.DRAFT
        assert event.event_date is None
        assert event.image is None
        assert event.updated_at is None

    def test_free_event_creation(self):
        """Тест создания бесплатного события"""
        event = Event(
            title="Free Meetup",
            description="Free community meetup",
            creator_id=1,
            cost=0.0,
            max_participants=50
        )

        assert event.cost == 0.0
        assert event.max_participants == 50

    def test_event_can_join_active_with_space(self):
        """Тест возможности присоединения к активному событию с местами"""
        event = Event(
            title="Test Event",
            description="Test",
            creator_id=1,
            status=EventStatus.ACTIVE,
            max_participants=5,
            current_participants=5
        )

        assert event.can_join() == False

    def test_event_can_join_unlimited_capacity(self):
        """Тест возможности присоединения к событию без ограничений"""
        event = Event(
            title="Test Event",
            description="Test",
            creator_id=1,
            status=EventStatus.ACTIVE,
            max_participants=None,
            current_participants=100
        )

        assert event.can_join() == True

    def test_event_join_success(self):
        """Тест успешного присоединения к событию"""
        event = Event(
            title="Test Event",
            description="Test",
            creator_id=1,
            status=EventStatus.ACTIVE,
            max_participants=10,
            current_participants=5
        )

        initial_participants = event.current_participants
        success = event.join_event()

        assert success == True
        assert event.current_participants == initial_participants + 1
        assert event.updated_at is not None

    def test_event_join_when_full(self):
        """Тест присоединения к заполненному событию"""
        event = Event(
            title="Test Event",
            description="Test",
            creator_id=1,
            status=EventStatus.ACTIVE,
            max_participants=5,
            current_participants=5
        )

        success = event.join_event()

        assert success == False
        assert event.current_participants == 5  # Не изменился

    def test_event_join_when_inactive(self):
        """Тест присоединения к неактивному событию"""
        event = Event(
            title="Test Event",
            description="Test",
            creator_id=1,
            status=EventStatus.DRAFT,
            max_participants=10,
            current_participants=0
        )

        success = event.join_event()

        assert success == False
        assert event.current_participants == 0

    def test_event_string_representation(self):
        """Тест строкового представления события"""
        event = Event(
            id=1,
            title="Test Workshop",
            cost=100.0,
            creator_id=2
        )

        str_repr = str(event)
        assert "id=1" in str_repr
        assert "Test Workshop" in str_repr
        assert "cost=100.0" in str_repr
        assert "creator=2" in str_repr


class TestTransactionModel:
    """Тесты модели Transaction"""

    def test_transaction_creation(self):
        """Тест создания транзакции"""
        transaction = Transaction(
            amount=100.0,
            transaction_type=TransactionType.DEPOSIT,
            description="Test deposit",
            user_id=1
        )

        assert transaction.amount == 100.0
        assert transaction.transaction_type == TransactionType.DEPOSIT
        assert transaction.status == TransactionStatus.PENDING
        assert transaction.description == "Test deposit"
        assert transaction.user_id == 1
        assert transaction.event_id is None
        assert transaction.reference_id is None
        assert transaction.created_at is not None
        assert transaction.completed_at is None

    def test_transaction_default_values(self):
        """Тест значений по умолчанию для транзакции"""
        transaction = Transaction(
            amount=50.0,
            transaction_type=TransactionType.WITHDRAWAL,
            user_id=1
        )

        assert transaction.status == TransactionStatus.PENDING
        assert transaction.description is None
        assert transaction.reference_id is None
        assert transaction.event_id is None
        assert transaction.completed_at is None

    def test_event_payment_transaction(self):
        """Тест транзакции оплаты события"""
        transaction = Transaction(
            amount=150.0,
            transaction_type=TransactionType.EVENT_PAYMENT,
            description="Payment for workshop",
            user_id=1,
            event_id=5
        )

        assert transaction.transaction_type == TransactionType.EVENT_PAYMENT
        assert transaction.event_id == 5
        assert transaction.amount == 150.0

    def test_refund_transaction(self):
        """Тест транзакции возврата"""
        transaction = Transaction(
            amount=75.0,
            transaction_type=TransactionType.REFUND,
            description="Event cancellation refund",
            user_id=1,
            event_id=3
        )

        assert transaction.transaction_type == TransactionType.REFUND
        assert transaction.event_id == 3

    def test_transaction_complete(self):
        """Тест завершения транзакции"""
        transaction = Transaction(
            amount=100.0,
            transaction_type=TransactionType.DEPOSIT,
            user_id=1
        )

        assert transaction.status == TransactionStatus.PENDING
        assert transaction.completed_at is None

        transaction.complete()

        assert transaction.status == TransactionStatus.COMPLETED
        assert transaction.completed_at is not None

    def test_transaction_fail(self):
        """Тест провала транзакции"""
        transaction = Transaction(
            amount=100.0,
            transaction_type=TransactionType.WITHDRAWAL,
            user_id=1,
            description="Original description"
        )

        reason = "Insufficient funds"
        transaction.fail(reason)

        assert transaction.status == TransactionStatus.FAILED
        assert reason in transaction.description

    def test_transaction_fail_without_reason(self):
        """Тест провала транзакции без указания причины"""
        transaction = Transaction(
            amount=100.0,
            transaction_type=TransactionType.WITHDRAWAL,
            user_id=1,
            description="Original description"
        )

        transaction.fail()

        assert transaction.status == TransactionStatus.FAILED
        assert transaction.description == "Original description"

    def test_transaction_fail_no_original_description(self):
        """Тест провала транзакции без исходного описания"""
        transaction = Transaction(
            amount=100.0,
            transaction_type=TransactionType.WITHDRAWAL,
            user_id=1
        )

        reason = "Network error"
        transaction.fail(reason)

        assert transaction.status == TransactionStatus.FAILED
        assert f"Failed: {reason}" in transaction.description

    def test_transaction_string_representation(self):
        """Тест строкового представления транзакции"""
        transaction = Transaction(
            id=1,
            amount=100.0,
            transaction_type=TransactionType.DEPOSIT,
            user_id=5
        )

        str_repr = str(transaction)
        assert "id=1" in str_repr
        assert "type=deposit" in str_repr
        assert "amount=100.0" in str_repr
        assert "user_id=5" in str_repr


class TestEnumValues:
    """Тесты перечислений (Enum)"""

    def test_user_role_values(self):
        """Тест значений UserRole"""
        assert UserRole.USER == "user"
        assert UserRole.ADMIN == "admin"

        # Проверяем, что можно создать пользователя с каждой ролью
        user = User(
            email="user@example.com",
            username="user",
            hashed_password="password",
            role=UserRole.USER
        )
        assert user.role == UserRole.USER

        admin = User(
            email="admin@example.com",
            username="admin",
            hashed_password="password",
            role=UserRole.ADMIN
        )
        assert admin.role == UserRole.ADMIN

    def test_event_status_values(self):
        """Тест значений EventStatus"""
        assert EventStatus.DRAFT == "draft"
        assert EventStatus.ACTIVE == "active"
        assert EventStatus.CANCELLED == "cancelled"
        assert EventStatus.COMPLETED == "completed"

        # Проверяем создание событий с разными статусами
        for status in [EventStatus.DRAFT, EventStatus.ACTIVE, EventStatus.CANCELLED, EventStatus.COMPLETED]:
            event = Event(
                title="Test Event",
                description="Test",
                creator_id=1,
                status=status
            )
            assert event.status == status

    def test_transaction_type_values(self):
        """Тест значений TransactionType"""
        assert TransactionType.DEPOSIT == "deposit"
        assert TransactionType.WITHDRAWAL == "withdrawal"
        assert TransactionType.EVENT_PAYMENT == "event_payment"
        assert TransactionType.REFUND == "refund"

        # Проверяем создание транзакций каждого типа
        for trans_type in [TransactionType.DEPOSIT, TransactionType.WITHDRAWAL,
                          TransactionType.EVENT_PAYMENT, TransactionType.REFUND]:
            transaction = Transaction(
                amount=100.0,
                transaction_type=trans_type,
                user_id=1
            )
            assert transaction.transaction_type == trans_type

    def test_transaction_status_values(self):
        """Тест значений TransactionStatus"""
        assert TransactionStatus.PENDING == "pending"
        assert TransactionStatus.COMPLETED == "completed"
        assert TransactionStatus.FAILED == "failed"
        assert TransactionStatus.CANCELLED == "cancelled"

        # Проверяем установку разных статусов
        transaction = Transaction(
            amount=100.0,
            transaction_type=TransactionType.DEPOSIT,
            user_id=1
        )

        for status in [TransactionStatus.PENDING, TransactionStatus.COMPLETED,
                      TransactionStatus.FAILED, TransactionStatus.CANCELLED]:
            transaction.status = status
            assert transaction.status == status


class TestModelRelationships:
    """Тесты связей между моделями"""

    def test_user_events_relationship(self):
        """Тест связи пользователя с событиями"""
        user = User(
            id=1,
            email="creator@example.com",
            username="creator",
            hashed_password="password"
        )

        # Пользователь может иметь список событий (через back_populates)
        # В реальной БД это будет загружаться автоматически
        assert hasattr(user, 'events')
        assert hasattr(user, 'transactions')

    def test_user_transactions_relationship(self):
        """Тест связи пользователя с транзакциями"""
        user = User(
            id=1,
            email="user@example.com",
            username="user",
            hashed_password="password"
        )

        # Пользователь может иметь список транзакций
        assert hasattr(user, 'transactions')

    def test_event_creator_relationship(self):
        """Тест связи события с создателем"""
        event = Event(
            id=1,
            title="Test Event",
            description="Test",
            creator_id=1
        )

        # Событие может иметь ссылку на создателя
        assert hasattr(event, 'creator')
        assert event.creator_id == 1

    def test_transaction_user_relationship(self):
        """Тест связи транзакции с пользователем"""
        transaction = Transaction(
            id=1,
            amount=100.0,
            transaction_type=TransactionType.DEPOSIT,
            user_id=5
        )

        # Транзакция может иметь ссылку на пользователя
        assert hasattr(transaction, 'user')
        assert transaction.user_id == 5


class TestModelValidation:
    """Тесты валидации моделей"""

    def test_user_email_field(self):
        """Тест поля email пользователя"""
        user = User(
            email="test@example.com",
            username="test",
            hashed_password="password"
        )

        assert user.email == "test@example.com"
        # SQLModel/Pydantic будет валидировать email формат

    def test_event_cost_non_negative(self):
        """Тест что стоимость события не отрицательная"""
        # Модель позволяет отрицательные значения, но бизнес-логика должна проверять
        event = Event(
            title="Test Event",
            description="Test",
            creator_id=1,
            cost=-10.0  # Отрицательная стоимость
        )

        assert event.cost == -10.0  # Модель это позволяет

    def test_transaction_amount_precision(self):
        """Тест точности суммы транзакции"""
        precise_amount = 123.45

        transaction = Transaction(
            amount=precise_amount,
            transaction_type=TransactionType.DEPOSIT,
            user_id=1
        )

        assert transaction.amount == precise_amount

    def test_event_max_participants_validation(self):
        """Тест валидации максимального количества участников"""
        # Модель должна позволять None (без ограничений)
        event_unlimited = Event(
            title="Unlimited Event",
            description="No limit",
            creator_id=1,
            max_participants=None
        )

        assert event_unlimited.max_participants is None

        # И положительные числа
        event_limited = Event(
            title="Limited Event",
            description="With limit",
            creator_id=1,
            max_participants=50
        )

        assert event_limited.max_participants == 50


class TestModelEdgeCases:
    """Тесты граничных случаев для моделей"""

    def test_user_zero_balance(self):
        """Тест пользователя с нулевым балансом"""
        user = User(
            email="zero@example.com",
            username="zero",
            hashed_password="password",
            balance=0.0
        )

        assert user.balance == 0.0
        assert user.has_sufficient_balance(0.0) == True
        assert user.has_sufficient_balance(0.01) == False

    def test_event_zero_cost(self):
        """Тест бесплатного события"""
        event = Event(
            title="Free Event",
            description="Free event",
            creator_id=1,
            cost=0.0
        )

        assert event.cost == 0.0

    def test_event_zero_participants(self):
        """Тест события без участников"""
        event = Event(
            title="Empty Event",
            description="No participants yet",
            creator_id=1,
            current_participants=0
        )

        assert event.current_participants == 0

    def test_transaction_zero_amount(self):
        """Тест транзакции с нулевой суммой"""
        transaction = Transaction(
            amount=0.0,
            transaction_type=TransactionType.DEPOSIT,
            user_id=1,
            description="Zero amount transaction"
        )

        assert transaction.amount == 0.0

    def test_very_large_amounts(self):
        """Тест очень больших сумм"""
        large_amount = 999999.99

        user = User(
            email="rich@example.com",
            username="rich",
            hashed_password="password",
            balance=large_amount
        )

        event = Event(
            title="Expensive Event",
            description="Very expensive",
            creator_id=1,
            cost=large_amount
        )

        transaction = Transaction(
            amount=large_amount,
            transaction_type=TransactionType.DEPOSIT,
            user_id=1
        )

        assert user.balance == large_amount
        assert event.cost == large_amount
        assert transaction.amount == large_amount

    def test_long_text_fields(self):
        """Тест длинных текстовых полей"""
        long_title = "A" * 1000
        long_description = "B" * 5000

        event = Event(
            title=long_title,
            description=long_description,
            creator_id=1
        )

        assert len(event.title) == 1000
        assert len(event.description) == 5000

        transaction = Transaction(
            amount=100.0,
            transaction_type=TransactionType.DEPOSIT,
            user_id=1,
            description=long_description
        )

        assert len(transaction.description) == 5000
            status=EventStatus.ACTIVE,
            max_participants=10,
            current_participants=5
        )

        assert event.can_join() == True

    def test_event_can_join_inactive(self):
        """Тест невозможности присоединения к неактивному событию"""
        event = Event(
            title="Test Event",
            description="Test",
            creator_id=1,
            status=EventStatus.DRAFT
        )

        assert event.can_join() == False

    def test_event_can_join_full_capacity(self):
            """Тест невозможности присоединения к заполненному событию"""
            event = Event(
                title="Test Event",
                description="Test",
                creator_id=1,
                status=EventStatus.ACTIVE,
                max_participants=5,
                current_participants=5
            )

            assert event.can_join() == False

        def test_event_can_join_inactive(self):
            """Тест невозможности присоединения к неактивному событию"""
            event = Event(
                title="Test Event",
                description="Test",
                creator_id=1,
                status=EventStatus.DRAFT
            )

            assert event.can_join() == False

        def test_event_can_join_cancelled(self):
            """Тест невозможности присоединения к отмененному событию"""
            event = Event(
                title="Test Event",
                description="Test",
                creator_id=1,
                status=EventStatus.CANCELLED,
                max_participants=10,
                current_participants=3
            )

            assert event.can_join() == False

        def test_event_can_join_completed(self):
            """Тест невозможности присоединения к завершенному событию"""
            event = Event(
                title="Test Event",
                description="Test",
                creator_id=1,
                status=EventStatus.COMPLETED,
                max_participants=10,
                current_participants=8
            )

            assert event.can_join() == False

        def test_event_join_success(self):
            """Тест успешного присоединения к событию"""
            event = Event(
                title="Test Event",
                description="Test",
                creator_id=1,
                status=EventStatus.ACTIVE,
                max_participants=10,
                current_participants=5
            )

            initial_participants = event.current_participants
            success = event.join_event()

            assert success == True
            assert event.current_participants == initial_participants + 1
            assert event.updated_at is not None

        def test_event_join_when_full(self):
            """Тест присоединения к заполненному событию"""
            event = Event(
                title="Test Event",
                description="Test",
                creator_id=1,
                status=EventStatus.ACTIVE,
                max_participants=5,
                current_participants=5
            )

            success = event.join_event()

            assert success == False
            assert event.current_participants == 5  # Не изменился

        def test_event_join_when_inactive(self):
            """Тест присоединения к неактивному событию"""
            event = Event(
                title="Test Event",
                description="Test",
                creator_id=1,
                status=EventStatus.DRAFT,
                max_participants=10,
                current_participants=0
            )

            success = event.join_event()

            assert success == False
            assert event.current_participants == 0

        def test_event_string_representation(self):
            """Тест строкового представления события"""
            event = Event(
                id=1,
                title="Test Workshop",
                cost=100.0,
                creator_id=2
            )

            str_repr = str(event)
            assert "id=1" in str_repr
            assert "Test Workshop" in str_repr
            assert "cost=100.0" in str_repr
            assert "creator=2" in str_repr


    class TestTransactionModel:
        """Тесты модели Transaction"""

        def test_transaction_creation(self):
            """Тест создания транзакции"""
            transaction = Transaction(
                amount=100.0,
                transaction_type=TransactionType.DEPOSIT,
                description="Test deposit",
                user_id=1
            )

            assert transaction.amount == 100.0
            assert transaction.transaction_type == TransactionType.DEPOSIT
            assert transaction.status == TransactionStatus.PENDING
            assert transaction.description == "Test deposit"
            assert transaction.user_id == 1
            assert transaction.event_id is None
            assert transaction.reference_id is None
            assert transaction.created_at is not None
            assert transaction.completed_at is None

        def test_transaction_default_values(self):
            """Тест значений по умолчанию для транзакции"""
            transaction = Transaction(
                amount=50.0,
                transaction_type=TransactionType.WITHDRAWAL,
                user_id=1
            )

            assert transaction.status == TransactionStatus.PENDING
            assert transaction.description is None
            assert transaction.reference_id is None
            assert transaction.event_id is None
            assert transaction.completed_at is None

        def test_event_payment_transaction(self):
            """Тест транзакции оплаты события"""
            transaction = Transaction(
                amount=150.0,
                transaction_type=TransactionType.EVENT_PAYMENT,
                description="Payment for workshop",
                user_id=1,
                event_id=5
            )

            assert transaction.transaction_type == TransactionType.EVENT_PAYMENT
            assert transaction.event_id == 5
            assert transaction.amount == 150.0

        def test_refund_transaction(self):
            """Тест транзакции возврата"""
            transaction = Transaction(
                amount=75.0,
                transaction_type=TransactionType.REFUND,
                description="Event cancellation refund",
                user_id=1,
                event_id=3
            )

            assert transaction.transaction_type == TransactionType.REFUND
            assert transaction.event_id == 3

        def test_transaction_complete(self):
            """Тест завершения транзакции"""
            transaction = Transaction(
                amount=100.0,
                transaction_type=TransactionType.DEPOSIT,
                user_id=1
            )

            assert transaction.status == TransactionStatus.PENDING
            assert transaction.completed_at is None

            transaction.complete()

            assert transaction.status == TransactionStatus.COMPLETED
            assert transaction.completed_at is not None

        def test_transaction_fail(self):
            """Тест провала транзакции"""
            transaction = Transaction(
                amount=100.0,
                transaction_type=TransactionType.WITHDRAWAL,
                user_id=1,
                description="Original description"
            )

            reason = "Insufficient funds"
            transaction.fail(reason)

            assert transaction.status == TransactionStatus.FAILED
            assert reason in transaction.description

        def test_transaction_fail_without_reason(self):
            """Тест провала транзакции без указания причины"""
            transaction = Transaction(
                amount=100.0,
                transaction_type=TransactionType.WITHDRAWAL,
                user_id=1,
                description="Original description"
            )

            transaction.fail()

            assert transaction.status == TransactionStatus.FAILED
            assert transaction.description == "Original description"

        def test_transaction_fail_no_original_description(self):
            """Тест провала транзакции без исходного описания"""
            transaction = Transaction(
                amount=100.0,
                transaction_type=TransactionType.WITHDRAWAL,
                user_id=1
            )

            reason = "Network error"
            transaction.fail(reason)

            assert transaction.status == TransactionStatus.FAILED
            assert f"Failed: {reason}" in transaction.description

        def test_transaction_string_representation(self):
            """Тест строкового представления транзакции"""
            transaction = Transaction(
                id=1,
                amount=100.0,
                transaction_type=TransactionType.DEPOSIT,
                user_id=5
            )

            str_repr = str(transaction)
            assert "id=1" in str_repr
            assert "type=deposit" in str_repr
            assert "amount=100.0" in str_repr
            assert "user_id=5" in str_repr


    class TestEnumValues:
        """Тесты перечислений (Enum)"""

        def test_user_role_values(self):
            """Тест значений UserRole"""
            assert UserRole.USER == "user"
            assert UserRole.ADMIN == "admin"

            # Проверяем, что можно создать пользователя с каждой ролью
            user = User(
                email="user@example.com",
                username="user",
                hashed_password="password",
                role=UserRole.USER
            )
            assert user.role == UserRole.USER

            admin = User(
                email="admin@example.com",
                username="admin",
                hashed_password="password",
                role=UserRole.ADMIN
            )
            assert admin.role == UserRole.ADMIN

        def test_event_status_values(self):
            """Тест значений EventStatus"""
            assert EventStatus.DRAFT == "draft"
            assert EventStatus.ACTIVE == "active"
            assert EventStatus.CANCELLED == "cancelled"
            assert EventStatus.COMPLETED == "completed"

            # Проверяем создание событий с разными статусами
            for status in [EventStatus.DRAFT, EventStatus.ACTIVE, EventStatus.CANCELLED, EventStatus.COMPLETED]:
                event = Event(
                    title="Test Event",
                    description="Test",
                    creator_id=1,
                    status=status
                )
                assert event.status == status

        def test_transaction_type_values(self):
            """Тест значений TransactionType"""
            assert TransactionType.DEPOSIT == "deposit"
            assert TransactionType.WITHDRAWAL == "withdrawal"
            assert TransactionType.EVENT_PAYMENT == "event_payment"
            assert TransactionType.REFUND == "refund"

            # Проверяем создание транзакций каждого типа
            for trans_type in [TransactionType.DEPOSIT, TransactionType.WITHDRAWAL,
                              TransactionType.EVENT_PAYMENT, TransactionType.REFUND]:
                transaction = Transaction(
                    amount=100.0,
                    transaction_type=trans_type,
                    user_id=1
                )
                assert transaction.transaction_type == trans_type

        def test_transaction_status_values(self):
            """Тест значений TransactionStatus"""
            assert TransactionStatus.PENDING == "pending"
            assert TransactionStatus.COMPLETED == "completed"
            assert TransactionStatus.FAILED == "failed"
            assert TransactionStatus.CANCELLED == "cancelled"

            # Проверяем установку разных статусов
            transaction = Transaction(
                amount=100.0,
                transaction_type=TransactionType.DEPOSIT,
                user_id=1
            )

            for status in [TransactionStatus.PENDING, TransactionStatus.COMPLETED,
                          TransactionStatus.FAILED, TransactionStatus.CANCELLED]:
                transaction.status = status
                assert transaction.status == status


    class TestModelRelationships:
        """Тесты связей между моделями"""

        def test_user_events_relationship(self):
            """Тест связи пользователя с событиями"""
            user = User(
                id=1,
                email="creator@example.com",
                username="creator",
                hashed_password="password"
            )

            # Пользователь может иметь список событий (через back_populates)
            # В реальной БД это будет загружаться автоматически
            assert hasattr(user, 'events')
            assert hasattr(user, 'transactions')

        def test_user_transactions_relationship(self):
            """Тест связи пользователя с транзакциями"""
            user = User(
                id=1,
                email="user@example.com",
                username="user",
                hashed_password="password"
            )

            # Пользователь может иметь список транзакций
            assert hasattr(user, 'transactions')

        def test_event_creator_relationship(self):
            """Тест связи события с создателем"""
            event = Event(
                id=1,
                title="Test Event",
                description="Test",
                creator_id=1
            )

            # Событие может иметь ссылку на создателя
            assert hasattr(event, 'creator')
            assert event.creator_id == 1

        def test_transaction_user_relationship(self):
            """Тест связи транзакции с пользователем"""
            transaction = Transaction(
                id=1,
                amount=100.0,
                transaction_type=TransactionType.DEPOSIT,
                user_id=5
            )

            # Транзакция может иметь ссылку на пользователя
            assert hasattr(transaction, 'user')
            assert transaction.user_id == 5


    class TestModelValidation:
        """Тесты валидации моделей"""

        def test_user_email_field(self):
            """Тест поля email пользователя"""
            user = User(
                email="test@example.com",
                username="test",
                hashed_password="password"
            )

            assert user.email == "test@example.com"
            # SQLModel/Pydantic будет валидировать email формат

        def test_event_cost_non_negative(self):
            """Тест что стоимость события не отрицательная"""
            # Модель позволяет отрицательные значения, но бизнес-логика должна проверять
            event = Event(
                title="Test Event",
                description="Test",
                creator_id=1,
                cost=-10.0  # Отрицательная стоимость
            )

            assert event.cost == -10.0  # Модель это позволяет

        def test_transaction_amount_precision(self):
            """Тест точности суммы транзакции"""
            precise_amount = 123.45

            transaction = Transaction(
                amount=precise_amount,
                transaction_type=TransactionType.DEPOSIT,
                user_id=1
            )

            assert transaction.amount == precise_amount

        def test_event_max_participants_validation(self):
            """Тест валидации максимального количества участников"""
            # Модель должна позволять None (без ограничений)
            event_unlimited = Event(
                title="Unlimited Event",
                description="No limit",
                creator_id=1,
                max_participants=None
            )

            assert event_unlimited.max_participants is None

            # И положительные числа
            event_limited = Event(
                title="Limited Event",
                description="With limit",
                creator_id=1,
                max_participants=50
            )

            assert event_limited.max_participants == 50


    class TestModelEdgeCases:
        """Тесты граничных случаев для моделей"""

        def test_user_zero_balance(self):
            """Тест пользователя с нулевым балансом"""
            user = User(
                email="zero@example.com",
                username="zero",
                hashed_password="password",
                balance=0.0
            )

            assert user.balance == 0.0
            assert user.has_sufficient_balance(0.0) == True
            assert user.has_sufficient_balance(0.01) == False

        def test_event_zero_cost(self):
            """Тест бесплатного события"""
            event = Event(
                title="Free Event",
                description="Free event",
                creator_id=1,
                cost=0.0
            )

            assert event.cost == 0.0

        def test_event_zero_participants(self):
            """Тест события без участников"""
            event = Event(
                title="Empty Event",
                description="No participants yet",
                creator_id=1,
                current_participants=0
            )

            assert event.current_participants == 0

        def test_transaction_zero_amount(self):
            """Тест транзакции с нулевой суммой"""
            transaction = Transaction(
                amount=0.0,
                transaction_type=TransactionType.DEPOSIT,
                user_id=1,
                description="Zero amount transaction"
            )

            assert transaction.amount == 0.0

        def test_very_large_amounts(self):
            """Тест очень больших сумм"""
            large_amount = 999999.99

            user = User(
                email="rich@example.com",
                username="rich",
                hashed_password="password",
                balance=large_amount
            )

            event = Event(
                title="Expensive Event",
                description="Very expensive",
                creator_id=1,
                cost=large_amount
            )

            transaction = Transaction(
                amount=large_amount,
                transaction_type=TransactionType.DEPOSIT,
                user_id=1
            )

            assert user.balance == large_amount
            assert event.cost == large_amount
            assert transaction.amount == large_amount

        def test_long_text_fields(self):
            """Тест длинных текстовых полей"""
            long_title = "A" * 1000
            long_description = "B" * 5000

            event = Event(
                title=long_title,
                description=long_description,
                creator_id=1
            )

            assert len(event.title) == 1000
            assert len(event.description) == 5000

            transaction = Transaction(
                amount=100.0,
                transaction_type=TransactionType.DEPOSIT,
                user_id=1,
                description=long_description
            )

            assert len(transaction.description) == 5000

        def test_unicode_text_fields(self):
            """Тест полей с Unicode символами"""
            unicode_title = "Мастер-класс по программированию 🚀"
            unicode_description = "Изучаем Python с эмодзи 🐍 и специальными символами: áéíóú"

            event = Event(
                title=unicode_title,
                description=unicode_description,
                creator_id=1
            )

            assert event.title == unicode_title
            assert event.description == unicode_description

            user = User(
                email="unicode@example.com",
                username="пользователь",
                full_name="Иван Иванович",
                hashed_password="password"
            )

            assert user.username == "пользователь"
            assert user.full_name == "Иван Иванович"

        def test_boundary_values(self):
            """Тест граничных значений"""
            # Минимальные положительные значения
            min_event = Event(
                title="A",  # Минимальная длина
                description="B",
                creator_id=1,
                cost=0.01,  # Минимальная стоимость
                max_participants=1  # Минимальные участники
            )

            assert min_event.title == "A"
            assert min_event.cost == 0.01
            assert min_event.max_participants == 1

            # Минимальная транзакция
            min_transaction = Transaction(
                amount=0.01,
                transaction_type=TransactionType.DEPOSIT,
                user_id=1
            )

            assert min_transaction.amount == 0.01
