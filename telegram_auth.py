import base64
import hashlib
import json
import secrets
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from cryptography.fernet import Fernet, InvalidToken


TELEGRAM_AUTH_URL = "https://oauth.telegram.org/auth"
TELEGRAM_SCOPES = "openid profile"
AUTH_STATE_TTL_SECONDS = 10 * 60


class TelegramAuthConfigurationError(ValueError):
    pass


class TelegramAuthStateError(ValueError):
    pass


def create_authorization_request(
    telegram_client_id,
    app_url,
    state_secret,
):
    _require_config(
        TELEGRAM_CLIENT_ID=telegram_client_id,
        APP_URL=app_url,
        AUTH_STATE_SECRET=state_secret,
    )

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = _base64url(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    )
    auth_state = _encrypt_state(
        {
            "code_verifier": code_verifier,
        },
        state_secret,
    )
    query = urlencode(
        {
            "client_id": telegram_client_id,
            "redirect_uri": app_url,
            "response_type": "code",
            "scope": TELEGRAM_SCOPES,
            "state": auth_state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    authorize_url = f"{TELEGRAM_AUTH_URL}?{query}"
    return authorize_url


def create_callback_url(app_url, auth_state):
    return _with_query_parameter(app_url, "auth_state", auth_state)


def read_callback_state(auth_state, state_secret):
    if not auth_state:
        raise TelegramAuthStateError(
            "The Telegram sign-in callback is missing its state."
        )
    if not state_secret:
        raise TelegramAuthConfigurationError(
            "AUTH_STATE_SECRET is not configured."
        )

    try:
        payload = _fernet(state_secret).decrypt(
            auth_state.encode("ascii"),
            ttl=AUTH_STATE_TTL_SECONDS,
        )
        state = json.loads(payload)
    except (InvalidToken, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
        raise TelegramAuthStateError(
            "Sign-in request is invalid or has expired."
        ) from None

    code_verifier = state.get("code_verifier")
    if not isinstance(code_verifier, str) or not code_verifier:
        raise TelegramAuthStateError(
            "Sign-in request does not contain a PKCE verifier."
        )

    return state


def _encrypt_state(payload, state_secret):
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return _fernet(state_secret).encrypt(encoded).decode("ascii")


def _fernet(state_secret):
    key = base64.urlsafe_b64encode(
        hashlib.sha256(state_secret.encode("utf-8")).digest()
    )
    return Fernet(key)


def _base64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _with_query_parameter(url, key, value):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[key] = value
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def _require_config(**values):
    missing = [name for name, value in values.items() if not value]
    if missing:
        names = ", ".join(missing)
        raise TelegramAuthConfigurationError(
            f"Missing Telegram authentication configuration: {names}"
        )
