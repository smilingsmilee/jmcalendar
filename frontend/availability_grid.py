import os
import streamlit as st
import streamlit.components.v1 as components

_frontend_dir = os.path.dirname(os.path.abspath(__file__))
_component_func = components.declare_component("availability_grid", path=_frontend_dir)


def availability_grid(days, hours, values, key):
    result = _component_func(days=days, hours=hours, values=values, key=key, default=None)
    if result is None:
        return None

    nonce_key = f"_{key}_availability_grid_nonce"
    if result.get("nonce") == st.session_state.get(nonce_key):
        return None
    st.session_state[nonce_key] = result.get("nonce")
    return result.get("values")