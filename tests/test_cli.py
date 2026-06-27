from typer.testing import CliRunner

from irl_gaslight import identity_adapter, main
from irl_identity.oauth import GoogleOAuthConfig, build_auth_url, create_pkce_pair

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
