from sqlmodel import SQLModel, Session, create_engine, select
from contextlib import contextmanager
from typing import Generator
import logging
from .config import get_settings

logger = logging.getLogger(__name__)


from sqlmodel import SQLModel, Session, create_engine, select
from contextlib import contextmanager
from typing import Generator
import logging
from .config import get_settings

logger = logging.getLogger(__name__)


def get_database_engine():
    """
    Create and configure the SQLAlchemy engine.

    Returns:
        Engine: Configured SQLAlchemy engine
    """
    try:
        settings = get_settings()
        logger.info(f"Connecting to database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

        engine = create_engine(
            url=settings.DATABASE_URL_sync,
            echo=settings.DEBUG,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        logger.error("Make sure all required environment variables are set in .env file")
        raise


# Глобальный экземпляр движка
engine = get_database_engine()


def get_session() -> Generator[Session, None, None]:
    """Генератор сессий для dependency injection"""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


@contextmanager
def get_db_session():
    """Context manager для работы с сессией"""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def init_db(drop_all: bool = False) -> None:
    """
    Initialize database schema.

    Args:
        drop_all: If True, drops all tables before creation

    Raises:
        Exception: Any database-related exception
    """
    try:
        logger.info("Initializing database...")

        # Импортируем все модели для создания таблиц
        from models import User, Event, Transaction

        if drop_all:
            logger.warning("Dropping all existing tables...")
            SQLModel.metadata.drop_all(engine)

        logger.info("Creating database tables...")
        SQLModel.metadata.create_all(engine)

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def test_connection() -> bool:
    """
    Test database connection.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with Session(engine) as session:
            session.exec(select(1))
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
