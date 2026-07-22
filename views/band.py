import streamlit as st
from datetime import datetime, time, timedelta
from database import *

def band_page():    
    band_id = st.session_state.band.id

    st.session_state.is_leader = is_leader(st.session_state.user.id, band_id)

    st.title(f"{st.session_state.band.name}")
    st.code(f"{app_url}?join_band={band_id}")
    st.caption("Share this link with someone to invite them to the band.")

    show_members(band_id)
    if st.session_state.is_leader:
        show_availabilities(band_id)
        new_rehearsal(band_id)
    show_upcoming_rehearsals(band_id)
    
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

def show_availabilities(band_id):
    st.subheader("Availability")

    members = get_members_from_band_id(band_id)
    if not members:
        st.info("No members yet.")
        return

    band_availabilities = get_availabilities_from_band_id(band_id)

    if "rehearsal_date_slots" not in st.session_state:
        st.session_state.rehearsal_date_slots = [0]
        st.session_state.rehearsal_date_next_id = 1

    slots = st.session_state.rehearsal_date_slots
    widths = [1] + [1] * len(members)
    kept_slots = []
    last_date_value = None

    for slot_id in slots:
        col1, col2 = st.columns([1, 4])
        with col1:
            date_value = st.date_input("Date", value=None, format="DD/MM/YYYY", key=f"rehearsal_date_{slot_id}")
            time_range = (time(hour=10), time(hour=21))
            if date_value is not None:
                time_range = st.slider(
                    "Time range",
                    min_value=time(hour=10),
                    max_value=time(hour=21),
                    value=time_range,
                    step=timedelta(hours=1),
                    key=f"rehearsal_time_range_{slot_id}",
                )
                
        with col2:
            if date_value is not None:
                start_time, end_time = time_range
                st.markdown(f"**{date_value.strftime('%a %d %b')}**")
                header_cols = st.columns(widths)
                header_cols[0].write("")
                for col, member in zip(header_cols[1:], members):
                    col.markdown(f"**{member['name']}**")
                    if member["instrument"]:
                        col.caption(member["instrument"])
                for slot in [time(hour=h) for h in range(start_time.hour, end_time.hour+1)]:
                    timestamp = datetime.combine(date_value, slot).isoformat()
                    available_ids = band_availabilities.get(timestamp, [])
                    row_cols = st.columns(widths)
                    row_cols[0].markdown(slot.strftime("%I %p").lstrip("0"))
                    for col, member in zip(row_cols[1:], members):
                        col.markdown("✓" if member["id"] in available_ids else "")

        last_date_value = date_value
        if date_value is not None:
            kept_slots.append(slot_id)

    if last_date_value is not None:
        kept_slots.append(st.session_state.rehearsal_date_next_id)
        st.session_state.rehearsal_date_next_id += 1
    else:
        kept_slots.append(slots[-1])

    if kept_slots != slots:
        st.session_state.rehearsal_date_slots = kept_slots
        st.rerun()

def new_rehearsal(band_id):
    pass

def show_upcoming_rehearsals(band_id):
    pass