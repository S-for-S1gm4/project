import requests
import streamlit as st

# URL вашего API. Лучше вынести в переменные окружения.
API_URL = "http://localhost/api" # Убедитесь, что порт правильный, если запускаете не через Nginx

def get_auth_header():
    """Получение заголовка авторизации из состояния сессии."""
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def login(email, password):
    """Авторизация пользователя."""
    try:
        response = requests.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка входа: {e.response.json().get('detail', 'Неверные данные')}")
        return None

def register(username, email, password):
    """Регистрация нового пользователя."""
    try:
        response = requests.post(f"{API_URL}/auth/register", json={
            "email": email,
            "username": username,
            "password": password
        })
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка регистрации: {e.response.json().get('detail', 'Пользователь уже существует')}")
        return None

def get_active_events():
    """Получение списка активных событий."""
    try:
        response = requests.get(f"{API_URL}/events", params={"status_filter": "active"}, headers=get_auth_header())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Не удалось загрузить события: {e}")
        return []

def get_profile():
    """Получение профиля пользователя."""
    try:
        response = requests.get(f"{API_URL}/users/profile", headers=get_auth_header())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None # Ошибку не показываем, т.к. может быть просто не авторизован

def get_transactions():
    """Получение истории транзакций."""
    try:
        response = requests.get(f"{API_URL}/users/transactions", headers=get_auth_header())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Не удалось загрузить транзакции: {e}")
        return []

def add_balance(amount, description):
    """Пополнение баланса."""
    try:
        response = requests.post(f"{API_URL}/users/balance", json={"amount": amount, "description": description}, headers=get_auth_header())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка пополнения: {e.response.json().get('detail')}")
        return None

def create_event(title, description, cost, max_participants):
    """Создание нового события."""
    try:
        payload = {
            "title": title,
            "description": description,
            "cost": cost,
            "max_participants": max_participants if max_participants > 0 else None
        }
        response = requests.post(f"{API_URL}/events/", json=payload, headers=get_auth_header())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка создания события: {e.response.json().get('detail')}")
        return None

def join_event(event_id):
    """Присоединение к событию."""
    try:
        response = requests.post(f"{API_URL}/events/{event_id}/join", headers=get_auth_header())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Не удалось присоединиться: {e.response.json().get('detail')}")
        return None
