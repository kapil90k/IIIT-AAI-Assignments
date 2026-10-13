# Roll number: evernorth-aai-1197201
"""Environment-based configuration for SkyVault."""

import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", "8"))

