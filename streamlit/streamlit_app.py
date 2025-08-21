"""
Веб-интерфейс на Streamlit для Event Planner API.
Приложение предоставляет полнофункциональный интерфейс для взаимодействия
с бэкенд-сервисом Event Planner.
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, Any
import time

# --- КОНФИГУРАЦИЯ ---
# Для запуска через Docker Compose используется "http://nginx/api"
# Для локального запуска (FastAPI на порту 8080) используется "http://localhost:8080/api"
API_BASE_URL = "http://nginx/api"
APP_TITLE = "Event Planner - Web Interface"

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ГЛОБАЛЬНЫЕ СТИЛИ ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #667eea;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        border-radius: 0.5rem;
    }
    .stMetric {
        border-left: 5px solid #667eea;
        padding-left: 15px;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)


# --- КЛИЕНТ ДЛЯ РАБОТЫ С API ---
class APIClient:
    """Клиент для работы с Event Planner API"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    def set_auth_token(self, token: str):
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def clear_auth_token(self):
        self.session.headers.pop("Authorization", None)

    def request(self, method: str, endpoint: str, **kwargs) -> Dict:
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            if response.status_code in [200, 201, 202]:
                return {"success": True, "data": response.json()}
            else:
                error_data = response.json() if response.content else {"detail": "Unknown error"}
                return {"success": False, "error": error_data.get("detail", "API Error"), "status_code": response.status_code}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Connection Error: {e}"}

    # Методы API
    def register(self, email: str, username: str, password: str, full_name: str = None) -> Dict:
        return self.request("POST", "/auth/register", json={"email": email, "username": username, "password": password, "full_name": full_name})
    def login(self, email: str, password: str) -> Dict:
        return self.request("POST", "/auth/login", json={"email": email, "password": password})
    def get_profile(self) -> Dict:
        return self.request("GET", "/users/profile")
    def add_balance(self, amount: float, description: str) -> Dict:
        return self.request("POST", "/users/balance", json={"amount": amount, "description": description})
    def get_transactions(self, limit: int = 100) -> Dict:
        return self.request("GET", f"/users/transactions?limit={limit}")
    def get_transaction_summary(self) -> Dict:
        return self.request("GET", "/users/transactions/summary")
    def get_my_events(self) -> Dict:
        return self.request("GET", "/users/events")
    def get_events_stats(self) -> Dict:
        return self.request("GET", "/users/events/stats")
    def get_events(self, **params) -> Dict:
        return self.request("GET", "/events", params=params)
    def create_event(self, **data) -> Dict:
        return self.request("POST", "/events/", json=data)
    def join_event(self, event_id: int) -> Dict:
        return self.request("POST", f"/events/{event_id}/join")
    def activate_event(self, event_id: int) -> Dict:
        return self.request("POST", f"/events/{event_id}/activate")
    def predict_participation(self, event_id: int, user_features: Dict) -> Dict:
        return self.request("POST", "/events/predict", json={"event_id": event_id, "user_features": user_features})
    def get_events_overview(self) -> Dict:
        return self.request("GET", "/events/stats/overview")
    def search_events(self, query: str, limit: int = 10) -> Dict:
        return self.request("GET", f"/events/search?query={query}&limit={limit}")

# --- УПРАВЛЕНИЕ СОСТОЯНИЕМ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
@st.cache_resource
def get_api_client():
    return APIClient(API_BASE_URL)
api = get_api_client()

# Инициализация состояния сессии
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = None

def authenticate_user(token: str, user_data: Dict):
    st.session_state.authenticated = True
    st.session_state.user_data = user_data
    api.set_auth_token(token)

def logout_user():
    st.session_state.authenticated = False
    st.session_state.user_data = None
    api.clear_auth_token()
    st.success("Вы вышли из системы.")
    time.sleep(1)
    st.rerun()

def format_currency(amount: float) -> str:
    return f"${amount:.2f}"

def format_datetime(dt_str: Any) -> str:
    if not dt_str: return "N/A"
    try:
        if isinstance(dt_str, datetime):
            return dt_str.strftime("%d.%m.%Y %H:%M")
        dt = datetime.fromisoformat(str(dt_str).replace('Z', '+00:00'))
        return dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        return str(dt_str)

# --- РЕНДЕРИНГ СТРАНИЦ ---
def show_login_page():
    st.title("Вход в систему")
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="user@example.com")
        password = st.text_input("Пароль", type="password")
        if st.form_submit_button("Войти", use_container_width=True):
            with st.spinner("Выполняется вход..."):
                result = api.login(email, password)
                if result["success"]:
                    authenticate_user(result["data"]["access_token"], result["data"]["user"])
                    st.success("Вход выполнен успешно!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Ошибка входа: {result['error']}")

def show_registration_page():
    st.title("Регистрация")
    with st.form("registration_form"):
        email = st.text_input("Email*")
        username = st.text_input("Имя пользователя*")
        password = st.text_input("Пароль*", type="password", help="Минимум 6 символов")
        if st.form_submit_button("Зарегистрироваться", use_container_width=True):
            if not all([email, username, password]):
                st.error("Заполните все обязательные поля.")
            else:
                with st.spinner("Создается аккаунт..."):
                    result = api.register(email, username, password)
                    if result["success"]:
                        st.success("Регистрация успешна! Теперь вы можете войти.")
                    else:
                        st.error(f"Ошибка регистрации: {result['error']}")

def show_dashboard_page():
    st.title("Главная панель")
    profile_res = api.get_profile()
    if not profile_res['success']:
        st.error("Не удалось загрузить данные профиля.")
        return
    st.session_state.user_data = profile_res['data']

    col1, col2, col3 = st.columns(3)
    col1.metric("Баланс", format_currency(st.session_state.user_data.get('balance', 0)))
    my_events_res = api.get_my_events()
    col2.metric("Мои события", len(my_events_res['data']) if my_events_res.get('success') else 0)
    trans_summary_res = api.get_transaction_summary()
    col3.metric("Транзакций", trans_summary_res['data']['total_transactions'] if trans_summary_res.get('success') else 0)

    st.subheader("Последние активные события")
    events_res = api.get_events(status_filter="active", limit=5)
    if events_res['success'] and events_res['data']:
        for event in events_res['data']:
            with st.expander(f"{event['title']} - {format_currency(event['cost'])}"):
                st.write(event.get('description', '...'))
                if event.get('can_join') and st.button("Присоединиться", key=f"dash_join_{event['id']}"):
                    join_res = api.join_event(event['id'])
                    if join_res['success']:
                        st.success("Вы присоединились!")
                        st.rerun()
                    else:
                        st.error(join_res['error'])
    else:
        st.info("Нет активных событий.")

def show_profile_page():
    st.title("Профиль пользователя")
    profile_res = api.get_profile()
    if profile_res['success']:
        st.json(profile_res['data'])
    else:
        st.error("Не удалось загрузить профиль.")

def show_balance_page():
    st.title("Управление балансом")
    balance_res = api.get_balance()
    if balance_res['success']:
        st.metric("Текущий баланс", format_currency(balance_res['data']['balance']))
    with st.expander("Пополнить баланс", expanded=True):
        with st.form("add_balance_form"):
            amount = st.number_input("Сумма", min_value=1.0, value=50.0, step=10.0)
            description = st.text_input("Описание", "Пополнение через веб-интерфейс")
            if st.form_submit_button("Пополнить"):
                add_res = api.add_balance(amount, description)
                if add_res['success']:
                    st.success("Баланс пополнен!")
                    st.rerun()
                else:
                    st.error(add_res['error'])
    st.subheader("История транзакций")
    trans_res = api.get_transactions()
    if trans_res['success'] and trans_res['data']:
        df = pd.DataFrame(trans_res['data'])
        st.dataframe(df[['created_at', 'transaction_type', 'amount', 'description', 'status']])
    else:
        st.info("Транзакций пока нет.")

def show_events_page():
    st.title("Все события")
    events_res = api.get_events(status_filter="active")
    if events_res['success'] and events_res['data']:
        for event in events_res['data']:
            with st.container():
                st.subheader(event['title'])
                st.write(f"**Стоимость:** {format_currency(event['cost'])}")
                st.write(f"**Участники:** {event['current_participants']}/{event.get('max_participants') or '∞'}")
                if event['can_join']:
                    if st.button("Присоединиться", key=f"join_{event['id']}"):
                        join_res = api.join_event(event['id'])
                        if join_res['success']:
                            st.success("Вы присоединились!")
                            st.rerun()
                        else:
                            st.error(join_res['error'])
                st.divider()
    else:
        st.info("Активных событий нет.")

def show_my_events_page():
    st.title("Мои события")
    with st.expander("Создать новое событие"):
        with st.form("create_event_form"):
            title = st.text_input("Название*")
            description = st.text_area("Описание")
            cost = st.number_input("Стоимость", min_value=0.0)
            if st.form_submit_button("Создать"):
                if title:
                    create_res = api.create_event(title=title, description=description, cost=cost)
                    if create_res['success']:
                        st.success(f"Событие '{title}' создано!")
                        st.rerun()
                    else:
                        st.error(create_res['error'])
    my_events_res = api.get_my_events()
    if my_events_res['success'] and my_events_res['data']:
        for event in my_events_res['data']:
            with st.expander(f"{event['title']} (Статус: {event['status']})"):
                st.json(event)
                if event['status'] == 'draft':
                    if st.button("Активировать", key=f"activate_{event['id']}"):
                        act_res = api.activate_event(event['id'])
                        if act_res['success']:
                            st.success("Событие активировано!")
                            st.rerun()
                        else:
                            st.error(act_res['error'])
    else:
        st.info("Вы еще не создали ни одного события.")

def show_ml_predictions_page():
    st.title("ML Предсказания")
    events_res = api.get_events(status_filter="active")
    if events_res['success'] and events_res['data']:
        events = events_res['data']
        event_options = {f"{e['title']} ({format_currency(e['cost'])})": e['id'] for e in events}
        selected_event_title = st.selectbox("Выберите событие для анализа:", list(event_options.keys()))
        if st.button("Получить предсказание"):
            event_id = event_options[selected_event_title]
            with st.spinner("Анализ..."):
                pred_res = api.predict_participation(event_id, {})
                if pred_res['success']:
                    pred_data = pred_res['data']
                    st.subheader("Результат предсказания")
                    st.metric("Вероятность участия", f"{pred_data['confidence']:.0%}")
                    st.info(f"Рекомендация: {pred_data['recommendation']}")
                else:
                    st.error(pred_res['error'])
    else:
        st.warning("Нет активных событий для анализа.")

def show_analytics_page():
    st.title("Аналитика")
    st.subheader("Анализ ваших транзакций")
    trans_res = api.get_transactions()
    if trans_res['success'] and trans_res['data']:
        df = pd.DataFrame(trans_res['data'])
        df['created_at'] = pd.to_datetime(df['created_at'])
        fig = px.pie(df, names='transaction_type', values='amount', title='Распределение по типам транзакций')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Нет данных для аналитики.")

def show_public_events_page():
    st.title("Публичные события")
    st.info("Для участия войдите или зарегистрируйтесь.")
    events_res = api.get_events(status_filter="active")
    if events_res['success'] and events_res['data']:
        for event in events_res['data']:
            st.subheader(event['title'])
            st.write(f"**Стоимость:** {format_currency(event['cost'])}")
            st.divider()
    else:
        st.info("Активных событий нет.")

def show_about_page():
    st.title("О системе")
    st.markdown("Это веб-интерфейс для **Event Planner API**, созданный с помощью Streamlit.")
    health_res = api.request("GET", "/health")
    if health_res['success']:
        st.success("API Статус: Работает")
        st.json(health_res['data'])
    else:
        st.error("API Статус: Недоступен")

# --- ГЛАВНАЯ ФУНКЦИЯ И МАРШРУТИЗАЦИЯ ---
def main():
    st.markdown('<h1 class="main-header">Event Planner</h1>', unsafe_allow_html=True)
    health_check = api.request("GET", "/health")
    if not health_check.get("success"):
        st.error(f"Не удается подключиться к API. {health_check.get('error')}")
        return

    with st.sidebar:
        st.title("Меню")
        if st.session_state.authenticated:
            user = st.session_state.user_data
            st.success(f"Пользователь: {user.get('username')}")
            # Обновляем баланс в сайдбаре
            profile_res = api.get_profile()
            if profile_res['success']:
                st.session_state.user_data['balance'] = profile_res['data']['balance']
            st.metric("Баланс", format_currency(st.session_state.user_data.get('balance', 0)))

            page_options = ["Главная", "Профиль", "Баланс", "События", "Мои события", "ML Предсказания", "Аналитика"]
            page = st.radio("Навигация", page_options, key="nav_auth")
            if st.button("Выйти"):
                logout_user()
        else:
            st.warning("Вы не авторизованы")
            page_options = ["Вход", "Регистрация", "Просмотр событий", "О системе"]
            page = st.radio("Навигация", page_options, key="nav_no_auth")

    pages = {
        "Вход": show_login_page, "Регистрация": show_registration_page,
        "Просмотр событий": show_public_events_page, "О системе": show_about_page,
        "Главная": show_dashboard_page, "Профиль": show_profile_page,
        "Баланс": show_balance_page, "События": show_events_page,
        "Мои события": show_my_events_page, "ML Предсказания": show_ml_predictions_page,
        "Аналитика": show_analytics_page,
    }
    pages.get(page, show_about_page)()

if __name__ == "__main__":
    main()
