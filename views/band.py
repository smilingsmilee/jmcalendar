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
    st.caption("Click a time to select it, then confirm to schedule the rehearsals.")

    members = get_members_from_band_id(band_id)
    if not members:
        st.info("No members yet.")
        return

    band_availabilities = get_availabilities_from_band_id(band_id)

    if "rehearsal_date_slots" not in st.session_state:
        st.session_state.rehearsal_date_slots = [0]
        st.session_state.rehearsal_date_next_id = 1
    if "selected_rehearsal_slots" not in st.session_state:
        st.session_state.selected_rehearsal_slots = {}
    selected_slots = st.session_state.selected_rehearsal_slots.setdefault(band_id, set())

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
                    is_selected = timestamp in selected_slots
                    row_cols = st.columns(widths)
                    with row_cols[0]:
                        if st.button(
                            slot.strftime("%I %p").lstrip("0"),
                            key=f"select_{slot_id}_{timestamp}",
                            type="primary" if is_selected else "secondary",
                            use_container_width=True,
                        ):
                            if is_selected:
                                selected_slots.discard(timestamp)
                            else:
                                selected_slots.add(timestamp)
                            st.rerun()
                    for col, member in zip(row_cols[1:], members):
                        col.markdown("✓" if member["id"] in available_ids else "")

        last_date_value = date_value
        if date_value is not None:
            kept_slots.append(slot_id)

    if selected_slots:
        st.caption("Selected:")
        for start, end in merge_rehearsal_ranges(selected_slots):
            start_str = start.strftime("%I %p").lstrip("0")
            end_str = end.strftime("%I %p").lstrip("0")
            st.markdown(f"**{start.strftime('%a %d %b')}, {start_str} - {end_str}**")

        col_confirm, col_clear = st.columns(2)
        with col_confirm:
            if st.button("Confirm rehearsals", use_container_width=True):
                try:
                    for timestamp in selected_slots:
                        add_rehearsal(band_id, timestamp, st.session_state.user.id)
                    st.session_state.selected_rehearsal_slots[band_id] = set()
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not schedule rehearsals: {e}")
        with col_clear:
            if st.button("Clear selection", use_container_width=True):
                st.session_state.selected_rehearsal_slots[band_id] = set()
                st.rerun()

    if last_date_value is not None:
        kept_slots.append(st.session_state.rehearsal_date_next_id)
        st.session_state.rehearsal_date_next_id += 1
    else:
        kept_slots.append(slots[-1])

    if kept_slots != slots:
        st.session_state.rehearsal_date_slots = kept_slots
        st.rerun()

def merge_rehearsal_ranges(timestamps):
    ranges = []
    start = prev = None
    for dt in sorted(datetime.fromisoformat(ts) for ts in timestamps):
        if start is None:
            start = prev = dt
        elif dt - prev == timedelta(hours=1):
            prev = dt
        else:
            ranges.append((start, prev + timedelta(hours=1)))
            start = prev = dt
    if start is not None:
        ranges.append((start, prev + timedelta(hours=1)))
    return ranges

def show_upcoming_rehearsals(band_id):
    pass