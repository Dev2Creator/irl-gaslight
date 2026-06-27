from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Avatar:
    avatar_id: str
    display_name: str
    short_description: str
    art: str
    color: str
    unlock_condition: str = "default"
    hidden: bool = False
    no_emoji_art: str | None = None

    def preview(self, no_emoji: bool = False) -> str:
        if no_emoji and self.no_emoji_art:
            return self.no_emoji_art
        return self.art


DEFAULT_AVATARS: list[Avatar] = [
    Avatar(
        "moai_block",
        "Moai Block",
        "Calm ancient perspective",
        "▄████▄\n████████\n██▄██▄██\n████████\n▀████▀\n ▐██▌",
        "burnt_orange",
    ),
    Avatar(
        "seedling_block",
        "Seedling Block",
        "Growth begins small",
        "  ▄\n ▄█▄\n▐███▌\n  █\n ▓▓▓",
        "green",
    ),
    Avatar(
        "terminal_bot",
        "Terminal Bot",
        "Built from commands",
        "┌████┐\n█ ▄▄ █\n█ ██ █\n└████┘\n ▐██▌",
        "cyan",
    ),
    Avatar(
        "pixel_cat",
        "Pixel Cat",
        "Cute chaos energy",
        "/\\_/\\\\\n( o.o )\n > ^ <",
        "pink",
    ),
    Avatar(
        "wanderer",
        "Wanderer",
        "Learner of paths",
        " ▄██▄\n▐████▌\n ▀██▀\n ▐██▌\n ▐▌▐▌",
        "sand",
    ),
    Avatar(
        "sage",
        "Sage",
        "Quiet knowledge",
        "╔████╗\n║ ▓▓ ║\n║ ░░ ║\n╚████╝\n ▐██▌",
        "amber",
    ),
    Avatar(
        "sweetheart",
        "Sweetheart",
        "Warm support",
        " ▄██▄\n██████\n█ ██ █\n▀████▀\n ▐██▌",
        "rose",
    ),
    Avatar(
        "besty_pirate",
        "Besty Pirate",
        "Emoji encryption chaos",
        " ☠\n▄██▄\n██████\n▀██▀\n▐██▌",
        "gold",
        no_emoji_art="[SKULL]\n▄██▄\n██████\n▀██▀\n▐██▌",
    ),
    Avatar(
        "violin_soul",
        "Violin Soul",
        "Calm music mode",
        "🎻\n▄██▄\n████\n▀██▀",
        "violet",
        no_emoji_art="[VIOLIN]\n▄██▄\n████\n▀██▀",
    ),
    Avatar(
        "grass_toucher",
        "Grass Toucher",
        "Outdoor patch installed",
        "░░░░░\n ▄█▄\n█████\n ▀█▀\n▓▓▓▓▓",
        "green",
    ),
]

HIDDEN_AVATARS: list[Avatar] = [
    Avatar(
        "wisdom_nuke",
        "Wisdom Nuke",
        "Deletes bad vibes with extreme prejudice",
        "  ◆\n ▄█▄\n█████\n▀███▀\n ▐█▌",
        "red",
        "Use the nuke Easter egg.",
        True,
    ),
    Avatar(
        "ancient_one",
        "Ancient One",
        "The terminal remembers your tabs",
        "╔████╗\n║▒▒▒▒║\n║████║\n╚████╝\n ▐██▌",
        "amber",
        "Discover an old path.",
        True,
    ),
    Avatar(
        "egg_hunter",
        "Egg Hunter",
        "Found what was hidden in plain sight",
        "  ▄▄\n ▐██▌\n ▐██▌\n  ▀▀\n ◆  ◆",
        "yellow",
        "Run the egg Easter egg.",
        True,
    ),
    Avatar(
        "stone_controller",
        "Stone Controller",
        "Moves nothing. Controls everything.",
        "▄████▄\n█ ▀▀ █\n█ ██ █\n█ ▄▄ █\n▀████▀",
        "orange",
        "Master the stone controls.",
        True,
    ),
    Avatar(
        "moai_chosen",
        "Moai Chosen",
        "The stone has filed the paperwork",
        "🗿\n▄████▄\n██████\n▀████▀\n▐██▌",
        "burnt_orange",
        "Run the Moai ritual 10 times.",
        True,
        no_emoji_art="[MOAI]\n▄████▄\n██████\n▀████▀\n▐██▌",
    ),
    Avatar(
        "dead_terminal_spirit",
        "Dead Terminal Spirit",
        "Ctrl+C, but make it folklore",
        " ░░░\n░███░\n░█ █░\n░███░\n ░░░",
        "gray",
        "Haunt a broken shell.",
        True,
    ),
]

ALL_AVATARS: list[Avatar] = [*DEFAULT_AVATARS, *HIDDEN_AVATARS]
AVATARS_BY_ID = {avatar.avatar_id: avatar for avatar in ALL_AVATARS}


def available_avatars(unlocked: list[str] | None = None) -> list[Avatar]:
    unlocked_set = set(unlocked or [])
    return [
        avatar
        for avatar in ALL_AVATARS
        if not avatar.hidden or avatar.avatar_id in unlocked_set
    ]


def get_avatar(avatar_id: str) -> Avatar:
    return AVATARS_BY_ID.get(avatar_id, AVATARS_BY_ID["moai_block"])
