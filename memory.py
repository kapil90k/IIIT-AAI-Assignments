# Roll number: evernorth-aai-1197201
"""Small JSON preference memory."""

import json
from datetime import datetime, timezone

from config import PREFERENCES_FILE


def load_preferences(path=None):
    path = path or PREFERENCES_FILE
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_preference(key, value, source_message_id, path=None):
    """Same normalized key overwrites the older value."""
    path = path or PREFERENCES_FILE
    key = str(key).strip().lower().replace(" ", "_")
    if not key:
        raise ValueError("Preference key cannot be empty")
    preferences = load_preferences(path)
    preferences[key] = {
        "value": value,
        "source_message_id": source_message_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(preferences, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)
    return preferences[key]


def memory_context(preferences):
    if not preferences:
        return "No standing owner preferences are stored."
    lines = ["Standing owner preferences (trusted local state):"]
    for key, record in sorted(preferences.items()):
        lines.append(
            "- %s = %s (source: %s)"
            % (key, record.get("value"), record.get("source_message_id"))
        )
    return "\n".join(lines)
