import streamlit as st
from supabase import create_client

app_url = st.secrets["APP_URL"]

class Band:
    def __init__(self, id, name):
        self.id = id
        self.name = name

def get_client():
    if "client" not in st.session_state:
        st.session_state.client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    return st.session_state.client

def ensure_user_profile(user):
    metadata = user.user_metadata or {}
    name = (
        metadata.get("name")
        or metadata.get("preferred_username")
        or "Telegram user"
    )
    get_client().table("users").upsert({
        "id": user.id,
        "name": name,
        "email": metadata.get("email"),
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
    result = get_client().table("members").select("member_id, instrument, leader, users(name)").eq("band_id", band_id).order("order", nullsfirst=False).execute()
    return [{
        "id": row["member_id"],
        "instrument": row["instrument"],
        "name": row["users"]["name"],
        "leader": row["leader"]
    } for row in result.data]

def update_member_instrument(band_id, member_id, instrument):
    get_client().table("members").update({"instrument": instrument}).eq("band_id", band_id).eq("member_id", member_id).execute()

def reorder_band_members(band_id, ordered_member_ids):
    for index, member_id in enumerate(ordered_member_ids):
        get_client().table("members").update({"order": index}).eq("band_id", band_id).eq("member_id", member_id).execute()

def get_availabilities_from_band_id(band_id):
    members = get_members_from_band_id(band_id)
    band_availabilities = {}
    for member in members:
        user_id = member["id"]
        availabilities = get_availabilities_from_user_id(user_id)
        for timestamp in availabilities:
            if timestamp not in band_availabilities:
                band_availabilities[timestamp] = [user_id]
            else:
                band_availabilities[timestamp].append(user_id)
    return band_availabilities

def get_availabilities_from_user_id(id):
    result = get_client().table("availabilities").select("timestamp").eq("id", id).execute()
    return [row["timestamp"] for row in result.data]

def add_rehearsal(band_id, timestamp, member_id, location=None):
    rehearsal = {
        "band_id": band_id,
        "timestamp": timestamp,
        "member_id": member_id,
        "attendance": True,
    }
    if location is not None:
        rehearsal["location"] = location
    get_client().table("rehearsals").upsert(rehearsal).execute()

def get_rehearsals_from_band_id(band_id):
    result = get_client().table("rehearsals").select("timestamp, member_id, attendance").eq("band_id", band_id).execute()
    rehearsals = {}
    for row in result.data:
        rehearsals.setdefault(row["timestamp"], {})[row["member_id"]] = row["attendance"]
    return rehearsals

def get_rehearsal_locations_from_band_id(band_id):
    result = get_client().table("rehearsals").select("timestamp, location").eq("band_id", band_id).execute()
    return {row["timestamp"]: row["location"] for row in result.data if row["location"]}

def get_rehearsal_location(band_id, timestamp):
    result = get_client().table("rehearsals").select("location").eq("band_id", band_id).eq("timestamp", timestamp).limit(1).execute()
    return result.data[0]["location"] if result.data else None

def set_rehearsal_attendance(band_id, timestamp, member_id, attendance):
    rehearsal = {
        "band_id": band_id,
        "timestamp": timestamp,
        "member_id": member_id,
        "attendance": attendance,
    }
    location = get_rehearsal_location(band_id, timestamp)
    if location is not None:
        rehearsal["location"] = location
    get_client().table("rehearsals").upsert(rehearsal).execute()

def update_rehearsal_location(band_id, timestamps, location):
    get_client().table("rehearsals").update({"location": location}).eq("band_id", band_id).in_("timestamp", timestamps).execute()

def delete_rehearsal(band_id, timestamp):
    get_client().table("rehearsals").delete().eq("band_id", band_id).eq("timestamp", timestamp).execute()

def get_rehearsals_from_user_id(user_id):
    result = get_client().table("rehearsals").select("timestamp, band_id, location").eq("member_id", user_id).eq("attendance", True).execute()
    return result.data
