# Event Planner API - Structured Architecture

Микросервисное приложение для планирования событий с **чистой архитектурой** и разделением слоев.

## 🏗️ Архитектура проекта

### Принципы разделения:
- **Schemas** - Контракты API (Pydantic модели)
- **Models** - Сущности базы данных (SQLModel)
- **Services** - Бизнес-логика
- **Routes** - HTTP эндпоинты (контроллеры)
- **Core** - Общие утилиты

```
app/
├── main.py                    # Точка входа FastAPI
├── requirements.txt
├── Dockerfile
├── schemas/                   # Pydantic схемы (API contracts)
│   ├── __init__.py
│   ├── auth.py               # Схемы аутентификации
│   ├── user.py               # Схемы пользователей
│   └── event.py              # Схемы событий
├── models/                    # SQLModel модели (Database entities)
│   ├── __init__.py
│   ├── user.py               # Модель пользователя
│   ├── event.py              # Модель события
│   └── transaction.py        # Модель транзакции
├── services/                  # Бизнес-логика
│   ├── __init__.py
│   ├── user_service.py       # Логика работы с пользователями
│   └── event_service.py      # Логика работы с событиями
├── routes/                    # HTTP эндпоинты (только routing)
│   ├── __init__.py
│   ├── auth.py               # Маршруты аутентификации
│   ├── user.py               # Маршруты пользователей
│   └── events.py             # Маршруты событий
├── core/                      # Общие утилиты
│   ├── __init__.py
│   ├── auth.py               # Утилиты аутентификации
│   └── exceptions.py         # Кастомные исключения
├── database/                  # Конфигурация БД
│   ├── __init__.py
│   ├── config.py             # Настройки
│   └── database.py           # Подключение к БД
└── scripts/                   # Вспомогательные скрипты
    ├── __init__.py
    ├── init_demo_data.py      # Создание демо-данных
    └── test_system.py         # Тестирование системы
```

## 📁 Описание слоев

### 1. **Schemas (API Contracts)**
Определяют структуру данных для API:
- Валидация входящих запросов
- Формат ответов API
- Документация Swagger
- Независимы от базы данных

### 2. **Models (Database Entities)**
SQLModel модели для работы с БД:
- Определение таблиц
- Связи между сущностями
- Бизнес-методы моделей
- Валидация на уровне БД

### 3. **Services (Business Logic)**
Основная бизнес-логика приложения:
- Операции с данными
- Бизнес-правила
- Валидация данных
- Взаимодействие с БД

### 4. **Routes (Controllers)**
HTTP эндпоинты и роутинг:
- Обработка HTTP запросов
- Валидация параметров
- Вызов сервисов
- Формирование ответов

### 5. **Core (Common Utilities)**
Общие компоненты:
- Аутентификация/авторизация
- Кастомные исключения
- Утилиты
- Middleware

## 🚀 Быстрый старт

### 1. Настройка окружения
```bash
# Клонируйте репозиторий
git clone <repository-url>
cd event-planner-api

# Создайте .env файл из примера
cp .env.template .env

# Отредактируйте .env файл
vim .env
```

### 2. Запуск с Docker Compose
```bash
# Полная настройка
make setup

# Или через docker-compose
mkdir -p logs/nginx logs/app
docker-compose build
docker-compose up -d
```

### 3. Инициализация данных
```bash
# Инициализация БД и демо-данных
make init-db
make init-demo

# Или напрямую
docker-compose exec app python -c "from database.database import init_db; init_db(drop_all=True)"
docker-compose exec app python scripts/init_demo_data.py
```

### 4. Проверка работы
- **Главная страница:** http://localhost
- **API Документация:** http://localhost/docs
- **Health Check:** http://localhost/api/health
- **RabbitMQ Management:** http://localhost:15672

## 🔧 Преимущества новой архитектуры

### ✅ Разделение ответственности
- **Схемы** отвечают только за валидацию API
- **Модели** - только за структуру БД
- **Сервисы** - только за бизнес-логику
- **Роуты** - только за HTTP обработку

### ✅ Легкость тестирования
```python
# Тестирование бизнес-логики независимо от API
def test_user_service():
    user = UserService.create_user(...)
    assert user.balance == 0.0

# Тестирование API независимо от бизнес-логики
def test_user_endpoint():
    response = client.post("/api/users", json=...)
    assert response.status_code == 200
```

### ✅ Переиспользование компонентов
```python
# Сервисы можно использовать в разных местах
from services.user_service import UserService

# В API эндпоинте
user = UserService.create_user(...)

# В Telegram боте
user = UserService.create_user(...)

# В CLI скрипте
user = UserService.create_user(...)
```

### ✅ Упрощение изменений
- Изменение API схем не влияет на БД
- Изменение бизнес-логики не влияет на роуты
- Добавление новых эндпоинтов не требует изменения сервисов

## 📊 Конфигурация

Все настройки в одном файле `.env`:

```bash
# Application settings
APP_NAME=EventPlannerAPI
APP_ENV=development
APP_PORT=8080
DEBUG=true

# Database configuration
DB_HOST=database
DB_PORT=5432
DB_NAME=event_planner
DB_USER=postgres
DB_PASSWORD=postgres123

# Security (ОБЯЗАТЕЛЬНО ИЗМЕНИТЬ В ПРОДАКШЕНЕ!)
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
```

## 🌐 API Endpoints

### Аутентификация (`/api/auth`)
```http
POST /api/auth/register    # Регистрация
POST /api/auth/login       # Вход
POST /api/auth/refresh     # Обновление токена
POST /api/auth/logout      # Выход
```

### Пользователи (`/api/users`)
```http
GET  /api/users/profile              # Профиль
PUT  /api/users/profile              # Обновление профиля
GET  /api/users/balance              # Баланс
POST /api/users/balance              # Пополнение
GET  /api/users/transactions         # История транзакций
GET  /api/users/transactions/summary # Сводка транзакций
GET  /api/users/events               # Мои события
GET  /api/users/events/stats         # Статистика событий
GET  /api/users/activity             # Журнал активности
DELETE /api/users/profile            # Удаление аккаунта
```

### События (`/api/events`)
```http
GET  /api/events                     # Список событий
GET  /api/events/{id}                # Конкретное событие
POST /api/events                     # Создание события
PUT  /api/events/{id}                # Обновление события
POST /api/events/{id}/join           # Присоединение к событию
POST /api/events/{id}/activate       # Активация события
POST /api/events/predict             # ML предсказание
GET  /api/events/predictions/history # История предсказаний
GET  /api/events/stats/overview      # Общая статистика
GET  /api/events/{id}/participants   # Участники события
GET  /api/events/search              # Поиск событий
```

## 🧪 Тестирование

### Системные тесты
```bash
# Тестирование всей системы
make test-system

# Или напрямую
docker-compose exec app python scripts/test_system.py
```

### Юнит тесты (пример структуры)
```
tests/
├── test_services/
│   ├── test_user_service.py
│   └── test_event_service.py
├── test_routes/
│   ├── test_auth.py
│   ├── test_users.py
│   └── test_events.py
└── test_models/
    ├── test_user.py
    └── test_event.py
```

## 🐳 Docker Services

### app (FastAPI приложение)
- **Порт:** 8080
- **Функции:** API, бизнес-логика
- **Архитектура:** Разделенные слои

### nginx (Веб-прокси)
- **Порты:** 80, 443
- **Функции:** Балансировка, статика

### database (PostgreSQL)
- **Порт:** 5432
- **Функции:** Хранение данных

### rabbitmq (Очередь сообщений)
- **Порты:** 5672, 15672
- **Функции:** Асинхронные задачи

## 📈 Мониторинг

### Health Checks
```http
GET /api/health
```

```json
{
  "status": "healthy",
  "app_name": "EventPlannerAPI",
  "database": "connected",
  "architecture": "separated_layers"
}
```

### Логирование
- **Приложение:** `./logs/app/`
- **Nginx:** `./logs/nginx/`
- **Уровни:** DEBUG, INFO, WARNING, ERROR

## 🛡️ Безопасность

### Для продакшена:
1. **Смените пароли:** Все пароли в `.env`
2. **JWT ключи:** Используйте криптостойкие ключи
3. **SSL:** Настройте HTTPS в Nginx
4. **Debug:** Отключите `DEBUG=false`
5. **CORS:** Ограничьте домены

### Генерация ключей:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🔄 Команды управления

### Make команды:
```bash
make help           # Показать все команды
make setup          # Полная настройка
make up             # Запустить сервисы
make down           # Остановить сервисы
make logs           # Показать логи
make health         # Проверить здоровье
make clean          # Удалить данные
```

### Docker Compose:
```bash
# Основные команды
docker-compose build
docker-compose up -d
docker-compose down
docker-compose logs -f

# Подключение к сервисам
docker-compose exec app /bin/bash
docker-compose exec database psql -U postgres -d event_planner
```

## 📝 Разработка

### Добавление нового эндпоинта:
1. **Схемы:** Создать Pydantic модели в `schemas/`
2. **Сервис:** Добавить бизнес-логику в `services/`
3. **Роут:** Создать эндпоинт в `routes/`
4. **Тесты:** Написать тесты для всех слоев

### Пример:
```python
# 1. schemas/notification.py
class NotificationRequest(BaseModel):
    message: str
    user_id: int

# 2. services/notification_service.py
class NotificationService:
    @staticmethod
    def send_notification(user_id: int, message: str):
        # Бизнес-логика отправки

# 3. routes/notifications.py
@router.post("/notifications")
async def send_notification(data: NotificationRequest):
    NotificationService.send_notification(data.user_id, data.message)
    return {"status": "sent"}
```

## 🤝 Вклад в проект

1. **Fork** репозитория
2. **Создайте** feature ветку
3. **Следуйте** архитектурным принципам
4. **Добавьте** тесты
5. **Отправьте** Pull Request

## 📚 Дополнительные ресурсы

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [Clean Architecture Principles](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

## 🎯 Ключевые улучшения архитектуры

### ✅ Решенные проблемы:
- ❌ **Было:** Смешанные схемы, бизнес-логика и роуты в одном файле
- ✅ **Стало:** Четкое разделение по слоям и ответственности

- ❌ **Было:** Сложность тестирования и изменения кода
- ✅ **Стало:** Легкое unit-тестирование каждого слоя отдельно

- ❌ **Было:** Дублирование кода между разными модулями
- ✅ **Стало:** Переиспользование сервисов и утилит

- ❌ **Было:** Плохая читаемость и сложность навигации
- ✅ **Стало:** Понятная структура проекта и назначение файлов

### 🚀 Готово к продакшену:
- Proper error handling с кастомными исключениями
- Структурированное логирование
- Валидация данных на всех уровнях
- Безопасная аутентификация
- Comprehensive API documentation
- Health checks и мониторинг
