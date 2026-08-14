import uuid
from types import SimpleNamespace

import streamlit as st
from database import Band, ensure_user_profile, get_band_name_from_band_id, join_band
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
    if st.secrets.get("DEV_MODE"):
        dev_sign_in()

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

def dev_sign_in():
    st.divider()
    st.caption("DEV_MODE is on: sign in without Telegram for local testing.")
    name = st.text_input("Dev user name", value="Dev User", key="dev_sign_in_name")
    if st.button("Dev Sign In", width="stretch") and name.strip():
        user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"dev:{name.strip()}"))
        user = SimpleNamespace(id=user_id, user_metadata={
            "name": name.strip(),
            "preferred_username": name.strip(),
            "email": f"dev_{user_id}@users.invalid",
        })
        ensure_user_profile(user)
        st.session_state.user = user
        st.session_state.dev_mode = True
        st.session_state.page = "home"
        pending_band_id = st.session_state.pop("pending_join_band", None)
        if pending_band_id:
            try:
                join_band(user.id, pending_band_id, is_leader=False)
                st.session_state.band = Band(
                    id=pending_band_id,
                    name=get_band_name_from_band_id(pending_band_id),
                )
                st.session_state.pop("invite_prompt_shown", None)
            except Exception as e:
                st.error(f"Could not join band: {e}")
        st.rerun()
