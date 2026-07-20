import streamlit as st
from database import *
from views.landing import *
from views.home import *

def main():
    st.set_page_config(page_title="JMCalendar", page_icon=":house:")

    if "page" not in st.session_state:
        st.session_state.page = "landing"
    if "user" not in st.session_state:
        st.session_state.user = None

    code = st.query_params.get("code")
    if code:
        authenticate_user(code)

    pages = {
        "landing": landing_page,
        "signin": signin_page,
        "forgot_password": forgot_password_page,
        "signup": signup_page,
        "reset_password": reset_password_page,
        "home": home_page
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

if __name__ == "__main__":
    main()