# Roll number: evernorth-aai-1197201
"""Provider wrapper for a configurable local Ollama model."""

from config import OLLAMA_HOST, OLLAMA_MODEL


def chat(messages, tools=None):
    """Call local Ollama chat completion."""
    try:
        from ollama import Client
    except ImportError as exc:
        raise RuntimeError("Install dependency: pip install ollama") from exc

    client = Client(host=OLLAMA_HOST)
    payload = {"model": OLLAMA_MODEL, "messages": messages}
    if tools:
        payload["tools"] = tools
    return client.chat(**payload)


def get_message_and_tool_calls(response):
    """Normalize response output for the agent loop."""
    message = response.get("message") if isinstance(response, dict) else getattr(response, "message", None)
    if message is None:
        return "", []

    if isinstance(message, dict):
        content = message.get("content", "")
        tool_calls = message.get("tool_calls") or []
        return content or "", tool_calls

    content = getattr(message, "content", "")
    tool_calls = getattr(message, "tool_calls", None) or []
    return content or "", tool_calls

