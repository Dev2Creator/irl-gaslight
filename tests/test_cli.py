import io
import urllib.error

import pytest
from typer.testing import CliRunner

from irl_gaslight import identity_adapter, main
import irl_identity.oauth as oauth_module
from irl_identity.oauth import (
    GoogleOAuthConfig,
    build_auth_url,
    configure_google_client,
    create_pkce_pair,
    exchange_code,
)

runner = CliRunner()


def test_daily_renders_grounding():
    result = runner.invoke(main.app, ["daily"])
    assert result.exit_code == 0
    assert "Daily reality check" in result.stdout


def test_spot_detects_reality_denial():
    result = runner.invoke(main.app, ["spot", "That never happened. You imagined it."])
    assert result.exit_code == 0
    assert "Reality denial" in result.stdout
    assert "Grounded response" in result.stdout


def test_comeback_rejects_unknown_tone():
    result = runner.invoke(main.app, ["comeback", "--tone", "mean"])
    assert result.exit_code == 2


def test_resources_contains_safety_guidance():
    result = runner.invoke(main.app, ["resources"])
    assert result.exit_code == 0
    assert "immediate danger" in result.stdout


def test_favorites_starts_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "STATE_FILE", tmp_path / "state.json")
    result = runner.invoke(main.app, ["favorites"])
    assert result.exit_code == 0
    assert "Nothing saved yet" in result.stdout


def test_expanded_library_has_110_entries():
    total = sum(
        len(items)
        for items in (main.TACTICS, main.BOUNDARIES, main.COMEBACKS, main.SCENARIOS, main.DAILY)
    )
    assert total == 110


def test_help_lists_library_commands():
    result = runner.invoke(main.app, ["--help"])
    assert result.exit_code == 0
    assert "favorites" in result.stdout
    assert "upgrade" in result.stdout

def test_oauth_status_unlinked(monkeypatch):
    monkeypatch.setattr(identity_adapter, "google_status", lambda: None)
    result = runner.invoke(main.app, ["oauth", "status"])
    assert result.exit_code == 0
    assert "No Google account linked" in result.stdout


def test_identity_markup_uses_shared_profile(monkeypatch):
    monkeypatch.setattr(
        identity_adapter,
        "load_profile",
        lambda: {"name": "Anika", "name_pronunciation": "Ah-nee-kah", "pronouns": "she/her"},
    )
    monkeypatch.setattr(identity_adapter, "google_status", lambda: {"email": "a@example.com"})
    markup = identity_adapter.identity_markup()
    assert "Anika" in markup
    assert "she/her" in markup
    assert "a@example.com" in markup


def test_shared_oauth_uses_pkce():
    _, challenge = create_pkce_pair()
    url = build_auth_url(
        GoogleOAuthConfig(client_id="client.apps.googleusercontent.com"),
        "http://127.0.0.1:1234/callback",
        "state123",
        challenge,
    )
    assert "accounts.google.com" in url
    assert "code_challenge_method=S256" in url


def test_help_lists_identity_commands():
    result = runner.invoke(main.app, ["--help"])
    assert result.exit_code == 0
    for command in ("oauth", "profile", "avatar", "oath"):
        assert command in result.stdout


def test_token_exchange_surfaces_google_error(monkeypatch):
    error = urllib.error.HTTPError(
        "https://oauth2.googleapis.com/token",
        400,
        "Bad Request",
        {},
        io.BytesIO(b'{"error":"invalid_client","error_description":"Client authentication failed"}'),
    )

    def fail_exchange(*args, **kwargs):
        raise error

    monkeypatch.setattr(oauth_module.urllib.request, "urlopen", fail_exchange)
    with pytest.raises(RuntimeError, match="Client authentication failed"):
        exchange_code(
            GoogleOAuthConfig(client_id="client.apps.googleusercontent.com"),
            "http://127.0.0.1:1234/callback",
            "code",
            "verifier",
        )

def test_configure_google_client(tmp_path, monkeypatch):
    credentials = tmp_path / "client.json"
    credentials.write_text(
        '{"installed":{"client_id":"client.apps.googleusercontent.com","client_secret":"secret"}}',
        encoding="utf-8",
    )
    destination = tmp_path / ".irl" / "google_client.json"
    monkeypatch.setattr(oauth_module, "PROFILE_DIR", destination.parent)
    monkeypatch.setattr(oauth_module, "CLIENT_CONFIG_PATH", destination)
    config = configure_google_client(credentials)
    assert config.client_id == "client.apps.googleusercontent.com"
    assert config.client_secret == "secret"
    stored = destination.read_text(encoding="utf-8")
    assert "client.apps.googleusercontent.com" in stored
    assert "secret" in stored