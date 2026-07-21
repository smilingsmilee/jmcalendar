import streamlit as st
from database import *
from views.landing import *
from views.home import *
from views.band import *

def main():
    st.set_page_config(page_title="JMCalendar", page_icon=":house:")

    if "page" not in st.session_state:
        st.session_state.page = "landing"
    if "user" not in st.session_state:
        st.session_state.user = None

    code = st.query_params.get("code")
    if code:
        authenticate_user(code)

    join_band_id = st.query_params.get("join_band")
    if join_band_id:
        handle_band_invite(join_band_id)

    pages = {
        "landing": landing_page,
        "signin": signin_page,
        "forgot_password": forgot_password_page,
        "signup": signup_page,
        "reset_password": reset_password_page,
        "home": home_page,
        "band": band_page
    }
    page = pages.get(st.session_state.page)
    if page:
        page()
    else:
        st.error(f"Unknown page: {st.session_state.page}")

def authenticate_user(code):
    auth_type = st.query_params.get("type")

    try:
        session = exchange_code_for_session(code)
        st.session_state.user = session.user
    except Exception as e:
        st.error(f"Could not verify link: {e}")
        return
    finally:
        st.query_params.clear()

    if auth_type == "recovery":
        st.session_state.page = "reset_password"
    elif auth_type == "signup":
        st.session_state.page = "home"
    else:
        st.error(f"Unknown authentication type: {auth_type}")

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