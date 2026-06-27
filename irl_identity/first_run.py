from __future__ import annotations

import sys
from typing import Sequence

import questionary

from .oauth import config_from_env, google_status, run_google_login
from .profile import load_profile, now_iso, save_profile
from .ui import RenderOptions, ask_name_pronunciation, display_name_with_pronunciation, ensure_profile, panel

HELP_FLAGS = {"-h", "--help", "--version", "-V", "--install-completion", "--show-completion"}


def should_skip_first_run(argv: Sequence[str] | None = None) -> bool:
    args = list(sys.argv[1:] if argv is None else argv[1:])
    return any(arg in HELP_FLAGS for arg in args)


def _mark_app_seen(app_name: str, status: str) -> None:
    profile = load_profile() or {}
    first_run_apps = dict(profile.get("first_run_apps", {}))
    first_run_apps[app_name] = {
        "completed_at": now_iso(),
        "status": status,
    }
    profile["first_run_apps"] = first_run_apps
    profile["updated_at"] = now_iso()
    save_profile(profile)


def app_seen(app_name: str) -> bool:
    profile = load_profile() or {}
    first_run_apps = profile.get("first_run_apps", {})
    return isinstance(first_run_apps, dict) and app_name in first_run_apps



def ensure_name_pronunciation(options: RenderOptions) -> dict:
    profile = load_profile() or {}
    name = str(profile.get("name", "Traveler"))
    if not str(profile.get("name_pronunciation", "")).strip():
        profile["name_pronunciation"] = ask_name_pronunciation(name, options)
        profile["updated_at"] = now_iso()
        save_profile(profile)
    return profile


def print_run_identity(app_label: str, options: RenderOptions) -> None:
    profile = load_profile() or {}
    if not profile:
        return
    display_name = display_name_with_pronunciation(profile)
    pronouns = str(profile.get("pronouns", "they/them"))
    options.console.print(
        panel(
            f"The stone greets {display_name}.\nPronouns: {pronouns}",
            f"{app_label} Identity",
            options,
        )
    )
def ensure_first_run_login(
    app_name: str,
    *,
    app_label: str | None = None,
    argv: Sequence[str] | None = None,
    options: RenderOptions | None = None,
) -> None:
    """Run the shared IRL profile + Google OAuth ritual once per app.

    This is intentionally soft-fail: if OAuth is cancelled or unavailable, the
    app keeps running and the first-run ritual does not nag on every launch.
    """
    if should_skip_first_run(argv):
        return

    options = options or RenderOptions()
    label = app_label or app_name

    try:
        ensure_profile(app_name, options)
        ensure_name_pronunciation(options)
    except Exception:
        # If an app is being used in a non-interactive environment, do not brick it.
        return

    if app_seen(app_name):
        print_run_identity(label, options)
        return

    if google_status():
        _mark_app_seen(app_name, "profile-ready-google-linked")
        print_run_identity(label, options)
        return

    console = options.console
    console.print(
        panel(
            f"{label} is entering the IRL Universe for the first time.\n\n"
            "Link Google once so the profile can travel across the ecosystem.\n"
            "The stone opens a browser, waits locally, then seals the identity.",
            "IRL First-Time Login",
            options,
        )
    )

    try:
        approved = questionary.confirm("Link Google now?", default=True, qmark="🗿").ask()
    except Exception:
        approved = False

    if not approved:
        _mark_app_seen(app_name, "google-skipped")
        console.print(panel("Skipped for now. The app will continue.", "IRL Login", options))
        print_run_identity(label, options)
        return

    try:
        result = run_google_login(config_from_env(), open_browser=True)
        google = result.get("google", {})
        who = google.get("name") or google.get("email") or "Google traveler"
        _mark_app_seen(app_name, "google-linked")
        console.print(panel(f"Linked: {who}\nWelcome to {label}.", "OAuth Sealed", options))
        print_run_identity(label, options)
    except Exception as exc:
        _mark_app_seen(app_name, "google-failed")
        console.print(panel(f"Google login did not finish.\n{exc}\n\nContinuing without link.", "OAuth Not Sealed", options))
        print_run_identity(label, options)
