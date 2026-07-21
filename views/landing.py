import streamlit as st
from database import *

def landing_page():
    st.title("JMCalendar")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sign In", use_container_width=True):
            st.session_state.page = "signin"
            st.rerun()
    with col2:
        if st.button("Sign Up", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()

def signin_page():
    st.title("Sign In")

    with st.form("signin_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In")

    if submitted:
        try:
            st.session_state.user = sign_in(email, password).user
            st.session_state.page = "home"
            st.rerun()
        except Exception as e:
            st.error(f"Sign in failed: {e}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Back"):
            st.session_state.page = "landing"
            st.rerun()
    with col2:
        if st.button("Forgot password?"):
            st.session_state.page = "forgot_password"
            st.rerun()
    with col3:
        if st.button("Sign up as new user"):
            st.session_state.page = "signup"
            st.rerun()

def forgot_password_page():
    st.title("Reset Password")
    st.write("Enter your email and we'll send you a link to reset your password.")

    with st.form("forgot_password_form"):
        email = st.text_input("Email")
        submitted = st.form_submit_button("Send Reset Link")

    if submitted:
        if not email:
            st.error("Please enter your email.")
        else:
            try:
                request_password_reset(email)
                st.success(
                    "If an account exists for that email, a reset link has been sent."
                )
            except Exception as e:
                st.error(f"Could not send reset email: {e}")

    if st.button("Back"):
        st.session_state.page = "signin"
        st.rerun()

def signup_page():
    st.title("Sign Up")

    with st.form("signup_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Sign Up")

    if submitted:
        if not name or not email or not password:
            st.error("Please fill out all fields.")
        elif password != confirm_password:
            st.error("Passwords do not match.")
        else:
            try:
                result = sign_up(email, password, name)
                if result.user and result.user.identities:
                    add_new_user_to_database(result.user.id, name, email)
                    st.success(
                        "Account created! Check your email to confirm your address."
                    )
                else:
                    st.error("An account with this email already exists.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")

    if st.button("Back"):
        st.session_state.page = "landing"
        st.rerun()

def reset_password_page():
    st.title("Set a New Password")

    with st.form("reset_password_form"):
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Update Password")

    if submitted:
        if not new_password:
            st.error("Please enter a new password.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            try:
                update_password(new_password)
                st.success("Password updated!")
                st.session_state.user = None
                st.session_state.page = "landing"
                st.rerun()
            except Exception as e:
                st.error(f"Could not update password: {e}")