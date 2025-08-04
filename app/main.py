import os
import sys
import logging
from database.database import init_db, test_connection
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


class APIHandler(http.server.SimpleHTTPRequestHandler):
    """Простой HTTP обработчик для демонстрации API"""

    def do_GET(self):
        """Обработка GET запросов"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        try:
            if path == '/':
                self.serve_home_page()
            elif path == '/api/users':
                self.serve_users()
            elif path == '/api/events':
                self.serve_events()
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

    def serve_home_page(self):
        """Главная страница с информацией о системе"""
        app_name = os.getenv('APP_NAME', 'EventPlannerAPI')

        # Получаем статистику
        try:
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
            users_html = f"<tr><td colspan='5'>Error: {e}</td></tr>"
            events_html = f"<tr><td colspan='5'>Error: {e}</td></tr>"
            users = []
            events = []
            active_events = []

        response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{app_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #f5f5f5; padding: 20px; border-radius: 8px; flex: 1; }}
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
                <h1>{app_name}</h1>
                <p><strong>Status:</strong> ✅ Running</p>
                <p><strong>Database:</strong> ✅ Connected</p>

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

            self.
