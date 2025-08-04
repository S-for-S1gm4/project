from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str
    APP_ENV: str
    APP_PORT: int
    DEBUG: bool

    # Database configuration
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # RabbitMQ configuration
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str

    # API settings
    API_VERSION: str
    API_PREFIX: str

    # Security
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_EXPIRATION_DELTA: int

    # Logging
    LOG_LEVEL: str
    LOG_FILE: str

    @property
    def DATABASE_URL_asyncpg(self) -> str:
        """URL для асинхронного подключения через asyncpg"""
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def DATABASE_URL_psycopg(self) -> str:
        """URL для подключения через psycopg (новая версия)"""
        return f'postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def DATABASE_URL_sync(self) -> str:
        """URL для синхронного подключения"""
        return f'postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def RABBITMQ_URL(self) -> str:
        """URL для подключения к RabbitMQ"""
        return f'amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/'

    model_config = SettingsConfigDict(
        env_file="../.env",  # Ищем .env файл в родительской директории (корень проекта)
        env_file_encoding="utf-8",
        case_sensitive=True,
        # Позволяет переопределять значения через переменные окружения
        env_ignore_empty=True
    )

    def validate(self) -> None:
        """Validate critical configuration settings"""
        required_db_fields = [self.DB_HOST, self.DB_USER, self.DB_PASSWORD, self.DB_NAME]
        if not all(required_db_fields):
            missing_fields = []
            if not self.DB_HOST:
                missing_fields.append("DB_HOST")
            if not self.DB_USER:
                missing_fields.append("DB_USER")
            if not self.DB_PASSWORD:
                missing_fields.append("DB_PASSWORD")
            if not self.DB_NAME:
                missing_fields.append("DB_NAME")

            raise ValueError(f"Missing required database configuration: {', '.join(missing_fields)}")

        # Дополнительные проверки
        if self.DB_PORT <= 0 or self.DB_PORT > 65535:
            raise ValueError(f"Invalid DB_PORT: {self.DB_PORT}")

        if self.APP_PORT <= 0 or self.APP_PORT > 65535:
            raise ValueError(f"Invalid APP_PORT: {self.APP_PORT}")


@lru_cache()
def get_settings() -> Settings:
    """
    Получение настроек с кэшированием.
    Использует lru_cache для избежания повторного чтения файла .env
    """
    settings = Settings()
    settings.validate()
    return settings


# Функция для демонстрации загруженных настроек
def print_settings_info():
    """Вывод информации о загруженных настройках (без секретных данных)"""
    settings = get_settings()

    print("=== LOADED SETTINGS ===")
    print(f"APP_NAME: {settings.APP_NAME}")
    print(f"APP_ENV: {settings.APP_ENV}")
    print(f"APP_PORT: {settings.APP_PORT}")
    print(f"DEBUG: {settings.DEBUG}")
    print(f"DB_HOST: {settings.DB_HOST}")
    print(f"DB_PORT: {settings.DB_PORT}")
    print(f"DB_NAME: {settings.DB_NAME}")
    print(f"DB_USER: {settings.DB_USER}")
    print(f"DB_PASSWORD: {'*' * len(settings.DB_PASSWORD)}")  # Скрываем пароль
    print(f"API_VERSION: {settings.API_VERSION}")
    print(f"API_PREFIX: {settings.API_PREFIX}")
    print(f"LOG_LEVEL: {settings.LOG_LEVEL}")
    print("=" * 25)


if __name__ == "__main__":
    # Для тестирования конфигурации
    try:
        print_settings_info()
        settings = get_settings()
        print(f"Database URL: {settings.DATABASE_URL_sync}")
        print(f"RabbitMQ URL: {settings.RABBITMQ_URL}")
        print("✓ Configuration loaded successfully!")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
