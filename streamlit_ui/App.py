import streamlit as st
import api_client

# Инициализация состояния сессии
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

st.set_page_config(page_title="Event Planner", layout="wide")

def show_login_form():
    """Форма входа."""
    with st.form("login_form"):
        st.subheader("Вход")
        email = st.text_input("Email")
        password = st.text_input("Пароль", type="password")
        submitted = st.form_submit_button("Войти")

        if submitted:
            data = api_client.login(email, password)
            if data:
                st.session_state.token = data.get("access_token")
                st.session_state.user = data.get("user")
                st.success("Вы успешно вошли в систему!")
                st.experimental_rerun()

def show_register_form():
    """Форма регистрации."""
    with st.form("register_form"):
        st.subheader("Регистрация")
        username = st.text_input("Имя пользователя")
        email = st.text_input("Email для регистрации")
        password = st.text_input("Пароль для регистрации", type="password")
        submitted = st.form_submit_button("Зарегистрироваться")

        if submitted:
            user = api_client.register(username, email, password)
            if user:
                st.success("Регистрация прошла успешно! Теперь вы можете войти.")

# --- Основная логика ---
if not st.session_state.token:
    st.title("Добро пожаловать в Event Planner!")
    login_tab, register_tab = st.tabs(["Вход", "Регистрация"])
    with login_tab:
        show_login_form()
    with register_tab:
        show_register_form()
else:
    st.sidebar.header(f"Привет, {st.session_state.user.get('username')}!")
    st.sidebar.metric("Баланс", f"${st.session_state.user.get('balance', 0):.2f}")

    if st.sidebar.button("Выйти"):
        st.session_state.token = None
        st.session_state.user = None
        st.experimental_rerun()

    st.title("Главная")
    st.write("Используйте меню слева для навигации по разделам.")
    st.info("Вы авторизованы. Теперь вам доступны все разделы приложения.")
