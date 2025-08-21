import streamlit as st
import pandas as pd
import api_client

st.set_page_config(page_title="События", layout="wide")
st.title("🎉 Активные события")

if not st.session_state.get("token"):
    st.warning("Пожалуйста, войдите в систему, чтобы просматривать события.")
    st.stop()

events = api_client.get_active_events()

if not events:
    st.info("Активных событий пока нет.")
else:
    for event in events:
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(event['title'])
                st.caption(f"ID: {event['id']} | Создатель ID: {event['creator_id']}")
                st.write(event.get('description', 'Без описания.'))

            with col2:
                st.metric("Стоимость", f"${event['cost']:.2f}")
                st.metric("Участники", f"{event['current_participants']}/{event.get('max_participants') or '∞'}")

                if st.button("Присоединиться", key=f"join_{event['id']}"):
                    result = api_client.join_event(event['id'])
                    if result:
                        st.success(result['message'])
                        # Обновляем баланс в сайдбаре (простой способ)
                        st.session_state.user['balance'] = result['new_balance']
                        st.experimental_rerun()
            st.divider()
