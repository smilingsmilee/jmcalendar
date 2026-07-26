import os
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
            os.getenv("SUPABASE_URL"),
            os.getenv("APP_URL"),
            os.getenv("AUTH_STATE_SECRET"),
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
