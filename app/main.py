import os
import sys
import logging
from database.database import init_db, test_connection
from database.config import get_settings, print_settings_info
from services.user_service import UserService
from services.event_service import EventService
import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment():
    """Проверка переменных окружения"""
    logger.info("Checking environment variables...")

    try:
        settings = get_settings()
        logger.info("SUCCESS: All required environment variables are loaded")

        # Показываем загруженные настройки (без секретов)
        if settings.DEBUG:
            print_settings_info()

        return settings
    except Exception as e:
        logger.error(f"ERROR: Environment check failed: {e}")
        logger.error("Please check your .env file and ensure all required variables are set")
        return None


def setup_database():
    """Инициализация подключения к базе данных"""
    try:
        settings = get_settings()
        logger.info(f"Setting up database connection to {settings.DB_HOST}:{settings.DB_PORT}")

        # Проверяем подключение
        if test_connection():
            logger.info("SUCCESS: Database connection successful")
            return True
        else:
            logger.error("ERROR: Database connection failed")
            return False

    except Exception as e:
        logger.error(f"ERROR: Database setup failed: {e}")
        return False


def setup_rabbitmq():
    """Инициализация подключения к RabbitMQ"""
    try:
        settings = get_settings()
        logger.info(f"RabbitMQ configuration: {settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}")
        # Здесь будет код инициализации подключения к RabbitMQ
        logger.info("SUCCESS: RabbitMQ configuration loaded")
        return settings.RABBITMQ_URL
    except Exception as e:
        logger.error(f"ERROR: RabbitMQ setup failed: {e}")
        return None


class APIHandler(http.server.SimpleHTTPRequestHandler):
    """Простой HTTP обработчик для демонстрации API"""

    def do_GET(self):
        """Обработка GET запросов"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        try:
            if path == '/':
                self.serve_home_page()
            elif path == '/api/users':
                self.serve_users()
            elif path == '/api/events':
                self.serve_events()
            elif path == '/api/health':
                self.serve_health_check()
            elif path.startswith('/api/users/') and path.endswith('/transactions'):
                user_id = int(path.split('/')[-2])
                self.serve_user_transactions(user_id)
            elif path.startswith('/api/users/') and path.endswith('/balance'):
                user_id = int(path.split('/')[-2])
                self.serve_user_balance(user_id)
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            logger.error(f"Error handling request {path}: {e}")
            self.send_error(500, f"Internal Server Error: {e}")

    def serve_health_check(self):
        """Health check endpoint"""
        try:
            settings = get_settings()
            db_status = test_connection()

            health_data = {
                'status': 'healthy' if db_status else 'unhealthy',
                'app_name': settings.APP_NAME,
                'version': settings.API_VERSION,
                'environment': settings.APP_ENV,
                'database': 'connected' if db_status else 'disconnected',
                'debug_mode': settings.DEBUG
            }

            status_code = 200 if db_status else 503
            self.send_json_response(health_data, status=status_code)

        except Exception as e:
            self.send_json_response({
                'status': 'error',
                'error': str(e)
            }, status=500)

    def serve_home_page(self):
        """Главная страница с информацией о системе"""
        try:
            settings = get_settings()

            # Получаем статистику
            users = UserService.get_all_users()
            events = EventService.get_all_events()
            active_events = EventService.get_active_events()

            users_html = ""
            for user in users[:5]:  # Показываем первых 5 пользователей
                users_html += f"""
                <tr>
                    <td>{user.id}</td>
                    <td>{user.username}</td>
                    <td>{user.email}</td>
                    <td>{user.balance}</td>
                    <td>{user.role}</td>
                </tr>
                """

            events_html = ""
            for event in events[:5]:  # Показываем первые 5 событий
                events_html += f"""
                <tr>
                    <td>{event.id}</td>
                    <td>{event.title}</td>
                    <td>{event.cost}</td>
                    <td>{event.current_participants}</td>
                    <td>{event.status}</td>
                </tr>
                """

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            settings = get_settings()
            users_html = f"<tr><td colspan='5'>Error loading users: {e}</td></tr>"
            events_html = f"<tr><td colspan='5'>Error loading events: {e}</td></tr>"
            users = []
            events = []
            active_events = []

        response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{settings.APP_NAME}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #f5f5f5; padding: 20px; border-radius: 8px; flex: 1; }}
                .config-info {{ background: #e7f3ff; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .api-links {{ margin: 20px 0; }}
                .api-links a {{ display: inline-block; margin: 5px 10px 5px 0; padding: 8px 16px;
                              background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
                .api-links a:hover {{ background: #0056b3; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{settings.APP_NAME}</h1>
                <p><strong>Status:</strong> Running</p>
                <p><strong>Environment:</strong> {settings.APP_ENV}</p>
                <p><strong>Database:</strong> Connected to {settings.DB_HOST}:{settings.DB_PORT}</p>

                <div class="config-info">
                    <h3>Configuration</h3>
                    <p><strong>App Port:</strong> {settings.APP_PORT}</p>
                    <p><strong>API Version:</strong> {settings.API_VERSION}</p>
                    <p><strong>Debug Mode:</strong> {'Enabled' if settings.DEBUG else 'Disabled'}</p>
                    <p><strong>Log Level:</strong> {settings.LOG_LEVEL}</p>
                </div>

                <div class="stats">
                    <div class="stat-card">
                        <h3>Users</h3>
                        <p><strong>{len(users)}</strong> total users</p>
                        <p><strong>{sum(u.balance for u in users):.2f}</strong> total balance</p>
                    </div>
                    <div class="stat-card">
                        <h3>Events</h3>
                        <p><strong>{len(events)}</strong> total events</p>
                        <p><strong>{len(active_events)}</strong> active events</p>
                    </div>
                    <div class="stat-card">
                        <h3>Participation</h3>
                        <p><strong>{sum(e.current_participants for e in events)}</strong> total participants</p>
                    </div>
                </div>

                <div class="api-links">
                    <h3>API Endpoints:</h3>
                    <a href="/api/health">Health Check</a>
                    <a href="/api/users">All Users</a>
                    <a href="/api/events">All Events</a>
                    {f'<a href="/api/users/{users[0].id}/transactions">User Transactions</a>' if users else ''}
                    {f'<a href="/api/users/{users[0].id}/balance">User Balance</a>' if users else ''}
                </div>

                <h2>Recent Users</h2>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Balance</th>
                        <th>Role</th>
                    </tr>
                    {users_html}
                </table>

                <h2>Recent Events</h2>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Title</th>
                        <th>Cost</th>
                        <th>Participants</th>
                        <th>Status</th>
                    </tr>
                    {events_html}
                </table>
            </div>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(response.encode())

    def serve_users(self):
        """API для получения всех пользователей"""
        try:
            users = UserService.get_all_users()
            users_data = []
            for user in users:
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.full_name,
                    'balance': user.balance,
                    'role': user.role,
                    'is_active': user.is_active,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                })

            self.send_json_response(users_data)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

    def serve_events(self):
        """API для получения всех событий"""
        try:
            events = EventService.get_all_events()
            events_data = []
            for event in events:
                events_data.append({
                    'id': event.id,
                    'title': event.title,
                    'description': event.description,
                    'cost': event.cost,
                    'max_participants': event.max_participants,
                    'current_participants': event.current_participants,
                    'status': event.status,
                    'creator_id': event.creator_id,
                    'event_date': event.event_date.isoformat() if event.event_date else None,
                    'created_at': event.created_at.isoformat() if event.created_at else None
                })

            self.send_json_response(events_data)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

    def serve_user_transactions(self, user_id: int):
        """API для получения транзакций пользователя"""
        try:
            transactions = UserService.get_user_transactions(user_id)
            transactions_data = []
            for transaction in transactions:
                transactions_data.append({
                    'id': transaction.id,
                    'amount': transaction.amount,
                    'transaction_type': transaction.transaction_type,
                    'status': transaction.status,
                    'description': transaction.description,
                    'created_at': transaction.created_at.isoformat() if transaction.created_at else None,
                    'completed_at': transaction.completed_at.isoformat() if transaction.completed_at else None
                })

            self.send_json_response(transactions_data)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

    def serve_user_balance(self, user_id: int):
        """API для получения баланса пользователя"""
        try:
            user = UserService.get_user_by_id(user_id)
            if not user:
                self.send_json_response({'error': 'User not found'}, status=404)
                return

            balance_data = {
                'user_id': user.id,
                'username': user.username,
                'balance': user.balance,
                'last_updated': user.updated_at.isoformat() if user.updated_at else None
            }

            self.send_json_response(balance_data)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

    def send_json_response(self, data, status=200):
        """Отправка JSON ответа"""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = json.dumps(data, indent=2, ensure_ascii=False)
        self.wfile.write(response.encode('utf-8'))


def main():
    """Основная функция приложения"""
    logger.info("Starting Event Planner API...")

    # Проверяем переменные окружения
    settings = check_environment()
    if not settings:
        logger.error("Failed to load configuration. Exiting.")
        sys.exit(1)

    logger.info(f"Application: {settings.APP_NAME}")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Port: {settings.APP_PORT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Инициализируем подключения
    if not setup_database():
        logger.error("Failed to setup database connection. Exiting.")
        sys.exit(1)

    rabbitmq_url = setup_rabbitmq()
    if not rabbitmq_url:
        logger.warning("RabbitMQ setup failed, but continuing...")

    # Запускаем HTTP сервер
    try:
        logger.info(f"Starting HTTP server on port {settings.APP_PORT}...")

        with socketserver.TCPServer(("", settings.APP_PORT), APIHandler) as httpd:
            logger.info(f"Server started at http://localhost:{settings.APP_PORT}")
            logger.info(f"Health check: http://localhost:{settings.APP_PORT}/api/health")
            httpd.serve_forever()

    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
