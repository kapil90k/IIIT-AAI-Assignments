# Roll number: evernorth-aai-1197201
"""Small persistent-memory store for Project SkyVault."""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


MEMORY_FILE = Path(
    os.getenv("SKYVAULT_MEMORY_FILE", str(Path(__file__).with_name("memory_store.json")))
)
_LOCK = threading.Lock()


def _read_store():
    if not MEMORY_FILE.exists():
        return {}
    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_store(data):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = MEMORY_FILE.with_suffix(MEMORY_FILE.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, sort_keys=True)
    temporary.replace(MEMORY_FILE)


def remember(key, value, source):
    """Persist a fact; a normalized key replaces its previous value."""
    normalized = str(key or "").strip().lower().replace(" ", "_")
    if not normalized:
        return {"status": False, "message": "Memory key must not be empty"}

    record = {
        "value": value,
        "source": str(source or "unknown"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with _LOCK:
            store = _read_store()
            replaced = normalized in store
            store[normalized] = record
            _write_store(store)
        return {
            "status": True,
            "result": {
                "key": normalized,
                "value": value,
                "replaced": replaced,
            },
        }
    except OSError as exc:
        return {"status": False, "message": "Could not persist memory: %s" % exc}


def recall(query):
    """Return exact or token-matched memories for a natural-language query."""
    normalized = str(query or "").strip().lower().replace(" ", "_")
    store = _read_store()
    if not normalized:
        matches = store
    elif normalized in store:
        matches = {normalized: store[normalized]}
    else:
        tokens = {token for token in normalized.split("_") if len(token) > 2}
        matches = {
            key: record
            for key, record in store.items()
            if tokens.intersection(set(key.split("_")))
            or any(token in str(record.get("value", "")).lower() for token in tokens)
        }

    if not matches:
        return {"status": False, "message": "No memory matched query: %s" % query}
    return {"status": True, "result": matches}


def memory_summary(max_items=20):
    """Build the short working-memory context injected at run start."""
    store = _read_store()
    if not store:
        return "No persistent facts are currently stored."
    lines = []
    for key, record in sorted(store.items())[:max_items]:
        lines.append("- %s: %s (source: %s)" % (key, record.get("value"), record.get("source")))
    return "\n".join(lines)
