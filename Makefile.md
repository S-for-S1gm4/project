# Event Planner API - Makefile

.PHONY: help build up down logs clean restart status init-db test-system init-demo health

# Цвета для вывода
GREEN=\033[0;32m
YELLOW=\033[1;33m
RED=\033[0;31m
NC=\033[0m # No Color

help: ## Показать это сообщение помощи
	@echo "$(GREEN)Event Planner API - Доступные команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-15s$(NC) %s\n", $1, $2}'

check-env: ## Проверить наличие .env файла
	@echo "$(GREEN)🔍 Checking .env file...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ .env file not found!$(NC)"; \
		echo "$(YELLOW)📋 Copy .env.example to .env and configure it$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN) .env file found$(NC)"

build: check-env ## Собрать все Docker образы
	@echo "$(GREEN) Building Docker images...$(NC)"
	docker-compose build

up: check-env ## Запустить все сервисы
	@echo "$(GREEN) Starting all services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN) Services started!$(NC)"
	@echo "$(YELLOW) Application: http://localhost$(NC)"
	@echo "$(YELLOW) RabbitMQ Management: http://localhost:15672$(NC)"
	@echo "$(YELLOW) Database: localhost:5432$(NC)"

down: ## Остановить все сервисы
	@echo "$(YELLOW) Stopping all services...$(NC)"
	docker-compose down

logs: ## Показать логи всех сервисов
	docker-compose logs -f

logs-app: ## Показать логи только приложения
	docker-compose logs -f app

logs-db: ## Показать логи базы данных
	docker-compose logs -f database

logs-rabbitmq: ## Показать логи RabbitMQ
	docker-compose logs -f rabbitmq

status: ## Показать статус всех сервисов
	@echo "$(GREEN) Services status:$(NC)"
	docker-compose ps

restart: ## Перезапустить все сервисы
	@echo "$(YELLOW) Restarting services...$(NC)"
	docker-compose restart

rebuild: ## Пересобрать и перезапустить приложение
	@echo "$(GREEN)🔨 Rebuilding application...$(NC)"
	docker-compose build app
	docker-compose up -d app

clean: ## Остановить и удалить все контейнеры, сети и volumes
	@echo "$(RED)🗑️  Warning: This will remove all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --remove-orphans; \
		docker system prune -f; \
		echo "$(GREEN) Cleanup completed$(NC)"; \
	else \
		echo "$(YELLOW)❌ Cleanup cancelled$(NC)"; \
	fi

init-db: ## Инициализировать базу данных (пересоздать таблицы)
	@echo "$(GREEN)  Initializing database...$(NC)"
	docker-compose exec app python -c "from database.database import init_db; init_db(drop_all=True)"
	@echo "$(GREEN) Database initialized$(NC)"

init-demo: ## Заполнить базу данных демо-данными
	@echo "$(GREEN) Creating demo data...$(NC)"
	docker-compose exec app python scripts/init_demo_data.py
	@echo "$(GREEN) Demo data created$(NC)"

test-system: ## Запустить тесты системы
	@echo "$(GREEN) Running system tests...$(NC)"
	docker-compose exec app python scripts/test_system.py

health: ## Проверить здоровье всех сервисов
	@echo "$(GREEN) Health check:$(NC)"
	@echo "$(YELLOW)Application:$(NC)"
	@curl -s http://localhost/api/health | python -m json.tool || echo "❌ App not responding"
	@echo "\n$(YELLOW)Nginx:$(NC)"
	@curl -s http://localhost/nginx-health || echo "❌ Nginx not responding"
	@echo "\n$(YELLOW)Database:$(NC)"
	@docker-compose exec -T database pg_isready -U postgres || echo "❌ Database not ready"
	@echo "\n$(YELLOW)RabbitMQ:$(NC)"
	@curl -s http://localhost:15672/api/overview -u admin:admin123 > /dev/null && echo " RabbitMQ OK" || echo "❌ RabbitMQ not responding"

db-shell: ## Подключиться к базе данных
	@echo "$(GREEN) Connecting to database...$(NC)"
	docker-compose exec database psql -U postgres -d event_planner

app-shell: ## Подключиться к контейнеру приложения
	@echo "$(GREEN) Connecting to app container...$(NC)"
	docker-compose exec app /bin/bash

setup: check-env build up init-db init-demo ## Полная настройка проекта (сборка, запуск, инициализация)
	@echo "$(GREEN) Project setup completed!$(NC)"
	@echo "$(YELLOW) Visit: http://localhost$(NC)"

# Команды для создания example файлов
create-env-example: ## Создать пример .env файла
	@echo "$(GREEN) Creating .env.example file...$(NC)"
	@if [ ! -f .env.example ]; then \
		cp .env .env.example 2>/dev/null || echo "# Copy from .env artifact and configure" > .env.example; \
	fi
	@echo "$(GREEN) .env.example created$(NC)"
	@echo "$(YELLOW) Configure .env file before running$(NC)"

show-env: ## Показать текущие переменные окружения (без секретов)
	@echo "$(GREEN)🔧 Current environment variables:$(NC)"
	@if [ -f .env ]; then \
		echo "$(YELLOW)From .env file:$(NC)"; \
		grep -E "^[A-Z_]+" .env | grep -v "PASSWORD\|SECRET\|KEY" || true; \
		echo "$(RED)Secrets are hidden$(NC)"; \
	else \
		echo "$(RED)No .env file found$(NC)"; \
	fi

# Команды для разработки
dev-logs: ## Логи для разработки (только app и database)
	docker-compose logs -f app database

dev-restart: ## Быстрый перезапуск приложения для разработки
	docker-compose restart app

# Команды для создания директорий
create-dirs: ## Создать необходимые директории
	@echo "$(GREEN) Creating directories...$(NC)"
	mkdir -p logs/nginx
	mkdir -p app/logs
	@echo "$(GREEN) Directories created$(NC)"

# Значение по умолчанию
.DEFAULT_GOAL := help
