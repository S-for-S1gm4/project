import streamlit as st
import api_client

st.set_page_config(page_title="Создать событие", layout="centered")
st.title("✏️ Создать новое событие")

if not st.session_state.get("token"):
    st.warning("Пожалуйста, войдите в систему, чтобы создавать события.")
    st.stop()

with st.form("create_event_form", clear_on_submit=True):
    title = st.text_input("Название события")
    description = st.text_area("Описание")
    cost = st.number_input("Стоимость участия", min_value=0.0, step=5.0, format="%.2f")
    max_participants = st.number_input("Макс. участников (0 - без лимита)", min_value=0, step=5)

    submitted = st.form_submit_button("Создать событие")
    if submitted:
        if not title:
            st.error("Название не может быть пустым!")
        else:
            result = api_client.create_event(title, description, cost, max_participants)
            if result:
                st.success(f"Событие '{result['title']}' успешно создано с ID: {result['id']}!")
                st.balloons()
