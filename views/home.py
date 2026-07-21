import streamlit as st
from datetime import datetime, timedelta, time
from database import *

def home_page():
    user_id = st.session_state.user.id

    if "availability" not in st.session_state:
        try:
            st.session_state.availability = get_availability(user_id)
        except Exception as e:
            st.error(f"Could not load your availability: {e}")
            st.session_state.availability = set()
    if "week_offset" not in st.session_state:
        st.session_state.week_offset = 0
        
    calendar(user_id)
    show_bands(user_id)

    if st.button("Sign out", use_container_width=True):
        st.session_state.user = None
        st.session_state.page = "landing"
        st.session_state.week_offset = 0
        st.session_state.pop("availability", None)
        st.rerun()

def calendar(user_id):
    st.title("My Availability")
    st.caption("Click a cell to toggle your availability for that time slot.")

    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=st.session_state.week_offset)
    week_days = [monday + timedelta(days=i) for i in range(7)]

    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("← Previous week", use_container_width=True):
            st.session_state.week_offset -= 1
            st.rerun()
    with col2:
        if week_days[0].year != week_days[-1].year:
            st.markdown(
                f"<div style='text-align:center; padding-top:0.5rem;'>"
                f"{week_days[0].strftime('%d %b %Y')} - {week_days[-1].strftime('%d %b %Y')}</div>",
                unsafe_allow_html=True
            )
        elif week_days[0].month != week_days[-1].month:
            st.markdown(
                f"<div style='text-align:center; padding-top:0.5rem;'>"
                f"{week_days[0].strftime('%d %b')} - {week_days[-1].strftime('%d %b %Y')}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='text-align:center; padding-top:0.5rem;'>"
                f"{week_days[0].strftime('%d')} - {week_days[-1].strftime('%d %b %Y')}</div>",
                unsafe_allow_html=True
            )
    with col3:
        if st.button("Next week →", use_container_width=True):
            st.session_state.week_offset += 1
            st.rerun()

    header_cols = st.columns([1] * 8)
    header_cols[0].write("")
    for col, day in zip(header_cols[1:], week_days):
        col.markdown(
            f"<div style='text-align:center;'><b>{day.strftime('%a')}</b><br>{day.strftime('%d %b')}</div>",
            unsafe_allow_html=True,
        )

    for slot in [time(hour=h) for h in range(10, 22)]:
        row_cols = st.columns([1] * 8)
        row_cols[0].markdown(
            f"<div style='text-align:center; padding-top:0.5rem;'>{slot.strftime('%I %p').lstrip('0')}</div>",
            unsafe_allow_html=True,
        )
        for col, day in zip(row_cols[1:], week_days):
            key = datetime.combine(day, slot).isoformat()
            selected = key in st.session_state.availability
            with col:
                st.button(
                    "✓" if selected else " ",
                    key=f"slot_{key}",
                    type="primary" if selected else "secondary",
                    on_click=_toggle_slot,
                    args=(user_id, key),
                    use_container_width=True,
                )

    week_dates = {d.isoformat() for d in week_days}

    col4, col5 = st.columns(2)
    with col4:
        if st.button("Clear this week", use_container_width=True):
            to_remove = {key for key in st.session_state.availability if key.split("T", 1)[0] in week_dates}
            try:
                for key in to_remove:
                    remove_availability(user_id, key)
                st.session_state.availability -= to_remove
            except Exception as e:
                st.error(f"Could not clear this week: {e}")
            st.rerun()
    with col5:
        if st.button("To current week", use_container_width=True):
            st.session_state.week_offset = 0
            st.rerun()

def show_bands(user_id):
    st.title("My Bands")
    try:
        band_ids = get_band_ids_from_user_id(user_id)
        if not band_ids:
            st.info("You are not a member of any bands yet.")
        else:
            for band_id in band_ids:
                band_name = get_band_name_from_band_id(band_id)
                if st.button(f"{band_name}"):
                    st.session_state.band_id = band_id
                    st.session_state.band_name = band_name
                    st.session_state.page = "band"
                    st.rerun()

    except Exception as e:
        st.error(f"Could not load your bands: {e}")

def _toggle_slot(user_id, key):
    try:
        if key not in st.session_state.availability:
            add_availability(user_id, key)
            st.session_state.availability.add(key)
        else:
            remove_availability(user_id, key)
            st.session_state.availability.discard(key)
    except Exception as e:
        st.error(f"Could not save availability: {e}")