import streamlit as st
from types import SimpleNamespace
import uuid
import jwt
import requests
from database import *
from telegram_auth import (
    TelegramAuthConfigurationError,
    TelegramAuthStateError,
    create_callback_url,
    read_callback_state,
)
from views.signin import signin_page
from views.home import home_page
from views.band import band_page

def main():
    st.set_page_config(page_title="JMCalendar", page_icon=":house:")

    if "user" not in st.session_state:
        st.session_state.user = None
    if "page" not in st.session_state:
        st.session_state.page = "signin"

    auth_error = (
        st.query_params.get("error_description")
        or st.query_params.get("error")
    )
    if auth_error:
        handle_authentication_error()

    code = st.query_params.get("code")
    if code:
        authenticate_user(
            code,
            st.query_params.get("state") or st.query_params.get("auth_state"),
        )

    join_band_id = st.query_params.get("join_band")

    if join_band_id:
        handle_band_invite(join_band_id)

    if st.session_state.user is not None and st.session_state.page == "signin":
        st.session_state.page = "home"
    elif (
        st.session_state.user is None
        and st.session_state.page in {"home", "band"}
    ):
        st.session_state.page = "signin"

    pages = {
        "signin": signin_page,
        "home": home_page,
        "band": band_page
    }
    page = pages.get(st.session_state.page)
    if page:
        page()
    else:
        st.error(f"Unknown page: {st.session_state.page}")

# new tele auth
def authenticate_user(code, auth_state):
    try:
        state = read_callback_state(auth_state, st.secrets.get("AUTH_STATE_SECRET"))
        user = exchange_telegram_code(code, state["code_verifier"], auth_state)
        ensure_user_profile(user)
        st.session_state.user = user
        st.session_state.page = "home"
        stale_pending_band_id = st.session_state.pop("pending_join_band", None)
        pending_band_id = state.get("join_band") or stale_pending_band_id
        if pending_band_id:
            handle_band_invite(pending_band_id)
    except (TelegramAuthConfigurationError, TelegramAuthStateError) as e:
        st.error(str(e))
        st.session_state.page = "signin"
    except Exception as e:
        st.error("Telegram sign-in could not be completed. If this problem persists, please contact JMExco.")
        # st.error(f"Telegram sign-in could not be completed: {e}")
        st.session_state.page = "signin"
    finally:
        st.query_params.clear()

def handle_authentication_error():
    st.query_params.clear()
    st.session_state.page = "signin"
    st.error("Telegram sign-in was cancelled or could not be completed.")


def exchange_telegram_code(code, code_verifier, auth_state):
    client_id = st.secrets.get("TELEGRAM_CLIENT_ID")
    client_secret = st.secrets.get("TELEGRAM_CLIENT_SECRET")
    callback_url = st.secrets.get("APP_URL")
    token = requests.post(
        "https://oauth.telegram.org/token",
        data={"grant_type": "authorization_code", "code": code,
              "redirect_uri": callback_url, "client_id": client_id,
              "code_verifier": code_verifier},
        auth=(client_id, client_secret), timeout=15,
    )
    token.raise_for_status()
    token_data = token.json()
    id_token = token_data.get("id_token")
    if not id_token:
        details = token_data.get("error_description") or token_data.get("error")
        if not details:
            details = ", ".join(sorted(token_data.keys())) or "empty response"
        raise ValueError(f"Telegram did not return an ID token ({details}).")
    signing_key = jwt.PyJWKClient("https://oauth.telegram.org/.well-known/jwks.json").get_signing_key_from_jwt(id_token)
    claims = jwt.decode(id_token, signing_key.key, algorithms=["RS256"], audience=client_id,
                        issuer="https://oauth.telegram.org")
    # Existing Supabase tables use UUIDs for user IDs. Telegram's `sub` is a
    # numeric identifier, so derive a stable UUID from it for database use.
    user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"telegram:{claims['sub']}"))
    return SimpleNamespace(id=user_id, user_metadata={
        "name": claims.get("name"),
        "preferred_username": claims.get("preferred_username"),
        # Temporary compatibility value while users.email remains NOT NULL.
        "email": f"telegram_{claims['sub']}@users.invalid",
    })

def handle_band_invite(band_id):
    if st.session_state.user is None:
        st.session_state.pending_join_band = band_id
        if st.session_state.get("invite_prompt_shown") != band_id:
            st.info("Sign in to accept this band invite.")
            st.session_state.page = "signin"
            st.session_state.invite_prompt_shown = band_id
        return

    try:
        join_band(st.session_state.user.id, band_id, is_leader=False)
        st.session_state.band = Band(id=band_id, name=get_band_name_from_band_id(band_id))
        st.session_state.page = "band"
        st.session_state.pop("invite_prompt_shown", None)
    except Exception as e:
        st.error(f"Could not join band: {e}")
    finally:
        st.query_params.clear()

if __name__ == "__main__":
    main()
