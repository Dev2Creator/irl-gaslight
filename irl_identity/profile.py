from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .avatars import get_avatar

PROFILE_DIR = Path.home() / ".irl"
PROFILE_PATH = PROFILE_DIR / "profile.json"


def now_date() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def profile_exists() -> bool:
    return PROFILE_PATH.exists()


def load_profile() -> dict[str, Any] | None:
    if not PROFILE_PATH.exists():
        return None
    try:
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_profile(profile: dict[str, Any]) -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(
        json.dumps(profile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def create_profile(
    *,
    name: str,
    pronouns: str,
    avatar_id: str,
    created_by_app: str,
    name_pronunciation: str | None = None,
    title: str = "Wisdom Seeker",
) -> dict[str, Any]:
    avatar = get_avatar(avatar_id)
    clean_name = name.strip() or "Traveler"
    profile = {
        "name": clean_name,
        "name_pronunciation": (name_pronunciation or clean_name).strip() or clean_name,
        "pronouns": pronouns.strip() or "they/them",
        "avatar_id": avatar.avatar_id,
        "avatar_name": avatar.display_name,
        "title": title,
        "oath_accepted": True,
        "accepted_at": now_date(),
        "created_by_app": created_by_app,
        "wisdom_level": 1,
        "curiosity": 0,
        "streak": 0,
        "favorites_count": 0,
        "unlocked_avatars": [avatar.avatar_id],
        "ritual_counts": {},
        "updated_at": now_iso(),
    }
    save_profile(profile)
    return profile


def update_profile(**changes: Any) -> dict[str, Any]:
    profile = load_profile() or {}
    profile.update(changes)
    profile["updated_at"] = now_iso()
    if "avatar_id" in changes:
        profile["avatar_name"] = get_avatar(str(changes["avatar_id"])).display_name
    save_profile(profile)
    return profile


def reset_profile() -> bool:
    if PROFILE_PATH.exists():
        PROFILE_PATH.unlink()
        return True
    return False


def unlock_avatar(avatar_id: str) -> tuple[dict[str, Any], bool]:
    profile = load_profile() or {}
    unlocked = list(profile.get("unlocked_avatars", []))
    if avatar_id not in unlocked:
        unlocked.append(avatar_id)
        profile["unlocked_avatars"] = unlocked
        profile["updated_at"] = now_iso()
        save_profile(profile)
        return profile, True
    return profile, False


def increment_ritual(name: str) -> int:
    profile = load_profile() or {}
    counts = dict(profile.get("ritual_counts", {}))
    counts[name] = int(counts.get(name, 0)) + 1
    profile["ritual_counts"] = counts
    profile["updated_at"] = now_iso()
    save_profile(profile)
    return counts[name]