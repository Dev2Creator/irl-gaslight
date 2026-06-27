from __future__ import annotations

import typer

from .avatars import get_avatar
from .oauth import config_from_env, google_status, oauth_setup_help, run_google_login, unlink_google
from .profile import increment_ritual, unlock_avatar
from .ui import RenderOptions, confirm_reset, edit_profile, ensure_profile, panel, show_oath, show_profile


def options_from_flags(
    plain: bool = False,
    no_emoji: bool = False,
    compact: bool = False,
    no_color: bool = False,
) -> RenderOptions:
    return RenderOptions(plain=plain, no_emoji=no_emoji, compact=compact, no_color=no_color)


def add_common_commands(app: typer.Typer, app_name: str) -> None:
    profile_app = typer.Typer(help="View, edit, or reset your shared IRL profile.")
    app.add_typer(profile_app, name="profile")

    @app.callback(invoke_without_command=True)
    def main(
        ctx: typer.Context,
        plain: bool = typer.Option(False, "--plain", help="Use simpler boxes and rendering."),
        no_emoji: bool = typer.Option(False, "--no-emoji", help="Replace emoji with text labels."),
        compact: bool = typer.Option(False, "--compact", help="Use a shorter profile greeting."),
        no_color: bool = typer.Option(False, "--no-color", help="Disable terminal color."),
    ) -> None:
        options = options_from_flags(plain, no_emoji, compact, no_color)
        if ctx.invoked_subcommand is None:
            profile = ensure_profile(app_name, options)
            show_profile(profile, app_name, options)

    @profile_app.callback(invoke_without_command=True)
    def profile_main(
        ctx: typer.Context,
        plain: bool = False,
        no_emoji: bool = False,
        compact: bool = False,
        no_color: bool = False,
    ) -> None:
        options = options_from_flags(plain, no_emoji, compact, no_color)
        if ctx.invoked_subcommand is None:
            show_profile(ensure_profile(app_name, options), app_name, options)

    @profile_app.command("edit")
    def profile_edit(
        plain: bool = False,
        no_emoji: bool = False,
        compact: bool = False,
        no_color: bool = False,
    ) -> None:
        options = options_from_flags(plain, no_emoji, compact, no_color)
        show_profile(edit_profile(app_name, options), app_name, options)

    @profile_app.command("reset")
    def profile_reset(
        plain: bool = False,
        no_emoji: bool = False,
        compact: bool = False,
        no_color: bool = False,
    ) -> None:
        confirm_reset(options_from_flags(plain, no_emoji, compact, no_color))

    @app.command("avatar")
    def avatar(
        plain: bool = False,
        no_emoji: bool = False,
        compact: bool = False,
        no_color: bool = False,
    ) -> None:
        options = options_from_flags(plain, no_emoji, compact, no_color)
        profile = ensure_profile(app_name, options)
        avatar_obj = get_avatar(str(profile.get("avatar_id", "moai_block")))
        options.console.print(panel(avatar_obj.preview(options.no_emoji), avatar_obj.display_name, options))
        options.console.print(avatar_obj.short_description)

    @app.command("oath")
    def oath(
        plain: bool = False,
        no_emoji: bool = False,
        compact: bool = False,
        no_color: bool = False,
    ) -> None:
        show_oath(options_from_flags(plain, no_emoji, compact, no_color))


identity_app = typer.Typer(help="Shared IRL ecosystem identity launcher.")
oauth_app = typer.Typer(help="Google OAuth ritual for the shared IRL identity.")
wisdom_app = typer.Typer(help="IRL Wisdom™ command line app.")
besty_app = typer.Typer(help="IRL Besty command line app.")
transpower_app = typer.Typer(help="Trans Power command line app.")

add_common_commands(identity_app, "irl")
identity_app.add_typer(oauth_app, name="oauth")
add_common_commands(wisdom_app, "irl-wisdom")
add_common_commands(besty_app, "besty")
add_common_commands(transpower_app, "transpower")


@oauth_app.command("login")
def oauth_login(
    no_browser: bool = typer.Option(False, "--no-browser", help="Print the Google URL instead of opening a browser."),
    plain: bool = False,
    no_emoji: bool = False,
    compact: bool = False,
    no_color: bool = False,
) -> None:
    options = options_from_flags(plain, no_emoji, compact, no_color)
    ensure_profile("irl", options)
    config = config_from_env()
    if config is None:
        options.console.print(panel(oauth_setup_help(), "Google OAuth Setup", options))
        raise typer.Exit(code=1)
    options.console.print(
        panel(
            "Opening Google sign-in.\nReturn here when the browser says the ritual is sealed.",
            "IRL Google OAuth",
            options,
        )
    )
    try:
        result = run_google_login(
            config,
            open_browser=not no_browser,
            on_auth_url=options.console.print if no_browser else None,
        )
    except Exception as exc:
        options.console.print(panel(str(exc), "OAuth Failed", options))
        raise typer.Exit(code=1) from exc
    google = result.get("google", {})
    name = google.get("name") or google.get("email") or "Google traveler"
    options.console.print(
        panel(
            f"Linked: {name}\nEmail: {google.get('email', 'unknown')}\nProvider: Google",
            "OAuth Sealed",
            options,
        )
    )


@oauth_app.command("status")
def oauth_status(
    plain: bool = False,
    no_emoji: bool = False,
    compact: bool = False,
    no_color: bool = False,
) -> None:
    options = options_from_flags(plain, no_emoji, compact, no_color)
    google = google_status()
    if not google:
        options.console.print(panel("No Google account linked yet.\nRun: irl-identity oauth login", "OAuth Status", options))
        return
    options.console.print(
        panel(
            f"Linked: yes\nName: {google.get('name', '')}\nEmail: {google.get('email', '')}\nLinked at: {google.get('linked_at', '')}",
            "OAuth Status",
            options,
        )
    )


@oauth_app.command("logout")
def oauth_logout(
    plain: bool = False,
    no_emoji: bool = False,
    compact: bool = False,
    no_color: bool = False,
) -> None:
    options = options_from_flags(plain, no_emoji, compact, no_color)
    removed = unlink_google()
    message = "Google link removed from this terminal." if removed else "No Google link was stored here."
    options.console.print(panel(message, "OAuth Logout", options))


@wisdom_app.command("egg")
def egg() -> None:
    ensure_profile("irl-wisdom", RenderOptions())
    _, unlocked = unlock_avatar("egg_hunter")
    msg = "Egg Hunter avatar unlocked." if unlocked else "Egg Hunter already walks with you."
    RenderOptions().console.print(msg)


@wisdom_app.command("moai")
def moai() -> None:
    options = RenderOptions()
    ensure_profile("irl-wisdom", options)
    count = increment_ritual("moai")
    if count >= 10:
        _, unlocked = unlock_avatar("moai_chosen")
        options.console.print("Moai Chosen avatar unlocked." if unlocked else "The chosen stone nods again.")
    else:
        options.console.print(f"Moai ritual {count}/10. The stone is considering your application.")


@wisdom_app.command("nuke")
def nuke() -> None:
    ensure_profile("irl-wisdom", RenderOptions())
    _, unlocked = unlock_avatar("wisdom_nuke")
    RenderOptions().console.print("Wisdom Nuke avatar unlocked." if unlocked else "Wisdom Nuke already armed. Calmly.")


if __name__ == "__main__":
    identity_app()
