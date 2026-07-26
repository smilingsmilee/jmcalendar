import streamlit as st
import os
from database import *
from telegram_auth import (
    TelegramAuthConfigurationError,
    TelegramAuthStateError,
    create_callback_url,
    read_callback_state,
)
from views.signin import signin_page
from views.home import home_page
from views.band import band_page

def main():
    st.set_page_config(page_title="JMCalendar", page_icon=":house:")

    if "user" not in st.session_state:
        st.session_state.user = None
    if "page" not in st.session_state:
        st.session_state.page = "signin"

    auth_error = (
        st.query_params.get("error_description")
        or st.query_params.get("error")
    )
    if auth_error:
        handle_authentication_error()

    code = st.query_params.get("code")
    if code:
        authenticate_user(code, st.query_params.get("auth_state"))

    join_band_id = st.query_params.get("join_band")

    if join_band_id:
        handle_band_invite(join_band_id)

    if st.session_state.user is not None and st.session_state.page == "signin":
        st.session_state.page = "home"
    elif (
        st.session_state.user is None
        and st.session_state.page in {"home", "band"}
    ):
        st.session_state.page = "signin"

    pages = {
        "signin": signin_page,
        "home": home_page,
        "band": band_page
    }
    page = pages.get(st.session_state.page)
    if page:
        page()
    else:
        st.error(f"Unknown page: {st.session_state.page}")

# new tele auth
def authenticate_user(code, auth_state):
    try:
        state = read_callback_state(auth_state, os.getenv("AUTH_STATE_SECRET"))
        response = exchange_code_for_session(
            code,
            state["code_verifier"],
            create_callback_url(os.getenv("APP_URL"), auth_state),
        )
        if response.user is None or response.session is None:
            raise ValueError("Supabase did not return an authenticated session.")
        ensure_user_profile(response.user)
        st.session_state.user = response.user
        st.session_state.page = "home"
    except (TelegramAuthConfigurationError, TelegramAuthStateError) as e:
        st.error(str(e))
        st.session_state.page = "signin"
    except Exception:
        st.error("Telegram sign-in could not be completed. Please try again.")
        st.session_state.page = "signin"
    finally:
        st.query_params.clear()

def handle_authentication_error():
    st.query_params.clear()
    st.session_state.page = "signin"
    st.error("Telegram sign-in was cancelled or could not be completed.")

def handle_band_invite(band_id):
    if st.session_state.user is None:
        if st.session_state.get("invite_prompt_shown") != band_id:
            st.info("Sign in to accept this band invite.")
            st.session_state.page = "signin"
            st.session_state.invite_prompt_shown = band_id
        return

    try:
        join_band(st.session_state.user.id, band_id, is_leader=False)
        st.session_state.band = Band(id=band_id, name=get_band_name_from_band_id(band_id))
        st.session_state.page = "band"
    except Exception as e:
        st.error(f"Could not join band: {e}")
    finally:
        st.query_params.clear()

if __name__ == "__main__":
    main()
