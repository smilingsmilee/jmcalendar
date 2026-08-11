import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
from database import *

def band_page():
    if st.session_state.dev_mode:
        st.title("Dev mode")

    band_id = st.session_state.band.id

    st.session_state.is_leader = is_leader(st.session_state.user.id, band_id)

    st.title(f"{st.session_state.band.name}")
    st.code(f"{app_url}?join_band={band_id}")
    st.caption("Share this link with someone to invite them to the band.")

    st.divider()

    show_members(band_id)

    st.divider()

    if st.session_state.is_leader:
        show_availabilities(band_id)

    st.divider()

    show_upcoming_rehearsals(band_id)

    st.divider()

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
    st.caption("Select times in the grid, then confirm to schedule the rehearsals.")

    members = get_members_from_band_id(band_id)
    if not members:
        st.info("No members yet.")
        return

    band_availabilities = get_availabilities_from_band_id(band_id)

    if "rehearsal_date_slots" not in st.session_state:
        st.session_state.rehearsal_date_slots = [0]
        st.session_state.rehearsal_date_next_id = 1

    slots = st.session_state.rehearsal_date_slots

    if st.session_state.pop("clear_availability_selection", False):
        for slot_id in slots:
            st.session_state[f"avail_grid_{slot_id}"] = {"selection": {"rows": [], "columns": [], "cells": []}}

    kept_slots = []
    last_date_value = None
    all_selected_timestamps = set()

    for slot_id in slots:
        col1, col2 = st.columns([1, 4])
        with col1:
            date_value = st.date_input("Date", value=None, format="DD/MM/YYYY", key=f"rehearsal_date_{slot_id}")
        with col2:
            if date_value is not None:
                st.markdown(f"**{date_value.strftime('%a %d %b')}**")

                hours = [time(hour=h) for h in range(10, 22)]
                timestamps = [datetime.combine(date_value, hour).isoformat() for hour in hours]
                time_labels = [hour.strftime("%I %p").lstrip("0") for hour in hours]
                member_labels = [
                    f"{member['name']} ({member['instrument']})" if member["instrument"] else member["name"]
                    for member in members
                ]

                grid = pd.DataFrame(
                    {
                        ts: [
                            "available" if member["id"] in band_availabilities.get(ts, []) else "unavailable"
                            for member in members
                        ]
                        for ts in timestamps
                    },
                    index=member_labels,
                )

                styled_grid = grid.style.map(
                    lambda status: f"background-color: {'#1e8e3e' if status == 'available' else '#d93025'}; color: transparent"
                )

                grid_key = f"avail_grid_{slot_id}"
                event = st.dataframe(
                    styled_grid,
                    column_config={
                        ts: st.column_config.Column(label=label, width=50)
                        for ts, label in zip(timestamps, time_labels)
                    },
                    width='stretch',
                    hide_index=False,
                    on_select="rerun",
                    selection_mode="multi-column",
                    key=grid_key,
                )
                all_selected_timestamps.update(event.selection.columns)

        last_date_value = date_value
        if date_value is not None:
            kept_slots.append(slot_id)

    if all_selected_timestamps:
        st.caption("Selected:")
        for start, end in merge_rehearsal_ranges(all_selected_timestamps):
            start_str = start.strftime("%I %p").lstrip("0")
            end_str = end.strftime("%I %p").lstrip("0")
            st.markdown(f"**{start.strftime('%a %d %b')}, {start_str} - {end_str}**")

        location = st.text_input(
            "Location",
            key="rehearsal_location_input",
            placeholder="e.g. Practice Room 2 (optional)",
        )

        col_confirm, col_clear = st.columns(2)
        with col_confirm:
            if st.button("Confirm rehearsals", width='stretch'):
                try:
                    for timestamp in all_selected_timestamps:
                        add_rehearsal(band_id, timestamp, st.session_state.user.id, location or None)
                    st.session_state.clear_availability_selection = True
                    st.session_state.pop("rehearsal_location_input", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not schedule rehearsals: {e}")
        with col_clear:
            if st.button("Clear selection", width='stretch'):
                st.session_state.clear_availability_selection = True
                st.session_state.pop("rehearsal_location_input", None)
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
    st.subheader("Upcoming Rehearsals")

    members = get_members_from_band_id(band_id)
    rehearsal_attendance = get_rehearsals_from_band_id(band_id)
    rehearsal_locations = get_rehearsal_locations_from_band_id(band_id)

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