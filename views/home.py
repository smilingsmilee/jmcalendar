import streamlit as st
from datetime import datetime, timedelta, time
from database import *
from frontend.availability_grid import availability_grid

def home_page():
    if st.session_state.dev_mode:
        st.title("Dev mode")

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

    st.divider()
    
    show_bands(user_id)

    if "show_new_band_form" not in st.session_state:
        st.session_state.show_new_band_form = False

    if st.button("Create new band", width='stretch'):
        st.session_state.show_new_band_form = True

    if st.session_state.show_new_band_form:
        with st.form("New band"):
            band_name = st.text_input("Name of band")
            col1a, col1b = st.columns(2)
            with col1a:
                submitted = st.form_submit_button("Create", width='stretch')
            with col1b:
                cancelled = st.form_submit_button("Cancel", width='stretch')
        if submitted:
            try:
                band_id = add_new_band_to_database(band_name)
                join_band(user_id, band_id, is_leader=True)
                st.session_state.show_new_band_form = False
                st.rerun()
            except Exception as e:
                st.error(f"Could not create band: {e}")
        elif cancelled:
            st.session_state.show_new_band_form = False
            st.rerun()

    st.divider()

    show_upcoming_rehearsals(user_id)

    st.divider()

    sign_out_current = st.button(
        "Sign Out",
        width="stretch",
        help="Sign out on this device only.",
    )
    sign_out_everywhere = st.button(
        "Sign Out of All Devices",
        width="stretch",
        help="End all of your active sessions.",
    )

    if sign_out_current or sign_out_everywhere:
        st.session_state.clear()
        st.session_state.page = "signin"
        st.rerun()

def calendar(user_id):
    st.title("My Availability")
    st.caption("Click or drag across cells to toggle your availability for that time slot.")

    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=st.session_state.week_offset)
    week_days = [monday + timedelta(days=i) for i in range(7)]

    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("← Previous week", width='stretch'):
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
        if st.button("Next week →", width='stretch'):
            st.session_state.week_offset += 1
            st.rerun()

    hours = [time(hour=h) for h in range(10, 22)]
    time_labels = [hour.strftime("%I %p").lstrip("0") for hour in hours]
    day_labels = [day.strftime("%a %d %b") for day in week_days]

    values = [
        [datetime.combine(day, hour).isoformat() in st.session_state.availability for day in week_days]
        for hour in hours
    ]

    grid_key = f"avail_grid_{monday.isoformat()}"
    edited = availability_grid(days=day_labels, hours=time_labels, values=values, key=grid_key)

    if edited is not None:
        changed = False
        for row, hour in enumerate(hours):
            for col, day in enumerate(week_days):
                key = datetime.combine(day, hour).isoformat()
                was_selected = key in st.session_state.availability
                now_selected = bool(edited[row][col])
                if now_selected != was_selected:
                    try:
                        if now_selected:
                            add_availability(user_id, key)
                            st.session_state.availability.add(key)
                        else:
                            remove_availability(user_id, key)
                            st.session_state.availability.discard(key)
                        changed = True
                    except Exception as e:
                        st.error(f"Could not save availability: {e}")
        if changed:
            st.rerun()

    week_dates = {d.isoformat() for d in week_days}

    col4, col5 = st.columns(2)
    with col4:
        if st.button("Clear this week", width='stretch'):
            to_remove = {key for key in st.session_state.availability if key.split("T", 1)[0] in week_dates}
            try:
                for key in to_remove:
                    remove_availability(user_id, key)
                st.session_state.availability -= to_remove
            except Exception as e:
                st.error(f"Could not clear this week: {e}")
            st.rerun()
    with col5:
        if st.button("To current week", width='stretch'):
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
                if st.button(f"{band_name}", key=band_id):
                    st.session_state.band = Band(id=band_id, name=band_name)
                    st.session_state.page = "band"
                    st.rerun()

    except Exception as e:
        st.error(f"Could not load your bands: {e}")

def show_upcoming_rehearsals(user_id):
    st.subheader("Upcoming Rehearsals")

    rehearsals = get_rehearsals_from_user_id(user_id)

    now = datetime.now()
    upcoming = [r for r in rehearsals if datetime.fromisoformat(r["timestamp"]) >= now]

    if not upcoming:
        st.write("No upcoming rehearsals.")
        return

    timestamps_by_band = {}
    location_by_timestamp = {}
    for r in upcoming:
        timestamps_by_band.setdefault(r["band_id"], []).append(r["timestamp"])
        if r.get("location"):
            location_by_timestamp[r["timestamp"]] = r["location"]

    ranges = []
    for band_id, timestamps in timestamps_by_band.items():
        band_name = get_band_name_from_band_id(band_id)
        for start, end in merge_rehearsal_ranges(timestamps):
            location = location_by_timestamp.get(start.isoformat())
            ranges.append((start, end, band_name, location))

    for start, end, band_name, location in sorted(ranges, key=lambda r: (r[0], r[1], r[2])):
        start_str = start.strftime("%I %p").lstrip("0")
        end_str = end.strftime("%I %p").lstrip("0")
        if location is not None:
            st.markdown(f"{band_name}, **{start.strftime('%a %d %b')}, {start_str} - {end_str}** @ {location}")
        else:
            st.markdown(f"{band_name}, **{start.strftime('%a %d %b')}, {start_str} - {end_str}**")

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
