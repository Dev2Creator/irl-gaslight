from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from .profile import PROFILE_DIR, load_profile, now_iso, save_profile

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_SCOPES = ("openid", "email", "profile")
DEFAULT_CLIENT_ID = "715633377290-2g0losgju3k8uptldf4o1dihae0tni5b.apps.googleusercontent.com"
TOKEN_PATH = PROFILE_DIR / "google_oauth.json"


@dataclass(frozen=True)
class GoogleOAuthConfig:
    client_id: str
    client_secret: str | None = None
    scopes: tuple[str, ...] = DEFAULT_SCOPES
    timeout_seconds: int = 180


def config_from_env() -> GoogleOAuthConfig | None:
    client_id = os.getenv("IRL_GOOGLE_CLIENT_ID", DEFAULT_CLIENT_ID).strip()
    if not client_id:
        return None
    client_secret = os.getenv("IRL_GOOGLE_CLIENT_SECRET", "").strip() or None
    scopes = tuple(os.getenv("IRL_GOOGLE_SCOPES", " ".join(DEFAULT_SCOPES)).split())
    return GoogleOAuthConfig(client_id=client_id, client_secret=client_secret, scopes=scopes)


def oauth_setup_help() -> str:
    return "\n".join(
        [
            "Google OAuth is not configured yet.",
            "",
            "Create a Google OAuth Desktop client, then set:",
            "  IRL_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com",
            "",
            "Optional:",
            "  IRL_GOOGLE_CLIENT_SECRET=your-desktop-client-secret",
            "  IRL_GOOGLE_SCOPES=openid email profile",
            "",
            "Redirect URI used by this terminal flow:",
            "  http://127.0.0.1:<random-port>/callback",
            "",
            "The terminal opens Google, waits locally, then seals the profile.",
        ]
    )


def _base64_url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def create_pkce_pair() -> tuple[str, str]:
    verifier = _base64_url(secrets.token_bytes(48))
    challenge = _base64_url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def decode_jwt_payload(token: str) -> dict[str, Any]:
    try:
        payload = token.split(".")[1]
        padding = "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload + padding).decode("utf-8"))
    except (IndexError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return {}


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    server: "OAuthCallbackServer"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802 - stdlib API name
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        self.server.oauth_result = {key: values[0] for key, values in params.items() if values}
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"""
<!doctype html>
<title>IRL OAuth Complete</title>
<body style="background:#090807;color:#d8b08a;font-family:monospace;padding:2rem">
<h1>IRL OAuth sealed.</h1>
<p>You can return to the terminal. The stone remembers.</p>
</body>
"""
        )
        threading.Thread(target=self.server.shutdown, daemon=True).start()


class OAuthCallbackServer(ThreadingHTTPServer):
    oauth_result: dict[str, str] | None = None


def wait_for_callback(timeout_seconds: int) -> tuple[str, dict[str, str]]:
    server = OAuthCallbackServer(("127.0.0.1", 0), OAuthCallbackHandler)
    _, port = server.server_address
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if server.oauth_result is not None:
            result = server.oauth_result
            server.server_close()
            return redirect_uri, result
        time.sleep(0.1)
    server.shutdown()
    server.server_close()
    raise TimeoutError("Google OAuth timed out while waiting for the local callback.")


def build_auth_url(config: GoogleOAuthConfig, redirect_uri: str, state: str, challenge: str) -> str:
    params = {
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(config.scopes),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code(config: GoogleOAuthConfig, redirect_uri: str, code: str, verifier: str) -> dict[str, Any]:
    payload = {
        "client_id": config.client_id,
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    if config.client_secret:
        payload["client_secret"] = config.client_secret
    request = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed Google HTTPS endpoint
        return json.loads(response.read().decode("utf-8"))


def save_google_tokens(tokens: dict[str, Any]) -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(tokens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def remove_google_tokens() -> bool:
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        return True
    return False


def google_status() -> dict[str, Any] | None:
    profile = load_profile() or {}
    google = profile.get("google")
    if isinstance(google, dict) and google.get("linked"):
        return google
    return None


def unlink_google() -> bool:
    removed_tokens = remove_google_tokens()
    profile = load_profile() or {}
    had_profile_link = bool(profile.get("google"))
    profile.pop("google", None)
    profile["updated_at"] = now_iso()
    save_profile(profile)
    return removed_tokens or had_profile_link


def run_google_login(
    config: GoogleOAuthConfig | None = None,
    *,
    open_browser: bool = True,
    on_auth_url: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    config = config or config_from_env()
    if config is None:
        raise RuntimeError(oauth_setup_help())

    verifier, challenge = create_pkce_pair()
    state = secrets.token_urlsafe(32)
    result_holder: dict[str, Any] = {}

    server = OAuthCallbackServer(("127.0.0.1", 0), OAuthCallbackHandler)
    _, port = server.server_address
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    auth_url = build_auth_url(config, redirect_uri, state, challenge)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if on_auth_url is not None:
        on_auth_url(auth_url)
    if open_browser:
        webbrowser.open(auth_url)
    else:
        result_holder["auth_url"] = auth_url

    deadline = time.time() + config.timeout_seconds
    while time.time() < deadline:
        if server.oauth_result is not None:
            callback = server.oauth_result
            break
        time.sleep(0.1)
    else:
        server.shutdown()
        server.server_close()
        raise TimeoutError("Google OAuth timed out while waiting for the local callback.")

    server.server_close()
    if callback.get("state") != state:
        raise RuntimeError("OAuth state mismatch. The stone rejected the callback.")
    if "error" in callback:
        raise RuntimeError(f"Google OAuth error: {callback['error']}")
    code = callback.get("code")
    if not code:
        raise RuntimeError("Google OAuth callback did not include an authorization code.")

    tokens = exchange_code(config, redirect_uri, code, verifier)
    save_google_tokens(tokens)
    claims = decode_jwt_payload(str(tokens.get("id_token", "")))
    google = {
        "linked": True,
        "provider": "google",
        "email": claims.get("email", ""),
        "email_verified": bool(claims.get("email_verified", False)),
        "name": claims.get("name", ""),
        "given_name": claims.get("given_name", ""),
        "picture": claims.get("picture", ""),
        "sub": claims.get("sub", ""),
        "linked_at": now_iso(),
        "scopes": list(config.scopes),
    }
    profile = load_profile() or {}
    profile["google"] = google
    if google["name"] and profile.get("name") in (None, "", "Traveler"):
        profile["name"] = google["name"]
    profile["updated_at"] = now_iso()
    save_profile(profile)
    result_holder["google"] = google
    return result_holder
