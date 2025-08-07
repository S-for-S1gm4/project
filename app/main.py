"""
Основной файл FastAPI приложения для Event Planner API
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import logging

# Импорты ваших модулей
from database.database import init_db, test_connection
from database.config import get_settings
from routes.auth import auth_router
from routes.user import user_router
from routes.events import event_router
from services.user_service import UserService
from services.event_service import EventService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем настройки
settings = get_settings()

# Создаем FastAPI приложение
app = FastAPI(
    title=settings.APP_NAME,
    description="Event Planner API with ML predictions and user management",
    version=settings.API_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(event_router)

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info(f"Starting {settings.APP_NAME}")

    # Проверяем подключение к БД
    if not test_connection():
        logger.error("Database connection failed!")
        raise Exception("Cannot connect to database")

    logger.info("Database connection successful")
    logger.info(f"FastAPI server starting on port {settings.APP_PORT}")
    logger.info(f"API Documentation: http://localhost:{settings.APP_PORT}/docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    logger.info("Shutting down FastAPI application")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Главная страница с информацией о системе"""
    try:
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
                <td>${user.balance}</td>
                <td>{user.role}</td>
            </tr>
            """

        events_html = ""
        for event in events[:5]:  # Показываем первые 5 событий
            events_html += f"""
            <tr>
                <td>{event.id}</td>
                <td>{event.title}</td>
                <td>${event.cost}</td>
                <td>{event.current_participants}</td>
                <td>{event.status}</td>
            </tr>
            """

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        users_html = f"<tr><td colspan='5'>Error loading users: {e}</td></tr>"
        events_html = f"<tr><td colspan='5'>Error loading events: {e}</td></tr>"
        users = []
        events = []
        active_events = []

    html_content = f"""
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
            <p><strong>Status:</strong> Running on FastAPI</p>
            <p><strong>Environment:</strong> {settings.APP_ENV}</p>
            <p><strong>Database:</strong> Connected to {settings.DB_HOST}:{settings.DB_PORT}</p>

            <div class="config-info">
                <h3>FastAPI Configuration</h3>
                <p><strong>App Port:</strong> {settings.APP_PORT}</p>
                <p><strong>API Version:</strong> {settings.API_VERSION}</p>
                <p><strong>Debug Mode:</strong> {'Enabled' if settings.DEBUG else 'Disabled'}</p>
                <p><strong>Documentation:</strong> <a href="/docs">Swagger UI</a> | <a href="/redoc">ReDoc</a></p>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <h3>Users</h3>
                    <p><strong>{len(users)}</strong> total users</p>
                    <p><strong>${sum(u.balance for u in users):.2f}</strong> total balance</p>
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
                <a href="/docs">API Documentation</a>
                <a href="/api/health">Health Check</a>
                <a href="/api/auth/register">Register</a>
                <a href="/api/auth/login">Login</a>
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

    return HTMLResponse(content=html_content)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    db_status = test_connection()

    return JSONResponse(
        status_code=200 if db_status else 503,
        content={
            "status": "healthy" if db_status else "unhealthy",
            "app_name": settings.APP_NAME,
            "version": settings.API_VERSION,
            "environment": settings.APP_ENV,
            "database": "connected" if db_status else "disconnected",
            "debug_mode": settings.DEBUG,
            "framework": "FastAPI"
        }
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Обработчик 404 ошибок"""
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "path": str(request.url)}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Обработчик внутренних ошибок"""
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# Для запуска через uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
