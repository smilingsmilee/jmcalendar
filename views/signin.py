import streamlit as st
from telegram_auth import (
    TelegramAuthConfigurationError,
    create_authorization_request,
)

def signin_page():
    st.title("Sign In")
    if notice := st.session_state.pop("auth_notice", None):
        st.warning(notice)
    st.write("Use your Telegram account to continue.")
    telegram_sign_in()

def telegram_sign_in():
    try:
        authorization_url = create_authorization_request(
            st.secrets.get("TELEGRAM_CLIENT_ID"),
            st.secrets.get("APP_URL"),
            st.secrets.get("AUTH_STATE_SECRET"),
            join_band_id=st.session_state.get("pending_join_band"),
        )
    except TelegramAuthConfigurationError as e:
        st.error(str(e))
        return

    st.link_button(
        "Continue with Telegram",
        authorization_url,
        type="primary",
        width="stretch",
    )
