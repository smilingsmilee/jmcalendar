import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
from database import *
from frontend.availability_grid import availability_heatmap

def band_page():
    if st.session_state.dev_mode:
        st.title("Dev mode")

    band_id = st.session_state.band.id
    band_name = st.session_state.band.name

    st.session_state.is_leader = is_leader(st.session_state.user.id, band_id)

    show_band_name_and_invite_link(band_name, band_id)

    st.divider()

    members = get_members_from_band_id(band_id)

    show_members(band_id, members)

    st.divider()

    show_availabilities(band_id, members)

    st.divider()

    show_upcoming_rehearsals(band_id, members)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.get("confirm_quit_band"):
            st.warning("Leave this band?")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Yes", key="confirm_quit_band_yes", width="stretch"):
                    remove_member_from_band(band_id, st.session_state.user.id)
                    st.session_state.pop("confirm_quit_band", None)
                    st.session_state.pop("band", None)
                    st.session_state.page = "home"
                    st.rerun()
            with col_no:
                if st.button("No", key="confirm_quit_band_no", width="stretch"):
                    st.session_state.pop("confirm_quit_band", None)
                    st.rerun()
        else:
            if st.button("Quit band", width="stretch"):
                st.session_state.confirm_quit_band = True
                st.rerun()
    with col2:
        if st.button("To home", width="stretch"):
            st.session_state.page = "home"
            st.rerun()

    if st.session_state.is_leader:
        if st.session_state.get("confirm_delete_band"):
            st.warning("Remove all members and delete this band?")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Yes", key="confirm_delete_band_yes", width="stretch"):
                    try:
                        delete_band(band_id)
                        st.session_state.pop("confirm_delete_band", None)
                        st.session_state.pop("band", None)
                        st.session_state.page = "home"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not delete band: {e}")
            with col_no:
                if st.button("No", key="confirm_delete_band_no", width="stretch"):
                    st.session_state.pop("confirm_delete_band", None)
                    st.rerun()
        else:
            if st.button("Delete band", width="stretch"):
                st.session_state.confirm_delete_band = True
                st.rerun()
    
def show_band_name_and_invite_link(band_name, band_id):
    st.title(band_name)

    if "change_band_name_form" not in st.session_state:
        st.session_state.change_band_name_form = False

    if st.session_state.is_leader:
        if st.button("Change name"):
            st.session_state.change_band_name_form = True

        if st.session_state.change_band_name_form:
            with st.form("Change band name"):
                new_name = st.text_input("Name of band", value=band_name)
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("Save", width='stretch')
                with col2:
                    cancelled = st.form_submit_button("Cancel", width='stretch')
            if submitted:
                try:
                    update_band_name(band_id, new_name)
                    st.session_state.band.name = new_name
                    st.session_state.change_band_name_form = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not change band name: {e}")
            elif cancelled:
                st.session_state.change_band_name_form = False
                st.rerun()

    st.code(f"{app_url}?join_band={band_id}")
    st.caption("Share this link with someone to invite them to the band.")

def get_key_member_ids(band_id, members):
    if not st.session_state.is_leader:
        return set()
    all_ids = {member["id"] for member in members}
    key_member_ids = st.session_state.setdefault("band_key_members", {}).setdefault(band_id, set())
    key_member_ids &= all_ids
    return key_member_ids

def show_members(band_id, members):
    st.subheader("Members")
    if not members:
        st.info("No members yet.")
        return

    if not st.session_state.is_leader:
        for member in members:
            if member["instrument"]:
                st.markdown(f"**{member['name']}**: {member['instrument']}")
            else:
                st.markdown(f"**{member['name']}**")
    else:
        key_member_ids = get_key_member_ids(band_id, members)
        st.caption("⭐ Key members must all be available for a slot to show as free on the heatmap. This selection is only visible to you and resets when you leave the page.")
        for index, member in enumerate(members):
            col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 4, 8, 2, 4])
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
                    key=f"instrument_{member['id']}"
                )
            if instrument != (member["instrument"] or ""):
                try:
                    update_member_instrument(band_id, member["id"], instrument or None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not update {member['name']}'s instrument: {e}")
            with col5:
                key_member = st.checkbox(
                    "⭐",
                    value=member["id"] in key_member_ids,
                    key=f"key_member_{band_id}_{member['id']}"
                )
                if key_member:
                    key_member_ids.add(member["id"])
                else:
                    key_member_ids.discard(member["id"])
            with col6:
                if member["id"] != st.session_state.user.id:
                    confirm_key = f"confirm_kick_{member['id']}"
                    if st.session_state.get(confirm_key):
                        st.warning(f"Remove {member['name']} from the band?")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Yes", key=f"{confirm_key}_yes", width="stretch"):
                                remove_member_from_band(band_id, member["id"])
                                st.session_state.pop(confirm_key, None)
                                st.rerun()
                        with col_no:
                            if st.button("No", key=f"{confirm_key}_no", width="stretch"):
                                st.session_state.pop(confirm_key, None)
                                st.rerun()
                    else:
                        if st.button("Kick", key=f"kick_{member['id']}"):
                            st.session_state[confirm_key] = True
                            st.rerun()

def move_member(band_id, members, from_index, to_index):
    ids = [member["id"] for member in members]
    ids[from_index], ids[to_index] = ids[to_index], ids[from_index]
    reorder_band_members(band_id, ids)
    st.rerun()

def show_availabilities(band_id, members):
    st.subheader("Availability")

    total_members = len(members)
    if total_members == 0:
        st.info("No members yet.")
        return

    key_member_ids = get_key_member_ids(band_id, members)
    if key_member_ids:
        st.caption("Green cells mean all ⭐ key members are free at that time. Click or drag within a day to see who's available.")
    else:
        st.caption("Darker cells mean more members are free at that time. Click or drag within a day to see who's available.")

    if "band_avail_week_offset" not in st.session_state:
        st.session_state.band_avail_week_offset = 0

    band_availabilities = get_availabilities_from_band_id(band_id, members)

    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=st.session_state.band_avail_week_offset)
    week_days = [monday + timedelta(days=i) for i in range(7)]

    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("← Previous week", width='stretch', key="band_avail_prev_week"):
            st.session_state.band_avail_week_offset -= 1
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
        if st.button("Next week →", width='stretch', key="band_avail_next_week"):
            st.session_state.band_avail_week_offset += 1
            st.rerun()

    hours = [time(hour=h) for h in range(10, 22)]
    time_labels = [hour.strftime("%I %p").lstrip("0") for hour in hours]
    day_labels = [day.strftime("%a %d %b") for day in week_days]

    if key_member_ids:
        counts = [
            [
                1 if key_member_ids.issubset(band_availabilities.get(datetime.combine(day, hour).isoformat(), [])) else 0
                for day in week_days
            ]
            for hour in hours
        ]
        max_count = 1
    else:
        counts = [
            [len(band_availabilities.get(datetime.combine(day, hour).isoformat(), [])) for day in week_days]
            for hour in hours
        ]
        max_count = total_members

    grid_key = f"band_avail_heatmap_{band_id}_{monday.isoformat()}"
    clicked = availability_heatmap(days=day_labels, hours=time_labels, counts=counts, max_count=max_count, key=grid_key)

    if clicked is not None:
        row_start, row_end, col = clicked
        st.session_state.band_avail_selected_range = {
            "start": datetime.combine(week_days[col], hours[row_start]).isoformat(),
            "end": datetime.combine(week_days[col], hours[row_end]).isoformat(),
        }

    valid_timestamps = {datetime.combine(day, hour).isoformat() for day in week_days for hour in hours}
    selected_range = st.session_state.get("band_avail_selected_range")
    if selected_range and selected_range["start"] in valid_timestamps and selected_range["end"] in valid_timestamps:
        start_dt = datetime.fromisoformat(selected_range["start"])
        end_dt = datetime.fromisoformat(selected_range["end"])
        selected_timestamps = []
        curr = start_dt
        while curr <= end_dt:
            selected_timestamps.append(curr.isoformat())
            curr += timedelta(hours=1)

        start_label = start_dt.strftime("%I %p").lstrip("0")
        if start_dt == end_dt:
            st.markdown(f"**{start_dt.strftime('%a %d %b')}, {start_label}**")
        else:
            end_label = (end_dt + timedelta(hours=1)).strftime("%I %p").lstrip("0")
            st.markdown(f"**{start_dt.strftime('%a %d %b')}, {start_label} - {end_label}**")

        member_labels = [
            f"{member['name']} ({member['instrument']})" if member["instrument"] else member["name"]
            for member in members
        ]
        slot_labels = [datetime.fromisoformat(ts).strftime("%I %p").lstrip("0") for ts in selected_timestamps]

        grid = pd.DataFrame(
            {
                ts: [
                    "available" if member["id"] in band_availabilities.get(ts, []) else "unavailable"
                    for member in members
                ]
                for ts in selected_timestamps
            },
            index=member_labels,
        )

        styled_grid = grid.style.map(
            lambda status: f"background-color: {'#1e8e3e' if status == 'available' else '#d93025'}; color: transparent"
        )

        st.dataframe(
            styled_grid,
            column_config={
                ts: st.column_config.Column(label=label, width=50)
                for ts, label in zip(selected_timestamps, slot_labels)
            },
            width='stretch',
            hide_index=False,
        )

        if st.session_state.is_leader:
            rehearsal_attendance, _ = get_rehearsals_from_band_id(band_id)
            if any(ts in rehearsal_attendance for ts in selected_timestamps):
                st.caption("A rehearsal already overlaps this range.")
            elif st.button("Create rehearsal", key="band_avail_create_rehearsal"):
                for ts in selected_timestamps:
                    add_rehearsal(band_id, ts, st.session_state.user.id)
                st.session_state.pop("band_avail_selected_range", None)
                st.rerun()

    if st.button("To current week", width='stretch', key="band_avail_current_week"):
        st.session_state.band_avail_week_offset = 0
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

def show_upcoming_rehearsals(band_id, members):
    st.subheader("Upcoming Rehearsals")

    rehearsal_attendance, rehearsal_locations = get_rehearsals_from_band_id(band_id)

    now = datetime.now()
    upcoming_timestamps = [
        ts for ts in rehearsal_attendance if datetime.fromisoformat(ts) >= now
    ]

    if not upcoming_timestamps:
        st.write("No upcoming rehearsals.")
        return

    for start, end in merge_rehearsal_ranges(upcoming_timestamps):
        hours = []
        curr = start
        while curr < end:
            hours.append(curr.isoformat())
            curr += timedelta(hours=1)

        attendance_by_member = rehearsal_attendance.get(hours[0], {})
        my_attendance = attendance_by_member.get(st.session_state.user.id)

        start_str = start.strftime("%I %p").lstrip("0")
        end_str = end.strftime("%I %p").lstrip("0")
        location = rehearsal_locations.get(hours[0])
        if location is not None:
            st.markdown(f"**{start.strftime('%a %d %b')}, {start_str} - {end_str} @ {location}**")
        else:
            st.markdown(f"**{start.strftime('%a %d %b')}, {start_str} - {end_str}**")

        if st.session_state.is_leader:
            edit_location_key = f"edit_location_{hours[0]}"
            if st.session_state.get(edit_location_key):
                new_location = st.text_input(
                    "Location",
                    value=location or "",
                    key=f"location_input_{hours[0]}",
                    label_visibility="collapsed",
                    placeholder="e.g. Practice Room 2",
                )
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("Save", key=f"{edit_location_key}_save", width='stretch'):
                        try:
                            update_rehearsal_location(band_id, hours, new_location or None)
                            st.session_state.pop(edit_location_key, None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not update location: {e}")
                with col_cancel:
                    if st.button("Cancel", key=f"{edit_location_key}_cancel", width='stretch'):
                        st.session_state.pop(edit_location_key, None)
                        st.rerun()
            else:
                if st.button(
                    "Edit location" if location else "Add location",
                    key=f"{edit_location_key}_toggle",
                ):
                    st.session_state[edit_location_key] = True
                    st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "✅ I'll be there",
                key=f"attend_yes_{hours[0]}",
                type="primary" if my_attendance is True else "secondary",
                width='stretch',
            ):
                new_attendance = None if my_attendance is True else True
                for ts in hours:
                    set_rehearsal_attendance(band_id, ts, st.session_state.user.id, new_attendance)
                    remove_availability(st.session_state.user.id, ts)
                st.rerun()
        with col2:
            if st.button(
                "❌ Can't make it",
                key=f"attend_no_{hours[0]}",
                type="primary" if my_attendance is False else "secondary",
                width='stretch',
            ):
                new_attendance = None if my_attendance is False else False
                for ts in hours:
                    set_rehearsal_attendance(band_id, ts, st.session_state.user.id, new_attendance)
                st.rerun()

        for member in members:
            status = attendance_by_member.get(member["id"])
            icon = "✅" if status is True else "❌" if status is False else "⏳"
            st.write(f"{icon} {member['name']}")

        if st.session_state.is_leader:
            confirm_key = f"confirm_delete_{hours[0]}"
            if st.session_state.get(confirm_key):
                st.warning("Delete this rehearsal for everyone?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Yes, delete", key=f"{confirm_key}_yes", width='stretch'):
                        for ts in hours:
                            for member in members:
                                if attendance_by_member.get(member["id"]) is True:
                                    add_availability(member["id"], ts)
                            delete_rehearsal(band_id, ts)
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                with col2:
                    if st.button("Cancel", key=f"{confirm_key}_no", width='stretch'):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
            else:
                if st.button("Delete rehearsal", key=f"delete_{hours[0]}", width='stretch'):
                    st.session_state[confirm_key] = True
                    st.rerun()