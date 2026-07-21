import streamlit as st
from database import *

def band_page():
    st.title(f"{st.session_state.band_name}")
    st.code(f"{app_url}?join_band={st.session_state.band_id}")
    st.caption("Share this link with someone to invite them to the band.")

    show_members()
    show_upcoming_rehearsals()
    
    if st.button("To home"):
        st.session_state.page = "home"
        st.rerun()
        
def show_members():
    pass

def show_upcoming_rehearsals():
    pass