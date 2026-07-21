import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

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

def add_new_user_to_database(user_id, name, email):
    get_client().table("users").upsert({
        "id": user_id,
        "name": name,
        "email": email
    }).execute()
    
def add_new_band_to_database(name):
    result = get_client().table("bands").insert({"name": name}).execute()
    return result.data[0]["id"]

def join_band(user_id, band_id, is_leader=False):
    get_client().table("members").upsert({"band_id": band_id, "member_id": user_id, "leader": is_leader}).execute()

def get_availability(user_id):
    result = get_client().table("availabilities").select("timestamp").eq("id", user_id).execute()
    return {row["timestamp"] for row in result.data}

def add_availability(user_id, timestamp):
    get_client().table("availabilities").upsert({"id": user_id, "timestamp": timestamp}).execute()

def remove_availability(user_id, timestamp):
    get_client().table("availabilities").delete().eq("id", user_id).eq("timestamp", timestamp).execute()

def get_band_ids_from_user_id(user_id):
    result = get_client().table("members").select("band_id").eq("member_id", user_id).execute()
    return [row["band_id"] for row in result.data]

def get_band_name_from_band_id(band_id):
    result = get_client().table("bands").select("name").eq("id", band_id).execute()
    return result.data[0]["name"]

def is_leader(user_id, band_id):
    result = get_client().table("members").select("leader").eq("member_id", user_id).eq("band_id", band_id).execute()
    return result.data[0]["leader"]

def get_members_from_band_id(band_id):
    result = get_client().table("members").select("member_id, instrument, leader, users(name)").eq("band_id", band_id).execute()
    return [{
        "id": row["member_id"],
        "instrument": row["instrument"],
        "name": row["users"]["name"],
        "leader": row["leader"]
    } for row in result.data]

def update_member_instrument(band_id, member_id, instrument):
    get_client().table("members").update({"instrument": instrument}).eq("band_id", band_id).eq("member_id", member_id).execute()