import streamlit as st
import pandas as pd
import api_client

st.set_page_config(page_title="Профиль", layout="centered")
st.title("👤 Мой профиль")

if not st.session_state.get("token"):
    st.warning("Пожалуйста, войдите в систему, чтобы просмотреть профиль.")
    st.stop()

# --- Пополнение баланса ---
with st.expander("Пополнить баланс"):
    with st.form("balance_form", clear_on_submit=True):
        amount = st.number_input("Сумма", min_value=0.01, step=10.0, format="%.2f")
        description = st.text_input("Описание (необязательно)", "Пополнение через Web")
        submitted = st.form_submit_button("Пополнить")

        if submitted:
            result = api_client.add_balance(amount, description)
            if result:
                st.success(result['message'])
                st.session_state.user['balance'] = result['new_balance']
                st.experimental_rerun()


# --- История транзакций ---
st.subheader("История транзакций")
transactions = api_client.get_transactions()
if transactions:
    df = pd.DataFrame(transactions)
    df_display = df[['created_at', 'transaction_type', 'amount', 'description', 'status']]
    df_display['created_at'] = pd.to_datetime(df_display['created_at']).dt.strftime('%Y-%m-%d %H:%M')
    st.dataframe(df_display, use_container_width=True)
else:
    st.info("У вас пока нет транзакций.")
