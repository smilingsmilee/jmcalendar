import streamlit as st
from database import *

def band_page():    
    band_id = st.session_state.band_id

    st.session_state.is_leader = is_leader(st.session_state.user.id, band_id)

    st.title(f"{st.session_state.band_name}")
    st.code(f"{app_url}?join_band={st.session_state.band_id}")
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
        for member in members:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"**{member['name']}**")
            with col2:
                instrument = st.text_input(
                    "",
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
    # TODO: allow band leader to reorder members

def show_upcoming_rehearsals():
    pass