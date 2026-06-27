"""Bridge IRL Gaslight to the shared IRL ecosystem identity and OAuth system."""

from __future__ import annotations

import sys
import typer
from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from irl_identity.avatars import get_avatar
from irl_identity.first_run import app_seen, ensure_first_run_login
from irl_identity.oauth import config_from_env, google_status, run_google_login, unlink_google
from irl_identity.profile import load_profile
from irl_identity.ui import RenderOptions, confirm_reset, edit_profile, ensure_profile, show_oath, show_profile

APP_NAME = "irl-gaslight"
APP_LABEL = "IRL Gaslight"
ACCENT = "#F29265"
CREAM = "#D7C0AA"
BORDER = "#6B4E36"
MUTED = "#614B39"

oauth_app = typer.Typer(help="Link or unlink Google from the shared IRL identity.")
profile_app = typer.Typer(help="View, edit, or reset your shared IRL profile.", invoke_without_command=True)


def _options() -> RenderOptions:
    return RenderOptions()


def _panel(body: str, title: str) -> Panel:
    return Panel(body, title=title, border_style=BORDER, box=box.SQUARE, padding=(1, 2))


def run_first_launch() -> None:
    """Run the shared ritual once; failures never block the defensive CLI."""
    try:
        if not app_seen(APP_NAME):
            ensure_first_run_login(APP_NAME, app_label=APP_LABEL, argv=sys.argv)
    except Exception:
        return


def identity_markup() -> str:
    profile = load_profile() or {}
    google = google_status() or {}
    if not profile:
        return f"[{MUTED}]Identity   [/{MUTED}][{CREAM}]Traveler (not created)[/{CREAM}]"
    name = escape(str(profile.get("name") or "Traveler"))
    pronunciation = escape(str(profile.get("name_pronunciation") or "").strip())
    pronouns = escape(str(profile.get("pronouns") or "").strip())
    details = ""
    if pronunciation and pronunciation.casefold() != name.casefold():
        details += f" [{MUTED}]({pronunciation})[/{MUTED}]"
    if pronouns:
        details += f" [{CREAM}]- {pronouns}[/{CREAM}]"
    account = escape(str(google.get("email") or "Google not linked"))
    return (
        f"[{MUTED}]Identity   [/{MUTED}][{ACCENT}]{name}[/{ACCENT}]{details}\n"
        f"[{MUTED}]Account    [/{MUTED}][{CREAM}]{account}[/{CREAM}]"
    )


def show_identity_profile() -> None:
    profile = ensure_profile(APP_NAME, _options())
    show_profile(profile, APP_NAME, _options())


def show_oauth_status() -> None:
    google = google_status()
    if not google:
        Console().print(_panel("No Google account linked.\n\nRun: irl-gaslight oauth login", "OAuth Status"))
        return
    body = (
        f"Linked: yes\n"
        f"Name: {escape(str(google.get('name', '')))}\n"
        f"Email: {escape(str(google.get('email', '')))}\n"
        f"Linked at: {escape(str(google.get('linked_at', '')))}\n\n"
        "Tokens remain local under ~/.irl."
    )
    Console().print(_panel(body, "OAuth Status"))


@oauth_app.command("login")
def oauth_login(
    no_browser: bool = typer.Option(False, "--no-browser", help="Print the Google URL instead of opening it."),
) -> None:
    ensure_profile(APP_NAME, _options())
    Console().print(_panel("Opening Google sign-in. Return here after the browser confirms the link.", "IRL Google OAuth"))
    try:
        result = run_google_login(
            config_from_env(),
            open_browser=not no_browser,
            on_auth_url=Console().print if no_browser else None,
        )
    except Exception as exc:
        Console().print(_panel(escape(str(exc)), "OAuth Failed"))
        raise typer.Exit(code=1) from exc
    google = result.get("google", {})
    who = google.get("name") or google.get("email") or "Google traveler"
    Console().print(_panel(f"Linked: {escape(str(who))}\nEmail: {escape(str(google.get('email', '')))}\nProvider: Google", "OAuth Sealed"))


@oauth_app.command("status")
def oauth_status() -> None:
    show_oauth_status()


@oauth_app.command("logout")
def oauth_logout() -> None:
    removed = unlink_google()
    message = "Google link removed from this terminal." if removed else "No Google link was stored here."
    Console().print(_panel(message, "OAuth Logout"))


@profile_app.callback(invoke_without_command=True)
def profile_main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        show_identity_profile()


@profile_app.command("edit")
def profile_edit() -> None:
    show_profile(edit_profile(APP_NAME, _options()), APP_NAME, _options())


@profile_app.command("reset")
def profile_reset() -> None:
    confirm_reset(_options())


def avatar() -> None:
    """Show the active shared IRL avatar."""
    profile = ensure_profile(APP_NAME, _options())
    avatar_obj = get_avatar(str(profile.get("avatar_id", "moai_block")))
    Console().print(_panel(f"{avatar_obj.preview()}\n\n{avatar_obj.short_description}", avatar_obj.display_name))


def oath() -> None:
    """Read and optionally renew the shared IRL Wisdom oath."""
    show_oath(_options())


def register_identity_commands(app: typer.Typer) -> None:
    app.add_typer(oauth_app, name="oauth")
    app.add_typer(profile_app, name="profile")
    app.command("avatar")(avatar)
    app.command("oath")(oath)
