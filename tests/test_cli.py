from typer.testing import CliRunner

from irl_gaslight import main

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