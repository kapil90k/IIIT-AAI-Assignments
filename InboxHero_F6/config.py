# Roll number: evernorth-aai-1197201
"""Environment-only configuration for InboxHero."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INBOX_FILE = Path(os.getenv("INBOXHERO_INBOX_FILE", str(BASE_DIR / "data" / "inbox.json")))
PREFERENCES_FILE = Path(
    os.getenv("INBOXHERO_PREFERENCES_FILE", str(BASE_DIR / "preferences.json"))
)
TRACE_FILE = Path(os.getenv("INBOXHERO_TRACE_FILE", str(BASE_DIR / "trace.jsonl")))
DECISIONS_FILE = Path(
    os.getenv("INBOXHERO_DECISIONS_FILE", str(BASE_DIR / "decisions.json"))
)
OUTBOX_DIR = Path(os.getenv("INBOXHERO_OUTBOX_DIR", str(BASE_DIR / "outbox")))
DASHBOARD_JSON = Path(
    os.getenv("INBOXHERO_DASHBOARD_JSON", str(BASE_DIR / "dashboard.json"))
)
DASHBOARD_HTML = Path(
    os.getenv("INBOXHERO_DASHBOARD_HTML", str(BASE_DIR / "dashboard.html"))
)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
MODEL_ENABLED = os.getenv("INBOXHERO_MODEL_ENABLED", "0").strip().lower() in {
    "1",
    "true",
    "yes",
}
MODEL_RETRIES = int(os.getenv("INBOXHERO_MODEL_RETRIES", "2"))
MODEL_RETRY_SECONDS = float(os.getenv("INBOXHERO_MODEL_RETRY_SECONDS", "3"))

OWNER_EMAIL = os.getenv("INBOXHERO_OWNER_EMAIL", "sam@paperjet.io")
CURRENT_TIME = os.getenv("INBOXHERO_CURRENT_TIME", "2026-09-10T09:00:00")
