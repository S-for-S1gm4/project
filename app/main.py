import os
import sys
import logging
from models.user import User
from models.event import Event

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_database():
    """Инициализация подключения к базе данных"""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        logger.info(f"Database URL configured: {db_url.split('@')[1]}")  # Скрываем пароль
    else:
        logger.warning("DATABASE_URL not set")
    # Здесь будет код инициализации SQLAlchemy
    return db_url

def setup_rabbitmq():
    """Инициализация подключения к RabbitMQ"""
    rabbitmq_url = os.getenv('RABBITMQ_URL')
    if rabbitmq_url:
        logger.info("RabbitMQ URL configured")
    else:
        logger.warning("RABBITMQ_URL not set")
    # Здесь будет код инициализации подключения к RabbitMQ
    return rabbitmq_url

def main():
    """Основная функция приложения"""
    logger.info("Starting Event Planner API...")

    # Проверяем переменные окружения
    app_name = os.getenv('APP_NAME', 'EventPlannerAPI')
    app_port = int(os.getenv('APP_PORT', '8080'))
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'

    logger.info(f"Application: {app_name}")
    logger.info(f"Port: {app_port}")
    logger.info(f"Debug mode: {debug_mode}")

    # Инициализируем подключения
    db_url = setup_database()
    rabbitmq_url = setup_rabbitmq()

    # Тестовые данные
    test_user = User(id=1, email='test@mail.ru')
    test_event = Event(
        id=1,
        title='Test Event',
        description='Test description',
        creator=test_user
    )

    logger.info(f"Created test user: {test_user}")
    logger.info(f"Created test event: {test_event}")

    # Здесь должен быть запуск веб-сервера
    # Для демонстрации просто создадим простой HTTP сервер
    if db_url and rabbitmq_url:
        logger.info(f"Starting HTTP server on port {app_port}...")
        try:
            import http.server
            import socketserver

            class SimpleHandler(http.server.SimpleHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    response = f"""
                    <html>
                    <body>
                        <h1>{app_name}</h1>
                        <p>Status: Running</p>
                        <p>Database: Connected</p>
                        <p>RabbitMQ: Connected</p>
                        <p>Test User: {test_user}</p>
                        <p>Test Event: {test_event}</p>
                    </body>
                    </html>
                    """
                    self.wfile.write(response.encode())

            with socketserver.TCPServer(("", app_port), SimpleHandler) as httpd:
                logger.info(f"Server started at http://localhost:{app_port}")
                httpd.serve_forever()

        except KeyboardInterrupt:
            logger.info("Shutting down server...")
            sys.exit(0)
    else:
        logger.error("Failed to initialize required services")
        sys.exit(1)

if __name__ == "__main__":
    main()
