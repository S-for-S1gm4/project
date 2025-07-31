# Event Planner API

Микросервисное приложение для планирования событий с использованием Docker Compose.

## Структура проекта

```
project/
├── docker-compose.yaml     # Конфигурация Docker Compose
├── .env                    # Глобальные переменные окружения
├── Makefile               # Команды для управления проектом
├── app/                   # Основное приложение
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env              # Переменные окружения приложения
│   ├── main.py
│   └── models/
│       ├── __init__.py
│       ├── user.py
│       └── event.py
├── nginx/                 # Веб-прокси
│   ├── Dockerfile
│   └── nginx.conf
└── volumes/              # Постоянные данные
    ├── rabbitmq/
    └── postgres/
```

## Сервисы

1. **app** - Основное приложение (Python)
   - Порт: 8080 (внутренний)
   - Конфигурация через env_file
   - Исходные файлы подключены через volumes

2. **web-proxy** - Nginx прокси
   - Порты: 80, 443 (внешние)
   - Зависит от сервиса app
   - Проксирует запросы к app

3. **rabbitmq** - Очередь сообщений
   - Порты: 5672 (AMQP), 15672 (Management UI)
   - Данные сохраняются в volumes/rabbitmq
   - Автоматический перезапуск при сбоях

4. **database** - PostgreSQL
   - Порт: 5432
   - Данные сохраняются в volumes/postgres

## Установка и запуск

### Предварительные требования
- Docker
- Docker Compose
- Make (опционально)

### Первый запуск

1. Клонируйте репозиторий
2. Создайте директории для volumes:
   ```bash
   mkdir -p volumes/rabbitmq volumes/postgres
   ```

3. Запустите сервисы:
   ```bash
   # С использованием Make
   make build
   make up

   # Или напрямую через docker-compose
   docker-compose build
   docker-compose up -d
   ```

### Проверка работы

1. Веб-интерфейс: http://localhost
2. RabbitMQ Management: http://localhost:15672
   - Username: admin
   - Password: admin123

### Полезные команды

```bash
# Посмотреть логи всех сервисов
make logs

# Посмотреть логи конкретного сервиса
docker-compose logs -f app

# Остановить все сервисы
make down

# Очистить все данные (ВНИМАНИЕ: удалит БД и очереди)
make clean

# Подключиться к БД
make db-shell
```

## Переменные окружения

### app/.env
- `APP_NAME` - Название приложения
- `APP_PORT` - Порт приложения
- `DATABASE_URL` - URL подключения к БД
- `RABBITMQ_URL` - URL подключения к RabbitMQ
- `DEBUG` - Режим отладки

## Разработка

При разработке файлы приложения автоматически синхронизируются благодаря volumes. Изменения в коде будут видны внутри контейнера.

Для применения изменений в Dockerfile или зависимостях:
```bash
make rebuild
```

## Troubleshooting

### Проблемы с правами доступа к volumes
```bash
sudo chown -R $USER:$USER volumes/
```

### Порты уже заняты
Проверьте, что порты 80, 443, 5432, 5672, 15672 не заняты другими приложениями.

### Контейнеры не запускаются
Проверьте логи:
```bash
docker-compose logs <service_name>
```