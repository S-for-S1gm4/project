# Event Planner API

Микросервисное приложение для планирования событий с использованием Docker Compose.

## Структура проекта

```
project/
├── .env                    # Единый файл переменных окружения
├── .env.template           # Пример конфигурации
├── docker-compose.yaml    # Конфигурация Docker Compose
├── README.md
├── app/                  # Основное приложение
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── database/
│   │   ├── config.py
│   │   └── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── event.py
│   │   └── transaction.py
│   ├── services/
│   │   ├── user_service.py
│   │   └── event_service.py
│   └── scripts/
│       ├── init_demo_data.py
│       └── test_system.py
├── nginx/               # Веб-прокси
│   ├── Dockerfile
│   └── nginx.conf
└── logs/               # Логи (создается автоматически)
    ├── nginx/
    └── app/
```

## Быстрый старт

### 1. Настройка окружения
```bash
# Клонируйте репозиторий
git clone <repository-url>
cd event-planner-api

# Создайте .env файл из примера
cp .env.example .env

# Отредактируйте .env файл под свои нужды
vim .env
```

### 2. Запуск проекта
```bash
# С использованием Make (если установлен)
make setup

# Или через docker-compose напрямую:
mkdir -p logs/nginx logs/app
docker-compose build
docker-compose up -d
```

### 3. Инициализация базы данных
```bash
# С помощью Make
make init-db
make init-demo

# Или напрямую
docker-compose exec app python -c "from database.database import init_db; init_db(drop_all=True)"
docker-compose exec app python scripts/init_demo_data.py
```

### 4. Проверка работы
- Веб-интерфейс: http://localhost
- Health Check: http://localhost/api/health
- RabbitMQ Management: http://localhost:15672 (admin/admin123)
- База данных: localhost:5432

## Конфигурация

Все настройки находятся в одном файле `.env` в корне проекта:

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

### Окружения:
- Development: `APP_ENV=development`, `DEBUG=true`
- Production: `APP_ENV=production`, `DEBUG=false`

## Сервисы

1. **app** - Основное приложение (Python + SQLModel)
   - Порт: 8080 (внутренний)
   - ORM с поддержкой пользователей, событий, транзакций
   - RESTful API

2. **nginx** - Веб-прокси
   - Порты: 80, 443 (внешние)
   - Балансировка нагрузки и статические файлы

3. **database** - PostgreSQL 15
   - Порт: 5432
   - Персистентные данные

4. **rabbitmq** - Очередь сообщений
   - Порты: 5672 (AMQP), 15672 (Management UI)
   - Персистентные очереди

## Команды управления

### С использованием Make:
```bash
make help           # Показать все команды
make setup          # Полная настройка проекта
make up             # Запустить сервисы
make down           # Остановить сервисы
make logs           # Показать логи
make init-db        # Инициализировать БД
make init-demo      # Создать демо-данные
make test-system    # Запустить тесты системы
make health         # Проверить здоровье сервисов
make clean          # Удалить все данные (ОСТОРОЖНО!)
```

### Через docker-compose напрямую:
```bash
# Основные команды
docker-compose build
docker-compose up -d
docker-compose down
docker-compose logs -f

# База данных
docker-compose exec app python -c "from database.database import init_db; init_db(drop_all=True)"
docker-compose exec app python scripts/init_demo_data.py
docker-compose exec app python scripts/test_system.py

# Подключение к сервисам
docker-compose exec database psql -U postgres -d event_planner
docker-compose exec app /bin/bash
```

## API Endpoints

### Основные:
- `GET /` - Главная страница с статистикой
- `GET /api/health` - Health check
- `GET /api/users` - Список пользователей
- `GET /api/events` - Список событий

### Пользователи:
- `GET /api/users/{id}/balance` - Баланс пользователя
- `GET /api/users/{id}/transactions` - История транзакций

## Модель данных

### User (Пользователь)
- Баланс, роль (user/admin)
- Система транзакций
- Хэширование паролей

### Event (Событие)
- Стоимость участия
- Ограничения по участникам
- Статусы событий

### Transaction (Транзакция)
- Пополнение/списание баланса
- Оплата событий
- История операций

## Тестирование функциональности

Система включает демо-данные и тесты:

```bash
# Создание демо-данных
docker-compose exec app python scripts/init_demo_data.py

# Тестирование системы
docker-compose exec app python scripts/test_system.py
```

**Демо-данные включают:**
- 4 пользователя (включая админа)
- Различные события (платные/бесплатные)
- Транзакции пополнения/списания
- Участие в событиях

## Безопасность

### Для продакшена:
1. Измените все пароли и ключи в `.env`
2. Используйте сильные пароли для БД и RabbitMQ
3. Настройте SSL сертификаты для Nginx
4. Отключите debug режим: `DEBUG=false`

### Генерация секретных ключей:
```bash
# Для SECRET_KEY и JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Troubleshooting

### Проблемы с правами доступа:
```bash
sudo chown -R $USER:$USER logs/
```

### Порты заняты:
Проверьте, что порты 80, 5432, 5672, 15672 не заняты

### Контейнеры не запускаются:
```bash
docker-compose logs <service_name>
```

### Проблемы с переменными окружения:
Убедитесь, что .env файл существует и содержит все необходимые переменные

## Мониторинг

- Логи приложения: `./logs/app/`
- Логи Nginx: `./logs/nginx/`
- Health checks: Встроенные в каждый сервис
- RabbitMQ Management UI: Мониторинг очередей

## Разработка

Для разработки файлы приложения автоматически синхронизируются через volumes:

```bash
# Изменения в коде сразу видны в контейнере
vim app/main.py

# Перезапуск только приложения
docker-compose restart app
```

## Логирование

Настройка через `.env`:
```bash
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
LOG_FILE=/app/logs/app.log   # Путь к файлу логов
```
