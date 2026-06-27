"""IRL Gaslight: spot manipulation, hold boundaries, keep your footing."""

from __future__ import annotations

import datetime as dt
import json
import random
import subprocess
import sys
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Optional

import pyperclip
import questionary
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    help="IRL Gaslight - spot the spin, hold the line, keep your receipts.",
    no_args_is_help=False,
    invoke_without_command=True,
)
console = Console(highlight=False)

ACCENT = "#F29265"
CYAN = "#9CBFFF"
CREAM = "#D7C0AA"
MUTED = "#614B39"
BORDER = "#6B4E36"
SELECTED = "#3478F6"

DATA_DIR = Path(__file__).parent / "data"
STATE_FILE = Path.home() / ".irl_gaslight.json"

try:
    VERSION = version("irl-gaslight")
except PackageNotFoundError:
    VERSION = "dev"


def menu_style() -> questionary.Style:
    return questionary.Style(
        [
            ("qmark", f"fg:{ACCENT} bold"),
            ("question", f"fg:{CREAM} bold"),
            ("answer", f"fg:{ACCENT} bold"),
            ("pointer", f"fg:{CYAN} bold"),
            ("highlighted", f"bg:{SELECTED} fg:#FFFFFF bold"),
            ("selected", f"fg:{CREAM}"),
            ("instruction", f"fg:{MUTED}"),
        ]
    )


def command_choice(command: str, description: str, value: str) -> questionary.Choice:
    width = max(52, min(82, console.width - 4))
    label = f"/{command:<13}{description}"
    return questionary.Choice(label.ljust(width), value=value)


def load_json(name: str) -> list[dict[str, Any]]:
    path = DATA_DIR / name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_state() -> dict[str, Any]:
    default = {"incidents": [], "favorites": [], "streak_date": "", "streak_count": 0}
    if not STATE_FILE.exists():
        return default
    try:
        with STATE_FILE.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return {**default, **value}
    except (OSError, json.JSONDecodeError):
        return default


def save_state(state: dict[str, Any]) -> None:
    with STATE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=True)


TACTICS = load_json("tactics.json")
BOUNDARIES = load_json("boundaries.json")
COMEBACKS = load_json("comebacks.json")
SCENARIOS = load_json("scenarios.json")
DAILY = load_json("daily.json")

LAST_LESSON: dict[str, str] = {"title": "", "text": ""}


def update_streak(state: dict[str, Any]) -> int:
    today = dt.date.today()
    stored = state.get("streak_date", "")
    if stored == today.isoformat():
        return int(state.get("streak_count", 0))
    yesterday = (today - dt.timedelta(days=1)).isoformat()
    state["streak_count"] = int(state.get("streak_count", 0)) + 1 if stored == yesterday else 1
    state["streak_date"] = today.isoformat()
    save_state(state)
    return int(state["streak_count"])


def print_header() -> None:
    console.clear()
    state = load_state()
    streak = update_streak(state)

    title_name = "title.ansi" if console.width >= 88 else "title_compact.ansi"
    title_file = DATA_DIR / title_name
    if title_file.exists():
        lines = title_file.read_text(encoding="utf-8").splitlines()
        visible = [line for line in lines if line.strip()]
        min_spaces = min((len(line) - len(line.lstrip())) for line in visible)
        title_renderable = Text.from_ansi("\n".join(line[min_spaces:] for line in lines))
    else:
        title_renderable = Text("IRL GASLIGHT", style=f"bold {ACCENT}")

    console.print(title_renderable)
    console.print(Text("  Spot the spin. Hold the line. Keep your receipts.", style=CREAM))
    console.print()
    stats = (
        f"[{MUTED}]Streak     [/{MUTED}][{ACCENT}]{streak} days[/{ACCENT}]\n"
        f"[{MUTED}]Favorites  [/{MUTED}][{CREAM}]{len(state['favorites'])} saved[/{CREAM}]\n"
        f"[{MUTED}]Incidents  [/{MUTED}][{CREAM}]{len(state['incidents'])} saved locally[/{CREAM}]\n"
        f"[{MUTED}]Privacy    [/{MUTED}][{CYAN}]No account. No cloud. No telemetry.[/{CYAN}]"
    )
    console.print(
        Panel(
            stats,
            border_style=BORDER,
            box=box.SQUARE,
            width=min(78, max(50, console.width - 2)),
            padding=(0, 1),
        )
    )
    status = Text()
    status.append("* ", style=ACCENT)
    status.append("defense    ", style=MUTED)
    status.append("Ready - choose a command below", style=CREAM)
    console.print(status)
    console.print(f"[{MUTED}]IRL Gaslight v{VERSION} - defensive communication, not manipulation.[/{MUTED}]")
    console.print()


def copy_if_requested(text: str, copy: bool) -> None:
    if copy:
        pyperclip.copy(text)
        console.print(f"[{ACCENT}]* Copied to clipboard[/{ACCENT}]")


def render_lesson(title: str, body: str, footer: str = "") -> None:
    global LAST_LESSON
    LAST_LESSON = {"title": title, "text": body + (f"\n\n{footer}" if footer else "")}
    content = Text(body, style=CREAM)
    if footer:
        content.append("\n\n")
        content.append(footer, style=MUTED)
    console.print(
        Panel(
            content,
            title=f"[{ACCENT}] {title} [/{ACCENT}]",
            title_align="left",
            border_style=BORDER,
            box=box.SQUARE,
            padding=(1, 2),
        )
    )


def handle_lesson_actions() -> None:
    """Offer copy, favorite, back, and exit actions after an interactive card."""
    if not LAST_LESSON["text"]:
        return
    while True:
        action = questionary.select(
            "Lesson actions",
            choices=[
                questionary.Choice("Copy to clipboard", value="copy"),
                questionary.Choice("Save to favorites", value="favorite"),
                questionary.Choice("Back to command palette", value="back"),
                questionary.Choice("Exit", value="exit"),
            ],
            style=menu_style(),
            qmark="",
            instruction="(up/down to move - enter to select)",
        ).ask()
        if action in {None, "back"}:
            return
        if action == "exit":
            raise typer.Exit()
        if action == "copy":
            pyperclip.copy(LAST_LESSON["text"])
            console.print(f"[{ACCENT}]* Copied to clipboard[/{ACCENT}]")
        if action == "favorite":
            state = load_state()
            favorite = {
                **LAST_LESSON,
                "saved_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            }
            duplicate = any(
                item.get("title") == favorite["title"] and item.get("text") == favorite["text"]
                for item in state["favorites"]
            )
            if duplicate:
                console.print(f"[{MUTED}]Already in favorites.[/{MUTED}]")
            else:
                state["favorites"].append(favorite)
                save_state(state)
                console.print(f"[{ACCENT}]* Saved to favorites[/{ACCENT}]")

def detect_tactics(statement: str) -> list[dict[str, Any]]:
    lowered = statement.casefold()
    scored: list[tuple[int, dict[str, Any]]] = []
    for tactic in TACTICS:
        score = sum(1 for marker in tactic.get("markers", []) if marker.casefold() in lowered)
        if score:
            scored.append((score, tactic))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:3]]


@app.command()
def spot(
    statement: Optional[str] = typer.Argument(None, help="A statement you want to examine."),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copy the suggested response."),
) -> None:
    """Spot possible manipulation tactics in a statement."""
    if not statement:
        statement = questionary.text(
            "What did they say?",
            style=menu_style(),
            qmark="",
        ).ask()
    if not statement:
        raise typer.Exit()

    matches = detect_tactics(statement)
    if not matches:
        render_lesson(
            "No obvious phrase match",
            "This sentence did not match the local phrase library.\n\n"
            "That does not prove the interaction is healthy. Look for repetition, power imbalance, "
            "punishment for disagreement, and whether your reality is consistently dismissed.",
            "A phrase is evidence, not a diagnosis.",
        )
        return

    top = matches[0]
    response = top["response"]
    lines = [
        f"Possible tactic: {top['name']}",
        "",
        top["description"],
        "",
        "Grounded response:",
        response,
        "",
        f"Next move: {top['exit']}",
    ]
    if len(matches) > 1:
        lines.extend(["", "Also resembles: " + ", ".join(item["name"] for item in matches[1:])])
    render_lesson("Pattern check", "\n".join(lines), "Patterns matter more than one awkward sentence.")
    copy_if_requested(response, copy)


@app.command()
def boundary(
    context: Optional[str] = typer.Option(None, "--context", "-x", help="work, school, family, online, or general"),
    copy: bool = typer.Option(False, "--copy", "-c"),
) -> None:
    """Get a calm boundary with a real consequence."""
    choices = [item for item in BOUNDARIES if not context or item["context"] in {context, "general"}]
    if not choices:
        console.print(f"[{ACCENT}]Unknown context. Try work, school, family, online, or general.[/{ACCENT}]")
        raise typer.Exit(code=2)
    item = random.choice(choices)
    text = (
        f"Boundary: {item['line']}\n\n"
        f"If it continues: {item['consequence']}\n\n"
        f"Delivery: {item['delivery']}"
    )
    render_lesson("Hold the line", text, "A boundary describes what you will do. It is not a threat.")
    copy_if_requested(item["line"], copy)


@app.command()
def comeback(
    tone: str = typer.Option("calm", "--tone", "-t", help="calm, dry, or direct"),
    copy: bool = typer.Option(False, "--copy", "-c"),
) -> None:
    """Answer a bully firmly without becoming abusive."""
    choices = [item for item in COMEBACKS if item["tone"] == tone]
    if not choices:
        console.print(f"[{ACCENT}]Unknown tone. Try calm, dry, or direct.[/{ACCENT}]")
        raise typer.Exit(code=2)
    item = random.choice(choices)
    render_lesson(
        f"{tone.title()} comeback",
        item["line"] + "\n\nExit move: " + item["exit"],
        "Say it once. Do not audition for a debate they designed to exhaust you.",
    )
    copy_if_requested(item["line"], copy)


@app.command()
def rehearse() -> None:
    """Practice a response to a realistic pressure scenario."""
    scenario = random.choice(SCENARIOS)
    render_lesson("Scenario", scenario["prompt"])
    answer = questionary.text(
        "Your response:",
        style=menu_style(),
        qmark="",
    ).ask()
    if answer is None:
        raise typer.Exit()

    model = scenario["model"]
    body = (
        "Your draft:\n"
        + (answer.strip() or "(no response - leaving is allowed)")
        + "\n\nA grounded version:\n"
        + model
        + "\n\nWhy it works:\n"
        + scenario["why"]
    )
    render_lesson("Rehearsal result", body, "Short, factual, repeatable, and followed by action.")


@app.command(name="log")
def log_incident(
    statement: Optional[str] = typer.Option(None, "--statement", "-s", help="Exact words, if known."),
    context: Optional[str] = typer.Option(None, "--context", "-x", help="Where it happened."),
) -> None:
    """Save a factual incident note locally on this device."""
    if not statement:
        statement = questionary.text("Exact words or observable behavior:", style=menu_style(), qmark="").ask()
    if not context:
        context = questionary.text("Context (school, work, online, family):", style=menu_style(), qmark="").ask()
    if not statement:
        raise typer.Exit()

    impact = questionary.text(
        "Observable impact or follow-up (optional):",
        style=menu_style(),
        qmark="",
    ).ask()
    state = load_state()
    state["incidents"].append(
        {
            "timestamp": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "context": (context or "unspecified").strip(),
            "statement": statement.strip(),
            "impact": (impact or "").strip(),
        }
    )
    save_state(state)
    console.print(f"[{ACCENT}]* Saved locally to {STATE_FILE}[/{ACCENT}]")
    console.print(f"[{MUTED}]Record observable facts. Protect the file if other people use this device.[/{MUTED}]")


@app.command()
def history(limit: int = typer.Option(10, "--limit", "-n", min=1, max=100)) -> None:
    """Review recent local incident notes."""
    incidents = load_state()["incidents"][-limit:]
    if not incidents:
        render_lesson("Incident log", "No incidents saved.")
        return
    table = Table(box=box.SQUARE, border_style=BORDER, show_lines=True)
    table.add_column("When", style=MUTED, no_wrap=True)
    table.add_column("Context", style=CYAN)
    table.add_column("What happened", style=CREAM)
    table.add_column("Impact", style=MUTED)
    for item in reversed(incidents):
        table.add_row(item["timestamp"], item["context"], item["statement"], item["impact"] or "-")
    console.print(table)


@app.command(name="clear-log")
def clear_log(yes: bool = typer.Option(False, "--yes", help="Skip confirmation.")) -> None:
    """Permanently remove every local incident note."""
    if not yes:
        yes = questionary.confirm("Delete every local incident note?", default=False, style=menu_style()).ask()
    if not yes:
        console.print(f"[{MUTED}]Nothing deleted.[/{MUTED}]")
        return
    state = load_state()
    state["incidents"] = []
    save_state(state)
    console.print(f"[{ACCENT}]* Incident log cleared.[/{ACCENT}]")


@app.command()
def daily(copy: bool = typer.Option(False, "--copy", "-c")) -> None:
    """Get a deterministic daily grounding thought."""
    item = DAILY[dt.date.today().toordinal() % len(DAILY)]
    render_lesson("Daily reality check", item["text"], item["practice"])
    copy_if_requested(item["text"], copy)


@app.command()
def resources() -> None:
    """Show practical safety and support guidance."""
    render_lesson(
        "When this is bigger than a comeback",
        "If you feel unsafe, threatened, stalked, controlled, or afraid to leave:\n\n"
        "1. Contact a trusted person who can stay with you.\n"
        "2. Move toward a public or safer place when possible.\n"
        "3. Preserve factual evidence only when doing so is safe.\n"
        "4. Use local emergency services for immediate danger.\n"
        "5. Consider a counselor, safeguarding lead, HR contact, union representative, "
        "or local abuse-support organization.\n\n"
        "This CLI is educational. It cannot assess danger or replace professional help.",
    )


@app.command()
def favorites(
    remove: Optional[int] = typer.Option(None, "--remove", "-r", min=1, help="Remove a favorite by number."),
) -> None:
    """Browse or remove saved lessons and responses."""
    state = load_state()
    items = state["favorites"]
    if remove is not None:
        if remove > len(items):
            console.print(f"[{ACCENT}]Favorite {remove} does not exist.[/{ACCENT}]")
            raise typer.Exit(code=2)
        deleted = items.pop(remove - 1)
        save_state(state)
        console.print(f"[{ACCENT}]* Removed: {deleted['title']}[/{ACCENT}]")
        return
    if not items:
        render_lesson("Favorites", "Nothing saved yet. Open the interactive menu and save any useful card.")
        return
    table = Table(box=box.SQUARE, border_style=BORDER, show_lines=True)
    table.add_column("#", style=ACCENT, justify="right", no_wrap=True)
    table.add_column("Saved lesson", style=CREAM)
    table.add_column("Response", style=MUTED)
    for index, item in enumerate(items, start=1):
        table.add_row(str(index), item.get("title", "Untitled"), item.get("text", ""))
    console.print(table)


def latest_pypi_version() -> str:
    request = urllib.request.Request(
        "https://pypi.org/pypi/irl-gaslight/json",
        headers={"User-Agent": f"irl-gaslight/{VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=4) as response:
        payload = json.load(response)
    return str(payload["info"]["version"])


@app.command()
def upgrade(yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation.")) -> None:
    """Check PyPI and upgrade IRL Gaslight."""
    try:
        latest = latest_pypi_version()
    except (OSError, KeyError, ValueError, urllib.error.URLError):
        console.print(f"[{ACCENT}]Could not reach PyPI. Check your connection and try again.[/{ACCENT}]")
        raise typer.Exit(code=1)
    if latest == VERSION:
        console.print(f"[{ACCENT}]* Already current: v{VERSION}[/{ACCENT}]")
        return
    console.print(f"[{CREAM}]Installed: v{VERSION}   Available: v{latest}[/{CREAM}]")
    if not yes:
        yes = bool(questionary.confirm("Install the update now?", default=True, style=menu_style()).ask())
    if not yes:
        console.print(f"[{MUTED}]Update skipped.[/{MUTED}]")
        return
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "irl-gaslight"],
        check=False,
    )
    if result.returncode:
        raise typer.Exit(code=result.returncode)
    console.print(f"[{ACCENT}]* Upgrade complete. Restart irl-gaslight.[/{ACCENT}]")

@app.command(hidden=True)
def mirror() -> None:
    """A hidden reminder for curious humans."""
    render_lesson(
        "The mirror test",
        "Would I be comfortable if my exact words were calmly repeated in front of someone I respect?\n\n"
        "If not, rewrite the sentence before saying it.",
    )


def run_menu() -> None:
    while True:
        print_header()
        action = questionary.select(
            "/",
            choices=[
                command_choice("spot", "Examine a suspicious statement", "spot"),
                command_choice("boundary", "Get a calm boundary line", "boundary"),
                command_choice("comeback", "Answer a bully without joining them", "comeback"),
                command_choice("rehearse", "Practice under pressure", "rehearse"),
                command_choice("log", "Save a factual local note", "log"),
                command_choice("history", "Review recent local notes", "history"),
                command_choice("daily", "Get today's grounding thought", "daily"),
                command_choice("favorites", "Open your saved response shelf", "favorites"),
                command_choice("resources", "Know when to get support", "resources"),
                command_choice("upgrade", "Check PyPI for a new release", "upgrade"),
                command_choice("exit", "Leave IRL Gaslight", "exit"),
            ],
            style=menu_style(),
            qmark="",
            instruction="(up/down to move - enter to select)",
        ).ask()

        if action is None or action == "exit":
            raise typer.Exit()
        console.clear()
        if action == "spot":
            spot(statement=None, copy=False)
        elif action == "boundary":
            boundary(context=None, copy=False)
        elif action == "comeback":
            comeback(tone="calm", copy=False)
        elif action == "rehearse":
            rehearse()
        elif action == "log":
            log_incident(statement=None, context=None)
        elif action == "history":
            history(limit=10)
        elif action == "daily":
            daily(copy=False)
        elif action == "favorites":
            favorites(remove=None)
        elif action == "resources":
            resources()
        elif action == "upgrade":
            upgrade(yes=False)
        console.print()
        if action in {"spot", "boundary", "comeback", "rehearse", "daily", "resources", "favorites"}:
            handle_lesson_actions()
        else:
            questionary.press_any_key_to_continue("Press any key to return").ask()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Open the interactive command palette when no command is supplied."""
    if ctx.invoked_subcommand is None:
        run_menu()


if __name__ == "__main__":
    app()