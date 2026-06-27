from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import questionary
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .avatars import Avatar, available_avatars, get_avatar
from .profile import create_profile, load_profile, reset_profile, save_profile


THEME = {
    "amber": "#d8b08a",
    "orange": "#ff9b63",
    "burnt": "#b85f3f",
    "dark": "#090807",
    "dim": "#6f4d37",
    "green": "#77c88a",
    "rose": "#ff8da1",
    "cyan": "#76d1d1",
    "gray": "#9c958e",
}


@dataclass(frozen=True)
class RenderOptions:
    plain: bool = False
    no_emoji: bool = False
    compact: bool = False
    no_color: bool = False

    @property
    def console(self) -> Console:
        return Console(color_system=None if self.no_color else "auto")


def icon(value: str, options: RenderOptions) -> str:
    if not options.no_emoji:
        return value
    return {
        "🗿": "[MOAI]",
        "🌱": "[SEED]",
        "🎻": "[VIOLIN]",
        "✨": "*",
        "☠": "[SKULL]",
    }.get(value, value)


def styled(text: str, style: str, options: RenderOptions) -> Text | str:
    return text if options.no_color else Text(text, style=style)


def panel(content: str | Table | Text, title: str, options: RenderOptions) -> Panel:
    return Panel(
        content,
        title=title,
        border_style="none" if options.no_color else THEME["dim"],
        box=box.ASCII if options.plain else box.DOUBLE,
        padding=(0, 1),
    )


def welcome_screen(app_name: str, options: RenderOptions) -> None:
    console = options.console
    title = "IRL FIRST LAUNCH"
    body = "\n".join(
        [
            "Welcome, traveler.",
            "",
            "Before entering the IRL Universe,",
            "we create your terminal identity.",
            "",
            "Name. Pronouns. Avatar. Oath. Google link.",
            "Not a login form — a tiny character creation ritual.",
        ]
    )
    console.print(panel(body, title, options))
    if not options.compact:
        console.print(
            styled(
                f"{icon('🗿', options)} The amber monitor wakes for {app_name}.",
                THEME["orange"],
                options,
            )
        )


def ask_text(prompt: str, default: str | None = None) -> str:
    return questionary.text(prompt, default=default or "").ask() or default or ""


def ask_choice(prompt: str, choices: Iterable[str]) -> str:
    return questionary.select(prompt, choices=list(choices)).ask() or list(choices)[0]


def choose_pronouns() -> str:
    choices = [
        "she/her        She, her",
        "he/him         He, him",
        "they/them      They, them",
        "she/they       She or they",
        "he/they        He or they",
        "any pronouns   Any respectful pronouns",
        "custom         Write your own",
    ]
    selected = ask_choice("Choose your pronouns:", choices)
    value = selected.split()[0]
    if value == "custom":
        return ask_text("Enter your pronouns:", "xe/xem")
    return value


def avatar_label(avatar: Avatar) -> str:
    return f"{avatar.display_name:<16} {avatar.short_description}"


def choose_avatar(options: RenderOptions, unlocked: list[str] | None = None) -> str:
    console = options.console
    avatars = available_avatars(unlocked)
    selected_label = ask_choice(
        "Choose your CLI avatar:",
        [avatar_label(avatar) for avatar in avatars],
    )
    selected_index = [avatar_label(avatar) for avatar in avatars].index(selected_label)
    avatar = avatars[selected_index]
    console.print()
    console.print(
        panel(
            f"{avatar.display_name.upper()}\n\n{avatar.preview(options.no_emoji)}\n\nThe stone remembers.",
            "Avatar Selected",
            options,
        )
    )
    return avatar.avatar_id


OATH = [
    "I seek useful knowledge.",
    "I question my assumptions.",
    "I respect evidence.",
    "I credit contributors.",
    "I learn from mistakes.",
    "I help when I can.",
    "I leave places better than I found them.",
    "I do not chase unnecessary drama.",
    "I touch grass when required.",
]


def show_oath(options: RenderOptions) -> bool:
    console = options.console
    oath_text = "\n".join(OATH)
    oath_text += "\n\nThe stone does not ask for perfection.\nOnly progress."
    console.print(panel(oath_text, "Wisdom Oath", options))
    return bool(questionary.confirm("Do you accept the Wisdom Oath?", default=True).ask())



def display_name_with_pronunciation(profile: dict) -> str:
    name = str(profile.get("name", "Traveler"))
    pronunciation = str(profile.get("name_pronunciation", "")).strip()
    if pronunciation and pronunciation.lower() != name.lower():
        return f"{name} ({pronunciation})"
    return name


def ask_name_pronunciation(name: str, options: RenderOptions) -> str:
    clean_name = (name or "Traveler").strip() or "Traveler"
    options.console.print(
        panel(
            f"How should the terminal say {clean_name}?\nExample: Ah-nee-kah, Uh-nee-kuh, A-ni-ka.",
            "Name Pronunciation",
            options,
        )
    )
    return ask_text("Name pronunciation:", clean_name).strip() or clean_name


def profile_table(profile: dict, options: RenderOptions) -> Table:
    table = Table(
        title="IRL PROFILE",
        box=box.ROUNDED if not options.plain else box.ASCII,
        show_header=False,
        border_style="none" if options.no_color else THEME["dim"],
    )
    table.add_column("Field", style="none" if options.no_color else THEME["dim"])
    table.add_column("Value", style="none" if options.no_color else THEME["amber"])
    table.add_row("Name", str(profile.get("name", "Traveler")))
    table.add_row("Pronounced", str(profile.get("name_pronunciation", profile.get("name", "Traveler"))))
    table.add_row("Pronouns", str(profile.get("pronouns", "they/them")))
    table.add_row("Avatar", str(profile.get("avatar_name", "Moai Block")))
    table.add_row("Title", str(profile.get("title", "Wisdom Seeker")))
    table.add_row("Oath", "Accepted" if profile.get("oath_accepted") else "Not accepted")
    return table

def show_profile(profile: dict, app_name: str, options: RenderOptions) -> None:
    console = options.console
    avatar = get_avatar(str(profile.get("avatar_id", "moai_block")))
    if not options.compact:
        console.print(avatar.preview(options.no_emoji), style="none" if options.no_color else THEME["orange"])
    console.print(profile_table(profile, options))
    console.print()
    console.print(greeting_for(app_name, profile, options))


def greeting_for(app_name: str, profile: dict, options: RenderOptions) -> str:
    name = display_name_with_pronunciation(profile)
    avatar = profile.get("avatar_name", "Moai Block")
    if app_name == "irl":
        return f"Welcome back, {name}.\nAvatar: {avatar}\nReady to install something useful?"
    if app_name == "irl-wisdom":
        return f"The stone greets {name}.\nChoose a path."
    if app_name == "besty":
        return f"Emoji chaos awaits, {name}."
    if app_name == "transpower":
        return f"Welcome back, {name}.\nYour safe space is ready."
    return f"Welcome back, {name}."


def moai_name_line(name: str, options: RenderOptions) -> None:
    clean_name = (name or "Traveler").strip() or "Traveler"
    options.console.print(
        panel(
            f"The stone hears: {clean_name}.\nA name is not a cage. It is a campfire.",
            "Moai Response",
            options,
        )
    )


def run_first_launch(app_name: str, options: RenderOptions) -> dict:
    welcome_screen(app_name, options)
    name = ask_text("What should we call you?", os.getenv("USERNAME") or "Anika")
    moai_name_line(name, options)
    name_pronunciation = ask_name_pronunciation(name, options)
    pronouns = choose_pronouns()
    options.console.print(panel(f"Pronouns set: {pronouns}\nRespect saved. The terminal will remember.", "Identity Texture", options))
    avatar_id = choose_avatar(options, ["moai_block"])
    accepted = show_oath(options)
    if not accepted:
        options.console.print("Oath declined. The gate stays warm for later.")
        raise typer_exit()
    profile = create_profile(
        name=name,
        pronouns=pronouns,
        name_pronunciation=name_pronunciation,
        avatar_id=avatar_id,
        created_by_app=app_name,
    )
    options.console.print("Oath accepted.\nWelcome to the IRL Universe.")
    show_profile(profile, app_name, options)
    return profile

def typer_exit():
    import typer

    return typer.Exit(code=1)


def ensure_profile(app_name: str, options: RenderOptions) -> dict:
    profile = load_profile()
    if profile:
        return profile
    return run_first_launch(app_name, options)


def edit_profile(app_name: str, options: RenderOptions) -> dict:
    profile = ensure_profile(app_name, options)
    field = ask_choice("What do you want to change?", ["name", "pronunciation", "pronouns", "avatar", "title", "done"])
    if field == "done":
        return profile
    if field == "name":
        profile["name"] = ask_text("New name:", str(profile.get("name", "Traveler")))
    elif field == "pronunciation":
        profile["name_pronunciation"] = ask_name_pronunciation(str(profile.get("name", "Traveler")), options)
    elif field == "pronouns":
        profile["pronouns"] = choose_pronouns()
    elif field == "avatar":
        profile["avatar_id"] = choose_avatar(options, list(profile.get("unlocked_avatars", [])))
        profile["avatar_name"] = get_avatar(profile["avatar_id"]).display_name
    elif field == "title":
        profile["title"] = ask_text("New title:", str(profile.get("title", "Wisdom Seeker")))
    save_profile(profile)
    return profile

def confirm_reset(options: RenderOptions) -> None:
    if questionary.confirm("Reset the shared IRL profile?", default=False).ask():
        removed = reset_profile()
        options.console.print("Profile reset." if removed else "No profile existed.")
