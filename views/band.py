import streamlit as st
from database import *

def band_page():    
    band_id = st.session_state.band.id

    st.session_state.is_leader = is_leader(st.session_state.user.id, band_id)

    st.title(f"{st.session_state.band.name}")
    st.code(f"{app_url}?join_band={band_id}")
    st.caption("Share this link with someone to invite them to the band.")

    show_members(band_id)
    show_upcoming_rehearsals()
    
    if st.button("To home"):
        st.session_state.page = "home"
        st.rerun()
        
def show_members(band_id):
    st.subheader("Members")
    members = get_members_from_band_id(band_id)
    if not members:
        st.info("No members yet.")
    elif not st.session_state.is_leader:
        for member in members:
            if member["instrument"]:
                st.markdown(f"**{member['name']}**: {member['instrument']}")
            else:
                st.markdown(f"**{member['name']}**")
    else:
        for index, member in enumerate(members):
            col1, col2, col3, col4 = st.columns([1, 1, 5, 10])
            with col1:
                if st.button("↑", key=f"up_{member['id']}", disabled=index == 0):
                    move_member(band_id, members, index, index - 1)
            with col2:
                if st.button("↓", key=f"down_{member['id']}", disabled=index == len(members) - 1):
                    move_member(band_id, members, index, index + 1)
            with col3:
                st.markdown(f"**{member['name']}**")
            with col4:
                instrument = st.text_input(
                    "Instrument",
                    value=member["instrument"] or "",
                    label_visibility="collapsed",
                    placeholder="Instrument",
                )
            if instrument != (member["instrument"] or ""):
                try:
                    update_member_instrument(band_id, member["id"], instrument or None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not update {member['name']}'s instrument: {e}")

def move_member(band_id, members, from_index, to_index):
    ids = [member["id"] for member in members]
    ids[from_index], ids[to_index] = ids[to_index], ids[from_index]
    reorder_band_members(band_id, ids)
    st.rerun()

def show_upcoming_rehearsals():
    pass