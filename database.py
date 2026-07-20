import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app_url = os.getenv("APP_URL")

def get_client():
    if "client" not in st.session_state:
        st.session_state.client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    return st.session_state.client

def sign_in(email, password):
    return get_client().auth.sign_in_with_password({"email": email, "password": password})

def sign_up(email, password, name):
    return get_client().auth.sign_up({
        "email": email,
        "password": password,
        "options": {
            "email_redirect_to": app_url,
            "data": {"name": name}
        }
    })

def request_password_reset(email):
    return get_client().auth.reset_password_for_email(email, options={"redirect_to": app_url})

def exchange_code_for_session(code):
    return get_client().auth.exchange_code_for_session({"auth_code": code})

def update_password(new_password):
    return get_client().auth.update_user({"password": new_password})

def add_new_user_in_database(user_id, name, email):
    get_client().table("users").upsert({
        "id": user_id,
        "name": name,
        "email": email
    }).execute()