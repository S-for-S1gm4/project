"""
Тесты для UserService - сервиса работы с пользователями
"""
import pytest
from services.user_service import UserService
from models import UserRole, TransactionType
from core.exceptions import DuplicateUserException


class TestUserCreation:
    """Тесты создания пользователей"""

    def test_create_user_success(self, clean_db, sample_user_data):
        """Тест успешного создания пользователя"""
        user = UserService.create_user(**sample_user_data)

        assert user.id is not None
        assert user.email == sample_user_data["email"]
        assert user.username == sample_user_data["username"]
        assert user.full_name == sample_user_data["full_name"]
        assert user.role == UserRole.USER
        assert user.balance == 0.0
        assert user.is_active == True
        assert user.created_at is not None

        # Проверяем, что пароль хэшируется
        assert user.hashed_password != sample_user_data["password"]
        assert len(user.hashed_password) > 0

    def test_create_admin_user(self, clean_db, sample_admin_data):
        """Тест создания администратора"""
        admin = UserService.create_user(**sample_admin_data)

        assert admin.role == UserRole.ADMIN
        assert admin.email == sample_admin_data["email"]
        assert admin.username == sample_admin_data["username"]

    def test_create_user_duplicate_email(self, created_user, sample_user_data):
        """Тест создания пользователя с дублирующимся email"""
        # Пытаемся создать пользователя с тем же email
        duplicate_data = sample_user_data.copy()
        duplicate_data["username"] = "different_username"

        with pytest.raises(DuplicateUserException) as exc_info:
            UserService.create_user(**duplicate_data)

        assert "email" in str(exc_info.value.message).lower()

    def test_create_user_duplicate_username(self, created_user, sample_user_data):
        """Тест создания пользователя с дублирующимся username"""
        # Пытаемся создать пользователя с тем же username
        duplicate_data = sample_user_data.copy()
        duplicate_data["email"] = "different@example.com"

        with pytest.raises(DuplicateUserException) as exc_info:
            UserService.create_user(**duplicate_data)

        assert "username" in str(exc_info.value.message).lower()

    def test_create_user_minimal_data(self, clean_db):
        """Тест создания пользователя с минимальными данными"""
        minimal_data = {
            "email": "minimal@example.com",
            "username": "minimal",
            "password": "password123"
        }

        user = UserService.create_user(**minimal_data)

        assert user.id is not None
        assert user.email == minimal_data["email"]
        assert user.username == minimal_data["username"]
        assert user.full_name is None
        assert user.role == UserRole.USER


class TestUserRetrieval:
    """Тесты получения пользователей"""

    def test_get_user_by_id_exists(self, created_user):
        """Тест получения существующего пользователя по ID"""
        retrieved_user = UserService.get_user_by_id(created_user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email
        assert retrieved_user.username == created_user.username

    def test_get_user_by_id_not_exists(self, clean_db):
        """Тест получения несуществующего пользователя по ID"""
        retrieved_user = UserService.get_user_by_id(99999)

        assert retrieved_user is None

    def test_get_user_by_email_exists(self, created_user):
        """Тест получения существующего пользователя по email"""
        retrieved_user = UserService.get_user_by_email(created_user.email)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email

    def test_get_user_by_email_not_exists(self, clean_db):
        """Тест получения несуществующего пользователя по email"""
        retrieved_user = UserService.get_user_by_email("nonexistent@example.com")

        assert retrieved_user is None

    def test_get_all_users(self, multiple_users):
        """Тест получения всех пользователей"""
        all_users = UserService.get_all_users()

        assert len(all_users) == 3
        assert all(user.id is not None for user in all_users)

        # Проверяем, что все созданные пользователи присутствуют
        user_emails = [user.email for user in all_users]
        expected_emails = [f"user{i}@example.com" for i in range(3)]

        for email in expected_emails:
            assert email in user_emails

    def test_get_all_users_empty_db(self, clean_db):
        """Тест получения пользователей из пустой БД"""
        all_users = UserService.get_all_users()

        assert all_users == []


class TestBalanceOperations:
    """Тесты операций с балансом"""

    def test_add_balance_success(self, created_user):
        """Тест успешного пополнения баланса"""
        initial_balance = created_user.balance
        amount = 250.0
        description = "Test balance addition"

        success = UserService.add_balance(created_user.id, amount, description)

        assert success == True

        # Проверяем обновленный баланс
        updated_user = UserService.get_user_by_id(created_user.id)
        assert updated_user.balance == initial_balance + amount

        # Проверяем создание транзакции
        transactions = UserService.get_user_transactions(created_user.id)
        assert len(transactions) == 1

        transaction = transactions[0]
        assert transaction.amount == amount
        assert transaction.transaction_type == TransactionType.DEPOSIT
        assert transaction.description == description
        assert transaction.user_id == created_user.id

    def test_add_balance_multiple_times(self, created_user):
        """Тест множественного пополнения баланса"""
        amounts = [100.0, 200.0, 50.0]

        for i, amount in enumerate(amounts):
            success = UserService.add_balance(
                created_user.id,
                amount,
                f"Addition {i+1}"
            )
            assert success == True

        # Проверяем итоговый баланс
        updated_user = UserService.get_user_by_id(created_user.id)
        expected_balance = sum(amounts)
        assert updated_user.balance == expected_balance

        # Проверяем количество транзакций
        transactions = UserService.get_user_transactions(created_user.id)
        assert len(transactions) == len(amounts)

    def test_add_balance_negative_amount(self, created_user):
        """Тест пополнения баланса отрицательной суммой"""
        with pytest.raises(ValueError) as exc_info:
            UserService.add_balance(created_user.id, -100.0, "Negative amount")

        assert "positive" in str(exc_info.value).lower()

    def test_add_balance_zero_amount(self, created_user):
        """Тест пополнения баланса нулевой суммой"""
        with pytest.raises(ValueError) as exc_info:
            UserService.add_balance(created_user.id, 0.0, "Zero amount")

        assert "positive" in str(exc_info.value).lower()

    def test_add_balance_nonexistent_user(self, clean_db):
        """Тест пополнения баланса несуществующего пользователя"""
        with pytest.raises(ValueError) as exc_info:
            UserService.add_balance(99999, 100.0, "Test")

        assert "not found" in str(exc_info.value).lower()

    def test_deduct_balance_success(self, user_with_balance):
        """Тест успешного списания с баланса"""
        initial_balance = user_with_balance.balance
        amount = 300.0
        description = "Test balance deduction"

        success = UserService.deduct_balance(user_with_balance.id, amount, description)

        assert success == True

        # Проверяем обновленный баланс
        updated_user = UserService.get_user_by_id(user_with_balance.id)
        assert updated_user.balance == initial_balance - amount

        # Проверяем создание транзакции
        transactions = UserService.get_user_transactions(user_with_balance.id)
        withdrawal_transactions = [
            t for t in transactions
            if t.transaction_type == TransactionType.WITHDRAWAL
        ]
        assert len(withdrawal_transactions) == 1

        transaction = withdrawal_transactions[0]
        assert transaction.amount == amount
        assert transaction.description == description

    def test_deduct_balance_insufficient_funds(self, user_with_balance):
        """Тест списания при недостаточном балансе"""
        # Пытаемся списать больше, чем есть на балансе
        excessive_amount = user_with_balance.balance + 100.0

        success = UserService.deduct_balance(
            user_with_balance.id,
            excessive_amount,
            "Excessive withdrawal"
        )

        assert success == False

        # Проверяем, что баланс не изменился
        updated_user = UserService.get_user_by_id(user_with_balance.id)
        assert updated_user.balance == user_with_balance.balance

    def test_deduct_balance_exact_amount(self, user_with_balance):
        """Тест списания точной суммы баланса"""
        exact_amount = user_with_balance.balance

        success = UserService.deduct_balance(
            user_with_balance.id,
            exact_amount,
            "Complete withdrawal"
        )

        assert success == True

        # Проверяем, что баланс стал нулевым
        updated_user = UserService.get_user_by_id(user_with_balance.id)
        assert updated_user.balance == 0.0

    def test_deduct_balance_negative_amount(self, user_with_balance):
        """Тест списания отрицательной суммы"""
        with pytest.raises(ValueError) as exc_info:
            UserService.deduct_balance(user_with_balance.id, -50.0, "Negative deduction")

        assert "positive" in str(exc_info.value).lower()

    def test_deduct_balance_nonexistent_user(self, clean_db):
        """Тест списания у несуществующего пользователя"""
        with pytest.raises(ValueError) as exc_info:
            UserService.deduct_balance(99999, 100.0, "Test")

        assert "not found" in str(exc_info.value).lower()


class TestTransactionHistory:
    """Тесты истории транзакций"""

    def test_get_user_transactions(self, transaction_history_user):
        """Тест получения истории транзакций пользователя"""
        transactions = UserService.get_user_transactions(transaction_history_user.id)

        # Должно быть 4 транзакции (3 пополнения + 1 списание)
        assert len(transactions) == 4

        # Проверяем типы транзакций
        deposit_count = len([t for t in transactions if t.transaction_type == TransactionType.DEPOSIT])
        withdrawal_count = len([t for t in transactions if t.transaction_type == TransactionType.WITHDRAWAL])

        assert deposit_count == 3
        assert withdrawal_count == 1

        # Проверяем, что транзакции отсортированы по дате (новые первые)
        dates = [t.created_at for t in transactions]
        assert dates == sorted(dates, reverse=True)

    def test_get_user_transactions_empty(self, created_user):
        """Тест получения истории транзакций для пользователя без операций"""
        transactions = UserService.get_user_transactions(created_user.id)

        assert transactions == []

    def test_get_user_transactions_nonexistent_user(self, clean_db):
        """Тест получения истории транзакций несуществующего пользователя"""
        transactions = UserService.get_user_transactions(99999)

        assert transactions == []

    def test_transaction_details(self, transaction_history_user):
        """Тест детальной информации о транзакциях"""
        # Добавляем еще одну транзакцию с известными параметрами
        test_amount = 75.0
        test_description = "Specific test transaction"

        UserService.add_balance(transaction_history_user.id, test_amount, test_description)

        transactions = UserService.get_user_transactions(transaction_history_user.id)

        # Находим нашу тестовую транзакцию (должна быть первой - самая новая)
        test_transaction = transactions[0]

        assert test_transaction.amount == test_amount
        assert test_transaction.description == test_description
        assert test_transaction.transaction_type == TransactionType.DEPOSIT
        assert test_transaction.user_id == transaction_history_user.id
        assert test_transaction.created_at is not None
        assert test_transaction.status is not None


class TestUserBalanceValidation:
    """Тесты валидации баланса пользователей"""

    def test_user_has_sufficient_balance_true(self, user_with_balance):
        """Тест проверки достаточности баланса - положительный случай"""
        # Пользователь имеет достаточно средств
        required_amount = user_with_balance.balance - 100.0

        assert user_with_balance.has_sufficient_balance(required_amount) == True

    def test_user_has_sufficient_balance_false(self, user_with_balance):
        """Тест проверки достаточности баланса - отрицательный случай"""
        # Пользователь не имеет достаточно средств
        required_amount = user_with_balance.balance + 100.0

        assert user_with_balance.has_sufficient_balance(required_amount) == False

    def test_user_has_sufficient_balance_exact(self, user_with_balance):
        """Тест проверки достаточности баланса - точная сумма"""
        # Пользователь имеет точно необходимую сумму
        required_amount = user_with_balance.balance

        assert user_with_balance.has_sufficient_balance(required_amount) == True


class TestUserPasswordHashing:
    """Тесты хэширования паролей"""

    def test_password_hashing_consistency(self, clean_db):
        """Тест консистентности хэширования паролей"""
        password = "test_password_123"

        # Создаем двух пользователей с одинаковым паролем
        user1 = UserService.create_user(
            email="user1@example.com",
            username="user1",
            password=password
        )

        user2 = UserService.create_user(
            email="user2@example.com",
            username="user2",
            password=password
        )

        # Хэши должны быть одинаковыми для одинаковых паролей
        assert user1.hashed_password == user2.hashed_password
        # Но не должны совпадать с исходным паролем
        assert user1.hashed_password != password

    def test_password_hashing_different_passwords(self, clean_db):
        """Тест хэширования разных паролей"""
        user1 = UserService.create_user(
            email="user1@example.com",
            username="user1",
            password="password1"
        )

        user2 = UserService.create_user(
            email="user2@example.com",
            username="user2",
            password="password2"
        )

        # Хэши должны быть разными для разных паролей
        assert user1.hashed_password != user2.hashed_password


class TestEdgeCases:
    """Тесты граничных случаев"""

    def test_user_balance_precision(self, created_user):
        """Тест точности операций с балансом"""
        # Добавляем сумму с копейками
        amount = 123.45
        UserService.add_balance(created_user.id, amount, "Precision test")

        updated_user = UserService.get_user_by_id(created_user.id)
        assert abs(updated_user.balance - amount) < 0.01  # Допускаем погрешность в 1 копейку

    def test_large_balance_operations(self, created_user):
        """Тест операций с большими суммами"""
        large_amount = 1000000.00  # Миллион долларов

        success = UserService.add_balance(created_user.id, large_amount, "Large amount test")
        assert success == True

        updated_user = UserService.get_user_by_id(created_user.id)
        assert updated_user.balance == large_amount

    def test_many_small_transactions(self, created_user):
        """Тест множества мелких транзакций"""
        num_transactions = 100
        small_amount = 1.0

        for i in range(num_transactions):
            UserService.add_balance(created_user.id, small_amount, f"Small transaction {i}")

        updated_user = UserService.get_user_by_id(created_user.id)
        expected_balance = num_transactions * small_amount
        assert abs(updated_user.balance - expected_balance) < 0.01

        transactions = UserService.get_user_transactions(created_user.id)
        assert len(transactions) == num_transactions
