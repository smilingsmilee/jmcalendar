import base64
import hashlib
import json
import secrets
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


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
    join_band_id=None,
):
    _require_config(
        TELEGRAM_CLIENT_ID=telegram_client_id,
        APP_URL=app_url,
        AUTH_STATE_SECRET=state_secret,
    )

    code_verifier = secrets.token_urlsafe(32)
    code_challenge = _base64url(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    )
    state_payload = {"code_verifier": code_verifier}
    if join_band_id:
        state_payload["join_band"] = join_band_id
    auth_state = _encrypt_state(
        state_payload,
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
        token = _b64url_decode(auth_state)
        nonce, ciphertext = token[:12], token[12:]
        payload = AESGCM(_aes_key(state_secret)).decrypt(nonce, ciphertext, None)
        state = json.loads(payload)
        issued_at = state.pop("ts")
        if time.time() - issued_at > AUTH_STATE_TTL_SECONDS:
            raise ValueError("state expired")
    except (InvalidTag, UnicodeError, ValueError, TypeError, KeyError, json.JSONDecodeError):
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
    payload = {**payload, "ts": int(time.time())}
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_aes_key(state_secret)).encrypt(nonce, encoded, None)
    return _base64url(nonce + ciphertext)


def _aes_key(state_secret):
    return hashlib.sha256(state_secret.encode("utf-8")).digest()


def _base64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


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
