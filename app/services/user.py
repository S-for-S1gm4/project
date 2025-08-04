from sqlmodel import Session, select
from typing import Optional, List
from models import User, UserRole, Transaction, TransactionType, TransactionStatus
from database.database import get_db_session
import hashlib
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Сервис для работы с пользователями"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Простое хэширование пароля (в продакшене используйте bcrypt)"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def create_user(email: str, username: str, password: str,
                   full_name: Optional[str] = None,
                   role: UserRole = UserRole.USER) -> User:
        """Создание нового пользователя"""
        with get_db_session() as session:
            # Проверяем, существует ли пользователь
            existing_user = session.exec(
                select(User).where(
                    (User.email == email) | (User.username == username)
                )
            ).first()

            if existing_user:
                raise ValueError(f"User with email {email} or username {username} already exists")

            # Создаем нового пользователя
            user = User(
                email=email,
                username=username,
                full_name=full_name,
                hashed_password=UserService.hash_password(password),
                role=role
            )

            session.add(user)
            session.commit()
            session.refresh(user)

            logger.info(f"Created user: {user}")
            return user

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        with get_db_session() as session:
            return session.get(User, user_id)

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Получение пользователя по email"""
        with get_db_session() as session:
            return session.exec(select(User).where(User.email == email)).first()

    @staticmethod
    def get_all_users() -> List[User]:
        """Получение всех пользователей"""
        with get_db_session() as session:
            return list(session.exec(select(User)).all())

    @staticmethod
    def add_balance(user_id: int, amount: float, description: str = "Balance top-up") -> bool:
        """Пополнение баланса пользователя"""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        with get_db_session() as session:
            user = session.get(User, user_id)
            if not user:
                raise ValueError(f"User with id {user_id} not found")

            # Создаем транзакцию
            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                transaction_type=TransactionType.DEPOSIT,
                description=description
            )

            # Обновляем баланс
            user.add_balance(amount)

            session.add(transaction)
            session.add(user)
            session.commit()

            # Отмечаем транзакцию как завершенную
            transaction.complete()
            session.add(transaction)
            session.commit()

            logger.info(f"Added {amount} to user {user_id} balance. New balance: {user.balance}")
            return True

    @staticmethod
    def deduct_balance(user_id: int, amount: float, description: str = "Balance deduction") -> bool:
        """Списание с баланса пользователя"""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        with get_db_session() as session:
            user = session.get(User, user_id)
            if not user:
                raise ValueError(f"User with id {user_id} not found")

            if not user.has_sufficient_balance(amount):
                logger.warning(f"Insufficient balance for user {user_id}. Required: {amount}, Available: {user.balance}")
                return False

            # Создаем транзакцию
            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                transaction_type=TransactionType.WITHDRAWAL,
                description=description
            )

            # Списываем с баланса
            user.deduct_balance(amount)

            session.add(transaction)
            session.add(user)
            session.commit()

            # Отмечаем транзакцию как завершенную
            transaction.complete()
            session.add(transaction)
            session.commit()

            logger.info(f"Deducted {amount} from user {user_id} balance. New balance: {user.balance}")
            return True

    @staticmethod
    def get_user_transactions(user_id: int) -> List[Transaction]:
        """Получение истории транзакций пользователя"""
        with get_db_session() as session:
            return list(session.exec(
                select(Transaction)
                .where(Transaction.user_id == user_id)
                .order_by(Transaction.created_at.desc())
            ).all())
